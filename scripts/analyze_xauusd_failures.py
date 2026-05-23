"""Analyze why XAUUSD positions failed."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///trading_bot.db")
if "postgresql+asyncpg://" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
elif "sqlite+aiosqlite://" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("sqlite+aiosqlite:///", "sqlite:///")


def analyze_xauusd_failures():
    """Analyze why XAUUSD positions failed."""
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        print("=" * 70)
        print("XAUUSD FAILURE ANALYSIS")
        print("=" * 70)
        print()

        # Get detailed position info
        query = text("""
            SELECT
                position_id,
                position_type,
                entry_price,
                stop_loss,
                take_profit,
                close_price,
                current_profit_pips,
                current_pnl_usd,
                open_time,
                close_time,
                is_winner,
                status,
                confluence_score
            FROM positions
            WHERE symbol = 'XAUUSD'
            ORDER BY open_time DESC
        """)

        result = session.execute(query)
        positions = result.fetchall()

        if not positions:
            print("[ERROR] No XAUUSD positions found!")
            return

        print(f"Total XAUUSD positions: {len(positions)}")
        print()

        # Analyze each position
        for i, pos in enumerate(positions, 1):
            print(f"{'=' * 70}")
            print(f"Position #{i}: {pos.position_type}")
            print(f"{'=' * 70}")

            # Calculate risk/reward
            if pos.position_type == 'BUY':
                risk_pips = (pos.entry_price - pos.stop_loss) / 0.01  # Gold pip = 0.01
                reward_pips = (pos.take_profit - pos.entry_price) / 0.01
                if pos.close_price:
                    actual_pips = (pos.close_price - pos.entry_price) / 0.01
            else:  # SELL
                risk_pips = (pos.stop_loss - pos.entry_price) / 0.01
                reward_pips = (pos.entry_price - pos.take_profit) / 0.01
                if pos.close_price:
                    actual_pips = (pos.entry_price - pos.close_price) / 0.01

            rr_ratio = reward_pips / risk_pips if risk_pips > 0 else 0

            print(f"Entry:    ${pos.entry_price:.2f}")
            print(f"SL:       ${pos.stop_loss:.2f} ({risk_pips:.1f} pips)")
            print(f"TP:       ${pos.take_profit:.2f} ({reward_pips:.1f} pips)")
            print(f"R:R Ratio: {rr_ratio:.2f}")
            print(f"Confluence: {pos.confluence_score:.1f}")
            print()

            if pos.close_price:
                print(f"Close:    ${pos.close_price:.2f}")
                print(f"Actual:   {actual_pips:.1f} pips (${pos.current_pnl_usd:.2f})")

                # Analyze why it hit SL
                if pos.current_pnl_usd < 0:
                    print()
                    print("[LOSS ANALYSIS]")
                    print("-" * 70)

                    # Check if R:R was too low
                    if rr_ratio < 2.0:
                        print(f"  - R:R ratio {rr_ratio:.2f} < 2.0 (TOO LOW!)")
                    else:
                        print(f"  - R:R ratio {rr_ratio:.2f} (OK)")

                    # Check confluence
                    if pos.confluence_score < 50:
                        print(f"  - Confluence {pos.confluence_score:.1f} < 50 (TOO LOW!)")
                    elif pos.confluence_score < 65:
                        print(f"  - Confluence {pos.confluence_score:.1f} (MODERATE)")
                    else:
                        print(f"  - Confluence {pos.confluence_score:.1f} (GOOD)")

                    # Check if position hit max drawdown
                    print(f"  - Max loss: ${abs(pos.current_pnl_usd):.2f}")

                    # Check if SL was too tight
                    if risk_pips < 100:
                        print(f"  - SL {risk_pips:.0f} pips (TOO TIGHT for Gold!)")
                        print(f"    Gold volatility needs 200-300 pips SL minimum")
                    elif risk_pips < 200:
                        print(f"  - SL {risk_pips:.0f} pips (STILL TIGHT)")
                    else:
                        print(f"  - SL {risk_pips:.0f} pips (OK)")

                print()

            print(f"Opened:   {pos.open_time}")
            if pos.close_time:
                duration = (pos.close_time - pos.open_time).total_seconds() / 60
                print(f"Closed:   {pos.close_time}")
                print(f"Duration: {duration:.1f} minutes")

            print()

        print("=" * 70)
        print("SUMMARY & RECOMMENDATIONS")
        print("=" * 70)
        print()

        # Calculate stats
        total_pnl = sum(p.current_pnl_usd for p in positions)
        avg_rr = 0
        count_rr = 0
        tight_sl = sum(1 for p in positions if p.position_type == 'BUY' and (p.entry_price - p.stop_loss) / 0.01 < 200)
        tight_sl += sum(1 for p in positions if p.position_type == 'SELL' and (p.stop_loss - p.entry_price) / 0.01 < 200)

        for p in positions:
            if p.position_type == 'BUY':
                risk = (p.entry_price - p.stop_loss) / 0.01
                reward = (p.take_profit - p.entry_price) / 0.01
            else:
                risk = (p.stop_loss - p.entry_price) / 0.01
                reward = (p.entry_price - p.take_profit) / 0.01

            if risk > 0:
                rr = reward / risk
                avg_rr += rr
                count_rr += 1

        avg_rr = avg_rr / count_rr if count_rr > 0 else 0

        print(f"Total P&L:        ${total_pnl:.2f}")
        print(f"Win Rate:          {sum(1 for p in positions if p.is_winner)}/{len(positions)}")
        print(f"Avg R:R Ratio:     {avg_rr:.2f}")
        print(f"Tight SL Count:    {tight_sl}/{len(positions)}")
        print()

        print("[ROOT CAUSE ANALYSIS]")
        print()

        if tight_sl == len(positions):
            print("1. STOP LOSS TOO TIGHT!")
            print("   - Gold needs 200-500 pips SL minimum")
            print("   - Current SL: 100-150 pips (WAY TOO SMALL)")
            print("   - Gold volatility: $50-$100 per day = 500-1000 pips")
            print()

        if avg_rr < 2.0:
            print("2. RISK:REWARD RATIO TOO LOW!")
            print(f"   - Average R:R: {avg_rr:.2f}")
            print("   - Need at least 2:1 or 3:1 for Gold")
            print()

        print("[RECOMMENDATIONS]")
        print()
        print("Option 1: WIDER STOPS (RECOMMENDED)")
        print("  - Increase SL to 300-500 pips for Gold")
        print("  - Adjust lot size to maintain same $ risk")
        print("  - This will give room for Gold volatility")
        print()
        print("Option 2: REDUCE FREQUENCY")
        print("  - Wait for confluence >= 85 (only BEST zones)")
        print("  - Trade only H4/D1 timeframes (less noise)")
        print("  - This will reduce but improve quality")
        print()
        print("Option 3: DISABLE XAUUSD (CONSERVATIVE)")
        print("  - Focus on forex pairs which are more stable")
        print("  - Re-enable XAUUSD when strategy is more robust")
        print()

        print("=" * 70)


if __name__ == "__main__":
    try:
        analyze_xauusd_failures()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
