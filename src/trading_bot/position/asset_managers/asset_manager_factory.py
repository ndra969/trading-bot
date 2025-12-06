"""
Asset Manager Factory - Factory pattern for asset-specific managers.

Provides automatic asset manager selection based on symbol.
"""

from trading_bot.position.asset_managers.base_asset_manager import BaseAssetManager
from trading_bot.position.asset_managers.commodity_position_manager import (
    CommodityPositionManager,
)
from trading_bot.position.asset_managers.crypto_position_manager import (
    CryptoPositionManager,
)
from trading_bot.position.asset_managers.forex_jpy_position_manager import (
    ForexJPYPositionManager,
)
from trading_bot.position.asset_managers.forex_position_manager import (
    ForexPositionManager,
)
from trading_bot.utils.logger import get_logger

logger = get_logger(__name__)


class AssetManagerFactory:
    """
    Factory for creating asset-specific position managers.

    Automatically determines the correct manager based on symbol.
    """

    # Manager instances (singleton pattern)
    _managers: dict[str, BaseAssetManager] = {}

    @classmethod
    def get_manager(cls, symbol: str) -> BaseAssetManager:
        """
        Get asset manager for a symbol.

        Args:
            symbol: Trading symbol (e.g., EURUSD, USDJPY, XAUUSD, BTCUSD)

        Returns:
            Asset-specific position manager
        """
        asset_class = cls._determine_asset_class(symbol)

        # Return cached instance if available
        if asset_class in cls._managers:
            return cls._managers[asset_class]

        # Create and cache new instance
        manager = cls._create_manager(asset_class)
        cls._managers[asset_class] = manager

        logger.debug(f"Created {asset_class} manager for {symbol}")
        return manager

    @classmethod
    def _determine_asset_class(cls, symbol: str) -> str:
        """
        Determine asset class from symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Asset class identifier
        """
        symbol = symbol.upper()

        # Check for JPY pairs
        if "JPY" in symbol:
            return "forex_jpy"

        # Check for commodities (Gold, Silver)
        if symbol in ["XAUUSD", "GOLD", "XAGUSD", "SILVER"]:
            return "commodities"

        # Check for crypto
        if symbol in ["BTCUSD", "ETHUSD", "BTCUSDT", "ETHUSDT"]:
            return "crypto"

        # Default to forex major
        return "forex_major"

    @classmethod
    def _create_manager(cls, asset_class: str) -> BaseAssetManager:
        """
        Create asset manager for asset class.

        Args:
            asset_class: Asset class identifier

        Returns:
            Asset-specific position manager

        Raises:
            ValueError: If asset class is unknown
        """
        if asset_class == "forex_major":
            return ForexPositionManager()
        elif asset_class == "forex_jpy":
            return ForexJPYPositionManager()
        elif asset_class == "commodities":
            return CommodityPositionManager()
        elif asset_class == "crypto":
            return CryptoPositionManager()
        else:
            raise ValueError(f"Unknown asset class: {asset_class}")

    @classmethod
    def get_all_managers(cls) -> dict[str, BaseAssetManager]:
        """
        Get all available asset managers.

        Returns:
            Dictionary of asset_class -> manager
        """
        return {
            "forex_major": ForexPositionManager(),
            "forex_jpy": ForexJPYPositionManager(),
            "commodities": CommodityPositionManager(),
            "crypto": CryptoPositionManager(),
        }

    @classmethod
    def clear_cache(cls) -> None:
        """Clear manager cache (useful for testing)."""
        cls._managers.clear()


# Convenience function
def get_asset_manager(symbol: str) -> BaseAssetManager:
    """
    Get asset manager for a symbol.

    Args:
        symbol: Trading symbol

    Returns:
        Asset-specific position manager
    """
    return AssetManagerFactory.get_manager(symbol)
