"""
Asset-Specific Position Managers.

Provides specialized position management for different asset classes.
"""

from trading_bot.position.asset_managers.asset_manager_factory import (
    AssetManagerFactory,
    get_asset_manager,
)
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

__all__ = [
    "BaseAssetManager",
    "ForexPositionManager",
    "ForexJPYPositionManager",
    "CommodityPositionManager",
    "CryptoPositionManager",
    "AssetManagerFactory",
    "get_asset_manager",
]
