"""
Example: Real-Time Alert Subscription
Subscribe to threat alerts via Redis Streams
"""

import json
from shared.redis_client import get_redis_client


def subscribe_to_alerts(stream: str = "safertrade:results"):
    """
    Subscribe to real-time threat alerts.
    
    The canonical stream 'safertrade:results' receives all alerts
    from all detection engines.
    """
    redis = get_redis_client()
    last_id = "$"  # Start from new messages
    
    print(f"Subscribing to {stream}...")
    print("Waiting for alerts (Ctrl+C to exit)\n")
    
    while True:
        # Block for new messages (timeout 5 seconds)
        messages = redis.xread({stream: last_id}, block=5000, count=10)
        
        if not messages:
            continue
        
        for stream_name, entries in messages:
            for entry_id, data in entries:
                last_id = entry_id
                
                # Parse alert
                alert = json.loads(data.get("data", "{}"))
                alert_type = data.get("type", "UNKNOWN")
                
                print(f"[{alert_type}] {entry_id}")
                print(f"  Chain: {alert.get('chain', 'N/A')}")
                print(f"  Risk: {alert.get('risk_score', 'N/A')}")
                print(f"  Data: {json.dumps(alert, indent=2)[:200]}...")
                print()


if __name__ == "__main__":
    subscribe_to_alerts()
