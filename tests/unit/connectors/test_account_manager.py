"""
Unit tests for Account Manager.

Tests account information retrieval, balance monitoring, and margin tracking.
"""

from unittest.mock import Mock, patch

import pytest

try:
    import MetaTrader5 as mt5

    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

from trading_bot.connectors.account_manager import AccountManager
from trading_bot.exceptions import MT5ConnectionError


@pytest.fixture
def mock_mt5_connector():
    """Create mock MT5 connector."""
    connector = Mock()
    connector.is_connected.return_value = True
    return connector


@pytest.fixture
def account_manager(mock_mt5_connector):
    """Create AccountManager instance."""
    with patch("trading_bot.connectors.account_manager.MT5_AVAILABLE", True):
        with patch("trading_bot.connectors.account_manager.mt5"):
            return AccountManager(mock_mt5_connector)


class TestAccountManagerInitialization:
    """Test AccountManager initialization."""

    def test_init_success(self, mock_mt5_connector):
        """Test successful initialization."""
        with patch("trading_bot.connectors.account_manager.MT5_AVAILABLE", True):
            manager = AccountManager(mock_mt5_connector)
            assert manager.connector == mock_mt5_connector

    def test_init_mt5_not_available(self, mock_mt5_connector):
        """Test initialization fails when MT5 not available."""
        with patch("trading_bot.connectors.account_manager.MT5_AVAILABLE", False):
            with pytest.raises(ImportError, match="MetaTrader5 package not available"):
                AccountManager(mock_mt5_connector)


class TestAccountInfoRetrieval:
    """Test account information retrieval."""

    def test_get_account_info_success(self, account_manager):
        """Test getting account info successfully."""
        with patch("trading_bot.connectors.account_manager.mt5") as mock_mt5:
            mock_account = Mock()
            mock_account._asdict.return_value = {
                "login": 12345,
                "balance": 10000.0,
                "equity": 10050.0,
                "margin": 50.0,
                "margin_free": 10000.0,
                "margin_level": 20100.0,
                "profit": 50.0,
                "leverage": 100,
                "currency": "USD",
                "server": "TestServer",
                "company": "TestBroker",
                "trade_allowed": True,
                "trade_mode": 0,  # DEMO
            }
            mock_mt5.account_info.return_value = mock_account

            info = account_manager.get_account_info()

            assert info["login"] == 12345
            assert info["balance"] == 10000.0
            assert info["equity"] == 10050.0
            mock_mt5.account_info.assert_called_once()

    def test_get_account_info_not_connected(self, account_manager, mock_mt5_connector):
        """Test getting account info fails when not connected."""
        mock_mt5_connector.is_connected.return_value = False

        with pytest.raises(MT5ConnectionError, match="MT5 not connected"):
            account_manager.get_account_info()

    def test_get_account_info_none_result(self, account_manager):
        """Test getting account info when MT5 returns None."""
        with patch("trading_bot.connectors.account_manager.mt5") as mock_mt5:
            mock_mt5.account_info.return_value = None
            mock_mt5.last_error.return_value = (10001, "Connection error")

            with pytest.raises(MT5ConnectionError, match="Failed to get account info"):
                account_manager.get_account_info()


class TestBalanceMonitoring:
    """Test balance and equity monitoring."""

    def test_get_balance(self, account_manager):
        """Test getting account balance."""
        with patch("trading_bot.connectors.account_manager.mt5") as mock_mt5:
            mock_account = Mock()
            mock_account._asdict.return_value = {"balance": 10000.0}
            mock_mt5.account_info.return_value = mock_account

            balance = account_manager.get_balance()

            assert balance == 10000.0

    def test_get_equity(self, account_manager):
        """Test getting account equity."""
        with patch("trading_bot.connectors.account_manager.mt5") as mock_mt5:
            mock_account = Mock()
            mock_account._asdict.return_value = {"equity": 10050.0}
            mock_mt5.account_info.return_value = mock_account

            equity = account_manager.get_equity()

            assert equity == 10050.0

    def test_get_profit(self, account_manager):
        """Test getting current profit/loss."""
        with patch("trading_bot.connectors.account_manager.mt5") as mock_mt5:
            mock_account = Mock()
            mock_account._asdict.return_value = {"profit": 50.0}
            mock_mt5.account_info.return_value = mock_account

            profit = account_manager.get_profit()

            assert profit == 50.0


class TestMarginTracking:
    """Test margin calculations and tracking."""

    def test_get_margin(self, account_manager):
        """Test getting used margin."""
        with patch("trading_bot.connectors.account_manager.mt5") as mock_mt5:
            mock_account = Mock()
            mock_account._asdict.return_value = {"margin": 50.0}
            mock_mt5.account_info.return_value = mock_account

            margin = account_manager.get_margin()

            assert margin == 50.0

    def test_get_free_margin(self, account_manager):
        """Test getting free margin."""
        with patch("trading_bot.connectors.account_manager.mt5") as mock_mt5:
            mock_account = Mock()
            mock_account._asdict.return_value = {"margin_free": 10000.0}
            mock_mt5.account_info.return_value = mock_account

            free_margin = account_manager.get_free_margin()

            assert free_margin == 10000.0

    def test_get_margin_level(self, account_manager):
        """Test getting margin level percentage."""
        with patch("trading_bot.connectors.account_manager.mt5") as mock_mt5:
            mock_account = Mock()
            mock_account._asdict.return_value = {"margin_level": 20100.0}
            mock_mt5.account_info.return_value = mock_account

            margin_level = account_manager.get_margin_level()

            assert margin_level == 20100.0

    def test_get_margin_level_zero(self, account_manager):
        """Test getting margin level when zero (no positions)."""
        with patch("trading_bot.connectors.account_manager.mt5") as mock_mt5:
            mock_account = Mock()
            mock_account._asdict.return_value = {"margin_level": 0.0}
            mock_mt5.account_info.return_value = mock_account

            margin_level = account_manager.get_margin_level()

            assert margin_level == 0.0


class TestAccountDetails:
    """Test account details retrieval."""

    def test_get_leverage(self, account_manager):
        """Test getting account leverage."""
        with patch("trading_bot.connectors.account_manager.mt5") as mock_mt5:
            mock_account = Mock()
            mock_account._asdict.return_value = {"leverage": 100}
            mock_mt5.account_info.return_value = mock_account

            leverage = account_manager.get_leverage()

            assert leverage == 100

    def test_get_currency(self, account_manager):
        """Test getting account currency."""
        with patch("trading_bot.connectors.account_manager.mt5") as mock_mt5:
            mock_account = Mock()
            mock_account._asdict.return_value = {"currency": "USD"}
            mock_mt5.account_info.return_value = mock_account

            currency = account_manager.get_currency()

            assert currency == "USD"

    def test_get_server(self, account_manager):
        """Test getting broker server name."""
        with patch("trading_bot.connectors.account_manager.mt5") as mock_mt5:
            mock_account = Mock()
            mock_account._asdict.return_value = {"server": "TestServer-Demo"}
            mock_mt5.account_info.return_value = mock_account

            server = account_manager.get_server()

            assert server == "TestServer-Demo"

    def test_get_company(self, account_manager):
        """Test getting broker company name."""
        with patch("trading_bot.connectors.account_manager.mt5") as mock_mt5:
            mock_account = Mock()
            mock_account._asdict.return_value = {"company": "TestBroker Ltd"}
            mock_mt5.account_info.return_value = mock_account

            company = account_manager.get_company()

            assert company == "TestBroker Ltd"


class TestTradingPermissions:
    """Test trading permissions and account type."""

    def test_is_trade_allowed_true(self, account_manager):
        """Test checking if trading is allowed (True)."""
        with patch("trading_bot.connectors.account_manager.mt5") as mock_mt5:
            mock_account = Mock()
            mock_account._asdict.return_value = {"trade_allowed": True}
            mock_mt5.account_info.return_value = mock_account

            is_allowed = account_manager.is_trade_allowed()

            assert is_allowed is True

    def test_is_trade_allowed_false(self, account_manager):
        """Test checking if trading is allowed (False)."""
        with patch("trading_bot.connectors.account_manager.mt5") as mock_mt5:
            mock_account = Mock()
            mock_account._asdict.return_value = {"trade_allowed": False}
            mock_mt5.account_info.return_value = mock_account

            is_allowed = account_manager.is_trade_allowed()

            assert is_allowed is False

    def test_get_account_type_demo(self, account_manager):
        """Test getting account type (DEMO)."""
        with patch("trading_bot.connectors.account_manager.mt5") as mock_mt5:
            mock_account = Mock()
            mock_account._asdict.return_value = {"trade_mode": 0}  # DEMO
            mock_mt5.account_info.return_value = mock_account

            account_type = account_manager.get_account_type()

            assert account_type == "DEMO"

    def test_get_account_type_real(self, account_manager):
        """Test getting account type (REAL)."""
        with patch("trading_bot.connectors.account_manager.mt5") as mock_mt5:
            mock_account = Mock()
            mock_account._asdict.return_value = {"trade_mode": 2}  # REAL
            mock_mt5.account_info.return_value = mock_account

            account_type = account_manager.get_account_type()

            assert account_type == "REAL"

    def test_get_account_type_contest(self, account_manager):
        """Test getting account type (CONTEST)."""
        with patch("trading_bot.connectors.account_manager.mt5") as mock_mt5:
            mock_account = Mock()
            mock_account._asdict.return_value = {"trade_mode": 1}  # CONTEST
            mock_mt5.account_info.return_value = mock_account

            account_type = account_manager.get_account_type()

            assert account_type == "CONTEST"

    def test_get_account_type_unknown(self, account_manager):
        """Test getting account type (UNKNOWN)."""
        with patch("trading_bot.connectors.account_manager.mt5") as mock_mt5:
            mock_account = Mock()
            mock_account._asdict.return_value = {"trade_mode": 99}  # Unknown
            mock_mt5.account_info.return_value = mock_account

            account_type = account_manager.get_account_type()

            assert account_type == "UNKNOWN"


class TestAccountSummary:
    """Test account summary generation."""

    def test_get_summary(self, account_manager):
        """Test getting complete account summary."""
        with patch("trading_bot.connectors.account_manager.mt5") as mock_mt5:
            mock_account = Mock()
            mock_account._asdict.return_value = {
                "balance": 10000.0,
                "equity": 10050.0,
                "margin": 50.0,
                "margin_free": 10000.0,
                "margin_level": 20100.0,
                "profit": 50.0,
                "leverage": 100,
                "currency": "USD",
                "server": "TestServer",
                "company": "TestBroker",
                "trade_allowed": True,
                "trade_mode": 0,
            }
            mock_mt5.account_info.return_value = mock_account

            summary = account_manager.get_summary()

            assert summary["balance"] == 10000.0
            assert summary["equity"] == 10050.0
            assert summary["margin"] == 50.0
            assert summary["free_margin"] == 10000.0
            assert summary["margin_level"] == 20100.0
            assert summary["profit"] == 50.0
            assert summary["leverage"] == 100
            assert summary["currency"] == "USD"
            assert summary["server"] == "TestServer"
            assert summary["company"] == "TestBroker"
            assert summary["trade_allowed"] is True
            assert summary["account_type"] == "DEMO"


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_get_account_info_exception(self, account_manager):
        """Test exception handling in get_account_info."""
        with patch("trading_bot.connectors.account_manager.mt5") as mock_mt5:
            mock_mt5.account_info.side_effect = Exception("Unexpected error")

            with pytest.raises(MT5ConnectionError, match="Failed to retrieve account info"):
                account_manager.get_account_info()
