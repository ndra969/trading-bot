"""
Risk Management Module.

Provides comprehensive portfolio risk control including:
- Portfolio risk management
- Correlation analysis
- Exposure management
- Drawdown protection
"""

from trading_worker.risk.drawdown_protector import DrawdownProtector
from trading_worker.risk.exposure_manager import ExposureManager
from trading_worker.risk.portfolio_risk_manager import PortfolioRiskManager

__all__ = [
    "PortfolioRiskManager",
    "ExposureManager",
    "DrawdownProtector",
]
