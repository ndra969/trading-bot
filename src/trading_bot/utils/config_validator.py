"""Startup configuration validation.

Enforces invariants that the rest of the codebase relies on. Raising at
startup is much friendlier than wrong-looking behavior at runtime.

Invariants enforced:
  1. For each asset class in position_management:
     trailing_activation > breakeven_trigger
     (so breakeven SL is locked in before trailing activates — required by
     the CloseReason resolver to distinguish BREAKEVEN_STOP vs TRAILING_STOP)
"""

from __future__ import annotations

from trading_bot.utils.logger import get_logger

logger = get_logger(__name__)

_ASSET_CLASSES = ("forex_major", "forex_jpy", "commodities", "crypto")


class ConfigValidationError(ValueError):
    """Raised when configuration violates a required invariant."""


def validate_position_management_config(config: dict) -> None:
    """Validate position_management config for all asset classes.

    Args:
        config: Full bot config dict.

    Raises:
        ConfigValidationError: If any invariant is violated.
    """
    pm_config = config.get("position_management", {})
    if not pm_config:
        logger.debug("No position_management config found — skipping validation")
        return

    violations: list[str] = []

    for asset_class in _ASSET_CLASSES:
        asset_config = pm_config.get(asset_class)
        if not asset_config:
            continue

        be_trigger = asset_config.get("breakeven_trigger")
        tr_activation = asset_config.get("trailing_activation")

        if be_trigger is None or tr_activation is None:
            continue  # Asset class doesn't use both → no invariant to check

        if tr_activation <= be_trigger:
            violations.append(
                f"{asset_class}: trailing_activation ({tr_activation}) must be > "
                f"breakeven_trigger ({be_trigger}). Breakeven must trigger first so "
                f"BREAKEVEN_STOP and TRAILING_STOP can be distinguished on close."
            )

    if violations:
        msg = "Invalid position_management config:\n  - " + "\n  - ".join(violations)
        raise ConfigValidationError(msg)

    logger.debug("✅ position_management config validated")
