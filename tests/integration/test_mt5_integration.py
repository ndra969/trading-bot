"""
Integration tests for MT5 connector and managers.

Tests complete workflows with MT5 connector, account manager, symbol manager,
data manager, order manager, and position manager.
"""

from unittest.mock import Mock, patch

import pytest

from tests.utils.mock_helpers import MockMT5
from trading_bot.connectors.account_manager import AccountManager
from trading_bot.connectors.data_manager import DataManager
from trading_bot.connectors.mt5_connector import MT5Connector
from trading_bot.connectors.order_manager import OrderManager
from trading_bot.connectors.position_manager import PositionManager
from trading_bot.connectors.symbol_manager import SymbolManager


@pytest.fixture
def mock_mt5_connector():
    """Create mock MT5 connector."""
    mock_mt5 = MockMT5()

    # Patch all MT5 modules
    patches = [
        patch("trading_bot.connectors.mt5_connector.mt5", new=mock_mt5),
        patch("trading_bot.connectors.account_manager.mt5", new=mock_mt5),
        patch("trading_bot.connectors.symbol_manager.mt5", new=mock_mt5),
        patch("trading_bot.connectors.data_manager.mt5", new=mock_mt5),
        patch("trading_bot.connectors.order_manager.mt5", new=mock_mt5),
        patch("trading_bot.connectors.position_manager.mt5", new=mock_mt5),
    ]

    for p in patches:
        p.start()

    try:
        connector = MT5Connector()
        connector.initialize()
        # Manually set as connected since is_connected() checks terminal_info
        connector._is_connected = True

        # Mock terminal_info to return connected terminal for is_connected() checks
        def mock_terminal_info_connected():
            terminal = Mock()
            terminal.connected = True
            return terminal

        mock_mt5.terminal_info = mock_terminal_info_connected

        yield connector
    finally:
        for p in patches:
            p.stop()


class TestMT5ManagerIntegration:
    """Test integration between MT5 connector and managers."""

    def test_account_manager_integration(self, mock_mt5_connector):
        """Test AccountManager integration with MT5Connector."""
        account_manager = AccountManager(mock_mt5_connector)

        # Test account info retrieval
        account_info = account_manager.get_account_info()
        assert account_info is not None
        assert "login" in account_info
        assert "balance" in account_info

        # Test balance retrieval
        balance = account_manager.get_balance()
        assert isinstance(balance, float)
        assert balance >= 0

        # Test summary
        summary = account_manager.get_summary()
        assert "balance" in summary
        assert "equity" in summary
        assert "margin" in summary

    def test_symbol_manager_integration(self, mock_mt5_connector):
        """Test SymbolManager integration with MT5Connector."""
        symbol_manager = SymbolManager(mock_mt5_connector)

        # Test symbol discovery
        symbols = symbol_manager.get_all_symbols()
        assert isinstance(symbols, list)
        assert len(symbols) > 0

        # Test symbol info retrieval
        symbol_info = symbol_manager.get_symbol_info("EURUSD")
        assert symbol_info is not None
        assert "name" in symbol_info
        assert "digits" in symbol_info

        # Test symbol validation
        result = symbol_manager.validate_symbol("EURUSD")
        assert result is True

    def test_data_manager_integration(self, mock_mt5_connector):
        """Test DataManager integration with MT5Connector and SymbolManager."""
        symbol_manager = SymbolManager(mock_mt5_connector)
        data_manager = DataManager(mock_mt5_connector, symbol_manager)

        # Test OHLCV data retrieval
        import pandas as pd

        ohlcv = data_manager.get_ohlcv("EURUSD", timeframe="H1", count=10)
        assert isinstance(ohlcv, pd.DataFrame)
        assert len(ohlcv) > 0
        assert "timestamp" in ohlcv.columns
        assert "open" in ohlcv.columns
        assert "close" in ohlcv.columns

        # Test tick data retrieval
        tick = data_manager.get_last_tick("EURUSD")
        assert tick is not None
        assert "bid" in tick
        assert "ask" in tick

    def test_order_manager_integration(self, mock_mt5_connector):
        """Test OrderManager integration with MT5Connector and SymbolManager."""
        symbol_manager = SymbolManager(mock_mt5_connector)
        order_manager = OrderManager(mock_mt5_connector, symbol_manager)

        # Test market order execution
        with patch("trading_bot.connectors.order_manager.mt5") as mock_mt5:
            # Set TRADE_RETCODE_DONE constant
            mock_mt5.TRADE_RETCODE_DONE = 10009
            mock_mt5.ORDER_TYPE_BUY = 0
            mock_mt5.ORDER_TYPE_SELL = 1
            mock_mt5.TRADE_ACTION_DEAL = 1
            mock_mt5.ORDER_TIME_GTC = 0
            mock_mt5.ORDER_FILLING_IOC = 1

            mock_result = Mock()
            mock_result.retcode = 10009  # TRADE_RETCODE_DONE
            mock_result.deal = 12345
            mock_result.order = 12345
            mock_result.volume = 0.01
            mock_result.price = 1.10000
            mock_result.comment = "Done"
            mock_result._asdict = lambda: {
                "retcode": 10009,
                "deal": 12345,
                "order": 12345,
                "volume": 0.01,
                "price": 1.10000,
                "comment": "Done",
            }

            mock_mt5.order_send.return_value = mock_result
            mock_mt5.symbol_info.return_value = Mock(
                _asdict=lambda: {
                    "name": "EURUSD",
                    "visible": True,
                    "trade_mode": 4,
                    "bid": 1.10000,
                    "ask": 1.10010,
                    "volume_min": 0.01,
                    "volume_max": 100.0,
                    "volume_step": 0.01,
                }
            )
            mock_mt5.symbol_select.return_value = True

            result = order_manager.send_market_order(symbol="EURUSD", order_type="BUY", volume=0.01)

            assert result is not None
            assert result.get("retcode") == 10009

    def test_position_manager_integration(self, mock_mt5_connector):
        """Test PositionManager integration with MT5Connector and SymbolManager."""
        symbol_manager = SymbolManager(mock_mt5_connector)
        position_manager = PositionManager(mock_mt5_connector, symbol_manager)

        # Test position retrieval
        with patch("trading_bot.connectors.position_manager.mt5") as mock_mt5:
            mock_position = Mock()
            mock_position.ticket = 12345
            mock_position.symbol = "EURUSD"
            mock_position.type = 0  # BUY
            mock_position.volume = 0.01
            mock_position.price_open = 1.10000
            mock_position.price_current = 1.10050
            mock_position.profit = 5.0
            mock_position._asdict = lambda: {
                "ticket": 12345,
                "symbol": "EURUSD",
                "type": 0,
                "volume": 0.01,
                "price_open": 1.10000,
                "price_current": 1.10050,
                "profit": 5.0,
            }

            mock_mt5.positions_get.return_value = [mock_position]

            positions = position_manager.get_all_positions()
            assert isinstance(positions, list)
            assert len(positions) > 0

            # Test position summary
            summary = position_manager.get_position_summary()
            assert "total_positions" in summary
            assert "total_profit" in summary


class TestCompleteTradingWorkflow:
    """Test complete trading workflow integration."""

    def test_complete_order_workflow(self, mock_mt5_connector):
        """Test complete order execution workflow."""
        # Initialize all managers
        account_manager = AccountManager(mock_mt5_connector)
        symbol_manager = SymbolManager(mock_mt5_connector)
        order_manager = OrderManager(mock_mt5_connector, symbol_manager)
        position_manager = PositionManager(mock_mt5_connector, symbol_manager)

        # Step 1: Check account balance
        balance = account_manager.get_balance()
        assert balance > 0

        # Step 2: Validate symbol
        symbol_manager.validate_symbol("EURUSD")

        # Step 3: Execute order
        with patch("trading_bot.connectors.order_manager.mt5") as mock_mt5:
            # Set MT5 constants
            mock_mt5.TRADE_RETCODE_DONE = 10009
            mock_mt5.ORDER_TYPE_BUY = 0
            mock_mt5.ORDER_TYPE_SELL = 1
            mock_mt5.TRADE_ACTION_DEAL = 1
            mock_mt5.ORDER_TIME_GTC = 0
            mock_mt5.ORDER_FILLING_IOC = 1

            mock_result = Mock()
            mock_result.retcode = 10009
            mock_result._asdict = lambda: {"retcode": 10009, "deal": 12345}
            mock_mt5.order_send.return_value = mock_result
            mock_mt5.symbol_info.return_value = Mock(
                _asdict=lambda: {
                    "name": "EURUSD",
                    "visible": True,
                    "trade_mode": 4,
                    "bid": 1.10000,
                    "ask": 1.10010,
                    "volume_min": 0.01,
                    "volume_max": 100.0,
                    "volume_step": 0.01,
                }
            )
            mock_mt5.symbol_select.return_value = True

            result = order_manager.send_market_order(symbol="EURUSD", order_type="BUY", volume=0.01)
            assert result is not None

        # Step 4: Check positions
        with patch("trading_bot.connectors.position_manager.mt5") as mock_mt5:
            mock_mt5.positions_get.return_value = []
            positions = position_manager.get_all_positions()
            assert isinstance(positions, list)

    def test_data_retrieval_workflow(self, mock_mt5_connector):
        """Test complete data retrieval workflow."""
        symbol_manager = SymbolManager(mock_mt5_connector)
        data_manager = DataManager(mock_mt5_connector, symbol_manager)

        # Step 1: Get available symbols
        symbols = symbol_manager.get_all_symbols()
        assert len(symbols) > 0

        # Step 2: Select symbol
        symbol = symbols[0]
        symbol_manager.select_symbol(symbol, True)

        # Step 3: Get OHLCV data
        import pandas as pd

        ohlcv = data_manager.get_ohlcv(symbol, timeframe="H1", count=100)
        assert isinstance(ohlcv, pd.DataFrame)
        assert len(ohlcv) > 0

        # Step 4: Get current price
        bid, ask = data_manager.get_current_price(symbol)
        assert isinstance(bid, float)
        assert isinstance(ask, float)
        assert ask > bid

    def test_position_monitoring_workflow(self, mock_mt5_connector):
        """Test position monitoring workflow."""
        symbol_manager = SymbolManager(mock_mt5_connector)
        position_manager = PositionManager(mock_mt5_connector, symbol_manager)
        account_manager = AccountManager(mock_mt5_connector)

        # Step 1: Get account equity
        equity = account_manager.get_equity()
        assert equity > 0

        # Step 2: Get all positions
        with patch("trading_bot.connectors.position_manager.mt5") as mock_mt5:
            mock_position = Mock()
            mock_position.ticket = 12345
            mock_position.symbol = "EURUSD"
            mock_position.type = 0
            mock_position.volume = 0.01
            mock_position.price_open = 1.10000
            mock_position.price_current = 1.10050
            mock_position.profit = 5.0
            mock_position._asdict = lambda: {
                "ticket": 12345,
                "symbol": "EURUSD",
                "type": 0,
                "volume": 0.01,
                "price_open": 1.10000,
                "price_current": 1.10050,
                "profit": 5.0,
            }

            mock_mt5.positions_get.return_value = [mock_position]
            mock_mt5.symbol_info.return_value = Mock(_asdict=lambda: {"point": 0.00001})

            positions = position_manager.get_all_positions()
            assert len(positions) > 0

            # Step 3: Calculate position profit
            total_profit = position_manager.get_total_profit()
            assert isinstance(total_profit, float)

            # Step 4: Get position summary
            summary = position_manager.get_position_summary()
            assert "total_positions" in summary
            assert "total_profit" in summary


class TestErrorHandlingIntegration:
    """Test error handling across components."""

    def test_connection_error_propagation(self):
        """Test error propagation when MT5 not connected."""
        with patch("trading_bot.connectors.mt5_connector.mt5", new=MockMT5()):
            connector = MT5Connector()
            # Don't initialize connector

            account_manager = AccountManager(connector)

            from trading_bot.exceptions import MT5ConnectionError

            with pytest.raises(MT5ConnectionError):
                account_manager.get_account_info()

    def test_symbol_error_propagation(self, mock_mt5_connector):
        """Test symbol error propagation."""
        symbol_manager = SymbolManager(mock_mt5_connector)

        # Mock symbol_info to return None for invalid symbol
        with patch("trading_bot.connectors.symbol_manager.mt5") as mock_mt5:
            mock_mt5.symbol_info.return_value = None

            from trading_bot.exceptions import MT5SymbolError

            with pytest.raises(MT5SymbolError):
                symbol_manager.get_symbol_info("INVALID_SYMBOL")

    def test_order_error_propagation(self, mock_mt5_connector):
        """Test order error propagation."""
        symbol_manager = SymbolManager(mock_mt5_connector)
        order_manager = OrderManager(mock_mt5_connector, symbol_manager)

        with patch("trading_bot.connectors.order_manager.mt5") as mock_mt5:
            mock_mt5.symbol_info.return_value = Mock(
                _asdict=lambda: {
                    "name": "EURUSD",
                    "visible": True,
                    "trade_mode": 4,
                    "bid": 1.10000,
                    "ask": 1.10010,
                    "volume_min": 0.01,
                    "volume_max": 100.0,
                    "volume_step": 0.01,
                }
            )
            mock_mt5.symbol_select.return_value = True
            mock_mt5.order_send.return_value = None
            mock_mt5.last_error.return_value = (10013, "Invalid volume")

            from trading_bot.exceptions import MT5OrderError

            with pytest.raises(MT5OrderError):
                order_manager.send_market_order(
                    symbol="EURUSD", order_type="BUY", volume=0.001  # Below minimum
                )
