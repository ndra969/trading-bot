"""
Enhanced Signal Validator - Week 15.5.3

Implements strict entry quality filters to improve win rate from 39% to 50%+.

Key improvements:
- Minimum 75% confluence (raised from 65%)
- Trend alignment validation (H4 and D1 must align)
- Volatility filter (reject if ATR > 1.5x average)
- Market condition filters (news, spread)
"""

from dataclasses import dataclass, field
from enum import Enum


class TrendDirection(Enum):
    """Trend direction enum."""

    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


@dataclass
class ValidationResult:
    """Signal validation result."""

    is_valid: bool
    rejection_reasons: list[str] = field(default_factory=list)
    quality_score: float = 0.0

    def add_rejection(self, reason: str):
        """Add rejection reason."""
        self.is_valid = False
        self.rejection_reasons.append(reason)


class SignalValidatorEnhanced:
    """
    Enhanced signal validator with strict entry quality filters.

    Validates trading signals against multiple criteria:
    - Minimum confluence threshold
    - Trend alignment (H4/D1)
    - Volatility conditions
    - Market conditions (news, spread)

    Usage:
        validator = SignalValidatorEnhanced(config)
        result = validator.validate_signal(signal)
        if result.is_valid:
            # Execute trade
    """

    def __init__(self, config: dict = None):
        """
        Initialize signal validator.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        strategy_config = self.config.get("strategy", {})

        # Load configuration
        self.min_confluence = strategy_config.get("min_confluence_score", 75.0)
        self.trend_alignment_required = strategy_config.get("trend_alignment_required", True)
        self.volatility_filter_enabled = strategy_config.get("volatility_filter_enabled", True)
        self.max_atr_multiplier = strategy_config.get("max_atr_multiplier", 1.5)
        self.news_event_filter_enabled = strategy_config.get("news_event_filter_enabled", True)
        self.spread_filter_enabled = strategy_config.get("spread_filter_enabled", True)
        self.max_spread_pips = strategy_config.get("max_spread_pips", 3.0)

    def validate_signal(self, signal: dict) -> ValidationResult:
        """
        Validate a trading signal against all filters.

        Args:
            signal: Signal dictionary with confluence, direction, etc.

        Returns:
            ValidationResult with validity and rejection reasons
        """
        result = ValidationResult(is_valid=True)

        # Check 1: Minimum confluence
        if signal.get("final_confidence", 0.0) < self.min_confluence:
            result.add_rejection("low_confluence")

        # Check 2: Trend alignment
        if self.trend_alignment_required:
            if not self.check_trend_alignment(signal):
                result.add_rejection("trend_misalignment")

        # Check 3: Volatility
        if self.volatility_filter_enabled:
            if not self.check_volatility(signal):
                result.add_rejection("extreme_volatility")

        # Check 4: Market conditions
        if not self.check_market_conditions(signal):
            result.add_rejection("poor_market_conditions")

        # Check 5: Spread
        if self.spread_filter_enabled:
            if not self.check_spread(signal):
                result.add_rejection("wide_spread")

        # Calculate quality score
        if result.is_valid:
            result.quality_score = self._calculate_quality_score(signal)

        return result

    def check_trend_alignment(self, signal: dict) -> bool:
        """
        Check if signal aligns with H4 and D1 trend.

        Args:
            signal: Signal dictionary with symbol and direction

        Returns:
            True if trend aligned, False otherwise
        """
        if not self.trend_alignment_required:
            return True

        symbol = signal.get("symbol", "")
        direction = signal.get("direction", "")

        # Get H4 and D1 trends
        h4_trend = self.get_trend_direction(symbol, "H4")
        d1_trend = self.get_trend_direction(symbol, "D1")

        # BUY requires bullish trends
        if direction == "BUY":
            return h4_trend == TrendDirection.BULLISH and d1_trend == TrendDirection.BULLISH

        # SELL requires bearish trends
        elif direction == "SELL":
            return h4_trend == TrendDirection.BEARISH and d1_trend == TrendDirection.BEARISH

        return False

    def get_trend_direction(self, symbol: str, timeframe: str) -> TrendDirection:
        """
        Get trend direction for a symbol and timeframe.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe (H4, D1)

        Returns:
            TrendDirection enum
        """
        # TODO: Implement actual trend calculation
        # This would analyze moving averages, higher highs/lows, etc.
        # For now, return NEUTRAL as placeholder
        return TrendDirection.NEUTRAL

    def check_volatility(self, signal: dict) -> bool:
        """
        Check if current volatility is acceptable.

        Rejects signal if ATR > 1.5x average ATR.

        Args:
            signal: Signal dictionary with symbol

        Returns:
            True if volatility acceptable, False if too high
        """
        if not self.volatility_filter_enabled:
            return True

        symbol = signal.get("symbol", "")

        # Get current and average ATR
        current_atr = self.get_atr(symbol)
        average_atr = self.get_average_atr(symbol)

        if current_atr is None or average_atr is None or average_atr == 0:
            # Cannot determine, allow signal
            return True

        # Check if current ATR exceeds threshold
        atr_ratio = current_atr / average_atr

        return atr_ratio <= self.max_atr_multiplier

    def get_atr(self, symbol: str, period: int = 14) -> float | None:
        """
        Get current ATR for a symbol.

        Args:
            symbol: Trading symbol
            period: ATR period

        Returns:
            Current ATR value or None
        """
        # TODO: Implement actual ATR calculation from market data
        # For now, return None to indicate unavailable
        return None

    def get_average_atr(self, symbol: str, lookback_periods: int = 20) -> float | None:
        """
        Get average ATR over lookback period.

        Args:
            symbol: Trading symbol
            lookback_periods: Number of periods to average

        Returns:
            Average ATR value or None
        """
        # TODO: Implement actual average ATR calculation
        # For now, return None to indicate unavailable
        return None

    def check_market_conditions(self, signal: dict) -> bool:
        """
        Check general market conditions.

        Checks for news events and other conditions.

        Args:
            signal: Signal dictionary

        Returns:
            True if conditions acceptable, False otherwise
        """
        # Check news events
        if self.news_event_filter_enabled:
            if self.is_news_event():
                return False

        return True

    def is_news_event(self) -> bool:
        """
        Check if high-impact news event is occurring.

        Returns:
            True if news event detected, False otherwise
        """
        # TODO: Implement actual news event detection
        # This would check economic calendar API
        # For now, return False (no news)
        return False

    def check_spread(self, signal: dict) -> bool:
        """
        Check if spread is acceptable.

        Args:
            signal: Signal dictionary with symbol

        Returns:
            True if spread acceptable, False if too wide
        """
        if not self.spread_filter_enabled:
            return True

        symbol = signal.get("symbol", "")
        current_spread = self.get_current_spread(symbol)

        if current_spread is None:
            # Cannot determine, allow signal
            return True

        return current_spread <= self.max_spread_pips

    def get_current_spread(self, symbol: str) -> float | None:
        """
        Get current spread for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Current spread in pips or None
        """
        # TODO: Implement actual spread fetching from MT5
        # For now, return None to indicate unavailable
        return None

    def _calculate_quality_score(self, signal: dict) -> float:
        """
        Calculate overall quality score for a signal.

        Args:
            signal: Signal dictionary

        Returns:
            Quality score (0-100)
        """
        # Base score from confluence
        score = signal.get("final_confidence", 0.0)

        # Bonus for high risk:reward
        rr_ratio = signal.get("risk_reward_ratio", 1.0)
        if rr_ratio >= 2.0:
            score += 10.0
        elif rr_ratio >= 1.5:
            score += 5.0

        # Cap at 100
        return min(100.0, score)

    def __str__(self) -> str:
        """String representation."""
        return (
            f"SignalValidatorEnhanced("
            f"min_confluence={self.min_confluence}%, "
            f"trend_required={self.trend_alignment_required}, "
            f"volatility_filter={self.volatility_filter_enabled})"
        )

    def __repr__(self) -> str:
        """Developer representation."""
        return self.__str__()
