"""
Unit tests for SupplyDemandStrategy.

Testing supply & demand strategy with TDD methodology.
"""

import pandas as pd
import pytest
import pytest_asyncio

from trading_bot.strategies.foundation.supply_demand import SupplyDemandStrategy


class TestSupplyDemandStrategyInitialization:
    """Test SupplyDemandStrategy initialization."""

    def test_supply_demand_strategy_initialization_default(self):
        """Test strategy with default parameters."""
        strategy = SupplyDemandStrategy(use_database=False)  # Disable database for unit tests
        assert strategy is not None
        assert hasattr(strategy, "detector")
        assert hasattr(strategy, "manager")
        assert hasattr(strategy, "analyzer")

    def test_supply_demand_strategy_initialization_with_config(self):
        """Test strategy with custom configuration."""
        config = {
            "zone_detection": {"min_zone_strength": 70.0},
            "analysis": {"min_zone_strength": 65.0},
        }
        strategy = SupplyDemandStrategy(
            config=config, use_database=False
        )  # Disable database for unit tests
        assert strategy.detector.min_zone_strength == 70.0
        assert strategy.analyzer.min_zone_strength == 65.0

    def test_supply_demand_strategy_initialization_empty_config(self):
        """Test strategy with empty config uses defaults."""
        strategy = SupplyDemandStrategy(
            config={}, use_database=False
        )  # Disable database for unit tests
        assert strategy.detector is not None
        assert strategy.manager is not None
        assert strategy.analyzer is not None


class TestSupplyDemandStrategyAnalyze:
    """Test strategy analysis functionality."""

    @pytest.fixture
    def sample_ohlcv_data(self):
        """Create sample OHLCV data."""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="1h")
        return pd.DataFrame(
            {
                "open": [1.1000] * 100,
                "high": [1.1010] * 100,
                "low": [1.0990] * 100,
                "close": [1.1000] * 100,
                "volume": [1000] * 100,
            },
            index=dates,
        )

    @pytest.mark.asyncio
    async def test_analyze_detects_zones(self, sample_ohlcv_data):
        """Test that analyze detects zones from data."""
        strategy = SupplyDemandStrategy(
            config={
                "zone_detection": {
                    "min_zone_strength": 30.0,
                    "min_zone_size_pips": 2,
                },
                "analysis": {"min_zone_strength": 30.0},
            },
            use_database=False,  # Disable database for unit tests
        )

        zones = await strategy.analyze("EURUSD", sample_ohlcv_data, "H1")
        assert isinstance(zones, list)

    @pytest.mark.asyncio
    async def test_analyze_stores_zones_in_manager(self, sample_ohlcv_data):
        """Test that detected zones are stored in manager."""
        strategy = SupplyDemandStrategy(
            config={
                "zone_detection": {
                    "min_zone_strength": 30.0,
                    "min_zone_size_pips": 2,
                },
                "analysis": {"min_zone_strength": 30.0},
            },
            use_database=False,  # Disable database for unit tests
        )

        await strategy.analyze("EURUSD", sample_ohlcv_data, "H1")

        # Zones should be stored
        stored_zones = strategy.get_zones("EURUSD")
        assert isinstance(stored_zones, list)

    @pytest.mark.asyncio
    async def test_analyze_returns_quality_zones(self, sample_ohlcv_data):
        """Test that analyze returns only quality zones."""
        strategy = SupplyDemandStrategy(
            config={
                "zone_detection": {
                    "min_zone_strength": 30.0,
                    "min_zone_size_pips": 2,
                },
                "analysis": {"min_zone_strength": 60.0},  # Higher threshold
            },
            use_database=False,  # Disable database for unit tests
        )

        zones = await strategy.analyze("EURUSD", sample_ohlcv_data, "H1")

        # All returned zones should meet quality threshold
        for zone in zones:
            assert zone.strength >= 60.0

    @pytest.mark.asyncio
    async def test_analyze_handles_errors_gracefully(self):
        """Test that analyze handles errors without crashing."""
        strategy = SupplyDemandStrategy(use_database=False)  # Disable database for unit tests

        # Invalid data (too short)
        invalid_data = pd.DataFrame(
            {
                "open": [1.1000] * 5,
                "high": [1.1010] * 5,
                "low": [1.0990] * 5,
                "close": [1.1000] * 5,
                "volume": [1000] * 5,
            }
        )

        # Should return empty list, not raise exception
        zones = await strategy.analyze("EURUSD", invalid_data, "H1")
        assert isinstance(zones, list)
        assert len(zones) == 0

    @pytest.mark.asyncio
    async def test_analyze_multiple_symbols(self, sample_ohlcv_data):
        """Test analyzing multiple symbols independently."""
        strategy = SupplyDemandStrategy(
            config={
                "zone_detection": {
                    "min_zone_strength": 30.0,
                    "min_zone_size_pips": 2,
                },
                "analysis": {"min_zone_strength": 30.0},
            },
            use_database=False,  # Disable database for unit tests
        )

        # Analyze first symbol
        zones1 = await strategy.analyze("EURUSD", sample_ohlcv_data, "H1")

        # Analyze second symbol
        zones2 = await strategy.analyze("GBPUSD", sample_ohlcv_data, "H1")

        # Both should work independently
        assert isinstance(zones1, list)
        assert isinstance(zones2, list)

        # Zones should be stored separately
        eurusd_zones = strategy.get_zones("EURUSD")
        gbpusd_zones = strategy.get_zones("GBPUSD")
        assert isinstance(eurusd_zones, list)
        assert isinstance(gbpusd_zones, list)


class TestSupplyDemandStrategyGetZones:
    """Test getting zones from strategy."""

    @pytest_asyncio.fixture
    async def strategy_with_zones(self, sample_ohlcv_data):
        """Create strategy with analyzed zones."""
        strategy = SupplyDemandStrategy(
            config={
                "zone_detection": {
                    "min_zone_strength": 30.0,
                    "min_zone_size_pips": 2,
                },
                "analysis": {"min_zone_strength": 30.0},
            },
            use_database=False,  # Disable database for unit tests
        )
        await strategy.analyze("EURUSD", sample_ohlcv_data, "H1")
        return strategy

    @pytest.fixture
    def sample_ohlcv_data(self):
        """Create sample OHLCV data."""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="1h")
        return pd.DataFrame(
            {
                "open": [1.1000] * 100,
                "high": [1.1010] * 100,
                "low": [1.0990] * 100,
                "close": [1.1000] * 100,
                "volume": [1000] * 100,
            },
            index=dates,
        )

    def test_get_zones_returns_stored_zones(self, strategy_with_zones):
        """Test that get_zones returns stored zones."""
        zones = strategy_with_zones.get_zones("EURUSD")
        assert isinstance(zones, list)

    def test_get_zones_nonexistent_symbol(self, strategy_with_zones):
        """Test getting zones for non-existent symbol."""
        zones = strategy_with_zones.get_zones("GBPUSD")
        assert isinstance(zones, list)
        assert len(zones) == 0

    @pytest.mark.asyncio
    async def test_get_zones_after_multiple_analyses(self, sample_ohlcv_data):
        """Test getting zones after multiple analyses."""
        strategy = SupplyDemandStrategy(
            config={
                "zone_detection": {
                    "min_zone_strength": 30.0,
                    "min_zone_size_pips": 2,
                },
                "analysis": {"min_zone_strength": 30.0},
            },
            use_database=False,  # Disable database for unit tests
        )

        # Analyze multiple times
        await strategy.analyze("EURUSD", sample_ohlcv_data, "H1")
        await strategy.analyze("EURUSD", sample_ohlcv_data, "H1")

        zones = strategy.get_zones("EURUSD")
        assert isinstance(zones, list)


class TestSupplyDemandStrategyIntegration:
    """Test strategy component integration."""

    def test_strategy_components_initialized(self):
        """Test that all components are properly initialized."""
        strategy = SupplyDemandStrategy(use_database=False)  # Disable database for unit tests

        # Check detector
        assert hasattr(strategy.detector, "detect_zones")

        # Check manager
        assert hasattr(strategy.manager, "add_zones")
        assert hasattr(strategy.manager, "get_zones")

        # Check analyzer
        assert hasattr(strategy.analyzer, "analyze_zones")

    @pytest.mark.asyncio
    async def test_strategy_workflow(self, sample_ohlcv_data):
        """Test complete strategy workflow."""
        strategy = SupplyDemandStrategy(
            config={
                "zone_detection": {
                    "min_zone_strength": 30.0,
                    "min_zone_size_pips": 2,
                },
                "analysis": {"min_zone_strength": 30.0},
            },
            use_database=False,  # Disable database for unit tests
        )

        # Analyze
        quality_zones = await strategy.analyze("EURUSD", sample_ohlcv_data, "H1")

        # Get zones
        all_zones = strategy.get_zones("EURUSD")

        # Verify workflow
        assert isinstance(quality_zones, list)
        assert isinstance(all_zones, list)

    @pytest.fixture
    def sample_ohlcv_data(self):
        """Create sample OHLCV data."""
        dates = pd.date_range(start="2024-01-01", periods=100, freq="1h")
        return pd.DataFrame(
            {
                "open": [1.1000] * 100,
                "high": [1.1010] * 100,
                "low": [1.0990] * 100,
                "close": [1.1000] * 100,
                "volume": [1000] * 100,
            },
            index=dates,
        )


class TestSupplyDemandStrategyEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_analyze_empty_dataframe(self):
        """Test analyzing empty DataFrame."""
        strategy = SupplyDemandStrategy(use_database=False)  # Disable database for unit tests
        empty_data = pd.DataFrame()

        zones = await strategy.analyze("EURUSD", empty_data, "H1")
        assert isinstance(zones, list)
        assert len(zones) == 0

    @pytest.mark.asyncio
    async def test_analyze_missing_columns(self):
        """Test analyzing data with missing columns."""
        strategy = SupplyDemandStrategy(use_database=False)  # Disable database for unit tests
        invalid_data = pd.DataFrame({"open": [1.1000] * 50})

        # Should handle error gracefully
        zones = await strategy.analyze("EURUSD", invalid_data, "H1")
        assert isinstance(zones, list)

    def test_get_zones_before_analysis(self):
        """Test getting zones before any analysis."""
        strategy = SupplyDemandStrategy(use_database=False)  # Disable database for unit tests

        zones = strategy.get_zones("EURUSD")
        assert isinstance(zones, list)
        assert len(zones) == 0
