"""
Example: Multi-Chain Monitoring
Monitor threats across multiple blockchain networks
"""

from shared.chains import SUPPORTED_CHAINS
from shared.redis_client import get_redis_client
from engines.health_check import HealthCheck


def get_chain_status():
    """Get status of all supported chains."""
    redis = get_redis_client()
    
    print("SaferTrade Multi-Chain Status")
    print("=" * 50)
    
    for chain_name, chain_config in SUPPORTED_CHAINS.items():
        chain_id = chain_config.get("chain_id", "N/A")
        rpc_configured = chain_config.get("rpc_url") is not None
        
        status = "Active" if rpc_configured else "Not Configured"
        symbol = chain_config.get("native_token", "ETH")
        
        print(f"{chain_name:12} | Chain ID: {str(chain_id):6} | {symbol:5} | {status}")
    
    print("=" * 50)


def monitor_all_chains():
    """Run health checks across all configured chains."""
    redis = get_redis_client()
    health = HealthCheck(redis)
    
    results = health.check_all_chains()
    
    print("\nChain Health Report")
    print("-" * 50)
    
    for chain, status in results.items():
        emoji = "OK" if status["healthy"] else "FAIL"
        latency = status.get("latency_ms", "N/A")
        block = status.get("latest_block", "N/A")
        
        print(f"[{emoji}] {chain}: Block {block}, Latency {latency}ms")


if __name__ == "__main__":
    get_chain_status()
    monitor_all_chains()
