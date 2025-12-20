"""
Unit tests for Data Manager.

Tests OHLCV data retrieval, historical data, tick data, and multi-timeframe support.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

try:
    import MetaTrader5 as mt5

    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

from trading_bot.connectors.data_manager import DataManager
from trading_bot.exceptions import MT5ConnectionError, MT5DataError


@pytest.fixture
def mock_mt5_connector():
    """Create mock MT5 connector."""
    connector = Mock()
    connector.is_connected.return_value = True
    return connector


@pytest.fixture
def mock_symbol_manager():
    """Create mock symbol manager."""
    symbol_manager = Mock()
    symbol_manager.validate_symbol.return_value = True
    return symbol_manager


@pytest.fixture
def data_manager(mock_mt5_connector, mock_symbol_manager):
    """Create DataManager instance."""
    with patch("trading_bot.connectors.data_manager.MT5_AVAILABLE", True):
        with patch("trading_bot.connectors.data_manager.mt5"):
            return DataManager(mock_mt5_connector, mock_symbol_manager)


def create_mock_rates(count: int = 100):
    """Create mock OHLCV rates data."""
    base_time = int(datetime.now().timestamp())
    dtype = [
        ("time", "i"),
        ("open", "d"),
        ("high", "d"),
        ("low", "d"),
        ("close", "d"),
        ("tick_volume", "i"),
        ("spread", "i"),
        ("real_volume", "i"),
    ]
    rates = np.empty(count, dtype=dtype)
    for i in range(count):
        rates[i] = (
            base_time - (count - i) * 3600,  # time
            1.10000 + i * 0.0001,  # open
            1.10050 + i * 0.0001,  # high
            1.09950 + i * 0.0001,  # low
            1.10020 + i * 0.0001,  # close
            1000 + i * 10,  # tick_volume
            10,  # spread
            100 + i,  # real_volume
        )
    return rates


def create_mock_ticks(count: int = 100):
    """Create mock tick data."""
    base_time = int(datetime.now().timestamp())
    dtype = [
        ("time", "i"),
        ("bid", "d"),
        ("ask", "d"),
        ("last", "d"),
        ("volume", "i"),
        ("flags", "i"),
    ]
    ticks = np.empty(count, dtype=dtype)
    for i in range(count):
        ticks[i] = (
            base_time - (count - i),  # time
            1.10000 + i * 0.00001,  # bid
            1.10010 + i * 0.00001,  # ask
            1.10005 + i * 0.00001,  # last
            1,  # volume
            6,  # flags
        )
    return ticks


class TestDataManagerInitialization:
    """Test DataManager initialization."""

    def test_init_success(self, mock_mt5_connector, mock_symbol_manager):
        """Test successful initialization."""
        with patch("trading_bot.connectors.data_manager.MT5_AVAILABLE", True):
            manager = DataManager(mock_mt5_connector, mock_symbol_manager)
            assert manager.connector == mock_mt5_connector
            assert manager.symbol_manager == mock_symbol_manager

    def test_init_mt5_not_available(self, mock_mt5_connector, mock_symbol_manager):
        """Test initialization fails when MT5 not available."""
        with patch("trading_bot.connectors.data_manager.MT5_AVAILABLE", False):
            with pytest.raises(ImportError, match="MetaTrader5 package not available"):
                DataManager(mock_mt5_connector, mock_symbol_manager)


class TestOHLCVDataRetrieval:
    """Test OHLCV data retrieval."""

    def test_get_ohlcv_success(self, data_manager, mock_symbol_manager):
        """Test getting OHLCV data successfully."""
        with patch("trading_bot.connectors.data_manager.mt5") as mock_mt5:
            mock_rates = create_mock_rates(100)
            mock_mt5.copy_rates_from_pos.return_value = mock_rates

            if MT5_AVAILABLE:
                mock_mt5.TIMEFRAME_H1 = mt5.TIMEFRAME_H1
            else:
                mock_mt5.TIMEFRAME_H1 = 60

            df = data_manager.get_ohlcv("EURUSD", timeframe="H1", count=100)

            assert isinstance(df, pd.DataFrame)
            assert len(df) == 100
            assert isinstance(df.index, pd.DatetimeIndex)  # timestamp is index
            assert "open" in df.columns
            assert "high" in df.columns
            assert "low" in df.columns
            assert "close" in df.columns
            assert "volume" in df.columns
            mock_mt5.copy_rates_from_pos.assert_called_once()

    def test_get_ohlcv_different_timeframes(self, data_manager):
        """Test getting OHLCV data for different timeframes."""
        with patch("trading_bot.connectors.data_manager.mt5") as mock_mt5:
            mock_rates = create_mock_rates(50)
            mock_mt5.copy_rates_from_pos.return_value = mock_rates

            timeframes = ["M1", "M5", "M15", "H1", "H4", "D1"]
            for tf in timeframes:
                df = data_manager.get_ohlcv("EURUSD", timeframe=tf, count=50)
                assert len(df) == 50
                assert isinstance(df, pd.DataFrame)

    def test_get_ohlcv_not_connected(self, data_manager, mock_mt5_connector):
        """Test getting OHLCV fails when not connected."""
        mock_mt5_connector.is_connected.return_value = False

        with pytest.raises(MT5ConnectionError, match="MT5 not connected"):
            data_manager.get_ohlcv("EURUSD")

    def test_get_ohlcv_invalid_timeframe(self, data_manager):
        """Test getting OHLCV with invalid timeframe."""
        with pytest.raises(MT5DataError, match="Invalid timeframe"):
            data_manager.get_ohlcv("EURUSD", timeframe="INVALID")

    def test_get_ohlcv_no_data(self, data_manager):
        """Test getting OHLCV when no data available."""
        with patch("trading_bot.connectors.data_manager.mt5") as mock_mt5:
            mock_mt5.copy_rates_from_pos.return_value = None
            mock_mt5.last_error.return_value = (10001, "No data")

            with pytest.raises(MT5DataError, match="No data available"):
                data_manager.get_ohlcv("EURUSD", count=100)

    def test_get_ohlcv_empty_data(self, data_manager):
        """Test getting OHLCV when empty data returned."""
        with patch("trading_bot.connectors.data_manager.mt5") as mock_mt5:
            mock_mt5.copy_rates_from_pos.return_value = np.array([], dtype=object)
            mock_mt5.last_error.return_value = (10001, "No data")

            with pytest.raises(MT5DataError, match="No data available"):
                data_manager.get_ohlcv("EURUSD", count=100)


class TestHistoricalDataFetching:
    """Test historical data fetching."""

    def test_get_ohlcv_range_success(self, data_manager):
        """Test getting OHLCV data for date range."""
        with patch("trading_bot.connectors.data_manager.mt5") as mock_mt5:
            mock_rates = create_mock_rates(50)
            mock_mt5.copy_rates_range.return_value = mock_rates

            date_from = datetime.now() - timedelta(days=7)
            date_to = datetime.now()

            df = data_manager.get_ohlcv_range("EURUSD", "H1", date_from, date_to)

            assert isinstance(df, pd.DataFrame)
            assert len(df) == 50
            mock_mt5.copy_rates_range.assert_called_once()

    def test_get_ohlcv_range_no_data(self, data_manager):
        """Test getting OHLCV range when no data available."""
        with patch("trading_bot.connectors.data_manager.mt5") as mock_mt5:
            mock_mt5.copy_rates_range.return_value = None

            date_from = datetime.now() - timedelta(days=7)
            date_to = datetime.now()

            with pytest.raises(MT5DataError, match="No data available for date range"):
                data_manager.get_ohlcv_range("EURUSD", "H1", date_from, date_to)

    def test_get_ohlcv_range_not_connected(self, data_manager, mock_mt5_connector):
        """Test getting OHLCV range fails when not connected."""
        mock_mt5_connector.is_connected.return_value = False

        date_from = datetime.now() - timedelta(days=7)
        date_to = datetime.now()

        with pytest.raises(MT5ConnectionError, match="MT5 not connected"):
            data_manager.get_ohlcv_range("EURUSD", "H1", date_from, date_to)


class TestTickData:
    """Test tick data retrieval."""

    def test_get_last_tick_success(self, data_manager):
        """Test getting last tick successfully."""
        with patch("trading_bot.connectors.data_manager.mt5") as mock_mt5:
            mock_tick = Mock()
            mock_tick._asdict.return_value = {
                "time": int(datetime.now().timestamp()),
                "bid": 1.10000,
                "ask": 1.10010,
                "last": 1.10005,
                "volume": 1,
            }
            mock_mt5.symbol_info_tick.return_value = mock_tick

            tick = data_manager.get_last_tick("EURUSD")

            assert isinstance(tick, dict)
            assert "bid" in tick
            assert "ask" in tick
            assert tick["bid"] == 1.10000
            assert tick["ask"] == 1.10010

    def test_get_last_tick_none(self, data_manager):
        """Test getting last tick when None returned."""
        with patch("trading_bot.connectors.data_manager.mt5") as mock_mt5:
            mock_mt5.symbol_info_tick.return_value = None

            with pytest.raises(MT5DataError, match="No tick data available"):
                data_manager.get_last_tick("EURUSD")

    def test_get_ticks_success(self, data_manager):
        """Test getting tick data successfully."""
        with patch("trading_bot.connectors.data_manager.mt5") as mock_mt5:
            mock_ticks = create_mock_ticks(100)
            mock_mt5.copy_ticks_from_pos.return_value = mock_ticks

            if MT5_AVAILABLE:
                mock_mt5.COPY_TICKS_ALL = mt5.COPY_TICKS_ALL
            else:
                mock_mt5.COPY_TICKS_ALL = 0

            df = data_manager.get_ticks("EURUSD", count=100)

            assert isinstance(df, pd.DataFrame)
            assert len(df) == 100
            assert "time" in df.columns
            assert "bid" in df.columns
            assert "ask" in df.columns

    def test_get_ticks_no_data(self, data_manager):
        """Test getting ticks when no data available."""
        with patch("trading_bot.connectors.data_manager.mt5") as mock_mt5:
            mock_mt5.copy_ticks_from_pos.return_value = None

            with pytest.raises(MT5DataError, match="No tick data available"):
                data_manager.get_ticks("EURUSD", count=100)

    def test_get_ticks_not_connected(self, data_manager, mock_mt5_connector):
        """Test getting ticks fails when not connected."""
        mock_mt5_connector.is_connected.return_value = False

        with pytest.raises(MT5ConnectionError, match="MT5 not connected"):
            data_manager.get_ticks("EURUSD")


class TestMultiTimeframeSupport:
    """Test multi-timeframe support."""

    def test_timeframe_constants(self, data_manager):
        """Test timeframe constants are defined."""
        assert "M1" in data_manager.TIMEFRAMES
        assert "M5" in data_manager.TIMEFRAMES
        assert "M15" in data_manager.TIMEFRAMES
        assert "H1" in data_manager.TIMEFRAMES
        assert "H4" in data_manager.TIMEFRAMES
        assert "D1" in data_manager.TIMEFRAMES

    def test_get_ohlcv_multiple_timeframes(self, data_manager):
        """Test getting data for multiple timeframes."""
        with patch("trading_bot.connectors.data_manager.mt5") as mock_mt5:
            mock_rates = create_mock_rates(100)
            mock_mt5.copy_rates_from_pos.return_value = mock_rates

            timeframes = ["M15", "H1", "H4", "D1"]
            for tf in timeframes:
                df = data_manager.get_ohlcv("EURUSD", timeframe=tf, count=100)
                assert isinstance(df, pd.DataFrame)
                assert len(df) == 100


class TestDataValidation:
    """Test data validation."""

    def test_get_ohlcv_validates_symbol(self, data_manager, mock_symbol_manager):
        """Test that get_ohlcv validates symbol."""
        with patch("trading_bot.connectors.data_manager.mt5") as mock_mt5:
            mock_rates = create_mock_rates(100)
            mock_mt5.copy_rates_from_pos.return_value = mock_rates

            data_manager.get_ohlcv("EURUSD", count=100)

            mock_symbol_manager.validate_symbol.assert_called_once_with("EURUSD", auto_enable=True)

    def test_get_ohlcv_range_validates_symbol(self, data_manager, mock_symbol_manager):
        """Test that get_ohlcv_range validates symbol."""
        with patch("trading_bot.connectors.data_manager.mt5") as mock_mt5:
            mock_rates = create_mock_rates(50)
            mock_mt5.copy_rates_range.return_value = mock_rates

            date_from = datetime.now() - timedelta(days=7)
            date_to = datetime.now()

            data_manager.get_ohlcv_range("EURUSD", "H1", date_from, date_to)

            mock_symbol_manager.validate_symbol.assert_called_once_with("EURUSD")


class TestCurrentPrice:
    """Test current price retrieval."""

    def test_get_current_price_success(self, data_manager):
        """Test getting current bid/ask prices."""
        with patch("trading_bot.connectors.data_manager.mt5") as mock_mt5:
            mock_tick = Mock()
            mock_tick._asdict.return_value = {
                "bid": 1.10000,
                "ask": 1.10010,
            }
            mock_mt5.symbol_info_tick.return_value = mock_tick

            bid, ask = data_manager.get_current_price("EURUSD")

            assert bid == 1.10000
            assert ask == 1.10010


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_get_ohlcv_exception(self, data_manager):
        """Test exception handling in get_ohlcv."""
        with patch("trading_bot.connectors.data_manager.mt5") as mock_mt5:
            mock_mt5.copy_rates_from_pos.side_effect = Exception("Unexpected error")

            with pytest.raises(MT5DataError):
                data_manager.get_ohlcv("EURUSD", count=100)

    def test_get_ohlcv_range_exception(self, data_manager):
        """Test exception handling in get_ohlcv_range."""
        with patch("trading_bot.connectors.data_manager.mt5") as mock_mt5:
            mock_mt5.copy_rates_range.side_effect = Exception("Unexpected error")

            date_from = datetime.now() - timedelta(days=7)
            date_to = datetime.now()

            with pytest.raises(MT5DataError):
                data_manager.get_ohlcv_range("EURUSD", "H1", date_from, date_to)

    def test_get_last_tick_exception(self, data_manager):
        """Test exception handling in get_last_tick."""
        with patch("trading_bot.connectors.data_manager.mt5") as mock_mt5:
            mock_mt5.symbol_info_tick.side_effect = Exception("Unexpected error")

            with pytest.raises(MT5DataError):
                data_manager.get_last_tick("EURUSD")
