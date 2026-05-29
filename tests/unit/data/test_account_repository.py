"""
Unit tests for AccountRepository.

Tests CRUD operations for TradingAccount model.
"""

import pytest
from sqlalchemy.exc import IntegrityError
from trading_core.data.repositories import AccountRepository


class TestAccountRepository:
    """Test AccountRepository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_account_success(self):
        """Test creating a trading account successfully."""
        repo = AccountRepository()

        account_data = {
            "account_id": 12345678,
            "broker_name": "Exness",
            "account_number": "12345678",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
        }

        account = await repo.create(account_data)

        assert account is not None
        assert account.account_id == 12345678
        assert account.broker_name == "Exness"
        assert account.balance == 10000.0

        # Cleanup
        await repo.delete(account.id)

    @pytest.mark.asyncio
    async def test_get_account_by_id(self):
        """Test getting account by ID."""
        repo = AccountRepository()

        # Create account first
        account_data = {
            "account_id": 11111111,
            "broker_name": "Exness",
            "account_number": "11111111",
            "account_type": "DEMO",
            "balance": 5000.0,
            "leverage": 200,
        }
        created = await repo.create(account_data)

        # Get by ID
        fetched = await repo.get_by_id(created.id)

        assert fetched is not None
        assert fetched.account_id == 11111111
        assert fetched.balance == 5000.0

        # Cleanup
        await repo.delete(created.id)

    @pytest.mark.asyncio
    async def test_get_account_by_account_id(self):
        """Test getting account by MT5 account_id."""
        repo = AccountRepository()

        # Create account
        account_data = {
            "account_id": 22222222,
            "broker_name": "XM",
            "account_number": "22222222",
            "account_type": "LIVE",
            "balance": 15000.0,
            "leverage": 500,
        }
        created = await repo.create(account_data)

        # Get by account_id
        fetched = await repo.get_by_account_id(22222222)

        assert fetched is not None
        assert fetched.account_id == 22222222
        assert fetched.broker_name == "XM"
        assert fetched.account_type == "LIVE"

        # Cleanup
        await repo.delete(created.id)

    @pytest.mark.asyncio
    async def test_get_active_accounts(self):
        """Test getting only active accounts."""
        repo = AccountRepository()

        # Create active account
        active_data = {
            "account_id": 33333333,
            "broker_name": "Exness",
            "account_number": "33333333",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
            "is_active": True,
        }
        active = await repo.create(active_data)

        # Create inactive account
        inactive_data = {
            "account_id": 44444444,
            "broker_name": "XM",
            "account_number": "44444444",
            "account_type": "DEMO",
            "balance": 5000.0,
            "leverage": 100,
            "is_active": False,
        }
        inactive = await repo.create(inactive_data)

        # Get active accounts
        active_accounts = await repo.get_active_accounts()

        assert len(active_accounts) >= 1
        assert all(acc.is_active for acc in active_accounts)

        # Cleanup
        await repo.delete(active.id)
        await repo.delete(inactive.id)

    @pytest.mark.asyncio
    async def test_update_account_balance(self):
        """Test updating account balance."""
        repo = AccountRepository()

        # Create account
        account_data = {
            "account_id": 55555555,
            "broker_name": "Exness",
            "account_number": "55555555",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
        }
        account = await repo.create(account_data)

        # Update balance
        updated = await repo.update_balance(account.id, 12500.0, 12600.0)

        assert updated.balance == 12500.0
        assert updated.equity == 12600.0

        # Cleanup
        await repo.delete(account.id)

    @pytest.mark.asyncio
    async def test_deactivate_account(self):
        """Test deactivating an account."""
        repo = AccountRepository()

        # Create account
        account_data = {
            "account_id": 66666666,
            "broker_name": "Exness",
            "account_number": "66666666",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
            "is_active": True,
        }
        account = await repo.create(account_data)

        # Deactivate
        deactivated = await repo.deactivate(account.id)

        assert deactivated.is_active is False

        # Cleanup
        await repo.delete(account.id)

    @pytest.mark.asyncio
    async def test_get_account_by_broker_and_number(self):
        """Test getting account by broker name and account number."""
        repo = AccountRepository()

        # Create account
        account_data = {
            "account_id": 77777777,
            "broker_name": "Exness",
            "account_number": "77777777",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
        }
        created = await repo.create(account_data)

        # Get by broker and number
        fetched = await repo.get_by_broker_and_number("Exness", "77777777")

        assert fetched is not None
        assert fetched.account_id == 77777777
        assert fetched.broker_name == "Exness"

        # Cleanup
        await repo.delete(created.id)

    @pytest.mark.asyncio
    async def test_list_accounts_pagination(self):
        """Test listing accounts with pagination."""
        repo = AccountRepository()

        # Create multiple accounts
        accounts = []
        for i in range(3):
            data = {
                "account_id": 80000000 + i,
                "broker_name": f"Broker{i}",
                "account_number": f"8000000{i}",
                "account_type": "DEMO",
                "balance": 10000.0,
                "leverage": 100,
            }
            acc = await repo.create(data)
            accounts.append(acc)

        # List with pagination
        page1 = await repo.list_accounts(limit=2, offset=0)

        assert len(page1) <= 2

        # Cleanup
        for acc in accounts:
            await repo.delete(acc.id)

    @pytest.mark.asyncio
    async def test_account_not_found_error(self):
        """Test getting non-existent account returns None."""
        repo = AccountRepository()

        account = await repo.get_by_id(999999)

        assert account is None

    @pytest.mark.asyncio
    async def test_duplicate_account_error(self):
        """Test creating duplicate account raises error."""
        repo = AccountRepository()

        # Create first account
        account_data = {
            "account_id": 99999999,
            "broker_name": "Exness",
            "account_number": "99999999",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
        }
        first = await repo.create(account_data)

        # Try to create duplicate
        with pytest.raises(IntegrityError):
            await repo.create(account_data)

        # Cleanup
        await repo.delete(first.id)

    @pytest.mark.asyncio
    async def test_update_balance_account_not_found(self):
        """Test updating balance for non-existent account raises error."""
        repo = AccountRepository()

        with pytest.raises(ValueError, match="Account with ID .* not found"):
            await repo.update_balance(999999, 10000.0, 10100.0)

    @pytest.mark.asyncio
    async def test_deactivate_account_not_found(self):
        """Test deactivating non-existent account raises error."""
        repo = AccountRepository()

        with pytest.raises(ValueError, match="Account with ID .* not found"):
            await repo.deactivate(999999)

    @pytest.mark.asyncio
    async def test_delete_account(self):
        """Test deleting an account."""
        repo = AccountRepository()

        # Create account
        account_data = {
            "account_id": 88888888,
            "broker_name": "Exness",
            "account_number": "88888888",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
        }
        created = await repo.create(account_data)

        # Delete
        deleted = await repo.delete(created.id)

        assert deleted is True

        # Verify deleted
        account = await repo.get_by_id(created.id)
        assert account is None

    @pytest.mark.asyncio
    async def test_delete_account_not_found(self):
        """Test deleting non-existent account returns False."""
        repo = AccountRepository()

        deleted = await repo.delete(999999)

        assert deleted is False
