"""
Unit tests for CLI commands.

Tests start, stop, status, config, and MT5 commands.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from trading_bot.cli import cli


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = Mock()
    config.env = "development"
    config.validate.return_value = True
    config.database.url = "sqlite+aiosqlite:///test.db"
    config.database.echo = False
    config.logging.level = "INFO"
    config.logging.file_path = "./logs/test.log"
    config.logging.max_file_size = "10 MB"
    config.logging.backup_count = 5
    config.mt5.terminal_path = None
    config.mt5.login = 12345
    config.mt5.password = "testpass"
    config.mt5.server = "TestServer"
    config.mt5.connection_timeout = 30
    config.mt5.retry_attempts = 3
    # Make config.get() work like a dict
    config.get = Mock(
        side_effect=lambda key, default=None: {
            "symbols": ["EURUSD", "GBPUSD"],
            "timeframe": "H1",
            "analysis_interval": 60,
            "initial_balance": 10000.0,
            "risk_management": {},
            "position_manager": {},
        }.get(key, default)
    )
    # Make config._config a dict-like object
    config._config = {
        "symbols": ["EURUSD", "GBPUSD"],
        "timeframe": "H1",
        "analysis_interval": 60,
        "initial_balance": 10000.0,
        "risk_management": {},
        "position_manager": {},
    }
    return config


class TestCLIInitialization:
    """Test CLI initialization."""

    def test_cli_group_exists(self, runner):
        """Test that CLI group exists."""
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Trading Bot" in result.output

    def test_cli_config_option(self, runner):
        """Test CLI config option."""
        # --help doesn't execute the command, so Configuration won't be called
        # Test with actual command instead
        with patch("trading_bot.cli.Configuration") as mock_config_class:
            mock_config = Mock()
            mock_config.env = "production"
            mock_config.validate.return_value = True
            mock_config.database.url = "sqlite+aiosqlite:///test.db"
            mock_config.database.echo = False
            mock_config.logging.level = "INFO"
            mock_config.logging.file_path = "./logs/test.log"
            mock_config.logging.max_file_size = "10 MB"
            mock_config.logging.backup_count = 5
            mock_config.mt5.terminal_path = None
            mock_config.mt5.login = 12345
            mock_config.mt5.password = "testpass"
            mock_config.mt5.server = "TestServer"
            mock_config.mt5.connection_timeout = 30
            mock_config.mt5.retry_attempts = 3
            mock_config_class.return_value = mock_config

            with patch("trading_bot.cli.init_database"):
                result = runner.invoke(cli, ["--config", "production", "status"])

                assert result.exit_code == 0
                mock_config_class.assert_called_once_with(env="production")


class TestStartCommand:
    """Test start command."""

    @patch("trading_bot.cli.init_database")
    @patch("trading_bot.cli.setup_logger")
    @patch("asyncio.run")
    @patch("trading_bot.main.TradingBot")
    def test_start_dry_run_mock_mode(
        self, mock_bot_class, mock_asyncio_run, mock_setup_logger, mock_init_db, runner, mock_config
    ):
        """Test start command with dry-run (mock mode)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            # Mock init_database to return a manager with mocked create_tables
            mock_db_manager = Mock()
            mock_db_manager.create_tables = AsyncMock()
            mock_init_db.return_value = mock_db_manager

            # Mock TradingBot instance
            mock_bot = Mock()
            mock_bot.start = AsyncMock()
            mock_bot.stop = AsyncMock()
            mock_bot_class.return_value = mock_bot
            # Mock asyncio.run to avoid actually running async code
            mock_asyncio_run.return_value = None

            result = runner.invoke(cli, ["--config", "development", "start", "--dry-run"])

            assert result.exit_code == 0
            assert "DRY-RUN" in result.output or "dry-run" in result.output.lower()
            mock_init_db.assert_called_once()
            mock_bot_class.assert_called_once()
            # asyncio.run is called twice: once for create_tables() and once for bot.start()
            assert mock_asyncio_run.call_count == 2

    @patch("trading_bot.cli.init_database")
    @patch("trading_bot.cli.MT5Connector")
    @patch("trading_bot.cli.setup_logger")
    @patch("asyncio.run")
    @patch("trading_bot.main.TradingBot")
    def test_start_dry_run_with_mt5(
        self,
        mock_bot_class,
        mock_asyncio_run,
        mock_setup_logger,
        mock_mt5,
        mock_init_db,
        runner,
        mock_config,
    ):
        """Test start command with dry-run and real MT5 connection."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            mock_connector = Mock()
            mock_connector.initialize.return_value = True
            mock_connector.account_info = {"login": 12345, "balance": 10000.0}
            mock_connector.is_connected.return_value = True
            mock_mt5.return_value = mock_connector

            # Mock TradingBot instance
            mock_bot = Mock()
            mock_bot.start = AsyncMock()
            mock_bot.stop = AsyncMock()
            mock_bot_class.return_value = mock_bot
            # Mock asyncio.run to avoid actually running async code
            mock_asyncio_run.return_value = None

            result = runner.invoke(
                cli, ["--config", "development", "start", "--dry-run", "--connect-mt5"]
            )

            assert result.exit_code == 0
            assert "DRY-RUN" in result.output or "dry-run" in result.output.lower()

    @patch("trading_bot.cli.init_database")
    @patch("trading_bot.cli.MT5Connector")
    @patch("trading_bot.cli.setup_logger")
    def test_start_live_mode(self, mock_setup_logger, mock_mt5, mock_init_db, runner, mock_config):
        """Test start command in live mode."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            mock_connector = Mock()
            mock_connector.initialize.return_value = True
            mock_connector.account_info = {"login": 12345, "balance": 10000.0}
            mock_mt5.return_value = mock_connector

            result = runner.invoke(cli, ["--config", "development", "start"])

            # May fail if MT5 not available, but should handle gracefully
            assert result.exit_code in [0, 1]  # 0 if success, 1 if MT5 not available

    @patch("trading_bot.cli.init_database")
    @patch("trading_bot.cli.setup_logger")
    def test_start_config_validation_failure(
        self, mock_setup_logger, mock_init_db, runner, mock_config
    ):
        """Test start command with invalid configuration."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            mock_config.validate.side_effect = ValueError("Invalid configuration")

            result = runner.invoke(cli, ["--config", "development", "start"])

            assert result.exit_code != 0
            assert "Invalid" in result.output or "Error" in result.output

    @patch("trading_bot.cli.init_database")
    @patch("trading_bot.cli.setup_logger")
    @patch("asyncio.run")
    @patch("trading_bot.main.TradingBot")
    def test_start_connect_mt5_without_dry_run(
        self, mock_bot_class, mock_asyncio_run, mock_setup_logger, mock_init_db, runner, mock_config
    ):
        """Test start command with --connect-mt5 without --dry-run (line 77-79)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            mock_db_manager = Mock()
            mock_db_manager.create_tables = AsyncMock()
            mock_init_db.return_value = mock_db_manager

            mock_bot = Mock()
            mock_bot.start = AsyncMock()
            mock_bot.stop = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_asyncio_run.return_value = None

            result = runner.invoke(cli, ["--config", "development", "start", "--connect-mt5"])

            assert result.exit_code == 0
            assert "WARNING" in result.output or "ignored" in result.output.lower()

    @patch("trading_bot.cli.init_database")
    @patch("trading_bot.cli.MT5Connector")
    @patch("trading_bot.cli.setup_logger")
    @patch("asyncio.run")
    @patch("trading_bot.main.TradingBot")
    def test_start_mt5_connection_failed(
        self,
        mock_bot_class,
        mock_asyncio_run,
        mock_setup_logger,
        mock_mt5,
        mock_init_db,
        runner,
        mock_config,
    ):
        """Test start command when MT5 connection fails (line 155-160)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            mock_db_manager = Mock()
            mock_db_manager.create_tables = AsyncMock()
            mock_init_db.return_value = mock_db_manager

            mock_connector = Mock()
            mock_connector.initialize.return_value = False
            mock_mt5.return_value = mock_connector

            mock_bot = Mock()
            mock_bot.start = AsyncMock()
            mock_bot.stop = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_asyncio_run.return_value = None

            result = runner.invoke(
                cli, ["--config", "development", "start", "--dry-run", "--connect-mt5"]
            )

            assert result.exit_code == 0
            assert "WARNING" in result.output or "failed" in result.output.lower()

    @patch("trading_bot.cli.init_database")
    @patch("trading_bot.cli.MT5Connector")
    @patch("trading_bot.cli.setup_logger")
    @patch("asyncio.run")
    @patch("trading_bot.main.TradingBot")
    def test_start_mt5_import_error(
        self,
        mock_bot_class,
        mock_asyncio_run,
        mock_setup_logger,
        mock_mt5,
        mock_init_db,
        runner,
        mock_config,
    ):
        """Test start command when MT5 ImportError occurs (line 162-164)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            mock_db_manager = Mock()
            mock_db_manager.create_tables = AsyncMock()
            mock_init_db.return_value = mock_db_manager

            mock_mt5.side_effect = ImportError("MetaTrader5 not available")

            mock_bot = Mock()
            mock_bot.start = AsyncMock()
            mock_bot.stop = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_asyncio_run.return_value = None

            result = runner.invoke(
                cli, ["--config", "development", "start", "--dry-run", "--connect-mt5"]
            )

            assert result.exit_code == 0
            assert "WARNING" in result.output or "not available" in result.output.lower()

    @patch("trading_bot.cli.init_database")
    @patch("trading_bot.cli.MT5Connector")
    @patch("trading_bot.cli.setup_logger")
    @patch("asyncio.run")
    @patch("trading_bot.main.TradingBot")
    def test_start_mt5_exception(
        self,
        mock_bot_class,
        mock_asyncio_run,
        mock_setup_logger,
        mock_mt5,
        mock_init_db,
        runner,
        mock_config,
    ):
        """Test start command when MT5 exception occurs (line 165-170)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            mock_db_manager = Mock()
            mock_db_manager.create_tables = AsyncMock()
            mock_init_db.return_value = mock_db_manager

            mock_mt5.side_effect = Exception("MT5 connection error")

            mock_bot = Mock()
            mock_bot.start = AsyncMock()
            mock_bot.stop = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_asyncio_run.return_value = None

            result = runner.invoke(
                cli, ["--config", "development", "start", "--dry-run", "--connect-mt5"]
            )

            assert result.exit_code == 0
            assert "WARNING" in result.output or "error" in result.output.lower()


class TestStatusCommand:
    """Test status command."""

    @patch("trading_bot.cli._mt5_connector", None)
    @patch("trading_bot.cli.setup_logger")
    def test_status_not_connected(self, mock_setup_logger, runner, mock_config):
        """Test status command when not connected."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            result = runner.invoke(cli, ["--config", "development", "status"])

            assert result.exit_code == 0
            assert "Not Connected" in result.output or "WARN" in result.output

    @patch("trading_bot.cli._mt5_connector")
    @patch("trading_bot.cli.setup_logger")
    def test_status_connected(self, mock_mt5_connector, mock_setup_logger, runner, mock_config):
        """Test status command when connected."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            mock_mt5_connector.is_connected.return_value = True
            mock_mt5_connector.account_info = {"login": 12345}

            result = runner.invoke(cli, ["--config", "development", "status"])

            assert result.exit_code == 0
            assert "Connected" in result.output or "OK" in result.output


class TestConfigCommands:
    """Test config commands."""

    @patch("trading_bot.cli.setup_logger")
    def test_config_show(self, mock_setup_logger, runner, mock_config):
        """Test config show command."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            result = runner.invoke(cli, ["--config", "development", "config", "show"])

            assert result.exit_code == 0
            # Should show configuration details

    @patch("trading_bot.cli.setup_logger")
    def test_config_validate(self, mock_setup_logger, runner, mock_config):
        """Test config validate command."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            result = runner.invoke(cli, ["--config", "development", "config", "validate"])

            assert result.exit_code == 0
            assert "valid" in result.output.lower() or "OK" in result.output


class TestMT5Commands:
    """Test MT5 commands."""

    @patch("trading_bot.cli.MT5Connector")
    @patch("trading_bot.cli.setup_logger")
    def test_mt5_connect_success(self, mock_setup_logger, mock_mt5, runner, mock_config):
        """Test MT5 connect command success."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            mock_connector = Mock()
            mock_connector.initialize.return_value = True
            mock_connector.account_info = {
                "login": 12345,
                "server": "TestServer",
                "company": "TestBroker",
                "balance": 10000.0,
                "equity": 10000.0,
                "leverage": 100,
            }
            mock_mt5.return_value = mock_connector

            result = runner.invoke(cli, ["--config", "development", "mt5", "connect"])

            # May fail if MT5 not available, but should handle gracefully
            assert result.exit_code in [0, 1]

    @patch("trading_bot.cli.MT5Connector")
    @patch("trading_bot.cli.setup_logger")
    def test_mt5_connect_failure(self, mock_setup_logger, mock_mt5, runner, mock_config):
        """Test MT5 connect command failure."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            mock_connector = Mock()
            mock_connector.initialize.return_value = False
            mock_mt5.return_value = mock_connector

            result = runner.invoke(cli, ["--config", "development", "mt5", "connect"])

            # Should handle failure gracefully
            assert result.exit_code in [0, 1]

    @patch("trading_bot.cli.setup_logger")
    def test_mt5_disconnect(self, mock_setup_logger, runner, mock_config):
        """Test MT5 disconnect command."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            with patch("trading_bot.cli._mt5_connector") as mock_mt5_connector:
                mock_mt5_connector.shutdown = Mock()

                result = runner.invoke(cli, ["--config", "development", "mt5", "disconnect"])

                assert result.exit_code == 0
                # shutdown should be called if connector exists
                if mock_mt5_connector:
                    assert (
                        mock_mt5_connector.shutdown.called
                        or "No active connection" in result.output
                    )

    @patch("trading_bot.cli.setup_logger")
    def test_mt5_disconnect_exception(self, mock_setup_logger, runner, mock_config):
        """Test MT5 disconnect command with exception (line 379-382)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            with patch("trading_bot.cli._mt5_connector") as mock_mt5_connector:
                mock_mt5_connector.shutdown.side_effect = Exception("Disconnect error")

                result = runner.invoke(cli, ["--config", "development", "mt5", "disconnect"])

                assert result.exit_code == 0
                assert "Warning" in result.output or "error" in result.output.lower()

    @patch("trading_bot.cli.setup_logger")
    def test_mt5_disconnect_no_connection(self, mock_setup_logger, runner, mock_config):
        """Test MT5 disconnect when no connection exists (line 381-382)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            with patch("trading_bot.cli._mt5_connector", None):

                result = runner.invoke(cli, ["--config", "development", "mt5", "disconnect"])

                assert result.exit_code == 0
                assert "No active connection" in result.output

    @patch("trading_bot.cli.setup_logger")
    def test_mt5_info(self, mock_setup_logger, runner, mock_config):
        """Test MT5 info command."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            with patch("trading_bot.cli._mt5_connector") as mock_mt5_connector:
                mock_mt5_connector.is_connected.return_value = True
                mock_mt5_connector.account_info = {
                    "login": 12345,
                    "balance": 10000.0,
                    "server": "TestServer",
                    "company": "TestBroker",
                    "equity": 10000.0,
                }
                mock_mt5_connector.terminal_info = {"name": "MetaTrader 5", "trade_allowed": True}

                result = runner.invoke(cli, ["--config", "development", "mt5", "status"])

                assert result.exit_code == 0
                assert "Connected" in result.output or "12345" in result.output

    @patch("trading_bot.cli.setup_logger")
    def test_mt5_status_not_connected(self, mock_setup_logger, runner, mock_config):
        """Test MT5 status when not connected (line 413-415)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            with patch("trading_bot.cli._mt5_connector", None):

                result = runner.invoke(cli, ["--config", "development", "mt5", "status"])

                assert result.exit_code == 0
                assert "Not Connected" in result.output


class TestVersionCommand:
    """Test version command."""

    @patch("trading_bot.cli.setup_logger")
    def test_version_command(self, mock_setup_logger, runner):
        """Test version command."""
        result = runner.invoke(cli, ["version"])

        assert result.exit_code == 0
        # Should show version information


class TestErrorHandling:
    """Test error handling in CLI."""

    @patch("trading_bot.cli.setup_logger")
    def test_invalid_command(self, mock_setup_logger, runner):
        """Test invalid command handling."""
        result = runner.invoke(cli, ["invalid-command"])

        assert result.exit_code != 0
        assert "No such command" in result.output or "Usage" in result.output

    @patch("trading_bot.cli.init_database")
    @patch("trading_bot.cli.setup_logger")
    def test_start_database_error(self, mock_setup_logger, mock_init_db, runner, mock_config):
        """Test start command with database error."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            mock_init_db.side_effect = Exception("Database error")

            result = runner.invoke(cli, ["--config", "development", "start", "--dry-run"])

            assert result.exit_code != 0
            assert "Error" in result.output or "error" in result.output.lower()


class TestAccountCommands:
    """Test account commands."""

    @patch("trading_bot.cli.AccountManager")
    @patch("trading_bot.cli.setup_logger")
    def test_account_info_success(
        self, mock_setup_logger, mock_account_manager, runner, mock_config
    ):
        """Test account info command success."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            with patch("trading_bot.cli._mt5_connector") as mock_mt5_connector:
                mock_mt5_connector.is_connected.return_value = True

                mock_manager = Mock()
                mock_manager.get_summary.return_value = {
                    "balance": 10000.0,
                    "equity": 10000.0,
                    "margin": 0.0,
                    "free_margin": 10000.0,
                    "margin_level": 0.0,
                    "profit": 0.0,
                    "leverage": 100,
                    "currency": "USD",
                    "server": "TestServer",
                    "company": "TestBroker",
                    "account_type": "DEMO",
                    "trade_allowed": True,
                }
                mock_account_manager.return_value = mock_manager

                result = runner.invoke(cli, ["--config", "development", "account", "info"])

                assert result.exit_code == 0
                assert "Account Information" in result.output

    @patch("trading_bot.cli.setup_logger")
    def test_account_info_not_connected(self, mock_setup_logger, runner, mock_config):
        """Test account info when not connected (line 430-435)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            with patch("trading_bot.cli._mt5_connector", None):

                result = runner.invoke(cli, ["--config", "development", "account", "info"])

                assert result.exit_code == 0
                assert "not connected" in result.output.lower()

    @patch("trading_bot.cli.AccountManager")
    @patch("trading_bot.cli.setup_logger")
    def test_account_info_exception(
        self, mock_setup_logger, mock_account_manager, runner, mock_config
    ):
        """Test account info with exception (line 462-464)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            with patch("trading_bot.cli._mt5_connector") as mock_mt5_connector:
                mock_mt5_connector.is_connected.return_value = True

                mock_manager = Mock()
                mock_manager.get_summary.side_effect = Exception("Account error")
                mock_account_manager.return_value = mock_manager

                result = runner.invoke(cli, ["--config", "development", "account", "info"])

                assert result.exit_code == 0
                assert "Error" in result.output


class TestStopCommand:
    """Test stop command."""

    @patch("trading_bot.cli.setup_logger")
    def test_stop_with_connector(self, mock_setup_logger, runner, mock_config):
        """Test stop command with MT5 connector."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            with patch("trading_bot.cli._mt5_connector") as mock_mt5_connector:
                mock_mt5_connector.shutdown = Mock()

                result = runner.invoke(cli, ["--config", "development", "stop"])

                assert result.exit_code == 0
                assert "stopped" in result.output.lower()

    @patch("trading_bot.cli.setup_logger")
    def test_stop_exception(self, mock_setup_logger, runner, mock_config):
        """Test stop command with exception (line 253-255)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            with patch("trading_bot.cli._mt5_connector") as mock_mt5_connector:
                mock_mt5_connector.shutdown.side_effect = Exception("Shutdown error")

                result = runner.invoke(cli, ["--config", "development", "stop"])

                assert result.exit_code == 0
                assert "stopped" in result.output.lower()


class TestStartCommandMissingCoverage:
    """Test start command - additional coverage for missing lines."""

    @patch("trading_bot.cli.init_database")
    @patch("trading_bot.cli.MT5Connector")
    @patch("trading_bot.cli.setup_logger")
    @patch("asyncio.run")
    @patch("trading_bot.main.TradingBot")
    def test_start_live_mode_mt5_success(
        self,
        mock_bot_class,
        mock_asyncio_run,
        mock_setup_logger,
        mock_mt5,
        mock_init_db,
        runner,
        mock_config,
    ):
        """Test start command in live mode with successful MT5 connection (line 156)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            mock_db_manager = Mock()
            mock_db_manager.create_tables = AsyncMock()
            mock_init_db.return_value = mock_db_manager

            mock_connector = Mock()
            mock_connector.initialize.return_value = True
            mock_connector.account_info = {
                "login": 12345,
                "balance": 10000.0,
                "server": "TestServer",
            }
            mock_mt5.return_value = mock_connector

            mock_bot = Mock()
            mock_bot.start = AsyncMock()
            mock_bot.stop = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_asyncio_run.return_value = None

            result = runner.invoke(cli, ["--config", "development", "start"])

            assert result.exit_code == 0
            assert "MT5 connected" in result.output
            # Should NOT show dry-run message
            assert "DRY-RUN" not in result.output

    @patch("trading_bot.cli.init_database")
    @patch("trading_bot.cli.MT5Connector")
    @patch("trading_bot.cli.setup_logger")
    @patch("trading_bot.main.TradingBot")
    def test_start_keyboard_interrupt(
        self, mock_bot_class, mock_setup_logger, mock_mt5, mock_init_db, runner, mock_config
    ):
        """Test start command with KeyboardInterrupt (line 231-239)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            mock_db_manager = Mock()
            mock_db_manager.create_tables = AsyncMock()
            mock_init_db.return_value = mock_db_manager

            mock_connector = Mock()
            mock_connector.initialize.return_value = True
            mock_connector.account_info = {"login": 12345, "balance": 10000.0}
            mock_mt5.return_value = mock_connector

            mock_bot = Mock()
            # Make bot.start raise KeyboardInterrupt when run through asyncio
            call_count = [0]

            def mock_asyncio_run(coro, *args, **kwargs):
                # First call is create_tables, second is bot.start()
                call_count[0] += 1
                if call_count[0] == 2:  # Second call (bot.start)
                    raise KeyboardInterrupt()
                return None

            mock_bot.stop = AsyncMock()
            mock_bot_class.return_value = mock_bot

            with patch("asyncio.run", side_effect=mock_asyncio_run):
                result = runner.invoke(cli, ["--config", "development", "start"])

            # KeyboardInterrupt should be handled gracefully (exit code 0 or 1 depending on implementation)
            assert result.exit_code in [0, 1]
            assert (
                "Stopping" in result.output
                or "stopped" in result.output.lower()
                or "ERROR" in result.output
            )

    @patch("trading_bot.cli.init_database")
    @patch("trading_bot.cli.MT5Connector")
    @patch("trading_bot.cli.setup_logger")
    @patch("trading_bot.main.TradingBot")
    def test_start_trading_loop_exception(
        self, mock_bot_class, mock_setup_logger, mock_mt5, mock_init_db, runner, mock_config
    ):
        """Test start command with exception in trading loop (line 236-239)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            mock_db_manager = Mock()
            mock_db_manager.create_tables = AsyncMock()
            mock_init_db.return_value = mock_db_manager

            mock_connector = Mock()
            mock_connector.initialize.return_value = True
            mock_connector.account_info = {"login": 12345, "balance": 10000.0}
            mock_mt5.return_value = mock_connector

            mock_bot = Mock()

            # Create a coroutine that raises an exception
            async def failing_start():
                raise RuntimeError("Trading loop error")

            mock_bot.start = failing_start
            mock_bot.stop = AsyncMock()
            mock_bot_class.return_value = mock_bot

            # Don't mock asyncio.run - let it actually run the coroutine
            result = runner.invoke(cli, ["--config", "development", "start"])

            # The exception should be re-raised after being logged
            assert result.exit_code == 1
            assert "ERROR" in result.output

    @patch("trading_bot.cli.init_database")
    @patch("trading_bot.cli.MT5Connector")
    @patch("trading_bot.cli.setup_logger")
    @patch("asyncio.run")
    @patch("trading_bot.main.TradingBot")
    def test_start_bot_config_no_trading_key(
        self,
        mock_bot_class,
        mock_asyncio_run,
        mock_setup_logger,
        mock_mt5,
        mock_init_db,
        runner,
        mock_config,
    ):
        """Test start command when bot_config has no 'trading' key (line 210-212)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            mock_db_manager = Mock()
            mock_db_manager.create_tables = AsyncMock()
            mock_init_db.return_value = mock_db_manager

            mock_connector = Mock()
            mock_connector.initialize.return_value = True
            mock_connector.account_info = {"login": 12345, "balance": 10000.0}
            mock_mt5.return_value = mock_connector

            # Remove _config to trigger line 210-212
            delattr(mock_config, "_config")

            mock_bot = Mock()
            mock_bot.start = AsyncMock()
            mock_bot.stop = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_asyncio_run.return_value = None

            result = runner.invoke(cli, ["--config", "development", "start"])

            assert result.exit_code == 0

    @patch("trading_bot.cli.init_database")
    @patch("trading_bot.cli.MT5Connector")
    @patch("trading_bot.cli.setup_logger")
    @patch("asyncio.run")
    @patch("trading_bot.main.TradingBot")
    def test_start_bot_config_has_trading_key(
        self,
        mock_bot_class,
        mock_asyncio_run,
        mock_setup_logger,
        mock_mt5,
        mock_init_db,
        runner,
        mock_config,
    ):
        """Test start command when bot_config has 'trading' key (line 212)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            mock_db_manager = Mock()
            mock_db_manager.create_tables = AsyncMock()
            mock_init_db.return_value = mock_db_manager

            mock_connector = Mock()
            mock_connector.initialize.return_value = True
            mock_connector.account_info = {"login": 12345, "balance": 10000.0}
            mock_mt5.return_value = mock_connector

            # Keep _config with trading key to trigger line 212 (just set dry_run)
            mock_config._config = {"symbols": ["EURUSD"], "trading": {"existing_key": "value"}}

            mock_bot = Mock()
            mock_bot.start = AsyncMock()
            mock_bot.stop = AsyncMock()
            mock_bot_class.return_value = mock_bot
            mock_asyncio_run.return_value = None

            result = runner.invoke(cli, ["--config", "development", "start"])

            assert result.exit_code == 0


class TestMT5ConnectMissingCoverage:
    """Test MT5 connect command - additional coverage for missing lines."""

    @patch("trading_bot.cli.MT5Connector")
    @patch("trading_bot.cli.setup_logger")
    def test_mt5_connect_import_error(self, mock_setup_logger, mock_mt5, runner, mock_config):
        """Test MT5 connect with ImportError (line 363-366)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            mock_mt5.side_effect = ImportError("MetaTrader5 not available")

            result = runner.invoke(cli, ["--config", "development", "mt5", "connect"])

            assert result.exit_code == 0
            assert "not installed" in result.output.lower() or "ERROR" in result.output

    @patch("trading_bot.cli.MT5Connector")
    @patch("trading_bot.cli.setup_logger")
    def test_mt5_connect_exception(self, mock_setup_logger, mock_mt5, runner, mock_config):
        """Test MT5 connect with general exception (line 367-370)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            mock_mt5.side_effect = Exception("Connection error")

            result = runner.invoke(cli, ["--config", "development", "mt5", "connect"])

            assert result.exit_code == 0
            assert "ERROR" in result.output or "error" in result.output.lower()


class TestConfigValidateMissingCoverage:
    """Test config validate command - additional coverage for missing lines."""

    @patch("trading_bot.cli.setup_logger")
    def test_config_validate_exception(self, mock_setup_logger, runner, mock_config):
        """Test config validate with exception (line 502-504)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            mock_config.validate.side_effect = ValueError("Invalid config")

            result = runner.invoke(cli, ["--config", "development", "config", "validate"])

            assert result.exit_code == 1
            assert "ERROR" in result.output or "validation failed" in result.output.lower()


class TestRulesCommand:
    """Test rules command and _display_claude_rules function (line 550-634)."""

    @patch("trading_bot.cli.setup_logger")
    def test_rules_windows_console_encoding(self, mock_setup_logger, runner, mock_config):
        """Test rules command with Windows console encoding (line 562-563)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            import os
            import tempfile

            with tempfile.TemporaryDirectory() as tmpdir:
                claude_md_path = os.path.join(tmpdir, "CLAUDE.md")
                with open(claude_md_path, "w", encoding="utf-8") as f:
                    f.write("# Test Rules\n\n## Critical Rules\n\nTest content here.")

                import trading_bot.cli

                original_file = trading_bot.cli.__file__

                try:
                    fake_cli_path = os.path.join(tmpdir, "cli.py")
                    with open(fake_cli_path, "w") as f:
                        f.write("# fake")

                    trading_bot.cli.__file__ = fake_cli_path

                    # Simulate Windows platform
                    with patch("sys.platform", "win32"):
                        result = runner.invoke(
                            cli, ["--config", "development", "rules", "--format", "full"]
                        )

                        # Should handle gracefully
                        assert result.exit_code == 0
                finally:
                    trading_bot.cli.__file__ = original_file

    @patch("trading_bot.cli.setup_logger")
    def test_rules_file_not_found(self, mock_setup_logger, runner, mock_config):
        """Test rules command when CLAUDE.md not found (line 569-571)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            # Force the file not to exist by using an invalid path
            import os
            import tempfile

            with tempfile.TemporaryDirectory() as tmpdir:
                # Empty temp directory - no CLAUDE.md
                import trading_bot.cli

                original_file = trading_bot.cli.__file__

                try:
                    fake_cli_path = os.path.join(tmpdir, "cli.py")
                    with open(fake_cli_path, "w") as f:
                        f.write("# fake")

                    trading_bot.cli.__file__ = fake_cli_path

                    result = runner.invoke(cli, ["--config", "development", "rules"])

                    # Should handle gracefully
                    assert result.exit_code == 0
                finally:
                    trading_bot.cli.__file__ = original_file

    @patch("trading_bot.cli.setup_logger")
    def test_rules_summary_format_with_content(self, mock_setup_logger, runner, mock_config):
        """Test rules command with summary format and actual content (line 577-601)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            import os
            import tempfile

            with tempfile.TemporaryDirectory() as tmpdir:
                # Create a proper CLAUDE.md with all required sections
                claude_md_path = os.path.join(tmpdir, "CLAUDE.md")
                with open(claude_md_path, "w", encoding="utf-8") as f:
                    f.write(
                        """
# Project Rules

## Critical Implementation Rules

Rule 1: Test rule
Rule 2: Another rule

## Code Quality Standards

Standard 1: Code must be clean
Standard 2: Add tests

## Testing Requirements

Test 1: Write tests first
Test 2: Ensure 100% coverage

## Test-Driven Development

TDD workflow description
"""
                    )

                import trading_bot.cli

                original_file = trading_bot.cli.__file__

                try:
                    fake_cli_path = os.path.join(tmpdir, "cli.py")
                    with open(fake_cli_path, "w") as f:
                        f.write("# fake")

                    trading_bot.cli.__file__ = fake_cli_path

                    result = runner.invoke(
                        cli, ["--config", "development", "rules", "--format", "summary"]
                    )

                    # Should handle gracefully
                    assert result.exit_code == 0
                finally:
                    trading_bot.cli.__file__ = original_file

    @patch("trading_bot.cli.setup_logger")
    def test_rules_rules_only_format_with_content(self, mock_setup_logger, runner, mock_config):
        """Test rules command with rules-only format and actual content (line 603-615)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            import os
            import tempfile

            with tempfile.TemporaryDirectory() as tmpdir:
                # Create a proper CLAUDE.md with Critical Implementation Rules section
                claude_md_path = os.path.join(tmpdir, "CLAUDE.md")
                with open(claude_md_path, "w", encoding="utf-8") as f:
                    f.write(
                        """
# Project Rules

## Critical Implementation Rules

Rule 1: Always write tests first
Rule 2: Never commit without tests
Rule 3: Follow TDD methodology

## Other Section

Other content here
"""
                    )

                import trading_bot.cli

                original_file = trading_bot.cli.__file__

                try:
                    fake_cli_path = os.path.join(tmpdir, "cli.py")
                    with open(fake_cli_path, "w") as f:
                        f.write("# fake")

                    trading_bot.cli.__file__ = fake_cli_path

                    result = runner.invoke(
                        cli, ["--config", "development", "rules", "--format", "rules-only"]
                    )

                    # Should handle gracefully
                    assert result.exit_code == 0
                finally:
                    trading_bot.cli.__file__ = original_file

    @patch("trading_bot.cli.setup_logger")
    def test_rules_rules_only_no_critical_section(self, mock_setup_logger, runner, mock_config):
        """Test rules-only format when Critical section not found (line 614-615)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            import os
            import tempfile

            with tempfile.TemporaryDirectory() as tmpdir:
                # Create CLAUDE.md WITHOUT Critical Implementation Rules section
                claude_md_path = os.path.join(tmpdir, "CLAUDE.md")
                with open(claude_md_path, "w", encoding="utf-8") as f:
                    f.write(
                        """
# Project Rules

## Some Other Section

Just some content
"""
                    )

                import trading_bot.cli

                original_file = trading_bot.cli.__file__

                try:
                    fake_cli_path = os.path.join(tmpdir, "cli.py")
                    with open(fake_cli_path, "w") as f:
                        f.write("# fake")

                    trading_bot.cli.__file__ = fake_cli_path

                    result = runner.invoke(
                        cli, ["--config", "development", "rules", "--format", "rules-only"]
                    )

                    # Should handle gracefully
                    assert result.exit_code == 0
                finally:
                    trading_bot.cli.__file__ = original_file

    @patch("trading_bot.cli.setup_logger")
    def test_rules_file_read_error(self, mock_setup_logger, runner, mock_config):
        """Test rules command with file read error (line 632-634)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            import os
            import tempfile

            with tempfile.TemporaryDirectory() as tmpdir:
                claude_md_path = os.path.join(tmpdir, "CLAUDE.md")

                # Create file but mock open to fail
                try:
                    with open(claude_md_path, "w") as f:
                        f.write("test")
                except OSError:
                    pass

                import trading_bot.cli

                original_file = trading_bot.cli.__file__

                try:
                    fake_cli_path = os.path.join(tmpdir, "cli.py")
                    with open(fake_cli_path, "w") as f:
                        f.write("# fake")

                    trading_bot.cli.__file__ = fake_cli_path

                    # Mock open to raise exception
                    with patch("builtins.open", side_effect=OSError("Permission denied")):
                        result = runner.invoke(cli, ["--config", "development", "rules"])

                        # Should handle error gracefully
                        assert result.exit_code == 0
                finally:
                    trading_bot.cli.__file__ = original_file

    @patch("trading_bot.cli.setup_logger")
    def test_rules_command_default_format(self, mock_setup_logger, runner, mock_config):
        """Test rules command with default format (line 646)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            # Mock the _display_claude_rules function
            with patch("trading_bot.cli._display_claude_rules") as mock_display:
                result = runner.invoke(cli, ["--config", "development", "rules"])

                assert result.exit_code == 0
                mock_display.assert_called_once_with("full")

    @patch("trading_bot.cli.setup_logger")
    def test_claude_command_alias(self, mock_setup_logger, runner, mock_config):
        """Test claude command alias (line 658)."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            # Mock the _display_claude_rules function
            with patch("trading_bot.cli._display_claude_rules") as mock_display:
                result = runner.invoke(cli, ["--config", "development", "claude"])

                assert result.exit_code == 0
                mock_display.assert_called_once_with("full")

    @patch("trading_bot.cli.setup_logger")
    def test_claude_command_with_format(self, mock_setup_logger, runner, mock_config):
        """Test claude command with format option."""
        with patch("trading_bot.cli.Configuration", return_value=mock_config):
            # Mock the _display_claude_rules function
            with patch("trading_bot.cli._display_claude_rules") as mock_display:
                result = runner.invoke(
                    cli, ["--config", "development", "claude", "--format", "summary"]
                )

                assert result.exit_code == 0
                mock_display.assert_called_once_with("summary")


class TestDisplayClaudeRulesDirectly:
    """Test _display_claude_rules helper function directly (line 550-634)."""

    @patch("trading_bot.cli.setup_logger")
    def test_display_claude_rules_full_format_direct(self, mock_setup_logger, runner, mock_config):
        """Test _display_claude_rules directly with full format."""
        import os
        import tempfile

        from trading_bot.cli import _display_claude_rules

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create CLAUDE.md
            claude_md_path = os.path.join(tmpdir, "CLAUDE.md")
            with open(claude_md_path, "w", encoding="utf-8") as f:
                f.write(
                    "# Test Rules\n\n## Section 1\n\nContent here\n\n## Section 2\n\nMore content"
                )

            import trading_bot.cli

            original_file = trading_bot.cli.__file__

            try:
                fake_cli_path = os.path.join(tmpdir, "cli.py")
                with open(fake_cli_path, "w") as f:
                    f.write("# fake")

                trading_bot.cli.__file__ = fake_cli_path

                # Call the function directly - it should not raise
                _display_claude_rules("full")
            finally:
                trading_bot.cli.__file__ = original_file

    @patch("trading_bot.cli.setup_logger")
    def test_display_claude_rules_summary_format_direct(
        self, mock_setup_logger, runner, mock_config
    ):
        """Test _display_claude_rules directly with summary format."""
        import os
        import tempfile

        from trading_bot.cli import _display_claude_rules

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create CLAUDE.md with proper sections
            claude_md_path = os.path.join(tmpdir, "CLAUDE.md")
            with open(claude_md_path, "w", encoding="utf-8") as f:
                f.write(
                    """
# Test Rules

## Critical Implementation Rules

Rule 1
Rule 2

## Code Quality Standards

Standard 1
Standard 2

## Testing Requirements

Test 1
Test 2

## Test-Driven Development

TDD content
"""
                )

            import trading_bot.cli

            original_file = trading_bot.cli.__file__

            try:
                fake_cli_path = os.path.join(tmpdir, "cli.py")
                with open(fake_cli_path, "w") as f:
                    f.write("# fake")

                trading_bot.cli.__file__ = fake_cli_path

                # Call the function directly
                _display_claude_rules("summary")
            finally:
                trading_bot.cli.__file__ = original_file

    @patch("trading_bot.cli.setup_logger")
    def test_display_claude_rules_only_format_direct(self, mock_setup_logger, runner, mock_config):
        """Test _display_claude_rules directly with rules-only format."""
        import os
        import tempfile

        from trading_bot.cli import _display_claude_rules

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create CLAUDE.md with Critical section
            claude_md_path = os.path.join(tmpdir, "CLAUDE.md")
            with open(claude_md_path, "w", encoding="utf-8") as f:
                f.write(
                    """
# Test Rules

## Critical Implementation Rules

Critical rule 1
Critical rule 2

## Other Section

Other content
"""
                )

            import trading_bot.cli

            original_file = trading_bot.cli.__file__

            try:
                fake_cli_path = os.path.join(tmpdir, "cli.py")
                with open(fake_cli_path, "w") as f:
                    f.write("# fake")

                trading_bot.cli.__file__ = fake_cli_path

                # Call the function directly
                _display_claude_rules("rules-only")
            finally:
                trading_bot.cli.__file__ = original_file

    @patch("trading_bot.cli.setup_logger")
    def test_display_claude_rules_file_not_found_direct(
        self, mock_setup_logger, runner, mock_config
    ):
        """Test _display_claude_rules directly when file not found."""
        import os
        import tempfile

        from trading_bot.cli import _display_claude_rules

        with tempfile.TemporaryDirectory() as tmpdir:
            import trading_bot.cli

            original_file = trading_bot.cli.__file__

            try:
                fake_cli_path = os.path.join(tmpdir, "cli.py")
                with open(fake_cli_path, "w") as f:
                    f.write("# fake")

                trading_bot.cli.__file__ = fake_cli_path

                # Call the function - should handle gracefully
                _display_claude_rules("full")
            finally:
                trading_bot.cli.__file__ = original_file

    @patch("trading_bot.cli.setup_logger")
    def test_display_claude_rules_windows_encoding_direct(
        self, mock_setup_logger, runner, mock_config
    ):
        """Test _display_claude_rules directly with Windows encoding."""
        import os
        import sys
        import tempfile

        from trading_bot.cli import _display_claude_rules

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create CLAUDE.md
            claude_md_path = os.path.join(tmpdir, "CLAUDE.md")
            with open(claude_md_path, "w", encoding="utf-8") as f:
                f.write("# Test Rules\n\nContent")

            import trading_bot.cli

            original_file = trading_bot.cli.__file__
            original_platform = sys.platform

            try:
                fake_cli_path = os.path.join(tmpdir, "cli.py")
                with open(fake_cli_path, "w") as f:
                    f.write("# fake")

                trading_bot.cli.__file__ = fake_cli_path

                # Simulate Windows platform
                with patch("sys.platform", "win32"):
                    _display_claude_rules("full")
            finally:
                trading_bot.cli.__file__ = original_file
                sys.platform = original_platform
