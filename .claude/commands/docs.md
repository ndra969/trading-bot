---
description: Quick access to documentation
argument-hint: [topic]
---

# Documentation Reference

Quick access to project documentation.

## Usage

```
/docs              # Show overview
/docs [topic]      # Show specific doc
/docs list         # List all docs
```

## Topics

### Architecture
- `architecture` - System architecture
- `database-erd` - Database schema & ERD

### Setup
- `windows-setup` - Windows/MT5 installation
- `mt5-connection` - MetaTrader5 setup
- `configuration` - Config management
- `asset-config` - Asset-specific settings
- `broker-symbols` - Multi-broker support
- `market-hours` - Trading sessions

### Trading
- `trading-types` - Scalping, Day, Swing, Position
- `position-management` - Position lifecycle
- `risk-management` - Risk limits & protection
- `notifications` - Telegram alerts
- `technical-indicators` - RSI, MA

### Guides
- `cli` - Command reference
- `coding-standards` - ⚠️ MANDATORY before coding
- `deployment` - Production deployment
- `dry-run` - Testing without risk
- `intraday` - Day trading execution
- `multi-account` - Multiple accounts
- `multi-timeframe` - MTF analysis
- `strategy` - Strategy development
- `troubleshooting` - Common issues

## Structure

```
docs/
├── architecture/    # System design & database
├── setup/           # Installation & configuration
├── trading/         # Trading concepts
├── guides/          # How-to guides
└── diagrams/        # Mermaid diagrams
```

## Examples

```
/docs                    # Overview
/docs coding-standards   # Standards (MANDATORY)
/docs risk-management    # Risk guide
/docs database-erd       # Schema
```

## Related

- `/rules` - Project rules
- `/status` - Bot status
- `/logs` - View logs
- `/new <category>/<name>` - Create new doc
