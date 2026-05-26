# Trading Types Guide

Configure the bot for different trading styles.

> **Implementation Status**: Currently only **Day Trading** is fully implemented. Other types are planned for future phases.

## Overview

The bot adapts strategy, risk, and timeframes based on trading type.

| Type | Status | Hold Duration | Timeframes | Risk/Trade | Max Daily Trades |
|------|--------|---------------|------------|------------|------------------|
| **Day Trading** | ✅ Implemented | 30-1440 min | M15, H1, H4 | 0.5% | 8 |
| **Scalping** | 📋 Planned (Phase 4) | 1-240 min | M1, M5, M15 | 0.2% | 20 |
| **Swing** | 📋 Planned (Phase 3) | 1-7 days | H4, D1, W1 | 0.8% | 2 |
| **Position** | 📋 Planned (Future) | 1-4 weeks | D1, W1, MN1 | 1.2% | 1 |

## Scalping 📋 Planned

**Status**: Not yet implemented (Phase 4 planned). Configurations below are documented for future reference.

**Best for**: High-frequency trading, quick profits, tight spreads

| Parameter | Value |
|-----------|-------|
| Hold target | 15 minutes |
| Primary TF | M1 |
| Risk/trade | 0.2% |
| Min SL | 5 pips |
| Breakeven | 5 pips |
| Trailing | 3 pips |
| Sessions | London + NY overlap |
| Max trades/day | 20 |

**Strategy weight**:
- Technical: 60% (heavy)
- Foundation: 25%
- Multi-TF: 15%

## Day Trading ✅ Implemented

**Status**: Fully implemented via `IntradayExecutor`.

**Best for**: Intraday opportunities, balanced approach

| Parameter | Value |
|-----------|-------|
| Hold target | 4 hours |
| Primary TF | H1 |
| Risk/trade | 0.5% |
| Min SL | 15 pips |
| Breakeven | 15 pips |
| Trailing | 10 pips |
| Sessions | London, NY |
| Max trades/day | 8 |

**Strategy weight**:
- Foundation: 40%
- Technical: 35%
- Multi-TF: 25%

## Swing Trading 📋 Planned

**Status**: Not yet implemented (Phase 3 planned). Configurations below are documented for future reference.

**Best for**: Multi-day trends, less monitoring needed

| Parameter | Value |
|-----------|-------|
| Hold target | 3 days |
| Primary TF | H4 |
| Risk/trade | 0.8% |
| Min SL | 50 pips |
| Breakeven | 50 pips |
| Trailing | 30 pips |
| Sessions | All |
| Max trades/day | 2 |

**Strategy weight**:
- Foundation: 45%
- Multi-TF: 35%
- Technical: 20%

## Position Trading 📋 Planned

**Status**: Not yet implemented (Future planning). Configurations below are documented for future reference.

**Best for**: Long-term trends, minimal monitoring

| Parameter | Value |
|-----------|-------|
| Hold target | 2 weeks |
| Primary TF | D1 |
| Risk/trade | 1.2% |
| Min SL | 150 pips |
| Breakeven | 150 pips |
| Trailing | 100 pips |
| Sessions | All |
| Max trades/day | 1 |

**Strategy weight**:
- Multi-TF: 40%
- Foundation: 35%
- Fundamental: 25%

## Switching Trading Types

> **Note**: CLI commands below are 📋 Planned. Currently set trading type via `config/trading_types.yaml`.

```bash
# Planned commands (not yet implemented)
uv run trading-bot type switch --type day_trading
uv run trading-bot type status
uv run trading-bot type compare --types scalping,day_trading
```

**Current method**: Edit `default_trading_type` in `config/trading_types.yaml`.

## Configuration

`config/trading_types.yaml`:

```yaml
default_trading_type: day_trading

types:
  scalping:
    hold_duration:
      target_minutes: 15
    timeframes:
      primary: M1
      analysis: [M1, M5, M15]
    risk:
      per_trade: 0.002
      max_positions: 5
      max_daily_trades: 20
    position:
      min_sl_pips: 5
      breakeven_pips: 5
      trailing_pips: 3

  day_trading:
    hold_duration:
      target_minutes: 240
    timeframes:
      primary: H1
      analysis: [M15, H1, H4]
    risk:
      per_trade: 0.005
      max_positions: 5
      max_daily_trades: 8
    position:
      min_sl_pips: 15
      breakeven_pips: 15
      trailing_pips: 10

  swing_trading:
    hold_duration:
      target_hours: 72
    timeframes:
      primary: H4
      analysis: [H4, D1, W1]
    risk:
      per_trade: 0.008
      max_positions: 3
      max_daily_trades: 2
    position:
      min_sl_pips: 50
      breakeven_pips: 50
      trailing_pips: 30

  position_trading:
    hold_duration:
      target_days: 14
    timeframes:
      primary: D1
      analysis: [D1, W1, MN1]
    risk:
      per_trade: 0.012
      max_positions: 2
      max_daily_trades: 1
    position:
      min_sl_pips: 150
      breakeven_pips: 150
      trailing_pips: 100
```

## Choosing the Right Type

### Recommended by Goal

| Goal | Trading Type |
|------|--------------|
| **Quick profits** | Scalping |
| **Daily income** | Day Trading |
| **Part-time trading** | Swing |
| **Long-term wealth** | Position |

### Recommended by Experience

| Experience | Trading Type |
|------------|--------------|
| Beginner | Day Trading or Swing |
| Intermediate | Day Trading + Swing |
| Advanced | Any |

## Performance Tracking

Each type tracks separate metrics:
- Win rate
- Average pips per trade
- Average holding time
- Risk-adjusted returns

```bash
# 📋 Planned (not yet implemented). Query DB directly for now:
uv run trading-bot performance --by-type
```

## Related Documentation

- [Multi-Timeframe Guide](../guides/multi-timeframe-guide.md) - MTF analysis
- [Risk Management](risk-management-guide.md) - Risk per type
- [Position Management](position-management-architecture.md) - Position lifecycle
- [Strategy Guide](../guides/strategy-guide.md) - Strategy architecture
