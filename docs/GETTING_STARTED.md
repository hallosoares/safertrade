# SaferTrade — Getting Started Guide

Welcome to SaferTrade! This guide will help you get up and running quickly.

## Prerequisites

- **Python 3.11+** — [Download Python](https://www.python.org/downloads/)
- **Redis** — [Install Redis](https://redis.io/docs/install/)
- **RPC Access** — Get free keys from [Alchemy](https://alchemy.com) or [Infura](https://infura.io)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/hallosoares/safertrade.git
cd safertrade
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your API keys:
```env
ALCHEMY_API_KEY=your_alchemy_key
ETHERSCAN_API_KEY=your_etherscan_key
REDIS_PASSWORD=your_secure_password
```

### 5. Start Redis

```bash
# Linux/macOS
redis-server &

# Or with Docker
docker run -d -p 6379:6379 redis:7
```

### 6. Run Your First Engine

```bash
# Check system health
python engines/health_check.py --health

# Run honeypot checker
python engines/honeypot_checker.py --health
```

## Basic Usage

### Honeypot Detection

```python
import asyncio
from engines.honeypot_checker import HoneypotChecker

async def check_token():
    checker = HoneypotChecker()

    # Check a token on Ethereum
    result = await checker.analyze_token(
        token_address="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC
        chain="ethereum"
    )

    print(f"Is Honeypot: {result.get('is_honeypot')}")
    print(f"Risk Score: {result.get('risk_score')}")

asyncio.run(check_token())
```

### Pump Detection

```python
from engines.pump_detector import PumpDetector

detector = PumpDetector()
result = await detector.analyze_token("0x...", chain="ethereum")

print(f"Pump Detected: {result.get('is_pump')}")
print(f"Confidence: {result.get('confidence')}")
```

## Configuration

### Supported Chains

| Chain | Environment Variable | Default RPC |
|-------|---------------------|-------------|
| Ethereum | `ETHEREUM_RPC_URL` | Alchemy |
| Polygon | `POLYGON_RPC_URL` | Alchemy |
| Arbitrum | `ARBITRUM_RPC_URL` | Alchemy |
| Optimism | `OPTIMISM_RPC_URL` | Alchemy |
| Base | `BASE_RPC_URL` | Alchemy |

### Redis Configuration

```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_password
REDIS_URL=redis://:your_password@localhost:6379/0
```

## Troubleshooting

### Redis Connection Failed
```
Error: Redis connection failed
```
**Solution:** Ensure Redis is running: `redis-cli ping` should return `PONG`

### RPC Rate Limited
```
Error: 429 Too Many Requests
```
**Solution:** Add more RPC endpoints or upgrade your Alchemy/Infura plan

## Next Steps

1. Explore the [examples/](../examples/) directory
2. Join our [GitHub Discussions](https://github.com/hallosoares/safertrade/discussions)
3. Check out [open issues](https://github.com/hallosoares/safertrade/issues) to contribute

## Getting Help

- 💬 [GitHub Discussions](https://github.com/hallosoares/safertrade/discussions)
- 🐛 [Issue Tracker](https://github.com/hallosoares/safertrade/issues)
