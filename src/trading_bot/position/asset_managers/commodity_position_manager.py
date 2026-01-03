"""
Commodity Position Manager - Gold, Silver (XAUUSD, XAGUSD).

Asset-specific parameters:
- Pip size: 0.1
- Breakeven: 500 pips trigger, 50 pips buffer
- Trailing: 600 pips activation, 300 pips distance
- Partial close: 600 pips (25%), 1200 pips (50%)
"""

from trading_bot.position.asset_managers.base_asset_manager import BaseAssetManager


class CommodityPositionManager(BaseAssetManager):
    """Position manager for commodities (Gold, Silver)."""

    def get_asset_class(self) -> str:
        """Get asset class name."""
        return "commodities"

    def get_pip_size(self) -> float:
        """Get pip size for commodities."""
        return 0.1

    def get_breakeven_distance(self) -> float:
        """Get breakeven trigger distance."""
        return 500.0  # 500 pips (for Gold)

    def get_breakeven_buffer(self) -> float:
        """Get breakeven buffer."""
        return 50.0  # 50 pips

    def get_trailing_activation(self) -> float:
        """Get trailing stop activation threshold."""
        return 600.0  # 600 pips

    def get_trailing_distance(self) -> float:
        """Get trailing stop distance."""
        return 300.0  # 300 pips

    def get_partial_close_levels(self) -> list[tuple[float, float]]:
        """Get partial close levels."""
        return [
            (600.0, 0.25),  # Close 25% at 600 pips
            (1200.0, 0.50),  # Close 50% at 1200 pips
        ]
