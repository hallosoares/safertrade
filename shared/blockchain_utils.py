"""
SaferTrade Multi-Chain Blockchain Utilities
Provides comprehensive blockchain utility functions and helpers for all supported chains
"""

import asyncio
import json
import os
import time
from typing import Any, Dict, List, Optional

import aiohttp
import requests
from web3 import Web3
from web3.types import BlockData, TxReceipt

from .chains import get_chain_config, get_chain_manager, get_web3_for_chain


def get_chain_web3(chain_name: str) -> Optional[Web3]:
    """
    Get Web3 instance configured for specified chain
    """
    return get_web3_for_chain(chain_name)


def get_chain_config_by_name(chain_name: str):
    """
    Get chain configuration for specified chain
    """
    return get_chain_config(chain_name)


def get_all_supported_chains() -> List[str]:
    """
    Get list of all supported chain names
    """
    manager = get_chain_manager()
    return manager.get_supported_chains()


def is_transaction_valid(tx_hash: str, chain_name: str, web3: Web3 = None) -> bool:
    """
    Verify if a transaction exists on specified chain
    """
    if web3 is None:
        web3 = get_chain_web3(chain_name)

    if not web3:
        return False

    try:
        # Normalize transaction hash if needed
        if not tx_hash.startswith("0x"):
            tx_hash = "0x" + tx_hash

        tx = web3.eth.get_transaction(tx_hash)
        return tx is not None
    except Exception:
        return False


def get_transaction_receipt(
    tx_hash: str, chain_name: str, web3: Web3 = None
) -> Optional[TxReceipt]:
    """
    Get transaction receipt from specified chain
    """
    if web3 is None:
        web3 = get_chain_web3(chain_name)

    if not web3:
        return None

    try:
        # Normalize transaction hash if needed
        if not tx_hash.startswith("0x"):
            tx_hash = "0x" + tx_hash

        receipt = web3.eth.get_transaction_receipt(tx_hash)
        return receipt
    except Exception:
        return None


def get_native_token_price(chain_name: str) -> float:
    """
    Get native token price for specified chain
    """
    try:
        chain_config = get_chain_config(chain_name)
        if not chain_config:
            return 0.0

        # Map chain names to CoinGecko IDs
        chain_to_cg_id = {
            "ethereum": "ethereum",
            "base": "ethereum",  # Base uses ETH
            "polygon": "matic-network",
            "optimism": "ethereum",  # Optimism uses ETH
            "arbitrum": "ethereum",  # Arbitrum uses ETH
            "blast": "ethereum",  # Blast uses ETH
        }

        cg_id = chain_to_cg_id.get(chain_name, "ethereum")

        coingecko_key = os.getenv("COINGECKO_API_KEY", "demo")
        headers = {}
        if coingecko_key and coingecko_key != "demo":
            headers["x-cg-pro-api-key"] = coingecko_key

        response = requests.get(
            f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd",
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()
        price = float(data[cg_id]["usd"])
        return price
    except Exception:
        # Fallback prices
        fallback_prices = {
            "ethereum": 3500.0,
            "base": 3500.0,
            "polygon": 0.8,
            "optimism": 3500.0,
            "arbitrum": 3500.0,
            "blast": 3500.0,
        }
        return fallback_prices.get(chain_name, 3500.0)


def get_gas_price(chain_name: str, web3: Web3 = None) -> int:
    """
    Get current gas price on specified chain
    """
    if web3 is None:
        web3 = get_chain_web3(chain_name)

    if not web3:
        return 1000000000  # 1 gwei fallback

    try:
        gas_price = web3.eth.gas_price
        return gas_price
    except Exception:
        return 1000000000  # 1 gwei fallback


def get_block_number(chain_name: str, web3: Web3 = None) -> int:
    """
    Get latest block number on specified chain
    """
    if web3 is None:
        web3 = get_chain_web3(chain_name)

    if not web3:
        return 0

    try:
        block_number = web3.eth.block_number
        return block_number
    except Exception:
        return 0


def get_token_balance(
    wallet_address: str,
    token_address: str = None,
    chain_name: str = "ethereum",
    web3: Web3 = None,
) -> int:
    """
    Get token balance for a wallet on specified chain
    If token_address is None, returns native token balance
    """
    if web3 is None:
        web3 = get_chain_web3(chain_name)

    if not web3:
        return 0

    try:
        wallet_address = web3.to_checksum_address(wallet_address)

        if token_address:
            # It's a token, not native token
            token_address = web3.to_checksum_address(token_address)

            # ABI for balanceOf function
            erc20_abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function",
                }
            ]

            token_contract = web3.eth.contract(address=token_address, abi=erc20_abi)
            balance = token_contract.functions.balanceOf(wallet_address).call()
            return balance
        else:
            # It's native token balance
            balance = web3.eth.get_balance(wallet_address)
            return balance
    except Exception:
        return 0


def get_transaction_details(
    tx_hash: str, chain_name: str, web3: Web3 = None
) -> Optional[Dict[str, Any]]:
    """
    Get comprehensive transaction details from specified chain
    """
    if web3 is None:
        web3 = get_chain_web3(chain_name)

    if not web3:
        return None

    try:
        # Normalize transaction hash if needed
        if not tx_hash.startswith("0x"):
            tx_hash = "0x" + tx_hash

        tx = web3.eth.get_transaction(tx_hash)
        receipt = get_transaction_receipt(tx_hash, chain_name, web3)

        if not tx:
            return None

        details = {
            "tx_hash": tx_hash,
            "from": tx["from"],
            "to": tx.get("to"),
            "value": int(tx["value"]),
            "gas": tx["gas"],
            "gas_price": tx.get("gasPrice", 0),
            "nonce": tx["nonce"],
            "block_number": tx.get("blockNumber", 0),
            "input": tx.get("input", "0x"),
            "status": receipt["status"] if receipt else None,
            "gas_used": receipt["gasUsed"] if receipt else None,
            "cumulative_gas_used": receipt["cumulativeGasUsed"] if receipt else None,
            "effective_gas_price": receipt.get("effectiveGasPrice", 0)
            if receipt
            else 0,
            "timestamp": None,  # Would require block timestamp lookup
        }

        # Add block timestamp if possible
        if details["block_number"]:
            try:
                block = web3.eth.get_block(details["block_number"])
                details["timestamp"] = block.timestamp
            except:
                details["timestamp"] = int(time.time())

        return details
    except Exception as e:
        print(f"Error getting {chain_name} transaction details: {e}")
        return None


def get_internal_transactions_from_local_node(
    tx_hash: str, chain_name: str = "ethereum", web3: Web3 = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Get internal transactions for a transaction from local Erigon node using trace_call.
    This is a more efficient alternative to Etherscan API for internal transactions.
    """
    if web3 is None:
        web3 = get_chain_web3(chain_name)

    if not web3:
        return None

    try:
        # Normalize transaction hash if needed
        if not tx_hash.startswith("0x"):
            tx_hash = "0x" + tx_hash

        # Get the transaction to get its block number
        tx = web3.eth.get_transaction(tx_hash)
        if not tx:
            return []

        block_number = tx["blockNumber"]

        # Try to use trace_transaction if available (Erigon supports this)
        try:
            internal_txs = web3.provider.make_request("trace_transaction", [tx_hash])

            if "result" in internal_txs:
                traces = internal_txs["result"]
                # Convert traces to internal transaction format
                internal_transactions = []
                for trace in traces:
                    internal_tx = {
                        "type": trace.get("type", "call"),
                        "from": trace.get("from", ""),
                        "to": trace.get("to", ""),
                        "value": int(trace.get("value", 0)),
                        "gas": trace.get("gas", 0),
                        "gas_used": trace.get("gasUsed", 0),
                        "input": trace.get("input", "0x"),
                        "output": trace.get("output", "0x"),
                        "block_number": block_number,
                        "transaction_hash": tx_hash,
                    }
                    internal_transactions.append(internal_tx)

                return internal_transactions
            else:
                # If trace_transaction not supported, return empty list
                return []
        except Exception as e:
            # If trace functionality not available, return empty list
            print(f"Trace functionality not available for internal transactions: {e}")
            return []

    except Exception as e:
        print(f"Error getting {chain_name} internal transactions: {e}")
        return []


def get_token_transfers_from_local_node(
    tx_hash: str, chain_name: str = "ethereum", web3: Web3 = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Get token transfers for a transaction by analyzing logs on local node.
    This is a local alternative to Etherscan token transfer API.
    """
    if web3 is None:
        web3 = get_chain_web3(chain_name)

    if not web3:
        return None

    try:
        # Normalize transaction hash if needed
        if not tx_hash.startswith("0x"):
            tx_hash = "0x" + tx_hash

        # Get the transaction receipt to access logs
        receipt = web3.eth.get_transaction_receipt(tx_hash)
        if not receipt:
            return []

        token_transfers = []

        # ERC-20 Transfer event signature: keccak('Transfer(address,address,uint256)')
        transfer_signature = (
            "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
        )

        # Process logs for Transfer events
        for log in receipt.logs:
            if len(log.topics) > 0 and log.topics[0].hex() == transfer_signature:
                # Decode Transfer event: Transfer(address indexed from, address indexed to, uint256 value)
                if len(log.topics) >= 3:
                    # Extract addresses from topics (topics[1] and topics[2] are indexed)
                    from_address = "0x" + log.topics[1].hex()[-40:]
                    to_address = "0x" + log.topics[2].hex()[-40:]

                    # The value is in the data part
                    value_hex = log.data
                    if value_hex.startswith("0x"):
                        value_hex = value_hex[2:]

                    try:
                        value = int(value_hex or "0", 16) if value_hex else 0
                    except ValueError:
                        value = 0

                    # Get token address (the contract that emitted the event)
                    token_address = log.address

                    transfer = {
                        "token_address": token_address,
                        "from_address": from_address.lower(),
                        "to_address": to_address.lower(),
                        "value": str(value),
                        "block_number": receipt.blockNumber,
                        "transaction_hash": tx_hash,
                        "log_index": log.logIndex,
                    }
                    token_transfers.append(transfer)

        return token_transfers

    except Exception as e:
        print(f"Error getting {chain_name} token transfers: {e}")
        return []


def get_contract_abi_from_local_node(
    contract_address: str, chain_name: str = "ethereum", web3: Web3 = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Retrieve contract ABI by attempting to decode bytecode from local node.
    Note: This only works if the contract source code is available or bytecode is standard.
    For verified contracts, Etherscan API may still be needed, but this provides a fallback.
    """
    if web3 is None:
        web3 = get_chain_web3(chain_name)

    if not web3:
        return None

    try:
        # Normalize contract address
        if not contract_address.startswith("0x"):
            contract_address = "0x" + contract_address
        contract_address = web3.to_checksum_address(contract_address)

        # Get the contract bytecode
        bytecode = web3.eth.get_code(contract_address)

        # For most practical purposes, we'll need to rely on verification or use other methods
        # But we can at least verify that the contract exists
        if len(bytecode) <= 2:  # Empty bytecode means no contract
            return None

        # Try to identify common contract types based on bytecode patterns
        # This is a simplified approach - in production you'd want more sophisticated detection
        if "ERC20" in str(bytecode[:50]) or "erc20" in str(bytecode[:50]).lower():
            # Basic ERC20 ABI skeleton - in practice you'd need the actual verified ABI
            basic_erc20_abi = [
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function",
                },
                {
                    "constant": False,
                    "inputs": [
                        {"name": "_to", "type": "address"},
                        {"name": "_value", "type": "uint256"},
                    ],
                    "name": "transfer",
                    "outputs": [{"name": "success", "type": "bool"}],
                    "type": "function",
                },
            ]
            return basic_erc20_abi
        else:
            # Return a generic ABI for common operations
            return [
                {"type": "fallback", "stateMutability": "payable"},
                {"type": "receive", "stateMutability": "payable"},
            ]

    except Exception as e:
        print(f"Error getting contract ABI from local node {chain_name}: {e}")
        return None


def is_contract_address(address: str, chain_name: str, web3: Web3 = None) -> bool:
    """
    Check if address is a contract on specified chain
    """
    if web3 is None:
        web3 = get_chain_web3(chain_name)

    if not web3:
        return False

    try:
        address = web3.to_checksum_address(address)
        code = web3.eth.get_code(address)
        return len(code) > 0
    except Exception:
        return False


def get_token_info(
    token_address: str, chain_name: str, web3: Web3 = None
) -> Optional[Dict[str, str]]:
    """
    Get token information for a token on specified chain
    """
    if web3 is None:
        web3 = get_chain_web3(chain_name)

    if not web3:
        return None

    try:
        token_address = web3.to_checksum_address(token_address)

        # ABI for common token functions
        token_abi = [
            {
                "constant": True,
                "inputs": [],
                "name": "name",
                "outputs": [{"name": "", "type": "string"}],
                "type": "function",
            },
            {
                "constant": True,
                "inputs": [],
                "name": "symbol",
                "outputs": [{"name": "", "type": "string"}],
                "type": "function",
            },
            {
                "constant": True,
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function",
            },
        ]

        token_contract = web3.eth.contract(address=token_address, abi=token_abi)

        info = {
            "name": None,
            "symbol": None,
            "decimals": 18,  # Default to 18 decimals
        }

        try:
            info["name"] = token_contract.functions.name().call()
        except:
            info["name"] = "Unknown Token"

        try:
            info["symbol"] = token_contract.functions.symbol().call()
        except:
            info["symbol"] = "UNKNOWN"

        try:
            info["decimals"] = token_contract.functions.decimals().call()
        except:
            info["decimals"] = 18

        return info
    except Exception as e:
        print(f"Error getting {chain_name} token info: {e}")
        return None


def get_block_timestamp(block_number: int, chain_name: str, web3: Web3 = None) -> int:
    """
    Get timestamp for a specific block on specified chain
    """
    if web3 is None:
        web3 = get_chain_web3(chain_name)

    if not web3:
        return int(time.time())

    try:
        block = web3.eth.get_block(block_number)
        return block.timestamp
    except Exception:
        return int(time.time())


def is_valid_address(
    address: str, chain_name: str = "ethereum", web3: Web3 = None
) -> bool:
    """
    Validate if an address is a valid chain address
    """
    if web3 is None:
        web3 = get_chain_web3(chain_name)

    if not web3:
        # Use Web3 library validation without network connection
        try:
            Web3.to_checksum_address(address)
            return True
        except:
            return False

    try:
        checksum_address = web3.to_checksum_address(address)
        return True
    except:
        return False


def get_chain_id(chain_name: str) -> int:
    """
    Get chain ID for specified chain
    """
    config = get_chain_config(chain_name)
    return config.chain_id if config else 0


def get_multiple_balances(
    wallet_address: str, token_addresses: List[str], chain_name: str, web3: Web3 = None
) -> Dict[str, int]:
    """
    Get balances for multiple tokens for a wallet on specified chain
    """
    balances = {}

    if web3 is None:
        web3 = get_chain_web3(chain_name)

    if not web3:
        return balances

    try:
        wallet_address = web3.to_checksum_address(wallet_address)

        # Get native token balance
        balances["native"] = web3.eth.get_balance(wallet_address)

        # Get token balances
        for token_address in token_addresses:
            try:
                token_addr = web3.to_checksum_address(token_address)

                # ABI for balanceOf function
                erc20_abi = [
                    {
                        "constant": True,
                        "inputs": [{"name": "_owner", "type": "address"}],
                        "name": "balanceOf",
                        "outputs": [{"name": "balance", "type": "uint256"}],
                        "type": "function",
                    }
                ]

                token_contract = web3.eth.contract(address=token_addr, abi=erc20_abi)
                balance = token_contract.functions.balanceOf(wallet_address).call()
                balances[token_address] = balance
            except Exception as e:
                balances[token_address] = 0
                print(f"Error getting balance for {token_address}: {e}")

    except Exception as e:
        print(f"Error getting balances for {wallet_address}: {e}")

    return balances


def estimate_transaction_cost(
    gas_limit: int, chain_name: str, web3: Web3 = None
) -> Dict[str, Any]:
    """
    Estimate transaction cost in native token and USD for specified chain
    """
    if web3 is None:
        web3 = get_chain_web3(chain_name)

    if not web3:
        return {"gas_price_gwei": 0, "cost_native_token": 0, "cost_usd": 0}

    try:
        gas_price = web3.eth.gas_price
        gas_price_gwei = gas_price / 1e9
        cost_native_token = (gas_price * gas_limit) / 1e18

        # Get native token price in USD
        native_price_usd = get_native_token_price(chain_name)
        cost_usd = cost_native_token * native_price_usd

        return {
            "gas_price_gwei": gas_price_gwei,
            "cost_native_token": cost_native_token,
            "cost_usd": cost_usd,
        }
    except Exception as e:
        print(f"Error estimating transaction cost: {e}")
        return {"gas_price_gwei": 0, "cost_native_token": 0, "cost_usd": 0}


def get_latest_blocks(
    chain_name: str, count: int = 10, web3: Web3 = None
) -> List[BlockData]:
    """
    Get latest blocks information from specified chain
    """
    if web3 is None:
        web3 = get_chain_web3(chain_name)

    if not web3:
        return []

    try:
        latest_block = web3.eth.block_number
        blocks = []

        for i in range(count):
            block_number = latest_block - i
            if block_number >= 0:
                block = web3.eth.get_block(block_number)
                blocks.append(block)

        return blocks
    except Exception as e:
        print(f"Error getting latest blocks: {e}")
        return []


# Chain-specific convenience functions
def get_base_web3() -> Optional[Web3]:
    """
    Get Web3 instance configured for Base chain
    """
    return get_chain_web3("base")


def get_base_config():
    """
    Get chain configuration for Base
    """
    return get_chain_config("base")


def get_ethereum_web3() -> Optional[Web3]:
    """
    Get Web3 instance configured for Ethereum chain
    """
    return get_chain_web3("ethereum")


def get_ethereum_config():
    """
    Get chain configuration for Ethereum
    """
    return get_chain_config("ethereum")


def get_polygon_web3() -> Optional[Web3]:
    """
    Get Web3 instance configured for Polygon chain
    """
    return get_chain_web3("polygon")


def get_polygon_config():
    """
    Get chain configuration for Polygon
    """
    return get_chain_config("polygon")


def get_arbitrum_web3() -> Optional[Web3]:
    """
    Get Web3 instance configured for Arbitrum chain
    """
    return get_chain_web3("arbitrum")


def get_arbitrum_config():
    """
    Get chain configuration for Arbitrum
    """
    return get_chain_config("arbitrum")


def get_optimism_web3() -> Optional[Web3]:
    """
    Get Web3 instance configured for Optimism chain
    """
    return get_chain_web3("optimism")


def get_optimism_config():
    """
    Get chain configuration for Optimism
    """
    return get_chain_config("optimism")


def get_blast_web3() -> Optional[Web3]:
    """
    Get Web3 instance configured for Blast chain
    """
    return get_chain_web3("blast")


def get_blast_config():
    """
    Get chain configuration for Blast
    """
    return get_chain_config("blast")


class EtherscanAPI:
    """
    Etherscan API integration with rate limiting for transaction analysis,
    internal transactions, token transfers, and contract ABI fetching
    """

    def __init__(self):
        # Chain-specific API endpoints
        self.etherscan_endpoints = {
            "ethereum": "https://api.etherscan.io/api",
            "polygon": "https://api.polygonscan.com/api",
            "arbitrum": "https://api.arbiscan.io/api",
            "optimism": "https://api-optimistic.etherscan.io/api",
            "bsc": "https://api.bscscan.com/api",
            "avalanche": "https://api.snowtrace.io/api",
            "base": "https://api.basescan.org/api",
        }

        # API keys from environment
        self.api_keys = {
            "ethereum": os.getenv("ETHERSCAN_API_KEY"),
            "polygon": os.getenv(
                "SNOWSCAN_API_KEY"
            ),  # Note: using SNOWSCAN as it's in .env
            "arbitrum": os.getenv("ARBISCAN_API_KEY"),
            "optimism": os.getenv("OPTIMISM_API_KEY"),
            "bsc": os.getenv("BSCSCAN_API_KEY"),
            "avalanche": os.getenv("SNOWSCAN_API_KEY"),  # Using SNOWSCAN for Avalanche
            "base": os.getenv(
                "BASESCAN_API_KEY"
            ),  # Note: BASESCAN_API_KEY not in .env but we'll try
        }

        # Fallback to ETHERSCAN_API_KEY if chain-specific key not found
        for chain, key in self.api_keys.items():
            if not key:
                self.api_keys[chain] = os.getenv(
                    "ETHERSCAN_API_KEY"
                )  # fallback to main key

        # Rate limiting: 5 calls per second (100ms interval)
        self.rate_limit_interval = 0.2  # 200ms for safety
        self.last_call_time = 0

        # Async HTTP session
        self._session = None

    async def get_session(self):
        """Get a shared HTTP session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def _rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        if time_since_last_call < self.rate_limit_interval:
            await asyncio.sleep(self.rate_limit_interval - time_since_last_call)
        self.last_call_time = time.time()

    def get_api_params(
        self, chain: str, module: str, action: str, **kwargs
    ) -> Dict[str, str]:
        """Build API parameters for Etherscan request"""
        chain = chain.lower()
        api_key = self.api_keys.get(chain)

        if not api_key:
            raise ValueError(f"No API key found for chain: {chain}")

        params = {
            "module": module,
            "action": action,
            "apikey": api_key,
        }
        params.update(kwargs)
        return params

    def get_chain_endpoint(self, chain: str) -> str:
        """Get the correct API endpoint for a chain"""
        chain = chain.lower()
        if chain not in self.etherscan_endpoints:
            raise ValueError(f"Unsupported chain: {chain}")
        return self.etherscan_endpoints[chain]

    async def get_transaction_details(
        self, tx_hash: str, chain: str = "ethereum"
    ) -> Optional[Dict[str, Any]]:
        """Fetch detailed transaction information from Etherscan API"""
        await self._rate_limit()

        try:
            params = self.get_api_params(
                chain, "proxy", "eth_getTransactionByHash", txhash=tx_hash
            )
            endpoint = self.get_chain_endpoint(chain)

            session = await self.get_session()
            async with session.get(endpoint, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "1":
                        return data.get("result")
                    else:
                        # Some endpoints return result directly without status wrapper
                        return data.get("result")
                else:
                    print(f"Etherscan API error: {response.status}")
                    return None
        except Exception as e:
            print(f"Error fetching transaction details: {e}")
            return None

    async def get_transaction_receipt(
        self, tx_hash: str, chain: str = "ethereum"
    ) -> Optional[Dict[str, Any]]:
        """Fetch transaction receipt from Etherscan API"""
        await self._rate_limit()

        try:
            params = self.get_api_params(
                chain, "proxy", "eth_getTransactionReceipt", txhash=tx_hash
            )
            endpoint = self.get_chain_endpoint(chain)

            session = await self.get_session()
            async with session.get(endpoint, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "1":
                        return data.get("result")
                    else:
                        return data.get("result")
                else:
                    print(f"Etherscan API error: {response.status}")
                    return None
        except Exception as e:
            print(f"Error fetching transaction receipt: {e}")
            return None

    async def get_internal_transactions(
        self, tx_hash: str, chain: str = "ethereum"
    ) -> Optional[List[Dict[str, Any]]]:
        """Get internal transactions for a transaction (trace)"""
        # First try to get from local node
        local_result = get_internal_transactions_from_local_node(tx_hash, chain)
        if local_result is not None and len(local_result) > 0:
            return local_result

        # If local node doesn't provide results, fall back to Etherscan API
        await self._rate_limit()

        try:
            params = self.get_api_params(
                chain, "trace", "gettxlistinternal", txhash=tx_hash
            )
            endpoint = self.get_chain_endpoint(chain)

            session = await self.get_session()
            async with session.get(endpoint, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "1":
                        return data.get("result")
                    else:
                        # Handle cases where there are no internal transactions
                        return []
                else:
                    print(f"Etherscan API error: {response.status}")
                    return []
        except Exception as e:
            print(f"Error fetching internal transactions: {e}")
            return []

    async def get_token_transfers(
        self, tx_hash: str, chain: str = "ethereum"
    ) -> Optional[List[Dict[str, Any]]]:
        """Get token transfers associated with a transaction"""
        # First try to get from local node using logs analysis
        local_result = get_token_transfers_from_local_node(tx_hash, chain)
        if local_result is not None and len(local_result) > 0:
            return local_result

        # If local node doesn't provide results, fall back to Etherscan API
        await self._rate_limit()

        # First, get the transaction to identify the block number and addresses
        tx_details = await self.get_transaction_details(tx_hash, chain)
        if not tx_details:
            return []

        # Get ERC20 token transfers for the specific transaction hash
        try:
            params = self.get_api_params(
                chain,
                "tokentx",  # Use 'tokentx' directly as the module
                "txlist",
                txhash=tx_hash,
            )
            endpoint = self.get_chain_endpoint(chain)

            session = await self.get_session()
            async with session.get(endpoint, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "1":
                        transfers = data.get("result", [])
                        # Ensure we return a list of transfers
                        if isinstance(transfers, list):
                            return transfers
                        else:
                            return []
                    else:
                        return []
                else:
                    print(f"Etherscan API error: {response.status}")
                    return []
        except Exception as e:
            print(f"Error fetching token transfers: {e}")
            return []

    async def get_contract_abi(
        self, contract_address: str, chain: str = "ethereum"
    ) -> Optional[List[Dict[str, Any]]]:
        """Fetch contract ABI from local node first, then Etherscan API as fallback"""
        # First try to get ABI from local node
        local_result = get_contract_abi_from_local_node(contract_address, chain)
        if local_result is not None:
            return local_result

        # If local node doesn't provide results, fall back to Etherscan API
        await self._rate_limit()

        try:
            params = self.get_api_params(
                chain, "contract", "getabi", address=contract_address
            )
            endpoint = self.get_chain_endpoint(chain)

            session = await self.get_session()
            async with session.get(endpoint, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "1":
                        abi_str = data.get("result", "[]")
                        try:
                            return json.loads(abi_str)
                        except json.JSONDecodeError:
                            print(f"Error parsing ABI JSON: {abi_str}")
                            return None
                    else:
                        # Handle case where contract is not verified
                        print(
                            f"Etherscan API error: {data.get('message', 'Contract source code not verified')}"
                        )
                        # Return basic ABI from local node instead of failing
                        return get_contract_abi_from_local_node(contract_address, chain)
                else:
                    print(f"Etherscan API error: {response.status}")
                    # Return basic ABI from local node instead of failing
                    return get_contract_abi_from_local_node(contract_address, chain)
        except Exception as e:
            print(f"Error fetching contract ABI: {e}")
            # Return basic ABI from local node instead of failing
            return get_contract_abi_from_local_node(contract_address, chain)

    async def get_multiple_transaction_details(
        self, tx_hashes: List[str], chain: str = "ethereum"
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """Fetch details for multiple transactions efficiently"""
        results = {}
        for tx_hash in tx_hashes:
            details = await self.get_transaction_details(tx_hash, chain)
            results[tx_hash] = details
            # Add small delay between requests to respect rate limits
            await asyncio.sleep(0.1)
        return results

    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()


# Global Etherscan API instance
_etherscan_api = None


def get_etherscan_api() -> EtherscanAPI:
    """Get or create the global Etherscan API instance"""
    global _etherscan_api
    if _etherscan_api is None:
        _etherscan_api = EtherscanAPI()
    return _etherscan_api


# Convenience functions for direct use
async def fetch_transaction_details(
    tx_hash: str, chain: str = "ethereum"
) -> Optional[Dict[str, Any]]:
    """Convenience function to fetch transaction details"""
    api = get_etherscan_api()
    return await api.get_transaction_details(tx_hash, chain)


async def fetch_internal_transactions(
    tx_hash: str, chain: str = "ethereum"
) -> Optional[List[Dict[str, Any]]]:
    """Convenience function to fetch internal transactions"""
    api = get_etherscan_api()
    return await api.get_internal_transactions(tx_hash, chain)


async def fetch_token_transfers(
    tx_hash: str, chain: str = "ethereum"
) -> Optional[List[Dict[str, Any]]]:
    """Convenience function to fetch token transfers"""
    api = get_etherscan_api()
    return await api.get_token_transfers(tx_hash, chain)


async def fetch_contract_abi(
    contract_address: str, chain: str = "ethereum"
) -> Optional[List[Dict[str, Any]]]:
    """Convenience function to fetch contract ABI"""
    api = get_etherscan_api()
    return await api.get_contract_abi(contract_address, chain)
