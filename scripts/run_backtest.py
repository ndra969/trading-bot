"""Backtest Engine — rewired 2026-06-13 for exit-payoff-tuning Phase 1.

Drives the REAL automation managers (BreakevenManager / TrailingStopManager /
PartialCloseManager) + PositionTracker + FoundationEngine over historical CSV
data, so exit/payoff metrics (MFE reached vs R kept, exit-reason buckets,
payoff ratio) reflect live behaviour instead of a divergent reimplementation.

Run via the uv workspace so `trading_core` / `trading_worker` import cleanly:

    uv run python scripts/run_backtest.py --symbol EURUSDc --timeframe H1
    uv run python scripts/run_backtest.py --symbol XAUUSDc --timeframe H1 \
        --trailing-activation-r 0.5 --tp-ratio 1.5 --partial on --volume 0.10

Sweep knobs (exit-payoff design L1/L2/L3) patch the loaded config before the
managers/engine are built, so a run reflects exactly that combo:
    --trailing-activation-r   trailing activation as a fraction of risk (all assets)
    --tp-ratio                signal_generation.risk_reward.default_take_profit_ratio
    --partial {off,on}        partial_close.enabled (size-gated by min_position_volume)
    --volume                  simulated open lot size (>= 0.04 lets partials fire)

Limitations: single-symbol single-TF (see run_mtf_backtest for H1-zone/M30-entry);
automation decisions use each bar's CLOSE (mirrors the live ~60s loop) while SL/TP
fills use the bar high/low; no spread / commission / slippage modelled; one
position at a time.
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pandas as pd
from trading_core.config import Configuration
from trading_core.utils.logger import get_logger
from trading_worker.position.automation.breakeven_manager import BreakevenManager
from trading_worker.position.automation.partial_close_manager import PartialCloseManager
from trading_worker.position.automation.trailing_stop_manager import TrailingStopManager
from trading_worker.position.pip_calculator import PipCalculator
from trading_worker.position.position_models import Position, PositionStatus, PositionType
from trading_worker.position.position_tracker import PositionTracker
from trading_worker.strategies.foundation.foundation_engine import FoundationEngine
from trading_worker.strategies.models import SignalDirection

logger = get_logger("run_backtest")


@dataclass
class PartialFill:
    """A single partial close (for weighted-R accounting)."""

    close_price: float
    volume: float
    fraction: float  # of the INITIAL volume
    r_multiple: float


@dataclass
class TradeRecord:
    """Outcome of one simulated trade, with payoff diagnostics."""

    symbol: str
    direction: SignalDirection
    entry_price: float
    initial_stop_loss: float
    take_profit: float
    entry_time: datetime
    initial_volume: float
    pip_size: float

    exit_price: float = 0.0
    exit_time: datetime | None = None
    close_reason: str = ""  # TAKE_PROFIT / STOP_LOSS / BREAKEVEN_STOP / TRAILING_STOP
    partials: list[PartialFill] = field(default_factory=list)
    peak_r: float = 0.0  # max favorable excursion, in R (true bar high/low)
    realized_r: float = 0.0  # volume-weighted R across partials + final exit

    @property
    def initial_risk(self) -> float:
        return abs(self.entry_price - self.initial_stop_loss)

    def directional_r(self, price: float) -> float:
        """R-multiple of `price` vs entry on the INITIAL risk."""
        if self.initial_risk == 0:
            return 0.0
        if self.direction == SignalDirection.BUY:
            return (price - self.entry_price) / self.initial_risk
        return (self.entry_price - price) / self.initial_risk

    @property
    def pips(self) -> float:
        if self.pip_size == 0:
            return 0.0
        raw = (
            self.exit_price - self.entry_price
            if self.direction == SignalDirection.BUY
            else self.entry_price - self.exit_price
        )
        return raw / self.pip_size


class BacktestEngine:
    """Core backtest simulation driving the real automation managers."""

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        data_path: str,
        *,
        open_volume: float = 0.10,
        overrides: dict | None = None,
        news_service=None,
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        self.data_path = data_path
        self.open_volume = open_volume
        # Optional NewsService for news-effect measurement (Phase 5). Default
        # None → backtest is byte-for-byte unchanged. A measurement script wires
        # one built against a calendar-populated DB; the gate/modifier are then
        # lookahead-safe because _create_signal_from_zone is fed data[:i+1], so
        # data.index[-1] is the current bar time.
        self.news_service = news_service

        self.config = self._load_config(overrides or {})
        self.full_data = self._load_data()
        self._build_runtime()

    def _build_runtime(self) -> None:
        """Construct the strategy + real automation managers + trade state.

        Shared by the single-TF engine and the MTF subclass so both drive the
        exact same live machinery off the same merged config.
        """
        self.engine = FoundationEngine(
            config=self.config, use_database=False, news_service=self.news_service
        )
        self.tracker = PositionTracker()
        self.breakeven = BreakevenManager(self.config)
        self.trailing = TrailingStopManager(self.config)
        self.partial = PartialCloseManager(self.config)
        self.pip_calculator = PipCalculator()

        self.trades: list[TradeRecord] = []
        self._active: Position | None = None
        self._active_record: TradeRecord | None = None
        self._trade_seq = 0

    # ----------------------------------------------------------------- setup
    def _load_config(self, overrides: dict) -> dict:
        """Load the same merged config the live bot uses, then apply backtest
        overrides (zone age, lower confluence gate) and any sweep knobs."""
        cfg = Configuration()._config.copy()

        # Backtest necessities: historical zones are "old" vs wall-clock, and
        # the live confluence gate is tuned for live; relax both so the
        # strategy actually produces trades to measure.
        cfg.setdefault("supply_demand", {}).setdefault("zone_detection", {})[
            "max_zone_age_hours"
        ] = 100000
        sg = cfg.setdefault("signal_generation", {})
        sg.setdefault("quality_thresholds", {})["min_confluence_score"] = 20.0

        self._deep_merge(cfg, overrides)
        logger.info(
            f"Config: TP ratio={cfg.get('signal_generation', {}).get('risk_reward', {}).get('default_take_profit_ratio')}, "
            f"partial_close.enabled={cfg.get('partial_close', {}).get('enabled')}"
        )
        return cfg

    @staticmethod
    def _deep_merge(base: dict, update: dict) -> None:
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                BacktestEngine._deep_merge(base[key], value)
            else:
                base[key] = value

    def _load_data(self) -> pd.DataFrame:
        path = Path(self.data_path)
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {path}")
        df = pd.read_csv(path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)
        return df.sort_index()

    # ------------------------------------------------------------------- run
    async def run(self) -> None:
        logger.info(f"Backtest {self.symbol} {self.timeframe}: {len(self.full_data)} bars")
        warmup = 100
        total = len(self.full_data)

        for i in range(warmup, total):
            current_time = self.full_data.index[i]
            candle = self.full_data.iloc[i]

            # 1. Exit check FIRST — this bar's high/low vs the SL/TP that
            #    automation set at the PREVIOUS bar's close (no lookahead).
            if self._active is not None:
                self._check_exit(candle, current_time)

            # 2. Still open: update P&L/MFE off the close, then run automation
            #    in live order (breakeven -> trailing -> partial) off the close.
            if self._active is not None:
                self._update_and_automate(candle, current_time)

            # 3. Flat: look for an entry on the data seen so far.
            if self._active is None:
                await self._try_entry(self.full_data.iloc[: i + 1], current_time)

            if i % 100 == 0:
                print(f"  {i}/{total} bars...", end="\r")

        # Close any trade still open at the end of the data, at the last close.
        if self._active is not None:
            last = self.full_data.iloc[-1]
            self._finalise_exit(float(last["close"]), self.full_data.index[-1], "STOP_LOSS")

        print("\nBacktest complete.")
        self._report()

    # --------------------------------------------------------------- entries
    async def _try_entry(self, data: pd.DataFrame, current_time: datetime) -> None:
        results = await self.engine.generate_signals(self.symbol, data, self.timeframe)
        signals = [r for r in results if r.has_signal]
        if not signals:
            return
        signal = max(signals, key=lambda r: r.score)
        self._open(signal, current_time)

    def _open(self, signal, entry_time: datetime) -> None:
        self._trade_seq += 1
        pos_id = f"bt_{self._trade_seq}"
        pip_size = self.pip_calculator.get_pip_size(self.symbol)
        pip_value = self.pip_calculator.calculate_pip_value(self.symbol, 1.0)

        position = Position(
            position_id=pos_id,
            symbol=self.symbol,
            position_type=(
                PositionType.BUY if signal.direction == SignalDirection.BUY else PositionType.SELL
            ),
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            volume=self.open_volume,
            pip_size=pip_size,
            pip_value_per_lot=pip_value,
            status=PositionStatus.PENDING,
        )
        # open_position freezes entry_to_sl_pips (ratio-based BE/trailing need it)
        # and resets MFE/MAE — mirrors the live open path.
        self.tracker.open_position(position)
        self.partial.initialize_position(position)

        record = TradeRecord(
            symbol=self.symbol,
            direction=signal.direction,
            entry_price=signal.entry_price,
            initial_stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            entry_time=entry_time,
            initial_volume=self.open_volume,
            pip_size=pip_size,
        )
        self._active = position
        self._active_record = record
        self.trades.append(record)
        logger.info(
            f"OPEN {signal.direction.value} {self.symbol} @ {signal.entry_price:.5f} "
            f"[SL {signal.stop_loss:.5f} TP {signal.take_profit:.5f}] score={signal.score:.1f} {entry_time}"
        )

    # ---------------------------------------------------------------- exits
    def _check_exit(self, candle: pd.Series, current_time: datetime) -> None:
        pos = self._active
        rec = self._active_record
        assert pos is not None and rec is not None
        high = float(candle["high"])
        low = float(candle["low"])

        # Track true peak (MFE) in R from this bar's favorable extreme.
        favorable = high if pos.position_type == PositionType.BUY else low
        rec.peak_r = max(rec.peak_r, rec.directional_r(favorable))

        # Pessimistic on ambiguity: if a bar straddles both SL and TP, assume
        # SL filled first.
        if pos.position_type == PositionType.BUY:
            if low <= pos.stop_loss:
                self._finalise_exit(pos.stop_loss, current_time, self._sl_reason(pos))
            elif high >= pos.take_profit:
                self._finalise_exit(pos.take_profit, current_time, "TAKE_PROFIT")
        else:  # SELL
            if high >= pos.stop_loss:
                self._finalise_exit(pos.stop_loss, current_time, self._sl_reason(pos))
            elif low <= pos.take_profit:
                self._finalise_exit(pos.take_profit, current_time, "TAKE_PROFIT")

    @staticmethod
    def _sl_reason(pos: Position) -> str:
        """Classify a stop-out by which protection had armed."""
        if pos.trailing_activated:
            return "TRAILING_STOP"
        if pos.breakeven_activated:
            return "BREAKEVEN_STOP"
        return "STOP_LOSS"

    def _finalise_exit(self, price: float, exit_time: datetime, reason: str) -> None:
        pos = self._active
        rec = self._active_record
        assert pos is not None and rec is not None

        remaining_volume = self.partial.get_remaining_volume(pos.position_id)
        if remaining_volume <= 0:
            remaining_volume = rec.initial_volume
        remaining_fraction = remaining_volume / rec.initial_volume

        rec.exit_price = price
        rec.exit_time = exit_time
        rec.close_reason = reason
        rec.realized_r += rec.directional_r(price) * remaining_fraction

        pos.status = PositionStatus.CLOSED
        self._reset_managers(pos.position_id)
        logger.info(
            f"CLOSE {rec.direction.value} ({reason}) @ {price:.5f} | "
            f"realized {rec.realized_r:+.2f}R | peak {rec.peak_r:.2f}R | {exit_time}"
        )
        self._active = None
        self._active_record = None

    def _reset_managers(self, pos_id: str) -> None:
        self.breakeven.reset_position(pos_id)
        self.trailing.reset_position(pos_id)
        self.partial.reset_position(pos_id)

    # ----------------------------------------------------- per-bar automation
    def _update_and_automate(self, candle: pd.Series, current_time: datetime) -> None:
        pos = self._active
        rec = self._active_record
        assert pos is not None and rec is not None

        close = float(candle["close"])
        # Mirror live: PositionTracker updates current_price / profit_pips / MFE.
        self.tracker.update_position_price(pos, close)

        # Live automation order: breakeven -> trailing (activate+update) -> partial.
        if self.breakeven.should_move_to_breakeven(pos):
            self.breakeven.move_to_breakeven(pos)

        if self.trailing.should_activate_trailing(pos):
            self.trailing.activate_trailing(pos)
        if self.trailing.should_update_trailing_stop(pos):
            self.trailing.update_trailing_stop(pos)

        if self.partial.should_close_partial(pos):
            result = self.partial.execute_partial_close(pos, close)
            closed_volume = result["close_volume"]
            fraction = closed_volume / rec.initial_volume
            r = rec.directional_r(close)
            rec.realized_r += r * fraction
            rec.partials.append(
                PartialFill(
                    close_price=close, volume=closed_volume, fraction=fraction, r_multiple=r
                )
            )
            logger.info(
                f"  PARTIAL L{result['level']} {closed_volume:.2f} lots @ {close:.5f} "
                f"({r:+.2f}R x {fraction:.0%})"
            )

    # --------------------------------------------------------------- report
    def _report(self) -> None:
        done = [t for t in self.trades if t.close_reason]
        if not done:
            print("\nNo completed trades.")
            return

        wins = [t for t in done if t.realized_r > 0]
        losses = [t for t in done if t.realized_r <= 0]
        win_rate = len(wins) / len(done) * 100
        total_r = sum(t.realized_r for t in done)
        avg_win = sum(t.realized_r for t in wins) / len(wins) if wins else 0.0
        avg_loss = sum(t.realized_r for t in losses) / len(losses) if losses else 0.0
        payoff = (avg_win / abs(avg_loss)) if avg_loss != 0 else float("inf")
        expectancy = total_r / len(done)

        print("\n" + "=" * 56)
        print(f"BACKTEST REPORT - {self.symbol} ({self.timeframe})")
        print("=" * 56)
        print(f"Trades:            {len(done)}  (W {len(wins)} / L {len(losses)})")
        print(f"Win rate:          {win_rate:.1f}%")
        print(f"Total return:      {total_r:+.2f}R")
        print(f"Expectancy/trade:  {expectancy:+.3f}R")
        print(f"Avg win:           {avg_win:+.2f}R   Avg loss: {avg_loss:+.2f}R")
        print(f"Payoff ratio:      {payoff:.2f}   (target >= 0.8)")
        print("-" * 56)

        # Per exit-reason bucket: count, avg peak (MFE reached), avg kept (R).
        print(f"{'exit reason':<16}{'n':>4}{'reached(MFE)':>14}{'kept(R)':>10}")
        buckets: dict[str, list[TradeRecord]] = {}
        for t in done:
            buckets.setdefault(t.close_reason, []).append(t)
        for reason in ("TAKE_PROFIT", "TRAILING_STOP", "BREAKEVEN_STOP", "STOP_LOSS"):
            bucket = buckets.get(reason, [])
            if not bucket:
                continue
            n = len(bucket)
            reached = sum(t.peak_r for t in bucket) / n
            kept = sum(t.realized_r for t in bucket) / n
            print(f"{reason:<16}{n:>4}{reached:>14.2f}{kept:>10.2f}")
        partials_fired = sum(len(t.partials) for t in done)
        print("-" * 56)
        print(f"Partial closes fired: {partials_fired}")
        print("=" * 56)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run strategy backtest (real automation managers)")
    parser.add_argument("--symbol", type=str, required=True, help="e.g. EURUSDc")
    parser.add_argument("--timeframe", type=str, default="H1")
    parser.add_argument("--data", type=str, default="data/backtest", help="CSV dir or file")
    parser.add_argument("--volume", type=float, default=0.10, help="Simulated open lot size")
    parser.add_argument(
        "--trailing-activation-r",
        type=float,
        default=None,
        help="Override trailing activation as a fraction of risk (all asset classes)",
    )
    parser.add_argument(
        "--breakeven-trigger-r",
        type=float,
        default=None,
        help="Override breakeven arm point as a fraction of risk (all asset classes). "
        "Higher = let winners run before locking BE (default 0.4).",
    )
    parser.add_argument(
        "--trailing-distance-r",
        type=float,
        default=None,
        help="Override trailing distance as a fraction of risk (all asset classes). "
        "Lower = trail tighter / give back less of the run (default 0.4).",
    )
    parser.add_argument(
        "--tp-ratio", type=float, default=None, help="Override default_take_profit_ratio"
    )
    parser.add_argument("--partial", choices=["off", "on"], default=None)
    parser.add_argument(
        "--log-level",
        type=str,
        default="WARNING",
        help="Loguru level for the run (default WARNING). Per-bar DEBUG logging "
        "dominates runtime, so backtests/sweeps run quiet by default; pass "
        "--log-level INFO/DEBUG to trace automation decisions.",
    )
    args = parser.parse_args()

    # Backtests never call setup_logger, so loguru's default DEBUG stderr sink
    # fires on every bar — that per-bar logging is the runtime bottleneck (M30
    # and BTC H1 sweeps time out under it). Reconfigure to a quiet level so runs
    # complete; the final report uses print() and is unaffected.
    import sys

    from loguru import logger as _loguru_logger

    _loguru_logger.remove()
    _loguru_logger.add(sys.stderr, level=args.log_level.upper())

    data_path = Path(args.data)
    if not data_path.suffix:
        data_path = data_path / f"{args.symbol}_{args.timeframe}.csv"
    if not data_path.exists():
        print(f"Error: data file {data_path} not found. Run scripts/download_data.py first.")
        return

    overrides = _build_overrides(args)
    engine = BacktestEngine(
        args.symbol,
        args.timeframe,
        str(data_path),
        open_volume=args.volume,
        overrides=overrides,
    )
    asyncio.run(engine.run())


def _build_overrides(args) -> dict:
    """Translate sweep CLI flags into a config-override dict."""
    overrides: dict = {}
    if args.tp_ratio is not None:
        overrides.setdefault("signal_generation", {}).setdefault("risk_reward", {})[
            "default_take_profit_ratio"
        ] = args.tp_ratio
    if args.partial is not None:
        overrides.setdefault("partial_close", {})["enabled"] = args.partial == "on"
    if args.trailing_activation_r is not None:
        pm = overrides.setdefault("position_management", {})
        for asset in ("forex_major", "forex_jpy", "commodities", "crypto"):
            pm.setdefault(asset, {})["trailing_activation_r"] = args.trailing_activation_r
    if args.breakeven_trigger_r is not None:
        pm = overrides.setdefault("position_management", {})
        for asset in ("forex_major", "forex_jpy", "commodities", "crypto"):
            pm.setdefault(asset, {})["breakeven_trigger_r"] = args.breakeven_trigger_r
    if args.trailing_distance_r is not None:
        pm = overrides.setdefault("position_management", {})
        for asset in ("forex_major", "forex_jpy", "commodities", "crypto"):
            pm.setdefault(asset, {})["trailing_distance_r"] = args.trailing_distance_r
    return overrides


if __name__ == "__main__":
    main()
