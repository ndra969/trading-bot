# Dry-Run Modes Guide

## Overview

Trading bot memiliki beberapa mode operasi untuk testing dan production yang aman.

## 🎯 Operating Modes

### 1. 🟢 Dry-Run Mode (Safe - Default untuk Testing)

```bash
uv run trading-bot start --dry-run
```

**Behavior:**
- ❌ **No real MT5 connection** → Completely safe
- ❌ **Mock account data** → Account: 12345678, Balance: $10,000
- ❌ **Simulated market data** → Fake prices for testing
- ❌ **Simulated orders** → No real execution
- ✅ **Perfect for development** → Test strategy logic safely

**Use Case:** Development dan testing strategy tanpa resiko sama sekali

**Output:**
```
DRY-RUN: Mock MT5, fully simulated (safe mode)
Initializing MOCK MT5 (Safe Mode)...
OK MOCK MT5 - Account: 12345678 (SIMULATED) | Balance: $10,000.00
   → All data is simulated (no real MT5 required)
```

---

### 2. 🔵 Dry-Run with Real MT5 (Testing with Real Data)

```bash
uv run trading-bot start --dry-run --connect-mt5
```

**Behavior:**
- ✅ **Real MT5 connection** → Connects to your account
- ✅ **Real account data** → Your actual balance/equity
- ✅ **Real market data** → Live prices and quotes
- ❌ **Simulated orders** → Orders logged but NOT executed
- ✅ **Test with real data** → Validate strategy with live data

**Use Case:** Testing strategy dengan real market data tapi tanpa execute order real

**Output:**
```
DRY-RUN: Real MT5 connection, simulated orders
Connecting to MT5...
OK MT5 connected (DRY-RUN) - Account: 159394302 | Balance: $1,792.81
   Orders will be SIMULATED (no real execution)
```

---

### 3. 🔴 Live Mode (Production - REAL MONEY)

```bash
uv run trading-bot start
```

**Behavior:**
- ✅ **Real MT5 connection** → Live connection
- ✅ **Real account data** → Your actual account
- ✅ **Real market data** → Live market
- ✅ **REAL ORDER EXECUTION** → ⚠️ **ACTUAL TRADES WITH REAL MONEY**
- ⚠️ **PRODUCTION USE ONLY** → Use with extreme caution

**Use Case:** Production trading dengan real money (only when fully tested)

**Output:**
```
Starting Trading Bot...
Connecting to MT5...
OK MT5 connected - Account: 159394302 | Balance: $1,792.81

⚠️ LIVE TRADING ACTIVE - Real orders will be executed!
```

---

## 📊 Comparison Table

| Feature | Dry-Run (Mock) | Dry-Run + Real MT5 | Live Mode |
|---------|----------------|-------------------|-----------|
| **MT5 Connection** | ❌ Simulated | ✅ Real | ✅ Real |
| **Account Data** | ❌ Fake ($10k) | ✅ Real | ✅ Real |
| **Market Prices** | ❌ Simulated | ✅ Real Live | ✅ Real Live |
| **Order Execution** | ❌ Simulated | ❌ Simulated | ✅ **REAL** |
| **Risk Level** | ✅ Zero Risk | ✅ Zero Risk | ⚠️ **REAL MONEY** |
| **MT5 Required** | ❌ No | ✅ Yes | ✅ Yes |
| **Windows Required** | ❌ No | ✅ Yes | ✅ Yes |
| **Use Case** | Development | Testing with real data | Production |

---

## 🎓 Usage Examples

### Development (Safe Testing)

```bash
# Default safe mode - no MT5 needed
uv run trading-bot start --dry-run

# Output:
# ✅ Mock MT5 initialized
# ✅ Simulated account: $10,000
# ✅ All operations simulated
# ✅ Safe for development
```

**Benefits:**
- Works on any OS (not just Windows)
- No MT5 installation needed
- No account required
- Zero risk
- Fast testing

---

### Pre-Production Testing

```bash
# Test with real market data
uv run trading-bot start --dry-run --connect-mt5

# Output:
# ✅ Real MT5 connection
# ✅ Real account data
# ✅ Real market prices
# ❌ Orders simulated (safe)
```

**Benefits:**
- Validate with real data
- See actual market conditions
- Test order logic
- No money at risk

---

### Production Deployment

```bash
# LIVE TRADING - Use with caution!
uv run trading-bot start

# Output:
# ✅ Real MT5 connection
# ✅ Real account
# ⚠️ LIVE TRADING ACTIVE
# ⚠️ Real orders executed
```

**Requirements:**
- Fully tested strategy
- Risk management validated
- Emergency procedures in place
- Monitoring active

---

## 🛡️ Safety Recommendations

### Development Phase
```bash
# Always use dry-run during development
uv run trading-bot start --dry-run
```

### Testing Phase
```bash
# Test with real data but simulated orders
uv run trading-bot start --dry-run --connect-mt5
```

### Production Phase
```bash
# Only after extensive testing
# Start with small position sizes
# Monitor closely for first 24 hours
uv run trading-bot start
```

---

## 🔍 How to Verify Mode

Check the startup output to confirm mode:

### Dry-Run (Mock)
```
DRY-RUN: Mock MT5, fully simulated (safe mode)
OK MOCK MT5 - Account: 12345678 (SIMULATED)
```
✅ Safe for development

### Dry-Run + Real MT5
```
DRY-RUN: Real MT5 connection, simulated orders
OK MT5 connected (DRY-RUN) - Account: 159394302
   Orders will be SIMULATED (no real execution)
```
✅ Safe testing with real data

### Live Mode
```
OK MT5 connected - Account: 159394302 | Balance: $1,792.81
⚠️ No dry-run flag detected
```
⚠️ **REAL TRADING - BE CAREFUL**

---

## 📝 Environment Configuration

### .env.dev (Development)
```env
# Development settings
DRY_RUN=true
LOG_LEVEL=DEBUG
MT5_LOGIN=your_demo_login  # Optional for --connect-mt5
MT5_PASSWORD=your_demo_password
MT5_SERVER=YourBroker-Demo
```

### .env.prd (Production)
```env
# Production settings
DRY_RUN=false  # ⚠️ Live trading
LOG_LEVEL=INFO
MT5_LOGIN=your_real_login
MT5_PASSWORD=your_real_password
MT5_SERVER=YourBroker-Real
```

---

## 🚨 Important Notes

### For Dry-Run Mode
1. ✅ Default is **mock MT5** (safest)
2. ✅ No MT5 installation needed
3. ✅ Works offline
4. ✅ Zero risk

### For Dry-Run + Connect MT5
1. ⚠️ Requires MT5 running
2. ⚠️ Windows only
3. ✅ Real market data
4. ✅ Orders still simulated (safe)

### For Live Mode
1. ⚠️ **REAL MONEY AT RISK**
2. ⚠️ Only use after thorough testing
3. ⚠️ Start with minimum position sizes
4. ⚠️ Monitor continuously

---

## 🎯 Decision Flow

```
Need to develop/test? 
    ↓ YES
    Use: --dry-run (mock MT5)
    Risk: ✅ Zero
    MT5 needed: ❌ No

Need real market data for validation?
    ↓ YES
    Use: --dry-run --connect-mt5
    Risk: ✅ Zero (simulated orders)
    MT5 needed: ✅ Yes

Ready for live trading?
    ↓ YES (after extensive testing)
    Use: (no flags)
    Risk: ⚠️ REAL MONEY
    MT5 needed: ✅ Yes
    
    ⚠️ CHECKLIST:
    □ Strategy tested thoroughly
    □ Risk management validated
    □ Position sizes set correctly
    □ Emergency stop configured
    □ Monitoring active
    □ Telegram alerts setup
```

---

## 📚 Related Documentation

- [MT5 Connection Guide](mt5-connection-guide.md)
- [Coding Standards](guides/coding-standards.md)
- [Testing Guide](testing-guide.md)
- [Risk Management](risk-management-guide.md)

---

**Version**: 1.0.0  
**Last Updated**: 2025-11-29

