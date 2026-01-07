"""
Example: Webhook Integration
Forward alerts to external endpoints (Discord, Slack, etc.)
"""

import json
import requests
from shared.redis_client import get_redis_client


class WebhookForwarder:
    """Forward SaferTrade alerts to webhooks."""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.redis = get_redis_client()
    
    def format_alert(self, alert_type: str, data: dict) -> dict:
        """Format alert for webhook delivery."""
        return {
            "content": f"**{alert_type}**",
            "embeds": [{
                "title": f"SaferTrade Alert: {alert_type}",
                "color": 0xFF0000 if data.get("risk_score", 0) > 70 else 0xFFFF00,
                "fields": [
                    {"name": "Chain", "value": data.get("chain", "N/A"), "inline": True},
                    {"name": "Risk Score", "value": str(data.get("risk_score", "N/A")), "inline": True},
                    {"name": "Address", "value": data.get("address", "N/A")[:42], "inline": False},
                ]
            }]
        }
    
    def send(self, alert_type: str, data: dict):
        """Send alert to webhook."""
        payload = self.format_alert(alert_type, data)
        response = requests.post(self.webhook_url, json=payload, timeout=10)
        return response.status_code == 200
    
    def run(self, stream: str = "safertrade:results"):
        """Subscribe and forward alerts."""
        last_id = "$"
        print(f"Forwarding alerts from {stream} to webhook...")
        
        while True:
            messages = self.redis.xread({stream: last_id}, block=5000, count=10)
            
            if not messages:
                continue
            
            for stream_name, entries in messages:
                for entry_id, data in entries:
                    last_id = entry_id
                    alert = json.loads(data.get("data", "{}"))
                    alert_type = data.get("type", "UNKNOWN")
                    
                    if self.send(alert_type, alert):
                        print(f"Forwarded: {alert_type}")
                    else:
                        print(f"Failed to forward: {alert_type}")


if __name__ == "__main__":
    # Replace with your webhook URL
    WEBHOOK_URL = "https://discord.com/api/webhooks/..."
    
    forwarder = WebhookForwarder(WEBHOOK_URL)
    forwarder.run()
