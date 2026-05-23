"""
Verify XAGUSD (Silver) symbol specifications from MT5.

This script checks the actual contract specifications to fix the pip value bug.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import MetaTrader5 as mt5
    from trading_bot.connectors.symbol_mapper import SymbolMapper
    from trading_bot.position.pip_calculator import PipCalculator
except ImportError as e:
    print(f"Error importing: {e}")
    print("Make sure MetaTrader5 is installed: pip install MetaTrader5")
    sys.exit(1)


def verify_symbol_specs(symbol: str):
    """Verify symbol specifications from MT5."""
    print(f"\n{'='*60}")
    print(f"Verifying Symbol: {symbol}")
    print(f"{'='*60}\n")
    
    # Initialize MT5
    if not mt5.initialize():
        print(f"❌ MT5 initialization failed: {mt5.last_error()}")
        return
    
    try:
        # Get symbol info
        info = mt5.symbol_info(symbol)
        if info is None:
            print(f"❌ Symbol {symbol} not found in MT5")
            return
        
        print("📊 MT5 Symbol Specifications:")
        print(f"  Symbol: {info.name}")
        print(f"  Description: {info.description}")
        print(f"  Contract size: {info.trade_contract_size}")
        print(f"  Digits: {info.digits}")
        print(f"  Point: {info.point}")
        print(f"  Tick size: {info.trade_tick_size}")
        print(f"  Tick value: {info.trade_tick_value}")
        print(f"  Tick value profit: {info.trade_tick_value_profit}")
        print(f"  Tick value loss: {info.trade_tick_value_loss}")
        print(f"  Min volume: {info.volume_min}")
        print(f"  Max volume: {info.volume_max}")
        print(f"  Volume step: {info.volume_step}")
        
        # Calculate pip size based on digits
        if info.digits >= 3:
            pip_size = 0.01  # 2 decimal places for price (e.g., 82.03)
        elif info.digits == 2:
            pip_size = 0.01
        else:
            pip_size = 0.1
        
        # Calculate pip value per lot
        # Pip value = (tick value / tick size) * pip size
        pip_value_per_lot = (info.trade_tick_value / info.trade_tick_size) * pip_size
        
        print(f"\n📐 Calculated Values:")
        print(f"  Pip size: {pip_size}")
        print(f"  Pip value per 1.0 lot: ${pip_value_per_lot:.2f}")
        print(f"  Pip value per 0.01 lot: ${pip_value_per_lot * 0.01:.2f}")
        print(f"  Pip value per 0.1 lot: ${pip_value_per_lot * 0.1:.2f}")
        
        # Compare with current config
        print(f"\n🔍 Current Bot Configuration:")
        mapper = SymbolMapper()
        calc = PipCalculator()
        
        current_pip_size = mapper.get_pip_size("XAGUSD")
        current_pip_value_per_lot = mapper.get_pip_value_per_lot("XAGUSD")
        current_pip_value_001 = calc.calculate_pip_value("XAGUSD", 0.01)
        
        print(f"  Pip size (config): {current_pip_size}")
        print(f"  Pip value per lot (config): ${current_pip_value_per_lot:.2f}")
        print(f"  Pip value per 0.01 lot (config): ${current_pip_value_001:.2f}")
        
        # Check if there's a mismatch
        print(f"\n⚠️  Mismatch Detection:")
        pip_size_match = abs(current_pip_size - pip_size) < 0.001
        pip_value_match = abs(current_pip_value_per_lot - pip_value_per_lot) < 1.0
        
        if pip_size_match:
            print(f"  ✅ Pip size: MATCH ({current_pip_size} == {pip_size})")
        else:
            print(f"  ❌ Pip size: MISMATCH ({current_pip_size} != {pip_size})")
            print(f"     Config should be: {pip_size}")
        
        if pip_value_match:
            print(f"  ✅ Pip value per lot: MATCH (${current_pip_value_per_lot:.2f} ≈ ${pip_value_per_lot:.2f})")
        else:
            print(f"  ❌ Pip value per lot: MISMATCH (${current_pip_value_per_lot:.2f} != ${pip_value_per_lot:.2f})")
            print(f"     Config should be: {pip_value_per_lot:.2f}")
        
        # Test with actual position data
        print(f"\n🧪 Test with Actual Position:")
        entry = 82.037
        sl = 77.990
        lot = 0.01
        
        distance = entry - sl
        pips_mt5 = distance / pip_size
        pips_config = distance / current_pip_size
        
        loss_mt5 = pips_mt5 * (pip_value_per_lot * lot)
        loss_config = pips_config * current_pip_value_001
        
        print(f"  Entry: {entry}")
        print(f"  SL: {sl}")
        print(f"  Distance: {distance:.3f}")
        print(f"  Lot: {lot}")
        print(f"\n  Using MT5 specs:")
        print(f"    Pips: {pips_mt5:.1f}")
        print(f"    Expected SL loss: ${loss_mt5:.2f}")
        print(f"\n  Using current config:")
        print(f"    Pips: {pips_config:.1f}")
        print(f"    Expected SL loss: ${loss_config:.2f}")
        print(f"\n  Difference: ${abs(loss_mt5 - loss_config):.2f} ({abs(loss_mt5 - loss_config) / loss_mt5 * 100:.1f}%)")
        
        if abs(loss_mt5 - loss_config) > 1.0:
            print(f"\n  🔴 CRITICAL: Loss calculation difference > $1!")
            print(f"     This will cause incorrect risk management!")
        
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    # Check both XAGUSDc (Exness Cent) and XAGUSDm (Exness Standard)
    symbols_to_check = ["XAGUSDc", "XAGUSDm", "XAGUSD"]
    
    for symbol in symbols_to_check:
        try:
            verify_symbol_specs(symbol)
        except Exception as e:
            print(f"\n❌ Error checking {symbol}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("Verification complete!")
    print(f"{'='*60}\n")
