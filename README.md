# 🛡️ SaferTrade — Open-Source DeFi Threat Detection

<div align="center">

[![License: BUSL-1.1](https://img.shields.io/badge/License-BUSL--1.1-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776ab.svg?logo=python&logoColor=white)](https://python.org)
[![Redis](https://img.shields.io/badge/Redis-Streams-dc382d.svg?logo=redis&logoColor=white)](https://redis.io)
[![Web3](https://img.shields.io/badge/Web3-Ethereum-3c3c3d.svg?logo=ethereum&logoColor=white)](https://ethereum.org)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**Real-time DeFi threat detection across 7 chains.**
Detect honeypots, phishing, pump & dumps, oracle attacks, and more.

[Getting Started](#-quick-start) •
[Engines](#-detection-engines) •
[Roadmap](#-roadmap) •
[Contributing](#-contributing) •
[License](#-license)

</div>

---

## 🎯 What is SaferTrade?

SaferTrade is an **open-source DeFi security toolkit** that helps developers and traders detect threats before they become victims:

- **🕵️ Honeypot Detection** — Identify tokens you can buy but can't sell
- **🎣 Phishing Detection** — Flag known scam addresses and contracts
- **📈 Pump & Dump Detection** — Spot coordinated price manipulation
- **🔮 Oracle Attack Detection** — Monitor for price feed manipulation
- **💧 Liquidity Analysis** — Assess rug pull risks
- **⚡ Real-time Alerts** — Redis Streams for sub-second notifications

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Blockchain     │────▶│  Detection       │────▶│  Redis          │
│  RPC Nodes      │     │  Engines         │     │  Streams        │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                        ┌─────────────────────────────────┴─────┐
                        ▼                   ▼                   ▼
                  ┌──────────┐       ┌──────────┐       ┌──────────┐
                  │  Your    │       │ Telegram │       │ Discord  │
                  │  App/API │       │  Alerts  │       │  Alerts  │
                  └──────────┘       └──────────┘       └──────────┘
```

## ⚡ Quick Start

```bash
# Clone the repository
git clone https://github.com/gadayubn/safertrade.git
cd safertrade

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your RPC keys (get free ones at alchemy.com or infura.io)

# Start Redis (required)
redis-server &

# Run a detection engine
python engines/honeypot_checker.py --health
```

## 🔍 Detection Engines

| Engine | Description | Status |
|--------|-------------|--------|
| `honeypot_checker.py` | Detect buy-only tokens | ✅ Ready |
| `phishing_detector.py` | Flag known scam addresses | ✅ Ready |
| `pump_detector.py` | Spot price manipulation | ✅ Ready |
| `oracle_manipulation_detector.py` | Monitor price feeds | ✅ Ready |
| `stablecoin_depeg_monitor.py` | Track stablecoin pegs | ✅ Ready |
| `token_holder_analyzer.py` | Analyze holder distribution | ✅ Ready |
| `liquidity_analyzer.py` | Assess liquidity risks | ✅ Ready |
| `gas_price_optimizer.py` | Optimize transaction costs | ✅ Ready |
| `health_check.py` | System monitoring | ✅ Ready |

### Example: Honeypot Detection

```python
from engines.honeypot_checker import HoneypotChecker

checker = HoneypotChecker()
result = await checker.analyze_token(
    token_address="0x...",
    chain="ethereum"
)

print(f"Is Honeypot: {result['is_honeypot']}")
print(f"Risk Score: {result['risk_score']}")
```

## 🌐 Supported Chains

| Chain | Chain ID | Status |
|-------|----------|--------|
| Ethereum | 1 | ✅ Full support |
| Base | 8453 | ✅ Full support |
| Polygon | 137 | ✅ Full support |
| Optimism | 10 | ✅ Full support |
| Arbitrum | 42161 | ✅ Full support |
| Blast | 81457 | ✅ Full support |
| Solana | — | ✅ Full support |

## 🗺️ Roadmap

### ✅ Released (v1.0)
- Core detection engines
- Multi-chain support (7 chains)
- Redis Streams integration
- Basic alert system

### 🚧 Coming Soon (v1.1)
- [ ] **Web Dashboard** — Visual interface for monitoring (90% complete!)
- [ ] **REST API** — Programmatic access to all detections
- [ ] **WebSocket Alerts** — Real-time push notifications
- [ ] **Telegram Bot** — Instant mobile alerts

### 🔮 Future (v2.0)
- [ ] **ML-Powered Detection** — Machine learning models for advanced threats
- [ ] **Whale Tracking** — Monitor large wallet movements
- [ ] **MEV Detection** — Sandwich attack monitoring
- [ ] **Flash Loan Analysis** — Flash loan attack detection
- [ ] **Knowledge Vault** — RAG-powered threat intelligence

> 💡 **Want to contribute?** Check out our [good first issues](https://github.com/gadayubn/safertrade/labels/good%20first%20issue)!

## 📊 Project Stats

- **Detection Engines:** 15+ specialized modules
- **Chains Supported:** 7 networks
- **Alert Latency:** <1 second via Redis Streams
- **License:** BUSL-1.1 (free for non-commercial use)

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Fork the repo, then:
git checkout -b feature/your-feature
# Make changes
git commit -m "feat: Add your feature"
git push origin feature/your-feature
# Open a Pull Request
```

### Good First Issues
- 🏷️ [good first issue](https://github.com/gadayubn/safertrade/labels/good%20first%20issue) — Great for newcomers
- 🆘 [help wanted](https://github.com/gadayubn/safertrade/labels/help%20wanted) — We need your expertise

## 📜 License

**Business Source License 1.1 (BUSL-1.1)**

- ✅ **Free for:** Learning, development, testing, research, internal PoCs
- ❌ **Requires license for:** Production/commercial use
- 📅 **Change Date:** December 10, 2029 (converts to GPLv2)

See [LICENSE](LICENSE), [COMMERCIAL_LICENSE.md](COMMERCIAL_LICENSE.md), and [LICENSE_FAQ.md](LICENSE_FAQ.md).

## 🔗 Links

- [Documentation](docs/GETTING_STARTED.md)
- [Commercial Licensing](COMMERCIAL_LICENSE.md)
- [Security Policy](SECURITY.md)
- [Changelog](CHANGELOG.md)

## 💬 Community

- 💬 [GitHub Discussions](https://github.com/gadayubn/safertrade/discussions) — Ask questions, share ideas
- 🐛 [Issue Tracker](https://github.com/gadayubn/safertrade/issues) — Report bugs, request features
- 🐦 [Twitter](https://twitter.com/SaferTrade) — Follow for updates

---

<div align="center">

**Built for DeFi safety. Powered by the community.**

⭐ Star this repo if you find it useful!

</div>
