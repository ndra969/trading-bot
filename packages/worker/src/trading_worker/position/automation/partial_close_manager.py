"""
Partial Close Manager - Automated partial position closure.

Closes portions of a position at profit targets.
"""

from typing import NamedTuple

from trading_core.utils.logger import get_logger

from trading_worker.position.pip_calculator import PipCalculator
from trading_worker.position.position_models import Position

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

        pc_cfg = self.config.get("partial_close", {})

        # Disabled by default — for small/cent accounts, 25% of 0.01 lot is
        # below MT5's 0.01 minimum so partial close silently never fires
        # anyway. Explicit flag prevents the misleading "should-fire-but-
        # skipped" log noise and documents the intent.
        self.enabled = bool(pc_cfg.get("enabled", False))

        # MT5 lot-size floor: a single partial-close order must be >= this.
        self.min_volume = float(pc_cfg.get("min_volume", 0.01))

        # Optional per-asset / flat level-ratio overrides (proportion of TP
        # distance + close % of remaining). Read once; resolved per asset.
        self._level_ratios_cfg = pc_cfg.get("level_ratios")

        # Position-level size gate: below this volume the FIRST partial can
        # never clear the lot floor, so partial close is skipped cleanly for
        # the whole position (no per-loop "should-fire-but-skipped" noise,
        # visible in the dashboard as a non-firing automation). When unset,
        # computed from the floor and the largest first-level close % — the
        # smallest position that CAN partial-close (e.g. 0.01 / 0.25 = 0.04).
        configured_min_pos = pc_cfg.get("min_position_volume")
        if configured_min_pos is not None:
            self.min_position_volume = float(configured_min_pos)
        else:
            first_close_pct = self._first_close_percentage()
            self.min_position_volume = (
                self.min_volume / first_close_pct if first_close_pct > 0 else self.min_volume
            )

        # Positions already announced as size-gated (log the skip once, not
        # every update loop).
        self._size_gated_logged: set[str] = set()

        logger.info(
            f"PartialCloseManager initialized (enabled={self.enabled}, "
            f"min_volume={self.min_volume:.3f}, "
            f"min_position_volume={self.min_position_volume:.3f})"
        )

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

        Levels are calculated dynamically based on TP distance (RR ratio) to ensure
        they always trigger before TP is reached.

        Args:
            position: Position to check

        Returns:
            Next partial close level or None if all levels completed
        """
        if position.position_id not in self.partial_closes:
            self.initialize_position(position)

        # Calculate TP distance in pips
        pip_size = position.pip_size
        if position.position_type.value == "BUY":
            tp_distance_pips = (position.take_profit - position.entry_price) / pip_size
        else:  # SELL
            tp_distance_pips = (position.entry_price - position.take_profit) / pip_size

        # Get partial close level ratios from config (as proportion of TP distance)
        # Default: Level 1 at 50% of TP, Level 2 at 80% of TP
        asset_class = self.pip_calculator._determine_asset_class(position.symbol)
        level_ratios = self._get_level_ratios(asset_class)

        completed_levels = self.partial_closes[position.position_id]

        # Calculate dynamic levels based on TP distance
        for level_num, (tp_ratio, close_pct) in enumerate(level_ratios, start=1):
            if level_num not in completed_levels:
                # Calculate level distance as proportion of TP
                level_distance_pips = tp_distance_pips * tp_ratio
                return PartialCloseLevel(level_num, level_distance_pips, close_pct)

        return None

    def _get_level_ratios(self, asset_class: str) -> list[tuple[float, float]]:
        """
        Get partial close level ratios (as proportion of TP distance) and close percentages.

        Returns list of (tp_ratio, close_percentage) tuples.
        tp_ratio: Proportion of TP distance (0.5 = 50% of TP, 0.8 = 80% of TP)
        close_percentage: Percentage of remaining volume to close (0.25 = 25%)

        Args:
            asset_class: Asset class (forex_major, forex_jpy, commodities, crypto)

        Returns:
            List of (tp_ratio, close_percentage) tuples

        Config (``partial_close.level_ratios``) overrides the defaults so the
        first partial can be moved to a REACHABLE tier (live data: ~19% of
        trades reach ~1R, almost none reach 2R). Accepts either a flat list of
        ``[tp_ratio, close_pct]`` pairs applied to every asset, or a dict
        keyed by asset class with a ``default`` fallback.
        """
        # Default ratios: Level 1 at 50% of TP (25% close), Level 2 at 80% of TP (50% close)
        # This ensures levels trigger before TP regardless of RR ratio
        default_ratios = [
            (0.5, 0.25),  # Level 1: 50% of TP, close 25%
            (0.8, 0.50),  # Level 2: 80% of TP, close 50% of remaining
        ]

        cfg = self._level_ratios_cfg
        raw = None
        if isinstance(cfg, dict):
            raw = cfg.get(asset_class) or cfg.get("default")
        elif isinstance(cfg, list) and cfg:
            raw = cfg

        if raw:
            return [(float(tp_ratio), float(close_pct)) for tp_ratio, close_pct in raw]
        return default_ratios

    def _first_close_percentage(self) -> float:
        """Close % of the first partial level (drives the min-position gate)."""
        ratios = self._get_level_ratios("forex_major")
        return ratios[0][1] if ratios else 0.25

    def should_close_partial(self, position: Position) -> bool:
        """
        Check if position should be partially closed.

        Args:
            position: Position to check

        Returns:
            True if partial close should happen
        """
        # Global disable check
        if not self.enabled:
            return False

        # Position must be open
        if not position.is_open:
            return False

        # Position-level size gate: when the whole position is too small for
        # any partial to clear the lot floor, skip cleanly for its lifetime
        # (announce once at debug, not every update loop).
        if position.volume < self.min_position_volume:
            if position.position_id not in self._size_gated_logged:
                self._size_gated_logged.add(position.position_id)
                logger.debug(
                    f"Partial close size-gated for {position.position_id}: "
                    f"volume {position.volume:.3f} < min_position_volume "
                    f"{self.min_position_volume:.3f} lots — partial disabled for this position"
                )
            return False

        # Get next level
        next_level = self.get_next_level(position)
        if not next_level:
            return False

        # Check if profit exceeds level distance
        if position.current_profit_pips < next_level.distance_pips:
            return False

        # Check if the calculated close volume clears the MT5 lot floor.
        remaining = self.remaining_volume.get(position.position_id, position.volume)
        close_volume = remaining * next_level.close_percentage

        if close_volume < self.min_volume:
            logger.debug(
                f"Skipping partial close for {position.position_id}: "
                f"Close volume {close_volume:.3f} < minimum {self.min_volume:.3f} "
                f"(Position: {position.volume:.3f} lots, Close %: {next_level.close_percentage * 100:.0f}%)"
            )
            return False

        return True

    def calculate_close_volume(self, position: Position, level: PartialCloseLevel) -> float:
        """
        Calculate volume to close for a partial close level.

        Args:
            position: Position
            level: Partial close level

        Returns:
            Volume to close (rounded to appropriate precision)
        """
        remaining = self.remaining_volume.get(position.position_id, position.volume)
        close_volume = remaining * level.close_percentage

        # Round based on asset class (crypto can have 3 decimals, forex typically 2)
        asset_class = self.pip_calculator._determine_asset_class(position.symbol)
        if asset_class == "crypto":
            return round(close_volume, 3)  # Crypto: 0.001 precision
        elif asset_class == "commodities":
            return round(close_volume, 1)  # Gold: 0.1 precision
        else:
            return round(close_volume, 2)  # Forex: 0.01 precision

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
            logger.warning(
                f"Close volume {close_volume:.3f} exceeds remaining {remaining:.3f}, adjusting to remaining"
            )
            close_volume = remaining

        # Validate the close clears the configured MT5 lot floor.
        if close_volume < self.min_volume:
            raise ValueError(
                f"Cannot partial close: volume {close_volume:.3f} < minimum {self.min_volume:.3f} "
                f"(position volume: {position.volume:.3f})"
            )

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
            f"Closed: {close_volume:.2f} lots ({next_level.close_percentage * 100:.0f}%), "
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

    def get_partial_close_levels(
        self, symbol: str, position: Position | None = None
    ) -> list[PartialCloseLevel]:
        """
        Get partial close levels for a symbol.

        If position is provided, levels are calculated dynamically based on TP distance.
        Otherwise, returns default static levels (for reference only).

        Args:
            symbol: Trading symbol
            position: Optional position to calculate dynamic levels

        Returns:
            List of partial close levels
        """
        if position:
            # Calculate dynamic levels based on position TP
            pip_size = position.pip_size
            if position.position_type.value == "BUY":
                tp_distance_pips = (position.take_profit - position.entry_price) / pip_size
            else:  # SELL
                tp_distance_pips = (position.entry_price - position.take_profit) / pip_size

            asset_class = self.pip_calculator._determine_asset_class(symbol)
            level_ratios = self._get_level_ratios(asset_class)

            levels = []
            for level_num, (tp_ratio, close_pct) in enumerate(level_ratios, start=1):
                level_distance_pips = tp_distance_pips * tp_ratio
                levels.append(PartialCloseLevel(level_num, level_distance_pips, close_pct))
            return levels
        else:
            # Return static config (for reference, may not match actual levels)
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
        self._size_gated_logged.discard(position_id)
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
