"""
Exposure Manager - Manages exposure limits and diversification.

Controls:
- Asset class exposure limits
- Per-symbol position limits
- Currency exposure tracking
- Leverage management
"""

from collections import defaultdict

from trading_bot.utils.logger import get_logger

logger = get_logger(__name__)


class ExposureManager:
    """
    Manages position exposure and limits.

    Enforces:
    - Maximum 1 position per symbol
    - Asset class exposure limits
    - Currency exposure tracking
    - Total leverage limits
    """

    def __init__(self, config: dict = None):
        """
        Initialize exposure manager.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Exposure limits
        self.max_positions_per_symbol = self.config.get("risk_management", {}).get(
            "max_positions_per_symbol", 1
        )
        # NOTE: global "max_total_positions" removed — per-asset-class limits
        # in active_symbols.yaml are the single source of truth. Sum of class
        # limits is the effective total cap.
        self.max_leverage = self.config.get("risk_management", {}).get("max_leverage", 10.0)

        # Asset class exposure limits (percentage of portfolio)
        self.max_asset_class_exposure_pct = self.config.get("risk_management", {}).get(
            "max_asset_class_exposure_percent", 40.0
        )

        # Asset class position limits (from active_symbols.yaml)
        # Reads max_concurrent_positions per asset class
        asset_classes_config = self.config.get("asset_classes", {})
        self.max_positions_per_asset_class: dict[str, int] = {}
        for asset_class_name, asset_class_cfg in asset_classes_config.items():
            if asset_class_cfg.get("enabled", False):
                max_pos = asset_class_cfg.get("max_concurrent_positions", 10)
                self.max_positions_per_asset_class[asset_class_name] = max_pos

        logger.debug(f"Asset class position limits: {self.max_positions_per_asset_class}")

        # Correlation management
        # Define correlated pairs (pairs that move together, should have same direction)
        # Define negative correlated pairs (pairs that move opposite, should have opposite direction)
        # Correlation threshold: 0.7+ means pairs move together, -0.7+ means pairs move opposite
        self.correlated_pairs = self._build_correlation_groups()
        self.negative_correlated_pairs = self._build_negative_correlation_groups()
        self.correlation_enabled = (
            self.config.get("risk_management", {})
            .get("correlation_management", {})
            .get("enabled", True)
        )

        # Tracking
        self.positions_by_symbol: dict[str, int] = defaultdict(int)
        self.positions_by_asset_class: dict[str, int] = defaultdict(int)
        self.currency_exposure: dict[str, float] = defaultdict(float)
        # Track position directions for correlation checking
        self.position_directions: dict[str, str] = {}  # symbol -> "BUY" or "SELL"

        logger.info(
            f"ExposureManager initialized: "
            f"Max positions/symbol: {self.max_positions_per_symbol}, "
            f"Asset class limits: {self.max_positions_per_asset_class}, "
            f"Correlation checking: {self.correlation_enabled}"
        )

    def can_open_position(
        self, symbol: str, asset_class: str, risk_amount: float, direction: str = None
    ) -> tuple[bool, str]:
        """
        Check if a new position can be opened.

        Args:
            symbol: Trading symbol
            asset_class: Asset class (forex_major, forex_jpy, etc.)
            risk_amount: Risk amount for the position
            direction: Position direction ("BUY" or "SELL")

        Returns:
            Tuple of (can_open, reason)
        """
        # Check per-symbol limit
        current_symbol_positions = self.positions_by_symbol.get(symbol, 0)
        if current_symbol_positions >= self.max_positions_per_symbol:
            return (
                False,
                f"Symbol limit reached: {current_symbol_positions}/{self.max_positions_per_symbol}",
            )

        # Check per-asset-class limit (from active_symbols.yaml)
        if asset_class in self.max_positions_per_asset_class:
            current_asset_class_positions = self.positions_by_asset_class.get(asset_class, 0)
            max_for_asset_class = self.max_positions_per_asset_class[asset_class]
            if current_asset_class_positions >= max_for_asset_class:
                return (
                    False,
                    f"Asset class {asset_class} limit reached: {current_asset_class_positions}/{max_for_asset_class}",
                )

        # No global total-positions check — per-asset-class limits above are
        # the single source of truth for position count caps.

        # Check correlation conflicts (if direction provided)
        if direction and self.correlation_enabled:
            conflict_reason = self._check_correlation_conflict(symbol, direction)
            if conflict_reason:
                logger.warning(
                    f"Correlation conflict detected for {symbol} {direction}: {conflict_reason}"
                )
                return False, conflict_reason

        # Check asset class exposure (if we have portfolio balance)
        # This would need portfolio balance to calculate percentage
        # For now, we just track counts

        return True, "OK"

    def register_position(
        self,
        symbol: str,
        asset_class: str,
        volume: float,
        currency_pair: str = None,
        direction: str = None,
    ) -> None:
        """
        Register a new position.

        Args:
            symbol: Trading symbol
            asset_class: Asset class
            volume: Position volume
            currency_pair: Currency pair (e.g., "EUR/USD")
            direction: Position direction ("BUY" or "SELL")
        """
        self.positions_by_symbol[symbol] += 1
        self.positions_by_asset_class[asset_class] += 1

        # Track position direction for correlation checking
        if direction:
            self.position_directions[symbol] = direction.upper()

        # Track currency exposure if provided
        if currency_pair:
            currencies = currency_pair.split("/")
            if len(currencies) == 2:
                base, quote = currencies
                self.currency_exposure[base] += volume
                self.currency_exposure[quote] -= volume

        logger.debug(
            f"Position registered: {symbol} ({asset_class}), "
            f"Direction: {direction}, "
            f"Total positions: {sum(self.positions_by_symbol.values())}"
        )

    def unregister_position(
        self, symbol: str, asset_class: str, volume: float, currency_pair: str = None
    ) -> None:
        """
        Unregister a closed position.

        Args:
            symbol: Trading symbol
            asset_class: Asset class
            volume: Position volume
            currency_pair: Currency pair
        """
        if self.positions_by_symbol[symbol] > 0:
            self.positions_by_symbol[symbol] -= 1

        if self.positions_by_asset_class[asset_class] > 0:
            self.positions_by_asset_class[asset_class] -= 1

        # Remove direction tracking
        if symbol in self.position_directions:
            del self.position_directions[symbol]

        # Update currency exposure
        if currency_pair:
            currencies = currency_pair.split("/")
            if len(currencies) == 2:
                base, quote = currencies
                self.currency_exposure[base] -= volume
                self.currency_exposure[quote] += volume

        logger.debug(f"Position unregistered: {symbol} ({asset_class})")

    def get_symbol_position_count(self, symbol: str) -> int:
        """
        Get number of open positions for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Number of open positions
        """
        return self.positions_by_symbol.get(symbol, 0)

    def get_total_position_count(self) -> int:
        """
        Get total number of open positions.

        Returns:
            Total position count
        """
        return sum(self.positions_by_symbol.values())

    def get_asset_class_exposure(self, asset_class: str) -> int:
        """
        Get number of positions for an asset class.

        Args:
            asset_class: Asset class

        Returns:
            Number of positions
        """
        return self.positions_by_asset_class.get(asset_class, 0)

    def get_currency_exposure(self, currency: str) -> float:
        """
        Get net exposure for a currency.

        Args:
            currency: Currency code (e.g., "EUR", "USD")

        Returns:
            Net exposure (positive = long, negative = short)
        """
        return self.currency_exposure.get(currency, 0.0)

    def get_exposure_summary(self) -> dict:
        """
        Get exposure summary.

        Returns:
            Dictionary with exposure statistics
        """
        return {
            "total_positions": self.get_total_position_count(),
            "positions_by_symbol": dict(self.positions_by_symbol),
            "positions_by_asset_class": dict(self.positions_by_asset_class),
            "currency_exposure": dict(self.currency_exposure),
            "max_positions_per_symbol": self.max_positions_per_symbol,
            "max_positions_per_asset_class": dict(self.max_positions_per_asset_class),
        }

    def _build_correlation_groups(self) -> dict[str, list[str]]:
        """
        Build correlation groups for currency pairs.

        Loads from config YAML if available, otherwise uses hardcoded defaults.

        Returns:
            Dictionary mapping symbol to list of correlated symbols
        """
        # Try to load from config first
        config_groups = (
            self.config.get("risk_management", {})
            .get("correlation_management", {})
            .get("correlation_groups", {})
        )

        if config_groups:
            # Use config if available
            correlation_groups = config_groups
        else:
            # Fallback to hardcoded defaults if config not found
            correlation_groups = {
                # Major USD pairs (positive correlation)
                "EURUSD": ["GBPUSD", "AUDUSD", "NZDUSD"],
                "GBPUSD": ["EURUSD", "AUDUSD", "NZDUSD"],
                "AUDUSD": ["EURUSD", "GBPUSD", "NZDUSD"],
                "NZDUSD": ["EURUSD", "GBPUSD", "AUDUSD"],
                # USD pairs (positive correlation)
                "USDJPY": ["USDCHF", "USDCAD"],
                "USDCHF": ["USDJPY", "USDCAD"],
                "USDCAD": ["USDJPY", "USDCHF"],
                # JPY pairs (positive correlation)
                "EURJPY": ["GBPJPY", "AUDJPY"],
                "GBPJPY": ["EURJPY", "AUDJPY"],
                "AUDJPY": ["EURJPY", "GBPJPY"],
            }

        # Build reverse mapping (symbol -> correlated symbols)
        # This ensures bidirectional correlation (if A correlates with B, then B correlates with A)
        result = {}
        for symbol, correlated in correlation_groups.items():
            # Normalize symbol
            normalized = symbol.upper().strip()

            # Normalize correlated symbols list
            if isinstance(correlated, list):
                normalized_correlated = [s.upper().strip() for s in correlated]
            else:
                # Handle case where config might have different structure
                normalized_correlated = []

            result[normalized] = normalized_correlated

            # Also add reverse mappings (bidirectional)
            for corr_symbol in normalized_correlated:
                if corr_symbol not in result:
                    result[corr_symbol] = []
                if normalized not in result[corr_symbol]:
                    result[corr_symbol].append(normalized)

        return result

    def _build_negative_correlation_groups(self) -> dict[str, list[str]]:
        """
        Build negative correlation groups for currency pairs.

        Negative correlation means pairs move in opposite directions.
        Example: USDCAD BUY (USD strong) vs EURUSD SELL (USD weak vs EUR)

        Loads from config YAML if available, otherwise uses hardcoded defaults.

        Returns:
            Dictionary mapping symbol to list of negatively correlated symbols
        """
        # Try to load from config first
        config_groups = (
            self.config.get("risk_management", {})
            .get("correlation_management", {})
            .get("negative_correlation_groups", {})
        )

        if config_groups:
            # Use config if available
            negative_correlation_groups = config_groups
        else:
            # Fallback to hardcoded defaults if config not found
            negative_correlation_groups = {
                # USD pairs vs Major pairs (negative correlation)
                # When USD is strong (USDCAD/USDJPY/USDCHF BUY), major pairs should be weak (EURUSD/GBPUSD SELL)
                "USDCAD": ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"],
                "USDJPY": ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"],
                "USDCHF": ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"],
                # Reverse mapping: Major pairs vs USD pairs
                "EURUSD": ["USDCAD", "USDJPY", "USDCHF"],
                "GBPUSD": ["USDCAD", "USDJPY", "USDCHF"],
                "AUDUSD": ["USDCAD", "USDJPY", "USDCHF"],
                "NZDUSD": ["USDCAD", "USDJPY", "USDCHF"],
            }

        # Build reverse mapping (symbol -> negatively correlated symbols)
        # This ensures bidirectional negative correlation
        result = {}
        for symbol, correlated in negative_correlation_groups.items():
            # Normalize symbol
            normalized = symbol.upper().strip()

            # Normalize correlated symbols list
            if isinstance(correlated, list):
                normalized_correlated = [s.upper().strip() for s in correlated]
            else:
                normalized_correlated = []

            result[normalized] = normalized_correlated

            # Also add reverse mappings (bidirectional)
            for corr_symbol in normalized_correlated:
                if corr_symbol not in result:
                    result[corr_symbol] = []
                if normalized not in result[corr_symbol]:
                    result[corr_symbol].append(normalized)

        return result

    def _check_correlation_conflict(self, symbol: str, direction: str) -> str | None:
        """
        Check if opening a position would conflict with correlated pairs.

        Handles both:
        - Positive correlation: pairs that move together (should have same direction)
        - Negative correlation: pairs that move opposite (should have opposite direction)

        Args:
            symbol: Trading symbol to check
            direction: Position direction ("BUY" or "SELL")

        Returns:
            Error message if conflict found, None otherwise
        """
        if not self.position_directions:
            return None

        # Normalize symbol and direction
        normalized_symbol = symbol.upper().strip()
        normalized_direction = direction.upper()

        # Check positive correlation (pairs that move together - same direction required)
        correlated_symbols = self.correlated_pairs.get(normalized_symbol, [])
        for corr_symbol in correlated_symbols:
            if corr_symbol in self.position_directions:
                existing_direction = self.position_directions[corr_symbol]
                if existing_direction != normalized_direction:
                    return (
                        f"Positive correlation conflict: {corr_symbol} has {existing_direction} position, "
                        f"cannot open {normalized_direction} for {symbol} "
                        f"(correlated pairs should have same direction)"
                    )

        # Check negative correlation (pairs that move opposite - opposite direction required)
        negative_correlated_symbols = self.negative_correlated_pairs.get(normalized_symbol, [])
        for neg_corr_symbol in negative_correlated_symbols:
            if neg_corr_symbol in self.position_directions:
                existing_direction = self.position_directions[neg_corr_symbol]
                # For negative correlation, directions should be opposite
                opposite_direction = "SELL" if normalized_direction == "BUY" else "BUY"
                if existing_direction != opposite_direction:
                    return (
                        f"Negative correlation conflict: {neg_corr_symbol} has {existing_direction} position, "
                        f"cannot open {normalized_direction} for {symbol} "
                        f"(negatively correlated pairs should have opposite direction: {neg_corr_symbol} {existing_direction} → {symbol} {opposite_direction})"
                    )

        return None

    def reset_tracking(self) -> None:
        """Reset exposure tracking (for testing or new session)."""
        self.positions_by_symbol.clear()
        self.positions_by_asset_class.clear()
        self.currency_exposure.clear()
        self.position_directions.clear()
        logger.info("Exposure tracking reset")

    def __str__(self) -> str:
        """String representation."""
        return (
            f"ExposureManager("
            f"{self.get_total_position_count()} positions, "
            f"{len(self.positions_by_symbol)} symbols)"
        )

    def __repr__(self) -> str:
        """Developer representation."""
        return self.__str__()
