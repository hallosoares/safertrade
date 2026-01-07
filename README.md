# SaferTrade

**Real-time DeFi threat detection and risk intelligence platform.**

SaferTrade provides detection engines for identifying honeypots, phishing addresses, pump-and-dump schemes, oracle manipulation, and other DeFi threats across multiple blockchain networks.

[![License: BUSL-1.1](https://img.shields.io/badge/License-BUSL--1.1-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776ab.svg)](https://python.org)
[![Redis](https://img.shields.io/badge/Redis-Streams-dc382d.svg)](https://redis.io)

---

## Overview

SaferTrade is a modular threat detection system designed for DeFi applications. It monitors on-chain activity in real-time and produces structured alerts via Redis Streams.

**Core capabilities:**
- Honeypot token detection (buy-only contracts)
- Phishing address identification
- Pump-and-dump pattern recognition
- Oracle price manipulation monitoring
- Stablecoin depeg tracking
- Token holder concentration analysis
- Liquidity risk assessment

## Architecture

```
Blockchain RPC ──> Detection Engines ──> Redis Streams ──> Consumers
                         │
                         └──> SQLite (persistence)
```

**Components:**
- **Engines**: Independent Python workers that analyze on-chain data
- **Transport**: Redis Streams for real-time message delivery
- **Storage**: SQLite with WAL journaling for historical persistence
- **Alerts**: Canonical envelope format with schema versioning

## Supported Networks

| Network | Chain ID | Status |
|---------|----------|--------|
| Ethereum | 1 | Supported |
| Base | 8453 | Supported |
| Polygon | 137 | Supported |
| Optimism | 10 | Supported |
| Arbitrum | 42161 | Supported |
| Blast | 81457 | Supported |
| Solana | — | Supported |

## Quick Start

### Prerequisites
- Python 3.11 or higher
- Redis 6.0 or higher
- Blockchain RPC access (Alchemy, Infura, or similar)

### Installation

```bash
git clone https://github.com/hallosoares/safertrade.git
cd safertrade

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Configure your RPC endpoints and Redis connection in .env
```

### Running an Engine

```bash
# Start Redis
redis-server &

# Run honeypot detection
python engines/honeypot_checker.py

# Run with health check only
python engines/honeypot_checker.py --health
```

## Detection Engines

| Engine | Purpose |
|--------|---------|
| `honeypot_checker.py` | Identifies tokens with restricted sell functionality |
| `pump_detector.py` | Detects coordinated price manipulation patterns |
| `oracle_manipulation_detector.py` | Monitors for price feed attacks |
| `stablecoin_depeg_monitor.py` | Tracks stablecoin peg deviations |
| `token_holder_analyzer.py` | Analyzes holder distribution and concentration |
| `gas_price_optimizer.py` | Optimizes transaction gas costs |
| `ohlcv_data_feed.py` | Provides market data feeds |
| `alert_processor.py` | Routes alerts to delivery channels |
| `health_check.py` | System health monitoring |

### Usage Example

```python
from engines.honeypot_checker import HoneypotChecker

checker = HoneypotChecker()
result = await checker.analyze_token(
    token_address="0x...",
    chain="ethereum"
)

if result["is_honeypot"]:
    print(f"Warning: Token flagged as honeypot")
    print(f"Risk score: {result['risk_score']}")
```

## Alert Format

All engines produce alerts following the canonical envelope schema:

```json
{
  "schema_v": "1.0",
  "type": "HONEYPOT_ALERT",
  "lane": "contract_safety",
  "timestamp": "2026-01-07T12:00:00Z",
  "data": {
    "token_address": "0x...",
    "chain": "ethereum",
    "risk_score": 0.85,
    "is_honeypot": true
  }
}
```

See `schemas/signals_v1.json` for the complete schema definition.

## Project Structure

```
safertrade/
├── engines/           # Detection engine modules
├── shared/            # Common utilities and configuration
│   ├── chains.py      # Chain definitions and RPC config
│   ├── redis_client.py
│   ├── database_config.py
│   └── ...
├── schemas/           # Signal and alert schemas
├── tests/             # Unit and integration tests
├── docs/              # Documentation
└── examples/          # Usage examples
```

## Configuration

Environment variables (see `.env.example`):

| Variable | Description |
|----------|-------------|
| `REDIS_HOST` | Redis server hostname |
| `REDIS_PORT` | Redis server port |
| `REDIS_PASSWORD` | Redis authentication password |
| `ALCHEMY_API_KEY` | Alchemy RPC API key |
| `ETHERSCAN_API_KEY` | Etherscan API key for contract verification |

## Roadmap

**Current Release (v1.0)**
- Core detection engines
- Multi-chain support
- Redis Streams integration
- Canonical alert schema

**In Development**
- REST API for programmatic access
- Web-based monitoring dashboard
- WebSocket real-time notifications
- Extended ML-based detection models

**Planned**
- Whale movement tracking
- MEV and sandwich attack detection
- Flash loan attack analysis
- Cross-chain correlation

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting pull requests.

**Development workflow:**
1. Fork the repository
2. Create a feature branch
3. Make changes following the code standards
4. Run tests: `python -m pytest tests/`
5. Submit a pull request

## License

This project is licensed under the Business Source License 1.1 (BUSL-1.1).

**Permitted uses:**
- Learning and education
- Development and testing
- Research and evaluation
- Internal proof-of-concept

**Commercial/production use** requires a separate commercial license. Contact the maintainers for licensing inquiries.

**Change Date:** December 10, 2029 (converts to GPLv2)

See [LICENSE](LICENSE), [COMMERCIAL_LICENSE.md](COMMERCIAL_LICENSE.md), and [LICENSE_FAQ.md](LICENSE_FAQ.md) for details.

## Documentation

- [Getting Started Guide](docs/GETTING_STARTED.md)
- [Commercial Licensing](COMMERCIAL_LICENSE.md)
- [Security Policy](SECURITY.md)
- [Changelog](CHANGELOG.md)

## Support

- [GitHub Issues](https://github.com/hallosoares/safertrade/issues) — Bug reports and feature requests
- [GitHub Discussions](https://github.com/hallosoares/safertrade/discussions) — Questions and community discussion

---

Copyright 2024-2026 SaferTrade Contributors. All rights reserved.
