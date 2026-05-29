"""
Base Asset Manager - Abstract base for asset-specific managers.

Defines interface for asset-specific position management.
"""

from abc import ABC, abstractmethod

from trading_core.utils.logger import get_logger

logger = get_logger(__name__)


class BaseAssetManager(ABC):
    """
    Abstract base class for asset-specific position managers.

    Each asset class (Forex, JPY, Commodity, Crypto) has specific
    parameters for pip size, breakeven, trailing, and partial closes.
    """

    def __init__(self):
        """Initialize base asset manager."""
        self.asset_class = self.get_asset_class()
        logger.debug(f"{self.asset_class} AssetManager initialized")

    @abstractmethod
    def get_asset_class(self) -> str:
        """Get asset class name."""
        pass

    @abstractmethod
    def get_pip_size(self) -> float:
        """Get pip size for this asset class."""
        pass

    @abstractmethod
    def get_breakeven_distance(self) -> float:
        """Get breakeven trigger distance in pips."""
        pass

    @abstractmethod
    def get_breakeven_buffer(self) -> float:
        """Get breakeven buffer in pips."""
        pass

    @abstractmethod
    def get_trailing_activation(self) -> float:
        """Get trailing stop activation threshold in pips."""
        pass

    @abstractmethod
    def get_trailing_distance(self) -> float:
        """Get trailing stop distance in pips."""
        pass

    @abstractmethod
    def get_partial_close_levels(self) -> list[tuple[float, float]]:
        """
        Get partial close levels.

        Returns:
            List of (distance_pips, close_percentage) tuples
        """
        pass

    def get_parameters(self) -> dict:
        """
        Get all parameters for this asset class.

        Returns:
            Dictionary with all asset-specific parameters
        """
        return {
            "asset_class": self.get_asset_class(),
            "pip_size": self.get_pip_size(),
            "breakeven": {
                "distance": self.get_breakeven_distance(),
                "buffer": self.get_breakeven_buffer(),
            },
            "trailing": {
                "activation": self.get_trailing_activation(),
                "distance": self.get_trailing_distance(),
            },
            "partial_close_levels": self.get_partial_close_levels(),
        }

    def __str__(self) -> str:
        """String representation."""
        return f"{self.get_asset_class()}Manager"

    def __repr__(self) -> str:
        """Developer representation."""
        return self.__str__()
