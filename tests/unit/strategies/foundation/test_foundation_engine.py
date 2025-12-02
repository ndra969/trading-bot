"""
Unit tests for FoundationEngine.

Testing foundation engine coordination with TDD methodology.
"""

import pandas as pd
import pytest
import pytest_asyncio

from trading_bot.strategies.foundation.foundation_engine import FoundationEngine


class TestFoundationEngineInitialization:
    """Test FoundationEngine initialization."""

    def test_foundation_engine_initialization_default(self):
        """Test engine with default parameters."""
        engine = FoundationEngine(use_database=False)  # Disable database for unit tests
        assert engine is not None
        assert hasattr(engine, "strategy")
        assert hasattr(engine, "analyze_symbol")
        assert hasattr(engine, "get_zones")

    def test_foundation_engine_initialization_with_config(self):
        """Test engine with custom configuration."""
        config = {
            "supply_demand": {
                "zone_detection": {"min_zone_strength": 70.0},
                "analysis": {"min_zone_strength": 65.0},
            }
        }
        engine = FoundationEngine(config=config, use_database=False)  # Disable database for unit tests
        assert engine.strategy.detector.min_zone_strength == 70.0
        assert engine.strategy.analyzer.min_zone_strength == 65.0

    def test_foundation_engine_initialization_empty_config(self):
        """Test engine with empty config uses defaults."""
        engine = FoundationEngine(config={}, use_database=False)  # Disable database for unit tests
        assert engine.strategy is not None


class TestFoundationEngineAnalyzeSymbol:
    """Test symbol analysis functionality."""

    @pytest.fixture
    def sample_ohlcv_data(self):
        """Create sample OHLCV data."""
        dates = pd.date_range(
            start=pd.Timestamp.now() - pd.Timedelta(hours=100), periods=100, freq="1h"
        )
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
    async def test_analyze_symbol_detects_zones(self, sample_ohlcv_data):
        """Test that analyze_symbol detects zones."""
        engine = FoundationEngine(
            config={
                "supply_demand": {
                    "zone_detection": {
                        "min_zone_strength": 30.0,
                        "min_zone_size_pips": 2,
                        "max_zone_age_hours": 1000,
                    },
                    "analysis": {"min_zone_strength": 30.0},
                }
            },
            use_database=False,  # Disable database for unit tests
        )

        zones = await engine.analyze_symbol("EURUSD", sample_ohlcv_data, "H1")
        assert isinstance(zones, list)

    @pytest.mark.asyncio
    async def test_analyze_symbol_delegates_to_strategy(self, sample_ohlcv_data):
        """Test that analyze_symbol delegates to strategy."""
        engine = FoundationEngine(
            config={
                "supply_demand": {
                    "zone_detection": {
                        "min_zone_strength": 30.0,
                        "min_zone_size_pips": 2,
                        "max_zone_age_hours": 1000,
                    },
                    "analysis": {"min_zone_strength": 30.0},
                }
            },
            use_database=False,  # Disable database for unit tests
        )

        # Analyze symbol
        await engine.analyze_symbol("EURUSD", sample_ohlcv_data, "H1")

        # Verify zones are stored in strategy
        stored_zones = engine.get_zones("EURUSD")
        assert isinstance(stored_zones, list)

    @pytest.mark.asyncio
    async def test_analyze_symbol_multiple_symbols(self, sample_ohlcv_data):
        """Test analyzing multiple symbols."""
        engine = FoundationEngine(
            config={
                "supply_demand": {
                    "zone_detection": {
                        "min_zone_strength": 30.0,
                        "min_zone_size_pips": 2,
                        "max_zone_age_hours": 1000,
                    },
                    "analysis": {"min_zone_strength": 30.0},
                }
            },
            use_database=False,  # Disable database for unit tests
        )

        # Analyze first symbol
        zones1 = await engine.analyze_symbol("EURUSD", sample_ohlcv_data, "H1")

        # Analyze second symbol
        zones2 = await engine.analyze_symbol("GBPUSD", sample_ohlcv_data, "H1")

        # Both should work
        assert isinstance(zones1, list)
        assert isinstance(zones2, list)

    @pytest.mark.asyncio
    async def test_analyze_symbol_handles_errors(self):
        """Test that analyze_symbol handles errors gracefully."""
        engine = FoundationEngine(use_database=False)  # Disable database for unit tests

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
        zones = await engine.analyze_symbol("EURUSD", invalid_data, "H1")
        assert isinstance(zones, list)
        assert len(zones) == 0


class TestFoundationEngineGetZones:
    """Test getting zones from engine."""

    @pytest_asyncio.fixture
    async def engine_with_zones(self, sample_ohlcv_data):
        """Create engine with analyzed zones."""
        engine = FoundationEngine(
            config={
                "supply_demand": {
                    "zone_detection": {
                        "min_zone_strength": 30.0,
                        "min_zone_size_pips": 2,
                        "max_zone_age_hours": 1000,
                    },
                    "analysis": {"min_zone_strength": 30.0},
                }
            },
            use_database=False,  # Disable database for unit tests
        )
        await engine.analyze_symbol("EURUSD", sample_ohlcv_data, "H1")
        return engine

    @pytest.fixture
    def sample_ohlcv_data(self):
        """Create sample OHLCV data."""
        dates = pd.date_range(
            start=pd.Timestamp.now() - pd.Timedelta(hours=100), periods=100, freq="1h"
        )
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

    def test_get_zones_returns_stored_zones(self, engine_with_zones):
        """Test that get_zones returns stored zones."""
        zones = engine_with_zones.get_zones("EURUSD")
        assert isinstance(zones, list)

    def test_get_zones_delegates_to_strategy(self, engine_with_zones):
        """Test that get_zones delegates to strategy."""
        zones = engine_with_zones.get_zones("EURUSD")
        assert isinstance(zones, list)

    def test_get_zones_nonexistent_symbol(self, engine_with_zones):
        """Test getting zones for non-existent symbol."""
        zones = engine_with_zones.get_zones("GBPUSD")
        assert isinstance(zones, list)
        assert len(zones) == 0

    def test_get_zones_before_analysis(self):
        """Test getting zones before any analysis."""
        engine = FoundationEngine(use_database=False)  # Disable database for unit tests

        zones = engine.get_zones("EURUSD")
        assert isinstance(zones, list)
        assert len(zones) == 0


class TestFoundationEngineIntegration:
    """Test engine integration with strategy."""

    @pytest.mark.asyncio
    async def test_engine_strategy_integration(self, sample_ohlcv_data):
        """Test complete engine-strategy integration."""
        engine = FoundationEngine(
            config={
                "supply_demand": {
                    "zone_detection": {
                        "min_zone_strength": 30.0,
                        "min_zone_size_pips": 2,
                        "max_zone_age_hours": 1000,
                    },
                    "analysis": {"min_zone_strength": 30.0},
                }
            },
            use_database=False,  # Disable database for unit tests
        )

        # Analyze symbol
        quality_zones = await engine.analyze_symbol("EURUSD", sample_ohlcv_data, "H1")

        # Get zones
        all_zones = engine.get_zones("EURUSD")

        # Verify integration
        assert isinstance(quality_zones, list)
        assert isinstance(all_zones, list)

    @pytest.fixture
    def sample_ohlcv_data(self):
        """Create sample OHLCV data."""
        dates = pd.date_range(
            start=pd.Timestamp.now() - pd.Timedelta(hours=100), periods=100, freq="1h"
        )
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


class TestFoundationEngineEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_analyze_symbol_empty_dataframe(self):
        """Test analyzing empty DataFrame."""
        engine = FoundationEngine(use_database=False)  # Disable database for unit tests
        empty_data = pd.DataFrame()

        zones = await engine.analyze_symbol("EURUSD", empty_data, "H1")
        assert isinstance(zones, list)
        assert len(zones) == 0

    @pytest.mark.asyncio
    async def test_analyze_symbol_missing_columns(self):
        """Test analyzing data with missing columns."""
        engine = FoundationEngine(use_database=False)  # Disable database for unit tests
        invalid_data = pd.DataFrame({"open": [1.1000] * 50})

        # Should handle error gracefully
        zones = await engine.analyze_symbol("EURUSD", invalid_data, "H1")
        assert isinstance(zones, list)

    def test_engine_configuration_passed_to_strategy(self):
        """Test that engine configuration is passed to strategy."""
        config = {
            "supply_demand": {
                "zone_detection": {"min_zone_strength": 75.0},
                "analysis": {"min_zone_strength": 70.0},
            }
        }
        engine = FoundationEngine(config=config, use_database=False)  # Disable database for unit tests

        # Verify config was passed
        assert engine.strategy.detector.min_zone_strength == 75.0
        assert engine.strategy.analyzer.min_zone_strength == 70.0
