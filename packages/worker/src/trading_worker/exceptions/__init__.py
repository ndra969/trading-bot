"""Custom exceptions for the trading bot."""

from .connector_exceptions import (
    ConnectionFailedError,
    ConnectorError,
    DataRetrievalError,
)
from .mt5_exceptions import (
    MT5ConnectionError,
    MT5DataError,
    MT5OrderError,
    MT5PermissionError,
    MT5SymbolError,
    MT5TerminalNotRunningError,
    MT5VersionIncompatibleError,
)
from .strategy_exceptions import (
    ConfluenceCalculationError,
    InsufficientDataError,
    SignalGenerationError,
    StrategyException,
    ZoneDetectionError,
    ZoneValidationError,
)

__all__ = [
    # MT5 Exceptions
    "MT5ConnectionError",
    "MT5TerminalNotRunningError",
    "MT5VersionIncompatibleError",
    "MT5PermissionError",
    "MT5OrderError",
    "MT5SymbolError",
    "MT5DataError",
    # Connector Exceptions
    "ConnectorError",
    "ConnectionFailedError",
    "DataRetrievalError",
    # Strategy Exceptions
    "StrategyException",
    "ZoneDetectionError",
    "ZoneValidationError",
    "InsufficientDataError",
    "SignalGenerationError",
    "ConfluenceCalculationError",
]
