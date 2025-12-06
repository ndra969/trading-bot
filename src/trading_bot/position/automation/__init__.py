"""
Position Automation Module.

Provides automated position management features:
- Breakeven automation
- Trailing stop management
- Partial close automation
"""

from trading_bot.position.automation.breakeven_manager import BreakevenManager
from trading_bot.position.automation.partial_close_manager import PartialCloseManager
from trading_bot.position.automation.trailing_stop_manager import TrailingStopManager

__all__ = [
    "BreakevenManager",
    "TrailingStopManager",
    "PartialCloseManager",
]
