"""
Forex JPY Position Manager - JPY pairs (USDJPY, EURJPY, etc.).

Asset-specific parameters:
- Pip size: 0.01
- Breakeven: 150 pips trigger, 20 pips buffer
- Trailing: 200 pips activation, 100 pips distance
- Partial close: 200 pips (25%), 400 pips (50%)
"""

from trading_worker.position.asset_managers.base_asset_manager import BaseAssetManager


class ForexJPYPositionManager(BaseAssetManager):
    """Position manager for Forex JPY pairs."""

    def get_asset_class(self) -> str:
        """Get asset class name."""
        return "Forex JPY"

    def get_pip_size(self) -> float:
        """Get pip size for JPY pairs."""
        return 0.01

    def get_breakeven_distance(self) -> float:
        """Get breakeven trigger distance."""
        return 150.0  # 150 pips

    def get_breakeven_buffer(self) -> float:
        """Get breakeven buffer."""
        return 20.0  # 20 pips

    def get_trailing_activation(self) -> float:
        """Get trailing stop activation threshold."""
        return 200.0  # 200 pips

    def get_trailing_distance(self) -> float:
        """Get trailing stop distance."""
        return 100.0  # 100 pips

    def get_partial_close_levels(self) -> list[tuple[float, float]]:
        """Get partial close levels."""
        return [
            (200.0, 0.25),  # Close 25% at 200 pips
            (400.0, 0.50),  # Close 50% at 400 pips
        ]
