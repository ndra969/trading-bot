"""Multi-Timeframe Backtest — rewired 2026-06-13 for exit-payoff-tuning Phase 1.

Zone detection on the higher TF (e.g. H1), entry confirmation on the lower TF
(e.g. M30) — the live MTF approach. Subclasses BacktestEngine so exits and
automation run through the SAME real managers (breakeven / trailing / partial)
+ PositionTracker; only zone detection and the entry scan are MTF-specific.

    uv run python scripts/run_mtf_backtest.py --symbol EURUSDc --zone-tf H1 --entry-tf M30
    uv run python scripts/run_mtf_backtest.py --symbol XAUUSDc --zone-tf H1 --entry-tf M30 \
        --trailing-activation-r 0.5 --tp-ratio 1.5 --partial on --volume 0.10

Sweep knobs and limitations match run_backtest.py.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import pandas as pd
from run_backtest import BacktestEngine, _build_overrides
from trading_core.utils.logger import get_logger

logger = get_logger("mtf_backtest")


class MTFBacktestEngine(BacktestEngine):
    """Multi-timeframe backtest: H1 zones, M30 entries, real automation managers."""

    def __init__(
        self,
        symbol: str,
        zone_tf: str,
        entry_tf: str,
        zone_data_path: str,
        entry_data_path: str,
        *,
        open_volume: float = 0.10,
        overrides: dict | None = None,
    ):
        self.symbol = symbol
        self.zone_tf = zone_tf
        self.entry_tf = entry_tf
        self.timeframe = entry_tf  # for the inherited report header
        self.open_volume = open_volume

        self.config = self._load_config(overrides or {})
        self.zone_data = self._load_data_from(zone_data_path)
        self.entry_data = self._load_data_from(entry_data_path)
        self._build_runtime()

        logger.info(
            f"MTF {symbol}: {len(self.zone_data)} {zone_tf} (zones) / "
            f"{len(self.entry_data)} {entry_tf} (entries)"
        )

    @staticmethod
    def _load_data_from(path: str) -> pd.DataFrame:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Data file not found: {p}")
        df = pd.read_csv(p)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df.set_index("timestamp", inplace=True)
        return df.sort_index()

    async def run(self) -> None:
        logger.info(f"MTF backtest {self.symbol} (zones {self.zone_tf}, entries {self.entry_tf})")

        # Detect zones once on the higher TF, referenced to its last bar so age
        # filters don't drop them as "expired" relative to wall-clock.
        last_zone_ts = self.zone_data.index[-1].to_pydatetime()
        zones = await self.engine.analyze_symbol(
            self.symbol, self.zone_data, self.zone_tf, reference_time=last_zone_ts
        )
        logger.info(f"Detected {len(zones)} zones on {self.zone_tf}")
        if not zones:
            print("\nNo zones detected.")
            self._report()
            return

        total = len(self.entry_data)
        lookback = 200
        for i in range(lookback, total):
            current_time = self.entry_data.index[i]
            candle = self.entry_data.iloc[i]
            price = float(candle["close"])

            # Exits + automation through the inherited real-manager machinery.
            if self._active is not None:
                self._check_exit(candle, current_time)
            if self._active is not None:
                self._update_and_automate(candle, current_time)

            # Flat: look for a zone the price is sitting in, then run the real
            # signal path (with H1 trend bias for commodities) at that zone.
            if self._active is None:
                for zone in zones:
                    zone._reference_time = current_time
                    if not self._price_at_zone(price, zone):
                        continue
                    bias = self._h1_trend_bias(candle, price)
                    signal = await self.engine._create_signal_from_zone(
                        self.symbol,
                        zone,
                        price,
                        self.entry_tf,
                        self.entry_data.iloc[: i + 1],
                        h1_trend_bias=bias,
                    )
                    if signal:
                        self._open(signal, current_time)
                        break

            if i % 100 == 0:
                print(f"  {i}/{total} bars...", end="\r")

        if self._active is not None:
            last = self.entry_data.iloc[-1]
            self._finalise_exit(float(last["close"]), self.entry_data.index[-1], "STOP_LOSS")

        print("\nMTF backtest complete.")
        self._report()

    @staticmethod
    def _price_at_zone(price: float, zone) -> bool:
        tolerance = (zone.upper_bound - zone.lower_bound) * 0.2
        return zone.lower_bound - tolerance <= price <= zone.upper_bound + tolerance

    def _h1_trend_bias(self, entry_candle: pd.Series, price: float) -> str | None:
        """H1 sniper trend bias for commodities (None for other assets).

        Mirrors the live Phase 5.24 gate: price on the right side of both EMA20
        and EMA50 with EMA50 sloping that way, plus a two-candle momentum guard.
        """
        asset_class = self.pip_calculator.symbol_mapper.get_asset_class(self.symbol)
        if asset_class != "commodities":
            return None

        h1_hist = self.zone_data[self.zone_data.index <= entry_candle.name]
        if len(h1_hist) < 50:
            return None

        ema_50 = h1_hist["close"].ewm(span=50, adjust=False).mean()
        ema_20 = h1_hist["close"].ewm(span=20, adjust=False).mean()
        ema50_curr, ema50_prev = ema_50.iloc[-1], ema_50.iloc[-2]
        ema20_curr = ema_20.iloc[-1]

        if price > ema50_curr and price > ema20_curr and ema50_curr > ema50_prev:
            bias = "BULLISH"
        elif price < ema50_curr and price < ema20_curr and ema50_curr < ema50_prev:
            bias = "BEARISH"
        else:
            return "NEUTRAL"

        # Momentum guard: don't fight two consecutive opposing H1 closes.
        if len(h1_hist) >= 3:
            c0, c1, c2 = (
                h1_hist["close"].iloc[-1],
                h1_hist["close"].iloc[-2],
                h1_hist["close"].iloc[-3],
            )
            if bias == "BULLISH" and c0 < c1 < c2:
                return "NEUTRAL"
            if bias == "BEARISH" and c0 > c1 > c2:
                return "NEUTRAL"
        return bias


async def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-timeframe backtest (real automation)")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--zone-tf", default="H1")
    parser.add_argument("--entry-tf", default="M30")
    parser.add_argument("--zone-data")
    parser.add_argument("--entry-data")
    parser.add_argument("--volume", type=float, default=0.10)
    parser.add_argument("--trailing-activation-r", type=float, default=None)
    parser.add_argument("--tp-ratio", type=float, default=None)
    parser.add_argument("--partial", choices=["off", "on"], default=None)
    args = parser.parse_args()

    base = Path("data/backtest")
    zone_data = args.zone_data or str(base / f"{args.symbol}_{args.zone_tf}.csv")
    entry_data = args.entry_data or str(base / f"{args.symbol}_{args.entry_tf}.csv")

    engine = MTFBacktestEngine(
        symbol=args.symbol,
        zone_tf=args.zone_tf,
        entry_tf=args.entry_tf,
        zone_data_path=zone_data,
        entry_data_path=entry_data,
        open_volume=args.volume,
        overrides=_build_overrides(args),
    )
    await engine.run()


if __name__ == "__main__":
    asyncio.run(main())
