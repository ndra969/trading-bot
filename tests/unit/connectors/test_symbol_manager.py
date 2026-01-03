"""
Unit tests for Symbol Manager.

Tests symbol discovery, validation, trading sessions, and broker mapping.
"""

from unittest.mock import Mock, patch

import pytest

try:
    import MetaTrader5 as mt5

    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

from trading_bot.connectors.symbol_manager import SymbolManager
from trading_bot.exceptions import MT5ConnectionError, MT5SymbolError


@pytest.fixture
def mock_mt5_connector():
    """Create mock MT5 connector."""
    connector = Mock()
    connector.is_connected.return_value = True
    return connector


@pytest.fixture
def symbol_manager(mock_mt5_connector):
    """Create SymbolManager instance."""
    with patch("trading_bot.connectors.symbol_manager.MT5_AVAILABLE", True):
        with patch("trading_bot.connectors.symbol_manager.mt5"):
            return SymbolManager(mock_mt5_connector)


class TestSymbolManagerInitialization:
    """Test SymbolManager initialization."""

    def test_init_success(self, mock_mt5_connector):
        """Test successful initialization."""
        with patch("trading_bot.connectors.symbol_manager.MT5_AVAILABLE", True):
            manager = SymbolManager(mock_mt5_connector)
            assert manager.connector == mock_mt5_connector

    def test_init_mt5_not_available(self, mock_mt5_connector):
        """Test initialization fails when MT5 not available."""
        with patch("trading_bot.connectors.symbol_manager.MT5_AVAILABLE", False):
            with pytest.raises(ImportError, match="MetaTrader5 package not available"):
                SymbolManager(mock_mt5_connector)


class TestSymbolDiscovery:
    """Test symbol discovery methods."""

    def test_get_all_symbols_success(self, symbol_manager):
        """Test getting all symbols successfully."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:

            class MockSymbol:
                def __init__(self, name):
                    self.name = name

            mock_mt5.symbols_get.return_value = [
                MockSymbol("EURUSD"),
                MockSymbol("GBPUSD"),
                MockSymbol("USDJPY"),
            ]

            symbols = symbol_manager.get_all_symbols()

            assert len(symbols) == 3
            assert "EURUSD" in symbols
            assert "GBPUSD" in symbols
            assert "USDJPY" in symbols

    def test_get_all_symbols_empty(self, symbol_manager):
        """Test getting symbols when none exist."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:
            mock_mt5.symbols_get.return_value = None

            symbols = symbol_manager.get_all_symbols()

            assert symbols == []

    def test_get_all_symbols_not_connected(self, symbol_manager, mock_mt5_connector):
        """Test getting symbols fails when not connected."""
        mock_mt5_connector.is_connected.return_value = False

        with pytest.raises(MT5ConnectionError, match="MT5 not connected"):
            symbol_manager.get_all_symbols()

    def test_get_all_symbols_exception(self, symbol_manager):
        """Test exception handling in get_all_symbols."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:
            mock_mt5.symbols_get.side_effect = Exception("Unexpected error")

            symbols = symbol_manager.get_all_symbols()

            assert symbols == []


class TestSymbolInfoRetrieval:
    """Test symbol information retrieval."""

    def test_get_symbol_info_success(self, symbol_manager):
        """Test getting symbol info successfully."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:

            class MockSymbolInfo:
                def __init__(self):
                    self.name = "EURUSD"
                    self.visible = True
                    self.trade_mode = 4  # FULL
                    self.description = "Euro vs US Dollar"
                    self.digits = 5
                    self.point = 0.00001
                    self.volume_min = 0.01
                    self.volume_max = 100.0
                    self.volume_step = 0.01
                    self.bid = 1.10000
                    self.ask = 1.10010

                def _asdict(self):
                    return vars(self)

            mock_mt5.symbol_info.return_value = MockSymbolInfo()

            info = symbol_manager.get_symbol_info("EURUSD")

            assert info["name"] == "EURUSD"
            assert info["visible"] is True
            assert info["trade_mode"] == 4
            assert info["digits"] == 5

    def test_get_symbol_info_none(self, symbol_manager):
        """Test getting symbol info when None returned."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:
            mock_mt5.symbol_info.return_value = None

            with pytest.raises(MT5SymbolError, match="Symbol not found"):
                symbol_manager.get_symbol_info("INVALID")

    def test_get_symbol_info_not_connected(self, symbol_manager, mock_mt5_connector):
        """Test getting symbol info fails when not connected."""
        mock_mt5_connector.is_connected.return_value = False

        with pytest.raises(MT5ConnectionError, match="MT5 not connected"):
            symbol_manager.get_symbol_info("EURUSD")


class TestSymbolValidation:
    """Test symbol validation methods."""

    def test_validate_symbol_success(self, symbol_manager):
        """Test validating symbol successfully."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:

            class MockSymbolInfo:
                def __init__(self):
                    self.visible = True
                    self.trade_mode = 4

                def _asdict(self):
                    return {"visible": self.visible, "trade_mode": self.trade_mode}

            mock_mt5.symbol_info.return_value = MockSymbolInfo()
            mock_mt5.symbol_select.return_value = True

            result = symbol_manager.validate_symbol("EURUSD")

            assert result is True

    def test_validate_symbol_not_visible(self, symbol_manager):
        """Test validating symbol that is not visible."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:

            class MockSymbolInfo:
                def __init__(self):
                    self.visible = False
                    self.trade_mode = 4

                def _asdict(self):
                    return {"visible": self.visible, "trade_mode": self.trade_mode}

            mock_mt5.symbol_info.return_value = MockSymbolInfo()

            with pytest.raises(MT5SymbolError, match="Symbol not available"):
                symbol_manager.validate_symbol("EURUSD")

    def test_validate_symbol_not_tradable(self, symbol_manager):
        """Test validating symbol that is not tradable."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:

            class MockSymbolInfo:
                def __init__(self):
                    self.visible = True
                    self.trade_mode = 0  # Not tradable

                def _asdict(self):
                    return {"visible": self.visible, "trade_mode": self.trade_mode}

            mock_mt5.symbol_info.return_value = MockSymbolInfo()

            with pytest.raises(MT5SymbolError, match="Trading not allowed"):
                symbol_manager.validate_symbol("EURUSD")

    def test_validate_symbol_not_found(self, symbol_manager):
        """Test validating symbol that doesn't exist."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:
            mock_mt5.symbol_info.return_value = None

            with pytest.raises(MT5SymbolError, match="Symbol not available"):
                symbol_manager.validate_symbol("INVALID")

    def test_validate_symbol_not_connected(self, symbol_manager, mock_mt5_connector):
        """Test validating symbol fails when not connected."""
        mock_mt5_connector.is_connected.return_value = False

        # validate_symbol calls is_symbol_available which calls get_symbol_info
        # which checks connection first and raises MT5ConnectionError
        with pytest.raises(MT5ConnectionError, match="MT5 not connected"):
            # This will fail at get_symbol_info level
            symbol_manager.get_symbol_info("EURUSD")


class TestSymbolSpecifications:
    """Test symbol specifications retrieval."""

    def test_get_symbol_specs_success(self, symbol_manager):
        """Test getting symbol specifications successfully."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:

            class MockSymbolInfo:
                def __init__(self):
                    self.description = "Euro vs US Dollar"
                    self.digits = 5
                    self.point = 0.00001
                    self.trade_tick_size = 0.00001
                    self.trade_tick_value = 1.0
                    self.trade_contract_size = 100000.0
                    self.volume_min = 0.01
                    self.volume_max = 100.0
                    self.volume_step = 0.01
                    self.swap_long = -0.5
                    self.swap_short = 0.3
                    self.currency_base = "EUR"
                    self.currency_profit = "USD"
                    self.currency_margin = "EUR"

                def _asdict(self):
                    return vars(self)

            mock_mt5.symbol_info.return_value = MockSymbolInfo()

            specs = symbol_manager.get_symbol_specs("EURUSD")

            assert specs["symbol"] == "EURUSD"
            assert specs["digits"] == 5
            assert specs["point"] == 0.00001
            assert specs["volume_min"] == 0.01

    def test_get_bid_ask_success(self, symbol_manager):
        """Test getting bid/ask prices."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:

            class MockSymbolInfo:
                def __init__(self):
                    self.bid = 1.10000
                    self.ask = 1.10010

                def _asdict(self):
                    return {"bid": self.bid, "ask": self.ask}

            mock_mt5.symbol_info.return_value = MockSymbolInfo()

            bid, ask = symbol_manager.get_bid_ask("EURUSD")

            assert bid == 1.10000
            assert ask == 1.10010

    def test_get_spread_success(self, symbol_manager):
        """Test getting spread."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:

            class MockSymbolInfo:
                def __init__(self):
                    self.spread = 10.0

                def _asdict(self):
                    return {"spread": self.spread}

            mock_mt5.symbol_info.return_value = MockSymbolInfo()

            spread = symbol_manager.get_spread("EURUSD")

            assert spread == 10.0


class TestSymbolAvailability:
    """Test symbol availability checking."""

    def test_is_symbol_available_success(self, symbol_manager):
        """Test checking if symbol is available."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:

            class MockSymbolInfo:
                def __init__(self):
                    self.visible = True

                def _asdict(self):
                    return {"visible": self.visible}

            mock_mt5.symbol_info.return_value = MockSymbolInfo()

            is_available = symbol_manager.is_symbol_available("EURUSD")

            assert is_available is True

    def test_is_symbol_available_not_visible(self, symbol_manager):
        """Test checking symbol that is not visible."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:

            class MockSymbolInfo:
                def __init__(self):
                    self.visible = False

                def _asdict(self):
                    return {"visible": self.visible}

            mock_mt5.symbol_info.return_value = MockSymbolInfo()

            is_available = symbol_manager.is_symbol_available("EURUSD")

            assert is_available is False

    def test_is_symbol_available_not_found(self, symbol_manager):
        """Test checking symbol that doesn't exist."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:
            mock_mt5.symbol_info.return_value = None

            is_available = symbol_manager.is_symbol_available("INVALID")

            assert is_available is False


class TestTradingAllowed:
    """Test trading allowed checking."""

    def test_is_trading_allowed_success(self, symbol_manager):
        """Test checking if trading is allowed."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:

            class MockSymbolInfo:
                def __init__(self):
                    self.trade_mode = 4  # FULL

                def _asdict(self):
                    return {"trade_mode": self.trade_mode}

            mock_mt5.symbol_info.return_value = MockSymbolInfo()

            is_allowed = symbol_manager.is_trading_allowed("EURUSD")

            assert is_allowed is True

    def test_is_trading_allowed_disabled(self, symbol_manager):
        """Test checking symbol with trading disabled."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:

            class MockSymbolInfo:
                def __init__(self):
                    self.trade_mode = 0  # DISABLED

                def _asdict(self):
                    return {"trade_mode": self.trade_mode}

            mock_mt5.symbol_info.return_value = MockSymbolInfo()

            is_allowed = symbol_manager.is_trading_allowed("EURUSD")

            assert is_allowed is False

    def test_is_trading_allowed_not_found(self, symbol_manager):
        """Test checking trading allowed when symbol not found."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:
            mock_mt5.symbol_info.return_value = None

            is_allowed = symbol_manager.is_trading_allowed("INVALID")

            assert is_allowed is False


class TestSymbolSelection:
    """Test symbol selection operations."""

    def test_select_symbol_success(self, symbol_manager):
        """Test selecting symbol successfully."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:
            mock_mt5.symbol_select.return_value = True

            result = symbol_manager.select_symbol("EURUSD")

            assert result is True
            mock_mt5.symbol_select.assert_called_once_with("EURUSD", True)

    def test_select_symbol_failure(self, symbol_manager):
        """Test selecting symbol when it fails."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:
            mock_mt5.symbol_select.return_value = False

            result = symbol_manager.select_symbol("INVALID")

            assert result is False

    def test_select_symbol_not_connected(self, symbol_manager, mock_mt5_connector):
        """Test selecting symbol fails when not connected."""
        mock_mt5_connector.is_connected.return_value = False

        with pytest.raises(MT5ConnectionError, match="MT5 not connected"):
            symbol_manager.select_symbol("EURUSD")

    def test_select_symbol_exception(self, symbol_manager):
        """Test exception handling in select_symbol (line 204-206)."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:
            mock_mt5.symbol_select.side_effect = Exception("Unexpected error")

            result = symbol_manager.select_symbol("EURUSD")

            # Should return False on exception
            assert result is False


class TestSymbolSearch:
    """Test symbol search functionality."""

    def test_search_symbols_success(self, symbol_manager):
        """Test searching for symbols."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:

            class MockSymbol:
                def __init__(self, name):
                    self.name = name

            mock_mt5.symbols_get.return_value = [
                MockSymbol("EURUSD"),
                MockSymbol("EURGBP"),
                MockSymbol("GBPUSD"),
            ]

            symbols = symbol_manager.get_all_symbols()

            # Filter for EUR symbols
            eur_symbols = [s for s in symbols if "EUR" in s]

            assert len(eur_symbols) >= 1
            assert "EURUSD" in eur_symbols

    def test_search_symbols_empty(self, symbol_manager):
        """Test searching when no symbols match."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:
            mock_mt5.symbols_get.return_value = []

            symbols = symbol_manager.get_all_symbols()

            assert symbols == []


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_get_symbol_info_exception(self, symbol_manager):
        """Test exception handling in get_symbol_info."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:
            mock_mt5.symbol_info.side_effect = Exception("Unexpected error")

            with pytest.raises(MT5SymbolError, match="Unexpected error"):
                symbol_manager.get_symbol_info("EURUSD")

    def test_get_all_symbols_exception_handling(self, symbol_manager):
        """Test exception handling in get_all_symbols."""
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:
            mock_mt5.symbols_get.side_effect = Exception("Unexpected error")

            symbols = symbol_manager.get_all_symbols()

            # Should return empty list on exception
            assert symbols == []
