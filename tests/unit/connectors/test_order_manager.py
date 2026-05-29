"""
Unit tests for Order Manager.

Tests order execution, validation, modification, and error handling.
"""

from unittest.mock import Mock, patch

import pytest

try:
    import MetaTrader5 as mt5

    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

from trading_worker.connectors.order_manager import OrderManager
from trading_worker.exceptions import MT5ConnectionError, MT5OrderError


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
    symbol_manager.get_symbol_info.return_value = {
        "volume_min": 0.01,
        "volume_max": 100.0,
        "volume_step": 0.01,
        "ask": 1.10010,
        "bid": 1.10000,
        "point": 0.00001,
    }
    return symbol_manager


@pytest.fixture
def order_manager(mock_mt5_connector, mock_symbol_manager):
    """Create OrderManager instance."""
    with patch("trading_worker.connectors.order_manager.MT5_AVAILABLE", True):
        with patch("trading_worker.connectors.order_manager.mt5"):
            return OrderManager(mock_mt5_connector, mock_symbol_manager)


class TestOrderManagerInitialization:
    """Test OrderManager initialization."""

    def test_init_success(self, mock_mt5_connector, mock_symbol_manager):
        """Test successful initialization."""
        with patch("trading_worker.connectors.order_manager.MT5_AVAILABLE", True):
            manager = OrderManager(mock_mt5_connector, mock_symbol_manager)
            assert manager.connector == mock_mt5_connector
            assert manager.symbol_manager == mock_symbol_manager

    def test_init_mt5_not_available(self, mock_mt5_connector, mock_symbol_manager):
        """Test initialization fails when MT5 not available."""
        with patch("trading_worker.connectors.order_manager.MT5_AVAILABLE", False):
            with pytest.raises(ImportError, match="MetaTrader5 package not available"):
                OrderManager(mock_mt5_connector, mock_symbol_manager)


class TestMarketOrders:
    """Test market order execution."""

    def test_send_market_buy_order_success(
        self, order_manager, mock_mt5_connector, mock_symbol_manager
    ):
        """Test successful market buy order."""
        with patch("trading_worker.connectors.order_manager.mt5") as mock_mt5:
            # Set TRADE_RETCODE_DONE constant
            if MT5_AVAILABLE:
                mock_mt5.TRADE_RETCODE_DONE = mt5.TRADE_RETCODE_DONE
            else:
                mock_mt5.TRADE_RETCODE_DONE = 10009

            # Mock successful order result
            mock_result = Mock()
            retcode = mock_mt5.TRADE_RETCODE_DONE
            mock_result._asdict.return_value = {
                "retcode": retcode,
                "deal": 12345,
                "order": 12345,
                "volume": 0.01,
                "price": 1.10010,
                "comment": "Success",
            }
            mock_mt5.order_send.return_value = mock_result

            result = order_manager.send_market_order(
                symbol="EURUSD",
                order_type="BUY",
                volume=0.01,
                sl=1.10000,
                tp=1.10100,
            )

            assert result["retcode"] == retcode
            assert result["deal"] == 12345
            mock_symbol_manager.validate_symbol.assert_called_once_with("EURUSD")
            mock_mt5.order_send.assert_called_once()

    def test_send_market_sell_order_success(
        self, order_manager, mock_mt5_connector, mock_symbol_manager
    ):
        """Test successful market sell order."""
        with patch("trading_worker.connectors.order_manager.mt5") as mock_mt5:
            if MT5_AVAILABLE:
                mock_mt5.TRADE_RETCODE_DONE = mt5.TRADE_RETCODE_DONE
            else:
                mock_mt5.TRADE_RETCODE_DONE = 10009

            mock_result = Mock()
            retcode = mock_mt5.TRADE_RETCODE_DONE
            mock_result._asdict.return_value = {
                "retcode": retcode,
                "deal": 12346,
                "order": 12346,
                "volume": 0.01,
                "price": 1.10000,
                "comment": "Success",
            }
            mock_mt5.order_send.return_value = mock_result

            result = order_manager.send_market_order(
                symbol="EURUSD",
                order_type="SELL",
                volume=0.01,
            )

            assert result["retcode"] == retcode
            assert result["deal"] == 12346

    def test_send_market_order_not_connected(self, order_manager, mock_mt5_connector):
        """Test market order fails when not connected."""
        mock_mt5_connector.is_connected.return_value = False

        with pytest.raises(MT5ConnectionError, match="MT5 not connected"):
            order_manager.send_market_order(
                symbol="EURUSD",
                order_type="BUY",
                volume=0.01,
            )

    def test_send_market_order_invalid_type(self, order_manager):
        """Test market order with invalid order type."""
        with pytest.raises(MT5OrderError, match="Invalid order type"):
            order_manager.send_market_order(
                symbol="EURUSD",
                order_type="INVALID",
                volume=0.01,
            )

    def test_send_market_order_volume_below_minimum(self, order_manager, mock_symbol_manager):
        """Test market order with volume below minimum."""
        mock_symbol_manager.get_symbol_info.return_value = {
            "volume_min": 0.01,
            "volume_max": 100.0,
            "volume_step": 0.01,
            "ask": 1.10010,
            "bid": 1.10000,
        }

        with pytest.raises(MT5OrderError, match="Volume.*below minimum"):
            order_manager.send_market_order(
                symbol="EURUSD",
                order_type="BUY",
                volume=0.005,  # Below minimum
            )

    def test_send_market_order_volume_exceeds_maximum(self, order_manager, mock_symbol_manager):
        """Test market order with volume exceeding maximum."""
        mock_symbol_manager.get_symbol_info.return_value = {
            "volume_min": 0.01,
            "volume_max": 100.0,
            "volume_step": 0.01,
            "ask": 1.10010,
            "bid": 1.10000,
        }

        with pytest.raises(MT5OrderError, match="Volume.*exceeds maximum"):
            order_manager.send_market_order(
                symbol="EURUSD",
                order_type="BUY",
                volume=200.0,  # Exceeds maximum
            )

    def test_send_market_order_rejected(self, order_manager):
        """Test market order rejection."""
        with patch("trading_worker.connectors.order_manager.mt5") as mock_mt5:
            mock_result = Mock()
            mock_result._asdict.return_value = {
                "retcode": 10004,  # Rejected
                "comment": "Insufficient funds",
            }
            mock_mt5.order_send.return_value = mock_result

            with pytest.raises(MT5OrderError, match="Order rejected"):
                order_manager.send_market_order(
                    symbol="EURUSD",
                    order_type="BUY",
                    volume=0.01,
                )

    def test_send_market_order_none_result(self, order_manager):
        """Test market order when MT5 returns None."""
        with patch("trading_worker.connectors.order_manager.mt5") as mock_mt5:
            mock_mt5.order_send.return_value = None
            mock_mt5.last_error.return_value = (10001, "Connection error")

            with pytest.raises(MT5OrderError, match="Order send failed"):
                order_manager.send_market_order(
                    symbol="EURUSD",
                    order_type="BUY",
                    volume=0.01,
                )


class TestPendingOrders:
    """Test pending order placement."""

    def test_send_buy_limit_order_success(self, order_manager):
        """Test successful buy limit order."""
        with patch("trading_worker.connectors.order_manager.mt5") as mock_mt5:
            if MT5_AVAILABLE:
                mock_mt5.TRADE_RETCODE_DONE = mt5.TRADE_RETCODE_DONE
            else:
                mock_mt5.TRADE_RETCODE_DONE = 10009

            mock_result = Mock()
            retcode = mock_mt5.TRADE_RETCODE_DONE
            mock_result._asdict.return_value = {
                "retcode": retcode,
                "order": 12347,
                "volume": 0.01,
                "price": 1.09900,
                "comment": "Success",
            }
            mock_mt5.order_send.return_value = mock_result

            result = order_manager.send_pending_order(
                symbol="EURUSD",
                order_type="BUY_LIMIT",
                volume=0.01,
                price=1.09900,
                sl=1.09800,
                tp=1.10100,
            )

            assert result["retcode"] == retcode
            assert result["order"] == 12347
            mock_mt5.order_send.assert_called_once()

    def test_send_sell_stop_order_success(self, order_manager):
        """Test successful sell stop order."""
        with patch("trading_worker.connectors.order_manager.mt5") as mock_mt5:
            if MT5_AVAILABLE:
                mock_mt5.TRADE_RETCODE_DONE = mt5.TRADE_RETCODE_DONE
            else:
                mock_mt5.TRADE_RETCODE_DONE = 10009

            mock_result = Mock()
            retcode = mock_mt5.TRADE_RETCODE_DONE
            mock_result._asdict.return_value = {
                "retcode": retcode,
                "order": 12348,
                "volume": 0.01,
                "price": 1.10100,
                "comment": "Success",
            }
            mock_mt5.order_send.return_value = mock_result

            result = order_manager.send_pending_order(
                symbol="EURUSD",
                order_type="SELL_STOP",
                volume=0.01,
                price=1.10100,
            )

            assert result["retcode"] == retcode

    def test_send_pending_order_invalid_type(self, order_manager):
        """Test pending order with invalid type."""
        with pytest.raises(MT5OrderError, match="Invalid pending order type"):
            order_manager.send_pending_order(
                symbol="EURUSD",
                order_type="INVALID",
                volume=0.01,
                price=1.10000,
            )

    def test_send_pending_order_not_connected(self, order_manager, mock_mt5_connector):
        """Test pending order fails when not connected."""
        mock_mt5_connector.is_connected.return_value = False

        with pytest.raises(MT5ConnectionError, match="MT5 not connected"):
            order_manager.send_pending_order(
                symbol="EURUSD",
                order_type="BUY_LIMIT",
                volume=0.01,
                price=1.09900,
            )


class TestOrderModification:
    """Test order/position modification."""

    def test_modify_position_success(self, order_manager):
        """Test successful position modification."""
        with patch("trading_worker.connectors.order_manager.mt5") as mock_mt5:
            if MT5_AVAILABLE:
                mock_mt5.TRADE_RETCODE_DONE = mt5.TRADE_RETCODE_DONE
            else:
                mock_mt5.TRADE_RETCODE_DONE = 10009

            # Mock position
            mock_position = Mock()
            mock_position.symbol = "EURUSD"
            mock_position.sl = 1.10000
            mock_position.tp = 1.10100
            mock_mt5.positions_get.return_value = [mock_position]

            # Mock modification result
            mock_result = Mock()
            retcode = mock_mt5.TRADE_RETCODE_DONE
            mock_result._asdict.return_value = {
                "retcode": retcode,
                "comment": "Modified",
            }
            mock_mt5.order_send.return_value = mock_result

            result = order_manager.modify_position(
                ticket=12345,
                sl=1.09950,
                tp=1.10150,
            )

            assert result["retcode"] == retcode
            mock_mt5.order_send.assert_called_once()

    def test_modify_position_not_found(self, order_manager):
        """Test modification when position not found."""
        with patch("trading_worker.connectors.order_manager.mt5") as mock_mt5:
            mock_mt5.positions_get.return_value = None

            with pytest.raises(MT5OrderError, match="Position.*not found"):
                order_manager.modify_position(ticket=99999, sl=1.09950)

    def test_modify_position_not_connected(self, order_manager, mock_mt5_connector):
        """Test modification fails when not connected."""
        mock_mt5_connector.is_connected.return_value = False

        with pytest.raises(MT5ConnectionError, match="MT5 not connected"):
            order_manager.modify_position(ticket=12345, sl=1.09950)

    def test_modify_position_none_result(self, order_manager):
        """Test modify position when MT5 returns None (line 291-292)."""
        with patch("trading_worker.connectors.order_manager.mt5") as mock_mt5:
            mock_position = Mock()
            mock_position.symbol = "EURUSD"
            mock_position.sl = 1.10000
            mock_position.tp = 1.10100
            mock_mt5.positions_get.return_value = [mock_position]

            mock_mt5.order_send.return_value = None
            mock_mt5.last_error.return_value = (10001, "Connection error")

            with pytest.raises(MT5OrderError, match="Position modification failed"):
                order_manager.modify_position(ticket=12345, sl=1.09950)

    def test_modify_position_rejected(self, order_manager):
        """Test modify position rejection (line 297-299)."""
        with patch("trading_worker.connectors.order_manager.mt5") as mock_mt5:
            if MT5_AVAILABLE:
                mock_mt5.TRADE_RETCODE_DONE = mt5.TRADE_RETCODE_DONE
            else:
                mock_mt5.TRADE_RETCODE_DONE = 10009

            mock_position = Mock()
            mock_position.symbol = "EURUSD"
            mock_position.sl = 1.10000
            mock_position.tp = 1.10100
            mock_mt5.positions_get.return_value = [mock_position]

            mock_result = Mock()
            mock_result._asdict.return_value = {
                "retcode": 10004,  # Rejected
                "comment": "Invalid SL/TP",
            }
            mock_mt5.order_send.return_value = mock_result

            with pytest.raises(MT5OrderError, match="Modification rejected"):
                order_manager.modify_position(ticket=12345, sl=1.09950)

    def test_modify_position_exception_handling(self, order_manager):
        """Test exception handling in modify_position (line 304-308)."""
        with patch("trading_worker.connectors.order_manager.mt5") as mock_mt5:
            mock_position = Mock()
            mock_position.symbol = "EURUSD"
            mock_position.sl = 1.10000
            mock_position.tp = 1.10100
            mock_mt5.positions_get.return_value = [mock_position]

            mock_mt5.order_send.side_effect = Exception("Unexpected error")

            with pytest.raises(MT5OrderError):
                order_manager.modify_position(ticket=12345, sl=1.09950)


class TestPositionClosure:
    """Test position closure."""

    def test_close_position_full_success(self, order_manager, mock_symbol_manager):
        """Test successful full position closure."""
        with patch("trading_worker.connectors.order_manager.mt5") as mock_mt5:
            if MT5_AVAILABLE:
                mock_mt5.TRADE_RETCODE_DONE = mt5.TRADE_RETCODE_DONE
                mock_mt5.POSITION_TYPE_BUY = mt5.POSITION_TYPE_BUY
            else:
                mock_mt5.TRADE_RETCODE_DONE = 10009
                mock_mt5.POSITION_TYPE_BUY = 0

            # Mock position
            mock_position = Mock()
            mock_position.symbol = "EURUSD"
            mock_position.volume = 0.01
            mock_position.type = mock_mt5.POSITION_TYPE_BUY
            mock_mt5.positions_get.return_value = [mock_position]

            # Mock close result
            mock_result = Mock()
            retcode = mock_mt5.TRADE_RETCODE_DONE
            mock_result._asdict.return_value = {
                "retcode": retcode,
                "deal": 12349,
                "comment": "Closed",
            }
            mock_mt5.order_send.return_value = mock_result

            mock_symbol_manager.get_symbol_info.return_value = {
                "bid": 1.10000,
                "ask": 1.10010,
            }

            result = order_manager.close_position(ticket=12345)

            assert result["retcode"] == retcode
            mock_mt5.order_send.assert_called_once()

    def test_close_position_partial_success(self, order_manager, mock_symbol_manager):
        """Test successful partial position closure."""
        with patch("trading_worker.connectors.order_manager.mt5") as mock_mt5:
            if MT5_AVAILABLE:
                mock_mt5.TRADE_RETCODE_DONE = mt5.TRADE_RETCODE_DONE
                mock_mt5.POSITION_TYPE_BUY = mt5.POSITION_TYPE_BUY
            else:
                mock_mt5.TRADE_RETCODE_DONE = 10009
                mock_mt5.POSITION_TYPE_BUY = 0

            mock_position = Mock()
            mock_position.symbol = "EURUSD"
            mock_position.volume = 0.10
            mock_position.type = mock_mt5.POSITION_TYPE_BUY
            mock_mt5.positions_get.return_value = [mock_position]

            mock_result = Mock()
            retcode = mock_mt5.TRADE_RETCODE_DONE
            mock_result._asdict.return_value = {
                "retcode": retcode,
                "deal": 12350,
            }
            mock_mt5.order_send.return_value = mock_result

            mock_symbol_manager.get_symbol_info.return_value = {
                "bid": 1.10000,
                "ask": 1.10010,
            }

            result = order_manager.close_position(ticket=12345, volume=0.05)

            assert result["retcode"] == retcode

    def test_close_position_sell_type(self, order_manager, mock_symbol_manager):
        """Test closing SELL position (line 347, 352)."""
        with patch("trading_worker.connectors.order_manager.mt5") as mock_mt5:
            if MT5_AVAILABLE:
                mock_mt5.TRADE_RETCODE_DONE = mt5.TRADE_RETCODE_DONE
                mock_mt5.POSITION_TYPE_SELL = mt5.POSITION_TYPE_SELL
                mock_mt5.ORDER_TYPE_BUY = mt5.ORDER_TYPE_BUY
            else:
                mock_mt5.TRADE_RETCODE_DONE = 10009
                mock_mt5.POSITION_TYPE_SELL = 1
                mock_mt5.ORDER_TYPE_BUY = 0

            # Mock SELL position
            mock_position = Mock()
            mock_position.symbol = "EURUSD"
            mock_position.volume = 0.01
            mock_position.type = mock_mt5.POSITION_TYPE_SELL
            mock_mt5.positions_get.return_value = [mock_position]

            # Mock close result
            mock_result = Mock()
            retcode = mock_mt5.TRADE_RETCODE_DONE
            mock_result._asdict.return_value = {
                "retcode": retcode,
                "deal": 12351,
                "comment": "Closed",
            }
            mock_mt5.order_send.return_value = mock_result

            # For SELL position, close_type should be ORDER_TYPE_BUY, so price should be ask
            mock_symbol_manager.get_symbol_info.return_value = {
                "bid": 1.10000,
                "ask": 1.10010,
            }

            result = order_manager.close_position(ticket=12346)

            assert result["retcode"] == retcode
            # Verify that ask price was used (for BUY close type)
            mock_symbol_manager.get_symbol_info.assert_called_once_with("EURUSD")

    def test_close_position_not_found(self, order_manager):
        """Test closure when position not found."""
        with patch("trading_worker.connectors.order_manager.mt5") as mock_mt5:
            mock_mt5.positions_get.return_value = None

            with pytest.raises(MT5OrderError, match="Position.*not found"):
                order_manager.close_position(ticket=99999)

    def test_close_position_not_connected(self, order_manager, mock_mt5_connector):
        """Test closure fails when not connected."""
        mock_mt5_connector.is_connected.return_value = False

        with pytest.raises(MT5ConnectionError, match="MT5 not connected"):
            order_manager.close_position(ticket=12345)

    def test_close_position_none_result(self, order_manager, mock_symbol_manager):
        """Test close position when MT5 returns None (line 375-377)."""
        with patch("trading_worker.connectors.order_manager.mt5") as mock_mt5:
            if MT5_AVAILABLE:
                mock_mt5.POSITION_TYPE_BUY = mt5.POSITION_TYPE_BUY
            else:
                mock_mt5.POSITION_TYPE_BUY = 0

            mock_position = Mock()
            mock_position.symbol = "EURUSD"
            mock_position.volume = 0.01
            mock_position.type = mock_mt5.POSITION_TYPE_BUY
            mock_mt5.positions_get.return_value = [mock_position]

            mock_mt5.order_send.return_value = None
            mock_mt5.last_error.return_value = (10001, "Connection error")

            mock_symbol_manager.get_symbol_info.return_value = {
                "bid": 1.10000,
                "ask": 1.10010,
            }

            with pytest.raises(MT5OrderError, match="Position close failed"):
                order_manager.close_position(ticket=12345)

    def test_close_position_rejected(self, order_manager, mock_symbol_manager):
        """Test close position rejection (line 381-384)."""
        with patch("trading_worker.connectors.order_manager.mt5") as mock_mt5:
            if MT5_AVAILABLE:
                mock_mt5.TRADE_RETCODE_DONE = mt5.TRADE_RETCODE_DONE
                mock_mt5.POSITION_TYPE_BUY = mt5.POSITION_TYPE_BUY
            else:
                mock_mt5.TRADE_RETCODE_DONE = 10009
                mock_mt5.POSITION_TYPE_BUY = 0

            mock_position = Mock()
            mock_position.symbol = "EURUSD"
            mock_position.volume = 0.01
            mock_position.type = mock_mt5.POSITION_TYPE_BUY
            mock_mt5.positions_get.return_value = [mock_position]

            mock_result = Mock()
            mock_result._asdict.return_value = {
                "retcode": 10004,  # Rejected
                "comment": "Market closed",
            }
            mock_mt5.order_send.return_value = mock_result

            mock_symbol_manager.get_symbol_info.return_value = {
                "bid": 1.10000,
                "ask": 1.10010,
            }

            with pytest.raises(MT5OrderError, match="Close rejected"):
                order_manager.close_position(ticket=12345)

    def test_close_position_exception_handling(self, order_manager, mock_symbol_manager):
        """Test exception handling in close_position (line 389-393)."""
        with patch("trading_worker.connectors.order_manager.mt5") as mock_mt5:
            if MT5_AVAILABLE:
                mock_mt5.POSITION_TYPE_BUY = mt5.POSITION_TYPE_BUY
            else:
                mock_mt5.POSITION_TYPE_BUY = 0

            mock_position = Mock()
            mock_position.symbol = "EURUSD"
            mock_position.volume = 0.01
            mock_position.type = mock_mt5.POSITION_TYPE_BUY
            mock_mt5.positions_get.return_value = [mock_position]

            mock_mt5.order_send.side_effect = Exception("Unexpected error")

            mock_symbol_manager.get_symbol_info.return_value = {
                "bid": 1.10000,
                "ask": 1.10010,
            }

            with pytest.raises(MT5OrderError):
                order_manager.close_position(ticket=12345)


class TestOrderErrorHandling:
    """Test order error handling."""

    def test_order_exception_handling(self, order_manager):
        """Test exception handling in order execution."""
        with patch("trading_worker.connectors.order_manager.mt5") as mock_mt5:
            mock_mt5.order_send.side_effect = Exception("Unexpected error")

            with pytest.raises(MT5OrderError):
                order_manager.send_market_order(
                    symbol="EURUSD",
                    order_type="BUY",
                    volume=0.01,
                )

    def test_pending_order_exception_handling(self, order_manager):
        """Test exception handling in pending order."""
        with patch("trading_worker.connectors.order_manager.mt5") as mock_mt5:
            mock_mt5.order_send.side_effect = Exception("Unexpected error")

            with pytest.raises(MT5OrderError):
                order_manager.send_pending_order(
                    symbol="EURUSD",
                    order_type="BUY_LIMIT",
                    volume=0.01,
                    price=1.09900,
                )

    def test_send_pending_order_none_result(self, order_manager):
        """Test pending order when MT5 returns None (line 228-229)."""
        with patch("trading_worker.connectors.order_manager.mt5") as mock_mt5:
            mock_mt5.order_send.return_value = None
            mock_mt5.last_error.return_value = (10001, "Connection error")

            with pytest.raises(MT5OrderError, match="Pending order failed"):
                order_manager.send_pending_order(
                    symbol="EURUSD",
                    order_type="BUY_LIMIT",
                    volume=0.01,
                    price=1.09900,
                )

    def test_send_pending_order_rejected(self, order_manager):
        """Test pending order rejection (line 234-236)."""
        with patch("trading_worker.connectors.order_manager.mt5") as mock_mt5:
            if MT5_AVAILABLE:
                mock_mt5.TRADE_RETCODE_DONE = mt5.TRADE_RETCODE_DONE
            else:
                mock_mt5.TRADE_RETCODE_DONE = 10009

            mock_result = Mock()
            mock_result._asdict.return_value = {
                "retcode": 10004,  # Rejected
                "comment": "Invalid price",
            }
            mock_mt5.order_send.return_value = mock_result

            with pytest.raises(MT5OrderError, match="Pending order rejected"):
                order_manager.send_pending_order(
                    symbol="EURUSD",
                    order_type="BUY_LIMIT",
                    volume=0.01,
                    price=1.09900,
                )
