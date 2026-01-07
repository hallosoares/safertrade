# SaferTrade Quick Start Guide

Get up and running with SaferTrade in 5 minutes.

## Prerequisites

- Python 3.11 or higher
- Redis 7.0 or higher
- At least one RPC endpoint

## Step 1: Clone and Setup

```bash
# Clone the repository
git clone https://github.com/hallosoares/safertrade.git
cd safertrade

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env  # or use your preferred editor
```

**Minimum required configuration:**

```
REDIS_URL=redis://localhost:6379
RPC_ETHEREUM=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY
```

## Step 3: Start Redis

```bash
# If using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or if Redis is installed locally
redis-server
```

## Step 4: Run Your First Check

```python
# test_safertrade.py
from engines.honeypot_checker.engine import HoneypotChecker
from shared.redis_client import get_redis_client

redis = get_redis_client()
checker = HoneypotChecker(redis)

# Check a known token (USDC on Ethereum)
result = checker.check_token("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")
print(f"Is Honeypot: {result.is_honeypot}")
print(f"Risk Score: {result.risk_score}")
```

```bash
python test_safertrade.py
```

## Step 5: Start an Engine

```bash
# Run the honeypot checker engine
python -m engines.honeypot_checker.engine
```

The engine will start monitoring and publishing results to Redis.

## Step 6: Subscribe to Alerts

In another terminal:

```python
# subscribe.py
import json
from shared.redis_client import get_redis_client

redis = get_redis_client()
last_id = "$"

print("Waiting for alerts...")
while True:
    messages = redis.xread({"safertrade:results": last_id}, block=5000)
    if messages:
        for stream, entries in messages:
            for entry_id, data in entries:
                print(f"Alert: {data}")
                last_id = entry_id
```

## Next Steps

- Read [examples/](../examples/) for more usage patterns
- Configure additional chains in `.env`
- Set up Telegram/Discord alerts
- Explore the full API documentation

## Troubleshooting

### Redis Connection Error
```
Ensure Redis is running: redis-cli ping
Should return: PONG
```

### RPC Timeout
```
Your RPC endpoint may be rate-limited.
Consider using a paid provider like Alchemy or Infura.
```

### Missing Dependencies
```bash
pip install -r requirements.txt --upgrade
```

## Getting Help

- [GitHub Issues](https://github.com/hallosoares/safertrade/issues)
- [Documentation](../docs/)
