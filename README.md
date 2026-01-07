<p align="center">
  <img src="assets/images/logo.png" alt="SaferTrade Logo" width="400">
</p>

<p align="center">
  <strong>Real-time DeFi threat detection and risk intelligence platform</strong>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-BUSL--1.1-blue.svg" alt="License"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.11+-3776ab.svg" alt="Python"></a>
  <a href="https://redis.io"><img src="https://img.shields.io/badge/Redis-Streams-dc382d.svg" alt="Redis"></a>
  <a href="https://github.com/hallosoares/safertrade/actions/workflows/tests.yml"><img src="https://github.com/hallosoares/safertrade/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <a href="#detection-engines"><img src="https://img.shields.io/badge/Engines-10+-green.svg" alt="Engines"></a>
  <a href="https://github.com/hallosoares/safertrade/commits/main"><img src="https://img.shields.io/badge/Maintained-yes-brightgreen.svg" alt="Maintained"></a>
  <a href="CONTRIBUTING.md"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome"></a>
</p>

---

## What is SaferTrade?

SaferTrade is the **only open-source, production-ready** DeFi threat detection platform. While other projects document threats, we detect them in real-time across 7 blockchain networks with 10+ specialized engines.

**Key differentiators:**
- Working detection code (not just documentation)
- Real-time monitoring via Redis Streams
- Multi-chain support out of the box
- Modular engine architecture for extensibility

---

## Architecture

```
                                    SAFERTRADE ARCHITECTURE
    
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                              DATA SOURCES                                    │
    │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
    │  │ Ethereum │ │   Base   │ │ Polygon  │ │ Arbitrum │ │  Solana  │  + more   │
    │  │   RPC    │ │   RPC    │ │   RPC    │ │   RPC    │ │   RPC    │           │
    │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘           │
    │       │            │            │            │            │                  │
    └───────┼────────────┼────────────┼────────────┼────────────┼──────────────────┘
            │            │            │            │            │
            └────────────┴────────────┼────────────┴────────────┘
                                      │
                                      ▼
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                           DETECTION ENGINES                                  │
    │                                                                              │
    │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
    │  │    Honeypot     │  │  Pump & Dump    │  │     Oracle      │              │
    │  │    Checker      │  │   Detector      │  │  Manipulation   │              │
    │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘              │
    │           │                    │                    │                        │
    │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
    │  │   Stablecoin    │  │     Token       │  │    Phishing     │              │
    │  │  Depeg Monitor  │  │ Holder Analyzer │  │    Detector     │              │
    │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘              │
    │           │                    │                    │                        │
    └───────────┼────────────────────┼────────────────────┼────────────────────────┘
                │                    │                    │
                └────────────────────┼────────────────────┘
                                     │
                                     ▼
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                            REDIS STREAMS                                     │
    │                                                                              │
    │    safertrade:results    signals.honeypot    signals.pump    signals.oracle  │
    │          │                                                                   │
    └──────────┼───────────────────────────────────────────────────────────────────┘
               │
               ▼
    ┌─────────────────────────────────────────────────────────────────────────────┐
    │                              OUTPUTS                                         │
    │                                                                              │
    │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
    │  │   REST API   │  │  WebSocket   │  │   Telegram   │  │   Webhooks   │     │
    │  │   /api/v1    │  │    Alerts    │  │    Alerts    │  │   Callbacks  │     │
    │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘     │
    │                                                                              │
    └─────────────────────────────────────────────────────────────────────────────┘
```

---

## Detection Engines

| Engine | Threat Type | Description |
|--------|-------------|-------------|
| `honeypot_checker` | Contract Risk | Detects honeypot contracts that prevent token selling |
| `pump_detector` | Market Manipulation | Identifies coordinated pump-and-dump schemes |
| `oracle_manipulation_detector` | Price Attack | Monitors for oracle price manipulation attempts |
| `stablecoin_depeg_monitor` | Peg Risk | Tracks stablecoin deviations from peg |
| `token_holder_analyzer` | Concentration Risk | Analyzes whale concentration and distribution |
| `phishing_detector` | Fraud | Identifies known phishing addresses and patterns |
| `gas_price_optimizer` | Cost | Monitors gas price anomalies and optimization |
| `health_check` | System | Platform health monitoring |
| `ohlcv_data_feed` | Data | Market data aggregation and validation |
| `alert_processor` | Delivery | Alert routing and multi-channel delivery |

---

## Quick Start

### Prerequisites
- Python 3.11+
- Redis 7.0+
- RPC endpoints for target chains

### Installation

```bash
# Clone repository
git clone https://github.com/hallosoares/safertrade.git
cd safertrade

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your RPC endpoints
```

### Basic Usage

```python
from engines.honeypot_checker.engine import HoneypotChecker
from shared.redis_client import get_redis_client

# Initialize
redis = get_redis_client()
checker = HoneypotChecker(redis)

# Check a token for honeypot characteristics
result = checker.check_token("0x...")

if result.is_honeypot:
    print(f"WARNING: Honeypot detected!")
    print(f"Risk score: {result.risk_score}")
    print(f"Reason: {result.reason}")
else:
    print("Token appears safe")
```

### Run Detection Engine

```bash
# Start the honeypot checker engine
python -m engines.honeypot_checker.engine

# Output will stream to Redis: safertrade:results
```

See [examples/](examples/) for more usage patterns.

---

## Multi-Chain Support

SaferTrade monitors threats across multiple networks:

| Network | Chain ID | Status |
|---------|----------|--------|
| Ethereum | 1 | Supported |
| Base | 8453 | Supported |
| Polygon | 137 | Supported |
| Optimism | 10 | Supported |
| Arbitrum | 42161 | Supported |
| Blast | 81457 | Supported |
| Solana | - | Supported |

---

## Configuration

Key environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `REDIS_URL` | Redis connection string | Yes |
| `RPC_ETHEREUM` | Ethereum RPC endpoint | Yes |
| `RPC_BASE` | Base RPC endpoint | Yes |
| `RPC_POLYGON` | Polygon RPC endpoint | Optional |
| `LOG_LEVEL` | Logging verbosity (DEBUG, INFO, WARNING) | No |

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for full reference.

---

## Project Structure

```
safertrade/
├── engines/           # Detection engines (modular, independent)
│   ├── honeypot_checker/
│   ├── pump_detector/
│   ├── oracle_manipulation_detector/
│   └── ...
├── shared/            # Common utilities and clients
│   ├── redis_client.py
│   ├── chains.py
│   └── ...
├── schemas/           # Data models and validation
├── data/              # Static data (phishing lists, etc.)
├── docs/              # Documentation
├── examples/          # Usage examples
└── tests/             # Test suite
```

---

## API Reference

When running the API server, documentation is available at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Example Endpoints

```bash
# Check token safety
GET /api/v1/token/{address}/safety

# Get whale movements
GET /api/v1/whale/movements?chain=ethereum&limit=100

# Subscribe to alerts (WebSocket)
WS /api/v1/ws/alerts
```

---

## Contributing

We welcome contributions. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting pull requests.

### Development Setup

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run linter
ruff check .

# Type checking
mypy engines/ shared/
```

### Good First Issues

Check issues labeled [`good first issue`](https://github.com/hallosoares/safertrade/labels/good%20first%20issue) for beginner-friendly contributions.

---

## Security

For security vulnerabilities, see [SECURITY.md](SECURITY.md). Do not open public issues for security concerns.

**Responsible Disclosure**: security@safertrade.io

---

## License

Business Source License 1.1 (BUSL-1.1)

- **Non-production use**: Free for learning, development, testing, research
- **Production use**: Requires commercial license until Change Date
- **Change Date**: December 10, 2029 (converts to Apache 2.0)

See [LICENSE](LICENSE) and [LICENSE_FAQ.md](LICENSE_FAQ.md) for details.

---

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/hallosoares/safertrade/issues)
- **Discussions**: [GitHub Discussions](https://github.com/hallosoares/safertrade/discussions)

---

<p align="center">
  <sub>Built for the DeFi community. Protect your investments.</sub>
</p>
