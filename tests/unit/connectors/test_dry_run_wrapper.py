"""Tests for DryRunMT5Wrapper.

Verifies that:
1. In dry-run mode, write operations return simulated results without
   calling the real connector.
2. In live mode (dry_run=False), all calls pass through transparently.
3. Read operations always pass through regardless of dry_run flag.
4. Unrecognized attributes/methods are forwarded to wrapped connector.
5. Simulated history is correctly tracked and clearable.
"""

from unittest.mock import MagicMock

import pytest

from trading_bot.connectors.dry_run_wrapper import DryRunMT5Wrapper


@pytest.fixture
def mock_connector():
    """Mock MT5Connector with common methods."""
    connector = MagicMock()
    connector.is_connected.return_value = True
    connector.account_info = {"login": 12345, "balance": 10000.0}
    connector.terminal_info = {"name": "MetaTrader 5"}
    connector.health_check.return_value = {"connected": True, "trade_allowed": True}
    connector.get_positions.return_value = []
    connector.get_history_deal.return_value = None
    return connector


# ───────────────────────────────────────────────────────────────────────
# Dry-run mode: write operations are simulated
# ───────────────────────────────────────────────────────────────────────


class TestDryRunWriteOperations:
    """Write operations should be simulated when dry_run=True."""

    def test_place_order_simulated_in_dry_run(self, mock_connector):
        wrapper = DryRunMT5Wrapper(mock_connector, dry_run=True)
        result = wrapper.place_order(
            symbol="EURUSD", order_type="BUY", volume=0.01, price=1.1, sl=1.09, tp=1.12
        )

        # Real connector NOT called
        mock_connector.place_order.assert_not_called()

        # Result has expected shape
        assert result["success"] is True
        assert result["order"] >= 90_000_000  # Dry-run ticket range
        assert result["volume"] == 0.01
        assert result["price"] == 1.1
        assert "DRY-RUN" in result["comment"]

    def test_modify_position_simulated_in_dry_run(self, mock_connector):
        wrapper = DryRunMT5Wrapper(mock_connector, dry_run=True)
        result = wrapper.modify_position(ticket=12345, sl=1.09, tp=1.12)

        mock_connector.modify_position.assert_not_called()
        assert result["success"] is True
        assert result["modified"] is True
        assert result["sl_changed"] is True
        assert result["tp_changed"] is True

    def test_close_position_simulated_in_dry_run(self, mock_connector):
        wrapper = DryRunMT5Wrapper(mock_connector, dry_run=True)
        result = wrapper.close_position(ticket=12345, volume=0.01)

        mock_connector.close_position.assert_not_called()
        assert result["success"] is True
        assert result["ticket"] == 12345
        assert "DRY-RUN" in result["comment"]


# ───────────────────────────────────────────────────────────────────────
# Live mode: all calls pass through to real connector
# ───────────────────────────────────────────────────────────────────────


class TestLiveModePassthrough:
    """When dry_run=False, the wrapper is transparent."""

    def test_place_order_passes_through(self, mock_connector):
        expected = {"success": True, "order": 99999, "price": 1.10005}
        mock_connector.place_order.return_value = expected

        wrapper = DryRunMT5Wrapper(mock_connector, dry_run=False)
        result = wrapper.place_order(
            symbol="EURUSD", order_type="BUY", volume=0.01, price=1.1
        )

        mock_connector.place_order.assert_called_once()
        assert result == expected

    def test_modify_position_passes_through(self, mock_connector):
        expected = {"success": True, "modified": True, "message": "OK"}
        mock_connector.modify_position.return_value = expected

        wrapper = DryRunMT5Wrapper(mock_connector, dry_run=False)
        result = wrapper.modify_position(ticket=12345, sl=1.09)

        mock_connector.modify_position.assert_called_once_with(ticket=12345, sl=1.09, tp=None)
        assert result == expected

    def test_close_position_passes_through(self, mock_connector):
        expected = {"success": True, "ticket": 12345}
        mock_connector.close_position.return_value = expected

        wrapper = DryRunMT5Wrapper(mock_connector, dry_run=False)
        result = wrapper.close_position(ticket=12345, volume=0.01)

        mock_connector.close_position.assert_called_once()
        assert result == expected


# ───────────────────────────────────────────────────────────────────────
# Read operations always pass through
# ───────────────────────────────────────────────────────────────────────


class TestReadOperationsAlwaysPassthrough:
    """Read ops should pass through in both dry-run and live modes."""

    @pytest.mark.parametrize("dry_run", [True, False])
    def test_is_connected(self, mock_connector, dry_run):
        wrapper = DryRunMT5Wrapper(mock_connector, dry_run=dry_run)
        assert wrapper.is_connected() is True
        mock_connector.is_connected.assert_called_once()

    @pytest.mark.parametrize("dry_run", [True, False])
    def test_get_positions(self, mock_connector, dry_run):
        mock_connector.get_positions.return_value = [{"ticket": 1}]
        wrapper = DryRunMT5Wrapper(mock_connector, dry_run=dry_run)
        result = wrapper.get_positions(symbol="EURUSD")
        assert result == [{"ticket": 1}]

    @pytest.mark.parametrize("dry_run", [True, False])
    def test_get_history_deal(self, mock_connector, dry_run):
        expected = {"ticket": 123, "profit": 50.0}
        mock_connector.get_history_deal.return_value = expected
        wrapper = DryRunMT5Wrapper(mock_connector, dry_run=dry_run)
        assert wrapper.get_history_deal(123) == expected

    @pytest.mark.parametrize("dry_run", [True, False])
    def test_health_check(self, mock_connector, dry_run):
        wrapper = DryRunMT5Wrapper(mock_connector, dry_run=dry_run)
        assert wrapper.health_check()["connected"] is True

    @pytest.mark.parametrize("dry_run", [True, False])
    def test_account_info_property(self, mock_connector, dry_run):
        wrapper = DryRunMT5Wrapper(mock_connector, dry_run=dry_run)
        assert wrapper.account_info["login"] == 12345


# ───────────────────────────────────────────────────────────────────────
# Simulated history tracking
# ───────────────────────────────────────────────────────────────────────


class TestSimulatedHistory:
    """Wrapper should track all simulated operations."""

    def test_tracks_simulated_orders(self, mock_connector):
        wrapper = DryRunMT5Wrapper(mock_connector, dry_run=True)
        wrapper.place_order(symbol="EURUSD", order_type="BUY", volume=0.01, price=1.1)
        wrapper.place_order(symbol="GBPUSD", order_type="SELL", volume=0.02, price=1.3)

        orders = wrapper.get_simulated_orders()
        assert len(orders) == 2
        assert orders[0]["symbol"] == "EURUSD"
        assert orders[1]["symbol"] == "GBPUSD"

    def test_tracks_simulated_modifications(self, mock_connector):
        wrapper = DryRunMT5Wrapper(mock_connector, dry_run=True)
        wrapper.modify_position(ticket=100, sl=1.09)
        wrapper.modify_position(ticket=200, tp=1.20)

        mods = wrapper.get_simulated_modifications()
        assert len(mods) == 2
        assert mods[0]["ticket"] == 100
        assert mods[1]["tp"] == 1.20

    def test_tracks_simulated_closes(self, mock_connector):
        wrapper = DryRunMT5Wrapper(mock_connector, dry_run=True)
        wrapper.close_position(ticket=100, volume=0.01)

        closes = wrapper.get_simulated_closes()
        assert len(closes) == 1
        assert closes[0]["ticket"] == 100

    def test_clear_simulated_history(self, mock_connector):
        wrapper = DryRunMT5Wrapper(mock_connector, dry_run=True)
        wrapper.place_order(symbol="EURUSD", order_type="BUY", volume=0.01, price=1.1)
        wrapper.modify_position(ticket=100, sl=1.09)
        wrapper.close_position(ticket=200, volume=0.01)

        wrapper.clear_simulated_history()
        assert wrapper.get_simulated_orders() == []
        assert wrapper.get_simulated_modifications() == []
        assert wrapper.get_simulated_closes() == []

    def test_ticket_counter_increments(self, mock_connector):
        wrapper = DryRunMT5Wrapper(mock_connector, dry_run=True)
        r1 = wrapper.place_order(symbol="EURUSD", order_type="BUY", volume=0.01, price=1.1)
        r2 = wrapper.place_order(symbol="EURUSD", order_type="BUY", volume=0.01, price=1.1)

        assert r2["order"] == r1["order"] + 1

    def test_live_mode_does_not_track(self, mock_connector):
        mock_connector.place_order.return_value = {"success": True, "order": 9}
        wrapper = DryRunMT5Wrapper(mock_connector, dry_run=False)
        wrapper.place_order(symbol="EURUSD", order_type="BUY", volume=0.01, price=1.1)

        # No simulated history in live mode
        assert wrapper.get_simulated_orders() == []


# ───────────────────────────────────────────────────────────────────────
# Attribute forwarding
# ───────────────────────────────────────────────────────────────────────


class TestAttributeForwarding:
    """Unrecognized attributes should forward to wrapped connector."""

    def test_forwards_unknown_method(self, mock_connector):
        mock_connector.some_custom_method = MagicMock(return_value="custom_result")
        wrapper = DryRunMT5Wrapper(mock_connector, dry_run=True)

        result = wrapper.some_custom_method()
        assert result == "custom_result"
        mock_connector.some_custom_method.assert_called_once()

    def test_forwards_unknown_attribute(self, mock_connector):
        mock_connector.custom_attribute = "test_value"
        wrapper = DryRunMT5Wrapper(mock_connector, dry_run=True)
        assert wrapper.custom_attribute == "test_value"
