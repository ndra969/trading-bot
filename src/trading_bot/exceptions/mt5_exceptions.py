"""
MetaTrader5-specific exceptions.

Custom exception hierarchy for MT5 operations.
"""


class MT5ConnectionError(Exception):
    """Base exception for MT5 connection errors."""

    pass


class MT5TerminalNotRunningError(MT5ConnectionError):
    """Exception raised when MT5 terminal is not running."""

    def __init__(self, message: str = "MT5 terminal is not running"):
        self.message = message
        super().__init__(self.message)


class MT5VersionIncompatibleError(MT5ConnectionError):
    """Exception raised when MT5 version is incompatible."""

    def __init__(self, version: str, min_version: str = "5.0.0"):
        self.message = f"MT5 version {version} is incompatible. Minimum required: {min_version}"
        super().__init__(self.message)


class MT5PermissionError(MT5ConnectionError):
    """Exception raised when MT5 permissions are insufficient."""

    def __init__(self, message: str = "Insufficient permissions to access MT5"):
        self.message = message
        super().__init__(self.message)


class MT5OrderError(Exception):
    """Base exception for MT5 order-related errors."""

    def __init__(self, message: str, error_code: int = 0):
        self.message = message
        self.error_code = error_code
        super().__init__(f"{message} (Error code: {error_code})")


class MT5SymbolError(Exception):
    """Exception for MT5 symbol-related errors."""

    def __init__(self, symbol: str, message: str):
        self.symbol = symbol
        self.message = message
        super().__init__(f"Symbol '{symbol}': {message}")


class MT5DataError(Exception):
    """Exception for MT5 data retrieval errors."""

    def __init__(self, message: str, symbol: str = None, timeframe: str = None):
        self.symbol = symbol
        self.timeframe = timeframe
        details = []
        if symbol:
            details.append(f"Symbol: {symbol}")
        if timeframe:
            details.append(f"Timeframe: {timeframe}")
        detail_str = ", ".join(details) if details else "No details"
        super().__init__(f"{message} ({detail_str})")
