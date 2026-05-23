---
description: Quick access to project documentation
argument-hint: [topic|list]
---

# Documentation Reference

Quick access to project documentation and guides.

## Arguments

- **no argument**: Display documentation overview
- `list`: List all available documentation
- `topic`: Display specific documentation topic

## Available Documentation Topics

### Core Implementation
- `architecture` - Complete system architecture
- `configuration` - Configuration management guide
- `strategy` - Strategy implementation guide
- `trading-types` - Trading types (scalping, day, swing, position)
- `risk-management` - Complete risk management system
- `position-management` - Position management with pip tracking
- `multi-timeframe` - Multi-timeframe analysis guide

### Technical Components
- `technical-indicators` - RSI & Moving Average implementation
- `technical-installation` - Windows library setup guide
- `broker-symbols` - Multi-broker compatibility
- `asset-config` - Asset-specific settings
- `timeframe` - Timeframe analysis guide

### Operations & Integration
- `windows-setup` - Windows/MT5 setup guide
- `cli` - Complete CLI command reference
- `notifications` - Telegram notification system
- `code-examples` - Production-ready patterns

### Database & Architecture
- `database-erd` - Complete database ERD with relationships
- `erd-diagram` - Database ERD diagram (Mermaid)
- `position-flow` - Position management flow diagram
- `risk-architecture` - Risk management system diagrams

### Quality Assurance
- `testing` - Comprehensive testing strategy
- `volume-testing` - Volume calculation test cases
- `risk-testing` - Risk management validation
- `coding-standards` - Complete coding standards (MANDATORY)

## Implementation Steps

1. **Parse topic** - Identify documentation to display
2. **Locate file** - Find documentation in `docs/` directory
3. **Read and display** - Show relevant documentation content
4. **Provide navigation** - Link to full documentation

## Documentation Files Location

```
docs/
├── README.md                          # Documentation index
├── architecture/
│   └── architecture-guide.md         # System architecture
├── guides/
│   ├── cli-reference.md              # CLI commands
│   ├── coding-standards.md           # ⚠️ MANDATORY before code changes
│   ├── deployment-guide.md           # Production deployment
│   ├── dry-run-guide.md              # Testing without risk
│   ├── intraday-execution-guide.md   # Day trading
│   ├── multi-account-guide.md        # Multiple accounts
│   ├── multi-timeframe-guide.md      # MTF analysis
│   ├── strategy-guide.md             # Strategy development
│   └── troubleshooting-guide.md      # Common issues
├── diagrams/
│   ├── database-erd.md               # Database schema (doc + mermaid)
│   ├── account-management-flow.mermaid
│   ├── integration-architecture.mermaid
│   ├── multi-timeframe-flow.mermaid
│   ├── open-position-flow.mermaid
│   ├── position-management-flow.mermaid
│   ├── risk-management-architecture.mermaid
│   ├── risk-notification-integration-flow.mermaid
│   ├── risk-notification-overview.mermaid
│   └── strategy-execution-flow.mermaid
├── integration/
│   └── mt5-connection-guide.md       # MetaTrader5 setup
├── setup/
│   ├── asset-configuration-guide.md  # Asset-specific settings
│   ├── broker-symbol-mapping-guide.md # Multi-broker support
│   ├── configuration-guide.md        # Configure settings
│   ├── market-hours-guide.md         # Trading hours
│   └── windows-setup-guide.md        # Windows/MT5 setup
└── trading/
    ├── notifications-guide.md        # Telegram alerts
    ├── position-management-architecture.md # Position lifecycle
    ├── risk-management-guide.md      # Risk limits & protection
    ├── technical-indicators-guide.md # RSI, MA, etc.
    └── trading-types-guide.md        # Scalping, Day, Swing, Position
```

## Examples

- `/docs` → Display documentation overview
- `/docs list` → List all available documentation
- `/docs risk-management` → Display risk management guide
- `/docs coding-standards` → Display coding standards (MANDATORY)

## Related

- `/rules` → Display project rules and guidelines
- `/claude` → Display CLAUDE.md content
