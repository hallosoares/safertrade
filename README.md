# SaferTrade

**Real-time DeFi threat detection and risk intelligence platform.**

SaferTrade provides detection engines for identifying honeypots, phishing addresses, pump-and-dump schemes, oracle manipulation, and other DeFi threats across multiple blockchain networks.

[![License: BUSL-1.1](https://img.shields.io/badge/License-BUSL--1.1-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776ab.svg)](https://python.org)
[![Redis](https://img.shields.io/badge/Redis-Streams-dc382d.svg)](https://redis.io)
[![Tests](https://github.com/hallosoares/safertrade/actions/workflows/tests.yml/badge.svg)](https://github.com/hallosoares/safertrade/actions/workflows/tests.yml)
[![Engines](https://img.shields.io/badge/Engines-10+-green.svg)](#detection-engines)
[![Maintained](https://img.shields.io/badge/Maintained-yes-brightgreen.svg)](https://github.com/hallosoares/safertrade/commits/main)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

---

## Overview

SaferTrade is a comprehensive DeFi threat detection platform that monitors blockchain activity in real-time. Built with a modular engine architecture, it can identify various types of malicious activity and market manipulation across Ethereum, Base, Polygon, Optimism, Arbitrum, Blast, and Solana networks.

### Key Features

- **Modular Detection Engines**: Each threat type has a dedicated engine
- **Multi-Chain Support**: 7 blockchain networks supported
- **Real-Time Processing**: Redis Streams for low-latency event processing
- **Extensible Architecture**: Add custom engines with minimal boilerplate

---

## Detection Engines

| Engine | Description |
|--------|-------------|
| `honeypot_checker` | Detects honeypot token contracts that prevent selling |
| `pump_detector` | Identifies pump-and-dump scheme patterns |
| `oracle_manipulation_detector` | Monitors for oracle price manipulation |
| `stablecoin_depeg_monitor` | Tracks stablecoin peg deviations |
| `token_holder_analyzer` | Analyzes token holder concentration |
| `gas_price_optimizer` | Monitors gas price anomalies |
| `health_check` | System health monitoring |
| `ohlcv_data_feed` | OHLCV data aggregation |
| `alert_processor` | Alert routing and delivery |
| `phishing_detector` | Identifies known phishing addresses |

---

## Installation

### Prerequisites

- Python 3.11 or higher
- Redis 7.0 or higher
- RPC access to target blockchain networks

### Setup

```bash
# Clone the repository
git clone https://github.com/hallosoares/safertrade.git
cd safertrade

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your RPC endpoints and API keys
```

---

## Quick Start

```python
from engines.honeypot_checker.engine import HoneypotChecker
from shared.redis_client import get_redis_client

# Initialize
redis = get_redis_client()
checker = HoneypotChecker(redis)

# Check a token
result = checker.check_token("0x...")
print(f"Is honeypot: {result.is_honeypot}")
```

See [examples/](examples/) for more usage patterns.

---

## Configuration

Configuration is managed through environment variables. Key settings:

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `RPC_ETHEREUM` | Ethereum RPC endpoint | Required |
| `RPC_BASE` | Base RPC endpoint | Required |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for full configuration reference.

---

## Architecture

```
safertrade/
├── engines/           # Detection engines (modular, independent)
├── shared/            # Common utilities and clients
├── schemas/           # Data models and validation
├── data/              # Static data (phishing lists, etc.)
├── docs/              # Documentation
└── tests/             # Test suite
```

Each engine is self-contained with its own configuration, processing logic, and output format. Engines communicate via Redis Streams.

---

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting pull requests.

### Development Setup

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run linter
ruff check .
```

---

## Security

For security vulnerabilities, please see [SECURITY.md](SECURITY.md). Do not open public issues for security concerns.

---

## License

This project is licensed under the Business Source License 1.1. See [LICENSE](LICENSE) for details.

**TL;DR**: Free for non-production use. Production/commercial use requires a commercial license until the Change Date (December 10, 2029), after which it converts to Apache 2.0.

---

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/hallosoares/safertrade/issues)
- **Security**: security@safertrade.io

---

Built for the DeFi community.
