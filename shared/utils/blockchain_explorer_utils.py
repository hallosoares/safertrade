#!/usr/bin/env python3
"""
blockchain_explorer_utils.py - SaferTrade Blockchain Explorer Link Generators

Utility functions for generating links to various blockchain explorers
and analytics platforms for transaction analysis and tracking.
"""


def generate_etherscan_link(hash_or_address: str, chain: str = "ethereum") -> str:
    """
    Generate Etherscan-compatible link for transaction hash or address on specified chain.

    Args:
        hash_or_address: Transaction hash or address
        chain: Blockchain network name

    Returns:
        URL string to the explorer page
    """
    chain = chain.lower()

    # Map chain names to their Etherscan-compatible URLs
    explorer_map = {
        "ethereum": "https://etherscan.io",
        "bsc": "https://bscscan.com",
        "polygon": "https://polygonscan.com",
        "avalanche": "https://snowtrace.io",
        "fantom": "https://ftmscan.com",
        "arbitrum": "https://arbiscan.io",
        "optimism": "https://optimistic.etherscan.io",
        "cronos": "https://cronoscan.com",
        "aurora": "https://aurorascan.dev",
        "base": "https://basescan.org",
        "blast": "https://blastscan.io",
        "gnosis": "https://gnosisscan.io",
        "celo": "https://celoscan.io",
        "linea": "https://lineascan.build",
        "scroll": "https://scrollscan.com",
        "mantle": "https://explorer.mantle.xyz",
        "moonbeam": "https://moonbeam.moonscan.io",
        "moonriver": "https://moonriver.moonscan.io",
        "cronos": "https://cronoscan.com",
        "canto": "https://canto.neobase.one",
        "kava": "https://kavascan.com",
        "klaytn": "https://scope.klaytn.com",
        "metis": "https://andromeda-explorer.metis.io",
        "polygon_zkevm": "https://zkevm.polygonscan.com",
        "zksync": "https://era.zksync.network",
    }

    base_url = explorer_map.get(chain, "https://etherscan.io")

    # Determine if it's a transaction hash or address based on length
    if len(hash_or_address) == 66:  # Transaction hash (0x + 64 hex chars)
        return f"{base_url}/tx/{hash_or_address}"
    elif len(hash_or_address) == 42:  # Address (0x + 40 hex chars)
        return f"{base_url}/address/{hash_or_address}"
    else:  # Assume it's an address if length is different
        return f"{base_url}/address/{hash_or_address}"


def generate_phalcon_link(hash: str, chain: str = "ethereum") -> str:
    """
    Generate Phalcon explorer link for transaction analysis.

    Args:
        hash: Transaction hash
        chain: Blockchain network name

    Returns:
        URL string to the Phalcon explorer page
    """
    chain = chain.lower()

    # Map chain names to Phalcon-compatible URLs
    phalcon_map = {
        "ethereum": "https://phalcon.blocksec.com/tx/eth",
        "bsc": "https://phalcon.blocksec.com/tx/bsc",
        "polygon": "https://phalcon.blocksec.com/tx/polygon",
        "arbitrum": "https://phalcon.blocksec.com/tx/arbitrum",
        "optimism": "https://phalcon.blocksec.com/tx/optimism",
        "base": "https://phalcon.blocksec.com/tx/base",
        "avalanche": "https://phalcon.blocksec.com/tx/avalanche",
        "fantom": "https://phalcon.blocksec.com/tx/fantom",
        "polygon_zkevm": "https://phalcon.blocksec.com/tx/polygon-zkevm",
        "zksync": "https://phalcon.blocksec.com/tx/zksync-era",
    }

    base_url = phalcon_map.get(chain, "https://phalcon.blocksec.com/tx/eth")

    return f"{base_url}/{hash}"


def generate_tenderly_link(hash: str, chain: str = "ethereum") -> str:
    """
    Generate Tenderly explorer link for transaction analysis.

    Args:
        hash: Transaction hash
        chain: Blockchain network name

    Returns:
        URL string to the Tenderly explorer page
    """
    chain = chain.lower()

    # Tenderly supports multiple networks, but with different path structures
    # Using the default network structure for now
    tenderly_network_map = {
        "ethereum": "mainnet",
        "bsc": "bsc",
        "polygon": "polygon",
        "avalanche": "avalanche",
        "fantom": "fantom",
        "arbitrum": "arbitrum",
        "optimism": "optimism",
        "base": "base",
        "gnosis": "gnosis",
        "polygon_zkevm": "polygon-zkevm",
        "zksync": "zksync",
        "linea": "linea",
        "scroll": "scroll",
    }

    network = tenderly_network_map.get(chain, "mainnet")

    # Tenderly has a specific format for transaction viewing
    return f"https://dashboard.tenderly.co/public/{network}/transaction/{hash}"


def generate_dedaub_link(hash: str, chain: str = "ethereum") -> str:
    """
    Generate Dedaub explorer link for transaction analysis.

    Args:
        hash: Transaction hash
        chain: Blockchain network name

    Returns:
        URL string to the Dedaub explorer page
    """
    chain = chain.lower()

    # Dedaub supports multiple networks
    dedaub_chain_map = {
        "ethereum": "mainnet",
        "bsc": "bsc",
        "polygon": "polygon",
        "arbitrum": "arbitrum",
        "optimism": "optimism",
        "base": "base",
        "avalanche": "avalanche",
        "fantom": "fantom",
        "gnosis": "gnosis",
        "polygon_zkevm": "polygon-zkevm",
        "zksync": "zksync-era",
        "linea": "linea",
        "scroll": "scroll",
    }

    chain_param = dedaub_chain_map.get(chain, "mainnet")

    return f"https://openchain.xyz/trace/{chain_param}/{hash}"


def generate_debank_link(address: str) -> str:
    """
    Generate DeBank link for an address to view portfolio and assets.

    Args:
        address: Wallet address

    Returns:
        URL string to the DeBank portfolio page
    """
    return f"https://debank.com/profile/{address}"


def generate_defillama_link(protocol: str) -> str:
    """
    Generate DefiLlama link for a DeFi protocol.

    Args:
        protocol: DeFi protocol name (lowercase, spaces replaced with hyphens)

    Returns:
        URL string to the DefiLlama protocol page
    """
    # Clean and format protocol name for URL
    protocol_clean = protocol.lower().replace(" ", "-").replace("_", "-")

    return f"https://defillama.com/protocol/{protocol_clean}"


# Example usage
if __name__ == "__main__":
    # Example usage of the functions
    print(
        "Etherscan:",
        generate_etherscan_link(
            "0x1234567890123456789012345678901234567890abcdef1234567890abcdef12345",
            "ethereum",
        ),
    )
    print(
        "Phalcon:",
        generate_phalcon_link(
            "0x1234567890123456789012345678901234567890abcdef1234567890abcdef12345",
            "ethereum",
        ),
    )
    print(
        "Tenderly:",
        generate_tenderly_link(
            "0x1234567890123456789012345678901234567890abcdef1234567890abcdef12345",
            "ethereum",
        ),
    )
    print(
        "Dedaub:",
        generate_dedaub_link(
            "0x1234567890123456789012345678901234567890abcdef1234567890abcdef12345",
            "ethereum",
        ),
    )
    print("DeBank:", generate_debank_link("0x1234567890123456789012345678901234567890"))
    print("DefiLlama:", generate_defillama_link("uniswap"))
