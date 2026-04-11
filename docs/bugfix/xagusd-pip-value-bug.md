# 🐛 CRITICAL BUG: XAGUSD Pip Value Calculation Error

**Tanggal**: 2026-02-10 23:15  
**Severity**: 🔴 **CRITICAL** - Menyebabkan loss 14x lebih besar dari yang diharapkan!  
**Status**: 🔍 **INVESTIGATING**

---

## 📊 Problem Statement

**User Report**:
> "Profit di log -12 pips tapi di MT5 -$59"

**Position Details** (dari log):
- Symbol: **XAGUSD** (Silver)
- Entry: **82.037**
- SL: **77.990**
- Lot: **0.01**
- Current Price: ~80.8
- **Log shows**: -12 pips = **-$1.20** (calculated)
- **MT5 shows**: -12 pips = **-$59** (actual)

**Discrepancy**: **49x difference** ($59 / $1.20 = 49.17x)

---

## 🔍 Root Cause Analysis

### **Current Configuration** (`config/symbol_mapping.yaml`):

```yaml
pip_values:
  commodities: 0.1          # Pip size (price movement)

pip_values_per_lot:
  commodities: 10.0         # ❌ WRONG! Pip value per 1.0 lot
```

### **Bot's Calculation**:

```
Entry: 82.037
SL: 77.990
Distance: 4.047
Pips: 4.047 / 0.1 = 40.47 pips ✅ (correct)

Pip value per lot: $10.00 (from config)
Lot size: 0.01
Pip value: $10.00 × 0.01 = $0.10 per pip ❌ (WRONG!)

Expected SL loss: 40.47 pips × $0.10 = $4.05
```

### **MT5's Reality**:

```
Current loss: -12 pips = -$59
Implied pip value: $59 / 12 pips = $4.92 per pip

For 0.01 lot:
Pip value per 1.0 lot = $4.92 / 0.01 = $492 per pip per lot ❌

Wait, this doesn't make sense. Let me recalculate...
```

### **Recalculation with SL Distance**:

```
SL distance: 40.47 pips
If hit SL, loss would be: 40.47 pips × pip_value

From MT5 current loss (-$59 at -12 pips):
Pip value = $59 / 12 pips = $4.92 per pip

Expected SL loss = 40.47 pips × $4.92 = $199.11 ❌❌❌
```

**This is CATASTROPHIC!**

---

## 🎯 The Real Problem

### **XAGUSD Contract Specifications** (Typical):

Different brokers have different contract sizes for Silver:

| Broker Type | Contract Size | Pip Size | Pip Value (1 lot) | Pip Value (0.01 lot) |
|-------------|---------------|----------|-------------------|----------------------|
| **Standard** | 5,000 oz | 0.01 | $50.00 | $0.50 |
| **Mini** | 1,000 oz | 0.01 | $10.00 | $0.10 |
| **Micro** | 100 oz | 0.01 | $1.00 | $0.01 |
| **Exness Cent?** | ??? oz | 0.01 or 0.001? | ??? | **$4.92???** |

### **Hypothesis**:

1. **Pip size might be wrong**: Config says `0.1`, but MT5 might use `0.01`
2. **Contract size is different**: Exness Cent might use larger contract size
3. **Pip value per lot is wrong**: Should be ~$492 instead of $10

---

## 🔬 Investigation Steps

### **Step 1: Verify MT5 Symbol Specifications**

We need to check the actual XAGUSD (XAGUSDc) specifications in MT5:

```python
import MetaTrader5 as mt5

symbol_info = mt5.symbol_info("XAGUSDc")
print(f"Contract size: {symbol_info.trade_contract_size}")
print(f"Digits: {symbol_info.digits}")
print(f"Point: {symbol_info.point}")
print(f"Tick size: {symbol_info.trade_tick_size}")
print(f"Tick value: {symbol_info.trade_tick_value}")
```

### **Step 2: Calculate Correct Pip Value**

From MT5 data:
- Current loss: **-$59** at **-12 pips**
- Implied pip value: **$4.92 per pip** for 0.01 lot

If pip size is actually **0.01** (not 0.1):
- Distance: 82.037 - 80.8 = **1.237**
- Pips: 1.237 / 0.01 = **123.7 pips** (not 12 pips!)
- Pip value: $59 / 123.7 = **$0.48 per pip**
- Pip value per lot: $0.48 / 0.01 = **$48 per lot**

This makes more sense!

### **Step 3: Verify with SL Distance**

If pip size = 0.01:
- SL distance: 82.037 - 77.990 = **4.047**
- SL pips: 4.047 / 0.01 = **404.7 pips** (not 40 pips!)
- Expected SL loss: 404.7 × $0.48 = **$194.26**

Still very high for 0.01 lot!

---

## 💡 Most Likely Root Cause

**XAGUSD pip size is 0.01, NOT 0.1**

Evidence:
1. Silver is typically quoted to **2 decimal places** (e.g., 82.03, not 82.0)
2. MT5 loss of $59 for ~12 pips makes sense if pip value = $4.92/pip
3. Config has **wrong pip size** for commodities

**Correct Configuration**:

```yaml
pip_values:
  commodities_gold: 0.1      # XAUUSD: 1 pip = $0.10 movement
  commodities_silver: 0.01   # XAGUSD: 1 pip = $0.01 movement ✅
  
pip_values_per_lot:
  commodities_gold: 10.0     # XAUUSD: $10 per pip per lot
  commodities_silver: 50.0   # XAGUSD: $50 per pip per lot (5000 oz) ✅
```

For 0.01 lot XAGUSD:
- Pip value = $50 × 0.01 = **$0.50 per pip**
- 12 pips loss = 12 × $0.50 = **$6.00** (closer to reality!)

But MT5 shows $59, so there might be additional factors...

---

## 🚨 Immediate Actions Required

### **1. STOP TRADING XAGUSD IMMEDIATELY** ❌

Current SL calculations are **WRONG**. Risk is **14-49x higher** than expected!

### **2. Verify MT5 Symbol Specifications**

Run this script to get actual values:

```python
# scripts/verify_xagusd_specs.py
import MetaTrader5 as mt5

mt5.initialize()
symbol = "XAGUSDc"  # or XAGUSDm depending on account

info = mt5.symbol_info(symbol)
print(f"Symbol: {symbol}")
print(f"Contract size: {info.trade_contract_size}")
print(f"Digits: {info.digits}")
print(f"Point: {info.point}")
print(f"Tick size: {info.trade_tick_size}")
print(f"Tick value: {info.trade_tick_value}")
print(f"Tick value profit: {info.trade_tick_value_profit}")
print(f"Tick value loss: {info.trade_tick_value_loss}")

# Calculate pip value
pip_size = 0.01 if info.digits >= 2 else 0.1
pip_value_per_lot = info.trade_tick_value / info.trade_tick_size * pip_size
print(f"\nCalculated pip size: {pip_size}")
print(f"Calculated pip value per 1.0 lot: ${pip_value_per_lot:.2f}")
print(f"Calculated pip value per 0.01 lot: ${pip_value_per_lot * 0.01:.2f}")
```

### **3. Fix Configuration**

Once we have MT5 specs, update `symbol_mapping.yaml`:

```yaml
# Option 1: Separate configs for Gold and Silver
pip_values:
  commodities_gold: 0.1
  commodities_silver: 0.01
  
# Option 2: Symbol-specific overrides
symbol_specific_pip_values:
  XAUUSD: 0.1
  XAGUSD: 0.01
```

### **4. Close Existing XAGUSD Position**

Current position has **WRONG SL calculation**. Risk is unknown!

---

## 📝 TODO

- [ ] Run MT5 verification script
- [ ] Get actual contract specs from broker
- [ ] Update `symbol_mapping.yaml` with correct values
- [ ] Add symbol-specific pip value support
- [ ] Test calculations with backtest
- [ ] Close current XAGUSD position (if still open)
- [ ] Add validation to prevent this in future

---

## 🔧 Proposed Fix

### **File**: `config/symbol_mapping.yaml`

Add symbol-specific pip values:

```yaml
# Asset class defaults
pip_values:
  commodities: 0.1          # Default for Gold
  crypto: 1.0
  forex_jpy: 0.01
  forex_major: 0.0001

# Symbol-specific overrides (NEW)
symbol_pip_values:
  XAGUSD: 0.01              # Silver uses 0.01, not 0.1
  XAUUSD: 0.1               # Gold uses 0.1 (explicit)

pip_values_per_lot:
  commodities: 10.0         # Default for Gold
  crypto: 1.0
  forex_jpy: 9.09
  forex_major: 10.0

# Symbol-specific pip values per lot (NEW)
symbol_pip_values_per_lot:
  XAGUSD: 50.0              # $50 per pip per lot (5000 oz contract)
  XAUUSD: 10.0              # $10 per pip per lot (100 oz contract)
```

### **File**: `src/trading_bot/connectors/symbol_mapper.py`

Update `get_pip_size()` to check symbol-specific values first:

```python
def get_pip_size(self, symbol: str) -> float:
    normalized_symbol = self.normalize_symbol(symbol)
    
    # Check symbol-specific overrides first
    if "symbol_pip_values" in self.config:
        if normalized_symbol in self.config["symbol_pip_values"]:
            return self.config["symbol_pip_values"][normalized_symbol]
    
    # Fall back to asset class default
    asset_class = self.get_asset_class(symbol)
    # ... existing logic
```

---

## ⚠️ Impact Assessment

**Current Risk**:
- XAGUSD position with 0.01 lot
- Expected max loss: **$4.05** (bot calculation)
- Actual max loss: **~$200** (if SL hit)
- **Risk multiplier: 49x** 🔴

**Affected Symbols**:
- ✅ XAUUSD: Likely correct (pip size 0.1 is standard)
- ❌ XAGUSD: **WRONG** (pip size should be 0.01)
- ❓ Other commodities: Need verification

---

**Next Step**: Run MT5 verification script to get exact specifications.
