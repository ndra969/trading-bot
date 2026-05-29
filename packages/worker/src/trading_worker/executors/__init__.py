"""
Trading executors package.

This package provides executor classes for different trading types:
- day_trading (IntradayExecutor)
- swing_trading (SwingExecutor) - TODO
- scalping (ScalpingExecutor) - TODO
- position_trading (PositionExecutor) - TODO

The executor pattern allows the trading bot to switch between different
trading styles by configuration, without modifying the core bot logic.
"""

from .base_executor import TradingTypeExecutor
from .factory import TradingTypeFactory
from .intraday_executor import IntradayExecutor

__all__ = ["TradingTypeExecutor", "TradingTypeFactory", "IntradayExecutor"]
