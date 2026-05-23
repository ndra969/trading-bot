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

### Core
- `architecture` - System architecture
- `coding-standards` - ⚠️ MANDATORY before coding
- `configuration` - Config management

### Guides
- `cli` - Command reference
- `dry-run` - Testing without risk
- `deployment` - Production deployment
- `intraday` - Day trading execution
- `multi-account` - Multiple accounts
- `multi-timeframe` - MTF analysis
- `strategy` - Strategy development
- `troubleshooting` - Common issues

### Trading
- `trading-types` - Scalping, Day, Swing, Position
- `position-management` - Position lifecycle
- `risk-management` - Risk limits & protection
- `notifications` - Telegram alerts
- `technical-indicators` - RSI, MA

### Setup
- `windows-setup` - Windows/MT5 installation
- `asset-config` - Asset-specific settings
- `broker-symbols` - Multi-broker support
- `market-hours` - Trading sessions

### Integration
- `mt5-connection` - MetaTrader5 setup

### Database
- `database-erd` - Schema diagram

## Structure

```
docs/
├── architecture/     # System design
├── diagrams/         # ERD, flows
├── guides/           # How-to guides
├── integration/      # External APIs
├── setup/            # Configuration
└── trading/          # Trading concepts
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
- `/new <category>/<name>` - Create new doc
