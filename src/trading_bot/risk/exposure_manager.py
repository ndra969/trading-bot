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
        self.max_total_positions = self.config.get("risk_management", {}).get(
            "max_total_positions", 10
        )
        self.max_leverage = self.config.get("risk_management", {}).get("max_leverage", 10.0)

        # Asset class exposure limits (percentage of portfolio)
        self.max_asset_class_exposure_pct = self.config.get("risk_management", {}).get(
            "max_asset_class_exposure_percent", 40.0
        )

        # Tracking
        self.positions_by_symbol: dict[str, int] = defaultdict(int)
        self.positions_by_asset_class: dict[str, int] = defaultdict(int)
        self.currency_exposure: dict[str, float] = defaultdict(float)

        logger.info(
            f"ExposureManager initialized: "
            f"Max positions/symbol: {self.max_positions_per_symbol}, "
            f"Max total: {self.max_total_positions}"
        )

    def can_open_position(
        self, symbol: str, asset_class: str, risk_amount: float
    ) -> tuple[bool, str]:
        """
        Check if a new position can be opened.

        Args:
            symbol: Trading symbol
            asset_class: Asset class (forex_major, forex_jpy, etc.)
            risk_amount: Risk amount for the position

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

        # Check total positions limit
        total_positions = sum(self.positions_by_symbol.values())
        if total_positions >= self.max_total_positions:
            return (
                False,
                f"Total position limit reached: {total_positions}/{self.max_total_positions}",
            )

        # Check asset class exposure (if we have portfolio balance)
        # This would need portfolio balance to calculate percentage
        # For now, we just track counts

        return True, "OK"

    def register_position(
        self, symbol: str, asset_class: str, volume: float, currency_pair: str = None
    ) -> None:
        """
        Register a new position.

        Args:
            symbol: Trading symbol
            asset_class: Asset class
            volume: Position volume
            currency_pair: Currency pair (e.g., "EUR/USD")
        """
        self.positions_by_symbol[symbol] += 1
        self.positions_by_asset_class[asset_class] += 1

        # Track currency exposure if provided
        if currency_pair:
            currencies = currency_pair.split("/")
            if len(currencies) == 2:
                base, quote = currencies
                self.currency_exposure[base] += volume
                self.currency_exposure[quote] -= volume

        logger.debug(
            f"Position registered: {symbol} ({asset_class}), "
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
            "max_total_positions": self.max_total_positions,
        }

    def reset_tracking(self) -> None:
        """Reset exposure tracking (for testing or new session)."""
        self.positions_by_symbol.clear()
        self.positions_by_asset_class.clear()
        self.currency_exposure.clear()
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
