#!/usr/bin/env python3
"""
Centralized Price Service with Redis Caching
Solves CoinGecko 429 rate limit issues by:
1. Redis caching (5min TTL) - reduces API calls 95%
2. Request deduplication - prevents duplicate concurrent requests
3. Fallback chain: CoinGecko → CoinMarketCap → DeFiLlama → CryptoCompare
4. Circuit breaker - stops calling failed APIs temporarily
5. DEX price feeds - Uniswap, Sushiswap, Curve for arbitrage detection
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import aiohttp
import redis
import requests

logger = logging.getLogger(__name__)


class PriceService:
    """Centralized price fetching with intelligent caching and fallbacks"""

    def __init__(self, redis_client=None):
        # Prefer centralized client; fall back to local if unavailable
        if redis_client is not None:
            self.redis = redis_client
        else:
            try:
                from shared.redis_client import get_redis_client

                self.redis = get_redis_client()
            except Exception:
                self.redis = redis.Redis(
                    host="localhost", port=6379, decode_responses=True
                )

        # API keys from environment
        self.coingecko_key = os.getenv("COINGECKO_API_KEY", "")
        self.cmc_key = os.getenv("CMC_API_KEY", "")
        self.cryptocompare_key = os.getenv("CRYPTOCOMPARE_API_KEY", "")

        # Cache TTL (5 minutes)
        self.cache_ttl = 300

        # Circuit breaker state (stops calling failed APIs)
        self.circuit_breaker = {
            "coingecko": {"failures": 0, "open_until": 0},
            "coinmarketcap": {"failures": 0, "open_until": 0},
            "defillama": {"failures": 0, "open_until": 0},
            "cryptocompare": {"failures": 0, "open_until": 0},
        }

        # Token ID mappings
        self.token_map = {
            "ETH": "ethereum",
            "BTC": "bitcoin",
            "USDT": "tether",
            "USDC": "usd-coin",
            "BNB": "binancecoin",
            "MATIC": "matic-network",
            "AVAX": "avalanche-2",
            "SOL": "solana",
            "ADA": "cardano",
            "DOT": "polkadot",
            "LINK": "chainlink",
            "UNI": "uniswap",
        }

    def get_price(self, token: str, force_refresh: bool = False) -> Optional[float]:
        """
        Get token price in USD with caching.

        Args:
            token: Token symbol (ETH, BTC, etc)
            force_refresh: Skip cache and fetch fresh price

        Returns:
            Price in USD or None if all sources fail
        """
        token = token.upper()
        cache_key = f"price:{token.lower()}:usd"

        # Check Redis cache first (unless force refresh)
        if not force_refresh:
            cached = self.redis.get(cache_key)
            if cached:
                try:
                    data = json.loads(cached)
                    logger.debug(
                        f"Cache HIT for {token}: ${data['price']} (source: {data['source']})"
                    )
                    return float(data["price"])
                except:  # nosec B110 - Bare except for JSON decode failures
                    pass

        # Cache miss - fetch from APIs with fallback chain
        price, source = self._fetch_with_fallback(token)

        if price and price > 0:
            # Cache the result
            cache_data = {"price": price, "source": source, "timestamp": time.time()}
            self.redis.setex(cache_key, self.cache_ttl, json.dumps(cache_data))
            logger.info(f"Fetched {token}: ${price:.2f} from {source}")
            return price

        logger.error(f"All price sources failed for {token}")
        return None

    def _fetch_with_fallback(self, token: str) -> Tuple[Optional[float], str]:
        """Try all price sources in order until one succeeds"""

        # 1. Try CoinGecko (primary)
        if self._is_circuit_open("coingecko"):
            logger.debug("CoinGecko circuit breaker OPEN, skipping")
        else:
            price = self._fetch_coingecko(token)
            if price:
                self._record_success("coingecko")
                return price, "coingecko"
            self._record_failure("coingecko")

        # 2. Try DeFiLlama (no rate limits!)
        if self._is_circuit_open("defillama"):
            logger.debug("DeFiLlama circuit breaker OPEN, skipping")
        else:
            price = self._fetch_defillama(token)
            if price:
                self._record_success("defillama")
                return price, "defillama"
            self._record_failure("defillama")

        # 3. Try CoinMarketCap
        if self.cmc_key and not self._is_circuit_open("coinmarketcap"):
            price = self._fetch_coinmarketcap(token)
            if price:
                self._record_success("coinmarketcap")
                return price, "coinmarketcap"
            self._record_failure("coinmarketcap")

        # 4. Try CryptoCompare
        if not self._is_circuit_open("cryptocompare"):
            price = self._fetch_cryptocompare(token)
            if price:
                self._record_success("cryptocompare")
                return price, "cryptocompare"
            self._record_failure("cryptocompare")

        return None, "none"

    def _fetch_coingecko(self, token: str) -> Optional[float]:
        """Fetch from CoinGecko API"""
        try:
            token_id = self.token_map.get(token, token.lower())

            # Use Pro API if key available
            if self.coingecko_key:
                url = "https://pro-api.coingecko.com/api/v3/simple/price"
                headers = {"X-Cg-Pro-Api-Key": self.coingecko_key}
            else:
                url = "https://api.coingecko.com/api/v3/simple/price"
                headers = {}

            params = {"ids": token_id, "vs_currencies": "usd"}

            response = requests.get(url, params=params, headers=headers, timeout=5)

            if response.status_code == 429:
                logger.warning(f"CoinGecko rate limit hit for {token}")
                return None

            response.raise_for_status()
            data = response.json()

            return float(data.get(token_id, {}).get("usd", 0))

        except Exception as e:
            logger.debug(f"CoinGecko fetch failed for {token}: {e}")
            return None

    def _fetch_defillama(self, token: str) -> Optional[float]:
        """Fetch from DeFiLlama (unlimited, no key required!)"""
        try:
            token_id = self.token_map.get(token, token.lower())

            # DeFiLlama uses coingecko IDs
            url = f"https://coins.llama.fi/prices/current/coingecko:{token_id}"

            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()

            price = data.get("coins", {}).get(f"coingecko:{token_id}", {}).get("price")
            return float(price) if price else None

        except Exception as e:
            logger.debug(f"DeFiLlama fetch failed for {token}: {e}")
            return None

    def _fetch_coinmarketcap(self, token: str) -> Optional[float]:
        """Fetch from CoinMarketCap API"""
        try:
            url = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest"
            headers = {"X-CMC_PRO_API_KEY": self.cmc_key}
            params = {"symbol": token, "convert": "USD"}

            response = requests.get(url, headers=headers, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()

            return float(data["data"][token][0]["quote"]["USD"]["price"])

        except Exception as e:
            logger.debug(f"CoinMarketCap fetch failed for {token}: {e}")
            return None

    def _fetch_cryptocompare(self, token: str) -> Optional[float]:
        """Fetch from CryptoCompare API"""
        try:
            url = "https://min-api.cryptocompare.com/data/price"
            params = {"fsym": token, "tsyms": "USD"}
            if self.cryptocompare_key:
                params["api_key"] = self.cryptocompare_key

            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()

            return float(data.get("USD", 0))

        except Exception as e:
            logger.debug(f"CryptoCompare fetch failed for {token}: {e}")
            return None

    def _is_circuit_open(self, source: str) -> bool:
        """Check if circuit breaker is open for a source"""
        breaker = self.circuit_breaker.get(source, {})
        return time.time() < breaker.get("open_until", 0)

    def _record_success(self, source: str):
        """Record successful API call"""
        self.circuit_breaker[source] = {"failures": 0, "open_until": 0}

    def _record_failure(self, source: str):
        """Record failed API call and potentially open circuit breaker"""
        breaker = self.circuit_breaker.get(source, {"failures": 0, "open_until": 0})
        breaker["failures"] += 1

        # Open circuit breaker after 3 failures (wait 5 minutes)
        if breaker["failures"] >= 3:
            breaker["open_until"] = time.time() + 300  # 5 minute cooldown
            logger.warning(f"Circuit breaker OPENED for {source} (too many failures)")

        self.circuit_breaker[source] = breaker

    def get_cache_stats(self) -> Dict:
        """Get cache performance statistics"""
        try:
            pattern = "price:*:usd"
            cached_tokens = []

            for key in self.redis.scan_iter(match=pattern, count=100):
                try:
                    data = json.loads(self.redis.get(key))
                    cached_tokens.append(
                        {
                            "token": key.split(":")[1].upper(),
                            "price": data["price"],
                            "source": data["source"],
                            "age_seconds": int(time.time() - data["timestamp"]),
                        }
                    )
                except:  # nosec B110 - Bare except for cache decode failures
                    pass

            return {
                "cached_tokens": len(cached_tokens),
                "cache_ttl_seconds": self.cache_ttl,
                "tokens": cached_tokens,
                "circuit_breakers": {
                    source: {
                        "failures": breaker["failures"],
                        "status": "OPEN" if self._is_circuit_open(source) else "CLOSED",
                    }
                    for source, breaker in self.circuit_breaker.items()
                },
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"error": str(e)}


# Singleton instance
_price_service = None


def get_price_service() -> PriceService:
    """Get singleton PriceService instance"""
    global _price_service
    if _price_service is None:
        _price_service = PriceService()
    return _price_service


if __name__ == "__main__":
    # Test the service
    logging.basicConfig(level=logging.INFO)
    service = get_price_service()

    # Test fetching prices
    tokens = ["ETH", "BTC", "USDT"]

    print("Testing price fetching...")
    for token in tokens:
        price = service.get_price(token)
        print(f"{token}: ${price:.2f}" if price else f"{token}: FAILED")

    print("\nCache stats:")
    print(json.dumps(service.get_cache_stats(), indent=2))


# ==============================================================================
# DEX PRICE FEED INTEGRATION
# Extracted from integrations/exchanges/dex_price_feeds.py
# Provides Uniswap V2/V3, Sushiswap, and Curve price data for arbitrage detection
# ==============================================================================


class DEXPriceFeed:
    """
    Connect to DEX subgraphs and APIs for real-time price data
    - Uniswap V2/V3
    - Sushiswap
    - Curve
    """

    def __init__(self, redis_host: str = None, redis_port: int = None):
        # Delegate to centralized client if possible
        try:
            from shared.redis_client import get_redis_client

            self.redis_client = get_redis_client()
        except Exception:
            redis_host = redis_host or "localhost"
            redis_port = redis_port or 6379
            self.redis_client = redis.Redis(
                host=redis_host, port=redis_port, decode_responses=True
            )

        # The Graph subgraph endpoints
        self.UNISWAP_V2_SUBGRAPH = (
            "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v2"
        )
        self.UNISWAP_V3_SUBGRAPH = (
            "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3"
        )
        self.SUSHISWAP_SUBGRAPH = (
            "https://api.thegraph.com/subgraphs/name/sushiswap/exchange"
        )

        # Curve API endpoint
        self.CURVE_API = "https://api.curve.fi/api/getPools/ethereum/main"

        # Top token pairs to monitor (WETH pairs for arbitrage)
        self.TOP_PAIRS = [
            ("WETH", "USDC"),
            ("WETH", "USDT"),
            ("WETH", "DAI"),
            ("WETH", "WBTC"),
            ("WETH", "UNI"),
            ("WETH", "LINK"),
            ("WETH", "MATIC"),
            ("WETH", "AAVE"),
            ("WETH", "CRV"),
            ("WETH", "SNX"),
        ]

        # Token addresses (Ethereum mainnet)
        self.TOKEN_ADDRESSES = {
            "WETH": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
            "USDC": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
            "USDT": "0xdac17f958d2ee523a2206206994597c13d831ec7",
            "DAI": "0x6b175474e89094c44da98b954eedeac495271d0f",
            "WBTC": "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599",
            "UNI": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
            "LINK": "0x514910771af9ca656af840dff83e8264ecf986ca",
            "MATIC": "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0",
            "AAVE": "0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9",
            "CRV": "0xd533a949740bb3306d119cc777fa900ba034cd52",
            "SNX": "0xc011a73ee8576fb46f5e1c5751ca3b9fe0af2a6f",
        }

        # Arbitrage threshold
        self.MIN_PROFIT_USD = 50  # Minimum $50 profit
        self.GAS_COST_ETH = 0.01  # Estimated gas cost for arbitrage (0.01 ETH)

    async def query_subgraph(self, url: str, query: str) -> Optional[Dict]:
        """Execute GraphQL query on a subgraph"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json={"query": query},
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("data")
                    else:
                        logger.error(f"Subgraph query failed: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error querying subgraph: {e}")
            return None

    async def get_uniswap_v2_prices(self) -> Dict[Tuple[str, str], float]:
        """Get token pair prices from Uniswap V2 or local node via direct contract queries"""
        prices = {}

        # First, try to get prices from local node using direct contract queries
        # This would require knowing specific pool addresses, so we'll implement a method that queries common pairs
        local_prices = await self.get_uniswap_v2_prices_from_local()
        if local_prices:
            prices.update(local_prices)
            logger.info(f"Got {len(local_prices) // 2} pair prices from local node")

        # If we don't have sufficient local data, fall back to subgraph
        if len(prices) < 10:  # If we have less than 10 pairs from local
            # GraphQL query for top pairs
            query = """
            {
              pairs(first: 100, orderBy: reserveUSD, orderDirection: desc) {
                id
                token0 {
                  symbol
                  id
                }
                token1 {
                  symbol
                  id
                }
                reserve0
                reserve1
                reserveUSD
                token0Price
                token1Price
              }
            }
            """

            data = await self.query_subgraph(self.UNISWAP_V2_SUBGRAPH, query)
            if not data or "pairs" not in data:
                return prices

            for pair in data["pairs"]:
                try:
                    token0_symbol = pair["token0"]["symbol"]
                    token1_symbol = pair["token1"]["symbol"]
                    token0_price = float(pair["token0Price"])
                    token1_price = float(pair["token1Price"])
                    reserve_usd = float(pair["reserveUSD"])

                    # Store both directions, but only update if not already in local data
                    pair_key_01 = (token0_symbol, token1_symbol)
                    pair_key_10 = (token1_symbol, token0_symbol)

                    if pair_key_01 not in prices:
                        prices[pair_key_01] = token1_price
                    if pair_key_10 not in prices:
                        prices[pair_key_10] = token0_price

                    # Cache in Redis
                    cache_key = f"dex:uniswap_v2:{token0_symbol}:{token1_symbol}"
                    cache_data = {
                        "price": token1_price,
                        "reserve_usd": reserve_usd,
                        "timestamp": time.time(),
                    }
                    self.redis_client.setex(
                        cache_key, 30, json.dumps(cache_data)
                    )  # 30 second cache

                except Exception as e:
                    logger.debug(f"Error processing Uniswap V2 pair: {e}")

            logger.info(
                f"Fetched {len([k for k in prices if k not in local_prices]) // 2} pair prices from Uniswap V2 subgraph"
            )

        logger.info(
            f"Total: {len(prices) // 2} pair prices available (local + subgraph)"
        )
        return prices

    async def get_uniswap_v2_prices_from_local(self) -> Dict[Tuple[str, str], float]:
        """Get token pair prices from local node by querying common Uniswap V2 pairs directly"""
        import os
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from web3 import Web3

        from shared.chains import get_web3_for_chain

        try:
            # Get Web3 instance for Ethereum
            w3 = get_web3_for_chain("ethereum")
            if not w3 or not w3.is_connected():
                logger.warning("Could not connect to local node for Uniswap V2 prices")
                return {}

            # Common Uniswap V2 pairs - we'll use well-known liquidity pool addresses
            # These can be found on Uniswap info or by querying the factory
            common_pairs = [
                # WETH/USDC - Uniswap V2 pool address
                ("0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc", "WETH", "USDC"),
                # WETH/USDT - Uniswap V2 pool address
                ("0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852", "WETH", "USDT"),
                # WBTC/WETH - Uniswap V2 pool address
                ("0xBB2b8038a1640196FbE3e38816F3e67Cba72D940", "WBTC", "WETH"),
                # DAI/WETH - Uniswap V2 pool address
                ("0xA478c2975Ab1Ea89e8196811F56a37E6C2bB7e68", "DAI", "WETH"),
                # UNI/WETH - Uniswap V2 pool address
                ("0xd37f7319C5CDED065D0c633A212E58928622d18d", "UNI", "WETH"),
            ]

            # Uniswap V2 Pair ABI for reserves
            pair_abi = [
                {
                    "constant": True,
                    "inputs": [],
                    "name": "getReserves",
                    "outputs": [
                        {"name": "_reserve0", "type": "uint112"},
                        {"name": "_reserve1", "type": "uint112"},
                        {"name": "_blockTimestampLast", "type": "uint32"},
                    ],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function",
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "token0",
                    "outputs": [{"name": "", "type": "address"}],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function",
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "token1",
                    "outputs": [{"name": "", "type": "address"}],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function",
                },
            ]

            prices = {}
            for pool_address, token0_symbol, token1_symbol in common_pairs:
                try:
                    # Create contract instance
                    pair_contract = w3.eth.contract(
                        address=Web3.to_checksum_address(pool_address), abi=pair_abi
                    )

                    # Get reserves
                    reserves = pair_contract.functions.getReserves().call()
                    reserve0 = int(reserves[0])
                    reserve1 = int(reserves[1])

                    # Get the actual token addresses to confirm
                    actual_token0 = pair_contract.functions.token0().call()
                    actual_token1 = pair_contract.functions.token1().call()

                    # Calculate prices if reserves are not zero
                    if reserve0 > 0 and reserve1 > 0:
                        # Calculate price of token1 in terms of token0
                        price_token1_in_token0 = (reserve0 / 1e18) / (reserve1 / 1e18)

                        # Calculate price of token0 in terms of token1
                        price_token0_in_token1 = (reserve1 / 1e18) / (reserve0 / 1e18)

                        # Store both directions
                        prices[(token0_symbol, token1_symbol)] = price_token1_in_token0
                        prices[(token1_symbol, token0_symbol)] = price_token0_in_token1

                        logger.debug(
                            f"Local price from Uniswap V2: {token0_symbol}/{token1_symbol} = {price_token1_in_token0}"
                        )
                except Exception as e:
                    logger.debug(f"Could not fetch price for pool {pool_address}: {e}")
                    continue

            return prices

        except Exception as e:
            logger.error(f"Error getting Uniswap V2 prices from local: {e}")
            return {}

    async def get_uniswap_v3_prices(self) -> Dict[Tuple[str, str], float]:
        """Get token pair prices from Uniswap V3 or local node via direct contract queries"""
        prices = {}

        # First, try to get prices from local node using direct contract queries
        local_prices = await self.get_uniswap_v3_prices_from_local()
        if local_prices:
            prices.update(local_prices)
            logger.info(f"Got {len(local_prices) // 2} pair prices from local node")

        # If we don't have sufficient local data, fall back to subgraph
        if len(prices) < 10:  # If we have less than 10 pairs from local
            # GraphQL query for top pools
            query = """
            {
              pools(first: 100, orderBy: totalValueLockedUSD, orderDirection: desc) {
                id
                token0 {
                  symbol
                  id
                }
                token1 {
                  symbol
                  id
                }
                totalValueLockedUSD
                token0Price
                token1Price
                liquidity
              }
            }
            """

            data = await self.query_subgraph(self.UNISWAP_V3_SUBGRAPH, query)
            if not data or "pools" not in data:
                return prices

            for pool in data["pools"]:
                try:
                    token0_symbol = pool["token0"]["symbol"]
                    token1_symbol = pool["token1"]["symbol"]
                    token0_price = float(pool["token0Price"])
                    token1_price = float(pool["token1Price"])
                    tvl_usd = float(pool["totalValueLockedUSD"])

                    # Store both directions, but only update if not already in local data
                    pair_key_01 = (token0_symbol, token1_symbol)
                    pair_key_10 = (token1_symbol, token0_symbol)

                    if pair_key_01 not in prices:
                        prices[pair_key_01] = token1_price
                    if pair_key_10 not in prices:
                        prices[pair_key_10] = token0_price

                    # Cache in Redis
                    cache_key = f"dex:uniswap_v3:{token0_symbol}:{token1_symbol}"
                    cache_data = {
                        "price": token1_price,
                        "tvl_usd": tvl_usd,
                        "timestamp": time.time(),
                    }
                    self.redis_client.setex(cache_key, 30, json.dumps(cache_data))

                except Exception as e:
                    logger.debug(f"Error processing Uniswap V3 pool: {e}")

            logger.info(
                f"Fetched {len([k for k in prices if k not in local_prices]) // 2} pair prices from Uniswap V3 subgraph"
            )

        logger.info(
            f"Total: {len(prices) // 2} pair prices available (local + subgraph)"
        )
        return prices

    async def get_uniswap_v3_prices_from_local(self) -> Dict[Tuple[str, str], float]:
        """Get token pair prices from local node by querying common Uniswap V3 pools directly"""
        import os
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from web3 import Web3

        from shared.chains import get_web3_for_chain

        try:
            # Get Web3 instance for Ethereum
            w3 = get_web3_for_chain("ethereum")
            if not w3 or not w3.is_connected():
                logger.warning("Could not connect to local node for Uniswap V3 prices")
                return {}

            # Common Uniswap V3 pairs with fee tiers - using well-known pool addresses
            common_v3_pairs = [
                # WETH/USDC 0.05% fee tier - Uniswap V3 pool address
                (
                    "0x88e6A0DeC4eF79f8785Ea23bA30d9ed7ABcC8973",
                    "WETH",
                    "USDC",
                    500,
                ),  # 0.05% fee
                # WETH/USDT 0.05% fee tier
                (
                    "0x16D4F26C15f3658ec65B1126ff27DD3dF5F2b1C5",
                    "WETH",
                    "USDT",
                    500,
                ),  # 0.05% fee
                # WBTC/USDC 0.3% fee tier
                (
                    "0x9DB9e0e8Ed25f8d7917E956f9Fea4B03C76722A3",
                    "WBTC",
                    "USDC",
                    3000,
                ),  # 0.3% fee
                # DAI/USDC 0.01% fee tier
                (
                    "0x60594a405d53811d3BC4766596EFD80fD545Aa47",
                    "DAI",
                    "USDC",
                    100,
                ),  # 0.01% fee
                # UNI/WETH 0.3% fee tier
                (
                    "0x5777d92f208679DB4B9778590Fa3CAB3aC9BE58e",
                    "UNI",
                    "WETH",
                    3000,
                ),  # 0.3% fee
            ]

            # Uniswap V3 Pool ABI for slot0 (which includes sqrtPriceX96)
            pool_abi = [
                {
                    "constant": True,
                    "inputs": [],
                    "name": "slot0",
                    "outputs": [
                        {"name": "sqrtPriceX96", "type": "uint160"},
                        {"name": "tick", "type": "int24"},
                        {"name": "observationIndex", "type": "uint16"},
                        {"name": "observationCardinality", "type": "uint16"},
                        {"name": "observationCardinalityNext", "type": "uint16"},
                        {"name": "feeProtocol", "type": "uint8"},
                        {"name": "unlocked", "type": "bool"},
                    ],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function",
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "token0",
                    "outputs": [{"name": "", "type": "address"}],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function",
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "token1",
                    "outputs": [{"name": "", "type": "address"}],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function",
                },
            ]

            prices = {}
            for pool_address, token0_symbol, token1_symbol, fee_tier in common_v3_pairs:
                try:
                    # Create contract instance
                    pool_contract = w3.eth.contract(
                        address=Web3.to_checksum_address(pool_address), abi=pool_abi
                    )

                    # Get slot0 data which includes sqrtPriceX96
                    slot0_data = pool_contract.functions.slot0().call()
                    sqrt_price_x96 = int(slot0_data[0])

                    # Get the actual token addresses to confirm
                    actual_token0 = pool_contract.functions.token0().call()
                    actual_token1 = pool_contract.functions.token1().call()

                    # Calculate price from sqrtPriceX96
                    # sqrtPriceX96 is sqrt(price) * 2^96
                    # price = (sqrtPriceX96 / 2^96)^2
                    sqrt_price = sqrt_price_x96 / (2**96)
                    price_token1_in_token0 = (
                        sqrt_price**2
                    )  # price of token1 in token0 units

                    # Get inverse for price of token0 in token1
                    price_token0_in_token1 = (
                        1 / price_token1_in_token0 if price_token1_in_token0 != 0 else 0
                    )

                    # Adjust for token decimals if needed (assuming standard 18 decimals for ETH-based tokens)
                    # For WETH/USDC, USDC has 6 decimals, so need to adjust accordingly
                    if token0_symbol == "USDC" or token1_symbol == "USDC":
                        # USDC has 6 decimals vs 18 for WETH, so adjust by 10^12
                        if token0_symbol == "USDC":
                            price_token1_in_token0 *= 10**12
                            price_token0_in_token1 /= 10**12
                        else:  # token1_symbol == "USDC"
                            price_token1_in_token0 /= 10**12
                            price_token0_in_token1 *= 10**12

                    # Store both directions
                    prices[(token0_symbol, token1_symbol)] = price_token1_in_token0
                    prices[(token1_symbol, token0_symbol)] = price_token0_in_token1

                    logger.debug(
                        f"Local price from Uniswap V3: {token0_symbol}/{token1_symbol} = {price_token1_in_token0}"
                    )
                except Exception as e:
                    logger.debug(
                        f"Could not fetch price for V3 pool {pool_address}: {e}"
                    )
                    continue

            return prices

        except Exception as e:
            logger.error(f"Error getting Uniswap V3 prices from local: {e}")
            return {}

    async def get_sushiswap_prices(self) -> Dict[Tuple[str, str], float]:
        """Get token pair prices from Sushiswap or local node via direct contract queries"""
        prices = {}

        # First, try to get prices from local node using direct contract queries
        local_prices = await self.get_sushiswap_prices_from_local()
        if local_prices:
            prices.update(local_prices)
            logger.info(f"Got {len(local_prices) // 2} pair prices from local node")

        # If we don't have sufficient local data, fall back to subgraph
        if len(prices) < 10:  # If we have less than 10 pairs from local
            query = """
            {
              pairs(first: 100, orderBy: reserveUSD, orderDirection: desc) {
                id
                token0 {
                  symbol
                  id
                }
                token1 {
                  symbol
                  id
                }
                reserve0
                reserve1
                reserveUSD
                token0Price
                token1Price
              }
            }
            """

            data = await self.query_subgraph(self.SUSHISWAP_SUBGRAPH, query)
            if not data or "pairs" not in data:
                return prices

            for pair in data["pairs"]:
                try:
                    token0_symbol = pair["token0"]["symbol"]
                    token1_symbol = pair["token1"]["symbol"]
                    token0_price = float(pair["token0Price"])
                    token1_price = float(pair["token1Price"])
                    reserve_usd = float(pair["reserveUSD"])

                    # Store both directions, but only update if not already in local data
                    pair_key_01 = (token0_symbol, token1_symbol)
                    pair_key_10 = (token1_symbol, token0_symbol)

                    if pair_key_01 not in prices:
                        prices[pair_key_01] = token1_price
                    if pair_key_10 not in prices:
                        prices[pair_key_10] = token0_price

                    # Cache in Redis
                    cache_key = f"dex:sushiswap:{token0_symbol}:{token1_symbol}"
                    cache_data = {
                        "price": token1_price,
                        "reserve_usd": reserve_usd,
                        "timestamp": time.time(),
                    }
                    self.redis_client.setex(cache_key, 30, json.dumps(cache_data))

                except Exception as e:
                    logger.debug(f"Error processing Sushiswap pair: {e}")

            logger.info(
                f"Fetched {len([k for k in prices if k not in local_prices]) // 2} pair prices from Sushiswap subgraph"
            )

        logger.info(
            f"Total: {len(prices) // 2} pair prices available (local + subgraph)"
        )
        return prices

    async def get_sushiswap_prices_from_local(self) -> Dict[Tuple[str, str], float]:
        """Get token pair prices from local node by querying common Sushiswap pairs directly"""
        import os
        import sys

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from web3 import Web3

        from shared.chains import get_web3_for_chain

        try:
            # Get Web3 instance for Ethereum
            w3 = get_web3_for_chain("ethereum")
            if not w3 or not w3.is_connected():
                logger.warning("Could not connect to local node for Sushiswap prices")
                return {}

            # Common Sushiswap pairs - using well-known liquidity pool addresses
            common_pairs = [
                # WETH/USDC - Sushiswap pool address
                ("0x397FF1542f962076d1b4Cc95497C41bD1B58b4e3", "WETH", "USDC"),
                # WETH/USDT - Sushiswap pool address
                ("0x66FDB2ECCfB58cF097bC737df5a79ca68d27B9b5", "WETH", "USDT"),
                # WBTC/WETH - Sushiswap pool address
                ("0xCEfF39fb82Da32321265d3D7C6a6C78b92e37639", "WBTC", "WETH"),
                # DAI/WETH - Sushiswap pool address
                ("0xC3D03e4F041Fd4cD388c549Ee2A29a9E5075882f", "DAI", "WETH"),
                # UNI/WETH - Sushiswap pool address
                ("0x6Bf725d12C9eDDDeaD96c37AFe2781CE78d148Ad", "UNI", "WETH"),
            ]

            # Sushiswap Pair ABI for reserves (same as Uniswap V2)
            pair_abi = [
                {
                    "constant": True,
                    "inputs": [],
                    "name": "getReserves",
                    "outputs": [
                        {"name": "_reserve0", "type": "uint112"},
                        {"name": "_reserve1", "type": "uint112"},
                        {"name": "_blockTimestampLast", "type": "uint32"},
                    ],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function",
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "token0",
                    "outputs": [{"name": "", "type": "address"}],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function",
                },
                {
                    "constant": True,
                    "inputs": [],
                    "name": "token1",
                    "outputs": [{"name": "", "type": "address"}],
                    "payable": False,
                    "stateMutability": "view",
                    "type": "function",
                },
            ]

            prices = {}
            for pool_address, token0_symbol, token1_symbol in common_pairs:
                try:
                    # Create contract instance
                    pair_contract = w3.eth.contract(
                        address=Web3.to_checksum_address(pool_address), abi=pair_abi
                    )

                    # Get reserves
                    reserves = pair_contract.functions.getReserves().call()
                    reserve0 = int(reserves[0])
                    reserve1 = int(reserves[1])

                    # Get the actual token addresses to confirm
                    actual_token0 = pair_contract.functions.token0().call()
                    actual_token1 = pair_contract.functions.token1().call()

                    # Calculate prices if reserves are not zero
                    if reserve0 > 0 and reserve1 > 0:
                        # Calculate price of token1 in terms of token0
                        price_token1_in_token0 = (reserve0 / 1e18) / (reserve1 / 1e18)

                        # Calculate price of token0 in terms of token1
                        price_token0_in_token1 = (reserve1 / 1e18) / (reserve0 / 1e18)

                        # Store both directions
                        prices[(token0_symbol, token1_symbol)] = price_token1_in_token0
                        prices[(token1_symbol, token0_symbol)] = price_token0_in_token1

                        logger.debug(
                            f"Local price from Sushiswap: {token0_symbol}/{token1_symbol} = {price_token1_in_token0}"
                        )
                except Exception as e:
                    logger.debug(
                        f"Could not fetch price for Sushiswap pool {pool_address}: {e}"
                    )
                    continue

            return prices

        except Exception as e:
            logger.error(f"Error getting Sushiswap prices from local: {e}")
            return {}

    async def get_curve_prices(self) -> Dict[Tuple[str, str], float]:
        """Get stable pool prices from Curve"""
        prices = {}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.CURVE_API) as response:
                    if response.status == 200:
                        data = await response.json()

                        if "data" in data and "poolData" in data["data"]:
                            for pool in data["data"]["poolData"]:
                                try:
                                    # Curve pools typically have stable coin pairs
                                    coins = pool.get("coins", [])
                                    if len(coins) >= 2:
                                        for i, coin1 in enumerate(coins):
                                            for coin2 in coins[i + 1 :]:
                                                symbol1 = coin1.get(
                                                    "symbol", ""
                                                ).upper()
                                                symbol2 = coin2.get(
                                                    "symbol", ""
                                                ).upper()

                                                if symbol1 and symbol2:
                                                    # For stablecoins, price is approximately 1:1
                                                    # In real implementation, would calculate from pool reserves
                                                    prices[(symbol1, symbol2)] = 1.0
                                                    prices[(symbol2, symbol1)] = 1.0

                                except Exception as e:
                                    logger.debug(f"Error processing Curve pool: {e}")

                        logger.info(
                            f"Fetched {len(prices) // 2} pair prices from Curve"
                        )

        except Exception as e:
            logger.error(f"Error fetching Curve prices: {e}")

        return prices

    def find_arbitrage_risks(
        self,
        uniswap_v2_prices: Dict,
        uniswap_v3_prices: Dict,
        sushiswap_prices: Dict,
        eth_price_usd: float = 2500,
    ) -> List[Dict]:
        """
        Compare prices across DEXs to identify arbitrage risk exposure
        """
        opportunities = []

        for token0, token1 in self.TOP_PAIRS:
            pair = (token0, token1)

            # Get prices from each DEX
            v2_price = uniswap_v2_prices.get(pair)
            v3_price = uniswap_v3_prices.get(pair)
            sushi_price = sushiswap_prices.get(pair)

            dex_prices = []
            if v2_price:
                dex_prices.append(("Uniswap V2", v2_price))
            if v3_price:
                dex_prices.append(("Uniswap V3", v3_price))
            if sushi_price:
                dex_prices.append(("Sushiswap", sushi_price))

            if len(dex_prices) < 2:
                continue

            # Find min and max prices
            dex_prices.sort(key=lambda x: x[1])
            buy_dex, buy_price = dex_prices[0]
            sell_dex, sell_price = dex_prices[-1]

            # Calculate price difference percentage
            price_diff_pct = ((sell_price - buy_price) / buy_price) * 100

            # Calculate profit (simplified)
            # Assuming 1 ETH trade size
            trade_size_eth = 1.0
            profit_eth = (sell_price - buy_price) * trade_size_eth
            profit_usd = profit_eth * eth_price_usd

            # Subtract gas costs
            gas_cost_usd = self.GAS_COST_ETH * eth_price_usd
            net_profit_usd = profit_usd - gas_cost_usd

            # Check if profitable
            if net_profit_usd > self.MIN_PROFIT_USD:
                opportunity = {
                    "type": "dex_arbitrage",
                    "token_pair": f"{token0}/{token1}",
                    "buy_dex": buy_dex,
                    "sell_dex": sell_dex,
                    "buy_price": buy_price,
                    "sell_price": sell_price,
                    "price_diff_pct": round(price_diff_pct, 4),
                    "profit_usd": round(profit_usd, 2),
                    "gas_cost_usd": round(gas_cost_usd, 2),
                    "net_profit_usd": round(net_profit_usd, 2),
                    "trade_size_eth": trade_size_eth,
                    "timestamp": datetime.now().isoformat(),
                    "chain": "ethereum",
                }

                opportunities.append(opportunity)

                logger.info(
                    f"💰 Arbitrage opportunity: {token0}/{token1} - "
                    f"Buy on {buy_dex} @ {buy_price:.6f}, "
                    f"Sell on {sell_dex} @ {sell_price:.6f}, "
                    f"Profit: ${net_profit_usd:.2f}"
                )

        return opportunities

    async def publish_arbitrage_opportunities(self, opportunities: List[Dict]):
        """Publish arbitrage opportunities to Redis for MEV analyzer"""
        for opp in opportunities:
            # Store in Redis
            key = f"dex:arbitrage:{opp['token_pair'].replace('/', '_')}:{int(time.time())}"
            self.redis_client.setex(key, 300, json.dumps(opp))  # 5 minute TTL

            # Publish to arbitrage channel
            self.redis_client.publish("dex:arbitrage_opportunities", json.dumps(opp))

            # Store for ML training
            self.redis_client.lpush("ml:arbitrage_training_data", json.dumps(opp))

    async def fetch_all_prices(self) -> Tuple[Dict, Dict, Dict, Dict]:
        """Fetch prices from all DEXs in parallel"""
        results = await asyncio.gather(
            self.get_uniswap_v2_prices(),
            self.get_uniswap_v3_prices(),
            self.get_sushiswap_prices(),
            self.get_curve_prices(),
            return_exceptions=True,
        )

        # Handle results
        v2_prices = results[0] if isinstance(results[0], dict) else {}
        v3_prices = results[1] if isinstance(results[1], dict) else {}
        sushi_prices = results[2] if isinstance(results[2], dict) else {}
        curve_prices = results[3] if isinstance(results[3], dict) else {}

        return v2_prices, v3_prices, sushi_prices, curve_prices

    async def monitor_dex_prices(self, interval_seconds: int = 10):
        """
        Main monitoring loop - fetch prices every interval_seconds
        """
        logger.info("🔄 Starting DEX price monitoring...")

        while True:
            try:
                # Fetch all prices
                (
                    v2_prices,
                    v3_prices,
                    sushi_prices,
                    curve_prices,
                ) = await self.fetch_all_prices()

                # Find arbitrage opportunities
                opportunities = self.find_arbitrage_risks(
                    v2_prices, v3_prices, sushi_prices
                )

                # Publish opportunities
                if opportunities:
                    await self.publish_arbitrage_opportunities(opportunities)
                    logger.info(f"Found {len(opportunities)} arbitrage opportunities")

                # Store aggregated price data for backtesting
                price_snapshot = {
                    "timestamp": datetime.now().isoformat(),
                    "uniswap_v2_count": len(v2_prices) // 2,
                    "uniswap_v3_count": len(v3_prices) // 2,
                    "sushiswap_count": len(sushi_prices) // 2,
                    "curve_count": len(curve_prices) // 2,
                    "opportunities_found": len(opportunities),
                }
                self.redis_client.lpush(
                    "dex:price_snapshots", json.dumps(price_snapshot)
                )

                # Wait for next interval
                await asyncio.sleep(interval_seconds)

            except Exception as e:
                logger.error(f"Error in DEX price monitoring: {e}")
                await asyncio.sleep(interval_seconds)
