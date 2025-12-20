"""
Technical Analyzer Module

This module provides a unified interface for calculating technical indicators
using various libraries (pandas-ta, ta, talib) with a robust fallback mechanism.
It is designed to be the foundation for the Technical Indicators Layer in Phase 5.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

# Configure logger
logger = logging.getLogger(__name__)


class TechnicalIndicatorCalculator:
    """
    Primary calculator using pandas-ta (most reliable for this project).
    """

    def __init__(self, cache_duration_minutes: int = 5):
        self.cache: dict[str, Any] = {}
        self.cache_duration = timedelta(minutes=cache_duration_minutes)

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self.cache:
            return False
        return datetime.now() < self.cache[cache_key]["expires"]

    def _cache_result(self, cache_key: str, data: Any):
        """Cache calculation result."""
        self.cache[cache_key] = {
            "data": data,
            "timestamp": datetime.now(),
            "expires": datetime.now() + self.cache_duration,
        }

    def calculate_multiple_indicators(
        self,
        prices: list[float],
        high: list[float] = None,
        low: list[float] = None,
        volume: list[float] = None,
    ) -> dict[str, list[float]]:
        """
        Calculate multiple indicators efficiently using pandas-ta.

        Args:
            prices: List of closing prices
            high: List of high prices (optional, defaults to close)
            low: List of low prices (optional, defaults to close)
            volume: List of volumes (optional, defaults to 1)

        Returns:
            Dictionary containing indicator lists
        """
        if not prices:
            return {}

        # Create DataFrame for multiple indicator calculation
        df = pd.DataFrame(
            {
                "close": prices,
                "high": high if high is not None else prices,
                "low": low if low is not None else prices,
                "volume": volume if volume is not None else [1.0] * len(prices),
            }
        )

        try:
            import pandas_ta  # noqa: F401

            # Calculate all indicators at once
            # RSI (14)
            df.ta.rsi(length=14, append=True)

            # EMAs (9, 21, 50)
            df.ta.ema(length=9, append=True)
            df.ta.ema(length=21, append=True)
            df.ta.ema(length=50, append=True)

            # SMA (200)
            df.ta.sma(length=200, append=True)

            # MACD (12, 26, 9)
            df.ta.macd(append=True)

            # Bollinger Bands (20, 2)
            df.ta.bbands(append=True)

            # ATR (14)
            df.ta.atr(length=14, append=True)

            # Extract results safely
            results = {
                "rsi": df["RSI_14"].dropna().tolist() if "RSI_14" in df.columns else [],
                "ema_9": df["EMA_9"].dropna().tolist() if "EMA_9" in df.columns else [],
                "ema_21": df["EMA_21"].dropna().tolist() if "EMA_21" in df.columns else [],
                "ema_50": df["EMA_50"].dropna().tolist() if "EMA_50" in df.columns else [],
                "sma_200": df["SMA_200"].dropna().tolist() if "SMA_200" in df.columns else [],
                "macd": (
                    df["MACD_12_26_9"].dropna().tolist() if "MACD_12_26_9" in df.columns else []
                ),
                "macd_signal": (
                    df["MACDs_12_26_9"].dropna().tolist() if "MACDs_12_26_9" in df.columns else []
                ),
                "macd_hist": (
                    df["MACDh_12_26_9"].dropna().tolist() if "MACDh_12_26_9" in df.columns else []
                ),
                "bb_upper": (
                    df["BBU_20_2.0"].dropna().tolist() if "BBU_20_2.0" in df.columns else []
                ),
                "bb_lower": (
                    df["BBL_20_2.0"].dropna().tolist() if "BBL_20_2.0" in df.columns else []
                ),
                "bb_mid": df["BBM_20_2.0"].dropna().tolist() if "BBM_20_2.0" in df.columns else [],
                "atr": df["ATRr_14"].dropna().tolist() if "ATRr_14" in df.columns else [],
            }

            return results

        except ImportError:
            logger.error("pandas-ta not installed")
            raise
        except Exception as e:
            logger.error(f"Error calculating indicators with pandas-ta: {e}")
            raise


class TALibIndicatorCalculator:
    """
    Alternative implementation using 'ta' library (pure Python) as fallback.
    """

    def __init__(self):
        try:
            from ta import momentum, trend, volatility, volume

            self.trend = trend
            self.momentum = momentum
            self.volume = volume
            self.volatility = volatility
        except ImportError:
            logger.error("'ta' library not installed")
            raise

    def calculate_indicators(self, df: pd.DataFrame) -> dict[str, list[float]]:
        """Calculate indicators using 'ta' library."""
        results = {}

        try:
            # RSI
            results["rsi"] = (
                self.momentum.RSIIndicator(close=df["close"], window=14).rsi().dropna().tolist()
            )

            # EMAs
            results["ema_9"] = (
                self.trend.EMAIndicator(close=df["close"], window=9)
                .ema_indicator()
                .dropna()
                .tolist()
            )

            results["ema_21"] = (
                self.trend.EMAIndicator(close=df["close"], window=21)
                .ema_indicator()
                .dropna()
                .tolist()
            )

            results["ema_50"] = (
                self.trend.EMAIndicator(close=df["close"], window=50)
                .ema_indicator()
                .dropna()
                .tolist()
            )

            # SMA
            results["sma_200"] = (
                self.trend.SMAIndicator(close=df["close"], window=200)
                .sma_indicator()
                .dropna()
                .tolist()
            )

            # MACD
            macd = self.trend.MACD(close=df["close"])
            results["macd"] = macd.macd().dropna().tolist()
            results["macd_signal"] = macd.macd_signal().dropna().tolist()
            results["macd_hist"] = macd.macd_diff().dropna().tolist()

            # Bollinger Bands
            bb = self.volatility.BollingerBands(close=df["close"], window=20, window_dev=2)
            results["bb_upper"] = bb.bollinger_hband().dropna().tolist()
            results["bb_lower"] = bb.bollinger_lband().dropna().tolist()
            results["bb_mid"] = bb.bollinger_mavg().dropna().tolist()

            # ATR
            atr = self.volatility.AverageTrueRange(
                high=df["high"], low=df["low"], close=df["close"], window=14
            )
            results["atr"] = atr.average_true_range().dropna().tolist()

            return results

        except Exception as e:
            logger.error(f"Error calculating indicators with 'ta' library: {e}")
            raise


class TALibHighPerformance:
    """
    High-performance implementation using TA-Lib (requires compilation).
    Only used if TA-Lib is installed.
    """

    def __init__(self):
        try:
            import talib

            self.talib = talib
            self.available = True
        except ImportError:
            self.available = False
            logger.debug("TA-Lib not available (optional)")

    def calculate_indicators(
        self, prices: list[float], high: list[float] = None, low: list[float] = None
    ) -> dict[str, list[float]]:
        """Calculate indicators using TA-Lib (fastest)."""
        if not self.available:
            raise ImportError("TA-Lib not installed")

        # Convert to numpy array (required by TA-Lib)
        price_array = np.array(prices, dtype=float)
        high_array = np.array(high, dtype=float) if high else price_array
        low_array = np.array(low, dtype=float) if low else price_array

        results = {
            "rsi": self.talib.RSI(price_array, timeperiod=14).tolist(),
            "ema_9": self.talib.EMA(price_array, timeperiod=9).tolist(),
            "ema_21": self.talib.EMA(price_array, timeperiod=21).tolist(),
            "ema_50": self.talib.EMA(price_array, timeperiod=50).tolist(),
            "sma_200": self.talib.SMA(price_array, timeperiod=200).tolist(),
            "macd": self.talib.MACD(price_array)[0].tolist(),
            "macd_signal": self.talib.MACD(price_array)[1].tolist(),
            "macd_hist": self.talib.MACD(price_array)[2].tolist(),
            "atr": self.talib.ATR(high_array, low_array, price_array, timeperiod=14).tolist(),
        }

        # Bollinger Bands
        upper, middle, lower = self.talib.BBANDS(
            price_array, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0
        )
        results["bb_upper"] = upper.tolist()
        results["bb_mid"] = middle.tolist()
        results["bb_lower"] = lower.tolist()

        # Remove NaN values (basic cleaning)
        clean_results = {}
        for key, values in results.items():
            clean_results[key] = [v for v in values if not np.isnan(v)]

        return clean_results


class RobustIndicatorCalculator:
    """
    Wrapper class that manages the fallback chain for indicator calculation.
    Priority: TA-Lib (Fastest) -> pandas-ta (Most Reliable) -> ta (Pure Python Fallback)
    """

    def __init__(self):
        self.primary = None
        self.secondary = None
        self.fallback = None

        self._initialize_calculators()

    def _initialize_calculators(self):
        """Initialize calculators with fallback chain."""

        # 1. Try TA-Lib first (Performance)
        try:
            self.primary = TALibHighPerformance()
            if self.primary.available:
                logger.info("✅ Using TA-Lib for high-performance indicators")
            else:
                self.primary = None
        except Exception:
            pass

        # 2. Try pandas-ta (Reliability)
        try:
            self.secondary = TechnicalIndicatorCalculator()
            if not self.primary:
                logger.info("✅ Using pandas-ta for technical indicators")
        except ImportError:
            logger.warning("pandas-ta not available")

        # 3. Try ta (Fallback)
        try:
            self.fallback = TALibIndicatorCalculator()
            if not self.primary and not self.secondary:
                logger.info("⚠️ Using 'ta' library as fallback")
        except ImportError:
            logger.warning("'ta' library not available")

        if not any([self.primary, self.secondary, self.fallback]):
            logger.error("❌ No technical analysis libraries available!")

    def calculate_all(
        self,
        prices: list[float],
        high: list[float] = None,
        low: list[float] = None,
        volume: list[float] = None,
    ) -> dict[str, list[float]]:
        """
        Calculate all indicators using the best available method.
        """
        # Try Primary (TA-Lib)
        if self.primary and self.primary.available:
            try:
                return self.primary.calculate_indicators(prices, high, low)
            except Exception as e:
                logger.warning(f"Primary calculator failed: {e}. Trying secondary...")

        # Try Secondary (pandas-ta)
        if self.secondary:
            try:
                return self.secondary.calculate_multiple_indicators(prices, high, low, volume)
            except Exception as e:
                logger.warning(f"Secondary calculator failed: {e}. Trying fallback...")

        # Try Fallback (ta)
        if self.fallback:
            try:
                df = pd.DataFrame(
                    {
                        "close": prices,
                        "high": high if high else prices,
                        "low": low if low else prices,
                        "volume": volume if volume else [1.0] * len(prices),
                    }
                )
                return self.fallback.calculate_indicators(df)
            except Exception as e:
                logger.error(f"Fallback calculator failed: {e}")
                raise

        raise RuntimeError("All technical indicator calculators failed")
