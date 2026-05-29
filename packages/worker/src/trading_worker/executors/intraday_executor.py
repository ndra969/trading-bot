"""
Intraday trading executor.

This executor implements day trading strategy with:
- H1 timeframe for zone detection
- M30 timeframe for entry signals
- H1 trend filter (Sniper) for commodities
- End-of-day position closure
"""

import asyncio
from datetime import datetime
from typing import Any

import pandas as pd
from trading_core.utils.logger import get_logger

from trading_worker.executors.base_executor import TradingTypeExecutor

logger = get_logger(__name__)


class IntradayExecutor(TradingTypeExecutor):
    """
    Intraday (Day Trading) executor.

    Implements multi-timeframe day trading strategy:
    - Zone detection on H1 timeframe
    - Entry confirmation on M30 timeframe
    - H1 EMA trend filter for commodities (Sniper gate)
    - All positions closed before end of trading day
    """

    def __init__(
        self, config: dict[str, Any], foundation_engine: Any, position_manager: Any
    ) -> None:
        """
        Initialize intraday executor.

        Args:
            config: Configuration dictionary
            foundation_engine: Foundation strategy engine instance
            position_manager: Position manager instance
        """
        super().__init__(config, foundation_engine, position_manager)
        logger.info("IntradayExecutor initialized (H1 zones, M30 entries)")

    async def initialize(self) -> None:
        """
        Initialize intraday-specific components.

        Sets up:
        - Pip calculator for asset-specific pip values
        - Zone cache for H1 zones
        - Configuration for cache duration
        """
        from trading_worker.position.pip_calculator import PipCalculator

        self.pip_calculator = PipCalculator()

        # Zone cache — refresh H1 zones at the configured interval. Reads from
        # trading.mtf.zone_cache_duration_minutes; falls back to 60 minutes.
        self.zone_cache: dict[str, tuple[list, datetime]] = {}
        self.zone_cache_duration_minutes = (
            self.config.get("trading", {}).get("mtf", {}).get("zone_cache_duration_minutes", 60)
        )

        logger.info(
            f"IntradayExecutor initialization complete "
            f"(zone cache: {self.zone_cache_duration_minutes} min)"
        )

    async def execute_trading_loop(self, symbols: list[str]) -> None:
        """
        Execute the intraday trading loop.

        Behavior:
        1. Scan every M30 candle close
        2. Check H1 zones (cached for 1 hour)
        3. Look for M30 entry confirmation
        4. Apply H1 trend filter for commodities
        5. Close all positions before end of trading day

        Args:
            symbols: List of symbols to trade
        """
        logger.info("Starting intraday trading loop (H1/M30 MTF)")

        # TODO: Implement full trading loop
        # This is a stub implementation for testing
        pass

    async def analyze_symbol(self, symbol: str, current_time: Any) -> dict[str, Any] | None:
        """
        Analyze a symbol for intraday trading opportunities.

        Steps:
        1. Get/refresh H1 zones
        2. Get current M30 price data
        3. Check if price is at a zone
        4. Apply H1 trend filter (commodities only)
        5. Validate M30 price action
        6. Generate signal if all conditions met

        Args:
            symbol: Symbol to analyze
            current_time: Current datetime for analysis

        Returns:
            Signal dictionary if entry conditions met, None otherwise
        """
        # TODO: Implement symbol analysis
        # This is a stub implementation for testing
        return None

    def get_timeframes(self) -> dict[str, str]:
        """
        Get timeframes used by intraday executor.

        Returns:
            Dictionary with timeframe configuration
        """
        return {
            "zone_timeframe": "H1",
            "entry_timeframe": "M30",
            "trend_timeframe": "H1",
        }

    def get_technical_indicators(self) -> dict[str, dict[str, Any]]:
        """
        Get technical indicators used by intraday executor.

        Returns:
            Dictionary with indicator configurations
        """
        return {
            "ema": {"fast": 20, "slow": 50, "trend": 200},
            "rsi": {"period": 14, "overbought": 70, "oversold": 30},
            "breakeven": {"trigger_r": 0.7, "offset_pips": 2.0},
            "trailing": {"activation_pips": 30.0, "limit_pips": 10.0},
        }

    async def _get_h1_trend_bias(self, symbol: str, current_time: datetime) -> str | None:
        """
        Get H1 trend bias using EMA 50/20 (Sniper Gate).

        Only applies to commodities (Gold, Silver, etc.).

        Logic extracted from run_mtf_backtest.py lines 174-238:
        1. Check if symbol is commodity
        2. Get H1 data (prevent lookahead bias)
        3. Calculate EMA 50 and EMA 20
        4. Determine trend based on Price vs EMA 50
        5. Apply momentum protection (2 consecutive candles)

        Args:
            symbol: Trading symbol (e.g., 'XAUUSD')
            current_time: Current datetime for analysis

        Returns:
            'BULLISH', 'BEARISH', 'NEUTRAL', or None (if not commodity)
        """
        # Check asset class
        asset_class = self.pip_calculator.symbol_mapper.get_asset_class(symbol)
        if asset_class != "commodities":
            return None

        # Get H1 data
        h1_data = await self.foundation_engine.get_market_data(symbol, "H1", 100)
        if len(h1_data) < 50:
            return None

        # FIX: Prevent Lookahead Bias
        # Only use H1 candles that have FULLY CLOSED
        # Standard H1 candle at 10:00 closes at 11:00
        # So at 10:30, we must NOT see 10:00 candle
        h1_safe_time = current_time - pd.Timedelta(hours=1)
        h1_mask = h1_data.index <= h1_safe_time
        h1_hist = h1_data[h1_mask]

        if len(h1_hist) < 50:
            return None

        # Multi-Stage Trend Verification
        h1_ema_50 = h1_hist["close"].ewm(span=50, adjust=False).mean()
        h1_ema_20 = h1_hist["close"].ewm(span=20, adjust=False).mean()

        ema_50_curr = h1_ema_50.iloc[-1]
        ema_50_prev = h1_ema_50.iloc[-2]
        _ema_20_curr = h1_ema_20.iloc[-1]  # Calculated for future use

        current_price = float(h1_hist.iloc[-1]["close"])

        # Slope calculation (kept for reference, new logic uses Price vs EMA 50)
        _slope_up = ema_50_curr > ema_50_prev
        _slope_down = ema_50_curr < ema_50_prev

        # Trend Gate Logic (Fixed per user feedback)
        # New Logic: Strict Price vs EMA 50
        # If Price > EMA 50, strictly BULLISH (Block SELLS)
        # If Price < EMA 50, strictly BEARISH (Block BUYS)
        is_bullish = current_price > ema_50_curr
        is_bearish = current_price < ema_50_curr

        if is_bullish:
            h1_trend_bias = "BULLISH"
        elif is_bearish:
            h1_trend_bias = "BEARISH"
        else:
            h1_trend_bias = "NEUTRAL"

        # Momentum Protection
        # Even if Price > EMA, if H1 is crashing, don't BUY
        if len(h1_hist) >= 3:
            c_curr = h1_hist["close"].iloc[-1]
            c_p1 = h1_hist["close"].iloc[-2]
            c_p2 = h1_hist["close"].iloc[-3]

            # If two consecutive red candles, block BUY
            if h1_trend_bias == "BULLISH" and c_curr < c_p1 and c_p1 < c_p2:
                logger.warning(
                    "SNIPER: Blocking BULLISH bias due to H1 Bearish Momentum (Crash protection)"
                )
                h1_trend_bias = "NEUTRAL"
            # If two consecutive green candles, block SELL
            if h1_trend_bias == "BEARISH" and c_curr > c_p1 and c_p1 > c_p2:
                logger.warning("SNIPER: Blocking BEARISH bias due to H1 Bullish Momentum")
                h1_trend_bias = "NEUTRAL"

        logger.info(
            f"SNIPER BIAS: {current_time} | Price: {current_price:.2f} | H1 EMA50: {ema_50_curr:.2f} | Bias: {h1_trend_bias}"
        )

        return h1_trend_bias

    async def _get_or_refresh_zones(
        self, symbol: str, timeframe: str, current_time: datetime
    ) -> list:
        """
        Get zones from cache or refresh if expired.

        Zones are cached for zone_cache_duration_minutes (60 minutes)
        to optimize performance.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe for zone detection (e.g., 'H1')
            current_time: Current datetime for cache age calculation

        Returns:
            List of zones detected on the timeframe
        """
        cache_key = f"{symbol}_{timeframe}"

        # Check cache
        if cache_key in self.zone_cache:
            cached_zones, cached_time = self.zone_cache[cache_key]
            age_minutes = (current_time - cached_time).total_seconds() / 60

            if age_minutes < self.zone_cache_duration_minutes:
                logger.debug(f"Using cached zones for {symbol} (age: {age_minutes:.1f}m)")
                return cached_zones

        # Refresh zones
        data = await self.foundation_engine.get_market_data(symbol, timeframe, 200)
        zones = await self.foundation_engine.analyze_symbol(
            symbol, data, timeframe, reference_time=current_time
        )

        # Update cache
        self.zone_cache[cache_key] = (zones, current_time)
        logger.info(f"Refreshed {len(zones)} zones for {symbol} on {timeframe}")

        return zones

    async def _wait_for_next_candle(self, timeframe: str) -> None:
        """
        Wait for next candle close.

        Args:
            timeframe: Timeframe to wait for (e.g., 'M30', 'H1')
        """
        wait_seconds = {
            "M1": 60,
            "M5": 300,
            "M15": 900,
            "M30": 1800,
            "H1": 3600,
            "H4": 14400,
        }
        wait_time = wait_seconds.get(timeframe, 1800)
        logger.debug(f"Waiting {wait_time}s for next {timeframe} candle")
        await asyncio.sleep(wait_time)

    async def should_close_all_positions(self, current_time: datetime) -> bool:
        """
        Check if all positions should be closed (end of trading day).

        Args:
            current_time: Current datetime

        Returns:
            True if positions should be closed
        """
        # Close at 23:30 UTC (before NY market close)
        return current_time.hour == 23 and current_time.minute >= 30
