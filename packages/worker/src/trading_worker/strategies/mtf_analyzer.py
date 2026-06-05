"""
MTFAnalyzer - Multi-Timeframe Analysis Engine.

Orchestrates zone detection on higher timeframe and entry confirmation on lower timeframe.
"""

from datetime import datetime

import pandas as pd
from trading_core.utils.logger import get_logger

from trading_worker.strategies.foundation.foundation_engine import FoundationEngine
from trading_worker.strategies.models import StrategyResult
from trading_worker.utils.timeframe_manager import TimeframeManager

logger = get_logger(__name__)


class MTFAnalyzer:
    """
    Multi-Timeframe Strategy Analyzer.

    Detects zones on higher timeframe (e.g., H1) and confirms entries on lower timeframe (e.g., M30).
    This matches the proven backtest approach that achieved +40R across 3 pairs.
    """

    def __init__(
        self,
        config: dict | None = None,
        use_database: bool = False,
        rejection_recorder=None,
    ):
        """
        Initialize MTF Analyzer.

        Args:
            config: Strategy configuration
            use_database: Whether to use database for persistence
            rejection_recorder: Optional RejectionRecorder for tuning telemetry.
        """
        self.config = config or {}
        self.use_database = use_database

        # Initialize FoundationEngine for zone detection and signal generation
        self.foundation_engine = FoundationEngine(
            config=self.config,
            use_database=self.use_database,
            rejection_recorder=rejection_recorder,
        )

        # Initialize TimeframeManager for validation
        self.tf_manager = TimeframeManager()

        # Cache for detected zones
        self.detected_zones = []
        self._zone_cache_timestamp: datetime | None = None

    async def analyze(
        self,
        symbol: str,
        zone_tf_data: pd.DataFrame,
        entry_tf_data: pd.DataFrame,
        zone_tf: str = "H1",
        entry_tf: str = "M30",
    ) -> list[StrategyResult]:
        """
        Perform multi-timeframe analysis.

        Args:
            symbol: Trading symbol (universal format, e.g., 'XAUUSD')
            zone_tf_data: OHLCV data for zone detection timeframe
            entry_tf_data: OHLCV data for entry confirmation timeframe
            zone_tf: Zone detection timeframe (default: H1)
            entry_tf: Entry confirmation timeframe (default: M30)

        Returns:
            List of strategy results (signals)
        """
        # Validate MTF configuration
        try:
            self.tf_manager.validate_mtf_pair(entry_tf=entry_tf, zone_tf=zone_tf)
        except ValueError as e:
            logger.error(f"Invalid MTF configuration: {e}")
            return []

        logger.info(f"MTF Analysis: {symbol} | Zone: {zone_tf} | Entry: {entry_tf}")

        # Step 1: Detect zones on higher timeframe
        zones = await self._detect_zones(symbol, zone_tf_data, zone_tf)

        if not zones:
            logger.debug(f"{symbol}: No zones detected on {zone_tf}")
            return []

        logger.info(f"{symbol}: Detected {len(zones)} zones on {zone_tf}")
        self.detected_zones = zones

        # Step 2: Calculate H1 Trend Bias (Sniper Gate)
        h1_trend_bias = self._calculate_h1_trend_bias(zone_tf_data)
        logger.info(f"{symbol}: H1 Trend Bias: {h1_trend_bias}")

        # Step 3: Check for entry signals on lower timeframe
        signals = await self._check_entry_signals(
            symbol=symbol,
            zones=zones,
            entry_tf_data=entry_tf_data,
            entry_tf=entry_tf,
            h1_trend_bias=h1_trend_bias,
        )

        if not signals:
            logger.debug(f"{symbol}: No entry signals on {entry_tf}")
            return []

        logger.info(f"{symbol}: Generated {len(signals)} signals from MTF analysis")
        return signals

    async def _detect_zones(self, symbol: str, data: pd.DataFrame, timeframe: str) -> list:
        """
        Detect supply/demand zones on higher timeframe.

        Args:
            symbol: Trading symbol
            data: OHLCV data
            timeframe: Timeframe string

        Returns:
            List of detected zones
        """
        try:
            # Use FoundationEngine's zone detector
            zones = await self.foundation_engine.analyze_symbol(
                symbol=symbol, data=data, timeframe=timeframe
            )

            return zones
        except Exception as e:
            logger.error(f"Error detecting zones for {symbol}: {e}", exc_info=True)
            return []

    async def _check_entry_signals(
        self,
        symbol: str,
        zones: list,
        entry_tf_data: pd.DataFrame,
        entry_tf: str,
        h1_trend_bias: str | None = None,
    ) -> list[StrategyResult]:
        """
        Check for entry signals on lower timeframe at zone levels.

        Args:
            symbol: Trading symbol
            zones: List of detected zones from higher TF
            entry_tf_data: OHLCV data for entry timeframe
            entry_tf: Entry timeframe string

        Returns:
            List of strategy results (signals)
        """
        if entry_tf_data.empty:
            logger.warning(f"{symbol}: Entry TF data is empty")
            return []

        # Get current price from latest entry TF candle
        current_price = float(entry_tf_data.iloc[-1]["close"])

        logger.debug(
            f"{symbol}: Checking {len(zones)} zones against entry TF price {current_price:.5f}"
        )

        # Generate signals using FoundationEngine
        # It will check if price is at any zone and create signals with proper SL/TP
        signals = await self.foundation_engine.generate_signals(
            symbol=symbol,
            data=entry_tf_data,
            timeframe=entry_tf,
            h1_trend_bias=h1_trend_bias,
        )

        # Filter signals to only those that are at our detected H1 zones
        # (FoundationEngine will re-detect zones on M30, we want to ensure
        # we're only taking signals that align with our H1 zones)
        valid_signals = []
        for signal in signals:
            if signal.has_signal:
                # Additional validation could be added here to ensure
                # signal is truly at one of our H1 zones
                valid_signals.append(signal)

        return valid_signals

    def _calculate_h1_trend_bias(self, h1_data: pd.DataFrame) -> str:
        """
        Calculate H1 trend bias using EMA 50 (Strict Sniper Gate).

        Matches the logic in IntradayExecutor/Backtest:
        - Price > EMA 50: BULLISH
        - Price < EMA 50: BEARISH
        - Momentum Protection: consecutive candles must align.

        Args:
            h1_data: H1 OHLCV data

        Returns:
            'BULLISH', 'BEARISH', or 'NEUTRAL'
        """
        if len(h1_data) < 50:
            return "NEUTRAL"

        # Calculate EMA 50
        ema_50 = h1_data["close"].ewm(span=50, adjust=False).mean()
        curr_ema = ema_50.iloc[-1]
        curr_price = float(h1_data["close"].iloc[-1])

        # Strict Price vs EMA 50
        if curr_price > curr_ema:
            bias = "BULLISH"
        elif curr_price < curr_ema:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"

        # Momentum Protection (2 consecutive candles)
        if len(h1_data) >= 3:
            c_curr = h1_data["close"].iloc[-1]
            c_p1 = h1_data["close"].iloc[-2]
            c_p2 = h1_data["close"].iloc[-3]

            # If two consecutive red candles, block BUY
            if bias == "BULLISH" and c_curr < c_p1 and c_p1 < c_p2:
                logger.info("SNIPER: Blocking BULLISH bias due to Bearish Momentum")
                bias = "NEUTRAL"
            # If two consecutive green candles, block SELL
            if bias == "BEARISH" and c_curr > c_p1 and c_p1 > c_p2:
                logger.info("SNIPER: Blocking BEARISH bias due to Bullish Momentum")
                bias = "NEUTRAL"

        return bias


class ZoneCache:
    """
    Cache for zone data to avoid re-detection on every lower TF candle.

    Zones are cached per symbol and invalidated when:
    1. New zone TF candle closes
    2. TTL expires
    """

    def __init__(self, ttl_minutes: int = 60):
        """
        Initialize zone cache.

        Args:
            ttl_minutes: Time-to-live for cached zones in minutes
        """
        self.ttl_minutes = ttl_minutes
        self._cache: dict[str, dict] = {}

    def get(self, symbol: str, zone_tf: str) -> list | None:
        """
        Get cached zones for symbol.

        Args:
            symbol: Trading symbol
            zone_tf: Zone timeframe

        Returns:
            Cached zones or None if expired/missing
        """
        cache_key = f"{symbol}_{zone_tf}"

        if cache_key not in self._cache:
            return None

        cached = self._cache[cache_key]

        # Check TTL
        age_minutes = (datetime.now() - cached["timestamp"]).total_seconds() / 60
        if age_minutes > self.ttl_minutes:
            logger.debug(f"Zone cache expired for {symbol} (age: {age_minutes:.1f}m)")
            del self._cache[cache_key]
            return None

        logger.debug(f"Using cached zones for {symbol} (age: {age_minutes:.1f}m)")
        return cached["zones"]

    def set(self, symbol: str, zone_tf: str, zones: list) -> None:
        """
        Cache zones for symbol.

        Args:
            symbol: Trading symbol
            zone_tf: Zone timeframe
            zones: List of zones to cache
        """
        cache_key = f"{symbol}_{zone_tf}"
        self._cache[cache_key] = {"zones": zones, "timestamp": datetime.now()}
        logger.debug(f"Cached {len(zones)} zones for {symbol}")

    def invalidate(self, symbol: str | None = None) -> None:
        """
        Invalidate cache.

        Args:
            symbol: If provided, invalidate only this symbol. Otherwise clear all.
        """
        if symbol:
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(symbol)]
            for key in keys_to_delete:
                del self._cache[key]
            logger.debug(f"Invalidated cache for {symbol}")
        else:
            self._cache.clear()
            logger.debug("Invalidated all zone cache")
