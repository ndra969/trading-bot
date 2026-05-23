# Coding Standards

Code style and conventions for the trading bot project.

## Tools

| Tool | Purpose | Command |
|------|---------|---------|
| **Black** | Code formatting | `uv run black src/ tests/` |
| **Ruff** | Linting | `uv run ruff check src/ tests/` |
| **MyPy** | Type checking | `uv run mypy src/trading_bot/` |
| **Pytest** | Testing | `uv run pytest` |

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Files/Modules | `snake_case` | `position_manager.py` |
| Classes | `PascalCase` | `PositionManager` |
| Functions/Methods | `snake_case` | `calculate_pip_value()` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_POSITIONS` |
| Private | `_leading_underscore` | `_internal_method()` |
| Type Variables | `PascalCase` | `T = TypeVar("T")` |

## Code Style

### Required

- **Python 3.12+** features (modern syntax)
- **Type hints** for all function parameters and returns
- **Async/await** for I/O operations
- **f-strings** for string formatting
- **Line length**: 100 characters max

### Example

```python
from typing import Optional
from decimal import Decimal

async def calculate_position_size(
    balance: Decimal,
    risk_percent: float,
    sl_pips: int,
    pip_value: Decimal,
) -> Decimal:
    """Calculate position size based on risk parameters.

    Args:
        balance: Account balance in USD
        risk_percent: Risk per trade (e.g., 0.01 for 1%)
        sl_pips: Stop loss distance in pips
        pip_value: USD value per pip

    Returns:
        Position size in lots

    Raises:
        ValueError: If risk parameters are invalid
    """
    if risk_percent <= 0 or risk_percent > 0.05:
        raise ValueError("Risk must be between 0 and 5%")

    risk_amount = balance * Decimal(str(risk_percent))
    volume = risk_amount / (sl_pips * pip_value)

    return volume.quantize(Decimal("0.01"))
```

## Import Organization

```python
# 1. Standard library
import asyncio
from datetime import datetime
from decimal import Decimal

# 2. Third-party
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

# 3. Local imports
from trading_bot.config import Config
from trading_bot.data.models import Position
```

## Error Handling

### Use Custom Exceptions

```python
# Define in src/trading_bot/exceptions/
class TradingError(Exception):
    """Base trading bot exception."""

class RiskLimitExceededError(TradingError):
    """Raised when risk limits are exceeded."""

# Usage
if total_risk > MAX_RISK:
    raise RiskLimitExceededError(
        f"Risk {total_risk} exceeds limit {MAX_RISK}"
    )
```

### Async Context

```python
async def execute_trade(signal: TradingSignal) -> Position:
    try:
        position = await position_manager.open(signal)
    except MT5ConnectionError as e:
        logger.error(f"MT5 connection failed: {e}")
        raise
    except RiskLimitExceededError as e:
        logger.warning(f"Risk limit hit: {e}")
        return None

    return position
```

## Configuration

**Never hardcode values** - use configuration:

```python
# ❌ Bad
MAX_POSITIONS = 5
RISK_PERCENT = 0.01

# ✅ Good
from trading_bot.config import config

max_positions = config.trading.max_positions
risk_percent = config.risk.risk_per_trade
```

## Logging

Use `loguru` with structured logging:

```python
from trading_bot.utils.logger import get_logger

logger = get_logger(__name__)

# Info level for normal events
logger.info(f"Position opened: {position.id} @ {position.entry_price}")

# Warning for non-critical issues
logger.warning(f"High correlation detected: {correlation:.2f}")

# Error for failures
logger.error(f"Order rejected: {error.message}", exc_info=True)

# Debug for development only
logger.debug(f"Strategy analysis: {analysis_result}")
```

## Testing Requirements

| Type | Coverage | Location |
|------|----------|----------|
| Unit tests | 85% min | `tests/unit/` |
| Critical components | 95% min | `tests/unit/test_risk_*.py` |
| Integration tests | Required | `tests/integration/` |
| Property tests | For math invariants | `tests/properties/` |

### Test Naming

```python
def test_<what>_<condition>_<expected>():
    """Test that <description>."""

# Examples
def test_position_size_with_zero_balance_raises_error():
    ...

def test_breakeven_trigger_at_70_percent_moves_sl_to_entry():
    ...
```

## Documentation

### Docstrings (Google style)

```python
def calculate_pip_value(symbol: str, lot_size: float) -> Decimal:
    """Calculate USD value per pip for a symbol.

    Args:
        symbol: Trading symbol (e.g., "EURUSD")
        lot_size: Position size in lots

    Returns:
        USD value per pip

    Raises:
        ValueError: If symbol is not supported
    """
```

### Comments

- **WHY, not WHAT** - code shows what, comments explain why
- **Avoid obvious comments** - don't comment what's clear from code
- **Update comments** - keep them in sync with code

```python
# ❌ Bad: states the obvious
counter = counter + 1  # Increment counter

# ✅ Good: explains why
# MT5 needs 1-based ticket numbering, but DB uses 0-based
counter = counter + 1
```

## Architecture Principles

1. **Single Responsibility** - One class, one purpose
2. **Dependency Injection** - Pass dependencies, don't import them
3. **Repository Pattern** - Separate data access from business logic
4. **Async-First** - All I/O is async
5. **Configuration over Code** - Use YAML configs, not magic values

## Pre-Commit Workflow

```bash
# Before committing
uv run black src/ tests/                    # Format
uv run ruff check src/ tests/ --fix         # Lint and auto-fix
uv run mypy src/trading_bot/                # Type check
uv run pytest --cov=src/trading_bot         # Test
uv run trading-bot start --dry-run          # Validate runtime
```

## Related Documentation

- [Architecture Guide](../architecture/architecture-guide.md) - System structure
- [Testing Guide](dry-run-guide.md) - Dry-run testing
- [Troubleshooting](troubleshooting-guide.md) - Common issues
