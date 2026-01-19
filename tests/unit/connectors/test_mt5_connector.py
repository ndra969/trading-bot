"""
Unit tests for MT5 Connector.

Tests MT5 connection, initialization, and health checks.
"""

from unittest.mock import MagicMock, patch

import pytest

from tests.utils.mock_helpers import MockMT5
from trading_bot.connectors.mt5_connector import MT5Connector


class TestMT5Connector:
    """Test MT5Connector class."""

    @patch("trading_bot.connectors.mt5_connector.mt5", new=MockMT5())
    def test_initialization_success(self):
        """Test successful MT5 initialization."""
        connector = MT5Connector()
        result = connector.initialize()

        assert result is True
        assert connector.is_connected() is True

    @patch("trading_bot.connectors.mt5_connector.mt5", new=MockMT5())
    def test_shutdown(self):
        """Test MT5 shutdown."""
        connector = MT5Connector()
        connector.initialize()
        connector.shutdown()

        assert connector.is_connected() is False

    @patch("trading_bot.connectors.mt5_connector.mt5", new=MockMT5())
    def test_health_check(self):
        """Test health check."""
        connector = MT5Connector()
        connector.initialize()

        health = connector.health_check()

        assert "connected" in health
        assert "terminal_running" in health
        assert "trade_allowed" in health

    @patch("trading_bot.connectors.mt5_connector.mt5", new=MockMT5())
    def test_context_manager(self):
        """Test context manager usage."""
        with MT5Connector() as connector:
            assert connector.is_connected() is True

        # After exiting context, should be disconnected
        # Note: In real implementation, check connection state

    @patch("trading_bot.connectors.mt5_connector.mt5", new=MockMT5())
    def test_terminal_info(self):
        """Test getting terminal info."""
        connector = MT5Connector()
        connector.initialize()

        info = connector.terminal_info

        assert isinstance(info, dict)
        assert "connected" in info

    @patch("trading_bot.connectors.mt5_connector.mt5", new=MockMT5())
    def test_account_info(self):
        """Test getting account info."""
        connector = MT5Connector()
        connector.initialize()

        info = connector.account_info

        assert isinstance(info, dict)
        assert "login" in info

    @patch("trading_bot.connectors.mt5_connector.mt5", new=MockMT5())
    def test_version(self):
        """Test getting MT5 version."""
        connector = MT5Connector()
        connector.initialize()

        version = connector.version

        assert version is not None
        assert isinstance(version, tuple)


class TestMT5ConnectorAdvanced:
    """Test advanced MT5 connector scenarios."""

    @patch("trading_bot.connectors.mt5_connector.mt5")
    @patch("trading_bot.connectors.mt5_connector.time.sleep")
    def test_connection_retry_mechanism(self, mock_sleep, mock_mt5):
        """Test connection retry on failure."""
        connector = MT5Connector(retry_attempts=2, retry_delay=0.1)

        attempt_count = [0]

        def mock_initialize(**kwargs):
            attempt_count[0] += 1
            if attempt_count[0] < 2:
                # Raise generic exception to trigger retry
                raise Exception("Temporary connection error")
            return True

        mock_mt5.initialize.side_effect = mock_initialize

        class MockTerminalInfo:
            def __init__(self):
                self.connected = True

            def _asdict(self):
                return {"connected": True}

        mock_mt5.terminal_info.return_value = MockTerminalInfo()
        mock_mt5.version.return_value = (5, 0, 0, 3000, "2024.01.01")
        mock_mt5.account_info.return_value = None

        # First attempt fails, but retry should succeed
        result = connector.initialize()

        assert result is True
        assert attempt_count[0] == 2  # Should retry once
        assert mock_sleep.call_count >= 1  # Should have slept between retries

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_terminal_not_running_error(self, mock_mt5):
        """Test terminal not running error."""
        connector = MT5Connector()

        mock_mt5.initialize.return_value = True

        class MockTerminalInfo:
            def __init__(self):
                self.connected = False

            def _asdict(self):
                return {"connected": False}

        mock_mt5.terminal_info.return_value = MockTerminalInfo()
        mock_mt5.shutdown = MagicMock()

        from trading_bot.exceptions import MT5TerminalNotRunningError

        with pytest.raises(MT5TerminalNotRunningError):
            connector.initialize()

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_version_incompatible_error(self, mock_mt5):
        """Test version incompatible error."""
        connector = MT5Connector()

        mock_mt5.initialize.return_value = True

        class MockTerminalInfo:
            def __init__(self):
                self.connected = True

            def _asdict(self):
                return {"connected": True}

        mock_mt5.terminal_info.return_value = MockTerminalInfo()
        mock_mt5.version.return_value = (4, 0, 0, 2000, "2020.01.01")  # Old version
        mock_mt5.shutdown = MagicMock()

        from trading_bot.exceptions import MT5VersionIncompatibleError

        with pytest.raises(MT5VersionIncompatibleError):
            connector.initialize()

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_login_failure(self, mock_mt5):
        """Test login failure handling."""
        connector = MT5Connector(login=12345, password="wrong", server="TestServer")

        mock_mt5.initialize.return_value = True

        class MockTerminalInfo:
            def __init__(self):
                self.connected = True

            def _asdict(self):
                return {"connected": True}

        mock_mt5.terminal_info.return_value = MockTerminalInfo()
        mock_mt5.version.return_value = (5, 0, 0, 3000, "2024.01.01")
        mock_mt5.login.return_value = False
        mock_mt5.last_error.return_value = (10004, "Invalid credentials")
        mock_mt5.shutdown = MagicMock()

        from trading_bot.exceptions import MT5ConnectionError

        with pytest.raises(MT5ConnectionError, match="MT5 login failed"):
            connector.initialize()

    @patch("trading_bot.connectors.mt5_connector.mt5")
    @patch("trading_bot.connectors.mt5_connector.time.sleep")
    def test_multiple_connection_attempts(self, mock_sleep, mock_mt5):
        """Test multiple connection attempts with delays."""
        connector = MT5Connector(retry_attempts=2, retry_delay=0.1)

        attempt_count = [0]

        def failing_initialize(**kwargs):
            attempt_count[0] += 1
            if attempt_count[0] < 2:
                # Raise generic exception to trigger retry
                raise Exception("Temporary connection error")
            return True

        mock_mt5.initialize.side_effect = failing_initialize

        class MockTerminalInfo:
            def __init__(self):
                self.connected = True

            def _asdict(self):
                return {"connected": True}

        mock_mt5.terminal_info.return_value = MockTerminalInfo()
        mock_mt5.version.return_value = (5, 0, 0, 3000, "2024.01.01")
        mock_mt5.account_info.return_value = None

        result = connector.initialize()

        # Should eventually succeed after retries
        assert result is True
        assert attempt_count[0] == 2
        assert mock_sleep.call_count >= 1  # Should have slept between retries

    @patch("trading_bot.connectors.mt5_connector.mt5")
    @patch("trading_bot.connectors.mt5_connector.time.sleep")
    def test_connection_timeout_handling(self, mock_sleep, mock_mt5):
        """Test connection timeout handling."""
        connector = MT5Connector(timeout=5, retry_attempts=1)

        mock_mt5.initialize.return_value = False
        mock_mt5.last_error.return_value = (10001, "Connection timeout")

        from trading_bot.exceptions import MT5ConnectionError

        with pytest.raises(MT5ConnectionError, match="MT5 initialization failed"):
            connector.initialize()

    @patch("trading_bot.connectors.mt5_connector.mt5", new=MockMT5())
    def test_health_check_when_disconnected(self):
        """Test health check when disconnected."""
        connector = MT5Connector()

        health = connector.health_check()

        assert health["connected"] is False
        assert health["terminal_running"] is False
        assert health["trade_allowed"] is False

    @patch("trading_bot.connectors.mt5_connector.mt5", new=MockMT5())
    def test_is_connected_checks_terminal(self):
        """Test is_connected checks terminal responsiveness."""
        connector = MT5Connector()
        connector._is_connected = True  # Simulate connected state

        mock_mt5 = MockMT5()
        mock_mt5.is_initialized = True

        class MockTerminalInfo:
            def __init__(self):
                self.connected = True

        mock_mt5.terminal_info = lambda: MockTerminalInfo()

        with patch("trading_bot.connectors.mt5_connector.mt5", new=mock_mt5):
            is_connected = connector.is_connected()

            assert is_connected is True

    @patch("trading_bot.connectors.mt5_connector.mt5", new=MockMT5())
    def test_is_connected_handles_exception(self):
        """Test is_connected handles exceptions gracefully."""
        connector = MT5Connector()
        connector._is_connected = True

        mock_mt5 = MockMT5()
        mock_mt5.terminal_info = lambda: (_ for _ in ()).throw(Exception("Terminal error"))

        with patch("trading_bot.connectors.mt5_connector.mt5", new=mock_mt5):
            is_connected = connector.is_connected()

            assert is_connected is False

    @patch("trading_bot.connectors.mt5_connector.mt5", new=MockMT5())
    def test_health_check_exception_handling(self):
        """Test health check handles exceptions."""
        connector = MT5Connector()
        connector._is_connected = True

        mock_mt5 = MockMT5()
        mock_mt5.terminal_info = lambda: (_ for _ in ()).throw(Exception("Health check error"))
        mock_mt5.account_info = lambda: None

        with patch("trading_bot.connectors.mt5_connector.mt5", new=mock_mt5):
            health = connector.health_check()

            # Should return health dict even on error
            assert isinstance(health, dict)
            assert "connected" in health

    @patch("trading_bot.connectors.mt5_connector.mt5", new=MockMT5())
    def test_initialization_with_terminal_path(self):
        """Test initialization with custom terminal path."""
        connector = MT5Connector(terminal_path="C:/Program Files/MetaTrader 5/terminal64.exe")

        mock_mt5 = MockMT5()
        mock_mt5.is_initialized = True

        class MockTerminalInfo:
            def __init__(self):
                self.connected = True
                self.name = "MetaTrader 5"

            def _asdict(self):
                return {"connected": True, "name": "MetaTrader 5"}

        mock_mt5.terminal_info = lambda: MockTerminalInfo()
        mock_mt5.version = lambda: (5, 0, 0, 3000, "2024.01.01")
        mock_mt5.account_info = lambda: None

        with patch("trading_bot.connectors.mt5_connector.mt5", new=mock_mt5):
            result = connector.initialize()

            assert result is True
            # Verify initialize was called with path
            assert connector.terminal_path is not None

    @patch("trading_bot.connectors.mt5_connector.mt5", new=MockMT5())
    def test_initialization_with_login_credentials(self):
        """Test initialization with login credentials."""
        connector = MT5Connector(
            login=12345, password="testpass", server="TestServer-Demo", timeout=30
        )

        mock_mt5 = MockMT5()
        mock_mt5.is_initialized = True
        mock_mt5.is_logged_in = True

        class MockTerminalInfo:
            def __init__(self):
                self.connected = True

            def _asdict(self):
                return {"connected": True}

        class MockAccountInfo:
            def __init__(self):
                self.login = 12345

            def _asdict(self):
                return {"login": 12345}

        mock_mt5.terminal_info = lambda: MockTerminalInfo()
        mock_mt5.version = lambda: (5, 0, 0, 3000, "2024.01.01")
        mock_mt5.login = lambda **kwargs: True
        mock_mt5.account_info = lambda: MockAccountInfo()

        with patch("trading_bot.connectors.mt5_connector.mt5", new=mock_mt5):
            result = connector.initialize()

            assert result is True
            assert connector.account_info.get("login") == 12345

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_modify_position_success(self, mock_mt5):
        """Test successful position modification."""
        connector = MT5Connector()
        connector._is_connected = True

        # Mock position
        class MockPosition:
            def __init__(self):
                self.ticket = 12345
                self.symbol = "EURUSD"
                self.sl = 1.0950
                self.tp = 1.1100
                self.price_open = 1.1000

        mock_mt5.positions_get.return_value = [MockPosition()]

        # Mock symbol info for tolerance calculation
        class MockSymbolInfo:
            def __init__(self):
                self.point = 0.00001  # 5-digit forex

        mock_mt5.symbol_info.return_value = MockSymbolInfo()

        # Mock successful order_send
        # Set TRADE_RETCODE_DONE constant on mock
        mock_mt5.TRADE_RETCODE_DONE = 10009

        class MockOrderResult:
            def __init__(self):
                self.retcode = mock_mt5.TRADE_RETCODE_DONE
                self.comment = "Success"

        mock_mt5.order_send.return_value = MockOrderResult()

        result = connector.modify_position(ticket=12345, sl=1.0960, tp=1.1100)

        assert result["success"] is True
        assert result["modified"] is True
        assert result["sl_changed"] is True
        assert result["tp_changed"] is False
        assert "Successfully modified" in result["message"]
        assert mock_mt5.order_send.called

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_modify_position_no_changes_needed(self, mock_mt5):
        """Test modify_position when no changes are needed."""
        connector = MT5Connector()
        connector._is_connected = True

        # Mock position with SL already at target
        class MockPosition:
            def __init__(self):
                self.ticket = 12345
                self.symbol = "EURUSD"
                self.sl = 1.0960  # Already at target
                self.tp = 1.1100
                self.price_open = 1.1000

        mock_mt5.positions_get.return_value = [MockPosition()]

        # Mock symbol info for tolerance calculation
        class MockSymbolInfo:
            def __init__(self):
                self.point = 0.00001  # 5-digit forex

        mock_mt5.symbol_info.return_value = MockSymbolInfo()

        # Try to modify to same value
        result = connector.modify_position(ticket=12345, sl=1.0960, tp=1.1100)

        assert result["success"] is True
        assert result["modified"] is False  # No actual modification
        assert result["sl_changed"] is False
        assert result["tp_changed"] is False
        assert "No changes needed" in result["message"]
        # Should not call order_send
        assert not mock_mt5.order_send.called

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_modify_position_not_connected(self, mock_mt5):
        """Test modify_position when not connected."""
        connector = MT5Connector()
        connector._is_connected = False

        result = connector.modify_position(ticket=12345, sl=1.0960)

        assert result["success"] is False
        assert result["modified"] is False
        assert "MT5 not connected" in result["message"]

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_modify_position_not_found(self, mock_mt5):
        """Test modify_position when position not found."""
        connector = MT5Connector()
        connector._is_connected = True

        mock_mt5.positions_get.return_value = None

        result = connector.modify_position(ticket=99999, sl=1.0960)

        assert result["success"] is False
        assert result["modified"] is False
        assert "not found" in result["message"]

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_modify_position_mt5_error(self, mock_mt5):
        """Test modify_position when MT5 returns error."""
        connector = MT5Connector()
        connector._is_connected = True

        # Mock position
        class MockPosition:
            def __init__(self):
                self.ticket = 12345
                self.symbol = "EURUSD"
                self.sl = 1.0950
                self.tp = 1.1100
                self.price_open = 1.1000

        mock_mt5.positions_get.return_value = [MockPosition()]

        # Mock symbol info
        class MockSymbolInfo:
            def __init__(self):
                self.point = 0.00001

        mock_mt5.symbol_info.return_value = MockSymbolInfo()

        # Mock error response
        class MockOrderResult:
            def __init__(self):
                self.retcode = 10004  # Error code
                self.comment = "Invalid request"

        mock_mt5.order_send.return_value = MockOrderResult()

        result = connector.modify_position(ticket=12345, sl=1.0960)

        assert result["success"] is False
        assert result["modified"] is False
        assert "error" in result["message"].lower() or "rejected" in result["message"].lower()

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_place_order_success(self, mock_mt5):
        """Test successful order placement."""
        connector = MT5Connector()
        connector._is_connected = True

        # Mock symbol info
        class MockSymbolInfo:
            def __init__(self):
                self.filling_mode = 1  # FOK supported

        mock_mt5.symbol_info.return_value = MockSymbolInfo()
        mock_mt5.TRADE_RETCODE_DONE = 10009
        mock_mt5.ORDER_FILLING_FOK = 1
        mock_mt5.ORDER_FILLING_IOC = 2
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TYPE_BUY = 0
        mock_mt5.ORDER_TIME_GTC = 0

        # Mock successful order result
        class MockOrderResult:
            def __init__(self):
                self.order = 12345
                self.retcode = 10009
                self.price = 1.10000
                self.volume = 0.01
                self.comment = "Success"

            def _asdict(self):
                return {
                    "order": self.order,
                    "retcode": self.retcode,
                    "price": self.price,
                    "volume": self.volume,
                    "comment": self.comment,
                }

        mock_mt5.order_send.return_value = MockOrderResult()

        result = connector.place_order(
            symbol="EURUSD",
            order_type="BUY",
            volume=0.01,
            price=1.10000,
            sl=1.09500,
            tp=1.11000,
        )

        assert result["success"] is True
        assert result["order"] == 12345
        assert result["price"] == 1.10000
        assert result["volume"] == 0.01

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_place_order_not_connected(self, mock_mt5):
        """Test place_order when not connected."""
        connector = MT5Connector()
        connector._is_connected = False

        result = connector.place_order(
            symbol="EURUSD",
            order_type="BUY",
            volume=0.01,
            price=1.10000,
            sl=1.09500,
            tp=1.11000,
        )

        assert result["success"] is False
        assert result["error"] == "MT5 not connected"
        assert result["error_code"] == 0
        assert "MT5 connection not established" in result["error_description"]

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_place_order_symbol_not_found(self, mock_mt5):
        """Test place_order when symbol not found."""
        connector = MT5Connector()
        connector._is_connected = True

        mock_mt5.symbol_info.return_value = None

        result = connector.place_order(
            symbol="INVALID",
            order_type="BUY",
            volume=0.01,
            price=1.10000,
            sl=1.09500,
            tp=1.11000,
        )

        assert result["success"] is False
        assert "not found" in result["error"]
        assert result["error_code"] == 0
        assert "Symbol not found in MT5" in result["error_description"]

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_place_order_none_result(self, mock_mt5):
        """Test place_order when MT5 returns None."""
        connector = MT5Connector()
        connector._is_connected = True

        # Mock symbol info
        class MockSymbolInfo:
            def __init__(self):
                self.filling_mode = 1

        mock_mt5.symbol_info.return_value = MockSymbolInfo()
        mock_mt5.ORDER_FILLING_FOK = 1
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TYPE_BUY = 0
        mock_mt5.ORDER_TIME_GTC = 0
        mock_mt5.order_send.return_value = None
        mock_mt5.last_error.return_value = (10004, "Requote")

        result = connector.place_order(
            symbol="EURUSD",
            order_type="BUY",
            volume=0.01,
            price=1.10000,
            sl=1.09500,
            tp=1.11000,
        )

        assert result["success"] is False
        assert result["error_code"] == 10004
        assert "Requote" in result["error_description"]

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_place_order_retcode_error(self, mock_mt5):
        """Test place_order when MT5 returns error retcode."""
        connector = MT5Connector()
        connector._is_connected = True

        # Mock symbol info
        class MockSymbolInfo:
            def __init__(self):
                self.filling_mode = 1

        mock_mt5.symbol_info.return_value = MockSymbolInfo()
        mock_mt5.ORDER_FILLING_FOK = 1
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TYPE_BUY = 0
        mock_mt5.ORDER_TIME_GTC = 0
        mock_mt5.TRADE_RETCODE_DONE = 10009

        # Mock error result
        class MockOrderResult:
            def __init__(self):
                self.retcode = 10019  # Not enough money
                self.comment = "Not enough money"

        mock_mt5.order_send.return_value = MockOrderResult()

        result = connector.place_order(
            symbol="EURUSD",
            order_type="BUY",
            volume=0.01,
            price=1.10000,
            sl=1.09500,
            tp=1.11000,
        )

        assert result["success"] is False
        assert result["error_code"] == 10019
        assert "not enough money" in result["error_description"].lower()

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_place_order_exception(self, mock_mt5):
        """Test place_order when exception occurs."""
        connector = MT5Connector()
        connector._is_connected = True

        # Mock symbol info
        class MockSymbolInfo:
            def __init__(self):
                self.filling_mode = 1

        mock_mt5.symbol_info.return_value = MockSymbolInfo()
        mock_mt5.ORDER_FILLING_FOK = 1
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TYPE_BUY = 0
        mock_mt5.ORDER_TIME_GTC = 0
        mock_mt5.order_send.side_effect = Exception("Unexpected error")

        result = connector.place_order(
            symbol="EURUSD",
            order_type="BUY",
            volume=0.01,
            price=1.10000,
            sl=1.09500,
            tp=1.11000,
        )

        assert result["success"] is False
        assert result["error_code"] == 10000
        assert "Unexpected error" in result["error"]
        assert "Exception occurred during order placement" in result["error_description"]

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_get_error_description(self, mock_mt5):
        """Test _get_error_description helper method."""
        connector = MT5Connector()

        # Test known error codes
        assert connector._get_error_description(10004) == "Requote"
        assert (
            connector._get_error_description(10019)
            == "There is not enough money to complete the request"
        )
        assert connector._get_error_description(10018) == "Market is closed"
        assert connector._get_error_description(10013) == "Invalid request"

        # Test unknown error code
        assert "Unknown error code: 99999" in connector._get_error_description(99999)


class TestMT5ConnectorMissingCoverage:
    """Tests for missing coverage lines in MT5Connector."""

    @patch("trading_bot.connectors.mt5_connector.MT5_AVAILABLE", False)
    def test_import_error_when_mt5_not_available(self):
        """Test ImportError when MetaTrader5 package not available."""
        with pytest.raises(ImportError, match="MetaTrader5 package not available"):
            MT5Connector()

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_initialize_with_terminal_path(self, mock_mt5):
        """Test initialize with custom terminal_path."""
        connector = MT5Connector(terminal_path="C:/Custom/Path/terminal64.exe")

        mock_mt5.initialize.return_value = True

        class MockTerminalInfo:
            def __init__(self):
                self.connected = True

            def _asdict(self):
                return {"connected": True, "name": "MetaTrader 5"}

        mock_mt5.terminal_info.return_value = MockTerminalInfo()
        mock_mt5.version.return_value = (5, 0, 0, 3000, "2024.01.01")
        mock_mt5.account_info.return_value = None

        result = connector.initialize()

        assert result is True
        # Verify initialize was called with path parameter
        mock_mt5.initialize.assert_called_once()

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_initialize_without_terminal_path(self, mock_mt5):
        """Test initialize without terminal_path (default)."""
        connector = MT5Connector()

        mock_mt5.initialize.return_value = True

        class MockTerminalInfo:
            def __init__(self):
                self.connected = True

            def _asdict(self):
                return {"connected": True, "name": "MetaTrader 5"}

        mock_mt5.terminal_info.return_value = MockTerminalInfo()
        mock_mt5.version.return_value = (5, 0, 0, 3000, "2024.01.01")
        mock_mt5.account_info.return_value = None

        result = connector.initialize()

        assert result is True

    @patch("trading_bot.connectors.mt5_connector.mt5")
    @patch("trading_bot.connectors.mt5_connector.time.sleep")
    def test_initialize_all_attempts_failed(self, mock_sleep, mock_mt5):
        """Test initialize when all retry attempts fail."""
        connector = MT5Connector(retry_attempts=2, retry_delay=0.1)

        mock_mt5.initialize.side_effect = Exception("Connection failed")

        from trading_bot.exceptions import MT5ConnectionError

        with pytest.raises(MT5ConnectionError, match="Failed to connect after 2 attempts"):
            connector.initialize()

        # Verify sleep was called between retries
        assert mock_sleep.call_count == 1

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_initialize_returns_false_after_retries(self, mock_mt5):
        """Test initialize returns False when retry loop completes without success."""
        # This test is designed to hit the 'return False' statement at line 182
        # However, in reality, the code raises an exception before reaching that line
        # The line 182 is actually unreachable code in the current implementation
        connector = MT5Connector(retry_attempts=1, retry_delay=0.1)

        # Make initialize succeed but something else fail
        mock_mt5.initialize.return_value = True

        class MockTerminalInfo:
            def __init__(self):
                self.connected = False

            def _asdict(self):
                return {"connected": False}

        mock_mt5.terminal_info.return_value = MockTerminalInfo()
        mock_mt5.shutdown = MagicMock()

        from trading_bot.exceptions import MT5TerminalNotRunningError

        # Should raise MT5TerminalNotRunningError, not return False
        with pytest.raises(MT5TerminalNotRunningError):
            connector.initialize()

    @patch("trading_bot.connectors.mt5_connector.mt5")
    @patch("trading_bot.connectors.mt5_connector.time.sleep")
    def test_initialize_specific_exception_then_retry(self, mock_sleep, mock_mt5):
        """Test initialize with specific MT5 exceptions that should not retry."""
        connector = MT5Connector(retry_attempts=3)

        # First attempt raises MT5 error
        mock_mt5.initialize.return_value = True

        class MockTerminalInfo:
            def __init__(self):
                self.connected = False

            def _asdict(self):
                return {"connected": False}

        mock_mt5.terminal_info.return_value = MockTerminalInfo()
        mock_mt5.shutdown = MagicMock()

        from trading_bot.exceptions import MT5TerminalNotRunningError

        # Should raise without retrying
        with pytest.raises(MT5TerminalNotRunningError):
            connector.initialize()

        # Should not have called sleep (no retry for specific exceptions)
        assert mock_sleep.call_count == 0

    def test_is_connected_when_not_connected(self):
        """Test is_connected returns False when _is_connected is False."""
        connector = MT5Connector()
        connector._is_connected = False

        result = connector.is_connected()

        assert result is False

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_is_connected_terminal_info_none(self, mock_mt5):
        """Test is_connected when terminal_info returns None."""
        connector = MT5Connector()
        connector._is_connected = True

        mock_mt5.terminal_info.return_value = None

        result = connector.is_connected()

        assert result is False

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_is_connected_terminal_disconnected(self, mock_mt5):
        """Test is_connected when terminal is disconnected."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockTerminalInfo:
            def __init__(self):
                self.connected = False
                self.trade_allowed = False

        mock_mt5.terminal_info.return_value = MockTerminalInfo()

        result = connector.is_connected()

        assert result is False

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_is_connected_server_mismatch(self, mock_mt5):
        """Test is_connected detects server mismatch."""
        connector = MT5Connector(server="ExpectedServer")
        connector._is_connected = True

        class MockTerminalInfo:
            def __init__(self):
                self.connected = True
                self.trade_allowed = True

        mock_mt5.terminal_info.return_value = MockTerminalInfo()

        class MockAccountInfo:
            def __init__(self):
                self.server = "DifferentServer"

        mock_mt5.account_info.return_value = MockAccountInfo()

        result = connector.is_connected()

        assert result is False
        assert connector._is_connected is False

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_is_connected_no_server_configured(self, mock_mt5):
        """Test is_connected when no server is configured (no server check)."""
        connector = MT5Connector(server=None)
        connector._is_connected = True

        class MockTerminalInfo:
            def __init__(self):
                self.connected = True
                self.trade_allowed = True

        mock_mt5.terminal_info.return_value = MockTerminalInfo()
        mock_mt5.account_info.return_value = None

        result = connector.is_connected()

        assert result is True

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_is_connected_exception_handling(self, mock_mt5):
        """Test is_connected handles exceptions gracefully."""
        connector = MT5Connector()
        connector._is_connected = True

        mock_mt5.terminal_info.side_effect = Exception("Terminal error")

        result = connector.is_connected()

        assert result is False

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_health_check_disconnected(self, mock_mt5):
        """Test health_check when not connected."""
        connector = MT5Connector()
        connector._is_connected = False

        health = connector.health_check()

        assert health["connected"] is False
        assert health["terminal_running"] is False
        assert health["trade_allowed"] is False
        assert health["server_match"] is True
        assert health["expected_server"] is None
        assert health["current_server"] is None
        assert health["terminal_info"] == {}
        assert health["account_info"] == {}

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_health_check_with_server_mismatch(self, mock_mt5):
        """Test health_check detects server mismatch."""
        connector = MT5Connector(server="ExpectedServer")
        connector._is_connected = True

        class MockTerminalInfo:
            def __init__(self):
                self.connected = True
                self.trade_allowed = True

            def _asdict(self):
                return {"connected": True, "trade_allowed": True}

        mock_mt5.terminal_info.return_value = MockTerminalInfo()

        class MockAccountInfo:
            def __init__(self):
                self.server = "DifferentServer"

            def _asdict(self):
                return {"server": "DifferentServer"}

        mock_mt5.account_info.return_value = MockAccountInfo()

        health = connector.health_check()

        assert health["connected"] is True
        assert health["terminal_running"] is True
        assert health["trade_allowed"] is True
        assert health["server_match"] is False
        assert health["expected_server"] == "ExpectedServer"
        assert health["current_server"] == "DifferentServer"

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_health_check_server_match(self, mock_mt5):
        """Test health_check when servers match."""
        connector = MT5Connector(server="ExpectedServer")
        connector._is_connected = True

        class MockTerminalInfo:
            def __init__(self):
                self.connected = True
                self.trade_allowed = True

            def _asdict(self):
                return {"connected": True, "trade_allowed": True}

        mock_mt5.terminal_info.return_value = MockTerminalInfo()

        class MockAccountInfo:
            def __init__(self):
                self.server = "ExpectedServer"

            def _asdict(self):
                return {"server": "ExpectedServer"}

        mock_mt5.account_info.return_value = MockAccountInfo()

        health = connector.health_check()

        assert health["server_match"] is True

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_health_check_no_account_server_attribute(self, mock_mt5):
        """Test health_check when account_info has no server attribute."""
        connector = MT5Connector(server="ExpectedServer")
        connector._is_connected = True

        class MockTerminalInfo:
            def __init__(self):
                self.connected = True
                self.trade_allowed = True

            def _asdict(self):
                return {"connected": True, "trade_allowed": True}

        mock_mt5.terminal_info.return_value = MockTerminalInfo()

        class MockAccountInfo:
            def __init__(self):
                pass

            def _asdict(self):
                return {}

        mock_mt5.account_info.return_value = MockAccountInfo()

        health = connector.health_check()

        assert health["current_server"] is None
        assert health["server_match"] is True  # No mismatch detected

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_health_check_exception_handling(self, mock_mt5):
        """Test health_check handles exceptions."""
        connector = MT5Connector()
        connector._is_connected = True

        mock_mt5.terminal_info.side_effect = Exception("Health check error")

        health = connector.health_check()

        # Should return default health dict on error
        assert health["connected"] is False
        assert health["terminal_running"] is False

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_place_order_filling_mode_fok(self, mock_mt5):
        """Test place_order with FOK filling mode."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockSymbolInfo:
            def __init__(self):
                self.filling_mode = 1  # FOK bit set

        mock_mt5.symbol_info.return_value = MockSymbolInfo()
        mock_mt5.TRADE_RETCODE_DONE = 10009
        mock_mt5.ORDER_FILLING_FOK = 1
        mock_mt5.ORDER_FILLING_IOC = 2
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TYPE_BUY = 0
        mock_mt5.ORDER_TYPE_SELL = 1
        mock_mt5.ORDER_TIME_GTC = 0

        class MockOrderResult:
            def __init__(self):
                self.retcode = 10009
                self.comment = "Success"
                self.order = 12345

            def _asdict(self):
                return {"retcode": self.retcode, "comment": self.comment, "order": self.order}

        mock_mt5.order_send.return_value = MockOrderResult()

        result = connector.place_order(
            symbol="EURUSD",
            order_type="BUY",
            volume=0.01,
            price=1.10000,
            sl=1.09500,
            tp=1.11000,
        )

        assert result["success"] is True
        # Verify request used FOK filling mode
        request = mock_mt5.order_send.call_args[0][0]
        assert request["type_filling"] == 1

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_place_order_filling_mode_ioc(self, mock_mt5):
        """Test place_order with IOC filling mode when FOK not supported."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockSymbolInfo:
            def __init__(self):
                self.filling_mode = 2  # Only IOC bit set

        mock_mt5.symbol_info.return_value = MockSymbolInfo()
        mock_mt5.TRADE_RETCODE_DONE = 10009
        mock_mt5.ORDER_FILLING_FOK = 1
        mock_mt5.ORDER_FILLING_IOC = 2
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TYPE_BUY = 0
        mock_mt5.ORDER_TYPE_SELL = 1
        mock_mt5.ORDER_TIME_GTC = 0

        class MockOrderResult:
            def __init__(self):
                self.retcode = 10009
                self.comment = "Success"
                self.order = 12345

            def _asdict(self):
                return {"retcode": self.retcode, "comment": self.comment, "order": self.order}

        mock_mt5.order_send.return_value = MockOrderResult()

        result = connector.place_order(
            symbol="EURUSD",
            order_type="SELL",
            volume=0.01,
            price=1.10000,
            sl=1.10500,
            tp=1.09000,
        )

        assert result["success"] is True
        # Verify request used IOC filling mode
        request = mock_mt5.order_send.call_args[0][0]
        assert request["type_filling"] == 2

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_place_order_filling_mode_default(self, mock_mt5):
        """Test place_order with default filling mode."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockSymbolInfo:
            def __init__(self):
                self.filling_mode = 0  # Neither FOK nor IOC

        mock_mt5.symbol_info.return_value = MockSymbolInfo()
        mock_mt5.TRADE_RETCODE_DONE = 10009
        mock_mt5.ORDER_FILLING_FOK = 1
        mock_mt5.ORDER_FILLING_IOC = 2
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_TYPE_BUY = 0
        mock_mt5.ORDER_TYPE_SELL = 1
        mock_mt5.ORDER_TIME_GTC = 0

        class MockOrderResult:
            def __init__(self):
                self.retcode = 10009
                self.comment = "Success"
                self.order = 12345

            def _asdict(self):
                return {"retcode": self.retcode, "comment": self.comment, "order": self.order}

        mock_mt5.order_send.return_value = MockOrderResult()

        result = connector.place_order(
            symbol="EURUSD",
            order_type="BUY",
            volume=0.01,
            price=1.10000,
            sl=1.09500,
            tp=1.11000,
        )

        assert result["success"] is True
        # Should use default FOK
        request = mock_mt5.order_send.call_args[0][0]
        assert request["type_filling"] == 1

    def test_get_positions_not_connected(self):
        """Test get_positions when not connected."""
        connector = MT5Connector()
        connector._is_connected = False

        positions = connector.get_positions()

        assert positions == []

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_get_positions_with_symbol(self, mock_mt5):
        """Test get_positions filtered by symbol."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockPosition:
            def __init__(self):
                self.ticket = 12345
                self.symbol = "EURUSD"

            def _asdict(self):
                return {"ticket": 12345, "symbol": "EURUSD"}

        mock_mt5.positions_get.return_value = [MockPosition()]

        positions = connector.get_positions(symbol="EURUSD")

        assert len(positions) == 1
        assert positions[0]["symbol"] == "EURUSD"
        mock_mt5.positions_get.assert_called_with(symbol="EURUSD")

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_get_positions_all(self, mock_mt5):
        """Test get_positions without symbol filter."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockPosition:
            def __init__(self):
                self.ticket = 12345
                self.symbol = "EURUSD"

            def _asdict(self):
                return {"ticket": 12345, "symbol": "EURUSD"}

        mock_mt5.positions_get.return_value = [MockPosition()]

        positions = connector.get_positions()

        assert len(positions) == 1
        mock_mt5.positions_get.assert_called_with()

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_get_positions_returns_none(self, mock_mt5):
        """Test get_positions when MT5 returns None."""
        connector = MT5Connector()
        connector._is_connected = True

        mock_mt5.positions_get.return_value = None

        positions = connector.get_positions()

        assert positions == []

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_get_positions_exception_handling(self, mock_mt5):
        """Test get_positions handles exceptions."""
        connector = MT5Connector()
        connector._is_connected = True

        mock_mt5.positions_get.side_effect = Exception("Get positions error")

        positions = connector.get_positions()

        assert positions == []

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_modify_position_with_tolerance_check_sl(self, mock_mt5):
        """Test modify_position SL change within tolerance."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockPosition:
            def __init__(self):
                self.ticket = 12345
                self.symbol = "EURUSD"
                self.sl = 1.0950
                self.tp = 1.1100
                self.price_open = 1.1000

        mock_mt5.positions_get.return_value = [MockPosition()]

        class MockSymbolInfo:
            def __init__(self):
                self.point = 0.00001

        mock_mt5.symbol_info.return_value = MockSymbolInfo()

        # Try to modify SL to a value within tolerance (diff = 0.00001 < 0.00005)
        # Tolerance is point * 0.5 = 0.000005, so 0.00001 > 0.000005, should be changed
        # Let's use a value within tolerance
        result = connector.modify_position(ticket=12345, sl=1.095002)

        assert result["success"] is True
        assert result["modified"] is False
        assert result["sl_changed"] is False

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_modify_position_tolerance_check_tp(self, mock_mt5):
        """Test modify_position TP change within tolerance."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockPosition:
            def __init__(self):
                self.ticket = 12345
                self.symbol = "EURUSD"
                self.sl = 1.0950
                self.tp = 1.1100
                self.price_open = 1.1000

        mock_mt5.positions_get.return_value = [MockPosition()]

        class MockSymbolInfo:
            def __init__(self):
                self.point = 0.00001

        mock_mt5.symbol_info.return_value = MockSymbolInfo()

        # Try to modify TP to a value within tolerance
        # Tolerance is point * 0.5 = 0.000005, so 0.00001 > 0.000005, should be changed
        # Let's use a value within tolerance
        result = connector.modify_position(ticket=12345, tp=1.110002)

        assert result["success"] is True
        assert result["modified"] is False
        assert result["tp_changed"] is False

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_modify_position_fallback_tolerance_forex_major(self, mock_mt5):
        """Test modify_position fallback tolerance for forex major pairs."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockPosition:
            def __init__(self):
                self.ticket = 12345
                self.symbol = "EURUSD"
                self.sl = 1.0950  # < 10, should trigger forex major tolerance
                self.tp = 1.1100
                self.price_open = 1.1000

        mock_mt5.positions_get.return_value = [MockPosition()]
        mock_mt5.symbol_info.return_value = None  # No symbol info, use fallback

        # Change SL beyond tolerance (0.0001)
        result = connector.modify_position(ticket=12345, sl=1.0900)

        assert result["sl_changed"] is True

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_modify_position_fallback_tolerance_forex_jpy(self, mock_mt5):
        """Test modify_position fallback tolerance for JPY pairs."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockPosition:
            def __init__(self):
                self.ticket = 12345
                self.symbol = "USDJPY"
                self.sl = 145.50
                self.tp = 146.00
                self.price_open = 145.75

        mock_mt5.positions_get.return_value = [MockPosition()]
        mock_mt5.symbol_info.return_value = None  # No symbol info, use fallback

        # Change SL beyond tolerance (0.01)
        result = connector.modify_position(ticket=12345, sl=145.40)

        assert result["sl_changed"] is True

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_modify_position_fallback_tolerance_commodities(self, mock_mt5):
        """Test modify_position fallback tolerance for commodities."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockPosition:
            def __init__(self):
                self.ticket = 12345
                self.symbol = "XAUUSD"
                self.sl = 2050.50
                self.tp = 2060.00
                self.price_open = 2055.00

        mock_mt5.positions_get.return_value = [MockPosition()]
        mock_mt5.symbol_info.return_value = None

        # Change SL beyond tolerance
        result = connector.modify_position(ticket=12345, sl=2050.00)

        assert result["sl_changed"] is True

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_modify_position_fallback_tolerance_crypto(self, mock_mt5):
        """Test modify_position fallback tolerance for crypto."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockPosition:
            def __init__(self):
                self.ticket = 12345
                self.symbol = "BTCUSD"
                self.sl = 45000.0
                self.tp = 46000.0
                self.price_open = 45500.0

        mock_mt5.positions_get.return_value = [MockPosition()]
        mock_mt5.symbol_info.return_value = None

        # Change SL beyond tolerance
        result = connector.modify_position(ticket=12345, sl=44990.0)

        assert result["sl_changed"] is True

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_modify_position_only_sl_change(self, mock_mt5):
        """Test modify_position changing only SL."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockPosition:
            def __init__(self):
                self.ticket = 12345
                self.symbol = "EURUSD"
                self.sl = 1.0950
                self.tp = 1.1100
                self.price_open = 1.1000

        mock_mt5.positions_get.return_value = [MockPosition()]

        class MockSymbolInfo:
            def __init__(self):
                self.point = 0.00001

        mock_mt5.symbol_info.return_value = MockSymbolInfo()
        mock_mt5.TRADE_RETCODE_DONE = 10009

        class MockOrderResult:
            def __init__(self):
                self.retcode = 10009
                self.comment = "Success"

        mock_mt5.order_send.return_value = MockOrderResult()

        result = connector.modify_position(ticket=12345, sl=1.0960)

        assert result["success"] is True
        assert result["modified"] is True
        assert result["sl_changed"] is True
        assert result["tp_changed"] is False

        # Verify request uses current TP
        request = mock_mt5.order_send.call_args[0][0]
        assert request["sl"] == 1.0960
        assert request["tp"] == 1.1100

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_modify_position_only_tp_change(self, mock_mt5):
        """Test modify_position changing only TP."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockPosition:
            def __init__(self):
                self.ticket = 12345
                self.symbol = "EURUSD"
                self.sl = 1.0950
                self.tp = 1.1100
                self.price_open = 1.1000

        mock_mt5.positions_get.return_value = [MockPosition()]

        class MockSymbolInfo:
            def __init__(self):
                self.point = 0.00001

        mock_mt5.symbol_info.return_value = MockSymbolInfo()
        mock_mt5.TRADE_RETCODE_DONE = 10009

        class MockOrderResult:
            def __init__(self):
                self.retcode = 10009
                self.comment = "Success"

        mock_mt5.order_send.return_value = MockOrderResult()

        result = connector.modify_position(ticket=12345, tp=1.1150)

        assert result["success"] is True
        assert result["modified"] is True
        assert result["sl_changed"] is False
        assert result["tp_changed"] is True

        # Verify request uses current SL
        request = mock_mt5.order_send.call_args[0][0]
        assert request["sl"] == 1.0950
        assert request["tp"] == 1.1150

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_modify_position_mt5_no_changes_code(self, mock_mt5):
        """Test modify_position when MT5 returns code 10025 (No changes)."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockPosition:
            def __init__(self):
                self.ticket = 12345
                self.symbol = "EURUSD"
                self.sl = 1.0950
                self.tp = 1.1100
                self.price_open = 1.1000

        mock_mt5.positions_get.return_value = [MockPosition()]

        class MockSymbolInfo:
            def __init__(self):
                self.point = 0.00001

        mock_mt5.symbol_info.return_value = MockSymbolInfo()

        class MockOrderResult:
            def __init__(self):
                self.retcode = 10025  # No changes
                self.comment = "No changes"

        mock_mt5.order_send.return_value = MockOrderResult()

        result = connector.modify_position(ticket=12345, sl=1.0960)

        assert result["success"] is True
        assert result["modified"] is False
        assert "MT5 reported no changes needed" in result["message"]

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_modify_position_exception_handling(self, mock_mt5):
        """Test modify_position exception handling."""
        connector = MT5Connector()
        connector._is_connected = True

        mock_mt5.positions_get.side_effect = Exception("Position lookup error")

        result = connector.modify_position(ticket=12345, sl=1.0960)

        assert result["success"] is False
        assert result["modified"] is False
        assert "Exception" in result["message"]

    def test_close_position_not_connected(self):
        """Test close_position when not connected."""
        connector = MT5Connector()
        connector._is_connected = False

        result = connector.close_position(ticket=12345)

        assert result is None

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_close_position_not_found(self, mock_mt5):
        """Test close_position when position not found."""
        connector = MT5Connector()
        connector._is_connected = True

        mock_mt5.positions_get.return_value = None

        result = connector.close_position(ticket=12345)

        assert result is None

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_close_position_buy_to_sell(self, mock_mt5):
        """Test close_position for BUY position (close with SELL)."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockPosition:
            def __init__(self):
                self.ticket = 12345
                self.symbol = "EURUSD"
                self.type = 0  # BUY
                self.volume = 0.1
                self.magic = 123456

        mock_mt5.positions_get.return_value = [MockPosition()]

        class MockTick:
            def __init__(self):
                self.bid = 1.0990
                self.ask = 1.1000

        mock_mt5.symbol_info_tick.return_value = MockTick()

        class MockSymbolInfo:
            def __init__(self):
                self.filling_mode = 1

        mock_mt5.symbol_info.return_value = MockSymbolInfo()
        mock_mt5.TRADE_RETCODE_DONE = 10009
        mock_mt5.ORDER_TYPE_SELL = 1
        mock_mt5.ORDER_TYPE_BUY = 0
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_FILLING_FOK = 1
        mock_mt5.ORDER_TIME_GTC = 0

        class MockOrderResult:
            def __init__(self):
                self.retcode = 10009
                self.order = 54321
                self.comment = "Success"

            def _asdict(self):
                return {"retcode": 10009, "order": 54321}

        mock_mt5.order_send.return_value = MockOrderResult()

        result = connector.close_position(ticket=12345)

        assert result is not None
        assert result["order"] == 54321

        # Verify close type is SELL
        request = mock_mt5.order_send.call_args[0][0]
        assert request["type"] == 1  # SELL
        assert request["price"] == 1.0990  # Bid price

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_close_position_sell_to_buy(self, mock_mt5):
        """Test close_position for SELL position (close with BUY)."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockPosition:
            def __init__(self):
                self.ticket = 12345
                self.symbol = "EURUSD"
                self.type = 1  # SELL
                self.volume = 0.1
                self.magic = 123456

        mock_mt5.positions_get.return_value = [MockPosition()]

        class MockTick:
            def __init__(self):
                self.bid = 1.0990
                self.ask = 1.1000

        mock_mt5.symbol_info_tick.return_value = MockTick()

        class MockSymbolInfo:
            def __init__(self):
                self.filling_mode = 1

        mock_mt5.symbol_info.return_value = MockSymbolInfo()
        mock_mt5.TRADE_RETCODE_DONE = 10009
        mock_mt5.ORDER_TYPE_SELL = 1
        mock_mt5.ORDER_TYPE_BUY = 0
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_FILLING_FOK = 1
        mock_mt5.ORDER_TIME_GTC = 0

        class MockOrderResult:
            def __init__(self):
                self.retcode = 10009
                self.order = 54321
                self.comment = "Success"

            def _asdict(self):
                return {"retcode": 10009, "order": 54321}

        mock_mt5.order_send.return_value = MockOrderResult()

        result = connector.close_position(ticket=12345)

        assert result is not None
        assert result["order"] == 54321

        # Verify close type is BUY
        request = mock_mt5.order_send.call_args[0][0]
        assert request["type"] == 0  # BUY
        assert request["price"] == 1.1000  # Ask price

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_close_position_partial_close(self, mock_mt5):
        """Test close_position with partial volume."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockPosition:
            def __init__(self):
                self.ticket = 12345
                self.symbol = "EURUSD"
                self.type = 0  # BUY
                self.volume = 0.1
                self.magic = 123456

        mock_mt5.positions_get.return_value = [MockPosition()]

        class MockTick:
            def __init__(self):
                self.bid = 1.0990
                self.ask = 1.1000

        mock_mt5.symbol_info_tick.return_value = MockTick()

        class MockSymbolInfo:
            def __init__(self):
                self.filling_mode = 1

        mock_mt5.symbol_info.return_value = MockSymbolInfo()
        mock_mt5.TRADE_RETCODE_DONE = 10009
        mock_mt5.ORDER_TYPE_SELL = 1
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_FILLING_FOK = 1
        mock_mt5.ORDER_TIME_GTC = 0

        class MockOrderResult:
            def __init__(self):
                self.retcode = 10009
                self.order = 54321

            def _asdict(self):
                return {"retcode": 10009, "order": 54321}

        mock_mt5.order_send.return_value = MockOrderResult()

        result = connector.close_position(ticket=12345, volume=0.05)

        assert result is not None

        # Verify partial volume
        request = mock_mt5.order_send.call_args[0][0]
        assert request["volume"] == 0.05

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_close_position_no_tick_data(self, mock_mt5):
        """Test close_position when tick data not available."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockPosition:
            def __init__(self):
                self.ticket = 12345
                self.symbol = "EURUSD"
                self.type = 0
                self.volume = 0.1

        mock_mt5.positions_get.return_value = [MockPosition()]
        mock_mt5.symbol_info_tick.return_value = None

        result = connector.close_position(ticket=12345)

        assert result is None

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_close_position_filling_mode_selection(self, mock_mt5):
        """Test close_position filling mode selection (IOC)."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockPosition:
            def __init__(self):
                self.ticket = 12345
                self.symbol = "EURUSD"
                self.type = 0
                self.volume = 0.1
                self.magic = 123456

        mock_mt5.positions_get.return_value = [MockPosition()]

        class MockTick:
            def __init__(self):
                self.bid = 1.0990
                self.ask = 1.1000

        mock_mt5.symbol_info_tick.return_value = MockTick()

        class MockSymbolInfo:
            def __init__(self):
                self.filling_mode = 2  # IOC only

        mock_mt5.symbol_info.return_value = MockSymbolInfo()
        mock_mt5.TRADE_RETCODE_DONE = 10009
        mock_mt5.ORDER_TYPE_SELL = 1
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_FILLING_FOK = 1
        mock_mt5.ORDER_FILLING_IOC = 2
        mock_mt5.ORDER_TIME_GTC = 0

        class MockOrderResult:
            def __init__(self):
                self.retcode = 10009
                self.order = 54321

            def _asdict(self):
                return {"retcode": 10009, "order": 54321}

        mock_mt5.order_send.return_value = MockOrderResult()

        result = connector.close_position(ticket=12345)

        assert result is not None

        # Verify IOC filling mode used
        request = mock_mt5.order_send.call_args[0][0]
        assert request["type_filling"] == 2  # IOC

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_close_position_result_none(self, mock_mt5):
        """Test close_position when order_send returns None."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockPosition:
            def __init__(self):
                self.ticket = 12345
                self.symbol = "EURUSD"
                self.type = 0
                self.volume = 0.1
                self.magic = 123456

        mock_mt5.positions_get.return_value = [MockPosition()]

        class MockTick:
            def __init__(self):
                self.bid = 1.0990
                self.ask = 1.1000

        mock_mt5.symbol_info_tick.return_value = MockTick()

        class MockSymbolInfo:
            def __init__(self):
                self.filling_mode = 1

        mock_mt5.symbol_info.return_value = MockSymbolInfo()
        mock_mt5.ORDER_TYPE_SELL = 1
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_FILLING_FOK = 1
        mock_mt5.ORDER_TIME_GTC = 0
        mock_mt5.order_send.return_value = None

        result = connector.close_position(ticket=12345)

        assert result is None

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_close_position_error_retcode(self, mock_mt5):
        """Test close_position when MT5 returns error."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockPosition:
            def __init__(self):
                self.ticket = 12345
                self.symbol = "EURUSD"
                self.type = 0
                self.volume = 0.1
                self.magic = 123456

        mock_mt5.positions_get.return_value = [MockPosition()]

        class MockTick:
            def __init__(self):
                self.bid = 1.0990
                self.ask = 1.1000

        mock_mt5.symbol_info_tick.return_value = MockTick()

        class MockSymbolInfo:
            def __init__(self):
                self.filling_mode = 1

        mock_mt5.symbol_info.return_value = MockSymbolInfo()
        mock_mt5.TRADE_RETCODE_DONE = 10009
        mock_mt5.ORDER_TYPE_SELL = 1
        mock_mt5.TRADE_ACTION_DEAL = 1
        mock_mt5.ORDER_FILLING_FOK = 1
        mock_mt5.ORDER_TIME_GTC = 0

        class MockOrderResult:
            def __init__(self):
                self.retcode = 10006  # Request rejected
                self.comment = "Request rejected"

        mock_mt5.order_send.return_value = MockOrderResult()

        result = connector.close_position(ticket=12345)

        assert result is None

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_close_position_exception_handling(self, mock_mt5):
        """Test close_position exception handling."""
        connector = MT5Connector()
        connector._is_connected = True

        mock_mt5.positions_get.side_effect = Exception("Close error")

        result = connector.close_position(ticket=12345)

        assert result is None

    def test_get_history_deal_not_connected(self):
        """Test get_history_deal when not connected."""
        connector = MT5Connector()
        connector._is_connected = False

        result = connector.get_history_deal(ticket=12345)

        assert result is None

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_get_history_deal_no_deals(self, mock_mt5):
        """Test get_history_deal when no deals found."""
        connector = MT5Connector()
        connector._is_connected = True

        mock_mt5.history_deals_get.return_value = None

        result = connector.get_history_deal(ticket=12345)

        assert result is None

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_get_history_deal_empty_deals(self, mock_mt5):
        """Test get_history_deal when deals list is empty."""
        connector = MT5Connector()
        connector._is_connected = True

        mock_mt5.history_deals_get.return_value = []

        result = connector.get_history_deal(ticket=12345)

        assert result is None

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_get_history_deal_closing_deal_found(self, mock_mt5):
        """Test get_history_deal finds closing deal."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockDeal:
            def __init__(self, entry, deal_type):
                self.entry = entry
                self.deal_type = deal_type
                self.ticket = 100
                self.price = 1.1000
                self.volume = 0.1

            def _asdict(self):
                return {
                    "entry": self.entry,
                    "deal_type": self.deal_type,
                    "ticket": self.ticket,
                    "price": self.price,
                    "volume": self.volume,
                }

        # Mix of deals, last one is closing deal
        mock_mt5.history_deals_get.return_value = [
            MockDeal(entry=0, deal_type=0),  # Entry IN
            MockDeal(entry=0, deal_type=0),  # Entry IN
            MockDeal(entry=1, deal_type=1),  # Entry OUT (closing deal)
        ]
        mock_mt5.DEAL_ENTRY_OUT = 1

        result = connector.get_history_deal(ticket=12345)

        assert result is not None
        assert result["entry"] == 1  # OUT deal

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_get_history_deal_no_closing_deal_uses_last(self, mock_mt5):
        """Test get_history_deal uses last deal when no OUT deal found."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockDeal:
            def __init__(self, entry, deal_type):
                self.entry = entry
                self.deal_type = deal_type
                self.ticket = 100
                self.price = 1.1000
                self.volume = 0.1

            def _asdict(self):
                return {
                    "entry": self.entry,
                    "deal_type": self.deal_type,
                    "ticket": self.ticket,
                    "price": self.price,
                    "volume": self.volume,
                }

        # Only IN deals, no OUT deal
        mock_mt5.history_deals_get.return_value = [
            MockDeal(entry=0, deal_type=0),  # Entry IN
            MockDeal(entry=0, deal_type=0),  # Entry IN (last one)
        ]
        mock_mt5.DEAL_ENTRY_OUT = 1

        result = connector.get_history_deal(ticket=12345)

        assert result is not None
        # Should return last deal in list
        assert result["entry"] == 0

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_get_history_deal_exception_handling(self, mock_mt5):
        """Test get_history_deal exception handling."""
        connector = MT5Connector()
        connector._is_connected = True

        mock_mt5.history_deals_get.side_effect = Exception("History error")

        result = connector.get_history_deal(ticket=12345)

        assert result is None

    def test_terminal_info_property_empty(self):
        """Test terminal_info property when not initialized."""
        connector = MT5Connector()
        connector._terminal_info = None

        info = connector.terminal_info

        assert info == {}

    def test_account_info_property_empty(self):
        """Test account_info property when not initialized."""
        connector = MT5Connector()
        connector._account_info = None

        info = connector.account_info

        assert info == {}

    @patch("trading_bot.connectors.mt5_connector.mt5.version")
    def test_version_property_exception(self, mock_version):
        """Test version property when exception occurs."""
        connector = MT5Connector()

        mock_version.side_effect = Exception("Version error")

        version = connector.version

        assert version is None

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_context_manager_exit(self, mock_mt5):
        """Test context manager __exit__ method."""
        connector = MT5Connector()
        connector._is_connected = True

        with patch.object(connector, "shutdown") as mock_shutdown:
            connector.__exit__(None, None, None)
            mock_shutdown.assert_called_once()

    @patch("trading_bot.connectors.mt5_connector.mt5")
    def test_modify_position_result_none(self, mock_mt5):
        """Test modify_position when order_send returns None."""
        connector = MT5Connector()
        connector._is_connected = True

        class MockPosition:
            def __init__(self):
                self.ticket = 12345
                self.symbol = "EURUSD"
                self.sl = 1.0950
                self.tp = 1.1100
                self.price_open = 1.1000

        mock_mt5.positions_get.return_value = [MockPosition()]

        class MockSymbolInfo:
            def __init__(self):
                self.point = 0.00001

        mock_mt5.symbol_info.return_value = MockSymbolInfo()
        mock_mt5.order_send.return_value = None

        result = connector.modify_position(ticket=12345, sl=1.0960)

        assert result["success"] is False
        assert result["modified"] is False
        assert "None" in result["message"]
