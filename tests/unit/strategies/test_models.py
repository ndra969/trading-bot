"""Tests for trading strategy models."""

from datetime import datetime

import pytest

from trading_bot.strategies.models import (
    SignalDirection,
    SignalStatus,
    StrategyResult,
    TradingSignal,
)


class TestStrategyResult:
    """Test cases for StrategyResult model."""

    def test_strategy_result_initialization(self):
        """Test basic initialization of StrategyResult."""
        result = StrategyResult(
            strategy_name="foundation",
            symbol="EURUSD",
            score=75.0,
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
            timeframe="H1",
        )

        assert result.strategy_name == "foundation"
        assert result.symbol == "EURUSD"
        assert result.score == 75.0
        assert result.direction == SignalDirection.BUY
        assert result.entry_price == 1.1000
        assert result.stop_loss == 1.0950
        assert result.take_profit == 1.1100
        assert result.timeframe == "H1"

    def test_strategy_result_score_validation(self):
        """Test score validation (must be 0-100)."""
        # Valid score
        result = StrategyResult(strategy_name="test", symbol="EURUSD", score=75.0)
        assert result.score == 75.0

        # Invalid score - too high
        with pytest.raises(ValueError, match="Score must be between 0-100"):
            StrategyResult(strategy_name="test", symbol="EURUSD", score=150.0)

        # Invalid score - negative
        with pytest.raises(ValueError, match="Score must be between 0-100"):
            StrategyResult(strategy_name="test", symbol="EURUSD", score=-10.0)

    def test_strategy_result_has_signal(self):
        """Test has_signal property."""
        # Complete signal
        result = StrategyResult(
            strategy_name="foundation",
            symbol="EURUSD",
            score=75.0,
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
        )
        assert result.has_signal is True

        # No direction
        result = StrategyResult(
            strategy_name="foundation",
            symbol="EURUSD",
            score=75.0,
            entry_price=1.1000,
            stop_loss=1.0950,
        )
        assert result.has_signal is False

        # No entry price
        result = StrategyResult(
            strategy_name="foundation",
            symbol="EURUSD",
            score=75.0,
            direction=SignalDirection.BUY,
            stop_loss=1.0950,
        )
        assert result.has_signal is False

    def test_strategy_result_risk_reward_ratio(self):
        """Test risk/reward ratio calculation."""
        # BUY signal with TP
        result = StrategyResult(
            strategy_name="foundation",
            symbol="EURUSD",
            score=75.0,
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1150,
        )
        assert result.risk_reward_ratio == pytest.approx(3.0, rel=0.01)

        # SELL signal with TP
        result = StrategyResult(
            strategy_name="foundation",
            symbol="EURUSD",
            score=75.0,
            direction=SignalDirection.SELL,
            entry_price=1.1000,
            stop_loss=1.1050,
            take_profit=1.0850,
        )
        assert result.risk_reward_ratio == pytest.approx(3.0, rel=0.01)

        # No TP
        result = StrategyResult(
            strategy_name="foundation",
            symbol="EURUSD",
            score=75.0,
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
        )
        assert result.risk_reward_ratio is None

    def test_strategy_result_to_dict(self):
        """Test conversion to dictionary."""
        result = StrategyResult(
            strategy_name="foundation",
            symbol="EURUSD",
            score=75.0,
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
            metadata={"zone_strength": 85.0},
            timeframe="H1",
        )

        data = result.to_dict()
        assert data["strategy_name"] == "foundation"
        assert data["symbol"] == "EURUSD"
        assert data["score"] == 75.0
        assert data["direction"] == "BUY"
        assert data["entry_price"] == 1.1000
        assert data["has_signal"] is True
        assert "zone_strength" in data["metadata"]

    def test_strategy_result_default_values(self):
        """Test default values for optional fields."""
        result = StrategyResult(strategy_name="test", symbol="EURUSD", score=50.0)

        assert result.direction is None
        assert result.entry_price is None
        assert result.stop_loss is None
        assert result.take_profit is None
        assert result.metadata == {}
        assert result.timeframe == "H1"
        assert isinstance(result.timestamp, datetime)


class TestTradingSignal:
    """Test cases for TradingSignal model."""

    def test_trading_signal_initialization_buy(self):
        """Test BUY signal initialization."""
        signal = TradingSignal(
            signal_id="sig_001",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1150,
            confluence_score=75.0,
            risk_reward_ratio=3.0,
            strategy_scores={"foundation": 80.0},
            timeframe="H1",
        )

        assert signal.signal_id == "sig_001"
        assert signal.symbol == "EURUSD"
        assert signal.direction == SignalDirection.BUY
        assert signal.entry_price == 1.1000
        assert signal.stop_loss == 1.0950
        assert signal.take_profit == 1.1150
        assert signal.confluence_score == 75.0
        assert signal.risk_reward_ratio == 3.0

    def test_trading_signal_initialization_sell(self):
        """Test SELL signal initialization."""
        signal = TradingSignal(
            signal_id="sig_002",
            symbol="GBPUSD",
            direction=SignalDirection.SELL,
            entry_price=1.2500,
            stop_loss=1.2550,
            take_profit=1.2350,
            confluence_score=70.0,
            risk_reward_ratio=3.0,
        )

        assert signal.signal_id == "sig_002"
        assert signal.direction == SignalDirection.SELL
        assert signal.stop_loss > signal.entry_price  # SELL: SL above entry
        assert signal.take_profit < signal.entry_price  # SELL: TP below entry

    def test_trading_signal_buy_validation(self):
        """Test BUY signal price validation."""
        # Valid BUY signal
        signal = TradingSignal(
            signal_id="sig_001",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1150,
            confluence_score=75.0,
            risk_reward_ratio=3.0,
        )
        assert signal.is_valid()

        # Invalid: SL above entry for BUY
        with pytest.raises(ValueError, match="stop_loss must be below entry_price"):
            TradingSignal(
                signal_id="sig_001",
                symbol="EURUSD",
                direction=SignalDirection.BUY,
                entry_price=1.1000,
                stop_loss=1.1050,  # Invalid: above entry
                take_profit=1.1150,
                confluence_score=75.0,
                risk_reward_ratio=3.0,
            )

        # Invalid: TP below entry for BUY
        with pytest.raises(ValueError, match="take_profit must be above entry_price"):
            TradingSignal(
                signal_id="sig_001",
                symbol="EURUSD",
                direction=SignalDirection.BUY,
                entry_price=1.1000,
                stop_loss=1.0950,
                take_profit=1.0980,  # Invalid: below entry
                confluence_score=75.0,
                risk_reward_ratio=3.0,
            )

    def test_trading_signal_sell_validation(self):
        """Test SELL signal price validation."""
        # Valid SELL signal
        signal = TradingSignal(
            signal_id="sig_002",
            symbol="EURUSD",
            direction=SignalDirection.SELL,
            entry_price=1.1000,
            stop_loss=1.1050,
            take_profit=1.0850,
            confluence_score=75.0,
            risk_reward_ratio=3.0,
        )
        assert signal.is_valid()

        # Invalid: SL below entry for SELL
        with pytest.raises(ValueError, match="stop_loss must be above entry_price"):
            TradingSignal(
                signal_id="sig_002",
                symbol="EURUSD",
                direction=SignalDirection.SELL,
                entry_price=1.1000,
                stop_loss=1.0950,  # Invalid: below entry
                take_profit=1.0850,
                confluence_score=75.0,
                risk_reward_ratio=3.0,
            )

        # Invalid: TP above entry for SELL
        with pytest.raises(ValueError, match="take_profit must be below entry_price"):
            TradingSignal(
                signal_id="sig_002",
                symbol="EURUSD",
                direction=SignalDirection.SELL,
                entry_price=1.1000,
                stop_loss=1.1050,
                take_profit=1.1020,  # Invalid: above entry
                confluence_score=75.0,
                risk_reward_ratio=3.0,
            )

    def test_trading_signal_confluence_score_validation(self):
        """Test confluence score validation."""
        # Valid score
        signal = TradingSignal(
            signal_id="sig_001",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1150,
            confluence_score=75.0,
            risk_reward_ratio=3.0,
        )
        assert signal.confluence_score == 75.0

        # Invalid: too high
        with pytest.raises(ValueError, match="Confluence score must be between 0-100"):
            TradingSignal(
                signal_id="sig_001",
                symbol="EURUSD",
                direction=SignalDirection.BUY,
                entry_price=1.1000,
                stop_loss=1.0950,
                take_profit=1.1150,
                confluence_score=150.0,
                risk_reward_ratio=3.0,
            )

    def test_trading_signal_risk_reward_validation(self):
        """Test risk/reward ratio validation."""
        # Valid R:R
        signal = TradingSignal(
            signal_id="sig_001",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1150,
            confluence_score=75.0,
            risk_reward_ratio=3.0,
        )
        assert signal.risk_reward_ratio == 3.0

        # Invalid: negative R:R
        with pytest.raises(ValueError, match="Risk/reward ratio must be positive"):
            TradingSignal(
                signal_id="sig_001",
                symbol="EURUSD",
                direction=SignalDirection.BUY,
                entry_price=1.1000,
                stop_loss=1.0950,
                take_profit=1.1150,
                confluence_score=75.0,
                risk_reward_ratio=-1.0,
            )

    def test_trading_signal_risk_pips(self):
        """Test risk calculation in pips."""
        # BUY signal
        signal = TradingSignal(
            signal_id="sig_001",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1150,
            confluence_score=75.0,
            risk_reward_ratio=3.0,
        )
        assert signal.risk_pips == pytest.approx(0.0050, abs=0.00001)

        # SELL signal
        signal = TradingSignal(
            signal_id="sig_002",
            symbol="EURUSD",
            direction=SignalDirection.SELL,
            entry_price=1.1000,
            stop_loss=1.1050,
            take_profit=1.0850,
            confluence_score=75.0,
            risk_reward_ratio=3.0,
        )
        assert signal.risk_pips == pytest.approx(0.0050, abs=0.00001)

    def test_trading_signal_reward_pips(self):
        """Test reward calculation in pips."""
        # BUY signal
        signal = TradingSignal(
            signal_id="sig_001",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1150,
            confluence_score=75.0,
            risk_reward_ratio=3.0,
        )
        assert signal.reward_pips == pytest.approx(0.0150, abs=0.00001)

        # SELL signal
        signal = TradingSignal(
            signal_id="sig_002",
            symbol="EURUSD",
            direction=SignalDirection.SELL,
            entry_price=1.1000,
            stop_loss=1.1050,
            take_profit=1.0850,
            confluence_score=75.0,
            risk_reward_ratio=3.0,
        )
        assert signal.reward_pips == pytest.approx(0.0150, abs=0.00001)

    def test_trading_signal_to_dict(self):
        """Test conversion to dictionary."""
        signal = TradingSignal(
            signal_id="sig_001",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1150,
            confluence_score=75.0,
            risk_reward_ratio=3.0,
            strategy_scores={"foundation": 80.0},
            timeframe="H1",
        )

        data = signal.to_dict()
        assert data["signal_id"] == "sig_001"
        assert data["symbol"] == "EURUSD"
        assert data["direction"] == "BUY"
        assert data["entry_price"] == 1.1000
        assert data["confluence_score"] == 75.0
        assert data["risk_reward_ratio"] == 3.0
        assert "foundation" in data["strategy_scores"]
        assert "risk_pips" in data
        assert "reward_pips" in data

    def test_trading_signal_string_representation(self):
        """Test string representations."""
        signal = TradingSignal(
            signal_id="sig_001",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1150,
            confluence_score=75.0,
            risk_reward_ratio=3.0,
        )

        str_repr = str(signal)
        assert "BUY" in str_repr
        assert "EURUSD" in str_repr
        assert "1.10000" in str_repr

        repr_str = repr(signal)
        assert "BUY" in repr_str
        assert "EURUSD" in repr_str

    def test_trading_signal_status_enum(self):
        """Test signal status handling."""
        signal = TradingSignal(
            signal_id="sig_001",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1150,
            confluence_score=75.0,
            risk_reward_ratio=3.0,
            status=SignalStatus.VALIDATED,
        )

        assert signal.status == SignalStatus.VALIDATED
        assert signal.is_valid()

        # Test with REJECTED status
        signal.status = SignalStatus.REJECTED
        assert not signal.is_valid()

    def test_trading_signal_positive_prices(self):
        """Test that all prices must be positive."""
        # Invalid: zero entry price
        with pytest.raises(ValueError, match="All prices must be positive"):
            TradingSignal(
                signal_id="sig_001",
                symbol="EURUSD",
                direction=SignalDirection.BUY,
                entry_price=0.0,
                stop_loss=1.0950,
                take_profit=1.1150,
                confluence_score=75.0,
                risk_reward_ratio=3.0,
            )

        # Invalid: negative stop loss
        with pytest.raises(ValueError, match="All prices must be positive"):
            TradingSignal(
                signal_id="sig_001",
                symbol="EURUSD",
                direction=SignalDirection.BUY,
                entry_price=1.1000,
                stop_loss=-1.0950,
                take_profit=1.1150,
                confluence_score=75.0,
                risk_reward_ratio=3.0,
            )

    def test_strategy_result_direction_string_conversion(self):
        """Test StrategyResult direction conversion from string."""
        # Test with string direction (line 55)
        result = StrategyResult(
            strategy_name="test",
            symbol="EURUSD",
            score=75.0,
            direction="BUY",  # String instead of enum
            entry_price=1.1000,
            stop_loss=1.0950,
        )
        assert result.direction == SignalDirection.BUY
        assert isinstance(result.direction, SignalDirection)

    def test_strategy_result_risk_reward_ratio_zero_risk(self):
        """Test risk_reward_ratio returns None when risk is zero or negative (line 80)."""
        # Risk is zero (entry == stop_loss)
        result = StrategyResult(
            strategy_name="test",
            symbol="EURUSD",
            score=75.0,
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.1000,  # Same as entry
            take_profit=1.1100,
        )
        assert result.risk_reward_ratio is None

        # Risk is negative (stop_loss > entry for BUY)
        result = StrategyResult(
            strategy_name="test",
            symbol="EURUSD",
            score=75.0,
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.1050,  # Above entry (invalid but test the code path)
            take_profit=1.1100,
        )
        assert result.risk_reward_ratio is None

    def test_trading_signal_direction_string_conversion(self):
        """Test TradingSignal direction conversion from string (line 133)."""
        signal = TradingSignal(
            signal_id="sig_001",
            symbol="EURUSD",
            direction="BUY",  # String instead of enum
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1150,
            confluence_score=75.0,
            risk_reward_ratio=3.0,
        )
        assert signal.direction == SignalDirection.BUY
        assert isinstance(signal.direction, SignalDirection)

    def test_trading_signal_status_string_conversion(self):
        """Test TradingSignal status conversion from string (line 136)."""
        signal = TradingSignal(
            signal_id="sig_001",
            symbol="EURUSD",
            direction=SignalDirection.BUY,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1150,
            confluence_score=75.0,
            risk_reward_ratio=3.0,
            status="VALIDATED",  # String instead of enum
        )
        assert signal.status == SignalStatus.VALIDATED
        assert isinstance(signal.status, SignalStatus)
