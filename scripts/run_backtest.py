"""
Backtest Engine.

Simulates strategy execution on historical data.
- Loads data from CSV (created by download_data.py)
- Runs FoundationEngine in mocked environment (no DB)
- Simulates trade execution and PnL calculation
"""

import argparse
import asyncio
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

# Add project root to Python path
project_root = str(Path(__file__).parent.parent / "src")
sys.path.append(project_root)

from trading_bot.strategies.foundation.foundation_engine import FoundationEngine
from trading_bot.strategies.models import SignalDirection, StrategyResult
from trading_bot.utils.logger import get_logger

logger = get_logger("run_backtest")


@dataclass
class MockTrade:
    """Mock trade object for backtesting (Memory Only)."""

    symbol: str
    direction: SignalDirection
    entry_price: float
    stop_loss: float
    take_profit: float
    entry_time: datetime
    volume: float = 0.01

    # Internal State
    initial_stop_loss: float = field(init=False)

    # Status
    is_open: bool = True
    exit_price: float = 0.0
    exit_time: datetime | None = None
    exit_reason: str = ""
    pnl: float = 0.0

    def __post_init__(self):
        self.initial_stop_loss = self.stop_loss

    @property
    def risk(self) -> float:
        """Risk in price units (based on Initial SL)."""
        return abs(self.entry_price - self.initial_stop_loss)

    @property
    def reward(self) -> float:
        """Reward in price units."""
        return abs(self.take_profit - self.entry_price)

    @property
    def r_multiple(self) -> float:
        """Realized R-Multiple (based on Initial Risk)."""
        if not self.exit_price or self.risk == 0:
            return 0.0

        raw_pnl = 0.0
        if self.direction == SignalDirection.BUY:
            raw_pnl = self.exit_price - self.entry_price
        else:
            raw_pnl = self.entry_price - self.exit_price

        return raw_pnl / self.risk

    @property
    def pips(self) -> float:
        """Realized PnL in Pips."""
        if not self.exit_price:
            return 0.0

        # Determine pip size based on price
        # Heuristic: < 50 = 0.0001 (Forex), > 50 = 0.01 (JPY)
        pip_size = 0.0001
        if self.entry_price > 50:
            pip_size = 0.01

        raw_pnl = 0.0
        if self.direction == SignalDirection.BUY:
            raw_pnl = self.exit_price - self.entry_price
        else:
            raw_pnl = self.entry_price - self.exit_price

        return raw_pnl / pip_size


import yaml

# ... imports ...


class BacktestEngine:
    """Core Backtest Simulation Engine."""

    def __init__(self, symbol: str, timeframe: str, data_path: str):
        self.symbol = symbol
        self.timeframe = timeframe
        self.data_path = data_path

        # Load Configuration
        self.config = self._load_config()

        # Load Data
        self.full_data = self._load_data()

        # Initialize Strategy (DISABLE DB PERSISTENCE)
        self.engine = FoundationEngine(config=self.config, use_database=False)

        # State
        self.trades: list[MockTrade] = []
        self.active_trade: MockTrade | None = None

        # Config (Simulated)
        self.spread = 0.0001  # Hardcoded spread assumption (can be improved)

    def _load_config(self) -> dict:
        """Load strategy parameters."""
        config_path = Path(project_root).parent / "config" / "strategy_parameters.yaml"
        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}

    def _load_data(self) -> pd.DataFrame:
        """Load CSV data."""
        path = Path(self.data_path)
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {path}")

        df = pd.read_csv(path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)
        return df.sort_index()

    async def run(self):
        """Run the simulation loop."""
        logger.info(f"Starting backtest for {self.symbol} {self.timeframe}...")
        logger.info(f"Data points: {len(self.full_data)}")

        # Simulation Loop
        # We need enough initial data for indicators (e.g., 100 periods)
        warmup_periods = 100

        total_candles = len(self.full_data)

        for i in range(warmup_periods, total_candles):
            # 1. Current "Slice" of data (simulate valid window at that time)
            # Strategy needs historical context up to current time
            # current_idx is the "close" of the current candle we just finished
            current_time = self.full_data.index[i]

            # Slice data up to current time (simulate standard live bot receiving data)
            # Using copy to ensure no contamination
            current_data = self.full_data.iloc[: i + 1].copy()

            # 2. Check Exits for Active Trades (based on Current Candle High/Low)
            self._check_exits(current_data.iloc[-1], current_time)

            # 3. Generate Signals (only if no active trade - simplified logic)
            # In a real bot we might stack trades, but for simplicity here assume 1 active trade
            if self.active_trade is None:
                await self._process_entry(current_data, current_time)

            if i % 100 == 0:
                print(f"Processed {i}/{total_candles} candles...", end="\r")

        print("\nBacktest Complete.")
        self._generate_report()

    def _check_exits(self, candle: pd.Series, current_time: datetime):
        """Check if active trade hit SL or TP in the current candle."""
        trade = self.active_trade
        if not trade:
            return

        # Simple High/Low check
        # In reality, we don't know if High or Low happened first within the bar.
        # WORST CASE assumption: If both SL and TP are hit in same candle, assume SL hit.

        high = candle["high"]
        low = candle["low"]

        # Check SL/TP based on direction
        sl_hit = False
        tp_hit = False
        exit_price = 0.0

        # Check High/Low for Take Profit / Stop Loss / Trailing

        # Determine pip size (Standardize)
        pip_size = 0.0001
        if self.active_trade.entry_price > 50:
            pip_size = 0.01

        # --- Load Trade Management Config based on Asset Class ---
        tm_config_root = self.config.get("trade_management", {})

        # 1. Get Asset Class
        # We can use a simple heuristic or try to import SymbolMapper
        # For backtest simplicity, let's use the mapped asset class from config/symbol_mapping.yaml logic
        # OR just a robust heuristic:
        asset_class = "defaults"  # Default to forex logic
        symbol_upper = self.symbol.upper()

        if "XAU" in symbol_upper or "GOLD" in symbol_upper:
            asset_class = "commodities"
        elif "BTC" in symbol_upper or "ETH" in symbol_upper:
            asset_class = "crypto"
        elif "JPY" in symbol_upper:
            asset_class = "forex_jpy"

        # 2. Get Settings
        defaults = tm_config_root.get("defaults", {})
        overrides = tm_config_root.get("overrides", {}).get(asset_class, {})

        # Merge Settings (Override specific keys)
        be_settings = defaults.get("breakeven", {}).copy()
        be_settings.update(overrides.get("breakeven", {}))

        ts_settings = defaults.get("trailing_stop", {}).copy()
        ts_settings.update(overrides.get("trailing_stop", {}))

        # Extract Values
        be_enabled = be_settings.get("enabled", True)
        be_trigger = be_settings.get("trigger_pips", 20.0)
        be_offset = be_settings.get("offset_pips", 2.0)

        ts_enabled = ts_settings.get("enabled", True)
        ts_activation = ts_settings.get("activation_pips", 30.0)
        ts_limit = ts_settings.get("limit_pips", 10.0)

        # --- Check SL/TP first (Standard execution) ---
        if self.active_trade.direction == SignalDirection.BUY:
            if low <= self.active_trade.stop_loss:
                self._close_trade(self.active_trade.stop_loss, current_time, "SL/Trailing")
                return
            if high >= self.active_trade.take_profit:
                self._close_trade(self.active_trade.take_profit, current_time, "TP")
                return

            # --- Trailing Stop & Breakeven Logic (BUY) ---
            current_profit = high - self.active_trade.entry_price
            current_profit_pips = current_profit / pip_size

            # 1. Breakeven
            if be_enabled:
                be_price = self.active_trade.entry_price + (be_offset * pip_size)
                # Check if profit reached trigger AND SL is below BE
                if current_profit_pips >= be_trigger and self.active_trade.stop_loss < be_price:
                    self.active_trade.stop_loss = be_price

            # 2. Trailing Stop
            if ts_enabled:
                if current_profit_pips >= ts_activation:
                    # Trailing SL should be High - limit
                    potential_sl = high - (ts_limit * pip_size)
                    # Only move SL UP
                    if potential_sl > self.active_trade.stop_loss:
                        self.active_trade.stop_loss = potential_sl

        else:  # SELL
            if high >= self.active_trade.stop_loss:
                self._close_trade(self.active_trade.stop_loss, current_time, "SL/Trailing")
                return
            if low <= self.active_trade.take_profit:
                self._close_trade(self.active_trade.take_profit, current_time, "TP")
                return

            # --- Trailing Stop & Breakeven Logic (SELL) ---
            current_profit = self.active_trade.entry_price - low
            current_profit_pips = current_profit / pip_size

            # 1. Breakeven
            if be_enabled:
                be_price = self.active_trade.entry_price - (be_offset * pip_size)
                # Check if profit reached trigger AND SL is above BE (for Sell, SL is higher)
                if current_profit_pips >= be_trigger and self.active_trade.stop_loss > be_price:
                    self.active_trade.stop_loss = be_price

            # 2. Trailing Stop
            if ts_enabled:
                if current_profit_pips >= ts_activation:
                    # Trailing SL should be Low + limit
                    potential_sl = low + (ts_limit * pip_size)
                    # Only move SL DOWN (for Sell)
                    if potential_sl < self.active_trade.stop_loss:
                        self.active_trade.stop_loss = potential_sl

        # Execute Exit
        # The new logic handles exits directly with `return` statements,
        # so these original `if sl_hit:` and `elif tp_hit:` checks are no longer needed.
        # They are effectively replaced by the direct `_close_trade` calls above.
        # Keeping them commented out for clarity that they were removed.
        # if sl_hit:
        #     self._close_trade(exit_price, current_time, "SL")
        # elif tp_hit:
        #     self._close_trade(exit_price, current_time, "TP")

    async def _process_entry(self, data: pd.DataFrame, current_time: datetime):
        """Get signal from strategy and open trade."""
        # Run strategy
        results = await self.engine.generate_signals(self.symbol, data, self.timeframe)

        if not results:
            return

        # Get Thresholds from Config
        quality_config = self.config.get("signal_generation", {}).get("quality_thresholds", {})
        min_score = quality_config.get("min_confluence_score", 20.0)

        # Filter for valid signals with sufficient score
        valid_signals = []
        for r in results:
            if not r.has_signal:
                continue

            if r.score < min_score:
                # logger.debug(f"Signal filtered: Score {r.score:.1f} < {min_score}")
                continue

            valid_signals.append(r)

        if not valid_signals:
            return

        # Take the best signal
        signal = valid_signals[0]

        # Open Trade
        self._open_trade(signal, current_time)

    def _open_trade(self, signal: StrategyResult, time: datetime):
        """Open a new mock trade."""
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

    def _close_trade(self, price: float, time: datetime, reason: str):
        """Close the active mock trade."""
        trade = self.active_trade
        if not trade:
            return

        trade.is_open = False
        trade.exit_price = price
        trade.exit_time = time
        trade.exit_reason = reason

        logger.info(
            f"CLOSE {trade.direction.value} ({reason}) @ {price:.5f} | R: {trade.r_multiple:.2f} | Pips: {trade.pips:.1f} at {time}"
        )

        self.active_trade = None

    def _generate_report(self):
        """Print performance statistics."""
        if not self.trades:
            print("\nNo trades generated.")
            return

        completed_trades = [t for t in self.trades if not t.is_open]
        if not completed_trades:
            print("\nNo completed trades.")
            return

        wins = [t for t in completed_trades if t.r_multiple > 0]
        losses = [t for t in completed_trades if t.r_multiple <= 0]

        win_rate = len(wins) / len(completed_trades) * 100
        total_r = sum(t.r_multiple for t in completed_trades)
        total_pips = sum(t.pips for t in completed_trades)
        max_r = max((t.r_multiple for t in completed_trades), default=0)
        min_r = min((t.r_multiple for t in completed_trades), default=0)

        print("\n" + "=" * 40)
        print(f"BACKTEST REPORT: {self.symbol} ({self.timeframe})")
        print("=" * 40)
        print(f"Total Trades:     {len(completed_trades)}")
        print(f"Wins:             {len(wins)}")
        print(f"Losses:           {len(losses)}")
        print(f"Win Rate:         {win_rate:.2f}%")
        print("-" * 20)
        print(f"Total Return (R): {total_r:.2f}R")
        print(f"Total Pips:       {total_pips:.1f} pips")
        print(f"Best Trade:       {max_r:.2f}R")
        print(f"Worst Trade:      {min_r:.2f}R")
        print("=" * 40)

        print("\nTRADE HISTORY:")
        print(
            f"{'ID':<4} | {'Type':<4} | {'Entry':<10} | {'SL':<10} | {'TP':<10} | {'Pips':<6} | {'Result':<6}"
        )
        print("-" * 70)

        for i, t in enumerate(completed_trades, 1):
            res_str = f"{t.r_multiple:+.2f}R"
            print(
                f"{i:<4} | {t.direction.value:<4} | {t.entry_price:<10.5f} | {t.stop_loss:<10.5f} | {t.take_profit:<10.5f} | {t.pips:<6.1f} | {res_str:<6}"
            )
        print("-" * 70)


def main():
    parser = argparse.ArgumentParser(description="Run Strategy Backtest")
    parser.add_argument("--symbol", type=str, required=True)
    parser.add_argument("--timeframe", type=str, default="H1")
    parser.add_argument(
        "--data", type=str, default="data/backtest", help="Directory containing CSV data"
    )

    args = parser.parse_args()

    # Construct filename
    data_path = Path(args.data)
    if not data_path.suffix:  # Is directory
        filename = f"{args.symbol}_{args.timeframe}.csv"
        data_path = data_path / filename

    if not data_path.exists():
        print(f"Error: Data file {data_path} not found.")
        print("Please run scripts/download_data.py first.")
        return

    # Run Backtest
    engine = BacktestEngine(args.symbol, args.timeframe, str(data_path))
    try:
        asyncio.run(engine.run())
    except KeyboardInterrupt:
        print("\nBacktest cancelled.")
    except Exception as e:
        logger.error(f"Backtest error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
