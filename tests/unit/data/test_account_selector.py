"""
Unit tests for AccountSelector service.

Tests account selection and switching logic for multi-account trading.
"""

import pytest
from trading_core.data.repositories import AccountRepository
from trading_core.data.services.account_selector import AccountSelector


class TestAccountSelector:
    """Test AccountSelector for multi-account trading."""

    @pytest.mark.asyncio
    async def test_get_active_account_single_account(self):
        """Test getting active account when only one account exists."""
        # Create single active account
        repo = AccountRepository()
        account_data = {
            "account_id": 12345678,
            "broker_name": "Exness",
            "account_number": "12345678",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
            "is_active": True,
        }
        created = await repo.create(account_data)

        selector = AccountSelector()
        account = await selector.get_active_account()

        assert account is not None
        assert account.account_id == 12345678
        assert account.is_active is True

        # Cleanup
        await repo.delete(created.id)

    @pytest.mark.asyncio
    async def test_get_active_account_multiple_accounts(self):
        """Test getting active account when multiple accounts exist."""
        # Create multiple active accounts
        repo = AccountRepository()
        accounts = []
        for i in range(3):
            account_data = {
                "account_id": 10000000 + i,
                "broker_name": f"Broker{i}",
                "account_number": f"1000000{i}",
                "account_type": "DEMO",
                "balance": 10000.0,
                "leverage": 100,
                "is_active": True,
            }
            acc = await repo.create(account_data)
            accounts.append(acc)

        selector = AccountSelector()
        account = await selector.get_active_account()

        # Should return first active account (or configured default)
        assert account is not None
        assert account.is_active is True
        assert account.account_id in [10000000, 10000001, 10000002]

        # Cleanup
        for acc in accounts:
            await repo.delete(acc.id)

    @pytest.mark.asyncio
    async def test_get_active_account_no_accounts(self):
        """Test getting active account when no accounts exist."""
        selector = AccountSelector()
        account = await selector.get_active_account()

        assert account is None

    @pytest.mark.asyncio
    async def test_get_active_account_only_inactive(self):
        """Test getting active account when only inactive accounts exist."""
        # Create inactive account
        repo = AccountRepository()
        account_data = {
            "account_id": 20000000,
            "broker_name": "Exness",
            "account_number": "20000000",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
            "is_active": False,
        }
        created = await repo.create(account_data)

        selector = AccountSelector()
        account = await selector.get_active_account()

        assert account is None

        # Cleanup
        await repo.delete(created.id)

    @pytest.mark.asyncio
    async def test_switch_account_success(self):
        """Test switching to a different account."""
        # Create multiple accounts
        repo = AccountRepository()
        accounts = []
        for i in range(2):
            account_data = {
                "account_id": 30000000 + i,
                "broker_name": f"Broker{i}",
                "account_number": f"3000000{i}",
                "account_type": "DEMO",
                "balance": 10000.0,
                "leverage": 100,
                "is_active": True,
            }
            acc = await repo.create(account_data)
            accounts.append(acc)

        selector = AccountSelector()

        # Switch to second account
        result = await selector.switch_account(30000001)

        assert result is True
        current = await selector.get_active_account()
        assert current.account_id == 30000001

        # Cleanup
        for acc in accounts:
            await repo.delete(acc.id)

    @pytest.mark.asyncio
    async def test_switch_account_not_found(self):
        """Test switching to non-existent account returns False."""
        selector = AccountSelector()
        result = await selector.switch_account(99999999)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_account_by_id(self):
        """Test getting specific account by ID."""
        # Create account
        repo = AccountRepository()
        account_data = {
            "account_id": 40000000,
            "broker_name": "Exness",
            "account_number": "40000000",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
            "is_active": True,
        }
        created = await repo.create(account_data)

        selector = AccountSelector()
        account = await selector.get_account_by_id(40000000)

        assert account is not None
        assert account.account_id == 40000000

        # Cleanup
        await repo.delete(created.id)

    @pytest.mark.asyncio
    async def test_get_all_active_accounts(self):
        """Test getting all active accounts."""
        # Create mix of active and inactive accounts
        repo = AccountRepository()
        accounts = []

        # Create 2 active accounts
        for i in range(2):
            account_data = {
                "account_id": 50000000 + i,
                "broker_name": f"Broker{i}",
                "account_number": f"5000000{i}",
                "account_type": "DEMO",
                "balance": 10000.0,
                "leverage": 100,
                "is_active": True,
            }
            acc = await repo.create(account_data)
            accounts.append(acc)

        # Create 1 inactive account
        inactive_data = {
            "account_id": 50000002,
            "broker_name": "Broker2",
            "account_number": "50000002",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
            "is_active": False,
        }
        inactive = await repo.create(inactive_data)
        accounts.append(inactive)

        selector = AccountSelector()
        active_accounts = await selector.get_all_active_accounts()

        assert len(active_accounts) == 2
        assert all(acc.is_active for acc in active_accounts)

        # Cleanup
        for acc in accounts:
            await repo.delete(acc.id)

    @pytest.mark.asyncio
    async def test_get_active_account_cache_invalidation_on_deactivation(self):
        """Test that cached account is cleared when account becomes inactive."""
        # Create account
        repo = AccountRepository()
        account_data = {
            "account_id": 60000000,
            "broker_name": "Exness",
            "account_number": "60000000",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
            "is_active": True,
        }
        created = await repo.create(account_data)

        selector = AccountSelector()

        # First call should cache the account
        account1 = await selector.get_active_account()
        assert account1 is not None
        assert account1.account_id == 60000000

        # Deactivate the account
        await repo.deactivate(created.id)

        # Second call should clear cache and return None
        account2 = await selector.get_active_account()
        assert account2 is None

        # Verify cache was cleared
        assert selector.get_current_account_id() is None

        # Cleanup
        await repo.delete(created.id)

    @pytest.mark.asyncio
    async def test_get_active_account_cache_invalidation_on_deletion(self):
        """Test that cached account is cleared when account is deleted."""
        # Create account
        repo = AccountRepository()
        account_data = {
            "account_id": 70000000,
            "broker_name": "Exness",
            "account_number": "70000000",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
            "is_active": True,
        }
        created = await repo.create(account_data)

        selector = AccountSelector()

        # First call should cache the account
        account1 = await selector.get_active_account()
        assert account1 is not None
        assert account1.account_id == 70000000

        # Delete the account
        await repo.delete(created.id)

        # Second call should clear cache and return None
        account2 = await selector.get_active_account()
        assert account2 is None

        # Cleanup is automatic (already deleted)

    @pytest.mark.asyncio
    async def test_switch_account_inactive_account(self):
        """Test switching to inactive account returns False."""
        # Create inactive account
        repo = AccountRepository()
        account_data = {
            "account_id": 80000000,
            "broker_name": "Exness",
            "account_number": "80000000",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
            "is_active": False,
        }
        created = await repo.create(account_data)

        selector = AccountSelector()
        result = await selector.switch_account(80000000)

        assert result is False

        # Cleanup
        await repo.delete(created.id)

    @pytest.mark.asyncio
    async def test_switch_account_active_to_inactive(self):
        """Test switching to account that becomes inactive."""
        # Create account
        repo = AccountRepository()
        account_data = {
            "account_id": 90000000,
            "broker_name": "Exness",
            "account_number": "90000000",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
            "is_active": True,
        }
        created = await repo.create(account_data)

        selector = AccountSelector()

        # Deactivate before switching
        await repo.deactivate(created.id)

        # Try to switch to now-inactive account
        result = await selector.switch_account(90000000)

        assert result is False

        # Cleanup
        await repo.delete(created.id)

    @pytest.mark.asyncio
    async def test_get_current_account_id(self):
        """Test getting current cached account ID."""
        selector = AccountSelector()

        # Initially should be None
        current_id = selector.get_current_account_id()
        assert current_id is None

        # Create account
        repo = AccountRepository()
        account_data = {
            "account_id": 100000000,
            "broker_name": "Exness",
            "account_number": "100000000",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
            "is_active": True,
        }
        await repo.create(account_data)

        # Get active account (should cache the ID)
        await selector.get_active_account()

        # Now should return cached ID
        current_id = selector.get_current_account_id()
        assert current_id == 100000000

        # Cleanup
        account = await repo.get_by_account_id(100000000)
        if account:
            await repo.delete(account.id)

    @pytest.mark.asyncio
    async def test_get_current_account_id_after_switch(self):
        """Test that current account ID updates after switching accounts."""
        # Create multiple accounts
        repo = AccountRepository()
        accounts = []
        for i in range(2):
            account_data = {
                "account_id": 110000000 + i,
                "broker_name": f"Broker{i}",
                "account_number": f"11000000{i}",
                "account_type": "DEMO",
                "balance": 10000.0,
                "leverage": 100,
                "is_active": True,
            }
            acc = await repo.create(account_data)
            accounts.append(acc)

        selector = AccountSelector()

        # Get first active account
        await selector.get_active_account()
        current_id = selector.get_current_account_id()
        assert current_id in [110000000, 110000001]

        # Switch to second account
        await selector.switch_account(110000001)

        # Current ID should be updated
        current_id = selector.get_current_account_id()
        assert current_id == 110000001

        # Cleanup
        for acc in accounts:
            await repo.delete(acc.id)

    @pytest.mark.asyncio
    async def test_get_current_account_id_when_none_cached(self):
        """Test getting current account ID when nothing is cached."""
        selector = AccountSelector()

        # No operations performed, cache should be None
        current_id = selector.get_current_account_id()
        assert current_id is None
