"""Tests for PipCalculator."""

from unittest.mock import patch

import pytest

from trading_bot.position.pip_calculator import PipCalculator


class TestPipCalculatorInitialization:
    """Test PipCalculator initialization."""

    def test_pip_calculator_initialization(self):
        """Test basic initialization."""
        calculator = PipCalculator()
        assert calculator is not None


class TestGetPipSize:
    """Test get_pip_size method."""

    def test_forex_major_pip_size(self):
        """Test pip size for forex major pairs."""
        calculator = PipCalculator()
        assert calculator.get_pip_size("EURUSD") == 0.0001
        assert calculator.get_pip_size("GBPUSD") == 0.0001
        assert calculator.get_pip_size("USDCHF") == 0.0001

    def test_forex_jpy_pip_size(self):
        """Test pip size for JPY pairs."""
        calculator = PipCalculator()
        assert calculator.get_pip_size("USDJPY") == 0.01
        assert calculator.get_pip_size("EURJPY") == 0.01
        assert calculator.get_pip_size("GBPJPY") == 0.01

    def test_commodities_pip_size(self):
        """Test pip size for commodities (Gold = 0.1, Silver = 0.01)."""
        calculator = PipCalculator()
        assert calculator.get_pip_size("XAUUSD") == 0.1
        assert calculator.get_pip_size("GOLD") == 0.1
        # Silver has different pip size than Gold (see config/symbol_mapping.yaml)
        assert calculator.get_pip_size("XAGUSD") == 0.01

    def test_crypto_pip_size(self):
        """Test pip size for crypto."""
        calculator = PipCalculator()
        assert calculator.get_pip_size("BTCUSD") == 1.0
        assert calculator.get_pip_size("ETHUSD") == 1.0
        assert calculator.get_pip_size("BTCUSDT") == 1.0


class TestCalculatePips:
    """Test calculate_pips method."""

    def test_calculate_pips_buy_profit_forex(self):
        """Test pip calculation for BUY position in profit (Forex)."""
        calculator = PipCalculator()
        pips = calculator.calculate_pips(
            symbol="EURUSD",
            entry_price=1.1000,
            current_price=1.1050,  # 50 pips profit
            position_type="BUY",
        )
        assert pips == pytest.approx(50.0, abs=0.1)

    def test_calculate_pips_buy_loss_forex(self):
        """Test pip calculation for BUY position in loss (Forex)."""
        calculator = PipCalculator()
        pips = calculator.calculate_pips(
            symbol="EURUSD",
            entry_price=1.1000,
            current_price=1.0950,  # 50 pips loss
            position_type="BUY",
        )
        assert pips == pytest.approx(-50.0, abs=0.1)

    def test_calculate_pips_sell_profit_forex(self):
        """Test pip calculation for SELL position in profit (Forex)."""
        calculator = PipCalculator()
        pips = calculator.calculate_pips(
            symbol="EURUSD",
            entry_price=1.1000,
            current_price=1.0950,  # 50 pips profit
            position_type="SELL",
        )
        assert pips == pytest.approx(50.0, abs=0.1)

    def test_calculate_pips_sell_loss_forex(self):
        """Test pip calculation for SELL position in loss (Forex)."""
        calculator = PipCalculator()
        pips = calculator.calculate_pips(
            symbol="EURUSD",
            entry_price=1.1000,
            current_price=1.1050,  # 50 pips loss
            position_type="SELL",
        )
        assert pips == pytest.approx(-50.0, abs=0.1)

    def test_calculate_pips_jpy_pair(self):
        """Test pip calculation for JPY pair."""
        calculator = PipCalculator()
        pips = calculator.calculate_pips(
            symbol="USDJPY",
            entry_price=150.00,
            current_price=151.00,  # 100 pips profit
            position_type="BUY",
        )
        assert pips == pytest.approx(100.0, abs=0.1)

    def test_calculate_pips_gold(self):
        """Test pip calculation for Gold."""
        calculator = PipCalculator()
        pips = calculator.calculate_pips(
            symbol="XAUUSD",
            entry_price=2000.0,
            current_price=2050.0,  # 500 pips profit
            position_type="BUY",
        )
        assert pips == pytest.approx(500.0, abs=0.1)

    def test_calculate_pips_crypto(self):
        """Test pip calculation for crypto."""
        calculator = PipCalculator()
        pips = calculator.calculate_pips(
            symbol="BTCUSD",
            entry_price=50000.0,
            current_price=51000.0,  # 1000 pips profit
            position_type="BUY",
        )
        assert pips == pytest.approx(1000.0, abs=0.1)


class TestCalculatePipValue:
    """Test calculate_pip_value method."""

    def test_pip_value_forex_standard_lot(self):
        """Test pip value for forex major pair (1 standard lot)."""
        calculator = PipCalculator()
        pip_value = calculator.calculate_pip_value("EURUSD", volume=1.0)
        assert pip_value == pytest.approx(10.0, abs=0.01)

    def test_pip_value_forex_half_lot(self):
        """Test pip value for forex major pair (0.5 lot)."""
        calculator = PipCalculator()
        pip_value = calculator.calculate_pip_value("EURUSD", volume=0.5)
        assert pip_value == pytest.approx(5.0, abs=0.01)

    def test_pip_value_jpy_pair(self):
        """Test pip value for JPY pair."""
        calculator = PipCalculator()
        pip_value = calculator.calculate_pip_value("USDJPY", volume=1.0)
        # JPY pairs use 9.09 per lot (from config) due to exchange rate calculation
        assert pip_value == pytest.approx(9.09, abs=0.01)

    def test_pip_value_gold(self):
        """Test pip value for Gold."""
        calculator = PipCalculator()
        pip_value = calculator.calculate_pip_value("XAUUSD", volume=1.0)
        assert pip_value == pytest.approx(10.0, abs=0.01)

    def test_pip_value_crypto(self):
        """Test pip value for crypto."""
        calculator = PipCalculator()
        pip_value = calculator.calculate_pip_value("BTCUSD", volume=1.0)
        assert pip_value == pytest.approx(1.0, abs=0.01)


class TestCalculateUSDAmount:
    """Test calculate_usd_amount method."""

    def test_usd_amount_forex(self):
        """Test USD amount calculation for forex."""
        calculator = PipCalculator()
        usd = calculator.calculate_usd_amount(
            symbol="EURUSD",
            entry_price=1.1000,
            target_price=1.1050,  # 50 pips
            volume=1.0,
        )
        assert usd == pytest.approx(500.0, abs=1.0)  # 50 pips * $10 = $500

    def test_usd_amount_jpy(self):
        """Test USD amount calculation for JPY pair."""
        calculator = PipCalculator()
        usd = calculator.calculate_usd_amount(
            symbol="USDJPY",
            entry_price=150.00,
            target_price=151.00,  # 100 pips
            volume=1.0,
        )
        # JPY pairs use 9.09 per lot (from config) due to exchange rate calculation
        assert usd == pytest.approx(909.0, abs=1.0)  # 100 pips * $9.09 = $909

    def test_usd_amount_gold(self):
        """Test USD amount calculation for Gold."""
        calculator = PipCalculator()
        usd = calculator.calculate_usd_amount(
            symbol="XAUUSD",
            entry_price=2000.0,
            target_price=2050.0,  # 500 pips
            volume=1.0,
        )
        assert usd == pytest.approx(5000.0, abs=1.0)  # 500 pips * $10 = $5000


class TestCalculateRiskRewardUSD:
    """Test calculate_risk_reward_usd method."""

    def test_risk_reward_usd_forex(self):
        """Test risk/reward USD calculation for forex."""
        calculator = PipCalculator()
        risk, reward, rr_ratio = calculator.calculate_risk_reward_usd(
            symbol="EURUSD",
            entry_price=1.1000,
            stop_loss=1.0950,  # 50 pips risk
            take_profit=1.1150,  # 150 pips reward
            volume=1.0,
        )
        assert risk == pytest.approx(500.0, abs=1.0)  # 50 pips * $10
        assert reward == pytest.approx(1500.0, abs=1.0)  # 150 pips * $10
        assert rr_ratio == pytest.approx(3.0, abs=0.01)

    def test_risk_reward_usd_jpy(self):
        """Test risk/reward USD calculation for JPY pair."""
        calculator = PipCalculator()
        risk, reward, rr_ratio = calculator.calculate_risk_reward_usd(
            symbol="USDJPY",
            entry_price=150.00,
            stop_loss=149.50,  # 50 pips risk
            take_profit=151.00,  # 100 pips reward
            volume=1.0,
        )
        # JPY pairs use 9.09 per lot (from config) due to exchange rate calculation
        assert risk == pytest.approx(454.5, abs=1.0)  # 50 pips * $9.09 = $454.5
        assert reward == pytest.approx(909.0, abs=1.0)  # 100 pips * $9.09 = $909
        assert rr_ratio == pytest.approx(2.0, abs=0.01)

    def test_risk_reward_usd_gold(self):
        """Test risk/reward USD calculation for Gold."""
        calculator = PipCalculator()
        risk, reward, rr_ratio = calculator.calculate_risk_reward_usd(
            symbol="XAUUSD",
            entry_price=2000.0,
            stop_loss=1995.0,  # 50 pips risk
            take_profit=2015.0,  # 150 pips reward
            volume=1.0,
        )
        assert risk == pytest.approx(500.0, abs=1.0)
        assert reward == pytest.approx(1500.0, abs=1.0)
        assert rr_ratio == pytest.approx(3.0, abs=0.01)


class TestDetermineAssetClass:
    """Test _determine_asset_class method."""

    def test_determine_forex_major(self):
        """Test asset class determination for forex major."""
        calculator = PipCalculator()
        assert calculator._determine_asset_class("EURUSD") == "forex_major"
        assert calculator._determine_asset_class("GBPUSD") == "forex_major"

    def test_determine_forex_jpy(self):
        """Test asset class determination for JPY pairs."""
        calculator = PipCalculator()
        assert calculator._determine_asset_class("USDJPY") == "forex_jpy"
        assert calculator._determine_asset_class("EURJPY") == "forex_jpy"

    def test_determine_commodities(self):
        """Test asset class determination for commodities."""
        calculator = PipCalculator()
        assert calculator._determine_asset_class("XAUUSD") == "commodities"
        assert calculator._determine_asset_class("GOLD") == "commodities"

    def test_determine_crypto(self):
        """Test asset class determination for crypto."""
        calculator = PipCalculator()
        assert calculator._determine_asset_class("BTCUSD") == "crypto"
        assert calculator._determine_asset_class("ETHUSD") == "crypto"


class TestUtilityMethods:
    """Test utility methods."""

    def test_string_representation(self):
        """Test string representation."""
        calculator = PipCalculator()
        str_repr = str(calculator)
        # String representation should indicate it uses SymbolMapper
        assert "PipCalculator" in str_repr
        assert "SymbolMapper" in str_repr or "YAML" in str_repr

    def test_determine_asset_class_unknown(self):
        """Test asset class determination for unknown symbol defaults to forex_major."""
        calculator = PipCalculator()
        # Mock the symbol_mapper's methods directly
        original_mapper = calculator.symbol_mapper
        with (
            patch.object(original_mapper, "get_asset_class", return_value="unknown"),
            patch.object(original_mapper, "normalize_symbol", return_value="UNKNOWN"),
        ):
            # Should default to forex_major and log warning
            asset_class = calculator._determine_asset_class("UNKNOWN")
            assert asset_class == "forex_major"
