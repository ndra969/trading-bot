"""
Unit tests for AccountSyncService.

Tests MT5 account synchronization and balance updates.
"""

from unittest.mock import MagicMock, patch

import pytest

from trading_bot.data.repositories import AccountRepository
from trading_bot.data.services.account_sync_service import AccountSyncService


class TestAccountSyncService:
    """Test AccountSyncService for MT5 account synchronization."""

    @pytest.mark.asyncio
    async def test_sync_account_success(self):
        """Test syncing account data from MT5 successfully."""
        # Mock MT5 account info as dict (account_info property returns dict)
        mt5_account_info_dict = {
            "login": 12345678,
            "balance": 10500.0,
            "equity": 10600.0,
            "leverage": 100,
            "server": "Exness-MT5Real",
            "currency": "USD",
        }

        # Create account in DB first
        repo = AccountRepository()
        account_data = {
            "account_id": 12345678,
            "broker_name": "Exness",
            "account_number": "12345678",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
        }
        created = await repo.create(account_data)

        # Mock MT5 connector - account_info is a property that returns dict
        with patch("trading_bot.data.services.account_sync_service.MT5Connector") as mock_mt5:
            mock_mt5_instance = MagicMock()
            mock_mt5_instance.is_connected.return_value = True
            mock_mt5_instance.account_info = mt5_account_info_dict  # Property returns dict
            mock_mt5.return_value = mock_mt5_instance

            # Sync account
            sync_service = AccountSyncService()
            result = await sync_service.sync_account(12345678)

            assert result is True
            # Verify balance was updated
            updated = await repo.get_by_account_id(12345678)
            assert updated.balance == 10500.0
            assert updated.equity == 10600.0

        # Cleanup
        await repo.delete(created.id)

    @pytest.mark.asyncio
    async def test_sync_account_not_found(self):
        """Test syncing non-existent account returns False."""
        sync_service = AccountSyncService()

        with patch("trading_bot.data.services.account_sync_service.MT5Connector") as mock_mt5:
            mock_mt5_instance = MagicMock()
            mock_mt5.return_value = mock_mt5_instance

            result = await sync_service.sync_account(99999999)

            assert result is False

    @pytest.mark.asyncio
    async def test_sync_account_mt5_connection_error(self):
        """Test handling MT5 connection errors gracefully."""
        # Create account
        repo = AccountRepository()
        account_data = {
            "account_id": 11111111,
            "broker_name": "Exness",
            "account_number": "11111111",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
        }
        created = await repo.create(account_data)

        # Mock MT5 connection failure
        with patch("trading_bot.data.services.account_sync_service.MT5Connector") as mock_mt5:
            mock_mt5_instance = MagicMock()
            mock_mt5_instance.get_account_info.side_effect = Exception("MT5 connection failed")
            mock_mt5.return_value = mock_mt5_instance

            sync_service = AccountSyncService()
            result = await sync_service.sync_account(11111111)

            assert result is False

        # Cleanup
        await repo.delete(created.id)

    @pytest.mark.asyncio
    async def test_sync_all_active_accounts(self):
        """Test syncing all active accounts."""
        # Create multiple accounts
        repo = AccountRepository()
        accounts = []
        for i in range(3):
            account_data = {
                "account_id": 20000000 + i,
                "broker_name": f"Broker{i}",
                "account_number": f"2000000{i}",
                "account_type": "DEMO",
                "balance": 10000.0,
                "leverage": 100,
                "is_active": True,
            }
            acc = await repo.create(account_data)
            accounts.append(acc)

        # Mock MT5 for all accounts - use property that returns dict
        call_count = [0]  # Mutable to track calls
        account_ids = [20000000, 20000001, 20000002]

        with patch("trading_bot.data.services.account_sync_service.MT5Connector") as mock_mt5:
            def create_mock_instance():
                mock_instance = MagicMock()
                mock_instance.is_connected.return_value = True
                # account_info is a property that returns dict
                account_id = account_ids[call_count[0] % 3]
                call_count[0] += 1
                mock_instance.account_info = {
                    "login": account_id,
                    "balance": 11000.0,  # Updated balance
                    "equity": 11100.0,
                    "leverage": 100,
                    "server": "Test-Server",
                    "currency": "USD",
                }
                return mock_instance

            mock_mt5.side_effect = lambda: create_mock_instance()

            sync_service = AccountSyncService()
            results = await sync_service.sync_all_active_accounts()

            assert results["total"] == 3
            assert results["success"] == 3
            assert results["failed"] == 0

        # Cleanup
        for acc in accounts:
            await repo.delete(acc.id)

    @pytest.mark.asyncio
    async def test_sync_inactive_account_skipped(self):
        """Test that inactive accounts are skipped during sync_all."""
        # Create inactive account
        repo = AccountRepository()
        account_data = {
            "account_id": 30000000,
            "broker_name": "TestBroker",
            "account_number": "30000000",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
            "is_active": False,
        }
        created = await repo.create(account_data)

        with patch("trading_bot.data.services.account_sync_service.MT5Connector") as mock_mt5:
            mock_mt5_instance = MagicMock()
            mock_mt5.return_value = mock_mt5_instance

            sync_service = AccountSyncService()
            await sync_service.sync_all_active_accounts()

            # Should not attempt to sync inactive account
            assert mock_mt5_instance.get_account_info.call_count == 0

        # Cleanup
        await repo.delete(created.id)

    @pytest.mark.asyncio
    async def test_check_account_connection_status(self):
        """Test checking MT5 account connection status."""
        with patch("trading_bot.data.services.account_sync_service.MT5Connector") as mock_mt5:
            mock_mt5_instance = MagicMock()
            mock_mt5_instance.is_connected.return_value = True
            mock_mt5.return_value = mock_mt5_instance

            sync_service = AccountSyncService()
            is_connected = await sync_service.check_connection_status()

            assert is_connected is True

    @pytest.mark.asyncio
    async def test_get_sync_status_report(self):
        """Test getting sync status report."""
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

        # Mock MT5
        mt5_account_info = MagicMock()
        mt5_account_info.login = 40000000
        mt5_account_info.balance = 10500.0
        mt5_account_info.equity = 10600.0
        mt5_account_info.leverage = 100
        mt5_account_info.server = "Exness-MT5Real"
        mt5_account_info.currency = "USD"

        with patch("trading_bot.data.services.account_sync_service.MT5Connector") as mock_mt5:
            mock_mt5_instance = MagicMock()
            mock_mt5_instance.get_account_info.return_value = mt5_account_info
            mock_mt5.return_value = mock_mt5_instance

            sync_service = AccountSyncService()
            await sync_service.sync_account(40000000)

            # Get status report
            report = sync_service.get_last_sync_status()

            assert report is not None
            assert "last_sync_time" in report
            assert "accounts_synced" in report

        # Cleanup
        await repo.delete(created.id)

    @pytest.mark.asyncio
    async def test_sync_partial_failure(self):
        """Test handling partial failures when syncing multiple accounts."""
        # Create multiple accounts
        repo = AccountRepository()
        accounts = []
        for i in range(3):
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

        # Mock MT5 - first succeeds, second fails, third succeeds
        call_count = [0]
        account_ids = [50000000, 50000001, 50000002]

        with patch("trading_bot.data.services.account_sync_service.MT5Connector") as mock_mt5:
            def create_mock_instance():
                mock_instance = MagicMock()
                account_id = account_ids[call_count[0]]
                call_count[0] += 1

                if account_id == 50000001:
                    mock_instance.is_connected.return_value = False
                    mock_instance.account_info = None
                else:
                    mock_instance.is_connected.return_value = True
                    mock_instance.account_info = {
                        "login": account_id,
                        "balance": 11000.0,
                        "equity": 11100.0,
                        "leverage": 100,
                        "server": "Test-Server",
                        "currency": "USD",
                    }
                return mock_instance

            mock_mt5.side_effect = lambda: create_mock_instance()

            sync_service = AccountSyncService()
            results = await sync_service.sync_all_active_accounts()

            assert results["total"] == 3
            assert results["success"] == 2
            assert results["failed"] == 1

        # Cleanup
        for acc in accounts:
            await repo.delete(acc.id)

    @pytest.mark.asyncio
    async def test_ensure_account_exists_creates_new_account(self):
        """Test ensure_account_exists creates new account when not in DB."""
        # Mock MT5 connector
        mt5_account_info = {
            "login": 88888888,
            "balance": 15000.0,
            "equity": 15200.0,
            "leverage": 200,
            "currency": "USD",
            "server": "Exness-MT5Real",
            "company": "Exness",
            "trade_mode": 2,  # LIVE account
        }

        with patch("trading_bot.data.services.account_sync_service.MT5Connector") as mock_mt5:
            mock_mt5_instance = MagicMock()
            mock_mt5_instance.is_connected.return_value = True
            mock_mt5_instance.account_info = mt5_account_info
            mock_mt5.return_value = mock_mt5_instance

            sync_service = AccountSyncService()
            result = await sync_service.ensure_account_exists(mock_mt5_instance)

            assert result is not None
            assert result.account_id == 88888888
            assert result.balance == 15000.0
            assert result.equity == 15200.0
            assert result.account_type == "LIVE"
            assert result.broker_name == "Exness"

            # Cleanup
            await sync_service.repository.delete(result.id)

    @pytest.mark.asyncio
    async def test_ensure_account_exists_updates_existing(self):
        """Test ensure_account_exists updates existing account."""
        repo = AccountRepository()
        account_data = {
            "account_id": 77777777,
            "broker_name": "Exness",
            "account_number": "77777777",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
        }
        created = await repo.create(account_data)

        # Mock MT5 connector with updated balance
        mt5_account_info = {
            "login": 77777777,
            "balance": 12500.0,  # Updated balance
            "equity": 12700.0,
            "leverage": 100,
            "currency": "USD",
        }

        with patch("trading_bot.data.services.account_sync_service.MT5Connector") as mock_mt5:
            mock_mt5_instance = MagicMock()
            mock_mt5_instance.is_connected.return_value = True
            mock_mt5_instance.account_info = mt5_account_info
            mock_mt5.return_value = mock_mt5_instance

            sync_service = AccountSyncService()
            result = await sync_service.ensure_account_exists(mock_mt5_instance)

            assert result is not None
            assert result.account_id == 77777777

            # Verify balance was updated
            updated = await repo.get_by_account_id(77777777)
            assert updated.balance == 12500.0
            assert updated.equity == 12700.0

            # Cleanup
            await repo.delete(created.id)

    @pytest.mark.asyncio
    async def test_ensure_account_exists_not_connected(self):
        """Test ensure_account_exists returns None when MT5 not connected."""
        with patch("trading_bot.data.services.account_sync_service.MT5Connector") as mock_mt5:
            mock_mt5_instance = MagicMock()
            mock_mt5_instance.is_connected.return_value = False
            mock_mt5.return_value = mock_mt5_instance

            sync_service = AccountSyncService()
            result = await sync_service.ensure_account_exists(mock_mt5_instance)

            assert result is None

    @pytest.mark.asyncio
    async def test_ensure_account_exists_no_account_info(self):
        """Test ensure_account_exists returns None when account_info is None."""
        with patch("trading_bot.data.services.account_sync_service.MT5Connector") as mock_mt5:
            mock_mt5_instance = MagicMock()
            mock_mt5_instance.is_connected.return_value = True
            mock_mt5_instance.account_info = None
            mock_mt5.return_value = mock_mt5_instance

            sync_service = AccountSyncService()
            result = await sync_service.ensure_account_exists(mock_mt5_instance)

            assert result is None

    @pytest.mark.asyncio
    async def test_ensure_account_exists_missing_login(self):
        """Test ensure_account_exists returns None when login ID missing."""
        mt5_account_info = {
            "balance": 15000.0,
            "equity": 15200.0,
            # Missing "login" field
        }

        with patch("trading_bot.data.services.account_sync_service.MT5Connector") as mock_mt5:
            mock_mt5_instance = MagicMock()
            mock_mt5_instance.is_connected.return_value = True
            mock_mt5_instance.account_info = mt5_account_info
            mock_mt5.return_value = mock_mt5_instance

            sync_service = AccountSyncService()
            result = await sync_service.ensure_account_exists(mock_mt5_instance)

            assert result is None

    @pytest.mark.asyncio
    async def test_ensure_account_exists_determines_demo_account(self):
        """Test ensure_account_exists correctly identifies DEMO account type."""
        mt5_account_info = {
            "login": 66666666,
            "balance": 10000.0,
            "equity": 10200.0,
            "leverage": 100,
            "currency": "USD",
            "server": "MetaTrader5-Demo",
            "company": "MetaQuotes",
            "trade_mode": 0,  # DEMO
        }

        with patch("trading_bot.data.services.account_sync_service.MT5Connector") as mock_mt5:
            mock_mt5_instance = MagicMock()
            mock_mt5_instance.is_connected.return_value = True
            mock_mt5_instance.account_info = mt5_account_info
            mock_mt5.return_value = mock_mt5_instance

            sync_service = AccountSyncService()
            result = await sync_service.ensure_account_exists(mock_mt5_instance)

            assert result is not None
            assert result.account_type == "DEMO"

            # Cleanup
            await sync_service.repository.delete(result.id)

    @pytest.mark.asyncio
    async def test_ensure_account_exists_extracts_broker_from_server(self):
        """Test ensure_account_exists extracts broker name from server when company unknown."""
        mt5_account_info = {
            "login": 55555555,
            "balance": 10000.0,
            "equity": 10200.0,
            "leverage": 100,
            "currency": "USD",
            "server": "ICMarketsSC-Demo",
            "company": "Unknown",
            "trade_mode": 0,
        }

        with patch("trading_bot.data.services.account_sync_service.MT5Connector") as mock_mt5:
            mock_mt5_instance = MagicMock()
            mock_mt5_instance.is_connected.return_value = True
            mock_mt5_instance.account_info = mt5_account_info
            mock_mt5.return_value = mock_mt5_instance

            sync_service = AccountSyncService()
            result = await sync_service.ensure_account_exists(mock_mt5_instance)

            assert result is not None
            assert result.broker_name == "ICMarketsSC"

            # Cleanup
            await sync_service.repository.delete(result.id)

    @pytest.mark.asyncio
    async def test_ensure_account_exists_exception_handling(self):
        """Test ensure_account_exists handles exceptions gracefully."""
        with patch("trading_bot.data.services.account_sync_service.MT5Connector") as mock_mt5:
            mock_mt5_instance = MagicMock()
            mock_mt5_instance.is_connected.side_effect = Exception("Connection error")
            mock_mt5.return_value = mock_mt5_instance

            sync_service = AccountSyncService()
            result = await sync_service.ensure_account_exists(mock_mt5_instance)

            assert result is None

    @pytest.mark.asyncio
    async def test_sync_account_uses_provided_connector(self):
        """Test sync_account uses provided mt5_connector when connected."""
        repo = AccountRepository()
        account_data = {
            "account_id": 44444444,
            "broker_name": "Exness",
            "account_number": "44444444",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
        }
        created = await repo.create(account_data)

        # Create service with provided connector
        mt5_account_info = {
            "login": 44444444,
            "balance": 13500.0,
            "equity": 13700.0,
            "leverage": 100,
            "server": "Exness-MT5Real",
            "currency": "USD",
        }

        with patch("trading_bot.data.services.account_sync_service.MT5Connector") as mock_mt5:
            mock_mt5_instance = MagicMock()
            mock_mt5_instance.is_connected.return_value = True
            mock_mt5_instance.account_info = mt5_account_info
            mock_mt5.return_value = mock_mt5_instance

            sync_service = AccountSyncService(mt5_connector=mock_mt5_instance)
            result = await sync_service.sync_account(44444444)

            assert result is True
            updated = await repo.get_by_account_id(44444444)
            assert updated.balance == 13500.0
            assert updated.equity == 13700.0

            # Cleanup
            await repo.delete(created.id)

    @pytest.mark.asyncio
    async def test_sync_account_account_info_none(self):
        """Test sync_account handles None account_info gracefully."""
        repo = AccountRepository()
        account_data = {
            "account_id": 33333333,
            "broker_name": "Exness",
            "account_number": "33333333",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
        }
        created = await repo.create(account_data)

        with patch("trading_bot.data.services.account_sync_service.MT5Connector") as mock_mt5:
            mock_mt5_instance = MagicMock()
            mock_mt5_instance.is_connected.return_value = True
            mock_mt5_instance.account_info = None  # None account_info
            mock_mt5.return_value = mock_mt5_instance

            sync_service = AccountSyncService()
            result = await sync_service.sync_account(33333333)

            assert result is False

            # Cleanup
            await repo.delete(created.id)

    @pytest.mark.asyncio
    async def test_sync_account_account_id_mismatch(self):
        """Test sync_account handles account ID mismatch."""
        repo = AccountRepository()
        account_data = {
            "account_id": 22222222,
            "broker_name": "Exness",
            "account_number": "22222222",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
        }
        created = await repo.create(account_data)

        mt5_account_info = {
            "login": 99999999,  # Different account ID
            "balance": 13500.0,
            "equity": 13700.0,
            "leverage": 100,
            "server": "Exness-MT5Real",
            "currency": "USD",
        }

        with patch("trading_bot.data.services.account_sync_service.MT5Connector") as mock_mt5:
            mock_mt5_instance = MagicMock()
            mock_mt5_instance.is_connected.return_value = True
            mock_mt5_instance.account_info = mt5_account_info
            mock_mt5.return_value = mock_mt5_instance

            sync_service = AccountSyncService()
            result = await sync_service.sync_account(22222222)

            assert result is False

            # Cleanup
            await repo.delete(created.id)

    @pytest.mark.asyncio
    async def test_sync_account_exception_handling(self):
        """Test sync_account handles exceptions and tracks errors."""
        repo = AccountRepository()
        account_data = {
            "account_id": 11111111,
            "broker_name": "Exness",
            "account_number": "11111111",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
        }
        created = await repo.create(account_data)

        with patch("trading_bot.data.services.account_sync_service.MT5Connector") as mock_mt5:
            mock_mt5_instance = MagicMock()
            mock_mt5_instance.is_connected.side_effect = Exception("Unexpected error")
            mock_mt5.return_value = mock_mt5_instance

            sync_service = AccountSyncService()
            result = await sync_service.sync_account(11111111)

            assert result is False

            # Check error was tracked
            status = sync_service.get_last_sync_status()
            assert status["accounts_failed"] == 1
            assert len(status["errors"]) == 1
            assert status["errors"][0]["account_id"] == 11111111

            # Cleanup
            await repo.delete(created.id)

    @pytest.mark.asyncio
    async def test_check_connection_status_exception(self):
        """Test check_connection_status handles exceptions gracefully."""
        with patch("trading_bot.data.services.account_sync_service.MT5Connector") as mock_mt5:
            mock_mt5.side_effect = Exception("Connection check failed")

            sync_service = AccountSyncService()
            is_connected = await sync_service.check_connection_status()

            assert is_connected is False

    @pytest.mark.asyncio
    async def test_sync_all_active_accounts_empty_list(self):
        """Test sync_all_active_accounts handles no active accounts."""
        # Ensure no active accounts exist
        repo = AccountRepository()
        # Create inactive account only
        account_data = {
            "account_id": 99999999,
            "broker_name": "Test",
            "account_number": "99999999",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
            "is_active": False,
        }
        created = await repo.create(account_data)

        sync_service = AccountSyncService()
        results = await sync_service.sync_all_active_accounts()

        assert results["total"] == 0
        assert results["success"] == 0
        assert results["failed"] == 0

        # Cleanup
        await repo.delete(created.id)

    @pytest.mark.asyncio
    async def test_sync_account_no_equity_in_mt5(self):
        """Test sync_account handles None equity from MT5."""
        repo = AccountRepository()
        account_data = {
            "account_id": 88888888,
            "broker_name": "Exness",
            "account_number": "88888888",
            "account_type": "DEMO",
            "balance": 10000.0,
            "leverage": 100,
        }
        created = await repo.create(account_data)

        # MT5 returns None equity
        mt5_account_info = {
            "login": 88888888,
            "balance": 14000.0,
            "equity": None,  # No equity data
            "leverage": 100,
            "server": "Exness-MT5Real",
            "currency": "USD",
        }

        with patch("trading_bot.data.services.account_sync_service.MT5Connector") as mock_mt5:
            mock_mt5_instance = MagicMock()
            mock_mt5_instance.is_connected.return_value = True
            mock_mt5_instance.account_info = mt5_account_info
            mock_mt5.return_value = mock_mt5_instance

            sync_service = AccountSyncService()
            result = await sync_service.sync_account(88888888)

            assert result is True
            updated = await repo.get_by_account_id(88888888)
            assert updated.balance == 14000.0

            # Cleanup
            await repo.delete(created.id)
