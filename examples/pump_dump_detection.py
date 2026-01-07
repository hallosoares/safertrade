"""
Example: Pump and Dump Detection
Identify coordinated price manipulation schemes
"""

from engines.pump_detector.engine import PumpDetector
from shared.redis_client import get_redis_client


def monitor_pump_patterns(token_address: str, chain: str = "ethereum"):
    """
    Detect pump-and-dump patterns for a token.
    
    Signs of pump-and-dump:
    - Sudden volume spikes without news
    - Coordinated social media activity
    - Price increases > 50% in short timeframe
    - Whale accumulation before pump
    """
    redis = get_redis_client()
    detector = PumpDetector(redis)
    
    result = detector.analyze(token_address, chain=chain)
    
    print(f"Token: {token_address}")
    print(f"Chain: {chain}")
    print(f"Pump Detected: {result.is_pump}")
    print(f"Confidence: {result.confidence}%")
    print(f"Phase: {result.phase}")  # accumulation, pump, dump
    
    if result.indicators:
        print("Indicators:")
        for indicator in result.indicators:
            print(f"  - {indicator}")
    
    return result


if __name__ == "__main__":
    # Example token
    TOKEN = "0x..."
    monitor_pump_patterns(TOKEN, chain="base")
