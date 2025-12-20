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

    def _get_settings(self, asset_class: str) -> dict:
        """
        Get trailing settings for asset class.

        Merges defaults with overrides.
        """
        tm_config = self.config.get("trade_management", {})

        # Get Defaults
        defaults = tm_config.get("defaults", {}).get("trailing_stop", {})

        # Get Overrides for Asset Class
        overrides = tm_config.get("overrides", {}).get(asset_class, {}).get("trailing_stop", {})

        # Merge
        settings = defaults.copy()
        settings.update(overrides)

        return settings

    def should_activate_trailing(self, position: Position) -> bool:
        """
        Check if trailing stop should be activated.

        Uses activation_pips from config.

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

        # Get activation threshold from config
        asset_class = self.pip_calculator._determine_asset_class(position.symbol)
        settings = self._get_settings(asset_class)
        threshold_pips = settings.get("activation_pips", 20.0)

        # Check if profit exceeds threshold
        if position.current_profit_pips >= threshold_pips:
            logger.info(
                f"🎯 Trailing stop ACTIVATED for {position.position_id} ({position.symbol}): "
                f"{position.current_profit_pips:.1f} pips profit (threshold: {threshold_pips:.1f} pips)"
            )
            return True
        else:
            logger.debug(
                f"Trailing stop NOT YET activated for {position.position_id} ({position.symbol}): "
                f"{position.current_profit_pips:.1f} pips < {threshold_pips:.1f} pips threshold"
            )

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

        Updates trailing stop when:
        1. Current profit exceeds highest recorded profit, OR
        2. Current price allows for better stop loss (even if profit same/fluctuating)

        This ensures trailing stop follows price movement and locks in profits.

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

        # Check if current profit exceeds highest recorded profit
        highest = self.highest_profit.get(position.position_id, 0.0)
        profit_increased = position.current_profit_pips > highest

        # Also check if we can improve stop loss based on current price
        # This handles cases where profit fluctuates but price still allows better SL
        asset_class = self.pip_calculator._determine_asset_class(position.symbol)
        settings = self._get_settings(asset_class)
        trailing_distance = settings.get("limit_pips", 10.0)
        pip_size = position.pip_size
        trailing_price = trailing_distance * pip_size

        # Calculate what the new stop loss would be
        if position.position_type.value == "BUY":
            potential_new_sl = position.current_price - trailing_price
            # For BUY: new SL must be higher than current SL (better protection)
            can_improve_sl = potential_new_sl > position.stop_loss
        else:  # SELL
            potential_new_sl = position.current_price + trailing_price
            # For SELL: new SL must be lower than current SL (better protection)
            can_improve_sl = potential_new_sl < position.stop_loss

        # Update if profit increased OR we can improve SL (and profit is still positive)
        # This ensures trailing follows price even if profit fluctuates slightly
        should_update = profit_increased or (
            can_improve_sl and position.current_profit_pips >= highest * 0.9
        )

        if should_update and not profit_increased:
            logger.debug(
                f"Trailing stop update triggered for {position.position_id}: "
                f"profit {position.current_profit_pips:.1f} pips (highest: {highest:.1f}), "
                f"can improve SL: {can_improve_sl}"
            )

        return should_update

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
        settings = self._get_settings(asset_class)
        trailing_distance = settings.get("limit_pips", 10.0)
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
            f"🔄 TRAILING STOP UPDATED for {position.position_id} ({position.symbol}): "
            f"SL: {old_stop_loss:.5f} → {new_stop_loss:.5f} "
            f"(profit: {position.current_profit_pips:.1f} pips, "
            f"trailing: {trailing_distance:.1f} pips, "
            f"current_price: {position.current_price:.5f})"
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
        settings = self._get_settings(asset_class)
        return settings.get("limit_pips", 10.0)

    def get_activation_threshold(self, symbol: str, position: Position | None = None) -> float:
        """
        Get activation threshold for a symbol.

        Args:
            symbol: Trading symbol
            position: Optional position (deprecated, unused)

        Returns:
            Activation threshold in pips
        """
        asset_class = self.pip_calculator._determine_asset_class(symbol)
        settings = self._get_settings(asset_class)
        return settings.get("activation_pips", 20.0)

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
