"""
Unit tests for Base Executor abstract class.

This test file follows TDD methodology:
- RED: Write failing tests first
- GREEN: Implement minimal code to pass
- REFACTOR: Improve while keeping tests green
"""

import pytest

from trading_bot.executors.base_executor import TradingTypeExecutor


class TestBaseExecutorAbstractClass:
    """Test that TradingTypeExecutor is properly abstract."""

    def test_base_executor_cannot_be_instantiated(self):
        """
        Test that TradingTypeExecutor cannot be instantiated directly.

        This test ensures that the base executor class is properly abstract
        and cannot be used directly without implementing required methods.
        """
        # Arrange & Act & Assert
        with pytest.raises(TypeError, match="abstract"):
            TradingTypeExecutor(config={}, foundation_engine=None, position_manager=None)

    def test_base_executor_requires_initialize_method(self):
        """
        Test that subclass must implement initialize() method.

        The initialize() method should be abstract and required for all
        executor implementations.
        """

        # Arrange
        class IncompleteExecutor(TradingTypeExecutor):
            """Missing initialize() method."""

            async def execute_trading_loop(self, symbols):
                pass

            async def analyze_symbol(self, symbol, current_time):
                pass

            def get_timeframes(self):
                pass

            def get_technical_indicators(self):
                pass

        # Act & Assert
        with pytest.raises(TypeError, match="abstract"):
            IncompleteExecutor(config={}, foundation_engine=None, position_manager=None)

    def test_base_executor_requires_execute_trading_loop_method(self):
        """
        Test that subclass must implement execute_trading_loop() method.

        This is the main method that runs the trading loop.
        """

        # Arrange
        class IncompleteExecutor(TradingTypeExecutor):
            """Missing execute_trading_loop() method."""

            async def initialize(self):
                pass

            async def analyze_symbol(self, symbol, current_time):
                pass

            def get_timeframes(self):
                pass

            def get_technical_indicators(self):
                pass

        # Act & Assert
        with pytest.raises(TypeError, match="abstract"):
            IncompleteExecutor(config={}, foundation_engine=None, position_manager=None)

    def test_base_executor_requires_analyze_symbol_method(self):
        """
        Test that subclass must implement analyze_symbol() method.

        This method analyzes a single symbol for trading opportunities.
        """

        # Arrange
        class IncompleteExecutor(TradingTypeExecutor):
            """Missing analyze_symbol() method."""

            async def initialize(self):
                pass

            async def execute_trading_loop(self, symbols):
                pass

            def get_timeframes(self):
                pass

            def get_technical_indicators(self):
                pass

        # Act & Assert
        with pytest.raises(TypeError, match="abstract"):
            IncompleteExecutor(config={}, foundation_engine=None, position_manager=None)

    def test_base_executor_requires_get_timeframes_method(self):
        """
        Test that subclass must implement get_timeframes() method.

        This method returns the timeframes used by this executor.
        """

        # Arrange
        class IncompleteExecutor(TradingTypeExecutor):
            """Missing get_timeframes() method."""

            async def initialize(self):
                pass

            async def execute_trading_loop(self, symbols):
                pass

            async def analyze_symbol(self, symbol, current_time):
                pass

            def get_technical_indicators(self):
                pass

        # Act & Assert
        with pytest.raises(TypeError, match="abstract"):
            IncompleteExecutor(config={}, foundation_engine=None, position_manager=None)

    def test_base_executor_requires_get_technical_indicators_method(self):
        """
        Test that subclass must implement get_technical_indicators() method.

        This method returns the technical indicators configuration.
        """

        # Arrange
        class IncompleteExecutor(TradingTypeExecutor):
            """Missing get_technical_indicators() method."""

            async def initialize(self):
                pass

            async def execute_trading_loop(self, symbols):
                pass

            async def analyze_symbol(self, symbol, current_time):
                pass

            def get_timeframes(self):
                pass

        # Act & Assert
        with pytest.raises(TypeError, match="abstract"):
            IncompleteExecutor(config={}, foundation_engine=None, position_manager=None)


class TestBaseExecutorInitialization:
    """Test that a complete subclass can be initialized."""

    def test_base_executor_initializes_with_config(self):
        """
        Test that a complete subclass can be instantiated with config.

        This test verifies that all dependencies are properly stored.
        """
        # Arrange
        mock_config = {"test": "config"}
        mock_foundation_engine = object()
        mock_position_manager = object()

        # Act
        class CompleteExecutor(TradingTypeExecutor):
            """Complete implementation of all abstract methods."""

            def __init__(self, config, foundation_engine, position_manager):
                super().__init__(config, foundation_engine, position_manager)
                self.config_received = config
                self.foundation_engine_received = foundation_engine
                self.position_manager_received = position_manager

            async def initialize(self):
                pass

            async def execute_trading_loop(self, symbols):
                pass

            async def analyze_symbol(self, symbol, current_time):
                pass

            def get_timeframes(self):
                return {}

            def get_technical_indicators(self):
                return {}

        executor = CompleteExecutor(
            config=mock_config,
            foundation_engine=mock_foundation_engine,
            position_manager=mock_position_manager,
        )

        # Assert
        assert executor.config_received == mock_config
        assert executor.foundation_engine_received == mock_foundation_engine
        assert executor.position_manager_received == mock_position_manager

    def test_base_executor_stores_dependencies(self):
        """
        Test that dependencies are accessible as instance attributes.

        Subclasses should be able to access config, foundation_engine,
        and position_manager via self.
        """
        # Arrange
        mock_config = {"key": "value"}
        mock_foundation_engine = object()
        mock_position_manager = object()

        # Act
        class CompleteExecutor(TradingTypeExecutor):
            """Complete implementation."""

            async def initialize(self):
                return self.config

            async def execute_trading_loop(self, symbols):
                return self.foundation_engine

            async def analyze_symbol(self, symbol, current_time):
                return self.position_manager

            def get_timeframes(self):
                return {}

            def get_technical_indicators(self):
                return {}

        executor = CompleteExecutor(
            config=mock_config,
            foundation_engine=mock_foundation_engine,
            position_manager=mock_position_manager,
        )

        # Assert
        assert executor.config == mock_config
        assert executor.foundation_engine == mock_foundation_engine
        assert executor.position_manager == mock_position_manager


class TestBaseExecutorAbstractMethodsSignature:
    """Test that abstract methods have correct signatures."""

    def test_initialize_is_async(self):
        """
        Test that initialize() is an async method.

        This ensures proper async/await support in subclasses.
        """

        # Arrange & Act
        class CompleteExecutor(TradingTypeExecutor):
            async def initialize(self):
                pass

            async def execute_trading_loop(self, symbols):
                pass

            async def analyze_symbol(self, symbol, current_time):
                pass

            def get_timeframes(self):
                return {}

            def get_technical_indicators(self):
                return {}

        executor = CompleteExecutor(config={}, foundation_engine=None, position_manager=None)

        # Assert
        import inspect

        assert inspect.iscoroutinefunction(executor.initialize)

    def test_execute_trading_loop_is_async(self):
        """Test that execute_trading_loop() is an async method."""

        # Arrange & Act
        class CompleteExecutor(TradingTypeExecutor):
            async def initialize(self):
                pass

            async def execute_trading_loop(self, symbols):
                pass

            async def analyze_symbol(self, symbol, current_time):
                pass

            def get_timeframes(self):
                return {}

            def get_technical_indicators(self):
                return {}

        executor = CompleteExecutor(config={}, foundation_engine=None, position_manager=None)

        # Assert
        import inspect

        assert inspect.iscoroutinefunction(executor.execute_trading_loop)

    def test_analyze_symbol_is_async(self):
        """Test that analyze_symbol() is an async method."""

        # Arrange & Act
        class CompleteExecutor(TradingTypeExecutor):
            async def initialize(self):
                pass

            async def execute_trading_loop(self, symbols):
                pass

            async def analyze_symbol(self, symbol, current_time):
                pass

            def get_timeframes(self):
                return {}

            def get_technical_indicators(self):
                return {}

        executor = CompleteExecutor(config={}, foundation_engine=None, position_manager=None)

        # Assert
        import inspect

        assert inspect.iscoroutinefunction(executor.analyze_symbol)

    def test_get_timeframes_returns_dict(self):
        """
        Test that get_timeframes() returns a dictionary.

        Timeframes should be returned as a dict with keys like
        'zone_timeframe', 'entry_timeframe', 'trend_timeframe'.
        """

        # Arrange & Act
        class CompleteExecutor(TradingTypeExecutor):
            async def initialize(self):
                pass

            async def execute_trading_loop(self, symbols):
                pass

            async def analyze_symbol(self, symbol, current_time):
                pass

            def get_timeframes(self):
                return {"zone_timeframe": "H1", "entry_timeframe": "M30"}

            def get_technical_indicators(self):
                return {}

        executor = CompleteExecutor(config={}, foundation_engine=None, position_manager=None)

        # Assert
        assert isinstance(executor.get_timeframes(), dict)

    def test_get_technical_indicators_returns_dict(self):
        """
        Test that get_technical_indicators() returns a dictionary.

        Technical indicators should be returned as a dict with
        indicator configurations (EMA, RSI, etc.).
        """

        # Arrange & Act
        class CompleteExecutor(TradingTypeExecutor):
            async def initialize(self):
                pass

            async def execute_trading_loop(self, symbols):
                pass

            async def analyze_symbol(self, symbol, current_time):
                pass

            def get_timeframes(self):
                return {}

            def get_technical_indicators(self):
                return {"ema": {"fast": 20, "slow": 50}}

        executor = CompleteExecutor(config={}, foundation_engine=None, position_manager=None)

        # Assert
        assert isinstance(executor.get_technical_indicators(), dict)
