"""
Data Downloader for Backtesting.

Fetches historical OHLCV data from MT5 and saves it to CSV.
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent / "src")
sys.path.append(project_root)

# Configure logging
from trading_bot.connectors.data_manager import DataManager
from trading_bot.connectors.mt5_connector import MT5Connector
from trading_bot.connectors.symbol_manager import SymbolManager
from trading_bot.utils.logger import get_logger

logger = get_logger("download_data")


async def download_data(symbol: str, timeframe: str, days: int, output_dir: str):
    """
    Download data from MT5 and save to CSV.
    """
    connector = MT5Connector()

    try:
        # Initialize connection
        if not connector.initialize():
            logger.error("Failed to connect to MT5")
            return

        symbol_manager = SymbolManager(connector)
        data_manager = DataManager(connector, symbol_manager)

        # Validate symbol
        if not symbol_manager.is_symbol_available(symbol):
            logger.error(f"Symbol {symbol} not found in MT5")
            return

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        logger.info(f"Downloading {symbol} {timeframe} data from {start_date} to {end_date}...")

        # Fetch data
        df = data_manager.get_ohlcv_range(
            symbol=symbol, timeframe=timeframe, date_from=start_date, date_to=end_date
        )

        if df is None or df.empty:
            logger.error("No data received")
            return

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save to CSV
        filename = f"{symbol}_{timeframe}.csv"
        file_path = output_path / filename

        # Reset index to save timestamp as column
        df.reset_index().to_csv(file_path, index=False)

        logger.info(f"Successfully saved {len(df)} rows to {file_path}")
        logger.info(f"Date range: {df.index[0]} to {df.index[-1]}")

    except Exception as e:
        logger.error(f"Error downloading data: {e}")
    finally:
        connector.shutdown()


def main():
    parser = argparse.ArgumentParser(description="Download MT5 historical data for backtesting")
    parser.add_argument("--symbol", type=str, required=True, help="Trading symbol (e.g., EURUSD)")
    parser.add_argument(
        "--timeframe", type=str, default="H1", help="Timeframe (M1, M5, M15, M30, H1, H4, D1)"
    )
    parser.add_argument(
        "--days", type=int, default=30, help="Number of days of history to download"
    )
    parser.add_argument("--output", type=str, default="data/backtest", help="Output directory")

    args = parser.parse_args()

    # Run async function
    asyncio.run(download_data(args.symbol, args.timeframe, args.days, args.output))


if __name__ == "__main__":
    main()
