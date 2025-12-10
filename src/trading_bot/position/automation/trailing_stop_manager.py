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
        "crypto": 500.0,  # 500 USD/pips (wide trailing for crypto volatility)
    }

    # Activation threshold (pips profit required to activate trailing)
    ACTIVATION_THRESHOLDS = {
        "forex_major": 20.0,  # Activate after 20 pips profit
        "forex_jpy": 200.0,  # Activate after 200 pips profit
        "commodities": 600.0,  # Activate after 600 pips profit
        "crypto": 500.0,  # Activate after 500 USD/pips profit (~$5 for 0.01 lot)
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
        
        Activation threshold is calculated as proportion of TP distance to ensure
        it triggers before TP regardless of RR ratio.

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

        # Calculate TP distance in pips
        pip_size = position.pip_size
        if position.position_type.value == "BUY":
            tp_distance_pips = (position.take_profit - position.entry_price) / pip_size
        else:  # SELL
            tp_distance_pips = (position.entry_price - position.take_profit) / pip_size

        # Get activation threshold as proportion of TP distance
        # Default: 66% of TP (equivalent to ~20 pips for 30 pips TP with RR 1:2)
        asset_class = self.pip_calculator._determine_asset_class(position.symbol)
        activation_ratio = self._get_activation_ratio(asset_class)
        threshold_pips = tp_distance_pips * activation_ratio

        # Check if profit exceeds threshold
        if position.current_profit_pips >= threshold_pips:
            logger.info(
                f"Trailing stop activated for {position.position_id}: "
                f"{position.current_profit_pips:.1f} pips (threshold: {threshold_pips:.1f} pips, "
                f"{activation_ratio*100:.0f}% of TP {tp_distance_pips:.1f} pips)"
            )
            return True

        return False
    
    def _get_activation_ratio(self, asset_class: str) -> float:
        """
        Get trailing stop activation threshold as proportion of TP distance.
        
        Returns ratio (0.66 = 66% of TP distance).
        This ensures trailing activates before TP regardless of RR ratio.
        
        Args:
            asset_class: Asset class (forex_major, forex_jpy, commodities, crypto)
            
        Returns:
            Activation ratio (0.0 - 1.0)
        """
        # Default: 66% of TP distance
        # This means trailing activates when profit reaches 66% of TP
        # Example: TP = 30 pips → activation at 20 pips
        # This ensures trailing activates well before TP is reached
        return 0.66  # 66% of TP distance

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

    def get_activation_threshold(self, symbol: str, position: Position | None = None) -> float:
        """
        Get activation threshold for a symbol.
        
        If position is provided, calculates threshold as proportion of TP distance.
        Otherwise, returns default static threshold (for reference only).

        Args:
            symbol: Trading symbol
            position: Optional position to calculate dynamic threshold

        Returns:
            Activation threshold in pips
        """
        if position:
            # Calculate dynamic threshold based on TP distance
            pip_size = position.pip_size
            if position.position_type.value == "BUY":
                tp_distance_pips = (position.take_profit - position.entry_price) / pip_size
            else:  # SELL
                tp_distance_pips = (position.entry_price - position.take_profit) / pip_size
            
            asset_class = self.pip_calculator._determine_asset_class(symbol)
            activation_ratio = self._get_activation_ratio(asset_class)
            return tp_distance_pips * activation_ratio
        else:
            # Return static config (for reference, may not match actual threshold)
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
