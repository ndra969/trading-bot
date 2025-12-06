"""
Position Management Module.

Provides comprehensive position lifecycle management including:
- Asset-specific pip calculations
- Real-time position tracking and P&L
- Automated position management
"""

from trading_bot.position.pip_calculator import PipCalculator
from trading_bot.position.position_manager import PositionManager
from trading_bot.position.position_models import (
    Position,
    PositionStatus,
    PositionType,
)
from trading_bot.position.position_tracker import PositionTracker

__all__ = [
    "PipCalculator",
    "PositionManager",
    "PositionTracker",
    "Position",
    "PositionStatus",
    "PositionType",
]
