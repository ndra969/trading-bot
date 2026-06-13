"""Data downloader for backtesting — ported 2026-06-13 to the trading_worker layout.

Fetches historical OHLCV from the running (logged-in) MT5 terminal and writes
CSVs that scripts/run_backtest.py + run_mtf_backtest.py read.

    uv run python scripts/download_data.py --symbol EURUSDc --timeframe H1 --days 30
    # pull everything the exit-payoff / enhancement sweeps need in one go:
    uv run python scripts/download_data.py \
        --symbol EURUSDc,USDJPYc,XAUUSDc,BTCUSDc --timeframe H1,M30 --days 45

Requires the MT5 terminal installed and LOGGED IN (Windows). Symbols must be the
BROKER symbols (e.g. exness_cent uses the `c` suffix: EURUSDc), matching the
backtest CSV filenames `{symbol}_{timeframe}.csv`.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from trading_core.utils.logger import get_logger
from trading_worker.connectors.data_manager import DataManager
from trading_worker.connectors.mt5_connector import MT5Connector
from trading_worker.connectors.symbol_manager import SymbolManager

logger = get_logger("download_data")


def _enable_symbol(symbol_manager: SymbolManager, symbol: str) -> bool:
    """Validate + enable a symbol in Market Watch (required before data pull)."""
    try:
        symbol_manager.validate_symbol(symbol, auto_enable=True)
        return True
    except Exception as e:
        logger.warning(f"validate_symbol({symbol}) failed: {e}; trying select_symbol...")
        if symbol_manager.select_symbol(symbol, enable=True):
            return True
        logger.error(f"Symbol {symbol} not available / cannot be enabled in MT5")
        return False


def _save(df, output_dir: str, symbol: str, timeframe: str) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    file_path = output_path / f"{symbol}_{timeframe}.csv"
    df.reset_index().to_csv(file_path, index=False)
    logger.info(f"Saved {len(df)} rows -> {file_path} (range: {df.index[0]} to {df.index[-1]})")


async def download_data(
    symbols: list[str], timeframes: list[str], days: int, output_dir: str
) -> None:
    """Download each symbol×timeframe series from MT5 and save to CSV."""
    connector = MT5Connector()
    try:
        if not connector.initialize():
            logger.error("Failed to connect to MT5 — is the terminal running and logged in?")
            return

        symbol_manager = SymbolManager(connector)
        data_manager = DataManager(connector, symbol_manager)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        ok, failed = 0, 0
        for symbol in symbols:
            if not _enable_symbol(symbol_manager, symbol):
                failed += 1
                continue
            for timeframe in timeframes:
                logger.info(f"Downloading {symbol} {timeframe} ({start_date} -> {end_date})...")
                try:
                    df = data_manager.get_ohlcv_range(
                        symbol=symbol,
                        timeframe=timeframe,
                        date_from=start_date,
                        date_to=end_date,
                    )
                except Exception as e:
                    logger.error(f"{symbol} {timeframe}: download failed: {e}")
                    failed += 1
                    continue
                if df is None or df.empty:
                    logger.error(f"{symbol} {timeframe}: no data received")
                    failed += 1
                    continue
                _save(df, output_dir, symbol, timeframe)
                ok += 1

        logger.info(f"Done: {ok} series saved, {failed} failed.")
    except Exception as e:
        logger.error(f"Error downloading data: {e}")
    finally:
        connector.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="Download MT5 historical data for backtesting")
    parser.add_argument(
        "--symbol",
        type=str,
        required=True,
        help="Broker symbol(s), comma-separated (e.g. EURUSDc,XAUUSDc)",
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        default="H1",
        help="Timeframe(s), comma-separated (M1,M5,M15,M30,H1,H4,D1)",
    )
    parser.add_argument("--days", type=int, default=30, help="Days of history to download")
    parser.add_argument("--output", type=str, default="data/backtest", help="Output directory")
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbol.split(",") if s.strip()]
    timeframes = [t.strip() for t in args.timeframe.split(",") if t.strip()]

    asyncio.run(download_data(symbols, timeframes, args.days, args.output))


if __name__ == "__main__":
    main()
