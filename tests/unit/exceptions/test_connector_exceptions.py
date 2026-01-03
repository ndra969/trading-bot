"""
Unit tests for connector exceptions.
"""

import pytest

from trading_bot.exceptions.connector_exceptions import (
    ConnectionFailedError,
    ConnectorError,
    DataRetrievalError,
)


class TestConnectorError:
    """Test base ConnectorError exception."""

    def test_connector_error_raises(self):
        """Test that ConnectorError can be raised."""
        with pytest.raises(ConnectorError):
            raise ConnectorError("Test error")

    def test_connector_error_inheritance(self):
        """Test that ConnectorError inherits from Exception."""
        assert issubclass(ConnectorError, Exception)


class TestConnectionFailedError:
    """Test ConnectionFailedError exception."""

    def test_connection_failed_error_raises(self):
        """Test that ConnectionFailedError can be raised."""
        with pytest.raises(ConnectionFailedError) as exc_info:
            raise ConnectionFailedError("MT5", "Timeout")

        assert exc_info.value.connector == "MT5"
        assert exc_info.value.reason == "Timeout"
        assert "MT5" in str(exc_info.value)
        assert "Timeout" in str(exc_info.value)

    def test_connection_failed_error_inheritance(self):
        """Test that ConnectionFailedError inherits from ConnectorError."""
        assert issubclass(ConnectionFailedError, ConnectorError)

    def test_connection_failed_error_attributes(self):
        """Test ConnectionFailedError attributes."""
        error = ConnectionFailedError("MT5", "Network error")
        assert error.connector == "MT5"
        assert error.reason == "Network error"


class TestDataRetrievalError:
    """Test DataRetrievalError exception."""

    def test_data_retrieval_error_raises(self):
        """Test that DataRetrievalError can be raised."""
        with pytest.raises(DataRetrievalError) as exc_info:
            raise DataRetrievalError("MT5", "rates", "No data available")

        assert exc_info.value.source == "MT5"
        assert exc_info.value.data_type == "rates"
        assert exc_info.value.reason == "No data available"
        assert "MT5" in str(exc_info.value)
        assert "rates" in str(exc_info.value)
        assert "No data available" in str(exc_info.value)

    def test_data_retrieval_error_inheritance(self):
        """Test that DataRetrievalError inherits from ConnectorError."""
        assert issubclass(DataRetrievalError, ConnectorError)

    def test_data_retrieval_error_attributes(self):
        """Test DataRetrievalError attributes."""
        error = DataRetrievalError("API", "ticker", "Invalid response")
        assert error.source == "API"
        assert error.data_type == "ticker"
        assert error.reason == "Invalid response"
