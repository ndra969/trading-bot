# Risk Management Guide

Multi-layer risk protection system for safe automated trading.

## Overview

```
Position Risk → Portfolio Risk → Account Risk
     (0.5%)        (2% max)        (15% stop)
```

## Risk Layers

### 1. Position-Level Risk

**Risk per Trade**: 0.5% of account balance (default)

```python
# Position sizing formula
volume = (balance × risk_percent) / (sl_distance × pip_value)
```

**Asset-Specific Limits**:
| Asset | Max SL | Breakeven | Trailing |
|-------|--------|-----------|----------|
| Forex Major | 50 pips | +15 pips | 10 pips |
| Forex JPY | 500 pips | +150 pips | 100 pips |
| Gold | 1000 pips | +500 pips | 300 pips |
| Crypto | $2000 | +$1000 | $500 |

### 2. Portfolio-Level Risk

**Limits**:
- **Max Total Exposure**: 6% of account
- **Max Concurrent Positions**: 10 positions
- **Correlation Limit**: Max 60% correlation between positions
- **Asset Class Limits**: Max 3 positions per asset class

### 3. Account-Level Protection

**Drawdown Protection** (automatic):
```
3% drawdown  → Reduce risk by 25%
5% drawdown  → Reduce risk by 50%
8% drawdown  → Reduce risk by 75%
10% drawdown → Emergency stop (close all)
```

## Configuration

`config/risk_parameters.yaml`:

```yaml
portfolio:
  max_risk_percent: 0.02          # 2% max portfolio risk
  max_positions: 10                # Max concurrent positions
  daily_loss_limit_percent: 0.01   # 1% daily loss limit
  emergency_stop_drawdown: 0.15    # 15% emergency stop

correlation:
  threshold: 0.60                  # Max correlation score
  max_correlated_exposure: 0.60    # Max correlated exposure

position:
  risk_per_trade: 0.005            # 0.5% per trade
  min_risk_reward: 2.0             # Min R:R ratio
```

## Volume Calculation

**Example** (EURUSD, $10K account, 30 pip SL, 1% risk):
```
Risk Amount = $10,000 × 0.01 = $100
Volume = $100 / (30 pips × $1 per pip/lot) = 0.33 lots
```

## Monitoring

### Real-Time Metrics
- **Current Risk**: Total portfolio exposure
- **Open Risk**: Sum of all open position risks
- **Correlation Matrix**: Correlation between open positions
- **Drawdown**: Current and maximum drawdown

### Alerts
- **Warning**: Risk > 80% of limit
- **Critical**: Risk > 95% of limit
- **Emergency**: Drawdown > 10%

## Emergency Procedures

### Manual Stop
```bash
uv run trading-bot stop --emergency
```

### Automatic Triggers
1. **Daily Loss Limit**: Stop trading when daily loss > 1%
2. **Drawdown Limit**: Close all positions at 15% drawdown
3. **Correlation Breach**: Reject new correlated positions

## Best Practices

1. **Start Conservative**: Use 0.25% risk when testing
2. **Monitor Daily**: Review risk metrics every day
3. **Adjust Per Account**: Scale limits based on account size
4. **Never Override**: Don't disable risk checks
5. **Keep Records**: Track all risk violations

## Related Documentation

- [Position Management Architecture](position-management-architecture.md) - Position lifecycle
- [Asset Configuration Guide](../setup/asset-configuration-guide.md) - Asset parameters
- [Trading Types Guide](trading-types-guide.md) - Risk by trading type
