# Strategy Tuning Plan

**Status**: Planned
**Priority**: 🟠 Medium
**Date**: 2026-05-24
**Context**: Account size $2000, day_trading mode

Tune strategy parameters for small account ($2K) to balance trade frequency vs quality.

## Current Issues

### 1. Confluence Threshold Too Low

**Config**: `day_trading.confluence_threshold: 30.0`
**Docs/intended**: minimum 65% confluence
**Impact**: Low-quality signals accepted (3 of 8 layers agreeing is enough)

### 2. Risk Per Trade Was Buggy (FIXED)

**Was**: 0.01% (`$0.20` on $2K) → volume always clamped to 0.01
**Now**: 1.0% (`$20` on $2K) → realistic volumes per asset

### 3. Per-Symbol Dynamic Volume Flag

**Status**: ✅ Already exists in `active_symbols.yaml` as `use_dynamic_lot_size`
**Action**: Verify all pairs have the flag explicitly set (no global default)

## Recommended Settings for $2000 Account

### Day Trading Conservative (Recommended Start)

```yaml
day_trading:
  risk_per_trade: 0.005          # 0.5% = $10/trade (was 1%)
  max_positions: 3               # Was 5
  confluence_threshold: 65.0     # Was 30.0
  max_loss_per_day: 0.015        # 1.5% = $30 (was 2%)
```

Max exposure: 3 × 0.5% = 1.5% per moment, $45 daily max loss.

### Day Trading Balanced (Current After Fix)

```yaml
day_trading:
  risk_per_trade: 0.01           # 1% = $20/trade
  max_positions: 5
  confluence_threshold: 65.0     # Raise from 30 to 65
  max_loss_per_day: 0.02         # 2% = $40
```

Max exposure: 5 × 1% = 5% per moment, $40 daily max loss.

### Day Trading Aggressive

```yaml
day_trading:
  risk_per_trade: 0.015          # 1.5% = $30/trade
  max_positions: 4
  confluence_threshold: 60.0
  max_loss_per_day: 0.03         # 3% = $60
```

Max exposure: 4 × 1.5% = 6% per moment, $60 daily max loss.

## Per-Pair Dynamic Volume Configuration

Each pair must have `use_dynamic_lot_size` explicitly:

```yaml
# config/active_symbols.yaml
EURUSD:
  use_dynamic_lot_size: true   # Calculate from risk
  min_volume_lots: 0.01
  max_volume_lots: 1.0

XAUUSD:
  use_dynamic_lot_size: false  # Fixed 0.01 (for high volatility)
  min_volume_lots: 0.01        # Used as fixed when dynamic=false

BTCUSD:
  use_dynamic_lot_size: false  # Crypto too volatile for small account
  min_volume_lots: 0.01        # Fixed minimum
  max_volume_lots: 0.1
```

**Rule**: If `use_dynamic_lot_size: false`, the bot uses `min_volume_lots` as fixed size.

## Audit Tasks

- [ ] List all pairs in active_symbols.yaml
- [ ] Verify each has `use_dynamic_lot_size` explicitly set
- [ ] Add flag with safe default (false) for any missing pair
- [ ] Document recommended settings per pair

## Strategy Per-Asset Tuning Recommendations

### Forex Majors (EURUSD, GBPUSD, etc.)
- `use_dynamic_lot_size: true` (risk-based calculation)
- 30 pip SL, 60 pip TP (1:2 RR)
- Min confluence 65%

### Forex JPY (USDJPY, EURJPY, etc.)
- `use_dynamic_lot_size: true`
- 40 pip SL (400 points - JPY pairs use 0.01 pip)
- More conservative due to volatility

### Commodities (XAUUSD, XAGUSD)
- `use_dynamic_lot_size: false` for small accounts
- Fixed 0.01 lot (Gold volatile, can lose $10-20 per 100 pips)
- Higher SL (100+ pips)
- Min confluence 70% (strict)

### Crypto (BTCUSD)
- `use_dynamic_lot_size: false` for small accounts ⚠️
- Fixed micro lot (0.01)
- Very wide SL (500+ pips for BTC)
- Min confluence 75% (very strict)
- Consider only trading during low volatility periods

## Open Questions

- [ ] Which preset to use? (Conservative/Balanced/Aggressive)
- [ ] Should we add a CLI command to switch presets?
- [ ] Test each preset in dry-run for a week?
- [ ] Track win rate per preset?

## Related

- [code-review-2026-05.md](code-review-2026-05.md)
- [refactor-codebase.md](refactor-codebase.md)
- Bug fix commit: `756457f` (risk_per_trade decimal/percent)
