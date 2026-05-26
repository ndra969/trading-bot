"""
Unit tests for database models.
"""


import pytest

from trading_bot.data.models import Position, SupplyDemandZone


class TestSupplyDemandZone:
    """Test SupplyDemandZone model."""

    def test_zone_range_property(self):
        """Test zone_range property calculation."""
        zone = SupplyDemandZone(
            zone_id="test_zone",
            symbol="EURUSD",
            zone_type="rejection",
            high_price=1.1000,
            low_price=1.0950,
        )
        assert zone.zone_range == pytest.approx(0.0050, rel=1e-6)

    def test_zone_midpoint_property(self):
        """Test zone_midpoint property calculation."""
        zone = SupplyDemandZone(
            zone_id="test_zone",
            symbol="EURUSD",
            zone_type="rejection",
            high_price=1.1000,
            low_price=1.0950,
        )
        assert zone.zone_midpoint == pytest.approx(1.0975, rel=1e-6)

    def test_is_price_in_zone_true(self):
        """Test is_price_in_zone returns True when price is in zone."""
        zone = SupplyDemandZone(
            zone_id="test_zone",
            symbol="EURUSD",
            zone_type="rejection",
            high_price=1.1000,
            low_price=1.0950,
        )
        assert zone.is_price_in_zone(1.0975) is True
        assert zone.is_price_in_zone(1.1000) is True  # At upper bound
        assert zone.is_price_in_zone(1.0950) is True  # At lower bound

    def test_is_price_in_zone_false(self):
        """Test is_price_in_zone returns False when price is outside zone."""
        zone = SupplyDemandZone(
            zone_id="test_zone",
            symbol="EURUSD",
            zone_type="rejection",
            high_price=1.1000,
            low_price=1.0950,
        )
        assert zone.is_price_in_zone(1.1100) is False  # Above zone
        assert zone.is_price_in_zone(1.0900) is False  # Below zone

    def test_touch_zone(self):
        """Test touch_zone method increments touched_count."""
        zone = SupplyDemandZone(
            zone_id="test_zone",
            symbol="EURUSD",
            zone_type="rejection",
            high_price=1.1000,
            low_price=1.0950,
            touched_count=0,
        )
        initial_count = zone.touched_count
        zone.touch_zone()
        assert zone.touched_count == initial_count + 1
        assert zone.last_touched is not None
        assert zone.updated_at is not None

    def test_touch_zone_multiple_times(self):
        """Test touch_zone method increments multiple times."""
        zone = SupplyDemandZone(
            zone_id="test_zone",
            symbol="EURUSD",
            zone_type="rejection",
            high_price=1.1000,
            low_price=1.0950,
            touched_count=0,
        )
        zone.touch_zone()
        zone.touch_zone()
        zone.touch_zone()
        assert zone.touched_count == 3

    def test_deactivate_zone(self):
        """Test deactivate_zone method."""
        zone = SupplyDemandZone(
            zone_id="test_zone",
            symbol="EURUSD",
            zone_type="rejection",
            high_price=1.1000,
            low_price=1.0950,
            is_active=True,
        )
        zone.deactivate_zone()
        assert zone.is_active is False
        assert zone.updated_at is not None

    def test_repr(self):
        """Test __repr__ method."""
        zone = SupplyDemandZone(
            zone_id="test_zone",
            symbol="EURUSD",
            zone_type="rejection",
            high_price=1.1000,
            low_price=1.0950,
            strength=75.5,
        )
        repr_str = repr(zone)
        assert "SupplyDemandZone" in repr_str
        assert "EURUSD" in repr_str
        assert "rejection" in repr_str
        assert "75.5" in repr_str


class TestPosition:
    """Test Position model."""

    def test_repr(self):
        """Test __repr__ method."""
        position = Position(
            position_id="test_position",
            symbol="EURUSD",
            position_type="BUY",
            status="OPEN",
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1050,
            volume=0.1,
            pip_size=0.0001,
            pip_value_per_lot=10.0,
        )
        repr_str = repr(position)
        assert "Position" in repr_str
        assert "test_position" in repr_str
        assert "EURUSD" in repr_str
        assert "BUY" in repr_str
        assert "OPEN" in repr_str

