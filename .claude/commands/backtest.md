---
description: Run backtesting on trading strategies
argument-hint: <symbol> [--strategy <name>] [--config <file>]
---

# Backtesting

Run backtesting on trading strategies to validate performance and identify issues.

## Arguments

- **symbol** (optional): Symbol to backtest (if not specified, uses config)
- `--strategy <name>`: Strategy to test (foundation, mtf, etc.)
- `--config <file>`: Custom configuration file

## Implementation Steps

1. **Parse arguments** - Extract symbol, strategy, and config
2. **Run backtest** - Execute backtesting script
3. **Analyze results** - Performance metrics, win rate, profit/loss
4. **Generate report** - Summary of backtest results

## Commands to Execute

```bash
# Single timeframe backtest
uv run python scripts/run_backtest.py --symbol EURUSD --timeframe H1

# Multi-timeframe backtest
uv run python scripts/run_mtf_backtest.py --symbol EURUSD

# With custom config
uv run python scripts/run_backtest.py --config config/backtest_custom.yaml

# Compare backtest results
uv run python scripts/compare_backtest_results.py
```

## Available Backtest Scripts

- `scripts/run_backtest.py` - Single timeframe backtesting
- `scripts/run_mtf_backtest.py` - Multi-timeframe backtesting
- `scripts/backtest_with_fixes.py` - Test with bug fixes
- `scripts/compare_backtest_results.py` - Compare multiple backtests
- `scripts/analyze_trading_performance.py` - Performance analysis

## Backtest Analysis

The backtest analyzes:
- Total trades executed
- Win rate and profit factor
- Average risk/reward ratio
- Maximum drawdown
- Confluence score distribution
- Zone detection accuracy
- Signal quality metrics

## Examples

- `/backtest EURUSD` → Backtest EURUSD with default settings
- `/backtest XAUUSD --strategy mtf` → Multi-timeframe backtest for Gold
- `/backtest --config config/backtest_production.yaml` → Custom config backtest

## Related

- `/analyze` → Analyze symbol with foundation strategy
- `/test` → Run test suite
- `/dry-run` → Validate complete system

## Performance Targets

From CLAUDE.md:
- Trading loop: <55 seconds execution time
- Database queries: <100ms response time
- Memory usage: <2GB under normal load
- MT5 operations: <1 second for execution
