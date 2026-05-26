# Strategy Tuning Plan

**Status**: 🟢 Tuning round 1 applied — observation phase
**Priority**: 🟠 Medium
**Date**: 2026-05-24, last updated 2026-05-26
**Context**: Account size $2000, day_trading mode

Tune strategy parameters for small account ($2K) to balance trade frequency vs quality.

## Round 1 Applied (2026-05-25 to 2026-05-26)

Triggered by ~3% drawdown ($1980 from $2040 starting). Per-symbol P&L showed
XAU/XAG dominating losses. Fixes applied:

| Change | Commit | Effect |
|---|---|---|
| Risk per trade: forex 0.4% → 0.2% | `832a2b1` | Worst-case daily exposure halved (5 × 0.2% = 1% vs 2%) |
| Commodities confluence: 15/18-20 → 40/50 | `84b930d` | Stops weak signals bypassing forex's 75% bar |
| XAU SL: min 80 → 200, default 150 → 350, max 300 → 600 pips | `84b930d` | Within 2-3x H1 ATR (was within 1x) |
| XAG SL: min 8 → 30, default 16 → 50, max 40 → 100 pips | `84b930d` | Same reasoning, scaled to silver pip value |
| Per-symbol BE/trailing | `67173fe` | Gold/silver each get scaled BE (~50% of SL) and trailing (~80% of SL) |
| close_reason now canonical enum | `b72031c` | Position outcomes properly classified for analysis |
| Slippage + market_session captured | `29d1e27` | Per-trade data quality improved for tuning |

**Observation phase:** Run for ~1 week, then review per-symbol P&L by `close_reason`
and `market_session` to decide round 2 adjustments.

---

## Previous Findings (Pre-Round 1)

### 1. Confluence Threshold

**Forex**: `day_trading.confluence_threshold: 30.0` is intentionally low to keep
trade frequency reasonable on a small account. Commodities bypassed even this and
only required 15-20% — patched in `84b930d` to require 40-50%.

### 2. Risk Per Trade Was Buggy (FIXED)

**Was (pre-fix)**: 0.01% (`$0.20` on $2K) → volume always clamped to 0.01
**After fix `756457f`**: percent-based, defaults at 1%
**After tuning `832a2b1`**: forex halved to 0.2%, commodities remain 0.1%

### 3. Per-Symbol Dynamic Volume Flag

✅ Resolved — all 12 symbols in `active_symbols.yaml` have `use_dynamic_lot_size`
explicitly set. Forex (USD + JPY) = true, XAUUSD/XAGUSD/BTCUSD = false (fixed 0.01).

---

## Current Settings (2026-05-26)

```yaml
# Forex pairs (EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, EURJPY, GBPJPY)
risk_per_trade: 0.002        # 0.2% — halved for drawdown protection
use_dynamic_lot_size: true   # risk-based sizing

# XAUUSD (gold) — fixed 0.01 lot, wider SL
risk_per_trade: 0.001
use_dynamic_lot_size: false
min_stop_loss_pips: 200      # $20 (2-3x H1 ATR)
default_stop_loss_pips: 350  # $35
max_stop_loss_pips: 600      # $60
breakeven_trigger: 175       # ≈50% of default SL
trailing_activation: 280     # ≈80% of default SL

# XAGUSD (silver) — fixed 0.01 lot, scaled for silver pip value
risk_per_trade: 0.001
use_dynamic_lot_size: false
min_stop_loss_pips: 30       # $15
default_stop_loss_pips: 50   # $25
max_stop_loss_pips: 100      # $50
breakeven_trigger: 25
trailing_activation: 40

# BTCUSD — fixed 0.01 lot
risk_per_trade: 0.001
use_dynamic_lot_size: false  # No per-symbol BE/trailing yet — uses crypto defaults
```

Commodities confluence threshold (in `foundation_engine._passes_final_quality_filters`):
- Trend-following: 40 (was 15)
- Counter-trend mild vol: 50 (was 20)
- Counter-trend high vol: 50 (was 18)

## Round 2 Candidates (Pending Observation Data)

- [ ] BTCUSD per-symbol BE/trailing (currently shares `crypto` asset class defaults)
- [ ] Confluence threshold tuning for forex (currently 30% via day_trading config)
- [ ] Market-session filtering — analyze whether one session is consistently losing
- [ ] Slippage analysis — high slippage symbols may need spread filter tightening
- [ ] Backfill `close_reason` for the 478 closed positions? (User said no; revisit if needed)

## Verification

- [x] Run `verify-data` CLI against MT5 to confirm position data matches reality
- [x] Confirm config validator catches inverted BE/trailing thresholds (per-symbol too)
- [x] All 1517 unit tests pass after every change

## Related

- [code-review-2026-05.md](code-review-2026-05.md)
- [refactor-codebase.md](refactor-codebase.md)
- Bug fix commit: `756457f` (risk_per_trade decimal/percent normalization)
- Tuning round 1 commits: `832a2b1`, `84b930d`, `67173fe`
- Data tracking commits: `b72031c`, `29d1e27`
