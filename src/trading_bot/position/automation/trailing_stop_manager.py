"""
Trailing Stop Manager - Dynamic trailing stop management.

Automatically adjusts stop loss as profit increases.

Week 15.5.2 Enhancements:
- ATR-based dynamic trailing (adaptive to volatility)
- Tiered trailing (progressive distances based on profit level)
- Session-aware adjustment (wider during volatile sessions)
"""

from dataclasses import dataclass
from datetime import datetime

from trading_bot.position.pip_calculator import PipCalculator
from trading_bot.position.position_models import Position
from trading_bot.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ATRBasedTrailingConfig:
    """Configuration for ATR-based trailing stop."""

    use_atr_trailing: bool = True
    activation_multiplier: float = 1.5  # Activate after 1.5x ATR profit
    distance_multiplier: float = 1.0  # Trail by 1.0x ATR

    # Fallback fixed values if ATR not available
    fallback_activation_pips: float = 20.0
    fallback_distance_pips: float = 15.0


@dataclass
class TieredTrailingConfig:
    """Configuration for tiered/progressive trailing stop."""

    use_tiered_trailing: bool = True
    tier_thresholds: list[float] = None  # Profit levels in pips
    tier_distances: list[float] = None  # Trailing distance per tier

    def __post_init__(self):
        """Initialize default tiers if not provided."""
        if self.tier_thresholds is None:
            self.tier_thresholds = [10.0, 20.0, 30.0]
        if self.tier_distances is None:
            self.tier_distances = [8.0, 12.0, 15.0]

        # Validate
        if len(self.tier_thresholds) != len(self.tier_distances):
            raise ValueError("Tier thresholds and distances must have same length")


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

    def __init__(self, config: dict = None, dry_run: bool = False):
        """
        Initialize trailing stop manager.

        Args:
            config: Configuration dictionary
            dry_run: If True, run in dry-run mode
        """
        self.config = config or {}
        self.dry_run = dry_run
        self.pip_calculator = PipCalculator()

        # Track highest profit for each position
        self.highest_profit: dict[str, float] = {}

        # Track if trailing is active for each position
        self.trailing_active: set[str] = set()

        # Load ATR and tiered configs for ALL asset classes
        self.atr_configs = self._load_all_atr_configs()
        self.tiered_configs = self._load_all_tiered_configs()

        logger.debug(
            f"TrailingStopManager initialized "
            f"(dry_run={dry_run}, Loaded configs for: {list(self.atr_configs.keys())})"
        )

    def _load_all_atr_configs(self) -> dict[str, ATRBasedTrailingConfig]:
        """Load ATR-based trailing configuration for ALL asset classes."""
        pm_config = self.config.get("position_management", {})
        atr_configs = {}

        # Define asset classes to load
        asset_classes = ["forex_major", "forex_jpy", "commodities", "crypto"]

        for asset_class in asset_classes:
            asset_config = pm_config.get(asset_class, {})
            atr_configs[asset_class] = ATRBasedTrailingConfig(
                use_atr_trailing=asset_config.get("use_atr_trailing", False),
                activation_multiplier=asset_config.get("trailing_activation_multiplier", 1.5),
                distance_multiplier=asset_config.get("trailing_distance_multiplier", 1.0),
                fallback_activation_pips=asset_config.get("trailing_activation", 20.0),
                fallback_distance_pips=asset_config.get("trailing_distance", 15.0),
            )

        return atr_configs

    def _load_all_tiered_configs(self) -> dict[str, TieredTrailingConfig]:
        """Load tiered trailing configuration for ALL asset classes."""
        pm_config = self.config.get("position_management", {})
        tiered_configs = {}

        # Define asset classes to load
        asset_classes = ["forex_major", "forex_jpy", "commodities", "crypto"]

        for asset_class in asset_classes:
            asset_config = pm_config.get(asset_class, {})
            tiered_configs[asset_class] = TieredTrailingConfig(
                use_tiered_trailing=asset_config.get("use_tiered_trailing", False),
                tier_thresholds=asset_config.get("tier_thresholds", [10.0, 20.0, 30.0]),
                tier_distances=asset_config.get("tier_distances", [8.0, 12.0, 15.0]),
            )

        return tiered_configs

    def _get_settings(self, asset_class: str) -> dict:
        """
        Get trailing settings for asset class.

        Supports both old and new config structures for backward compatibility:
        - New: position_management.forex_major.trailing_activation
        - Old: trade_management.overrides.forex_jpy.trailing_stop.activation_pips
        """
        # Try new structure first (position_management)
        pm_config = self.config.get("position_management", {})
        asset_config = pm_config.get(asset_class, {})

        if asset_config:
            # New structure found
            return {
                "activation_pips": asset_config.get("trailing_activation", 20.0),
                "limit_pips": asset_config.get("trailing_distance", 10.0),
            }

        # Fallback to old structure (trade_management)
        tm_config = self.config.get("trade_management", {})
        defaults = tm_config.get("defaults", {}).get("trailing_stop", {})
        overrides = tm_config.get("overrides", {}).get(asset_class, {}).get("trailing_stop", {})

        # Use override if available, otherwise use default
        activation_pips = overrides.get("activation_pips", defaults.get("activation_pips", 20.0))
        limit_pips = overrides.get("limit_pips", defaults.get("limit_pips", 10.0))

        return {
            "activation_pips": activation_pips,
            "limit_pips": limit_pips,
        }

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
                f"{position.current_profit_pips:.1f} pips profit "
                f"(threshold: {threshold_pips:.1f} pips)"
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

        position.trailing_activated = True
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

    # ========== Week 15.5.2: ATR-Based Trailing Methods ==========

    def get_atr(self, symbol: str, timeframe: str = "H1") -> float | None:
        """
        Get ATR (Average True Range) for a symbol.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe for ATR calculation

        Returns:
            ATR value in pips, or None if unavailable
        """
        # TODO: Implement actual ATR calculation from market data
        # For now, return None to trigger fallback to fixed pips
        # In production, this would query historical data and calculate ATR

        # Placeholder: Return typical ATR values for testing
        # In real implementation, this would come from market data
        return None

    def calculate_atr_activation(self, atr: float, asset_class: str = "forex_major") -> float:
        """
        Calculate ATR-based activation threshold.

        Args:
            atr: ATR value in pips
            asset_class: Asset class (forex_major, forex_jpy, commodities, crypto)

        Returns:
            Activation threshold in pips (1.5x ATR)
        """
        atr_config = self.atr_configs.get(asset_class, self.atr_configs["forex_major"])
        return atr * atr_config.activation_multiplier

    def calculate_atr_distance(self, atr: float, asset_class: str = "forex_major") -> float:
        """
        Calculate ATR-based trailing distance.

        Args:
            atr: ATR value in pips
            asset_class: Asset class (forex_major, forex_jpy, commodities, crypto)

        Returns:
            Trailing distance in pips (1.0x ATR)
        """
        atr_config = self.atr_configs.get(asset_class, self.atr_configs["forex_major"])
        return atr * atr_config.distance_multiplier

    def get_activation_threshold(
        self, symbol_or_position: str | dict, position: Position | None = None
    ) -> float:
        """
        Get activation threshold (ATR-based or fallback to fixed).

        Supports both old and new signatures for backward compatibility:
        - Old: get_activation_threshold(symbol: str, position: Position | None = None)
        - New: get_activation_threshold(position: dict)

        Args:
            symbol_or_position: Either symbol string (old) or position dict (new)
            position: Optional position (old signature, deprecated)

        Returns:
            Activation threshold in pips
        """
        # Determine symbol from input
        if isinstance(symbol_or_position, dict):
            # New signature: position dict
            symbol = symbol_or_position.get("symbol", "")
        else:
            # Old signature: symbol string
            symbol = symbol_or_position

        # Determine asset class
        asset_class = self.pip_calculator._determine_asset_class(symbol)
        atr_config = self.atr_configs.get(asset_class, self.atr_configs["forex_major"])

        # If ATR-based trailing not enabled for this asset class, use fallback
        if not atr_config.use_atr_trailing:
            settings = self._get_settings(asset_class)
            return settings.get("activation_pips", 20.0)

        # Try to get ATR
        atr = self.get_atr(symbol)

        if atr is not None:
            return self.calculate_atr_activation(atr, asset_class)
        else:
            # Fallback to fixed pips from config
            settings = self._get_settings(asset_class)
            return settings.get("activation_pips", atr_config.fallback_activation_pips)

    # ========== Week 15.5.2: Tiered Trailing Methods ==========

    def get_tiered_distance(self, position: dict) -> float:
        """
        Get tiered trailing distance based on profit level.

        Tiers work as ranges where thresholds[1:] define tier boundaries:
        - Profit < 20 pips: Tier 0 distance (8 pips) - tight initially
        - Profit 20-30 pips: Tier 1 distance (12 pips) - widen a bit
        - Profit >= 30 pips: Tier 2 distance (15 pips) - widest

        thresholds[0] is the activation threshold, not used for tier selection.

        Args:
            position: Position dictionary with current_profit_pips and symbol

        Returns:
            Trailing distance in pips for current profit tier
        """
        symbol = position.get("symbol", "")
        asset_class = self.pip_calculator._determine_asset_class(symbol)
        tiered_config = self.tiered_configs.get(asset_class, self.tiered_configs["forex_major"])
        atr_config = self.atr_configs.get(asset_class, self.atr_configs["forex_major"])

        if not tiered_config.use_tiered_trailing:
            return atr_config.fallback_distance_pips

        profit_pips = position.get("current_profit_pips", 0.0)

        # Use thresholds[1:] as tier boundaries
        # This treats thresholds[0] as activation only
        tier_boundaries = tiered_config.tier_thresholds[1:]

        # Find which tier we're in
        tier_index = 0
        for boundary in tier_boundaries:
            if profit_pips >= boundary:
                tier_index += 1
            else:
                break

        # Ensure we don't exceed available tiers
        tier_index = min(tier_index, len(tiered_config.tier_distances) - 1)

        return tiered_config.tier_distances[tier_index]

    def get_optimal_distance(self, position: dict, atr: float | None = None) -> float:
        """
        Get optimal trailing distance (max of ATR-based and tiered).

        Uses the WIDER of ATR distance or tiered distance to give position
        more breathing room and prevent premature exits.

        Args:
            position: Position dictionary with symbol
            atr: Optional ATR value

        Returns:
            Optimal trailing distance in pips
        """
        symbol = position.get("symbol", "")
        asset_class = self.pip_calculator._determine_asset_class(symbol)
        atr_config = self.atr_configs.get(asset_class, self.atr_configs["forex_major"])
        tiered_config = self.tiered_configs.get(asset_class, self.tiered_configs["forex_major"])

        distances = []

        # ATR-based distance
        if atr_config.use_atr_trailing and atr is not None:
            distances.append(self.calculate_atr_distance(atr, asset_class))

        # Tiered distance
        if tiered_config.use_tiered_trailing:
            distances.append(self.get_tiered_distance(position))

        # Fallback distance
        if not distances:
            distances.append(atr_config.fallback_distance_pips)

        # Return the WIDER distance (more conservative)
        return max(distances)

    # ========== Week 15.5.2: Session-Aware Trailing Methods ==========

    def get_current_session(self) -> str:
        """
        Get current trading session.

        Returns:
            Session name: 'asian', 'london_open', 'ny_open', 'regular'
        """
        # TODO: Implement actual session detection based on UTC time
        # For now, return 'regular'

        # Placeholder implementation
        now = datetime.utcnow()
        hour = now.hour

        # Simplified session logic (UTC time)
        if 0 <= hour < 8:
            return "asian"
        elif 8 <= hour < 10:
            return "london_open"
        elif 13 <= hour < 15:
            return "ny_open"
        else:
            return "regular"

    def adjust_for_session(self, base_distance: float, session: str) -> float:
        """
        Adjust trailing distance for trading session.

        Widens trailing during volatile sessions (London/NY open),
        tightens during low volatility (Asian session).

        Args:
            base_distance: Base trailing distance in pips
            session: Trading session name

        Returns:
            Adjusted trailing distance in pips
        """
        multipliers = {
            "london_open": 1.5,  # 50% wider during London open
            "ny_open": 1.5,  # 50% wider during NY open
            "asian": 0.7,  # 30% tighter during Asian session
            "regular": 1.0,  # No adjustment
        }

        multiplier = multipliers.get(session, 1.0)
        return base_distance * multiplier

    def calculate_trailing_sl(
        self, position: dict, current_price: float, distance_pips: float
    ) -> float:
        """
        Calculate new trailing stop loss price.

        Args:
            position: Position dictionary
            current_price: Current market price
            distance_pips: Trailing distance in pips

        Returns:
            New stop loss price
        """
        pip_size = position.get("pip_size", 0.0001)
        position_type = position.get("position_type", "BUY")
        current_sl = position.get("stop_loss", 0.0)

        distance_price = distance_pips * pip_size

        if position_type == "BUY":
            new_sl = current_price - distance_price
            # Never move SL backward (down for BUY)
            return max(new_sl, current_sl)
        else:  # SELL
            new_sl = current_price + distance_price
            # Never move SL backward (up for SELL)
            return min(new_sl, current_sl)

    def __str__(self) -> str:
        """String representation."""
        return f"TrailingStopManager({len(self.trailing_active)} positions trailing)"

    def __repr__(self) -> str:
        """Developer representation."""
        return self.__str__()
