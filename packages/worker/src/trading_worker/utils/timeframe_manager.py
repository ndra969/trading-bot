"""
TimeframeManager - Utility for managing timeframe hierarchies and alignments.

Used by MTF strategy to ensure proper timeframe relationships.
"""

from datetime import datetime


class TimeframeManager:
    """Manage timeframe hierarchies, alignment, and validation for MTF strategy."""

    # Timeframe hierarchy (lower to higher)
    TIMEFRAMES = {
        "M1": 1,
        "M5": 5,
        "M15": 15,
        "M30": 30,
        "H1": 60,
        "H4": 240,
        "D1": 1440,
    }

    def rank(self, timeframe: str) -> int:
        """
        Get numeric rank of timeframe.

        Args:
            timeframe: Timeframe string (e.g., 'H1', 'M30')

        Returns:
            Rank (minutes)

        Raises:
            ValueError: If timeframe is unknown
        """
        if timeframe not in self.TIMEFRAMES:
            raise ValueError(f"Unknown timeframe: {timeframe}")
        return self.TIMEFRAMES[timeframe]

    def is_lower(self, tf1: str, tf2: str) -> bool:
        """
        Check if tf1 is lower timeframe than tf2.

        Args:
            tf1: First timeframe
            tf2: Second timeframe

        Returns:
            True if tf1 < tf2
        """
        return self.rank(tf1) < self.rank(tf2)

    def to_minutes(self, timeframe: str) -> int:
        """
        Convert timeframe to minutes.

        Args:
            timeframe: Timeframe string

        Returns:
            Number of minutes
        """
        return self.rank(timeframe)

    def candles_per_higher_tf(self, lower_tf: str, higher_tf: str) -> int:
        """
        Calculate how many lower TF candles fit in one higher TF candle.

        Args:
            lower_tf: Lower timeframe
            higher_tf: Higher timeframe

        Returns:
            Number of lower TF candles per higher TF candle
        """
        return self.to_minutes(higher_tf) // self.to_minutes(lower_tf)

    def is_aligned(self, entry_tf: str, zone_tf: str, timestamp: datetime) -> bool:
        """
        Check if entry timeframe candle is aligned with zone timeframe.

        Alignment means this timestamp marks an entry TF candle close.
        For MTF strategy, we check entries at every entry TF candle close.
        For example, M30 closes at :00 and :30, both are valid alignment points for H1.

        Args:
            entry_tf: Entry timeframe (must be lower)
            zone_tf: Zone timeframe (must be higher)
            timestamp: Timestamp to check

        Returns:
            True if timestamp marks an entry TF candle close
        """
        entry_minutes = self.to_minutes(entry_tf)

        # Calculate total minutes since start of day
        total_minutes = timestamp.hour * 60 + timestamp.minute

        # Check if this timestamp marks the close of an entry TF candle
        is_entry_close = (total_minutes % entry_minutes) == 0

        return is_entry_close

    def validate_mtf_pair(self, entry_tf: str, zone_tf: str) -> None:
        """
        Validate that MTF pair is valid (entry < zone).

        Args:
            entry_tf: Entry timeframe
            zone_tf: Zone timeframe

        Raises:
            ValueError: If configuration is invalid
        """
        if entry_tf == zone_tf:
            raise ValueError(f"Entry and zone cannot be same timeframe: {entry_tf}")

        if not self.is_lower(entry_tf, zone_tf):
            raise ValueError(
                f"Entry timeframe ({entry_tf}) must be lower than zone timeframe ({zone_tf})"
            )
