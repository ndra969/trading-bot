"""
Trading Bot - Modern Python Trading System

A sophisticated automated trading bot with:
- Modern Python architecture (UV + Click + SQLAlchemy 2.0)
- MetaTrader5 integration
- Multi-asset support (Forex, Commodities, Crypto)
- Advanced risk management
- Test-driven development
"""

__version__ = "1.0.0"
__author__ = "Trading Bot Team"

# Expose key components
from .config import Configuration

__all__ = ["Configuration", "__version__"]
