"""
SaferTrade Multi-Chain Configuration and Utilities
Provides chain-specific configuration and helper functions
"""

import os
from dataclasses import dataclass
from typing import Dict, Optional

from web3 import Web3


@dataclass
class ChainConfig:
    """Configuration for a specific blockchain"""

    name: str
    chain_id: int
    rpc_url: str
    explorer_url: str
    native_token: str
    currency_symbol: str
    explorer_api_url: str
    api_key_env: str


class MultiChainManager:
    """Manages configuration for multiple blockchain networks"""

    def __init__(self):
        self.chains: Dict[str, ChainConfig] = {
            "ethereum": ChainConfig(
                name="Ethereum",
                chain_id=int(os.getenv("ETHEREUM_CHAIN_ID", "1")),
                rpc_url=os.getenv("ETHEREUM_RPC_URL", ""),
                explorer_url="https://etherscan.io",
                native_token="ETH",
                currency_symbol="ETH",
                explorer_api_url="https://api.etherscan.io/api",
                api_key_env="ETHERSCAN_API_KEY",
            ),
            "base": ChainConfig(
                name="Base",
                chain_id=int(os.getenv("BASE_CHAIN_ID", "8453")),
                rpc_url=os.getenv("BASE_RPC_URL", ""),
                explorer_url="https://basescan.org",
                native_token="ETH",
                currency_symbol="ETH",  # Base uses ETH as native
                explorer_api_url="https://api.basescan.org/api",
                api_key_env="BASESCAN_API_KEY",  # May need different key
            ),
            "polygon": ChainConfig(
                name="Polygon",
                chain_id=int(os.getenv("POLYGON_CHAIN_ID", "137")),
                rpc_url=os.getenv("POLYGON_RPC_URL", ""),
                explorer_url="https://polygonscan.com",
                native_token="MATIC",
                currency_symbol="MATIC",
                explorer_api_url="https://api.polygonscan.com/api",
                api_key_env="POLYGONSCAN_API_KEY",
            ),
            "optimism": ChainConfig(
                name="Optimism",
                chain_id=int(os.getenv("OPTIMISM_CHAIN_ID", "10")),
                rpc_url=os.getenv("OPTIMISM_RPC_URL", ""),
                explorer_url="https://optimistic.etherscan.io",
                native_token="ETH",
                currency_symbol="ETH",
                explorer_api_url="https://api-optimistic.etherscan.io/api",
                api_key_env="OPTIMISM_API_KEY",
            ),
            "arbitrum": ChainConfig(
                name="Arbitrum",
                chain_id=int(os.getenv("ARBITRUM_CHAIN_ID", "42161")),
                rpc_url=os.getenv("ARBITRUM_RPC_URL", ""),
                explorer_url="https://arbiscan.io",
                native_token="ETH",
                currency_symbol="ETH",
                explorer_api_url="https://api.arbiscan.io/api",
                api_key_env="ARBISCAN_API_KEY",
            ),
            "blast": ChainConfig(
                name="Blast",
                chain_id=int(os.getenv("BLAST_CHAIN_ID", "81457")),
                rpc_url=os.getenv("BLAST_RPC_URL", ""),
                explorer_url="https://blastscan.io",
                native_token="ETH",
                currency_symbol="ETH",
                explorer_api_url="https://api.blastscan.io/api",  # May not exist yet
                api_key_env="BLASTSCAN_API_KEY",  # May not exist yet
            ),
            "solana": ChainConfig(
                name="Solana",
                chain_id=0,  # Solana doesn't use chain IDs like EVM chains
                rpc_url=os.getenv(
                    "SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com"
                ),
                explorer_url="https://solscan.io",
                native_token="SOL",
                currency_symbol="SOL",
                explorer_api_url="https://api.solscan.io",
                api_key_env="SOLSCAN_API_KEY",
            ),
        }

    def get_chain_config(self, chain_name: str) -> Optional[ChainConfig]:
        """Get configuration for a specific chain"""
        return self.chains.get(chain_name.lower())

    def get_web3_instance(self, chain_name: str) -> Optional[Web3]:
        """Get Web3 instance for a specific chain"""
        config = self.get_chain_config(chain_name)
        if not config:
            return None

        rpc_url = config.rpc_url

        # Local Erigon preference logic (Ethereum only for now)
        if (
            chain_name.lower() == "ethereum"
            and os.getenv("LOCAL_ERIGON_ENABLE", "1") == "1"
        ):
            local_http = os.getenv("LOCAL_ERIGON_HTTP", "").strip()
            max_lag = int(os.getenv("LOCAL_ERIGON_MAX_LAG_BLOCKS", "5000") or 5000)
            if local_http:
                try:
                    w3_local = Web3(
                        Web3.HTTPProvider(local_http, request_kwargs={"timeout": 2})
                    )
                    if w3_local.is_connected():
                        latest_local = int(w3_local.eth.block_number)
                        ref_height = None
                        if rpc_url and rpc_url != local_http:
                            try:
                                w3_ref = Web3(
                                    Web3.HTTPProvider(
                                        rpc_url, request_kwargs={"timeout": 2}
                                    )
                                )
                                if w3_ref.is_connected():
                                    ref_height = int(w3_ref.eth.block_number)
                            except Exception:
                                ref_height = None
                        # Accept local if reference unavailable OR lag within threshold
                        if ref_height is None or (ref_height - latest_local) <= max_lag:
                            return w3_local
                except Exception:
                    pass  # Fall back to configured RPC below

        if rpc_url:
            try:
                return Web3(Web3.HTTPProvider(rpc_url))
            except Exception:
                return None
        return None

    def is_valid_chain(self, chain_name: str) -> bool:
        """Check if a chain name is supported"""
        return chain_name.lower() in self.chains

    def get_supported_chains(self) -> list:
        """Get list of supported chain names"""
        return list(self.chains.keys())

    def get_chain_by_id(self, chain_id: int) -> Optional[str]:
        """Get chain name by chain ID"""
        for name, config in self.chains.items():
            if config.chain_id == chain_id:
                return name
        return None

    def get_all_configs(self) -> Dict[str, ChainConfig]:
        """Get all chain configurations"""
        return self.chains.copy()


# Lazy-loaded global instance
_chain_manager = None


def get_chain_manager() -> MultiChainManager:
    """Get or create the global chain manager instance"""
    global _chain_manager
    if _chain_manager is None:
        _chain_manager = MultiChainManager()
    return _chain_manager


def validate_chain_param(chain: str) -> str:
    """Validate and normalize chain parameter"""
    if not chain:
        return "ethereum"  # Default

    normalized_chain = chain.lower()
    manager = get_chain_manager()
    if not manager.is_valid_chain(normalized_chain):
        raise ValueError(
            f"Unsupported chain: {chain}. Supported: {manager.get_supported_chains()}"
        )

    return normalized_chain


def get_web3_for_chain(chain: str) -> Optional[Web3]:
    """Get Web3 instance for the specified chain"""
    return get_chain_manager().get_web3_instance(chain)


def get_chain_config(chain: str) -> Optional[ChainConfig]:
    """Get configuration for the specified chain"""
    return get_chain_manager().get_chain_config(chain)
