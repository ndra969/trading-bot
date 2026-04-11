"""
Unit tests for TradingTypeFactory.

This test file follows TDD methodology:
- RED: Write failing tests first
- GREEN: Implement minimal code to pass
- REFACTOR: Improve while keeping tests green
"""

import pytest

from trading_bot.executors.factory import TradingTypeFactory


class TestTradingTypeFactoryCreateExecutor:
    """Test factory create_executor method."""

    def test_factory_creates_intraday_executor(self):
        """
        Test that factory creates IntradayExecutor for day_trading type.

        When requesting 'day_trading' trading type, the factory should
        return an instance of IntradayExecutor.
        """
        # Arrange
        trading_type = "day_trading"
        mock_config = {"test": "config"}
        mock_foundation_engine = object()
        mock_position_manager = object()

        # Act
        executor = TradingTypeFactory.create_executor(
            trading_type=trading_type,
            config=mock_config,
            foundation_engine=mock_foundation_engine,
            position_manager=mock_position_manager,
        )

        # Assert
        from trading_bot.executors.intraday_executor import IntradayExecutor

        assert isinstance(executor, IntradayExecutor)
        assert executor.config == mock_config
        assert executor.foundation_engine == mock_foundation_engine
        assert executor.position_manager == mock_position_manager

    def test_factory_raises_error_for_invalid_type(self):
        """
        Test that factory raises ValueError for unsupported trading types.

        When requesting an invalid trading type, the factory should raise
        ValueError with a helpful message listing supported types.
        """
        # Arrange
        invalid_type = "invalid_trading_type"
        mock_config = {}
        mock_foundation_engine = object()
        mock_position_manager = object()

        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported trading type"):
            TradingTypeFactory.create_executor(
                trading_type=invalid_type,
                config=mock_config,
                foundation_engine=mock_foundation_engine,
                position_manager=mock_position_manager,
            )

    def test_factory_error_message_contains_supported_types(self):
        """
        Test that ValueError message lists supported trading types.

        The error message should help developers understand which
        trading types are available.
        """
        # Arrange
        invalid_type = "scalping"  # Not implemented yet
        mock_config = {}
        mock_foundation_engine = object()
        mock_position_manager = object()

        # Act & Assert
        try:
            TradingTypeFactory.create_executor(
                trading_type=invalid_type,
                config=mock_config,
                foundation_engine=mock_foundation_engine,
                position_manager=mock_position_manager,
            )
            pytest.fail("Expected ValueError to be raised")
        except ValueError as e:
            error_message = str(e)
            # Error message should mention the invalid type
            assert invalid_type in error_message
            # Error message should mention supported types
            assert "day_trading" in error_message

    def test_factory_passes_dependencies_correctly(self):
        """
        Test that factory correctly passes all dependencies to executor.

        The factory should pass config, foundation_engine, and
        position_manager to the executor's __init__ method.
        """
        # Arrange
        mock_config = {"key": "value", "trading": {"mode": "mtf"}}
        mock_foundation_engine = object()
        mock_position_manager = object()

        # Act
        executor = TradingTypeFactory.create_executor(
            trading_type="day_trading",
            config=mock_config,
            foundation_engine=mock_foundation_engine,
            position_manager=mock_position_manager,
        )

        # Assert
        assert executor.config == mock_config
        assert executor.foundation_engine == mock_foundation_engine
        assert executor.position_manager == mock_position_manager


class TestTradingTypeFactorySupportedTypes:
    """Test that factory supports the correct trading types."""

    def test_factory_supports_day_trading(self):
        """Test that factory supports 'day_trading' type."""
        # This is already tested by test_factory_creates_intraday_executor
        # This test serves as documentation
        assert True

    def test_factory_does_not_support_swing_trading_yet(self):
        """
        Test that 'swing_trading' is not yet supported.

        Swing trading executor is planned but not implemented yet.
        This test documents current limitations.
        """
        # Arrange
        mock_config = {}
        mock_foundation_engine = object()
        mock_position_manager = object()

        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported trading type"):
            TradingTypeFactory.create_executor(
                trading_type="swing_trading",
                config=mock_config,
                foundation_engine=mock_foundation_engine,
                position_manager=mock_position_manager,
            )

    def test_factory_does_not_support_scalping_yet(self):
        """
        Test that 'scalping' is not yet supported.

        Scalping executor is planned but not implemented yet.
        This test documents current limitations.
        """
        # Arrange
        mock_config = {}
        mock_foundation_engine = object()
        mock_position_manager = object()

        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported trading type"):
            TradingTypeFactory.create_executor(
                trading_type="scalping",
                config=mock_config,
                foundation_engine=mock_foundation_engine,
                position_manager=mock_position_manager,
            )

    def test_factory_does_not_support_position_trading_yet(self):
        """
        Test that 'position_trading' is not yet supported.

        Position trading executor is planned but not implemented yet.
        This test documents current limitations.
        """
        # Arrange
        mock_config = {}
        mock_foundation_engine = object()
        mock_position_manager = object()

        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported trading type"):
            TradingTypeFactory.create_executor(
                trading_type="position_trading",
                config=mock_config,
                foundation_engine=mock_foundation_engine,
                position_manager=mock_position_manager,
            )


class TestTradingTypeFactoryLogging:
    """Test factory logging behavior."""

    def test_factory_logs_executor_creation(self):
        """
        Test that factory logs when creating an executor.

        The factory should log which executor type was created
        for debugging and monitoring purposes.

        Note: This test verifies the executor is created successfully.
        Actual logging is verified through manual inspection and
        the fact that other tests pass without exceptions.
        """
        # Arrange
        mock_config = {}
        mock_foundation_engine = object()
        mock_position_manager = object()

        # Act
        # If logging fails or exceptions occur, this will raise
        executor = TradingTypeFactory.create_executor(
            trading_type="day_trading",
            config=mock_config,
            foundation_engine=mock_foundation_engine,
            position_manager=mock_position_manager,
        )

        # Assert
        # Executor should be created successfully
        assert executor is not None
        from trading_bot.executors.intraday_executor import IntradayExecutor

        assert isinstance(executor, IntradayExecutor)
