import logging
import sys
from pathlib import Path

import pandas as pd
from trading_bot.strategies.foundation.zone_detector import ZoneDetector


def run_debug():
    # Configure logging
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout, force=True)

    symbol = "XAUUSDc"
    DATA_DIR = Path("d:/Workspaces/trading-bot/data/backtest")
    file_path = DATA_DIR / f"{symbol}_H1.csv"

    if not file_path.exists():
        print(f"Data file not found: {file_path}")
        return

    df = pd.read_csv(file_path)
    df.columns = [c.lower().strip() for c in df.columns]

    if "timestamp" in df.columns:
        df["time"] = pd.to_datetime(df["timestamp"])
    elif "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"])

    if "time" in df.columns:
        df = df.set_index("time")

    if "tick_volume" in df.columns and "volume" not in df.columns:
        df["volume"] = df["tick_volume"]

    print(f"Loaded {len(df)} candles")

    # Inject pattern
    if len(df) > 60:
        target_idx = 60
        ref_close = df["close"].iloc[target_idx - 1]

        # Consistent with test modification
        candle_range = ref_close * 0.01
        new_high = ref_close + candle_range
        new_low = ref_close - (candle_range * 0.1)
        new_open = ref_close
        new_close = ref_close

        df.iloc[target_idx, df.columns.get_loc("high")] = new_high
        df.iloc[target_idx, df.columns.get_loc("low")] = new_low
        df.iloc[target_idx, df.columns.get_loc("open")] = new_open
        df.iloc[target_idx, df.columns.get_loc("close")] = new_close
        df.iloc[target_idx, df.columns.get_loc("volume")] = 100000000

        print(
            f"Injected at {target_idx}: High {new_high:.2f}, Low {new_low:.2f}, Open/Close {new_open:.2f}"
        )

    # Config
    config = {
        "max_zone_age_hours": 999999,
        "min_zone_strength": 5.0,
        "max_zone_size_pips": 5000,
        "min_wick_ratio": 0.1,
        "volume_confirmation": False,
        "max_body_size_pct": 80,  # Ensure this is high enough
        "min_zone_size_pips": 1,  # Ensure this is low enough
    }

    detector = ZoneDetector(config)
    zones = detector.detect_zones(df)

    print(f"Detected {len(zones)} zones")
    for z in zones:
        print(z)


if __name__ == "__main__":
    run_debug()
