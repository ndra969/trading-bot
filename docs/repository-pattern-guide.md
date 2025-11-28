# Repository Pattern Implementation Guide

This guide covers the repository pattern implementation for clean database operations in the trading bot system.

## Overview

The repository pattern provides a clean architecture for database operations with:
- **Separation of concerns** between data access and business logic
- **Type-safe** database operations with proper error handling
- **Dependency injection** for easy testing and maintainability
- **Consistent interface** across all database operations

## Architecture

### 📁 Directory Structure

```
src/trading_bot/data/
├── repositories/
│   ├── __init__.py              # Package exports
│   ├── base.py                  # Base repository classes
│   ├── factory.py               # Repository factory and management
│   ├── trades.py                # Trades repository implementation
│   ├── market_data.py           # Market data repository
│   └── system_health.py         # System health repository
├── models.py                    # SQLAlchemy models
├── database.py                  # Database connection management
└── __init__.py                  # Data package exports

src/trading_bot/services/
├── __init__.py                  # Service exports
└── database.py                  # High-level database services

scripts/
└── test_repository_pattern.py   # Usage examples and tests
```

### 🏗️ Core Components

#### 1. Base Repository Classes

**BaseRepository**: Abstract base class with common CRUD operations
- `create(obj_in)` - Create new record
- `get_by_id(id)` - Get record by primary key
- `get_multi()` - Get multiple records with pagination
- `update(db_obj, obj_in)` - Update existing record
- `delete(id)` - Delete record by ID
- `count()` - Count total records
- `exists(id)` - Check if record exists

**TimestampedRepository**: Extends BaseRepository for timestamped models
- `get_created_after(timestamp)` - Records created after time
- `get_created_between(start, end)` - Records in time range
- `get_updated_since(timestamp)` - Records updated since time
- `get_latest(limit)` - Most recent records

#### 2. Repository Factory

**RepositoryFactory**: Creates repository instances with proper dependencies
**RepositoryRegistry**: Registers repositories for dependency injection
**RepositoryManager**: High-level manager for repository access

#### 3. Service Layer

**DatabaseService**: High-level service with convenient methods
- Automatic session management
- Repository access through dependency injection
- Context manager support for easy cleanup

## Usage Examples

### Basic Repository Usage

```python
from trading_bot.data.repositories import RepositoryManager
from trading_bot.data.database import get_db_session
from trading_bot.config import DatabaseConfig

# Initialize
config = DatabaseConfig(url="sqlite+aiosqlite:///trading_bot.db")
async with get_db_session(config) as session:
    manager = RepositoryManager(session)

    # Get repository
    trades_repo = manager.get_repository("trades")

    # Use repository
    trades = await trades_repo.get_multi(limit=10)
    active_trades = await trades_repo.get_active_trades()
    performance = await trades_repo.get_performance_summary()
```

### Service Layer Usage

```python
from trading_bot.services import DatabaseService, create_database_service

# Using context manager (recommended)
async with create_database_service(config) as db_service:
    # High-level operations
    trades = await db_service.get_active_trades()
    performance = await db_service.get_trade_performance_summary()

    # Create new trade
    trade_data = {
        "symbol": "EURUSD",
        "trade_type": "BUY",
        "entry_price": 1.0850,
        "volume": 0.1,
        "strategy": "supply_demand"
    }
    new_trade = await db_service.create_trade(trade_data)

    # Health check
    await db_service.create_health_check(
        component="database",
        status=ComponentStatus.HEALTHY,
        metrics={"connection_count": 5}
    )
```

### Direct Service Usage

```python
from trading_bot.services import DatabaseService

# Manual initialization
service = DatabaseService(config)
await service.initialize()

try:
    # Use service
    trades = await service.get_active_trades()
finally:
    await service.close()
```

## Specialized Repository Methods

### TradesRepository

```python
trades_repo = manager.get_repository("trades")

# Get trades by symbol
eurusd_trades = await trades_repo.get_by_symbol("EURUSD")

# Performance analysis
performance = await trades_repo.get_performance_summary(
    symbol="EURUSD",
    strategy="supply_demand"
)

# Profitable trades analysis
profitable = await trades_repo.get_profitable_trades(limit=10)

# Confidence-based filtering
high_conf = await trades_repo.get_by_confidence_range(80, 100)

# Risk-reward analysis
good_rr = await trades_repo.get_by_risk_reward_range(2.0, 5.0)
```

### MarketDataRepository

```python
market_data_repo = manager.get_repository("market_data")

# Get latest OHLCV data
latest = await market_data_repo.get_latest_by_symbol_timeframe(
    symbol="EURUSD",
    timeframe="H1"
)

# Historical data range
historical = await market_data_repo.get_by_date_range(
    symbol="EURUSD",
    timeframe="H1",
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 31)
)

# Zone analysis
zone_data = await market_data_repo.get_with_zones(
    symbol="EURUSD",
    timeframe="H1",
    zone_type="demand"
)

# Price range statistics
price_stats = await market_data_repo.get_price_range(
    symbol="EURUSD",
    timeframe="H1"
)
```

### SystemHealthRepository

```python
health_repo = manager.get_repository("system_health")

# Create health check
await health_repo.create_health_check(
    component="mt5",
    status=ComponentStatus.HEALTHY,
    metrics={"latency": 45, "connection_count": 1}
)

# Get component status
status_summary = await health_repo.get_component_status_summary(hours=24)

# Error analysis
errors = await health_repo.get_error_records(component="mt5")

# Uptime calculation
uptime = await health_repo.get_component_uptime(
    component="mt5",
    hours=24
)

# Performance trends
trends = await health_repo.get_component_health_trend(
    component="mt5",
    hours=24,
    interval_minutes=60
)
```

## Creating New Repositories

### 1. Create Repository Class

```python
# src/trading_bot/data/repositories/my_entity.py
from datetime import datetime
from typing import Dict, List, Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import MyEntity
from .base import TimestampedRepository
from .factory import register_repository

class MyEntityRepository(TimestampedRepository[MyEntity, Dict, Dict]):
    """Repository for MyEntity operations."""

    async def get_by_custom_field(self, *, field_value: str) -> List[MyEntity]:
        """Custom query method."""
        stmt = select(MyEntity).where(MyEntity.custom_field == field_value)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active_entities(self) -> List[MyEntity]:
        """Get active entities."""
        stmt = select(MyEntity).where(MyEntity.is_active == True)
        result = await self.session.execute(stmt)
        return result.scalars().all()

# Register the repository
register_repository("my_entity", MyEntityRepository, MyEntity)
```

### 2. Add to __init__.py

```python
# src/trading_bot/data/repositories/__init__.py
from .my_entity import MyEntityRepository

__all__ = [
    # ... other exports
    "MyEntityRepository",
]
```

### 3. Use in Service Layer

```python
# src/trading_bot/services/database.py
async def get_my_entities(self, active_only: bool = True) -> List[MyEntity]:
    """Get my entities with optional filtering."""
    repo = self.repositories.get_repository("my_entity")

    if active_only:
        return await repo.get_active_entities()
    else:
        return await repo.get_multi()
```

## Testing with Repository Pattern

### Mock Repository for Testing

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
async def mock_trades_repo():
    """Mock trades repository for testing."""
    repo = AsyncMock()
    repo.get_multi = AsyncMock(return_value=[])
    repo.get_active_trades = AsyncMock(return_value=[])
    repo.create = AsyncMock(return_value=MagicMock())
    return repo

@pytest.fixture
async def mock_repository_manager(mock_trades_repo):
    """Mock repository manager."""
    manager = AsyncMock()
    manager.get_repository = AsyncMock(return_value=mock_trades_repo)
    return manager

async def test_get_active_trades(mock_repository_manager):
    """Test getting active trades."""
    service = DatabaseService(config)
    service._repository_manager = mock_repository_manager

    trades = await service.get_active_trades()

    # Verify repository was called
    mock_repository_manager.get_repository.assert_called_with("trades")
    assert isinstance(trades, list)
```

### Integration Tests

```python
async def test_repository_integration():
    """Integration test with real database."""
    config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")

    async with create_database_service(config) as db_service:
        # Test actual database operations
        trade_data = {
            "symbol": "EURUSD",
            "trade_type": "BUY",
            "entry_price": 1.0850,
            "volume": 0.1,
            "status": TradeStatus.OPEN
        }

        # Create trade
        trade = await db_service.create_trade(trade_data)
        assert trade.symbol == "EURUSD"

        # Retrieve trade
        retrieved = await db_service.get_trade_by_id(trade.id)
        assert retrieved.id == trade.id
```

## Performance Considerations

### Bulk Operations

```python
# Efficient bulk insert
data_list = [
    {"symbol": "EURUSD", "close_price": 1.0850, ...},
    {"symbol": "EURUSD", "close_price": 1.0851, ...},
    # ... more data
]

created_records = await market_data_repo.bulk_insert_ohlcv(data_list)
```

### Query Optimization

```python
# Use specific field queries
trades = await trades_repo.get_by_field(
    field_name="strategy",
    field_value="supply_demand"
)

# Paginated results
page1 = await trades_repo.get_multi(skip=0, limit=50)
page2 = await trades_repo.get_multi(skip=50, limit=50)
```

### Connection Management

```python
# Always use context managers for proper cleanup
async with create_database_service(config) as db_service:
    # Operations here
    pass  # Automatic cleanup

# Or manual cleanup
service = DatabaseService(config)
await service.initialize()
try:
    # Operations
    pass
finally:
    await service.close()
```

## Best Practices

### 1. Use Service Layer for Business Logic

```python
# ✅ Good: Use service layer
async with create_database_service(config) as db_service:
    trades = await db_service.get_active_trades()
    performance = await db_service.get_trade_performance_summary()

# ❌ Avoid: Direct database access
from trading_bot.data.repositories import TradesRepository
# ... complex initialization and session management
```

### 2. Leverage Type Safety

```python
# ✅ Good: Type-safe operations
from trading_bot.data.models import TradeStatus
trades = await trades_repo.get_by_status(status=TradeStatus.OPEN)

# ❌ Avoid: String literals
trades = await trades_repo.get_by_status(status="OPEN")  # No type safety
```

### 3. Handle Errors Properly

```python
try:
    async with create_database_service(config) as db_service:
        trades = await db_service.get_active_trades()
except DatabaseError as e:
    logger.error(f"Database error: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise
```

### 4. Use Context Managers

```python
# ✅ Good: Automatic cleanup
async with create_database_service(config) as db_service:
    # Operations

# ❌ Avoid: Manual resource management
service = DatabaseService(config)
await service.initialize()
# ... operations (might forget to close)
```

## Migration from Old Database Access

### Before (Direct Database Access)

```python
from trading_bot.data.database import get_db_session
from trading_bot.data.models import Trade

async def get_trades():
    async for session in get_db_session(config):
        stmt = select(Trade).where(Trade.status == "OPEN")
        result = await session.execute(stmt)
        return result.scalars().all()
```

### After (Repository Pattern)

```python
from trading_bot.services import create_database_service

async def get_trades():
    async with create_database_service(config) as db_service:
        return await db_service.get_active_trades()
```

## Benefits

1. **Clean Architecture**: Separation of concerns between data access and business logic
2. **Type Safety**: Full type hints and compile-time error checking
3. **Testability**: Easy to mock repositories for unit testing
4. **Maintainability**: Consistent interface across all database operations
5. **Flexibility**: Easy to switch database backends or add new query methods
6. **Performance**: Optimized queries and connection management
7. **Error Handling**: Centralized error handling and logging
8. **Dependency Injection**: Easy to manage dependencies and test in isolation

The repository pattern provides a robust foundation for database operations that scales with the complexity of the trading bot system while maintaining clean, maintainable code.