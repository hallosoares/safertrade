"""
usd_calculator.py - USD Value Calculator for SaferTrade

Calculates token prices in USD using various APIs with caching and backup systems.
"""

import logging
import os
from typing import Dict, Optional

import requests
from cachetools import TTLCache

logger = logging.getLogger(__name__)


class USDCalculator:
    """
    Calculate token prices in USD using CoinGecko API with CoinMarketCap as backup.
    Includes caching to avoid rate limit issues.
    """

    def __init__(self):
        # Initialize cache with 5-minute TTL (300 seconds) and max size of 1000
        self.price_cache = TTLCache(maxsize=1000, ttl=300)

        # Get API keys from environment
        self.coingecko_api_key = os.getenv("COINGECKO_API_KEY")
        self.cmc_api_key = os.getenv("CMC_API_KEY")

        # Base URLs
        self.coingecko_url = "https://api.coingecko.com/api/v3/simple/price"
        self.cmc_url = (
            "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest"
        )

    def get_token_price_usd(self, token: str, amount: float) -> float:
        """
        Get the USD value of a specific amount of a token.

        Args:
            token: Token symbol or ID (e.g., 'ETH', 'BTC', 'UNI')
            amount: Amount of the token

        Returns:
            USD value of the token amount
        """
        try:
            # Create cache key
            cache_key = f"{token.lower()}_{amount}"

            # Check cache first
            if cache_key in self.price_cache:
                return self.price_cache[cache_key]

            # Get price from primary source (CoinGecko)
            price_usd = self._get_price_coingecko(token)

            # If CoinGecko fails, try CoinMarketCap as backup
            if price_usd is None or price_usd <= 0:
                price_usd = self._get_price_coinmarketcap(token)

            # If both sources fail, return 0
            if price_usd is None or price_usd <= 0:
                logger.warning(f"Could not fetch price for token {token}")
                return 0.0

            # Calculate USD value
            usd_value = amount * price_usd

            # Cache the result
            self.price_cache[cache_key] = usd_value

            return usd_value

        except Exception as e:
            logger.error(f"Error calculating USD value for {amount} {token}: {e}")
            return 0.0

    def _get_price_coingecko(self, token: str) -> Optional[float]:
        """
        Get token price from CoinGecko API.

        Args:
            token: Token symbol or ID

        Returns:
            Price in USD or None if failed
        """
        try:
            # Map common token names to CoinGecko IDs
            token_mapping = {
                "ETH": "ethereum",
                "BTC": "bitcoin",
                "BNB": "binancecoin",
                "MATIC": "matic-network",
                "AVAX": "avalanche-2",
                "FTM": "fantom",
                "ONE": "harmony",
                "ARB": "arbitrum",
                "OP": "optimism",
                "BASE": "base",
                "SOL": "solana",
                "LINK": "chainlink",
                "UNI": "uniswap",
                "AAVE": "aave",
                "COMP": "compound-governance-token",
                "YFI": "yearn-finance",
                "SNX": "synthetix-network-token",
                "CRV": "curve-dao-token",
                "SUSHI": "sushi",
                "BAL": "balancer",
                "MKR": "maker",
                "DAI": "dai",
                "USDC": "usd-coin",
                "USDT": "tether",
                "WBTC": "wrapped-bitcoin",
                "WETH": "weth",
            }

            coingecko_id = token_mapping.get(token.upper(), token.lower())

            params = {"ids": coingecko_id, "vs_currencies": "usd"}

            # Add API key if available
            headers = {}
            if self.coingecko_api_key:
                headers["x-cg-pro-api-key"] = self.coingecko_api_key

            response = requests.get(
                self.coingecko_url, params=params, headers=headers, timeout=10
            )
            response.raise_for_status()

            data = response.json()

            # Extract price from response
            if coingecko_id in data and "usd" in data[coingecko_id]:
                return float(data[coingecko_id]["usd"])

            return None

        except Exception as e:
            logger.warning(f"CoinGecko API failed for {token}: {e}")
            return None

    def _get_price_coinmarketcap(self, token: str) -> Optional[float]:
        """
        Get token price from CoinMarketCap API as backup.

        Args:
            token: Token symbol

        Returns:
            Price in USD or None if failed
        """
        if not self.cmc_api_key:
            logger.debug("CoinMarketCap API key not configured")
            return None

        try:
            headers = {
                "X-CMC_PRO_API_KEY": self.cmc_api_key,
                "Accept": "application/json",
            }

            params = {"symbol": token.upper()}

            response = requests.get(
                self.cmc_url, headers=headers, params=params, timeout=10
            )
            response.raise_for_status()

            data = response.json()

            # Extract price from response
            if "data" in data:
                for token_id, token_data in data["data"].items():
                    if isinstance(token_data, list):
                        for item in token_data:
                            if "quote" in item and "USD" in item["quote"]:
                                return float(item["quote"]["USD"]["price"])
                    elif (
                        isinstance(token_data, dict)
                        and "quote" in token_data
                        and "USD" in token_data["quote"]
                    ):
                        return float(token_data["quote"]["USD"]["price"])

            return None

        except Exception as e:
            logger.warning(f"CoinMarketCap API failed for {token}: {e}")
            return None

    def get_multiple_token_prices(self, tokens: Dict[str, float]) -> Dict[str, float]:
        """
        Get USD values for multiple tokens at once.

        Args:
            tokens: Dictionary mapping token symbols to amounts
                    e.g., {'ETH': 2.5, 'BTC': 0.1, 'UNI': 100}

        Returns:
            Dictionary mapping token symbols to their USD values
        """
        results = {}

        for token, amount in tokens.items():
            usd_value = self.get_token_price_usd(token, amount)
            results[token] = usd_value

        return results

    def get_token_price_only(self, token: str) -> Optional[float]:
        """
        Get just the price of a token without amount calculation.

        Args:
            token: Token symbol or ID

        Returns:
            Price in USD per token or None if failed
        """
        try:
            # Check if we already have a cached price for this token with a small amount
            cache_key = f"{token.lower()}_1"
            if cache_key in self.price_cache:
                return self.price_cache[cache_key]  # This is the price for 1 token

            # Get price by calculating 1 token
            price = self._get_price_coingecko(token)

            if price is None or price <= 0:
                price = self._get_price_coinmarketcap(token)

            if price is not None and price > 0:
                # Cache this as the price for 1 token
                self.price_cache[cache_key] = price

            return price

        except Exception as e:
            logger.error(f"Error getting price for {token}: {e}")
            return None


# Global instance
usd_calculator = USDCalculator()


def get_token_price_usd(token: str, amount: float) -> float:
    """
    Convenience function to get USD value of a token amount.

    Args:
        token: Token symbol or ID
        amount: Amount of the token

    Returns:
        USD value of the token amount
    """
    return usd_calculator.get_token_price_usd(token, amount)


def get_token_price_only(token: str) -> Optional[float]:
    """
    Convenience function to get just the price of a token.

    Args:
        token: Token symbol or ID

    Returns:
        Price in USD per token or None if failed
    """
    return usd_calculator.get_token_price_only(token)


def get_multiple_token_prices(tokens: Dict[str, float]) -> Dict[str, float]:
    """
    Convenience function to get USD values for multiple tokens.

    Args:
        tokens: Dictionary mapping token symbols to amounts

    Returns:
        Dictionary mapping token symbols to their USD values
    """
    return usd_calculator.get_multiple_token_prices(tokens)
