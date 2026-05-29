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

from trading_core.utils.logger import get_logger

logger = get_logger(__name__)

_ASSET_CLASSES = ("forex_major", "forex_jpy", "commodities", "crypto")


class ConfigValidationError(ValueError):
    """Raised when configuration violates a required invariant."""


def validate_position_management_config(config: dict) -> None:
    """Validate position_management config for asset classes AND per-symbol overrides.

    Args:
        config: Full bot config dict.

    Raises:
        ConfigValidationError: If any invariant is violated.
    """
    violations: list[str] = []

    # Asset-class-level config (default.yaml position_management section)
    pm_config = config.get("position_management", {})
    for asset_class in _ASSET_CLASSES:
        asset_config = pm_config.get(asset_class)
        if not asset_config:
            continue
        _check_invariant(
            label=asset_class,
            be_trigger=asset_config.get("breakeven_trigger"),
            tr_activation=asset_config.get("trailing_activation"),
            violations=violations,
        )

    # Per-symbol overrides (active_symbols.yaml symbols section)
    # Symbol overrides can shadow either field independently, so resolve the
    # *effective* value: symbol value if set, else its asset class's value.
    symbols_config = config.get("symbols", {})
    if isinstance(symbols_config, dict):
        for symbol, symbol_cfg in symbols_config.items():
            if not isinstance(symbol_cfg, dict):
                continue
            if "breakeven_trigger" not in symbol_cfg and "trailing_activation" not in symbol_cfg:
                continue

            asset_class = _resolve_asset_class(symbol_cfg)
            asset_defaults = pm_config.get(asset_class, {}) if asset_class else {}

            effective_be = symbol_cfg.get(
                "breakeven_trigger", asset_defaults.get("breakeven_trigger")
            )
            effective_tr = symbol_cfg.get(
                "trailing_activation", asset_defaults.get("trailing_activation")
            )

            _check_invariant(
                label=f"symbols.{symbol}",
                be_trigger=effective_be,
                tr_activation=effective_tr,
                violations=violations,
            )

    if violations:
        msg = "Invalid position_management config:\n  - " + "\n  - ".join(violations)
        raise ConfigValidationError(msg)

    logger.debug("✅ position_management config validated")


def _check_invariant(
    label: str,
    be_trigger: float | None,
    tr_activation: float | None,
    violations: list[str],
) -> None:
    """Add a violation if trailing_activation <= breakeven_trigger."""
    if be_trigger is None or tr_activation is None:
        return
    if tr_activation <= be_trigger:
        violations.append(
            f"{label}: trailing_activation ({tr_activation}) must be > "
            f"breakeven_trigger ({be_trigger}). Breakeven must trigger first so "
            f"BREAKEVEN_STOP and TRAILING_STOP can be distinguished on close."
        )


def _resolve_asset_class(symbol_cfg: dict) -> str | None:
    """Map a symbol config's asset_class string to a canonical class name.

    active_symbols.yaml uses "forex_majors" and "forex_crosses" for the
    symbol asset_class but default.yaml's position_management section
    keys on "forex_major" and "forex_jpy". Normalize here.
    """
    raw = symbol_cfg.get("asset_class")
    if not raw:
        return None
    mapping = {
        "forex_majors": "forex_major",
        "forex_major": "forex_major",
        "forex_crosses": "forex_jpy",
        "forex_jpy": "forex_jpy",
        "commodities": "commodities",
        "crypto": "crypto",
    }
    return mapping.get(raw, raw)
