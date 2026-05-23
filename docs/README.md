# Trading Bot Documentation

Complete documentation for the Trading Bot system.

## Quick Start

```bash
# Install dependencies
uv sync

# Setup environment
cp .env.example .env
# Edit .env with your credentials

# Test (safe, no real trades)
uv run trading-bot start --dry-run

# Live trading
uv run trading-bot start --config production
```

---

## Documentation

### 🚀 Getting Started

| Document | Description |
|----------|-------------|
| [Windows Setup](setup/windows-setup-guide.md) | Install on Windows with MT5 |
| [Configuration](setup/configuration-guide.md) | Configure settings |
| [Asset Configuration](setup/asset-configuration-guide.md) | Asset-specific parameters |
| [Broker Symbol Mapping](setup/broker-symbol-mapping-guide.md) | Multi-broker support |
| [Market Hours](setup/market-hours-guide.md) | Trading hours |
| [MT5 Connection](setup/mt5-connection-guide.md) | MetaTrader5 setup |

### 💡 Core Concepts

| Document | Description |
|----------|-------------|
| [Trading Types](trading/trading-types-guide.md) | Scalping, Day, Swing, Position |
| [Position Management](trading/position-management-architecture.md) | Position lifecycle & automation |
| [Risk Management](trading/risk-management-guide.md) | Risk limits & protection |
| [Notifications](trading/notifications-guide.md) | Telegram alerts |
| [Technical Indicators](trading/technical-indicators-guide.md) | RSI, MA, etc. |

### 📚 In-Depth Guides

| Document | Description |
|----------|-------------|
| [Strategy Guide](guides/strategy-guide.md) | Strategy development |
| [Multi-Timeframe Guide](guides/multi-timeframe-guide.md) | MTF analysis |
| [Multi-Account Guide](guides/multi-account-guide.md) | Multiple accounts |
| [Intraday Execution](guides/intraday-execution-guide.md) | Day trading |
| [Dry-Run Guide](guides/dry-run-guide.md) | Testing without risk |
| [CLI Reference](guides/cli-reference.md) | All CLI commands |
| [Coding Standards](guides/coding-standards.md) | Code style |
| [Deployment Guide](guides/deployment-guide.md) | Production deployment |
| [Troubleshooting](guides/troubleshooting-guide.md) | Common issues |

### 🏗️ Architecture

| Document | Description |
|----------|-------------|
| [Architecture Guide](architecture/architecture-guide.md) | System overview |
| [Database ERD](architecture/database-erd.md) | Database schema |

### 📊 Diagrams

Visual flow diagrams (Mermaid format):

| Diagram | Description |
|---------|-------------|
| [Strategy Execution](diagrams/strategy-execution-flow.mermaid) | Strategy flow |
| [Position Management](diagrams/position-management-flow.mermaid) | Position lifecycle |
| [Open Position Flow](diagrams/open-position-flow.mermaid) | Trade execution |
| [Risk Management](diagrams/risk-management-architecture.mermaid) | Risk system |
| [Risk-Notification](diagrams/risk-notification-integration-flow.mermaid) | Risk alerts flow |
| [Account Management](diagrams/account-management-flow.mermaid) | Account operations |
| [Multi-Timeframe](diagrams/multi-timeframe-flow.mermaid) | MTF analysis |
| [Integration Architecture](diagrams/integration-architecture.mermaid) | System integration |

---

## Project Status

**Version**: 2.0.0 | **Tests**: 1605+ (98% coverage) | **Status**: Production Ready

| Phase | Status |
|-------|--------|
| 0-5 | ✅ Complete |
| 5.5 | ⏳ Database Enhancement |
| 6 | 📋 Web Dashboard |

---

## Quick Links

- **Installation**: [Windows Setup](setup/windows-setup-guide.md)
- **Commands**: [CLI Reference](guides/cli-reference.md)
- **Issues**: [Troubleshooting](guides/troubleshooting-guide.md)
- **Architecture**: [Architecture Guide](architecture/architecture-guide.md)
