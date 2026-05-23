"""Check XAUUSD zones and positions in database."""
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
from sqlalchemy import create_engine, select, and_, text
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///trading_bot.db")

# Convert async URL to sync for simple script
if "postgresql+asyncpg://" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
elif "sqlite+aiosqlite://" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("sqlite+aiosqlite:///", "sqlite:///")


def check_xauusd_data():
    """Check XAUUSD zones and positions."""
    # Create sync engine
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        print("=" * 70)
        print("XAUUSD ANALYSIS REPORT")
        print("=" * 70)
        print()

        # 1. Check zones
        print("1. XAUUSD ZONES ANALYSIS")
        print("-" * 70)

        # Check zones with strength >= 75
        zone_query = text("""
            SELECT zone_id, zone_type, strength,
                   high_price, low_price,
                   created_at, is_active
            FROM supply_demand_zones
            WHERE symbol = 'XAUUSD'
            ORDER BY strength DESC
            LIMIT 20
        """)

        result = session.execute(zone_query)
        zones = result.fetchall()

        if zones:
            print(f"[OK] Total XAUUSD zones found: {len(zones)}")
            print()

            # Count by strength ranges
            high_strength = sum(1 for z in zones if z.strength >= 75)
            med_strength = sum(1 for z in zones if 60 <= z.strength < 75)
            low_strength = sum(1 for z in zones if z.strength < 60)

            print(f"Strength Distribution:")
            print(f"  >=75 (current threshold): {high_strength} zones")
            print(f"  60-74 (recommended):     {med_strength} zones")
            print(f"  <60 (weak):              {low_strength} zones")
            print()

            if zones:
                strengths = [z.strength for z in zones]
                print(f"Statistics:")
                print(f"  Highest:   {max(strengths):.1f}")
                print(f"  Lowest:    {min(strengths):.1f}")
                print(f"  Average:   {sum(strengths)/len(strengths):.1f}")
                print()

            print("Top 10 XAUUSD Zones:")
            for i, zone in enumerate(zones[:10], 1):
                status = "[ACTIVE]" if zone.is_active else "[INACTIVE]"
                print(f"{i:2d}. {status} {zone.zone_type:8s} | Strength: {zone.strength:5.1f} | "
                      f"Range: {zone.low_price:.2f} - {zone.high_price:.2f}")
        else:
            print("[ERROR] NO XAUUSD ZONES FOUND IN DATABASE!")
            print("   This is the MAIN PROBLEM - no zones = no signals = no trades!")

        print()
        print()

        # 2. Check positions
        print("2. XAUUSD POSITIONS HISTORY")
        print("-" * 70)

        pos_query = text("""
            SELECT position_id, symbol, position_type, status,
                   entry_price, stop_loss, take_profit,
                   open_time, close_time,
                   current_profit_pips, current_pnl_usd,
                   is_winner
            FROM positions
            WHERE symbol = 'XAUUSD'
            ORDER BY open_time DESC
            LIMIT 10
        """)

        result = session.execute(pos_query)
        positions = result.fetchall()

        if positions:
            print(f"[OK] Total XAUUSD positions: {len(positions)}")
            print()

            # Count by status
            closed = sum(1 for p in positions if p.status == 'CLOSED')
            open_pos = sum(1 for p in positions if p.status == 'OPEN')
            pending = sum(1 for p in positions if p.status == 'PENDING')

            print(f"Status Distribution:")
            print(f"  CLOSED:  {closed} positions")
            print(f"  OPEN:    {open_pos} positions")
            print(f"  PENDING: {pending} positions")
            print()

            if closed > 0:
                winners = sum(1 for p in positions if p.is_winner == True)
                win_rate = (winners / closed * 100) if closed > 0 else 0
                print(f"Performance:")
                print(f"  Winners:  {winners}/{closed}")
                print(f"  Win Rate: {win_rate:.1f}%")
            print()

            print("Recent Positions:")
            for i, pos in enumerate(positions[:5], 1):
                status_icon = {"OPEN": "[OPEN]", "CLOSED": "[CLOSED]", "PENDING": "[PENDING]"}.get(pos.status, "[?]")
                result_icon = "[WIN]" if pos.is_winner else "[LOSS]" if pos.is_winner is not None else "[?]"
                print(f"{i}. {status_icon} {pos.position_type} {pos.status}")
                print(f"   Entry: {pos.entry_price:.2f} | SL: {pos.stop_loss:.2f} | TP: {pos.take_profit:.2f}")
                print(f"   P&L: {pos.current_profit_pips:.1f} pips (${pos.current_pnl_usd:.2f}) {result_icon}")
                if pos.open_time:
                    print(f"   Opened: {pos.open_time}")
        else:
            print("[ERROR] NO XAUUSD POSITIONS FOUND!")
            print("   This confirms XAUUSD hasn't opened any positions yet.")

        print()
        print()

        # 3. Check signals
        print("3. XAUUSD SIGNALS ANALYSIS")
        print("-" * 70)

        # Check if there's a signals table or look at recent signals
        signal_query = text("""
            SELECT COUNT(*) as total_count
            FROM signals
            WHERE symbol = 'XAUUSD'
        """)

        try:
            result = session.execute(signal_query)
            signal_count = result.fetchone()[0]

            print(f"[OK] Total XAUUSD signals generated: {signal_count}")
        except Exception as e:
            print(f"[WARNING] Could not check signals table (may not exist): {e}")

        print()
        print("=" * 70)
        print("RECOMMENDATION:")
        print("=" * 70)

        if not zones or len(zones) == 0:
            print()
            print("[CRITICAL] PRIMARY ISSUE: NO XAUUSD ZONES DETECTED")
            print()
            print("Action Required:")
            print("1. Check if XAUUSD is being analyzed by the bot")
            print("2. Check logs for 'XAUUSD' analysis errors")
            print("3. Verify XAUUSD data is being downloaded from MT5")
            print("4. Lower min_zone_strength from 75 to 60-65")
            print()
        elif high_strength == 0:
            print()
            print(f"[ISSUE] NO ZONES WITH STRENGTH >= 75 (current threshold)")
            print(f"        But {med_strength} zones have strength 60-74")
            print()
            print("Action Required:")
            print("1. Lower min_zone_strength from 75 to 60 in active_symbols.yaml")
            print("2. This will allow {med_strength} additional zones to be used")
            print()
        else:
            print()
            print(f"[OK] XAUUSD has {high_strength} zones with strength >= 75")
            print(f"     Issue must be elsewhere (risk management, position limits, etc.)")
            print()

        print("=" * 70)


if __name__ == "__main__":
    try:
        check_xauusd_data()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
