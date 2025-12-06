"""
Risk Management Module.

Provides comprehensive portfolio risk control including:
- Portfolio risk management
- Correlation analysis
- Exposure management
- Drawdown protection
"""

from trading_bot.risk.drawdown_protector import DrawdownProtector
from trading_bot.risk.exposure_manager import ExposureManager
from trading_bot.risk.portfolio_risk_manager import PortfolioRiskManager

__all__ = [
    "PortfolioRiskManager",
    "ExposureManager",
    "DrawdownProtector",
]

