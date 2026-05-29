"""Additional tests for ExposureManager negative correlation feature."""

from trading_worker.risk.exposure_manager import ExposureManager


class TestNegativeCorrelationGroups:
    """Test negative correlation groups loading from config."""

    def test_negative_correlation_groups_from_config(self):
        """Test negative correlation groups loaded from config YAML."""
        config = {
            "risk_management": {
                "correlation_management": {
                    "enabled": True,
                    "negative_correlation_groups": {
                        "USDCAD": ["EURUSD", "GBPUSD"],
                        "EURUSD": ["USDCAD"],
                    },
                }
            }
        }
        manager = ExposureManager(config)

        # Check that USDCAD has EURUSD and GBPUSD as negatively correlated
        assert "EURUSD" in manager.negative_correlated_pairs.get("USDCAD", [])
        assert "GBPUSD" in manager.negative_correlated_pairs.get("USDCAD", [])

        # Check bidirectional mapping (EURUSD should have USDCAD)
        assert "USDCAD" in manager.negative_correlated_pairs.get("EURUSD", [])

    def test_negative_correlation_groups_fallback_to_defaults(self):
        """Test negative correlation groups fallback to hardcoded defaults when config not provided."""
        config = {
            "risk_management": {
                "correlation_management": {
                    "enabled": True,
                    # No negative_correlation_groups in config
                }
            }
        }
        manager = ExposureManager(config)

        # Should use hardcoded defaults
        assert "USDCAD" in manager.negative_correlated_pairs
        assert "EURUSD" in manager.negative_correlated_pairs.get("USDCAD", [])
        assert "USDCAD" in manager.negative_correlated_pairs.get("EURUSD", [])

    def test_negative_correlation_conflict_detection_same_direction(self):
        """Test negative correlation conflict detection prevents same direction positions."""
        config = {
            "risk_management": {
                "correlation_management": {
                    "enabled": True,
                    "negative_correlation_groups": {
                        "USDCAD": ["EURUSD"],
                        "EURUSD": ["USDCAD"],
                    },
                }
            }
        }
        manager = ExposureManager(config)

        # Register USDCAD BUY position
        manager.register_position("USDCAD", "forex_major", 1.0, direction="BUY")

        # Try to open EURUSD BUY (same direction - should be rejected for negative correlation)
        can_open, reason = manager.can_open_position(
            symbol="EURUSD", asset_class="forex_major", risk_amount=200.0, direction="BUY"
        )

        assert can_open is False
        assert "Negative correlation conflict" in reason
        assert "USDCAD" in reason
        assert "BUY" in reason
        assert "opposite direction" in reason

    def test_negative_correlation_opposite_direction_allowed(self):
        """Test that opposite direction on negatively correlated pairs is allowed."""
        config = {
            "risk_management": {
                "correlation_management": {
                    "enabled": True,
                    "negative_correlation_groups": {
                        "USDCAD": ["EURUSD"],
                        "EURUSD": ["USDCAD"],
                    },
                }
            }
        }
        manager = ExposureManager(config)

        # Register USDCAD BUY position
        manager.register_position("USDCAD", "forex_major", 1.0, direction="BUY")

        # Try to open EURUSD SELL (opposite direction - should be allowed for negative correlation)
        can_open, reason = manager.can_open_position(
            symbol="EURUSD", asset_class="forex_major", risk_amount=200.0, direction="SELL"
        )

        assert can_open is True
        assert reason == "OK"

    def test_negative_correlation_conflict_detection_reverse(self):
        """Test negative correlation conflict detection in reverse direction."""
        config = {
            "risk_management": {
                "correlation_management": {
                    "enabled": True,
                    "negative_correlation_groups": {
                        "USDCAD": ["EURUSD"],
                        "EURUSD": ["USDCAD"],
                    },
                }
            }
        }
        manager = ExposureManager(config)

        # Register EURUSD SELL position
        manager.register_position("EURUSD", "forex_major", 1.0, direction="SELL")

        # Try to open USDCAD SELL (same direction - should be rejected)
        can_open, reason = manager.can_open_position(
            symbol="USDCAD", asset_class="forex_major", risk_amount=200.0, direction="SELL"
        )

        assert can_open is False
        assert "Negative correlation conflict" in reason
        assert "EURUSD" in reason
        assert "SELL" in reason

    def test_negative_correlation_buy_sell_combination(self):
        """Test all combinations of BUY/SELL for negative correlation."""
        config = {
            "risk_management": {
                "correlation_management": {
                    "enabled": True,
                    "negative_correlation_groups": {
                        "USDCAD": ["EURUSD"],
                        "EURUSD": ["USDCAD"],
                    },
                }
            }
        }
        manager = ExposureManager(config)

        # Test 1: USDCAD BUY → EURUSD SELL (allowed)
        manager.register_position("USDCAD", "forex_major", 1.0, direction="BUY")
        can_open, reason = manager.can_open_position(
            symbol="EURUSD", asset_class="forex_major", risk_amount=200.0, direction="SELL"
        )
        assert can_open is True

        # Reset
        manager.reset_tracking()

        # Test 2: USDCAD SELL → EURUSD BUY (allowed)
        manager.register_position("USDCAD", "forex_major", 1.0, direction="SELL")
        can_open, reason = manager.can_open_position(
            symbol="EURUSD", asset_class="forex_major", risk_amount=200.0, direction="BUY"
        )
        assert can_open is True

        # Reset
        manager.reset_tracking()

        # Test 3: USDCAD BUY → EURUSD BUY (rejected)
        manager.register_position("USDCAD", "forex_major", 1.0, direction="BUY")
        can_open, reason = manager.can_open_position(
            symbol="EURUSD", asset_class="forex_major", risk_amount=200.0, direction="BUY"
        )
        assert can_open is False
        assert "Negative correlation conflict" in reason

        # Reset
        manager.reset_tracking()

        # Test 4: USDCAD SELL → EURUSD SELL (rejected)
        manager.register_position("USDCAD", "forex_major", 1.0, direction="SELL")
        can_open, reason = manager.can_open_position(
            symbol="EURUSD", asset_class="forex_major", risk_amount=200.0, direction="SELL"
        )
        assert can_open is False
        assert "Negative correlation conflict" in reason

    def test_negative_correlation_multiple_pairs(self):
        """Test negative correlation with multiple pairs (USDCAD vs EURUSD, GBPUSD, AUDUSD)."""
        config = {
            "risk_management": {
                "correlation_management": {
                    "enabled": True,
                    "negative_correlation_groups": {
                        "USDCAD": ["EURUSD", "GBPUSD", "AUDUSD"],
                        "EURUSD": ["USDCAD"],
                        "GBPUSD": ["USDCAD"],
                        "AUDUSD": ["USDCAD"],
                    },
                }
            }
        }
        manager = ExposureManager(config)

        # Register USDCAD BUY
        manager.register_position("USDCAD", "forex_major", 1.0, direction="BUY")

        # EURUSD BUY should be rejected
        can_open, reason = manager.can_open_position(
            symbol="EURUSD", asset_class="forex_major", risk_amount=200.0, direction="BUY"
        )
        assert can_open is False

        # GBPUSD BUY should be rejected
        can_open, reason = manager.can_open_position(
            symbol="GBPUSD", asset_class="forex_major", risk_amount=200.0, direction="BUY"
        )
        assert can_open is False

        # AUDUSD BUY should be rejected
        can_open, reason = manager.can_open_position(
            symbol="AUDUSD", asset_class="forex_major", risk_amount=200.0, direction="BUY"
        )
        assert can_open is False

        # But EURUSD SELL should be allowed
        can_open, reason = manager.can_open_position(
            symbol="EURUSD", asset_class="forex_major", risk_amount=200.0, direction="SELL"
        )
        assert can_open is True

    def test_negative_correlation_disabled(self):
        """Test that negative correlation checking is skipped when disabled."""
        config = {
            "risk_management": {
                "correlation_management": {
                    "enabled": False,  # Disabled
                    "negative_correlation_groups": {
                        "USDCAD": ["EURUSD"],
                        "EURUSD": ["USDCAD"],
                    },
                }
            }
        }
        manager = ExposureManager(config)

        # Register USDCAD BUY
        manager.register_position("USDCAD", "forex_major", 1.0, direction="BUY")

        # EURUSD BUY should be allowed (correlation checking disabled)
        can_open, reason = manager.can_open_position(
            symbol="EURUSD", asset_class="forex_major", risk_amount=200.0, direction="BUY"
        )
        assert can_open is True
        assert reason == "OK"

    def test_negative_correlation_no_direction_provided(self):
        """Test that negative correlation checking is skipped when direction not provided."""
        config = {
            "risk_management": {
                "correlation_management": {
                    "enabled": True,
                    "negative_correlation_groups": {
                        "USDCAD": ["EURUSD"],
                        "EURUSD": ["USDCAD"],
                    },
                }
            }
        }
        manager = ExposureManager(config)

        # Register USDCAD BUY
        manager.register_position("USDCAD", "forex_major", 1.0, direction="BUY")

        # EURUSD without direction should be allowed (no direction = no correlation check)
        can_open, reason = manager.can_open_position(
            symbol="EURUSD",
            asset_class="forex_major",
            risk_amount=200.0,
            # No direction parameter
        )
        assert can_open is True
        assert reason == "OK"

    def test_positive_and_negative_correlation_together(self):
        """Test that both positive and negative correlation checks work together."""
        config = {
            "risk_management": {
                "correlation_management": {
                    "enabled": True,
                    "correlation_groups": {
                        "EURUSD": ["GBPUSD"],  # Positive correlation
                        "GBPUSD": ["EURUSD"],
                    },
                    "negative_correlation_groups": {
                        "USDCAD": ["EURUSD"],  # Negative correlation
                        "EURUSD": ["USDCAD"],
                    },
                }
            }
        }
        manager = ExposureManager(config)

        # Register USDCAD BUY (negatively correlated with EURUSD)
        manager.register_position("USDCAD", "forex_major", 1.0, direction="BUY")

        # EURUSD BUY should be rejected (negative correlation conflict)
        can_open, reason = manager.can_open_position(
            symbol="EURUSD", asset_class="forex_major", risk_amount=200.0, direction="BUY"
        )
        assert can_open is False
        assert "Negative correlation conflict" in reason

        # Reset
        manager.reset_tracking()

        # Register EURUSD BUY
        manager.register_position("EURUSD", "forex_major", 1.0, direction="BUY")

        # GBPUSD BUY should be allowed (positive correlation - same direction)
        can_open, reason = manager.can_open_position(
            symbol="GBPUSD", asset_class="forex_major", risk_amount=200.0, direction="BUY"
        )
        assert can_open is True

        # GBPUSD SELL should be rejected (positive correlation - different direction)
        can_open, reason = manager.can_open_position(
            symbol="GBPUSD", asset_class="forex_major", risk_amount=200.0, direction="SELL"
        )
        assert can_open is False
        assert "Positive correlation conflict" in reason

    def test_unregister_position_removes_direction_tracking(self):
        """Test that unregistering position removes direction tracking."""
        config = {
            "risk_management": {
                "correlation_management": {
                    "enabled": True,
                    "negative_correlation_groups": {
                        "USDCAD": ["EURUSD"],
                        "EURUSD": ["USDCAD"],
                    },
                }
            }
        }
        manager = ExposureManager(config)

        # Register USDCAD BUY
        manager.register_position("USDCAD", "forex_major", 1.0, direction="BUY")
        assert "USDCAD" in manager.position_directions

        # Unregister should remove direction tracking
        manager.unregister_position("USDCAD", "forex_major", 1.0)
        assert "USDCAD" not in manager.position_directions

        # Now EURUSD BUY should be allowed (no conflict)
        can_open, reason = manager.can_open_position(
            symbol="EURUSD", asset_class="forex_major", risk_amount=200.0, direction="BUY"
        )
        assert can_open is True

    def test_correlation_groups_invalid_config_structure(self):
        """Test that invalid correlation_groups config structure is handled."""
        config = {
            "risk_management": {
                "correlation_management": {
                    "enabled": True,
                    "correlation_groups": {
                        "EURUSD": "INVALID_NOT_LIST",  # Not a list
                    },
                }
            }
        }
        manager = ExposureManager(config)

        # Should handle gracefully and use empty list
        assert "EURUSD" in manager.correlated_pairs
        # Should not crash

    def test_negative_correlation_groups_invalid_config_structure(self):
        """Test that invalid negative_correlation_groups config structure is handled."""
        config = {
            "risk_management": {
                "correlation_management": {
                    "enabled": True,
                    "negative_correlation_groups": {
                        "USDCAD": "INVALID_NOT_LIST",  # Not a list
                    },
                }
            }
        }
        manager = ExposureManager(config)

        # Should handle gracefully and use empty list
        assert "USDCAD" in manager.negative_correlated_pairs
        # Should not crash

    def test_check_correlation_conflict_empty_position_directions(self):
        """Test that _check_correlation_conflict returns None when position_directions is empty."""
        config = {
            "risk_management": {
                "correlation_management": {
                    "enabled": True,
                    "negative_correlation_groups": {
                        "USDCAD": ["EURUSD"],
                    },
                }
            }
        }
        manager = ExposureManager(config)

        # No positions registered, so position_directions is empty
        assert len(manager.position_directions) == 0

        # Should return None (no conflict)
        conflict = manager._check_correlation_conflict("EURUSD", "BUY")
        assert conflict is None
