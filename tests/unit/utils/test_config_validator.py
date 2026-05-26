"""Tests for startup config validation."""

import pytest

from trading_bot.utils.config_validator import (
    ConfigValidationError,
    validate_position_management_config,
)


class TestValidPositionManagementConfig:
    """Configs that should pass validation."""

    def test_empty_config_passes(self):
        validate_position_management_config({})

    def test_no_position_management_section_passes(self):
        validate_position_management_config({"trading": {"dry_run": True}})

    def test_trailing_above_breakeven_passes(self):
        validate_position_management_config(
            {
                "position_management": {
                    "forex_major": {
                        "breakeven_trigger": 30,
                        "trailing_activation": 40,
                    }
                }
            }
        )

    def test_partial_config_passes(self):
        # Asset class without both fields → no invariant to check
        validate_position_management_config(
            {
                "position_management": {
                    "forex_major": {"breakeven_trigger": 30},
                    "forex_jpy": {"trailing_activation": 50},
                }
            }
        )

    def test_all_asset_classes_valid(self):
        validate_position_management_config(
            {
                "position_management": {
                    "forex_major": {"breakeven_trigger": 30, "trailing_activation": 40},
                    "forex_jpy": {"breakeven_trigger": 40, "trailing_activation": 50},
                    "commodities": {"breakeven_trigger": 50, "trailing_activation": 80},
                    "crypto": {"breakeven_trigger": 400, "trailing_activation": 600},
                }
            }
        )


class TestInvalidPositionManagementConfig:
    """Configs that should fail validation."""

    def test_trailing_equal_to_breakeven_fails(self):
        with pytest.raises(ConfigValidationError, match="forex_major"):
            validate_position_management_config(
                {
                    "position_management": {
                        "forex_major": {
                            "breakeven_trigger": 30,
                            "trailing_activation": 30,
                        }
                    }
                }
            )

    def test_trailing_below_breakeven_fails(self):
        with pytest.raises(ConfigValidationError, match="forex_jpy"):
            validate_position_management_config(
                {
                    "position_management": {
                        "forex_jpy": {
                            "breakeven_trigger": 40,
                            "trailing_activation": 30,
                        }
                    }
                }
            )

    def test_multiple_violations_all_reported(self):
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_position_management_config(
                {
                    "position_management": {
                        "forex_major": {
                            "breakeven_trigger": 30,
                            "trailing_activation": 20,
                        },
                        "crypto": {
                            "breakeven_trigger": 400,
                            "trailing_activation": 100,
                        },
                    }
                }
            )
        msg = str(exc_info.value)
        assert "forex_major" in msg
        assert "crypto" in msg


class TestPerSymbolOverrides:
    """Per-symbol overrides must satisfy the same invariant."""

    def test_per_symbol_override_valid_passes(self):
        validate_position_management_config(
            {
                "position_management": {
                    "commodities": {"breakeven_trigger": 50, "trailing_activation": 80},
                },
                "symbols": {
                    "XAUUSD": {
                        "asset_class": "commodities",
                        "breakeven_trigger": 175,
                        "trailing_activation": 280,
                    },
                },
            }
        )

    def test_per_symbol_override_violation_fails(self):
        with pytest.raises(ConfigValidationError, match="symbols.XAUUSD"):
            validate_position_management_config(
                {
                    "position_management": {
                        "commodities": {"breakeven_trigger": 50, "trailing_activation": 80},
                    },
                    "symbols": {
                        "XAUUSD": {
                            "asset_class": "commodities",
                            "breakeven_trigger": 280,
                            "trailing_activation": 175,
                        },
                    },
                }
            )

    def test_symbol_only_overrides_one_field_uses_asset_default_for_other(self):
        """If symbol only sets BE, validator must check it against asset-class trailing."""
        with pytest.raises(ConfigValidationError, match="symbols.XAGUSD"):
            validate_position_management_config(
                {
                    "position_management": {
                        "commodities": {"breakeven_trigger": 50, "trailing_activation": 80},
                    },
                    "symbols": {
                        "XAGUSD": {
                            "asset_class": "commodities",
                            "breakeven_trigger": 200,  # > asset trailing 80 → violation
                        },
                    },
                }
            )

    def test_forex_majors_alias_normalizes_to_forex_major(self):
        """active_symbols uses "forex_majors" — validator should map to "forex_major"."""
        validate_position_management_config(
            {
                "position_management": {
                    "forex_major": {"breakeven_trigger": 30, "trailing_activation": 40},
                },
                "symbols": {
                    "EURUSD": {
                        "asset_class": "forex_majors",
                        "breakeven_trigger": 25,
                        # trailing comes from asset_class default (40) — 25 < 40 ✅
                    },
                },
            }
        )
