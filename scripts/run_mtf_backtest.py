"""
Multi-Timeframe Backtest Script.

Strategy:
- Zone Detection: H1 (strong, tested zones)
- Entry Confirmation: M30 (precise price action)

This follows the intraday trading approach where higher TF provides
context/zones and lower TF provides entry timing.
"""

import argparse
import asyncio
import sys
from pathlib import Path

import pandas as pd

# Add project root to Python path
project_root = str(Path(__file__).parent.parent / "src")
sys.path.append(project_root)

from run_backtest import BacktestEngine, MockTrade
from trading_bot.strategies.foundation.foundation_engine import FoundationEngine
from trading_bot.strategies.models import SignalDirection
from trading_bot.utils.logger import get_logger

logger = get_logger("mtf_backtest")


class MTFBacktestEngine(BacktestEngine):
    """Multi-Timeframe Backtest Engine."""

    def __init__(
        self, symbol: str, zone_tf: str, entry_tf: str, zone_data_path: str, entry_data_path: str
    ):
        """
        Initialize MTF backtest.

        Args:
            symbol: Trading symbol
            zone_tf: Higher timeframe for zone detection (e.g. 'H1')
            entry_tf: Lower timeframe for entry signals (e.g. 'M30')
            zone_data_path: Path to zone TF data CSV
            entry_data_path: Path to entry TF data CSV
        """
        self.symbol = symbol
        self.zone_tf = zone_tf
        self.entry_tf = entry_tf

        # Load configuration
        self.config = self._load_config()

        # Load both timeframe data
        self.zone_data = self._load_data_from_path(zone_data_path)
        self.entry_data = self._load_data_from_path(entry_data_path)

        logger.info(f"Loaded {len(self.zone_data)} {zone_tf} candles for zone detection")
        logger.info(f"Loaded {len(self.entry_data)} {entry_tf} candles for entry signals")

        # Initialize strategy
        self.engine = FoundationEngine(config=self.config, use_database=False)

        # State
        self.trades: list[MockTrade] = []
        self.active_trade: MockTrade | None = None
        self.spread = 0.0001

    def _load_data_from_path(self, path: str) -> pd.DataFrame:
        """Load CSV data from path."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Data file not found: {p}")

        df = pd.read_csv(p)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)
        return df.sort_index()

    async def run(self):
        """Run MTF backtest simulation."""
        logger.info(
            f"Starting MTF Backtest: {self.symbol} (Zone: {self.zone_tf}, Entry: {self.entry_tf})"
        )

        # Step 1: Detect zones on higher TF using ALL data
        logger.info(f"Detecting zones on {self.zone_tf}...")
        zones = await self.engine.analyze_symbol(self.symbol, self.zone_data, self.zone_tf)
        logger.info(f"Detected {len(zones)} zones on {self.zone_tf}")

        if not zones:
            logger.warning("No zones detected. Backtest complete.")
            self._print_report()
            return

        # Step 2: Walk through entry TF candles to find entry signals
        logger.info(f"Scanning {self.entry_tf} candles for entry signals...")

        total_candles = len(self.entry_data)
        lookback = 200  # Need history for indicators

        for i in range(lookback, total_candles):
            current_time = self.entry_data.index[i]
            current_candle = self.entry_data.iloc[i]
            current_price = float(current_candle["close"])

            # Get historical context
            historical_data = self.entry_data.iloc[: i + 1].copy()

            # Progress indicator
            if i % 100 == 0:
                print(f"\rProcessed {i}/{total_candles} candles...", end="", flush=True)

            # Check and update active trade (if any)
            if self.active_trade:
                self._update_trade(current_candle, current_time)
                if not self.active_trade:  # Trade closed
                    continue

            # Only open new trade if no active trade
            if not self.active_trade:
                # Get zones that are relevant at this time
                active_zones = [z for z in zones if self._is_zone_active(z, current_time)]

                if not active_zones:
                    continue

                # Check if price is at any zone
                for zone in active_zones:
                    if self._is_price_at_zone(current_price, zone):
                        # Generate signal using ENTRY TF data
                        result = await self.engine._create_signal_from_zone(
                            self.symbol, zone, current_price, self.entry_tf, historical_data
                        )

                        if result:
                            self._open_trade(result, current_time)
                            break  # Only one trade at a time

        print("\nBacktest Complete.\n")
        self._print_report()

    def _is_zone_active(self, zone, current_time):
        """Check if zone is still valid at current time."""
        # Simple heuristic: zones expire after 30 days
        zone_age_hours = (current_time - zone.first_detected).total_seconds() / 3600
        return zone_age_hours < 720  # 30 days

    def _is_price_at_zone(self, price, zone):
        """Check if price is at zone."""
        zone_size = zone.upper_bound - zone.lower_bound
        tolerance = zone_size * 0.2
        return zone.lower_bound - tolerance <= price <= zone.upper_bound + tolerance

    def _update_trade(self, current_candle, current_time):
        """Update active trade with current candle (check SL/TP, BE, TS)."""
        if not self.active_trade:
            return

        high = float(current_candle["high"])
        low = float(current_candle["low"])

        # Determine pip size
        pip_size = 0.1 if self.active_trade.entry_price > 500 else 0.0001

        # Get trade management config
        tm_config = self.config.get("trade_management", {})
        asset_class = "commodities" if "XAU" in self.symbol.upper() else "defaults"

        defaults = tm_config.get("defaults", {})
        overrides = tm_config.get("overrides", {}).get(asset_class, {})

        be_settings = defaults.get("breakeven", {}).copy()
        be_settings.update(overrides.get("breakeven", {}))

        ts_settings = defaults.get("trailing_stop", {}).copy()
        ts_settings.update(overrides.get("trailing_stop", {}))

        be_enabled = be_settings.get("enabled", True)
        be_trigger = be_settings.get("trigger_pips", 20.0)
        be_offset = be_settings.get("offset_pips", 2.0)

        ts_enabled = ts_settings.get("enabled", True)
        ts_activation = ts_settings.get("activation_pips", 30.0)
        ts_limit = ts_settings.get("limit_pips", 10.0)

        # Check SL/TP
        if self.active_trade.direction == SignalDirection.BUY:
            if low <= self.active_trade.stop_loss:
                self._close_trade(self.active_trade.stop_loss, current_time, "SL")
                return
            if high >= self.active_trade.take_profit:
                self._close_trade(self.active_trade.take_profit, current_time, "TP")
                return

            # Breakeven & Trailing
            current_profit_pips = (high - self.active_trade.entry_price) / pip_size

            if be_enabled:
                be_price = self.active_trade.entry_price + (be_offset * pip_size)
                if current_profit_pips >= be_trigger and self.active_trade.stop_loss < be_price:
                    self.active_trade.stop_loss = be_price

            if ts_enabled and current_profit_pips >= ts_activation:
                potential_sl = high - (ts_limit * pip_size)
                if potential_sl > self.active_trade.stop_loss:
                    self.active_trade.stop_loss = potential_sl
        else:  # SELL
            if high >= self.active_trade.stop_loss:
                self._close_trade(self.active_trade.stop_loss, current_time, "SL")
                return
            if low <= self.active_trade.take_profit:
                self._close_trade(self.active_trade.take_profit, current_time, "TP")
                return

            # Breakeven & Trailing
            current_profit_pips = (self.active_trade.entry_price - low) / pip_size

            if be_enabled:
                be_price = self.active_trade.entry_price - (be_offset * pip_size)
                if current_profit_pips >= be_trigger and self.active_trade.stop_loss > be_price:
                    self.active_trade.stop_loss = be_price

            if ts_enabled and current_profit_pips >= ts_activation:
                potential_sl = low + (ts_limit * pip_size)
                if potential_sl < self.active_trade.stop_loss:
                    self.active_trade.stop_loss = potential_sl

    def _open_trade(self, signal, time):
        """Open new trade from signal."""
        trade = MockTrade(
            symbol=self.symbol,
            direction=signal.direction,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            entry_time=time,
        )
        self.active_trade = trade
        self.trades.append(trade)
        logger.info(
            f"OPEN {signal.direction.value} @ {signal.entry_price:.5f} [SL: {signal.stop_loss:.5f}, TP: {signal.take_profit:.5f}] at {time}"
        )

    def _close_trade(self, price, time, reason):
        """Close active trade."""
        if not self.active_trade:
            return

        self.active_trade.is_open = False
        self.active_trade.exit_price = price
        self.active_trade.exit_time = time
        self.active_trade.exit_reason = reason

        logger.info(
            f"CLOSE {self.active_trade.direction.value} ({reason}) @ {price:.5f} | R: {self.active_trade.r_multiple:.2f}"
        )
        self.active_trade = None

    def _print_report(self):
        """Print backtest report."""
        if not self.trades:
            print("\nNo trades generated.")
            return

        completed = [t for t in self.trades if not t.is_open]
        if not completed:
            print("\nNo completed trades.")
            return

        wins = [t for t in completed if t.r_multiple > 0]
        losses = [t for t in completed if t.r_multiple <= 0]

        win_rate = len(wins) / len(completed) * 100
        total_r = sum(t.r_multiple for t in completed)
        total_pips = sum(t.pips for t in completed)
        best = max((t.r_multiple for t in completed), default=0)
        worst = min((t.r_multiple for t in completed), default=0)

        print("\n" + "=" * 40)
        print(f"MTF BACKTEST REPORT: {self.symbol}")
        print(f"Zone TF: {self.zone_tf} | Entry TF: {self.entry_tf}")
        print("=" * 40)
        print(f"Total Trades:     {len(completed)}")
        print(f"Wins:             {len(wins)}")
        print(f"Losses:           {len(losses)}")
        print(f"Win Rate:         {win_rate:.2f}%")
        print("-" * 20)
        print(f"Total Return (R): {total_r:.2f}R")
        print(f"Total Pips:       {total_pips:.1f} pips")
        print(f"Best Trade:       {best:.2f}R")
        print(f"Worst Trade:      {worst:.2f}R")
        print("=" * 40)

        print("\nTRADE HISTORY:")
        print(
            f"{'ID':<4} | {'Type':<4} | {'Entry':<10} | {'SL':<10} | {'TP':<10} | {'Pips':<6} | {'Result':<6}"
        )
        print("-" * 70)

        for i, t in enumerate(completed, 1):
            print(
                f"{i:<4} | {t.direction.value:<4} | {t.entry_price:<10.5f} | "
                + f"{t.stop_loss:<10.5f} | {t.take_profit:<10.5f} | {t.pips:<6.1f} | {t.r_multiple:+.2f}R"
            )
        print("-" * 70)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Multi-Timeframe Backtest")
    parser.add_argument("--symbol", required=True, help="Trading symbol")
    parser.add_argument("--zone-tf", default="H1", help="Zone detection timeframe")
    parser.add_argument("--entry-tf", default="M30", help="Entry signal timeframe")
    parser.add_argument("--zone-data", help="Path to zone TF data CSV")
    parser.add_argument("--entry-data", help="Path to entry TF data CSV")

    args = parser.parse_args()

    # Auto-detect data paths if not provided
    base_path = Path(__file__).parent.parent / "data" / "backtest"
    zone_data = args.zone_data or str(base_path / f"{args.symbol}_{args.zone_tf}.csv")
    entry_data = args.entry_data or str(base_path / f"{args.symbol}_{args.entry_tf}.csv")

    # Run backtest
    engine = MTFBacktestEngine(
        symbol=args.symbol,
        zone_tf=args.zone_tf,
        entry_tf=args.entry_tf,
        zone_data_path=zone_data,
        entry_data_path=entry_data,
    )

    await engine.run()


if __name__ == "__main__":
    asyncio.run(main())
