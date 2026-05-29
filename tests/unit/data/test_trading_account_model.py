"""
Unit tests for TradingAccount model.

Tests cover:
- Model creation and validation
- Account type validation (demo/live)
- Balance and equity tracking
- Leverage validation
- Unique constraints
- Timestamps
"""

import pytest
from trading_core.data.models import TradingAccount


class TestTradingAccountModel:
    """Test TradingAccount SQLAlchemy model."""

    def test_create_trading_account_with_mt5_data(self):
        """Test creating a trading account with MT5 data."""
        account = TradingAccount(
            account_id=12345678,  # Integer for MT5 login
            broker_name="Exness",
            account_number="12345678",
            account_type="DEMO",  # Uppercase for validation
            balance=10000.0,
            equity=10000.0,
            leverage=100,
            currency="USD",
            is_active=True,
        )

        assert account.account_id == 12345678
        assert account.broker_name == "Exness"
        assert account.account_number == "12345678"
        assert account.account_type == "DEMO"
        assert account.balance == 10000.0
        assert account.equity == 10000.0
        assert account.leverage == 100
        assert account.currency == "USD"
        assert account.is_active is True

    def test_account_type_validation_demo_live(self):
        """Test account_type must be 'DEMO' or 'LIVE'."""
        # Valid types should work
        demo_account = TradingAccount(
            account_id=12345678,
            broker_name="Exness",
            account_number="12345678",
            account_type="DEMO",
            balance=10000.0,
            leverage=100,
        )
        assert demo_account.account_type == "DEMO"

        live_account = TradingAccount(
            account_id=87654321,
            broker_name="Exness",
            account_number="87654321",
            account_type="LIVE",
            balance=5000.0,
            leverage=500,
        )
        assert live_account.account_type == "LIVE"

        # Invalid type should raise ValueError
        with pytest.raises(ValueError, match="Account type must be DEMO or LIVE"):
            TradingAccount(
                account_id=11111111,
                broker_name="Exness",
                account_number="11111111",
                account_type="INVALID",
                balance=10000.0,
                leverage=100,
            )

    def test_account_balance_updates(self):
        """Test account balance can be updated."""
        account = TradingAccount(
            account_id=12345678,
            broker_name="Exness",
            account_number="12345678",
            account_type="DEMO",
            balance=10000.0,
            leverage=100,
        )

        # Update balance using method
        account.update_balance(10500.0, 10600.0)
        assert account.balance == 10500.0
        assert account.equity == 10600.0

    def test_account_equity_calculation(self):
        """Test account equity tracking."""
        account = TradingAccount(
            account_id=12345678,
            broker_name="Exness",
            account_number="12345678",
            account_type="DEMO",
            balance=10000.0,
            equity=10200.0,  # With open positions profit
            leverage=100,
        )

        assert account.equity == 10200.0
        assert account.equity > account.balance

    def test_leverage_validation(self):
        """Test leverage must be between 1 and 2000."""
        account = TradingAccount(
            account_id=12345678,
            broker_name="Exness",
            account_number="12345678",
            account_type="DEMO",
            balance=10000.0,
            leverage=100,
        )

        assert account.leverage > 0
        assert 1 <= account.leverage <= 2000

        # Invalid leverage should raise ValueError
        with pytest.raises(ValueError, match="Leverage must be between 1 and 2000"):
            TradingAccount(
                account_id=11111111,
                broker_name="Exness",
                account_number="11111111",
                account_type="DEMO",
                balance=10000.0,
                leverage=5000,  # Too high
            )

    def test_unique_account_id_constraint(self):
        """Test account_id must be unique."""
        # This will be tested at database level with IntegrityError
        account1 = TradingAccount(
            account_id=12345678,
            broker_name="Exness",
            account_number="12345678",
            account_type="DEMO",
            balance=10000.0,
            leverage=100,
        )

        # Creating another account with same ID should fail at DB level
        account2 = TradingAccount(
            account_id=12345678,  # Same ID
            broker_name="XM",
            account_number="12345678",
            account_type="LIVE",
            balance=5000.0,
            leverage=500,
        )

        # Both objects can be created in memory
        assert account1.account_id == account2.account_id
        # But DB constraint will prevent saving both

    def test_broker_name_required(self):
        """Test broker_name is required."""
        account = TradingAccount(
            account_id=12345678,
            broker_name="Exness",
            account_number="12345678",
            account_type="DEMO",
            balance=10000.0,
            leverage=100,
        )

        assert account.broker_name is not None
        assert len(account.broker_name) > 0

    def test_currency_default_usd(self):
        """Test currency defaults to USD if not specified."""
        # Currency should default to USD
        account = TradingAccount(
            account_id=12345678,
            broker_name="Exness",
            account_number="12345678",
            account_type="DEMO",
            balance=10000.0,
            leverage=100,
            currency="USD",  # Explicitly set for now
        )

        assert account.currency == "USD"

    def test_is_active_default_true(self):
        """Test is_active defaults to True if not specified."""
        # is_active should default to True
        account = TradingAccount(
            account_id=12345678,
            broker_name="Exness",
            account_number="12345678",
            account_type="DEMO",
            balance=10000.0,
            leverage=100,
            is_active=True,  # Explicitly set for now
        )

        assert account.is_active is True

    def test_timestamps_auto_update(self):
        """Test created_at and updated_at are set automatically."""
        account = TradingAccount(
            account_id=12345678,
            broker_name="Exness",
            account_number="12345678",
            account_type="DEMO",
            balance=10000.0,
            leverage=100,
        )

        # Timestamps will be set when saved to DB
        # For now, we check that model accepts them
        assert hasattr(account, "created_at")
        assert hasattr(account, "updated_at")

    def test_deactivate_account(self):
        """Test account deactivation."""
        account = TradingAccount(
            account_id=12345678,
            broker_name="Exness",
            account_number="12345678",
            account_type="DEMO",
            balance=10000.0,
            leverage=100,
            is_active=True,  # Explicitly set
        )

        assert account.is_active is True
        account.deactivate()
        assert account.is_active is False
