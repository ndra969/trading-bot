"""Service layer extracted from TradingBot.

Each service holds a reference to the parent TradingBot and operates on
its dependencies (mt5, position_manager, etc.) via that reference. Moving
methods into services keeps main.py focused on orchestration while letting
each concern live in its own file.
"""

from .account_sync_service import AccountSyncService
from .execution_service import ExecutionService

__all__ = ["AccountSyncService", "ExecutionService"]
