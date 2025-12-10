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