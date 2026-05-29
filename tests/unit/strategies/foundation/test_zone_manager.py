"""
Unit tests for ZoneManager.

Testing zone lifecycle management with TDD methodology.
"""

from datetime import datetime

import pytest
import pytest_asyncio
from trading_worker.strategies.foundation.zone_detector import DetectedZone, ZoneType
from trading_worker.strategies.foundation.zone_manager import ZoneManager


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


class TestZoneManagerZoneMatching:
    """Test zone matching and similarity detection."""

    @pytest.mark.asyncio
    async def test_find_similar_zone_overlapping(self):
        """Test finding similar zone when zones overlap."""
        manager = ZoneManager(use_database=False)

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

        # Overlapping zone
        zone2 = DetectedZone(
            zone_type=ZoneType.REJECTION,
            upper_bound=1.0980,
            lower_bound=1.0930,
            strength=70.0,
            touches=2,
            volume_confirmed=True,
            first_detected=datetime.now(),
            last_tested=datetime.now(),
        )

        await manager.add_zones("EURUSD", [zone1], "H1")
        similar = manager._find_similar_zone("EURUSD", zone2)
        assert similar is not None
        assert similar == zone1

    @pytest.mark.asyncio
    async def test_find_similar_zone_close_distance(self):
        """Test finding similar zone when zones are close (within 5 pips)."""
        manager = ZoneManager(use_database=False)

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

        # Close zone (within 5 pips)
        zone2 = DetectedZone(
            zone_type=ZoneType.REJECTION,
            upper_bound=1.1005,
            lower_bound=1.0955,
            strength=70.0,
            touches=2,
            volume_confirmed=True,
            first_detected=datetime.now(),
            last_tested=datetime.now(),
        )

        await manager.add_zones("EURUSD", [zone1], "H1")
        similar = manager._find_similar_zone("EURUSD", zone2)
        assert similar is not None

    @pytest.mark.asyncio
    async def test_find_similar_zone_different_type(self):
        """Test that zones with different types are not considered similar."""
        manager = ZoneManager(use_database=False)

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
            zone_type=ZoneType.CONSOLIDATION,  # Different type
            upper_bound=1.1000,
            lower_bound=1.0950,
            strength=70.0,
            touches=2,
            volume_confirmed=True,
            first_detected=datetime.now(),
            last_tested=datetime.now(),
        )

        await manager.add_zones("EURUSD", [zone1], "H1")
        similar = manager._find_similar_zone("EURUSD", zone2)
        assert similar is None

    def test_zones_overlap_true(self):
        """Test zones_overlap returns True when zones overlap."""
        manager = ZoneManager(use_database=False)

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
            upper_bound=1.0980,
            lower_bound=1.0930,
            strength=70.0,
            touches=2,
            volume_confirmed=True,
            first_detected=datetime.now(),
            last_tested=datetime.now(),
        )

        assert manager._zones_overlap(zone1, zone2) is True

    def test_zones_overlap_false(self):
        """Test zones_overlap returns False when zones don't overlap."""
        manager = ZoneManager(use_database=False)

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
            upper_bound=1.1100,
            lower_bound=1.1050,
            strength=70.0,
            touches=2,
            volume_confirmed=True,
            first_detected=datetime.now(),
            last_tested=datetime.now(),
        )

        assert manager._zones_overlap(zone1, zone2) is False


class TestZoneManagerExpiration:
    """Test zone expiration logic."""

    @pytest.mark.asyncio
    async def test_remove_expired_zones_memory_only(self):
        """Test removing expired zones from memory."""
        from datetime import timedelta

        manager = ZoneManager(
            config={"max_zone_age_hours": 1}, use_database=False
        )  # 1 hour max age

        # Create old zone (2 hours ago)
        old_zone = DetectedZone(
            zone_type=ZoneType.REJECTION,
            upper_bound=1.1000,
            lower_bound=1.0950,
            strength=75.0,
            touches=3,
            volume_confirmed=True,
            first_detected=datetime.now() - timedelta(hours=2),
            last_tested=datetime.now() - timedelta(hours=2),
        )

        # Create new zone (30 minutes ago)
        new_zone = DetectedZone(
            zone_type=ZoneType.REJECTION,
            upper_bound=1.1050,
            lower_bound=1.1000,
            strength=70.0,
            touches=2,
            volume_confirmed=True,
            first_detected=datetime.now() - timedelta(minutes=30),
            last_tested=datetime.now() - timedelta(minutes=30),
        )

        # Manually add zones to test expiration
        manager.zones["EURUSD"] = [old_zone, new_zone]

        await manager._remove_expired_zones_memory_only("EURUSD")

        zones = manager.get_zones("EURUSD")
        assert len(zones) == 1
        assert zones[0] == new_zone

    @pytest.mark.asyncio
    async def test_remove_expired_zones_nonexistent_symbol(self):
        """Test removing expired zones for non-existent symbol."""
        manager = ZoneManager(use_database=False)
        # Should not raise error
        await manager._remove_expired_zones_memory_only("EURUSD")


class TestZoneManagerPriceUpdates:
    """Test updating zones with current price."""

    @pytest.mark.asyncio
    async def test_update_zones_with_current_price_touches_zone(self):
        """Test updating zones when price touches a zone."""
        manager = ZoneManager(use_database=False)

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

        initial_touches = zone.touches
        current_time = datetime.now()

        # Price touches the zone
        manager.update_zones_with_current_price("EURUSD", 1.0975, current_time)

        assert zone.touches == initial_touches + 1
        assert zone.last_tested == current_time

    @pytest.mark.asyncio
    async def test_update_zones_with_current_price_no_touch(self):
        """Test updating zones when price doesn't touch any zone."""
        manager = ZoneManager(use_database=False)

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

        initial_touches = zone.touches
        initial_last_tested = zone.last_tested

        # Price doesn't touch the zone
        manager.update_zones_with_current_price("EURUSD", 1.1100, datetime.now())

        assert zone.touches == initial_touches
        assert zone.last_tested == initial_last_tested

    def test_update_zones_with_current_price_nonexistent_symbol(self):
        """Test updating zones for non-existent symbol."""
        manager = ZoneManager(use_database=False)
        # Should not raise error
        manager.update_zones_with_current_price("EURUSD", 1.1000, datetime.now())


class TestZoneManagerZoneIdGeneration:
    """Test zone ID generation."""

    def test_generate_zone_id(self):
        """Test zone ID generation."""
        manager = ZoneManager(use_database=False)

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

        zone_id = manager._generate_zone_id("EURUSD", zone)
        assert isinstance(zone_id, str)
        assert "EURUSD" in zone_id
        assert "rejection" in zone_id.lower()
        assert "1.10000" in zone_id or "1.1000" in zone_id
        assert "1.09500" in zone_id or "1.0950" in zone_id

    def test_generate_zone_id_unique_for_different_zones(self):
        """Test that different zones generate different IDs."""
        manager = ZoneManager(use_database=False)

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
            zone_type=ZoneType.CONSOLIDATION,
            upper_bound=1.1050,
            lower_bound=1.1000,
            strength=70.0,
            touches=2,
            volume_confirmed=False,
            first_detected=datetime.now(),
            last_tested=datetime.now(),
        )

        id1 = manager._generate_zone_id("EURUSD", zone1)
        id2 = manager._generate_zone_id("EURUSD", zone2)

        assert id1 != id2


class TestZoneManagerZoneLimiting:
    """Test zone limiting when max_zones_per_symbol is reached."""

    @pytest.mark.asyncio
    async def test_add_zones_respects_max_limit(self):
        """Test that adding zones respects max_zones_per_symbol limit."""
        manager = ZoneManager(config={"max_zones_per_symbol": 3}, use_database=False)  # Max 3 zones

        zones = []
        for i in range(5):  # Try to add 5 zones
            # Make zones far apart so they don't overlap (at least 0.01 apart = 100 pips)
            # This ensures they're not considered similar
            zone = DetectedZone(
                zone_type=ZoneType.REJECTION,
                upper_bound=1.1000 + (i * 0.0100),  # 100 pips apart
                lower_bound=1.0950 + (i * 0.0100),
                strength=75.0 - (i * 5),  # Decreasing strength
                touches=3,
                volume_confirmed=True,
                first_detected=datetime.now(),
                last_tested=datetime.now(),
            )
            zones.append(zone)

        await manager.add_zones("EURUSD", zones, "H1")

        # Should only keep top 3 by strength
        stored_zones = manager.get_zones("EURUSD")
        assert len(stored_zones) == 3
        # Should be sorted by strength (descending)
        assert stored_zones[0].strength >= stored_zones[1].strength
        assert stored_zones[1].strength >= stored_zones[2].strength


class TestZoneManagerZoneUpdates:
    """Test zone update logic when similar zones are detected."""

    @pytest.mark.asyncio
    async def test_add_zones_updates_existing_zone(self):
        """Test that adding similar zone updates existing zone instead of adding new one."""
        manager = ZoneManager(use_database=False)

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

        # Add similar zone (overlapping)
        zone2 = DetectedZone(
            zone_type=ZoneType.REJECTION,
            upper_bound=1.0980,
            lower_bound=1.0930,
            strength=80.0,  # Stronger
            touches=2,
            volume_confirmed=True,
            first_detected=datetime.now(),
            last_tested=datetime.now(),
        )

        await manager.add_zones("EURUSD", [zone2], "H1")

        zones = manager.get_zones("EURUSD")
        assert len(zones) == 1  # Should update, not add new
        assert zones[0].strength == 80.0  # Should update to stronger strength
        assert zones[0].touches == 4  # Should increment touches (3 + 1)
