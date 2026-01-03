import asyncio
import logging

from trading_bot.position.position_manager import PositionManager
from trading_bot.strategies.models import SignalDirection, TradingSignal
from trading_bot.utils.logger import setup_logger

# Setup logging
setup_logger()
logger = logging.getLogger(__name__)


async def verify_automation():
    print("\n--- STARTING AUTOMATION VERIFICATION (TDD RED PHASE) ---")

    # 1. Setup Config with TIGHT triggers for easy testing
    mock_config = {
        "position_manager": {"max_positions_per_symbol": 5},
        "trade_management": {
            "defaults": {  # Fallback
                "breakeven": {"enabled": True, "trigger_pips": 10.0, "offset_pips": 2.0},
                "trailing_stop": {"enabled": True, "activation_pips": 20.0, "limit_pips": 10.0},
            },
            "overrides": {
                "commodities": {  # Gold (XAUUSD)
                    "breakeven": {"trigger_pips": 10.0, "offset_pips": 2.0},  # 10 pips = $1.00
                    "trailing_stop": {
                        "activation_pips": 20.0,
                        "limit_pips": 10.0,
                    },  # 20 pips = $2.00
                }
            },
        },
    }

    # 2. Initialize Position Manager
    pm = PositionManager(mock_config)
    print("PositionManager initialized.")

    # 3. Create a Mock Signal (XAUUSD BUY)
    # Entry: 2000.00
    # SL: 1990.00 (100 pips risk)
    # TP: 2050.00
    entry_price = 2000.00
    signal = TradingSignal(
        signal_id="verify_test_signal",
        symbol="XAUUSD",
        direction=SignalDirection.BUY,
        entry_price=entry_price,
        stop_loss=1990.00,
        take_profit=2050.00,
        confluence_score=80.0,
        risk_reward_ratio=5.0,  # 50 pips reward / 10 pips risk (using mock values)
        timeframe="H1",
        strategy_scores={},
    )

    # 4. Create Position
    position = pm.create_position_from_signal(signal, volume=0.1)
    pm.open_position(position.position_id)
    print(f"Position Created: {position.position_id} @ {entry_price}")
    print(f"Initial SL: {position.stop_loss}")

    pip_size = position.pip_size  # Likely 0.1 or 0.01 depending on broker mock
    print(f"Pip Size detected: {pip_size}")

    # 5. Simulate Price Move 1: Trigger Breakeven
    # Target: +10 pips ($1.00 if pip=0.1) -> Price 2001.00
    # If pip=0.01, +10 pips = $0.10 -> Price 2000.10
    # Let's assume standard gold 0.1 pip. +10 pips = +$1.00.

    # Move price to Entry + 12 pips (Clear BE trigger)
    be_trigger_price = entry_price + (12.0 * pip_size)
    print(f"\n--- Simulating Price Move to {be_trigger_price} (+12 pips) ---")

    # Update Position (This SHOULD trigger automation if integrated)
    pm.update_all_positions({"XAUUSD": be_trigger_price})
    pm.check_and_close_positions(
        {"XAUUSD": be_trigger_price}
    )  # This triggers the update logic loop

    # ASSERT BREAKEVEN
    expected_sl = entry_price + (2.0 * pip_size)  # Entry + 2 pips buffer
    current_sl = position.stop_loss

    print(f"Current SL: {current_sl:.5f}")
    if abs(current_sl - expected_sl) < 0.001:
        print("✅ SUCCESS: SL moved to Breakeven")
    elif current_sl == 1990.00:
        print("❌ FAILURE: SL did not move (Logic not connected)")
    else:
        print(f"❌ FAILURE: SL moved to unexpected level: {current_sl}")

    # 6. Simulate Price Move 2: Trigger Trailing
    # Activation: +20 pips. We move to +25 pips.
    # Trail Distance: 10 pips.
    # New Price: Entry + 25 pips.
    # Expected SL: Price - 10 pips = Entry + 15 pips.

    trail_trigger_price = entry_price + (25.0 * pip_size)
    print(f"\n--- Simulating Price Move to {trail_trigger_price} (+25 pips) ---")

    pm.update_all_positions({"XAUUSD": trail_trigger_price})
    pm.check_and_close_positions({"XAUUSD": trail_trigger_price})

    expected_trail_sl = trail_trigger_price - (10.0 * pip_size)
    current_sl = position.stop_loss

    print(f"Current SL: {current_sl:.5f}")
    if abs(current_sl - expected_trail_sl) < 0.001:
        print("✅ SUCCESS: SL Trailed correctly")
    elif current_sl == 1990.00:
        print("❌ FAILURE: SL still at initial (Logic not connected)")
    elif abs(current_sl - (entry_price + 2.0 * pip_size)) < 0.001:
        print("❌ FAILURE: SL stuck at Breakeven (Trailing not connected)")
    else:
        print(f"❌ FAILURE: SL at unexpected level: {current_sl}")


if __name__ == "__main__":
    asyncio.run(verify_automation())
