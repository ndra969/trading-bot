"""Analyze recent trading losses."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import asyncio
from datetime import datetime, timedelta
from trading_bot.data.database import get_session


async def check_recent_trades():
    """Check last 3 days of trades."""
    # Initialize database first
    from trading_bot.data.database import init_database
    import os

    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://trading_bot_dev_user:dev_password_123@localhost:5432/trading_bot_dev")
    init_database(db_url)

    async with get_session() as session:
        from sqlalchemy import text

        # Get last 3 days of trades
        three_days_ago = datetime.now() - timedelta(days=3)

        query = text(
            """
            SELECT
                symbol,
                position_type,
                entry_price,
                close_price,
                stop_loss,
                take_profit,
                current_pnl_usd as pnl,
                open_time,
                close_time,
                is_winner,
                confluence_score,
                breakeven_activated,
                trailing_activated
            FROM positions
            WHERE close_time IS NOT NULL
            AND close_time >= :days_ago
            ORDER BY close_time DESC
        """
        )

        result = await session.execute(query, {"days_ago": three_days_ago})
        trades = result.fetchall()

        print(f"Total trades (last 3 days): {len(trades)}")
        print()

        if len(trades) == 0:
            print("No closed trades found in last 3 days")
            return

        # Group by symbol
        by_symbol = {}
        wins = 0
        losses = 0
        total_pnl = 0

        for t in trades:
            sym = t[0]
            if sym not in by_symbol:
                by_symbol[sym] = {"trades": 0, "wins": 0, "pnl": 0}
            by_symbol[sym]["trades"] += 1
            by_symbol[sym]["pnl"] += (t[6] or 0)
            total_pnl += t[6] or 0
            if t[9]:
                wins += 1
                by_symbol[sym]["wins"] += 1
            else:
                losses += 1

        print("By Symbol:")
        for sym, data in sorted(by_symbol.items(), key=lambda x: x[1]["pnl"], reverse=True):
            winrate = (data["wins"] / data["trades"] * 100) if data["trades"] > 0 else 0
            print(
                f"  {sym}: {data['trades']} trades, {data['wins']}W/{data['trades']-data['wins']}L ({winrate:.0f}%), P&L: ${data['pnl']:.2f}"
            )

        print()
        winrate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        print(f"Overall: {wins}W/{losses}L ({winrate:.1f}% win rate)")
        print(f"Total P&L: ${total_pnl:.2f}")
        print()

        # Show recent losing trades
        print("=" * 70)
        print("RECENT LOSING TRADES:")
        print("=" * 70)
        print()

        loss_count = 0
        for t in trades:
            if not t[9]:  # is_winner = False
                loss_count += 1
                if loss_count > 10:  # Show max 10 losses
                    break

                print(f"{t[0]} {t[1]} | Confluence: {t[10]}%")
                print(f"  Entry: {t[2]:.5f}, Exit: {t[3]:.5f}")
                print(f"  SL: {t[4]:.5f}, TP: {t[5]:.5f}")
                print(f"  P&L: ${t[6]:.2f}")
                print(f"  Breakeven: {t[11]}, Trailing: {t[12]}")
                print()


asyncio.run(check_recent_trades())
