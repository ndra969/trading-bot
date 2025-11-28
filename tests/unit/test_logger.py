"""
Unit tests for logging system.

Tests logger setup and functionality.
"""

from trading_bot.utils.logger import get_logger, setup_logger


class TestLogger:
    """Test logging system."""

    def test_setup_logger(self, tmp_path):
        """Test logger setup."""
        log_file = tmp_path / "test.log"

        setup_logger(
            log_file=str(log_file),
            level="DEBUG",
            rotation="1 MB",
            retention=3,
        )

        # Logger should be configured
        logger = get_logger("test")
        logger.info("Test message")

        # Log file should be created
        assert log_file.exists()

    def test_get_logger(self):
        """Test getting logger instance."""
        logger = get_logger("test_module")

        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")
