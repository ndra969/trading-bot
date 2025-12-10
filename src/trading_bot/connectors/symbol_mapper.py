"""
MT5 Symbol Mapper
Universal symbol mapping across different brokers with comprehensive symbol conversion.
"""

from pathlib import Path
from typing import Any

import yaml

from ..utils.logger import get_logger

logger = get_logger(__name__)


class SymbolMappingError(Exception):
    """Exception raised for symbol mapping errors."""

    def __init__(self, message: str, symbol: str | None = None):
        self.symbol = symbol
        self.message = message
        if symbol:
            super().__init__(f"Symbol '{symbol}': {message}")
        else:
            super().__init__(message)


class SymbolMapper:
    """
    Universal symbol mapper for different brokers.

    Provides conversion between universal symbol names and broker-specific
    symbol formats with comprehensive validation and asset class detection.
    """

    def __init__(self, config_path: str | None = None):
        """
        Initialize symbol mapper with configuration.

        Args:
            config_path: Path to symbol mapping configuration file
        """
        self._config = self._load_config(config_path)
        self.default_broker = self._config.get("default_broker", "exness_standard")
        self._build_reverse_mappings()

        logger.info(f"SymbolMapper initialized with default broker: {self.default_broker}")

    def _load_config(self, config_path: str | None) -> dict:
        """Load symbol mapping configuration from YAML file."""
        if config_path is None:
            # Default config path relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = project_root / "config" / "symbol_mapping.yaml"

        try:
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded symbol mapping config from {config_path}")
                return config
        except FileNotFoundError as err:
            logger.error(f"Symbol mapping config not found at {config_path}")
            raise SymbolMappingError(f"Configuration file not found: {config_path}") from err
        except yaml.YAMLError as e:
            logger.error(f"Error parsing symbol mapping config: {e}")
            raise SymbolMappingError(f"Invalid YAML configuration: {e}") from e

    def _build_reverse_mappings(self):
        """Build reverse mappings for broker to universal conversion."""
        self._reverse_mappings = {}

        # Build regular reverse mappings
        for broker, mappings in self._config["brokers"].items():
            self._reverse_mappings[broker] = {v: k for k, v in mappings.items()}

        # Store special reverse mappings separately
        self._special_reverse_mappings = self._config.get("special_reverse_mappings", {})

    @property
    def broker_mappings(self) -> dict[str, dict[str, str]]:
        """Get broker mappings from configuration."""
        return self._config["brokers"]

    @property
    def asset_classes(self) -> dict[str, list[str]]:
        """Get asset classes from configuration."""
        return self._config["asset_classes"]

    @property
    def pip_values(self) -> dict[str, float]:
        """Get pip values from configuration."""
        return self._config["pip_values"]

    @property
    def pip_values_per_lot(self) -> dict[str, float]:
        """Get pip values per lot from configuration."""
        return self._config["pip_values_per_lot"]

    def get_supported_brokers(self) -> list[str]:
        """
        Get list of supported brokers.

        Returns:
            List of supported broker names
        """
        return list(self.broker_mappings.keys())

    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol name to universal format.

        Args:
            symbol: Input symbol name

        Returns:
            Normalized symbol name

        Raises:
            SymbolMappingError: If symbol is invalid
        """
        if not symbol or not symbol.strip():
            raise SymbolMappingError("Symbol cannot be empty", symbol=symbol)

        # Convert to uppercase
        normalized = symbol.upper().strip()

        # Remove common separators
        normalized = normalized.replace("/", "")
        normalized = normalized.replace("_", "")
        normalized = normalized.replace("-", "")

        return normalized

    def convert_to_broker_symbol(
        self, universal_symbol: str, broker_name: str | None = None
    ) -> str:
        """
        Convert universal symbol to broker-specific symbol.

        Args:
            universal_symbol: Universal symbol name
            broker_name: Target broker name (uses default if None)

        Returns:
            Broker-specific symbol name

        Raises:
            SymbolMappingError: If broker or symbol is invalid
        """
        # Use default broker if not specified
        if broker_name is None:
            broker_name = self.default_broker

        # Normalize inputs
        broker_name = broker_name.lower().strip()
        normalized_symbol = self.normalize_symbol(universal_symbol)

        # Check if broker is supported
        if broker_name not in self.broker_mappings:
            raise SymbolMappingError(f"Invalid broker: {broker_name}", symbol=universal_symbol)

        # Check if symbol is supported for this broker
        broker_mappings = self.broker_mappings[broker_name]
        if normalized_symbol not in broker_mappings:
            raise SymbolMappingError(
                f"Unsupported symbol: {normalized_symbol} for broker: {broker_name}",
                symbol=universal_symbol,
            )

        return broker_mappings[normalized_symbol]

    def convert_to_universal_symbol(
        self, broker_symbol: str, broker_name: str | None = None
    ) -> str:
        """
        Convert broker-specific symbol to universal symbol.

        Args:
            broker_symbol: Broker-specific symbol name
            broker_name: Source broker name (uses default if None)

        Returns:
            Universal symbol name

        Raises:
            SymbolMappingError: If conversion fails
        """
        # Use default broker if not specified
        if broker_name is None:
            broker_name = self.default_broker

        # Normalize inputs
        broker_name = broker_name.lower().strip()
        # Keep broker symbol case as-is for reverse mapping to work correctly
        normalized_broker_symbol = broker_symbol.strip()

        # Check special mappings first
        if broker_name in self._special_reverse_mappings:
            special_mappings = self._special_reverse_mappings[broker_name]
            if normalized_broker_symbol in special_mappings:
                return special_mappings[normalized_broker_symbol]

        # Check regular reverse mappings
        if broker_name in self._reverse_mappings:
            reverse_mappings = self._reverse_mappings[broker_name]
            if normalized_broker_symbol in reverse_mappings:
                return reverse_mappings[normalized_broker_symbol]

        raise SymbolMappingError(
            f"Cannot convert broker symbol {broker_symbol} to universal format",
            symbol=broker_symbol,
        )

    def get_broker_symbol_info(
        self, universal_symbol: str, broker_name: str | None = None
    ) -> dict[str, Any]:
        """
        Get comprehensive symbol information for a broker.

        Args:
            universal_symbol: Universal symbol name
            broker_name: Target broker name (uses default if None)

        Returns:
            Dictionary with symbol information
        """
        broker_symbol = self.convert_to_broker_symbol(universal_symbol, broker_name)
        asset_class = self.get_asset_class(universal_symbol)
        pip_size = self.get_pip_size(universal_symbol)
        pip_value_per_lot = self.get_pip_value_per_lot(universal_symbol)

        return {
            "universal_symbol": universal_symbol,
            "broker_symbol": broker_symbol,
            "broker_name": broker_name or self.default_broker,
            "asset_class": asset_class,
            "pip_size": pip_size,
            "pip_value_per_lot": pip_value_per_lot,
        }

    def get_asset_class(self, symbol: str) -> str:
        """
        Get asset class for a symbol (handles both universal and broker symbols).

        Args:
            symbol: Symbol name (can be universal or broker-specific)

        Returns:
            Asset class (forex, commodity, crypto, index)
        """
        normalized_symbol = self.normalize_symbol(symbol)

        # First, try direct lookup in asset_classes
        for asset_class, symbols in self.asset_classes.items():
            if normalized_symbol in symbols:
                return asset_class

        # If not found, try converting broker symbol to universal symbol
        # This handles cases like BTCUSDC -> BTCUSD, EURUSDc -> EURUSD
        try:
            # Try with default broker first
            universal_symbol = self.convert_to_universal_symbol(normalized_symbol)
            # Try lookup again with universal symbol
            for asset_class, symbols in self.asset_classes.items():
                if universal_symbol in symbols:
                    return asset_class
        except SymbolMappingError:
            # If conversion fails, symbol might not be a broker symbol
            # or might be a new symbol not in config - continue to default
            pass

        # Default to forex if not found
        logger.debug(f"Symbol {symbol} not found in asset_classes, defaulting to forex")
        return "forex"

    def get_pip_size(self, symbol: str) -> float:
        """
        Get pip size for a symbol.

        Args:
            symbol: Symbol name

        Returns:
            Pip size value
        """
        normalized_symbol = self.normalize_symbol(symbol)
        asset_class = self.get_asset_class(normalized_symbol)

        if asset_class == "forex":
            # Check if it's a JPY pair
            if "JPY" in normalized_symbol:
                return self.pip_values["forex_jpy"]
            else:
                return self.pip_values["forex_major"]
        elif asset_class == "commodity":
            return self.pip_values["commodities"]
        elif asset_class == "crypto":
            return self.pip_values["crypto"]
        else:
            # Default to forex major
            return self.pip_values["forex_major"]

    def get_pip_value_per_lot(self, symbol: str) -> float:
        """
        Get pip value per lot for a symbol.

        Args:
            symbol: Symbol name

        Returns:
            Pip value per standard lot
        """
        normalized_symbol = self.normalize_symbol(symbol)
        asset_class = self.get_asset_class(normalized_symbol)

        if asset_class == "forex":
            # Check if it's a JPY pair
            if "JPY" in normalized_symbol:
                return self.pip_values_per_lot["forex_jpy"]
            else:
                return self.pip_values_per_lot["forex_major"]
        elif asset_class == "commodity":
            return self.pip_values_per_lot["commodities"]
        elif asset_class == "crypto":
            return self.pip_values_per_lot["crypto"]
        else:
            # Default to forex major
            return self.pip_values_per_lot["forex_major"]

    def validate_broker_symbol(self, broker_symbol: str, broker_name: str | None = None) -> bool:
        """
        Validate if broker symbol is supported.

        Args:
            broker_symbol: Broker-specific symbol name
            broker_name: Source broker name (uses default if None)

        Returns:
            True if symbol is valid

        Raises:
            SymbolMappingError: If symbol is invalid
        """
        # Simply try to convert to universal symbol - will raise error if invalid
        self.convert_to_universal_symbol(broker_symbol, broker_name)
        return True

    def convert_multiple_to_broker(
        self, universal_symbols: list[str], broker_name: str | None = None
    ) -> list[str]:
        """
        Convert multiple universal symbols to broker symbols.

        Args:
            universal_symbols: List of universal symbol names
            broker_name: Target broker name (uses default if None)

        Returns:
            List of broker-specific symbol names
        """
        return [self.convert_to_broker_symbol(symbol, broker_name) for symbol in universal_symbols]

    def reverse_lookup(self, broker_symbol: str, broker_name: str | None = None) -> str:
        """
        Reverse lookup to find universal symbol from broker symbol.

        Args:
            broker_symbol: Broker-specific symbol name
            broker_name: Source broker name (uses default if None)

        Returns:
            Universal symbol name
        """
        return self.convert_to_universal_symbol(broker_symbol, broker_name)

    def get_all_symbols_for_broker(self, broker_name: str) -> list[str]:
        """
        Get all supported universal symbols for a broker.

        Args:
            broker_name: Broker name

        Returns:
            List of universal symbol names
        """
        broker_name = broker_name.lower().strip()

        if broker_name not in self.broker_mappings:
            raise SymbolMappingError(f"Invalid broker: {broker_name}", symbol=broker_name)

        return list(self.broker_mappings[broker_name].keys())
