"""
Partial Close Manager - Automated partial position closure.

Closes portions of a position at profit targets.
"""

from typing import NamedTuple

from trading_bot.position.pip_calculator import PipCalculator
from trading_bot.position.position_models import Position
from trading_bot.utils.logger import get_logger

logger = get_logger(__name__)


class PartialCloseLevel(NamedTuple):
    """Partial close level configuration."""

    level: int  # Level number (1, 2, etc.)
    distance_pips: float  # Distance from entry in pips
    close_percentage: float  # Percentage to close (0.0 - 1.0)


class PartialCloseManager:
    """
    Manages automated partial position closure.

    Closes portions of position at predefined profit targets:
    - Level 1: Close 25% at first target
    - Level 2: Close 50% of remaining at second target
    - Final: Remaining position runs to TP or SL

    Asset-specific partial close levels:
    - Forex Major: 20 pips / 40 pips
    - Forex JPY: 200 pips / 400 pips
    - Commodities (Gold): 600 pips / 1200 pips
    - Crypto: 100 USD / 200 USD
    """

    # Partial close configurations by asset class
    PARTIAL_CLOSE_CONFIGS = {
        "forex_major": [
            PartialCloseLevel(1, 20.0, 0.25),  # Close 25% at 20 pips
            PartialCloseLevel(2, 40.0, 0.50),  # Close 50% of remaining at 40 pips
        ],
        "forex_jpy": [
            PartialCloseLevel(1, 200.0, 0.25),  # Close 25% at 200 pips
            PartialCloseLevel(2, 400.0, 0.50),  # Close 50% of remaining at 400 pips
        ],
        "commodities": [
            PartialCloseLevel(1, 600.0, 0.25),  # Close 25% at 600 pips
            PartialCloseLevel(2, 1200.0, 0.50),  # Close 50% of remaining at 1200 pips
        ],
        "crypto": [
            PartialCloseLevel(1, 100.0, 0.25),  # Close 25% at 100 USD
            PartialCloseLevel(2, 200.0, 0.50),  # Close 50% of remaining at 200 USD
        ],
    }

    def __init__(self, config: dict = None):
        """
        Initialize partial close manager.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.pip_calculator = PipCalculator()

        # Track partial closes: position_id -> list of completed levels
        self.partial_closes: dict[str, list[int]] = {}

        # Track remaining volume: position_id -> remaining volume
        self.remaining_volume: dict[str, float] = {}

        logger.debug("PartialCloseManager initialized")

    def initialize_position(self, position: Position) -> None:
        """
        Initialize position for partial close tracking.

        Args:
            position: Position to initialize
        """
        self.partial_closes[position.position_id] = []
        self.remaining_volume[position.position_id] = position.volume

        logger.debug(
            f"Initialized partial close tracking for {position.position_id}: "
            f"{position.volume:.2f} lots"
        )

    def get_next_level(self, position: Position) -> PartialCloseLevel | None:
        """
        Get next partial close level for a position.

        Args:
            position: Position to check

        Returns:
            Next partial close level or None if all levels completed
        """
        if position.position_id not in self.partial_closes:
            self.initialize_position(position)

        asset_class = self.pip_calculator._determine_asset_class(position.symbol)
        levels = self.PARTIAL_CLOSE_CONFIGS.get(asset_class, [])

        completed_levels = self.partial_closes[position.position_id]

        for level_config in levels:
            if level_config.level not in completed_levels:
                return level_config

        return None

    def should_close_partial(self, position: Position) -> bool:
        """
        Check if position should be partially closed.

        Args:
            position: Position to check

        Returns:
            True if partial close should happen
        """
        # Position must be open
        if not position.is_open:
            return False

        # Get next level
        next_level = self.get_next_level(position)
        if not next_level:
            return False

        # Check if profit exceeds level distance
        return position.current_profit_pips >= next_level.distance_pips

    def calculate_close_volume(self, position: Position, level: PartialCloseLevel) -> float:
        """
        Calculate volume to close for a partial close level.

        Args:
            position: Position
            level: Partial close level

        Returns:
            Volume to close
        """
        remaining = self.remaining_volume.get(position.position_id, position.volume)
        close_volume = remaining * level.close_percentage
        return round(close_volume, 2)

    def execute_partial_close(self, position: Position, close_price: float) -> dict[str, float]:
        """
        Execute partial close for a position.

        Args:
            position: Position to partially close
            close_price: Price at which to close

        Returns:
            Dictionary with close details

        Raises:
            ValueError: If position cannot be partially closed
        """
        if not position.is_open:
            raise ValueError(f"Position {position.position_id} is not open")

        # Get next level
        next_level = self.get_next_level(position)
        if not next_level:
            raise ValueError(f"No more partial close levels for {position.position_id}")

        # Calculate close volume
        close_volume = self.calculate_close_volume(position, next_level)
        remaining = self.remaining_volume.get(position.position_id, position.volume)

        if close_volume > remaining:
            raise ValueError(f"Close volume {close_volume:.2f} exceeds remaining {remaining:.2f}")

        # Calculate profit for closed portion
        pips = self.pip_calculator.calculate_pips(
            symbol=position.symbol,
            entry_price=position.entry_price,
            current_price=close_price,
            position_type=position.position_type.value,
        )

        pip_value = self.pip_calculator.calculate_pip_value(position.symbol, close_volume)
        profit_usd = pips * pip_value

        # Update tracking
        new_remaining = remaining - close_volume
        self.remaining_volume[position.position_id] = new_remaining
        self.partial_closes[position.position_id].append(next_level.level)

        logger.info(
            f"Partial close executed for {position.position_id}: "
            f"Level {next_level.level}, "
            f"Closed: {close_volume:.2f} lots ({next_level.close_percentage*100:.0f}%), "
            f"Remaining: {new_remaining:.2f} lots, "
            f"Profit: {pips:.1f} pips (${profit_usd:.2f})"
        )

        return {
            "level": next_level.level,
            "close_volume": close_volume,
            "remaining_volume": new_remaining,
            "close_price": close_price,
            "profit_pips": pips,
            "profit_usd": profit_usd,
        }

    def get_completed_levels(self, position_id: str) -> list[int]:
        """
        Get list of completed partial close levels.

        Args:
            position_id: Position ID

        Returns:
            List of completed level numbers
        """
        return self.partial_closes.get(position_id, [])

    def get_remaining_volume(self, position_id: str) -> float:
        """
        Get remaining position volume.

        Args:
            position_id: Position ID

        Returns:
            Remaining volume in lots
        """
        return self.remaining_volume.get(position_id, 0.0)

    def get_partial_close_levels(self, symbol: str) -> list[PartialCloseLevel]:
        """
        Get partial close levels for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            List of partial close levels
        """
        asset_class = self.pip_calculator._determine_asset_class(symbol)
        return self.PARTIAL_CLOSE_CONFIGS.get(asset_class, [])

    def reset_position(self, position_id: str) -> None:
        """
        Reset partial close tracking for a position.

        Args:
            position_id: Position ID to reset
        """
        if position_id in self.partial_closes:
            del self.partial_closes[position_id]
        if position_id in self.remaining_volume:
            del self.remaining_volume[position_id]
        logger.debug(f"Reset partial close tracking for {position_id}")

    def get_tracked_positions_count(self) -> int:
        """Get count of tracked positions."""
        return len(self.partial_closes)

    def __str__(self) -> str:
        """String representation."""
        return f"PartialCloseManager({len(self.partial_closes)} positions tracked)"

    def __repr__(self) -> str:
        """Developer representation."""
        return self.__str__()
