"""
Trailing Stop Manager - Dynamic trailing stop management.

Automatically adjusts stop loss as profit increases.
"""

from trading_bot.position.pip_calculator import PipCalculator
from trading_bot.position.position_models import Position
from trading_bot.utils.logger import get_logger

logger = get_logger(__name__)


class TrailingStopManager:
    """
    Manages dynamic trailing stop loss adjustment.

    Progressively tightens stop loss as profit increases while
    maintaining a trailing distance.

    Asset-specific trailing distances:
    - Forex Major: 10 pips
    - Forex JPY: 100 pips
    - Commodities (Gold): 300 pips
    - Crypto: 30 USD
    """

    # Trailing stop distances (in pips/USD)
    TRAILING_DISTANCES = {
        "forex_major": 10.0,  # 10 pips
        "forex_jpy": 100.0,  # 100 pips
        "commodities": 300.0,  # 300 pips for Gold
        "crypto": 30.0,  # 30 USD
    }

    # Activation threshold (pips profit required to activate trailing)
    ACTIVATION_THRESHOLDS = {
        "forex_major": 20.0,  # Activate after 20 pips profit
        "forex_jpy": 200.0,  # Activate after 200 pips profit
        "commodities": 600.0,  # Activate after 600 pips profit
        "crypto": 60.0,  # Activate after 60 USD profit
    }

    def __init__(self, config: dict = None):
        """
        Initialize trailing stop manager.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.pip_calculator = PipCalculator()

        # Track highest profit for each position
        self.highest_profit: dict[str, float] = {}

        # Track if trailing is active for each position
        self.trailing_active: set[str] = set()

        logger.debug("TrailingStopManager initialized")

    def should_activate_trailing(self, position: Position) -> bool:
        """
        Check if trailing stop should be activated.

        Args:
            position: Position to check

        Returns:
            True if trailing should be activated
        """
        # Already active
        if position.position_id in self.trailing_active:
            return False

        # Position must be open
        if not position.is_open:
            return False

        # Get activation threshold
        asset_class = self.pip_calculator._determine_asset_class(position.symbol)
        threshold = self.ACTIVATION_THRESHOLDS.get(asset_class, 20.0)

        # Check if profit exceeds threshold
        if position.current_profit_pips >= threshold:
            logger.info(
                f"Trailing stop activated for {position.position_id}: "
                f"{position.current_profit_pips:.1f} pips (threshold: {threshold:.1f})"
            )
            return True

        return False

    def activate_trailing(self, position: Position) -> None:
        """
        Activate trailing stop for a position.

        Args:
            position: Position to activate trailing for
        """
        if not position.is_open:
            return

        self.trailing_active.add(position.position_id)
        self.highest_profit[position.position_id] = position.current_profit_pips

        logger.info(
            f"Trailing stop activated for {position.position_id} "
            f"at {position.current_profit_pips:.1f} pips"
        )

    def should_update_trailing_stop(self, position: Position) -> bool:
        """
        Check if trailing stop should be updated.

        Args:
            position: Position to check

        Returns:
            True if trailing stop should be updated
        """
        # Trailing must be active
        if position.position_id not in self.trailing_active:
            return False

        # Position must be open
        if not position.is_open:
            return False

        # Current profit must exceed highest recorded profit
        highest = self.highest_profit.get(position.position_id, 0.0)
        return position.current_profit_pips > highest

    def update_trailing_stop(self, position: Position) -> float:
        """
        Update trailing stop loss.

        Args:
            position: Position to update

        Returns:
            New stop loss price

        Raises:
            ValueError: If position cannot be updated
        """
        if not position.is_open:
            raise ValueError(f"Position {position.position_id} is not open")

        if position.position_id not in self.trailing_active:
            raise ValueError(f"Trailing not active for {position.position_id}")

        # Get trailing distance
        asset_class = self.pip_calculator._determine_asset_class(position.symbol)
        trailing_distance = self.TRAILING_DISTANCES.get(asset_class, 10.0)
        pip_size = position.pip_size

        # Calculate trailing distance in price units
        trailing_price = trailing_distance * pip_size

        # Calculate new stop loss based on current price
        if position.position_type.value == "BUY":
            new_stop_loss = position.current_price - trailing_price
            # Only move up (never down)
            if new_stop_loss <= position.stop_loss:
                return position.stop_loss
        else:  # SELL
            new_stop_loss = position.current_price + trailing_price
            # Only move down (never up)
            if new_stop_loss >= position.stop_loss:
                return position.stop_loss

        # Update position
        old_stop_loss = position.stop_loss
        position.stop_loss = new_stop_loss

        # Update highest profit
        self.highest_profit[position.position_id] = position.current_profit_pips

        logger.info(
            f"Updated trailing stop for {position.position_id}: "
            f"SL: {old_stop_loss:.5f} → {new_stop_loss:.5f} "
            f"(profit: {position.current_profit_pips:.1f} pips, "
            f"trailing: {trailing_distance:.1f} pips)"
        )

        return new_stop_loss

    def is_trailing_active(self, position_id: str) -> bool:
        """
        Check if trailing is active for a position.

        Args:
            position_id: Position ID to check

        Returns:
            True if trailing is active
        """
        return position_id in self.trailing_active

    def get_trailing_distance(self, symbol: str) -> float:
        """
        Get trailing distance for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Trailing distance in pips
        """
        asset_class = self.pip_calculator._determine_asset_class(symbol)
        return self.TRAILING_DISTANCES.get(asset_class, 10.0)

    def get_activation_threshold(self, symbol: str) -> float:
        """
        Get activation threshold for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Activation threshold in pips
        """
        asset_class = self.pip_calculator._determine_asset_class(symbol)
        return self.ACTIVATION_THRESHOLDS.get(asset_class, 20.0)

    def get_highest_profit(self, position_id: str) -> float:
        """
        Get highest profit recorded for a position.

        Args:
            position_id: Position ID

        Returns:
            Highest profit in pips
        """
        return self.highest_profit.get(position_id, 0.0)

    def reset_position(self, position_id: str) -> None:
        """
        Reset trailing tracking for a position.

        Args:
            position_id: Position ID to reset
        """
        if position_id in self.trailing_active:
            self.trailing_active.remove(position_id)
        if position_id in self.highest_profit:
            del self.highest_profit[position_id]
        logger.debug(f"Reset trailing tracking for {position_id}")

    def get_trailing_positions_count(self) -> int:
        """Get count of positions with active trailing."""
        return len(self.trailing_active)

    def __str__(self) -> str:
        """String representation."""
        return f"TrailingStopManager({len(self.trailing_active)} positions trailing)"

    def __repr__(self) -> str:
        """Developer representation."""
        return self.__str__()
