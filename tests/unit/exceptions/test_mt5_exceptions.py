"""
Unit tests for MT5 exceptions.
"""

import pytest
from trading_worker.exceptions.mt5_exceptions import (
    MT5ConnectionError,
    MT5DataError,
    MT5OrderError,
    MT5PermissionError,
    MT5SymbolError,
    MT5TerminalNotRunningError,
    MT5VersionIncompatibleError,
)


class TestMT5ConnectionError:
    """Test MT5ConnectionError exception."""

    def test_mt5_connection_error_raises(self):
        """Test that MT5ConnectionError can be raised."""
        with pytest.raises(MT5ConnectionError):
            raise MT5ConnectionError("Connection failed")

    def test_mt5_connection_error_inheritance(self):
        """Test that MT5ConnectionError inherits from Exception."""
        assert issubclass(MT5ConnectionError, Exception)


class TestMT5TerminalNotRunningError:
    """Test MT5TerminalNotRunningError exception."""

    def test_mt5_terminal_not_running_error_default(self):
        """Test MT5TerminalNotRunningError with default message."""
        with pytest.raises(MT5TerminalNotRunningError) as exc_info:
            raise MT5TerminalNotRunningError()

        assert exc_info.value.message == "MT5 terminal is not running"

    def test_mt5_terminal_not_running_error_custom(self):
        """Test MT5TerminalNotRunningError with custom message."""
        with pytest.raises(MT5TerminalNotRunningError) as exc_info:
            raise MT5TerminalNotRunningError("Custom error message")

        assert exc_info.value.message == "Custom error message"

    def test_mt5_terminal_not_running_error_inheritance(self):
        """Test that MT5TerminalNotRunningError inherits from MT5ConnectionError."""
        assert issubclass(MT5TerminalNotRunningError, MT5ConnectionError)


class TestMT5VersionIncompatibleError:
    """Test MT5VersionIncompatibleError exception."""

    def test_mt5_version_incompatible_error_default(self):
        """Test MT5VersionIncompatibleError with default min_version."""
        with pytest.raises(MT5VersionIncompatibleError) as exc_info:
            raise MT5VersionIncompatibleError("4.0.0")

        assert "4.0.0" in str(exc_info.value)
        assert "5.0.0" in str(exc_info.value)

    def test_mt5_version_incompatible_error_custom(self):
        """Test MT5VersionIncompatibleError with custom min_version."""
        with pytest.raises(MT5VersionIncompatibleError) as exc_info:
            raise MT5VersionIncompatibleError("4.5.0", "5.1.0")

        assert "4.5.0" in str(exc_info.value)
        assert "5.1.0" in str(exc_info.value)

    def test_mt5_version_incompatible_error_inheritance(self):
        """Test that MT5VersionIncompatibleError inherits from MT5ConnectionError."""
        assert issubclass(MT5VersionIncompatibleError, MT5ConnectionError)


class TestMT5PermissionError:
    """Test MT5PermissionError exception."""

    def test_mt5_permission_error_default(self):
        """Test MT5PermissionError with default message."""
        with pytest.raises(MT5PermissionError) as exc_info:
            raise MT5PermissionError()

        assert exc_info.value.message == "Insufficient permissions to access MT5"

    def test_mt5_permission_error_custom(self):
        """Test MT5PermissionError with custom message."""
        with pytest.raises(MT5PermissionError) as exc_info:
            raise MT5PermissionError("Custom permission error")

        assert exc_info.value.message == "Custom permission error"

    def test_mt5_permission_error_inheritance(self):
        """Test that MT5PermissionError inherits from MT5ConnectionError."""
        assert issubclass(MT5PermissionError, MT5ConnectionError)


class TestMT5OrderError:
    """Test MT5OrderError exception."""

    def test_mt5_order_error_with_message(self):
        """Test MT5OrderError with message only."""
        with pytest.raises(MT5OrderError) as exc_info:
            raise MT5OrderError("Order failed")

        assert exc_info.value.message == "Order failed"
        assert exc_info.value.error_code == 0
        assert "Order failed" in str(exc_info.value)
        assert "Error code: 0" in str(exc_info.value)

    def test_mt5_order_error_with_code(self):
        """Test MT5OrderError with message and error code."""
        with pytest.raises(MT5OrderError) as exc_info:
            raise MT5OrderError("Order rejected", error_code=10004)

        assert exc_info.value.message == "Order rejected"
        assert exc_info.value.error_code == 10004
        assert "Order rejected" in str(exc_info.value)
        assert "Error code: 10004" in str(exc_info.value)

    def test_mt5_order_error_inheritance(self):
        """Test that MT5OrderError inherits from Exception."""
        assert issubclass(MT5OrderError, Exception)


class TestMT5SymbolError:
    """Test MT5SymbolError exception."""

    def test_mt5_symbol_error(self):
        """Test MT5SymbolError."""
        with pytest.raises(MT5SymbolError) as exc_info:
            raise MT5SymbolError("EURUSD", "Symbol not found")

        assert exc_info.value.symbol == "EURUSD"
        assert exc_info.value.message == "Symbol not found"
        assert "EURUSD" in str(exc_info.value)
        assert "Symbol not found" in str(exc_info.value)

    def test_mt5_symbol_error_inheritance(self):
        """Test that MT5SymbolError inherits from Exception."""
        assert issubclass(MT5SymbolError, Exception)


class TestMT5DataError:
    """Test MT5DataError exception."""

    def test_mt5_data_error_message_only(self):
        """Test MT5DataError with message only."""
        with pytest.raises(MT5DataError) as exc_info:
            raise MT5DataError("Data retrieval failed")

        assert exc_info.value.symbol is None
        assert exc_info.value.timeframe is None
        assert "Data retrieval failed" in str(exc_info.value)
        assert "No details" in str(exc_info.value)

    def test_mt5_data_error_with_symbol(self):
        """Test MT5DataError with symbol."""
        with pytest.raises(MT5DataError) as exc_info:
            raise MT5DataError("Data retrieval failed", symbol="EURUSD")

        assert exc_info.value.symbol == "EURUSD"
        assert exc_info.value.timeframe is None
        assert "Data retrieval failed" in str(exc_info.value)
        assert "Symbol: EURUSD" in str(exc_info.value)

    def test_mt5_data_error_with_timeframe(self):
        """Test MT5DataError with timeframe."""
        with pytest.raises(MT5DataError) as exc_info:
            raise MT5DataError("Data retrieval failed", timeframe="H1")

        assert exc_info.value.symbol is None
        assert exc_info.value.timeframe == "H1"
        assert "Data retrieval failed" in str(exc_info.value)
        assert "Timeframe: H1" in str(exc_info.value)

    def test_mt5_data_error_with_both(self):
        """Test MT5DataError with symbol and timeframe."""
        with pytest.raises(MT5DataError) as exc_info:
            raise MT5DataError("Data retrieval failed", symbol="EURUSD", timeframe="H1")

        assert exc_info.value.symbol == "EURUSD"
        assert exc_info.value.timeframe == "H1"
        assert "Data retrieval failed" in str(exc_info.value)
        assert "Symbol: EURUSD" in str(exc_info.value)
        assert "Timeframe: H1" in str(exc_info.value)

    def test_mt5_data_error_inheritance(self):
        """Test that MT5DataError inherits from Exception."""
        assert issubclass(MT5DataError, Exception)
