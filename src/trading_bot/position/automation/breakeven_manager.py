"""
Breakeven Manager - Automated breakeven stop loss management.

Automatically moves stop loss to entry + buffer when conditions are met.
"""

from trading_bot.position.pip_calculator import PipCalculator
from trading_bot.position.position_models import Position
from trading_bot.utils.logger import get_logger

logger = get_logger(__name__)


class BreakevenManager:
    """
    Manages automatic breakeven stop loss adjustment.

    Moves stop loss to entry + buffer when position reaches
    specified profit threshold.

    Asset-specific breakeven distances:
    - Forex Major: 15 pips
    - Forex JPY: 150 pips
    - Commodities (Gold): 500 pips
    - Crypto: 50 USD
    """

    def __init__(self, config: dict = None):
        """
        Initialize breakeven manager.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.pip_calculator = PipCalculator()

        # Track positions that have been moved to breakeven
        self.breakeven_positions: set[str] = set()

        logger.debug("BreakevenManager initialized")

    def _get_settings(self, asset_class: str) -> dict:
        """
        Get breakeven settings for asset class.

        Uses position_management config structure from docs:
        position_management:
          forex_major:
            breakeven_trigger: 15
            breakeven_offset: 2
        """
        pm_config = self.config.get("position_management", {})

        # Get asset-specific config (flat structure as per docs)
        asset_config = pm_config.get(asset_class, {})

        # Map from docs field names to internal field names
        settings = {
            "trigger_pips": asset_config.get("breakeven_trigger", 15.0),
            "offset_pips": asset_config.get("breakeven_offset", 2.0),
        }

        return settings

    def should_move_to_breakeven(self, position: Position) -> bool:
        """
        Check if position should be moved to breakeven.

        Args:
            position: Position to check

        Returns:
            True if position should be moved to breakeven
        """
        # Already moved to breakeven
        if position.position_id in self.breakeven_positions:
            logger.debug(f"Breakeven check for {position.position_id}: Already at breakeven")
            return False

        # Position must be open
        if not position.is_open:
            logger.debug(
                f"Breakeven check for {position.position_id}: Position not open (status: {position.status.value})"
            )
            return False

        # Current price must be set
        if position.current_price is None:
            logger.debug(f"Breakeven check for {position.position_id}: Current price not set")
            return False

        # Get breakeven trigger distance
        asset_class = self.pip_calculator._determine_asset_class(position.symbol)
        settings = self._get_settings(asset_class)
        trigger_distance = settings.get("trigger_pips", 15.0)

        # Log current status for debugging
        logger.debug(
            f"Breakeven check for {position.position_id} ({position.symbol}): "
            f"profit={position.current_profit_pips:.1f} pips, "
            f"trigger={trigger_distance:.1f} pips, "
            f"asset_class={asset_class}"
        )

        # Check if current profit exceeds trigger distance
        if position.current_profit_pips >= trigger_distance:
            logger.info(
                f"✅ Breakeven trigger hit for {position.position_id}: "
                f"{position.current_profit_pips:.1f} pips (trigger: {trigger_distance:.1f})"
            )
            return True

        return False

    def move_to_breakeven(self, position: Position) -> float:
        """
        Move stop loss to breakeven (entry + buffer).

        Args:
            position: Position to move to breakeven

        Returns:
            New stop loss price

        Raises:
            ValueError: If position cannot be moved to breakeven
        """
        if not position.is_open:
            raise ValueError(f"Position {position.position_id} is not open")

        # Get asset class and buffer
        asset_class = self.pip_calculator._determine_asset_class(position.symbol)
        settings = self._get_settings(asset_class)
        buffer_pips = settings.get("offset_pips", 2.0)
        pip_size = position.pip_size

        # Calculate buffer in price units
        buffer_price = buffer_pips * pip_size

        # Calculate new stop loss
        if position.position_type.value == "BUY":
            new_stop_loss = position.entry_price + buffer_price
        else:  # SELL
            new_stop_loss = position.entry_price - buffer_price

        # Update position
        old_stop_loss = position.stop_loss
        position.stop_loss = new_stop_loss

        # Mark as moved to breakeven
        position.breakeven_activated = True
        self.breakeven_positions.add(position.position_id)

        logger.info(
            f"Moved {position.position_id} to breakeven: "
            f"SL: {old_stop_loss:.5f} → {new_stop_loss:.5f} "
            f"(entry: {position.entry_price:.5f}, buffer: {buffer_pips:.1f} pips)"
        )

        return new_stop_loss

    def is_at_breakeven(self, position_id: str) -> bool:
        """
        Check if position has been moved to breakeven.

        Args:
            position_id: Position ID to check

        Returns:
            True if position is at breakeven
        """
        return position_id in self.breakeven_positions

    def get_breakeven_distance(self, symbol: str) -> float:
        """
        Get breakeven trigger distance for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Breakeven trigger distance in pips
        """
        asset_class = self.pip_calculator._determine_asset_class(symbol)
        settings = self._get_settings(asset_class)
        return settings.get("trigger_pips", 15.0)

    def get_breakeven_buffer(self, symbol: str) -> float:
        """
        Get breakeven buffer for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Breakeven buffer in pips
        """
        asset_class = self.pip_calculator._determine_asset_class(symbol)
        settings = self._get_settings(asset_class)
        return settings.get("offset_pips", 2.0)

    def reset_position(self, position_id: str) -> None:
        """
        Reset breakeven tracking for a position.

        Args:
            position_id: Position ID to reset
        """
        if position_id in self.breakeven_positions:
            self.breakeven_positions.remove(position_id)
            logger.debug(f"Reset breakeven tracking for {position_id}")

    def get_breakeven_positions_count(self) -> int:
        """Get count of positions at breakeven."""
        return len(self.breakeven_positions)

    def __str__(self) -> str:
        """String representation."""
        return f"BreakevenManager({len(self.breakeven_positions)} positions at BE)"

    def __repr__(self) -> str:
        """Developer representation."""
        return self.__str__()
