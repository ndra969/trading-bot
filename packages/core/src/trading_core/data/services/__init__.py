"""
Data services for business logic (core layer).

AccountSyncService moved to trading_worker.services — it orchestrates the
MT5 connector (worker layer), so it does not belong in core.
"""

from .account_selector import AccountSelector

__all__ = ["AccountSelector"]
