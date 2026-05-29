"""
Unit tests for Position Manager.

Tests position tracking, P&L calculations, and position management.
"""

from unittest.mock import Mock, patch

import pytest

try:
    import MetaTrader5 as mt5

    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

from trading_worker.connectors.mt5_position_query import MT5PositionQuery
from trading_worker.exceptions import MT5ConnectionError


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
    symbol_manager.get_symbol_info.return_value = {
        "point": 0.00001,
        "bid": 1.10000,
        "ask": 1.10010,
    }
    return symbol_manager


@pytest.fixture
def position_manager(mock_mt5_connector, mock_symbol_manager):
    """Create MT5PositionQuery instance."""
    with patch("trading_worker.connectors.mt5_position_query.MT5_AVAILABLE", True):
        with patch("trading_worker.connectors.mt5_position_query.mt5"):
            return MT5PositionQuery(mock_mt5_connector, mock_symbol_manager)


class TestMT5PositionQueryInitialization:
    """Test MT5PositionQuery initialization."""

    def test_init_success(self, mock_mt5_connector, mock_symbol_manager):
        """Test successful initialization."""
        with patch("trading_worker.connectors.mt5_position_query.MT5_AVAILABLE", True):
            manager = MT5PositionQuery(mock_mt5_connector, mock_symbol_manager)
            assert manager.connector == mock_mt5_connector
            assert manager.symbol_manager == mock_symbol_manager

    def test_init_mt5_not_available(self, mock_mt5_connector, mock_symbol_manager):
        """Test initialization fails when MT5 not available."""
        with patch("trading_worker.connectors.mt5_position_query.MT5_AVAILABLE", False):
            with pytest.raises(ImportError, match="MetaTrader5 package not available"):
                MT5PositionQuery(mock_mt5_connector, mock_symbol_manager)


class TestPositionDiscovery:
    """Test position discovery methods."""

    def test_get_all_positions_success(self, position_manager):
        """Test getting all positions successfully."""
        with patch("trading_worker.connectors.mt5_position_query.mt5") as mock_mt5:
            mock_pos1 = Mock()
            mock_pos1._asdict.return_value = {
                "ticket": 12345,
                "symbol": "EURUSD",
                "type": 0,  # BUY
                "volume": 0.01,
                "profit": 10.0,
            }
            mock_pos2 = Mock()
            mock_pos2._asdict.return_value = {
                "ticket": 12346,
                "symbol": "GBPUSD",
                "type": 1,  # SELL
                "volume": 0.02,
                "profit": -5.0,
            }
            mock_mt5.positions_get.return_value = [mock_pos1, mock_pos2]

            positions = position_manager.get_all_positions()

            assert len(positions) == 2
            assert positions[0]["ticket"] == 12345
            assert positions[1]["ticket"] == 12346

    def test_get_all_positions_empty(self, position_manager):
        """Test getting positions when none exist."""
        with patch("trading_worker.connectors.mt5_position_query.mt5") as mock_mt5:
            mock_mt5.positions_get.return_value = None

            positions = position_manager.get_all_positions()

            assert positions == []

    def test_get_all_positions_not_connected(self, position_manager, mock_mt5_connector):
        """Test getting positions fails when not connected."""
        mock_mt5_connector.is_connected.return_value = False

        with pytest.raises(MT5ConnectionError, match="MT5 not connected"):
            position_manager.get_all_positions()

    def test_get_all_positions_exception(self, position_manager):
        """Test exception handling in get_all_positions (line 64-66)."""
        with patch("trading_worker.connectors.mt5_position_query.mt5") as mock_mt5:
            mock_mt5.positions_get.side_effect = Exception("Unexpected error")

            positions = position_manager.get_all_positions()

            # Should return empty list on exception
            assert positions == []

    def test_get_positions_by_symbol_success(self, position_manager):
        """Test getting positions by symbol."""
        with patch("trading_worker.connectors.mt5_position_query.mt5") as mock_mt5:
            mock_pos = Mock()
            mock_pos._asdict.return_value = {
                "ticket": 12345,
                "symbol": "EURUSD",
                "type": 0,
                "volume": 0.01,
            }
            mock_mt5.positions_get.return_value = [mock_pos]

            positions = position_manager.get_positions_by_symbol("EURUSD")

            assert len(positions) == 1
            assert positions[0]["symbol"] == "EURUSD"
            mock_mt5.positions_get.assert_called_once_with(symbol="EURUSD")

    def test_get_positions_by_symbol_empty(self, position_manager):
        """Test getting positions by symbol when none exist."""
        with patch("trading_worker.connectors.mt5_position_query.mt5") as mock_mt5:
            mock_mt5.positions_get.return_value = None

            positions = position_manager.get_positions_by_symbol("EURUSD")

            assert positions == []

    def test_get_positions_by_symbol_not_connected(self, position_manager, mock_mt5_connector):
        """Test getting positions by symbol fails when not connected (line 79)."""
        mock_mt5_connector.is_connected.return_value = False

        with pytest.raises(MT5ConnectionError, match="MT5 not connected"):
            position_manager.get_positions_by_symbol("EURUSD")

    def test_get_positions_by_symbol_exception(self, position_manager):
        """Test exception handling in get_positions_by_symbol (line 87-89)."""
        with patch("trading_worker.connectors.mt5_position_query.mt5") as mock_mt5:
            mock_mt5.positions_get.side_effect = Exception("Unexpected error")

            positions = position_manager.get_positions_by_symbol("EURUSD")

            # Should return empty list on exception
            assert positions == []

    def test_get_position_by_ticket_success(self, position_manager):
        """Test getting position by ticket."""
        with patch("trading_worker.connectors.mt5_position_query.mt5") as mock_mt5:
            mock_pos = Mock()
            mock_pos._asdict.return_value = {
                "ticket": 12345,
                "symbol": "EURUSD",
                "type": 0,
                "volume": 0.01,
            }
            mock_mt5.positions_get.return_value = [mock_pos]

            position = position_manager.get_position_by_ticket(12345)

            assert position is not None
            assert position["ticket"] == 12345
            mock_mt5.positions_get.assert_called_once_with(ticket=12345)

    def test_get_position_by_ticket_not_found(self, position_manager):
        """Test getting position by ticket when not found."""
        with patch("trading_worker.connectors.mt5_position_query.mt5") as mock_mt5:
            mock_mt5.positions_get.return_value = None

            position = position_manager.get_position_by_ticket(99999)

            assert position is None

    def test_get_position_by_ticket_not_connected(self, position_manager, mock_mt5_connector):
        """Test getting position by ticket fails when not connected (line 102)."""
        mock_mt5_connector.is_connected.return_value = False

        with pytest.raises(MT5ConnectionError, match="MT5 not connected"):
            position_manager.get_position_by_ticket(12345)

    def test_get_position_by_ticket_exception(self, position_manager):
        """Test exception handling in get_position_by_ticket (line 109-111)."""
        with patch("trading_worker.connectors.mt5_position_query.mt5") as mock_mt5:
            mock_mt5.positions_get.side_effect = Exception("Unexpected error")

            position = position_manager.get_position_by_ticket(12345)

            # Should return None on exception
            assert position is None


class TestPositionCounting:
    """Test position counting methods."""

    def test_get_position_count(self, position_manager):
        """Test getting total position count."""
        with patch("trading_worker.connectors.mt5_position_query.mt5") as mock_mt5:
            mock_pos1 = Mock()
            mock_pos1._asdict.return_value = {"ticket": 12345}
            mock_pos2 = Mock()
            mock_pos2._asdict.return_value = {"ticket": 12346}
            mock_mt5.positions_get.return_value = [mock_pos1, mock_pos2]

            count = position_manager.get_position_count()

            assert count == 2

    def test_get_position_count_by_symbol(self, position_manager):
        """Test getting position count by symbol."""
        with patch("trading_worker.connectors.mt5_position_query.mt5") as mock_mt5:
            mock_pos = Mock()
            mock_pos._asdict.return_value = {"ticket": 12345, "symbol": "EURUSD"}
            mock_mt5.positions_get.return_value = [mock_pos]

            count = position_manager.get_position_count_by_symbol("EURUSD")

            assert count == 1


class TestProfitLossCalculation:
    """Test P&L calculation methods."""

    def test_calculate_position_profit_positive(self, position_manager):
        """Test calculating profit for profitable position."""
        with patch("trading_worker.connectors.mt5_position_query.mt5") as mock_mt5:
            mock_pos = Mock()
            mock_pos._asdict.return_value = {
                "ticket": 12345,
                "profit": 25.50,
            }
            mock_mt5.positions_get.return_value = [mock_pos]

            profit = position_manager.calculate_position_profit(12345)

            assert profit == 25.50

    def test_calculate_position_profit_negative(self, position_manager):
        """Test calculating profit for losing position."""
        with patch("trading_worker.connectors.mt5_position_query.mt5") as mock_mt5:
            mock_pos = Mock()
            mock_pos._asdict.return_value = {
                "ticket": 12345,
                "profit": -15.75,
            }
            mock_mt5.positions_get.return_value = [mock_pos]

            profit = position_manager.calculate_position_profit(12345)

            assert profit == -15.75

    def test_calculate_position_profit_not_found(self, position_manager):
        """Test calculating profit when position not found."""
        with patch("trading_worker.connectors.mt5_position_query.mt5") as mock_mt5:
            mock_mt5.positions_get.return_value = None

            profit = position_manager.calculate_position_profit(99999)

            assert profit == 0.0

    def test_calculate_position_pips_buy_profitable(self, position_manager, mock_symbol_manager):
        """Test calculating pips for profitable BUY position."""
        with patch("trading_worker.connectors.mt5_position_query.mt5") as mock_mt5:
            mock_pos = Mock()
            mock_pos._asdict.return_value = {
                "ticket": 12345,
                "symbol": "EURUSD",
                "type": 0,  # BUY
                "price_open": 1.10000,
                "price_current": 1.10050,  # 50 pips profit
            }
            mock_mt5.positions_get.return_value = [mock_pos]

            mock_symbol_manager.get_symbol_info.return_value = {
                "point": 0.00001,
            }

            pips = position_manager.calculate_position_pips(12345)

            assert pips == pytest.approx(50.0, abs=0.01)  # (1.10050 - 1.10000) / 0.00001

    def test_calculate_position_pips_sell_profitable(self, position_manager, mock_symbol_manager):
        """Test calculating pips for profitable SELL position."""
        with patch("trading_worker.connectors.mt5_position_query.mt5") as mock_mt5:
            mock_pos = Mock()
            mock_pos._asdict.return_value = {
                "ticket": 12346,
                "symbol": "EURUSD",
                "type": 1,  # SELL
                "price_open": 1.10050,
                "price_current": 1.10000,  # 50 pips profit
            }
            mock_mt5.positions_get.return_value = [mock_pos]

            mock_symbol_manager.get_symbol_info.return_value = {
                "point": 0.00001,
            }

            pips = position_manager.calculate_position_pips(12346)

            assert pips == pytest.approx(50.0, abs=0.01)  # (1.10050 - 1.10000) / 0.00001

    def test_calculate_position_pips_not_found(self, position_manager):
        """Test calculating pips when position not found (line 164)."""
        with patch("trading_worker.connectors.mt5_position_query.mt5") as mock_mt5:
            mock_mt5.positions_get.return_value = None

            pips = position_manager.calculate_position_pips(99999)

            assert pips == 0.0

    def test_get_total_profit(self, position_manager):
        """Test getting total profit from all positions."""
        with patch("trading_worker.connectors.mt5_position_query.mt5") as mock_mt5:
            mock_pos1 = Mock()
            mock_pos1._asdict.return_value = {"profit": 10.0}
            mock_pos2 = Mock()
            mock_pos2._asdict.return_value = {"profit": -5.0}
            mock_pos3 = Mock()
            mock_pos3._asdict.return_value = {"profit": 20.0}
            mock_mt5.positions_get.return_value = [mock_pos1, mock_pos2, mock_pos3]

            total_profit = position_manager.get_total_profit()

            assert total_profit == 25.0  # 10 - 5 + 20


class TestPositionSummary:
    """Test position summary methods."""

    def test_get_position_summary(self, position_manager):
        """Test getting position summary."""
        with patch("trading_worker.connectors.mt5_position_query.mt5") as mock_mt5:
            mock_pos1 = Mock()
            mock_pos1._asdict.return_value = {
                "ticket": 12345,
                "symbol": "EURUSD",
                "type": 0,  # BUY
                "volume": 0.01,
                "profit": 10.0,
            }
            mock_pos2 = Mock()
            mock_pos2._asdict.return_value = {
                "ticket": 12346,
                "symbol": "GBPUSD",
                "type": 1,  # SELL
                "volume": 0.02,
                "profit": -5.0,
            }
            mock_mt5.positions_get.return_value = [mock_pos1, mock_pos2]

            summary = position_manager.get_position_summary()

            assert summary["total_positions"] == 2
            assert summary["buy_positions"] == 1
            assert summary["sell_positions"] == 1
            assert summary["total_profit"] == 5.0  # 10 - 5
            assert summary["total_volume"] == 0.03  # 0.01 + 0.02
            assert "EURUSD" in summary["symbols"]
            assert "GBPUSD" in summary["symbols"]

    def test_get_position_details(self, position_manager, mock_symbol_manager):
        """Test getting detailed position information."""
        with patch("trading_worker.connectors.mt5_position_query.mt5") as mock_mt5:
            from datetime import datetime

            mock_pos = Mock()
            mock_pos._asdict.return_value = {
                "ticket": 12345,
                "symbol": "EURUSD",
                "type": 0,  # BUY
                "volume": 0.01,
                "price_open": 1.10000,
                "price_current": 1.10050,
                "sl": 1.09900,
                "tp": 1.10200,
                "profit": 10.0,
                "swap": 0.5,
                "comment": "Test trade",
                "time": int(datetime.now().timestamp()),
            }
            mock_mt5.positions_get.return_value = [mock_pos]

            mock_symbol_manager.get_symbol_info.return_value = {
                "point": 0.00001,
            }

            details = position_manager.get_position_details(12345)

            assert details["ticket"] == 12345
            assert details["symbol"] == "EURUSD"
            assert details["type"] == "BUY"
            assert details["volume"] == 0.01
            assert details["price_open"] == 1.10000
            assert details["price_current"] == 1.10050
            assert details["sl"] == 1.09900
            assert details["tp"] == 1.10200
            assert details["profit"] == 10.0
            assert "profit_pips" in details

    def test_get_position_details_not_found(self, position_manager):
        """Test getting details when position not found."""
        with patch("trading_worker.connectors.mt5_position_query.mt5") as mock_mt5:
            mock_mt5.positions_get.return_value = None

            details = position_manager.get_position_details(99999)

            assert details == {}


class TestPositionProfitability:
    """Test position profitability checks."""

    def test_is_position_profitable_true(self, position_manager):
        """Test checking profitable position."""
        with patch("trading_worker.connectors.mt5_position_query.mt5") as mock_mt5:
            mock_pos = Mock()
            mock_pos._asdict.return_value = {
                "ticket": 12345,
                "profit": 25.0,
            }
            mock_mt5.positions_get.return_value = [mock_pos]

            is_profitable = position_manager.is_position_profitable(12345, threshold=10.0)

            assert is_profitable is True

    def test_is_position_profitable_false(self, position_manager):
        """Test checking unprofitable position."""
        with patch("trading_worker.connectors.mt5_position_query.mt5") as mock_mt5:
            mock_pos = Mock()
            mock_pos._asdict.return_value = {
                "ticket": 12345,
                "profit": 5.0,
            }
            mock_mt5.positions_get.return_value = [mock_pos]

            is_profitable = position_manager.is_position_profitable(12345, threshold=10.0)

            assert is_profitable is False

    def test_is_position_profitable_zero_threshold(self, position_manager):
        """Test checking profitability with zero threshold."""
        with patch("trading_worker.connectors.mt5_position_query.mt5") as mock_mt5:
            mock_pos = Mock()
            mock_pos._asdict.return_value = {
                "ticket": 12345,
                "profit": 0.01,
            }
            mock_mt5.positions_get.return_value = [mock_pos]

            is_profitable = position_manager.is_position_profitable(12345, threshold=0.0)

            assert is_profitable is True
