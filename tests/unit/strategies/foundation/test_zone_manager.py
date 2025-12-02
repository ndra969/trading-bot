"""
Unit tests for ZoneManager.

Testing zone lifecycle management with TDD methodology.
"""

from datetime import datetime

import pytest
import pytest_asyncio

from trading_bot.strategies.foundation.zone_detector import DetectedZone, ZoneType
from trading_bot.strategies.foundation.zone_manager import ZoneManager


class TestZoneManagerInitialization:
    """Test ZoneManager initialization."""

    def test_zone_manager_initialization(self):
        """Test zone manager initializes correctly."""
        manager = ZoneManager(use_database=False)  # Disable database for unit tests
        assert manager is not None
        assert hasattr(manager, "zones")
        assert isinstance(manager.zones, dict)
        assert len(manager.zones) == 0

    def test_zone_manager_empty_state(self):
        """Test zone manager starts with empty state."""
        manager = ZoneManager(use_database=False)  # Disable database for unit tests
        assert manager.get_zones("EURUSD") == []


class TestZoneManagerAddZones:
    """Test adding zones to manager."""

    @pytest.fixture
    def sample_zone(self):
        """Create a sample zone for testing."""
        return DetectedZone(
            zone_type=ZoneType.REJECTION,
            upper_bound=1.1000,
            lower_bound=1.0950,
            strength=75.0,
            touches=3,
            volume_confirmed=True,
            first_detected=datetime.now(),
            last_tested=datetime.now(),
        )

    @pytest.mark.asyncio
    async def test_add_zones_new_symbol(self, sample_zone):
        """Test adding zones for a new symbol."""
        manager = ZoneManager(use_database=False)  # Disable database for unit tests
        await manager.add_zones("EURUSD", [sample_zone], "H1")

        zones = manager.get_zones("EURUSD")
        assert len(zones) == 1
        assert zones[0] == sample_zone

    @pytest.mark.asyncio
    async def test_add_zones_existing_symbol(self, sample_zone):
        """Test adding zones to existing symbol."""
        manager = ZoneManager(use_database=False)  # Disable database for unit tests
        await manager.add_zones("EURUSD", [sample_zone], "H1")

        # Add another zone
        zone2 = DetectedZone(
            zone_type=ZoneType.CONSOLIDATION,
            upper_bound=1.1050,
            lower_bound=1.1000,
            strength=60.0,
            touches=2,
            volume_confirmed=False,
            first_detected=datetime.now(),
            last_tested=datetime.now(),
        )
        await manager.add_zones("EURUSD", [zone2], "H1")

        zones = manager.get_zones("EURUSD")
        assert len(zones) == 2

    @pytest.mark.asyncio
    async def test_add_zones_multiple_zones(self, sample_zone):
        """Test adding multiple zones at once."""
        manager = ZoneManager(use_database=False)  # Disable database for unit tests

        zone2 = DetectedZone(
            zone_type=ZoneType.CONSOLIDATION,
            upper_bound=1.1050,
            lower_bound=1.1000,
            strength=60.0,
            touches=2,
            volume_confirmed=False,
            first_detected=datetime.now(),
            last_tested=datetime.now(),
        )

        zone3 = DetectedZone(
            zone_type=ZoneType.BREAKOUT_ORIGIN,
            upper_bound=1.1100,
            lower_bound=1.1050,
            strength=80.0,
            touches=4,
            volume_confirmed=True,
            first_detected=datetime.now(),
            last_tested=datetime.now(),
        )

        await manager.add_zones("EURUSD", [sample_zone, zone2, zone3], "H1")

        zones = manager.get_zones("EURUSD")
        assert len(zones) == 3

    @pytest.mark.asyncio
    async def test_add_zones_empty_list(self):
        """Test adding empty zone list."""
        manager = ZoneManager(use_database=False)  # Disable database for unit tests
        await manager.add_zones("EURUSD", [], "H1")

        zones = manager.get_zones("EURUSD")
        assert len(zones) == 0

    @pytest.mark.asyncio
    async def test_add_zones_multiple_symbols(self, sample_zone):
        """Test adding zones for multiple symbols."""
        manager = ZoneManager(use_database=False)  # Disable database for unit tests

        zone2 = DetectedZone(
            zone_type=ZoneType.REJECTION,
            upper_bound=1500.0,
            lower_bound=1450.0,
            strength=70.0,
            touches=2,
            volume_confirmed=True,
            first_detected=datetime.now(),
            last_tested=datetime.now(),
        )

        await manager.add_zones("EURUSD", [sample_zone], "H1")
        await manager.add_zones("XAUUSD", [zone2], "H1")

        eurusd_zones = manager.get_zones("EURUSD")
        xauusd_zones = manager.get_zones("XAUUSD")

        assert len(eurusd_zones) == 1
        assert len(xauusd_zones) == 1
        assert eurusd_zones[0] == sample_zone
        assert xauusd_zones[0] == zone2


class TestZoneManagerGetZones:
    """Test retrieving zones from manager."""

    @pytest_asyncio.fixture
    async def manager_with_zones(self):
        """Create manager with sample zones."""
        manager = ZoneManager(use_database=False)  # Disable database for unit tests

        rejection_zone = DetectedZone(
            zone_type=ZoneType.REJECTION,
            upper_bound=1.1000,
            lower_bound=1.0950,
            strength=75.0,
            touches=3,
            volume_confirmed=True,
            first_detected=datetime.now(),
            last_tested=datetime.now(),
        )

        consolidation_zone = DetectedZone(
            zone_type=ZoneType.CONSOLIDATION,
            upper_bound=1.1050,
            lower_bound=1.1000,
            strength=60.0,
            touches=2,
            volume_confirmed=False,
            first_detected=datetime.now(),
            last_tested=datetime.now(),
        )

        breakout_zone = DetectedZone(
            zone_type=ZoneType.BREAKOUT_ORIGIN,
            upper_bound=1.1100,
            lower_bound=1.1050,
            strength=80.0,
            touches=4,
            volume_confirmed=True,
            first_detected=datetime.now(),
            last_tested=datetime.now(),
        )

        await manager.add_zones("EURUSD", [rejection_zone, consolidation_zone, breakout_zone], "H1")
        return manager

    def test_get_zones_all(self, manager_with_zones):
        """Test getting all zones for a symbol."""
        zones = manager_with_zones.get_zones("EURUSD")
        assert len(zones) == 3

    def test_get_zones_filtered_by_type(self, manager_with_zones):
        """Test getting zones filtered by type."""
        rejection_zones = manager_with_zones.get_zones("EURUSD", ZoneType.REJECTION)
        assert len(rejection_zones) == 1
        assert rejection_zones[0].zone_type == ZoneType.REJECTION

        consolidation_zones = manager_with_zones.get_zones("EURUSD", ZoneType.CONSOLIDATION)
        assert len(consolidation_zones) == 1
        assert consolidation_zones[0].zone_type == ZoneType.CONSOLIDATION

        breakout_zones = manager_with_zones.get_zones("EURUSD", ZoneType.BREAKOUT_ORIGIN)
        assert len(breakout_zones) == 1
        assert breakout_zones[0].zone_type == ZoneType.BREAKOUT_ORIGIN

    def test_get_zones_nonexistent_symbol(self, manager_with_zones):
        """Test getting zones for non-existent symbol."""
        zones = manager_with_zones.get_zones("GBPUSD")
        assert len(zones) == 0

    @pytest.mark.asyncio
    async def test_get_zones_filtered_type_nonexistent(self, manager_with_zones):
        """Test getting filtered zones when type doesn't exist."""
        # Add zones for another symbol with only one type
        zone = DetectedZone(
            zone_type=ZoneType.REJECTION,
            upper_bound=1.2000,
            lower_bound=1.1950,
            strength=70.0,
            touches=2,
            volume_confirmed=True,
            first_detected=datetime.now(),
            last_tested=datetime.now(),
        )
        await manager_with_zones.add_zones("GBPUSD", [zone], "H1")

        # Try to get consolidation zones for GBPUSD (none exist)
        consolidation_zones = manager_with_zones.get_zones("GBPUSD", ZoneType.CONSOLIDATION)
        assert len(consolidation_zones) == 0


class TestZoneManagerClearZones:
    """Test clearing zones from manager."""

    @pytest_asyncio.fixture
    async def manager_with_zones(self):
        """Create manager with sample zones."""
        manager = ZoneManager(use_database=False)  # Disable database for unit tests

        zone = DetectedZone(
            zone_type=ZoneType.REJECTION,
            upper_bound=1.1000,
            lower_bound=1.0950,
            strength=75.0,
            touches=3,
            volume_confirmed=True,
            first_detected=datetime.now(),
            last_tested=datetime.now(),
        )

        await manager.add_zones("EURUSD", [zone], "H1")
        return manager

    def test_clear_zones_existing_symbol(self, manager_with_zones):
        """Test clearing zones for existing symbol."""
        # Verify zones exist
        assert len(manager_with_zones.get_zones("EURUSD")) > 0

        # Clear zones
        manager_with_zones.clear_zones("EURUSD")

        # Verify zones are cleared
        assert len(manager_with_zones.get_zones("EURUSD")) == 0

    def test_clear_zones_nonexistent_symbol(self, manager_with_zones):
        """Test clearing zones for non-existent symbol (should not error)."""
        # Should not raise error
        manager_with_zones.clear_zones("GBPUSD")

        # Verify other symbols still have zones
        assert len(manager_with_zones.get_zones("EURUSD")) > 0

    @pytest.mark.asyncio
    async def test_clear_zones_multiple_symbols(self):
        """Test clearing zones for one symbol doesn't affect others."""
        manager = ZoneManager(use_database=False)  # Disable database for unit tests

        zone1 = DetectedZone(
            zone_type=ZoneType.REJECTION,
            upper_bound=1.1000,
            lower_bound=1.0950,
            strength=75.0,
            touches=3,
            volume_confirmed=True,
            first_detected=datetime.now(),
            last_tested=datetime.now(),
        )

        zone2 = DetectedZone(
            zone_type=ZoneType.REJECTION,
            upper_bound=1500.0,
            lower_bound=1450.0,
            strength=70.0,
            touches=2,
            volume_confirmed=True,
            first_detected=datetime.now(),
            last_tested=datetime.now(),
        )

        await manager.add_zones("EURUSD", [zone1], "H1")
        await manager.add_zones("XAUUSD", [zone2], "H1")

        # Clear one symbol
        manager.clear_zones("EURUSD")

        # Verify other symbol still has zones
        assert len(manager.get_zones("EURUSD")) == 0
        assert len(manager.get_zones("XAUUSD")) == 1


class TestZoneManagerEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_get_zones_after_clear(self):
        """Test getting zones after clearing."""
        manager = ZoneManager(use_database=False)  # Disable database for unit tests

        zone = DetectedZone(
            zone_type=ZoneType.REJECTION,
            upper_bound=1.1000,
            lower_bound=1.0950,
            strength=75.0,
            touches=3,
            volume_confirmed=True,
            first_detected=datetime.now(),
            last_tested=datetime.now(),
        )

        await manager.add_zones("EURUSD", [zone], "H1")
        manager.clear_zones("EURUSD")

        # Should return empty list, not error
        zones = manager.get_zones("EURUSD")
        assert isinstance(zones, list)
        assert len(zones) == 0

    @pytest.mark.asyncio
    async def test_add_zones_after_clear(self):
        """Test adding zones after clearing."""
        manager = ZoneManager(use_database=False)  # Disable database for unit tests

        zone1 = DetectedZone(
            zone_type=ZoneType.REJECTION,
            upper_bound=1.1000,
            lower_bound=1.0950,
            strength=75.0,
            touches=3,
            volume_confirmed=True,
            first_detected=datetime.now(),
            last_tested=datetime.now(),
        )

        await manager.add_zones("EURUSD", [zone1], "H1")
        manager.clear_zones("EURUSD")

        # Add new zones after clearing
        zone2 = DetectedZone(
            zone_type=ZoneType.CONSOLIDATION,
            upper_bound=1.1050,
            lower_bound=1.1000,
            strength=60.0,
            touches=2,
            volume_confirmed=False,
            first_detected=datetime.now(),
            last_tested=datetime.now(),
        )

        await manager.add_zones("EURUSD", [zone2], "H1")
        zones = manager.get_zones("EURUSD")
        assert len(zones) == 1
        assert zones[0] == zone2
