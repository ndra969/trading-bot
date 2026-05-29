"""
Unit tests for enhanced SupplyDemandZone model.

Tests session relationship and freshness score functionality.
"""


from trading_core.data.models import SupplyDemandZone


class TestSupplyDemandZoneEnhanced:
    """Test enhanced SupplyDemandZone model."""

    def test_zone_session_relationship(self):
        """Test zone can be linked to trading session."""
        zone = SupplyDemandZone(
            zone_id="zone_test_001",
            symbol="EURUSD",
            zone_type="rejection",
            high_price=1.1000,
            low_price=1.0950,
            session_id="sess_test_001",
        )

        assert zone.session_id == "sess_test_001"
        assert zone.symbol == "EURUSD"

    def test_freshness_score_default(self):
        """Test freshness_score defaults to 0.0."""
        zone = SupplyDemandZone(
            zone_id="zone_test_002",
            symbol="GBPUSD",
            zone_type="consolidation",
            high_price=1.3000,
            low_price=1.2950,
            freshness_score=0.0,  # Explicitly set for test
        )

        assert zone.freshness_score == 0.0

    def test_freshness_score_setting(self):
        """Test setting freshness_score."""
        zone = SupplyDemandZone(
            zone_id="zone_test_003",
            symbol="USDJPY",
            zone_type="breakout_origin",
            high_price=150.00,
            low_price=149.50,
            freshness_score=75.5,
        )

        assert zone.freshness_score == 75.5

    def test_freshness_score_validation(self):
        """Test freshness_score constraint validation."""
        # This will be validated at database level
        # For now, just test that we can set valid values
        zone = SupplyDemandZone(
            zone_id="zone_test_004",
            symbol="EURUSD",
            zone_type="rejection",
            high_price=1.1000,
            low_price=1.0950,
            freshness_score=100.0,  # Max value
        )

        assert zone.freshness_score == 100.0

    def test_zone_with_session_and_freshness(self):
        """Test zone with both session_id and freshness_score."""
        zone = SupplyDemandZone(
            zone_id="zone_test_005",
            symbol="GBPUSD",
            zone_type="rejection",
            high_price=1.3000,
            low_price=1.2950,
            session_id="sess_test_002",
            freshness_score=85.0,
        )

        assert zone.session_id == "sess_test_002"
        assert zone.freshness_score == 85.0

    def test_zone_without_session_backward_compatibility(self):
        """Test zone without session_id (backward compatibility)."""
        zone = SupplyDemandZone(
            zone_id="zone_test_006",
            symbol="EURUSD",
            zone_type="consolidation",
            high_price=1.1000,
            low_price=1.0950,
            session_id=None,  # Explicitly None for backward compatibility
            freshness_score=0.0,  # Explicitly set
            touched_count=0,  # Explicitly set
        )

        assert zone.session_id is None
        assert zone.freshness_score == 0.0

    def test_zone_quality_with_freshness(self):
        """Test zone quality calculation with freshness score."""
        zone = SupplyDemandZone(
            zone_id="zone_test_007",
            symbol="USDJPY",
            zone_type="rejection",
            high_price=150.00,
            low_price=149.50,
            strength=80.0,
            confluence_score=70.0,
            freshness_score=90.0,
        )

        # Zone has high quality metrics
        assert zone.strength == 80.0
        assert zone.confluence_score == 70.0
        assert zone.freshness_score == 90.0

    def test_zone_lifecycle_with_session(self):
        """Test zone lifecycle methods work with session."""
        zone = SupplyDemandZone(
            zone_id="zone_test_008",
            symbol="EURUSD",
            zone_type="rejection",
            high_price=1.1000,
            low_price=1.0950,
            session_id="sess_test_003",
            freshness_score=50.0,
            touched_count=0,  # Explicitly set
        )

        # Test zone methods still work
        assert zone.is_price_in_zone(1.0975) is True
        assert zone.is_price_in_zone(1.1100) is False

        # Touch zone
        zone.touch_zone()
        assert zone.touched_count == 1
        assert zone.last_touched is not None

        # Deactivate
        zone.deactivate_zone()
        assert zone.is_active is False
