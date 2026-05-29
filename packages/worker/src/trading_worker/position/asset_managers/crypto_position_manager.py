"""
Crypto Position Manager - Bitcoin, Ethereum (BTCUSD, ETHUSD).

Asset-specific parameters:
- Pip size: 1.0 USD
- Breakeven: 50 USD trigger, 5 USD buffer
- Trailing: 60 USD activation, 30 USD distance
- Partial close: 100 USD (25%), 200 USD (50%)
"""

from trading_worker.position.asset_managers.base_asset_manager import BaseAssetManager


class CryptoPositionManager(BaseAssetManager):
    """Position manager for cryptocurrencies."""

    def get_asset_class(self) -> str:
        """Get asset class name."""
        return "Crypto"

    def get_pip_size(self) -> float:
        """Get pip size for crypto (USD)."""
        return 1.0

    def get_breakeven_distance(self) -> float:
        """Get breakeven trigger distance."""
        return 50.0  # 50 USD

    def get_breakeven_buffer(self) -> float:
        """Get breakeven buffer."""
        return 5.0  # 5 USD

    def get_trailing_activation(self) -> float:
        """Get trailing stop activation threshold."""
        return 60.0  # 60 USD

    def get_trailing_distance(self) -> float:
        """Get trailing stop distance."""
        return 30.0  # 30 USD

    def get_partial_close_levels(self) -> list[tuple[float, float]]:
        """Get partial close levels."""
        return [
            (100.0, 0.25),  # Close 25% at 100 USD
            (200.0, 0.50),  # Close 50% at 200 USD
        ]
