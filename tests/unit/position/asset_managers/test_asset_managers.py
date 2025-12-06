"""Tests for asset-specific position managers."""

from trading_bot.position.asset_managers import (
    AssetManagerFactory,
    CommodityPositionManager,
    CryptoPositionManager,
    ForexJPYPositionManager,
    ForexPositionManager,
    get_asset_manager,
)


class TestForexPositionManager:
    """Test Forex major pairs position manager."""

    def test_forex_major_parameters(self):
        """Test forex major parameters."""
        manager = ForexPositionManager()

        assert manager.get_asset_class() == "Forex Major"
        assert manager.get_pip_size() == 0.0001
        assert manager.get_breakeven_distance() == 15.0
        assert manager.get_breakeven_buffer() == 2.0
        assert manager.get_trailing_activation() == 20.0
        assert manager.get_trailing_distance() == 10.0

    def test_forex_partial_close_levels(self):
        """Test forex partial close levels."""
        manager = ForexPositionManager()
        levels = manager.get_partial_close_levels()

        assert len(levels) == 2
        assert levels[0] == (20.0, 0.25)  # 25% at 20 pips
        assert levels[1] == (40.0, 0.50)  # 50% at 40 pips

    def test_forex_get_parameters(self):
        """Test getting all forex parameters."""
        manager = ForexPositionManager()
        params = manager.get_parameters()

        assert params["asset_class"] == "Forex Major"
        assert params["pip_size"] == 0.0001
        assert params["breakeven"]["distance"] == 15.0
        assert params["trailing"]["activation"] == 20.0
        assert len(params["partial_close_levels"]) == 2


class TestForexJPYPositionManager:
    """Test Forex JPY pairs position manager."""

    def test_forex_jpy_parameters(self):
        """Test forex JPY parameters."""
        manager = ForexJPYPositionManager()

        assert manager.get_asset_class() == "Forex JPY"
        assert manager.get_pip_size() == 0.01
        assert manager.get_breakeven_distance() == 150.0
        assert manager.get_breakeven_buffer() == 20.0
        assert manager.get_trailing_activation() == 200.0
        assert manager.get_trailing_distance() == 100.0

    def test_forex_jpy_partial_close_levels(self):
        """Test forex JPY partial close levels."""
        manager = ForexJPYPositionManager()
        levels = manager.get_partial_close_levels()

        assert len(levels) == 2
        assert levels[0] == (200.0, 0.25)  # 25% at 200 pips
        assert levels[1] == (400.0, 0.50)  # 50% at 400 pips

    def test_forex_jpy_get_parameters(self):
        """Test getting all forex JPY parameters."""
        manager = ForexJPYPositionManager()
        params = manager.get_parameters()

        assert params["asset_class"] == "Forex JPY"
        assert params["pip_size"] == 0.01
        assert params["breakeven"]["distance"] == 150.0


class TestCommodityPositionManager:
    """Test commodity (Gold) position manager."""

    def test_commodity_gold_parameters(self):
        """Test commodity Gold parameters."""
        manager = CommodityPositionManager()

        assert manager.get_asset_class() == "Commodity"
        assert manager.get_pip_size() == 0.1
        assert manager.get_breakeven_distance() == 500.0
        assert manager.get_breakeven_buffer() == 50.0
        assert manager.get_trailing_activation() == 600.0
        assert manager.get_trailing_distance() == 300.0

    def test_commodity_partial_close_levels(self):
        """Test commodity partial close levels."""
        manager = CommodityPositionManager()
        levels = manager.get_partial_close_levels()

        assert len(levels) == 2
        assert levels[0] == (600.0, 0.25)  # 25% at 600 pips
        assert levels[1] == (1200.0, 0.50)  # 50% at 1200 pips

    def test_commodity_get_parameters(self):
        """Test getting all commodity parameters."""
        manager = CommodityPositionManager()
        params = manager.get_parameters()

        assert params["asset_class"] == "Commodity"
        assert params["pip_size"] == 0.1
        assert params["trailing"]["distance"] == 300.0


class TestCryptoPositionManager:
    """Test crypto position manager."""

    def test_crypto_parameters(self):
        """Test crypto parameters."""
        manager = CryptoPositionManager()

        assert manager.get_asset_class() == "Crypto"
        assert manager.get_pip_size() == 1.0
        assert manager.get_breakeven_distance() == 50.0
        assert manager.get_breakeven_buffer() == 5.0
        assert manager.get_trailing_activation() == 60.0
        assert manager.get_trailing_distance() == 30.0

    def test_crypto_partial_close_levels(self):
        """Test crypto partial close levels."""
        manager = CryptoPositionManager()
        levels = manager.get_partial_close_levels()

        assert len(levels) == 2
        assert levels[0] == (100.0, 0.25)  # 25% at 100 USD
        assert levels[1] == (200.0, 0.50)  # 50% at 200 USD

    def test_crypto_get_parameters(self):
        """Test getting all crypto parameters."""
        manager = CryptoPositionManager()
        params = manager.get_parameters()

        assert params["asset_class"] == "Crypto"
        assert params["pip_size"] == 1.0
        assert params["breakeven"]["buffer"] == 5.0


class TestAssetManagerFactory:
    """Test asset manager factory."""

    def test_factory_forex_major(self):
        """Test factory returns forex major manager."""
        manager = AssetManagerFactory.get_manager("EURUSD")
        assert isinstance(manager, ForexPositionManager)
        assert manager.get_pip_size() == 0.0001

    def test_factory_forex_jpy(self):
        """Test factory returns forex JPY manager."""
        manager = AssetManagerFactory.get_manager("USDJPY")
        assert isinstance(manager, ForexJPYPositionManager)
        assert manager.get_pip_size() == 0.01

    def test_factory_commodity_gold(self):
        """Test factory returns commodity manager for Gold."""
        manager = AssetManagerFactory.get_manager("XAUUSD")
        assert isinstance(manager, CommodityPositionManager)
        assert manager.get_pip_size() == 0.1

    def test_factory_crypto(self):
        """Test factory returns crypto manager."""
        manager = AssetManagerFactory.get_manager("BTCUSD")
        assert isinstance(manager, CryptoPositionManager)
        assert manager.get_pip_size() == 1.0

    def test_factory_caching(self):
        """Test that factory caches manager instances."""
        manager1 = AssetManagerFactory.get_manager("EURUSD")
        manager2 = AssetManagerFactory.get_manager("GBPUSD")

        # Should return same instance for same asset class
        assert manager1 is manager2

    def test_factory_get_all_managers(self):
        """Test getting all managers from factory."""
        all_managers = AssetManagerFactory.get_all_managers()

        assert len(all_managers) == 4
        assert "forex_major" in all_managers
        assert "forex_jpy" in all_managers
        assert "commodities" in all_managers
        assert "crypto" in all_managers

    def test_factory_clear_cache(self):
        """Test clearing factory cache."""
        AssetManagerFactory.get_manager("EURUSD")
        AssetManagerFactory.clear_cache()

        # After clearing, should create new instance
        manager = AssetManagerFactory.get_manager("EURUSD")
        assert isinstance(manager, ForexPositionManager)


class TestConvenienceFunction:
    """Test convenience function."""

    def test_get_asset_manager_function(self):
        """Test get_asset_manager convenience function."""
        manager = get_asset_manager("EURUSD")
        assert isinstance(manager, ForexPositionManager)


class TestAssetManagerStringRepresentation:
    """Test string representations."""

    def test_string_representation_forex(self):
        """Test forex manager string representation."""
        manager = ForexPositionManager()
        str_repr = str(manager)
        assert "Forex Major" in str_repr

    def test_string_representation_jpy(self):
        """Test JPY manager string representation."""
        manager = ForexJPYPositionManager()
        str_repr = str(manager)
        assert "Forex JPY" in str_repr

    def test_string_representation_commodity(self):
        """Test commodity manager string representation."""
        manager = CommodityPositionManager()
        str_repr = str(manager)
        assert "Commodity" in str_repr

    def test_string_representation_crypto(self):
        """Test crypto manager string representation."""
        manager = CryptoPositionManager()
        str_repr = str(manager)
        assert "Crypto" in str_repr
