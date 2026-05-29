"""
Forex Position Manager - Major pairs (EURUSD, GBPUSD, etc.).

Asset-specific parameters:
- Pip size: 0.0001
- Breakeven: 15 pips trigger, 2 pips buffer
- Trailing: 20 pips activation, 10 pips distance
- Partial close: 20 pips (25%), 40 pips (50%)
"""

from trading_worker.position.asset_managers.base_asset_manager import BaseAssetManager


class ForexPositionManager(BaseAssetManager):
    """Position manager for Forex major pairs."""

    def get_asset_class(self) -> str:
        """Get asset class name."""
        return "Forex Major"

    def get_pip_size(self) -> float:
        """Get pip size for forex major pairs."""
        return 0.0001

    def get_breakeven_distance(self) -> float:
        """Get breakeven trigger distance."""
        return 15.0  # 15 pips

    def get_breakeven_buffer(self) -> float:
        """Get breakeven buffer."""
        return 2.0  # 2 pips

    def get_trailing_activation(self) -> float:
        """Get trailing stop activation threshold."""
        return 20.0  # 20 pips

    def get_trailing_distance(self) -> float:
        """Get trailing stop distance."""
        return 10.0  # 10 pips

    def get_partial_close_levels(self) -> list[tuple[float, float]]:
        """Get partial close levels."""
        return [
            (20.0, 0.25),  # Close 25% at 20 pips
            (40.0, 0.50),  # Close 50% at 40 pips
        ]
