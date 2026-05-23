"""Test position size calculation with new risk settings."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from trading_bot.position.pip_calculator import PipCalculator


def calculate_position_size_manual(balance, risk_amount, stop_distance_pips, pip_value_per_lot):
    """Manual position size calculation (without PortfolioRiskManager)."""
    if pip_value_per_lot == 0 or stop_distance_pips == 0:
        return 0.01  # Minimum lot size

    # Formula: Position Size = Risk Amount / (SL Distance × Pip Value per Lot)
    position_size = risk_amount / (stop_distance_pips * pip_value_per_lot)
    return position_size


def test_lot_size_calculation():
    """Test lot size calculation with 1% risk."""
    print("=" * 70)
    print("LOT SIZE CALCULATION TEST")
    print("=" * 70)
    print()

    # Test parameters (simulating USDJPY trade)
    balance = 1756.0
    risk_percentage = 0.01  # 1%
    risk_amount = balance * risk_percentage

    print(f"Account Balance: ${balance:.2f}")
    print(f"Risk Percentage: {risk_percentage * 100}%")
    print(f"Risk Amount: ${risk_amount:.2f}")
    print()

    # Initialize pip calculator
    pip_calculator = PipCalculator()

    # Test for different symbols
    test_symbols = [
        ("EURUSD", 1.1000, 1.0850, 1.1150),  # Example: Entry 1.1000, SL 1.0850, TP 1.1150
        ("GBPUSD", 1.2700, 1.2550, 1.2850),
        ("USDJPY", 158.228, 158.429, 157.832),  # Real example from notification
        ("USDCHF", 0.8800, 0.8950, 0.8650),
        ("AUDUSD", 0.6500, 0.6350, 0.6650),
        ("USDCAD", 1.3600, 1.3750, 1.3450),
    ]

    for symbol, entry, sl, tp in test_symbols:
        print(f"\n{'=' * 70}")
        print(f"SYMBOL: {symbol}")
        print(f"{'=' * 70}")

        # Calculate pip size
        pip_size = pip_calculator.get_pip_size(symbol)

        # Calculate stop loss distance
        risk_pips = abs(entry - sl) / pip_size

        print(f"Entry:  {entry:.5f}")
        print(f"SL:     {sl:.5f}")
        print(f"TP:     {tp:.5f}")
        print(f"Risk:   {risk_pips:.1f} pips")
        print()

        # Calculate pip value per lot
        pip_value_per_lot = pip_calculator.calculate_pip_value(symbol, 1.0)

        # Calculate position size (manual formula)
        position_size = calculate_position_size_manual(
            balance=balance,
            risk_amount=risk_amount,
            stop_distance_pips=risk_pips,
            pip_value_per_lot=pip_value_per_lot,
        )

        # Clamp to min/max (0.01 - 1.0 lots for most forex)
        position_size = max(0.01, min(position_size, 1.0))

        print(f"Position Size Calculation:")
        print(f"  Pip Size:          {pip_size}")
        print(f"  Pip Value per Lot: ${pip_value_per_lot:.2f}")
        print(f"  Max Risk Amount:   ${risk_amount:.2f}")
        print(f"  SL Distance:       {risk_pips:.1f} pips")
        print(f"  Position Size:     {position_size:.2f} lots")
        print()

        # Calculate actual risk
        actual_risk = risk_pips * pip_value_per_lot * position_size
        actual_risk_pct = (actual_risk / balance) * 100

        print(f"Actual Risk:")
        print(f"  Risk Amount: ${actual_risk:.2f}")
        print(f"  Risk Percentage: {actual_risk_pct:.2f}%")
        print()

        # Calculate potential profit
        reward_pips = abs(tp - entry) / pip_size

        potential_profit = reward_pips * pip_value_per_lot * position_size
        rr_ratio = reward_pips / risk_pips

        print(f"Potential Reward:")
        print(f"  TP Distance: {reward_pips:.1f} pips")
        print(f"  Potential Profit: ${potential_profit:.2f}")
        print(f"  R:R Ratio: {rr_ratio:.2f}")

    print()
    print("=" * 70)
    print("COMPARISON: 0.1% vs 1% Risk")
    print("=" * 70)
    print()

    # Compare USDJPY with 0.1% vs 1%
    symbol = "USDJPY"
    entry, sl, tp = 158.228, 158.429, 157.832
    pip_size = pip_calculator.get_pip_size(symbol)
    risk_pips = abs(entry - sl) / pip_size
    pip_value_per_lot = pip_calculator.calculate_pip_value(symbol, 1.0)

    for risk_pct in [0.001, 0.01]:
        risk_amt = balance * risk_pct
        pos_size = calculate_position_size_manual(balance, risk_amt, risk_pips, pip_value_per_lot)
        pos_size = max(0.01, min(pos_size, 1.0))

        print(f"Risk {risk_pct * 100}%: {pos_size:.2f} lots (${risk_amt:.2f} risk)")

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    print(f"With 1% risk and ${balance:.0f} balance:")
    print(f"  - Risk per trade: ${balance * 0.01:.2f}")
    print(f"  - Expected lot sizes: 0.08 - 0.20 lots (depending on SL distance)")
    print(f"  - Much better than 0.01 lots with 0.1% risk!")
    print()


if __name__ == "__main__":
    try:
        test_lot_size_calculation()
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
