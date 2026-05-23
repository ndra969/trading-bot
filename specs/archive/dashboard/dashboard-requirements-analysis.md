# 📊 Trading Dashboard & Analytics Requirements Analysis

**Date**: January 5, 2026
**Purpose**: Validation of user requirements and identification of critical gaps for a professional-grade trading dashboard.

---

## 🎯 1. Validation of User Concerns

You raised several critical points that are absolutely valid and essential for any professional trading system. Here is the breakdown:

### A. "Kita ga tau pakai akun mana" (Identity Context) ✅ **VALID & CRITICAL**
In a multi-environment setup (Demo vs Live, Cent vs Standard, or multiple Prop Firm accounts), knowing *which* account executed a trade is mandatory.
*   **Current Gap**: The `TRADING_SESSIONS` table tracks a session, but doesn't explicitly link to a specific `account_id` or `broker_account_number`.
*   **Risk**: Mixing data from a $100 Cent account with a $100,000 Prop account ruins all analytics.

### B. "Posisi dibuka dengan strategi apa" (Strategy Attribution) ✅ **VALID & CRITICAL**
Knowing that a trade was "Scalping" is not enough. You need to know *why* it was taken.
*   **Current Gap**: `TRADING_SESSIONS` has `trading_type`, but if a bot runs "Hybrid" mode (taking both Scalping and Day Trading signals), the session-level tag is insufficient.
*   **Requirement**: Each *Position* needs a `strategy_id` or `magic_number` equivalent to trace it back to the specific logic that triggered it (e.g., "Scalping_M5_RSI_Divergence").

### C. "Perubahan config bisa ada pembedanya" (Versioning & Auditability) ✅ **VALID & CRITICAL**
Trading results are meaningless without context of the configuration used.
*   **Scenario**: Week 1 you used `RSI > 70` for Sell. Week 2 you changed it to `RSI > 80`.
*   **Current Gap**: `config_profile` is just a string (name). If the *content* of that profile changes, you lose the history of what parameters actually produced the Week 1 results.
*   **Requirement**: Hash-based config tracking or a `CONFIG_VERSIONS` table to snapshot the exact parameters used for every session/trade.

---

## 🔍 2. Advanced Improvements & Missing Metrics (The "Improvement" Layer)

Beyond your points, a professional dashboard needs these "Source of Truth" metrics to actually answer "Mana posisi yang bagus":

### A. Execution Quality Analysis (Slippage & Latency)
*   **Expected Price vs. Executed Price**: Essential to detect broker manipulation or poor liquidity.
*   **Time to Fill**: How long between signal generation and order fill?

### B. "The Holy Grail" Metrics: MAE & MFE
To truly answer "Is this a good position?", P&L is not enough. You need:
*   **MAE (Maximum Adverse Excursion)**: How much did the price go *against* you while the trade was open?
    *   *Insight*: If your SL is 50 pips, but price never went against you more than 5 pips, your SL is too loose (inefficient).
*   **MFE (Maximum Favorable Excursion)**: How much did the price go *in your favor*?
    *   *Insight*: If price went +100 pips in profit but you closed at +10 pips, your Exit Strategy is broken.

### C. Market Context Snapshots
A trade doesn't happen in a vacuum.
*   **Volatility at Entry**: Was the market quiet or exploding?
*   **Spread at Entry**: Did you pay 2 pips or 20 pips?

---

## 🛠️ 3. Implementation Recommendations (No Code, Conceptual)

### Database Schema Updates Required

#### 1. Account Identity Layer
Need a new entity `TRADING_ACCOUNTS` to store:
*   `account_id` (PK)
*   `broker_name`
*   `account_number` (Login)
*   `currency`
*   `account_type` (Demo/Real/Cent)

*Link `TRADING_SESSIONS` to `TRADING_ACCOUNTS`.*

#### 2. Configuration Versioning Layer
Need a new entity `CONFIG_SNAPSHOTS` to store:
*   `config_hash` (PK) - Unique hash of the JSON content
*   `config_json` - The actual full parameters
*   `created_at`

*Link `TRADING_SESSIONS` to `CONFIG_SNAPSHOTS` instead of just a profile name.*

#### 3. Enhanced Position Metrics (The "Quality" Columns)
Add to `POSITIONS` table:
*   `magic_number` / `strategy_signature`: Unique ID for the specific logic block.
*   `mae_pips` & `mae_usd`: Max drawdown during trade.
*   `mfe_pips` & `mfe_usd`: Max potential profit during trade.
*   `execution_duration_ms`: Latency tracking.
*   `tags`: Array of strings for flexible categorization (e.g., ["NEWS", "RECOVERY", "MANUAL_INTERVENTION"]).

---

## 🎨 4. Dashboard Visualization Concepts

### A. The "Strategy Comparison" Matrix
A table comparing identical timeframes across different Config Versions.
*   *Row*: Config V1 vs Config V2
*   *Columns*: Win Rate, Drawdown, Avg MAE (Risk Efficiency).

### B. The "Efficiency" Scatter Plot
*   *X-Axis*: MFE (Max potential profit)
*   *Y-Axis*: Realized Profit
*   *Goal*: Dots should cluster near the diagonal line.
*   *Analysis*: Dots far below the line mean "Leaving money on the table".

### C. Equity Curve Simulator
"What if I didn't take trades during the 'New York' session?"
*   Allows filtering trades by metadata (Time, Strategy, Account) to simulate theoretical performance.

---

## ✅ Conclusion

Your intuition is 100% correct. The current schema is "functional" but **not "analytical"**. It can track *what happened*, but it struggles to explain *why it happened* or *how to improve it*.

**Immediate Action Plan**:
1.  Refine the Schema to include Accounts, Config Versioning, and MAE/MFE.
2.  Update the `DASHBOARD_BRAINSTORM.md` with these advanced requirements.
