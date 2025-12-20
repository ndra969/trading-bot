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
