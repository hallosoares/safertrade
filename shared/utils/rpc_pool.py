#!/usr/bin/env python3
"""
RPC Pool Utilities
==================

Centralized RPC endpoint management for SaferTrade.
"""

import os

from web3 import Web3


def _local_erigon_healthy(max_lag: int) -> bool:
    local_http = os.getenv("LOCAL_ERIGON_HTTP", "").strip()
    if not local_http or os.getenv("LOCAL_ERIGON_ENABLE", "1") != "1":
        return False
    try:
        w3_local = Web3(Web3.HTTPProvider(local_http, request_kwargs={"timeout": 2}))
        if not w3_local.is_connected():
            return False
        local_block = int(w3_local.eth.block_number)
        # Try reference RPC for lag assessment
        ref_url = os.getenv("ETHEREUM_RPC_URL", "").strip()
        ref_block = None
        if ref_url and ref_url != local_http:
            try:
                w3_ref = Web3(Web3.HTTPProvider(ref_url, request_kwargs={"timeout": 2}))
                if w3_ref.is_connected():
                    ref_block = int(w3_ref.eth.block_number)
            except Exception:
                ref_block = None
        return ref_block is None or (ref_block - local_block) <= max_lag
    except Exception:
        return False


def get_preferred_ethereum_rpcs() -> list:
    """Return ordered list of Ethereum RPC endpoints (local first if healthy)."""
    max_lag = int(os.getenv("LOCAL_ERIGON_MAX_LAG_BLOCKS", "5000") or 5000)
    endpoints = []
    if _local_erigon_healthy(max_lag):
        endpoints.append(os.getenv("LOCAL_ERIGON_HTTP"))
    # Primary configured
    primary = os.getenv("ETHEREUM_RPC_URL", "").strip()
    if primary and primary not in endpoints:
        endpoints.append(primary)
    # Infura fallback
    infura = os.getenv("INFURA_HTTPS", "").strip()
    if infura and infura not in endpoints:
        endpoints.append(infura)
    # Public node last-resort
    public_node = "https://ethereum.publicnode.com"
    if public_node not in endpoints:
        endpoints.append(public_node)
    return endpoints


def get_chain_rpc(chain: str) -> str:
    """Get RPC endpoint for chain using our configured API keys.

    Args:
        chain: Chain name (ethereum, arbitrum, etc.)

    Returns:
        RPC endpoint URL for the specified chain
    """
    rpc_map = {
        "ethereum": os.getenv(
            "ETHEREUM_RPC_URL",
            "https://eth-mainnet.g.alchemy.com/v2/DhrxxBK01fd1j16wT94NceFJAvJvrQUi",
        ),
        "arbitrum": os.getenv(
            "ARBITRUM_RPC_URL",
            "https://arb-mainnet.g.alchemy.com/v2/DhrxxBK01fd1j16wT94NceFJAvJvrQUi",
        ),
        "base": os.getenv(
            "BASE_RPC_URL",
            "https://base-mainnet.g.alchemy.com/v2/DhrxxBK01fd1j16wT94NceFJAvJvrQUi",
        ),
        "polygon": os.getenv(
            "POLYGON_RPC_URL",
            "https://polygon-mainnet.g.alchemy.com/v2/DhrxxBK01fd1j16wT94NceFJAvJvrQUi",
        ),
        "optimism": os.getenv(
            "OPTIMISM_RPC_URL",
            "https://opt-mainnet.g.alchemy.com/v2/DhrxxBK01fd1j16wT94NceFJAvJvrQUi",
        ),
    }
    return rpc_map.get(chain.lower(), rpc_map["ethereum"])
