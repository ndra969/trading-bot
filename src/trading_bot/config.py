"""
Configuration Management System

Handles YAML-based configuration with environment variable overrides.
Uses Pydantic for validation and type safety.
Supports environment-specific .env files (.env.dev, .env.prd)
"""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel

from trading_bot.utils import logger


class TelegramConfig(BaseModel):
    """Telegram notification configuration."""

    bot_token: str | None = None
    chat_id: str | None = None
    enabled: bool = False


class DatabaseConfig(BaseModel):
    """Database configuration."""

    url: str = "sqlite+aiosqlite:///./trading_bot.db"
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600


class TradingConfig(BaseModel):
    """Trading configuration.

    All runtime knobs (risk_per_trade, max_concurrent_positions,
    confluence_threshold) moved to more specific config layers:
      - risk_per_trade        → symbols.<SYMBOL>.risk_per_trade
      - max_concurrent        → asset_classes.<CLASS>.max_concurrent_positions
      - confluence_threshold  → signal_generation.quality_thresholds.<asset>

    Kept as an empty placeholder so Configuration.trading still returns a
    valid object and ``getattr(config.trading, "dry_run", ...)``
    fallback patterns elsewhere keep working.
    """

    # Pydantic v2: allow unknown fields so dry_run / mode / etc. read via
    # getattr() don't error out at parse time.
    model_config = {"extra": "allow"}


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    file_path: str = "./logs/trading_bot.log"
    max_file_size: str = "10 MB"
    backup_count: int = 5
    format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"


class MT5Config(BaseModel):
    """MetaTrader5 configuration."""

    terminal_path: str | None = None
    login: int | None = None
    password: str | None = None
    server: str | None = None
    connection_timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 5


class Configuration:
    """
    Main configuration manager.

    Loads configuration from YAML files and environment variables.
    Priority: Environment Variables > Environment-specific YAML > Default YAML
    """

    def __init__(self, env: str = "development"):
        """
        Initialize configuration.

        Args:
            env: Environment name (development, production, test)
        """
        self.env = env
        self.config_dir = Path("config")
        self._config: dict[str, Any] = {}

        # Load environment-specific .env file first
        self._load_env_file()

        # Then load YAML configuration
        self._load_config()

    def _load_env_file(self) -> None:
        """Load environment-specific .env file."""
        # Map environment names to .env file suffixes
        env_map = {
            "development": "dev",
            "production": "prd",
            "test": "test",
        }

        # Get the appropriate .env file suffix
        env_suffix = env_map.get(self.env, "dev")
        env_file = Path(f".env.{env_suffix}")

        # Load the environment-specific file if it exists
        # Note: override=False means existing env vars take precedence
        if env_file.exists():
            load_dotenv(env_file, override=False)
            # Use logger if available, otherwise silent load
            try:
                logger.info(f"Loaded environment file: {env_file}")
            except Exception:
                pass  # Logger not yet initialized
        else:
            # Fallback to default .env file
            default_env = Path(".env")
            if default_env.exists():
                load_dotenv(default_env, override=False)
                try:
                    logger.info(f"Loaded default environment file: {default_env}")
                except Exception:
                    pass

    def _load_config(self) -> None:
        """Load configuration from YAML files."""
        # Load default configuration
        default_path = self.config_dir / "default.yaml"
        if default_path.exists():
            with open(default_path) as f:
                self._config = yaml.safe_load(f) or {}

        # Load strategy parameters
        strategy_path = self.config_dir / "strategy_parameters.yaml"
        if strategy_path.exists():
            with open(strategy_path) as f:
                strategy_config = yaml.safe_load(f) or {}
                self._deep_merge(self._config, strategy_config)

        # Load active symbols
        active_symbols_path = self.config_dir / "active_symbols.yaml"
        if active_symbols_path.exists():
            with open(active_symbols_path) as f:
                active_symbols_config = yaml.safe_load(f) or {}
                # Handle special structure of active_symbols.yaml
                if "symbols" in active_symbols_config:
                    # Flatten symbol keys to list if needed by main.py
                    # Or just merge normally if main.py expects full config
                    self._deep_merge(self._config, active_symbols_config)

                    # Also populate the simple "symbols" list expected by TradingBot
                    enabled_symbols = []
                    if "symbols" in active_symbols_config:
                        for sym, data in active_symbols_config["symbols"].items():
                            if data.get("enabled", False):
                                enabled_symbols.append(sym)

                    if enabled_symbols:
                        self._config["enabled_symbols"] = enabled_symbols

        # Load trading types configuration
        trading_types_path = self.config_dir / "trading_types.yaml"
        if trading_types_path.exists():
            with open(trading_types_path) as f:
                trading_types_config = yaml.safe_load(f) or {}
                self._deep_merge(self._config, trading_types_config)

        # Load environment-specific configuration
        env_path = self.config_dir / f"{self.env}.yaml"
        if env_path.exists():
            with open(env_path) as f:
                env_config = yaml.safe_load(f) or {}
                self._deep_merge(self._config, env_config)

        # Override with environment variables
        self._apply_env_overrides()

    def _deep_merge(self, base: dict, update: dict) -> None:
        """Deep merge two dictionaries."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides."""
        # Database URL
        if db_url := os.getenv("DATABASE_URL"):
            self._config.setdefault("database", {})["url"] = db_url

        # Telegram configuration
        if telegram_token := os.getenv("TELEGRAM_BOT_TOKEN"):
            self._config.setdefault("telegram", {})["bot_token"] = telegram_token
        if telegram_chat := os.getenv("TELEGRAM_CHAT_ID"):
            self._config.setdefault("telegram", {})["chat_id"] = telegram_chat

        # MT5 configuration
        if mt5_login := os.getenv("MT5_LOGIN"):
            self._config.setdefault("mt5", {})["login"] = int(mt5_login)
        if mt5_password := os.getenv("MT5_PASSWORD"):
            self._config.setdefault("mt5", {})["password"] = mt5_password
        if mt5_server := os.getenv("MT5_SERVER"):
            self._config.setdefault("mt5", {})["server"] = mt5_server

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key.

        Args:
            key: Configuration key (e.g., "database.url")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value

    @property
    def database(self) -> DatabaseConfig:
        """Get database configuration."""
        return DatabaseConfig(**self._config.get("database", {}))

    @property
    def telegram(self) -> TelegramConfig:
        """Get telegram configuration."""
        return TelegramConfig(**self._config.get("telegram", {}))

    @property
    def trading(self) -> TradingConfig:
        """Get trading configuration."""
        return TradingConfig(**self._config.get("trading", {}))

    @property
    def logging(self) -> LoggingConfig:
        """Get logging configuration."""
        return LoggingConfig(**self._config.get("logging", {}))

    @property
    def mt5(self) -> MT5Config:
        """Get MT5 configuration."""
        return MT5Config(**self._config.get("mt5", {}))

    def validate(self) -> bool:
        """
        Validate configuration.

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        try:
            # Validate all configuration sections by accessing them
            _ = (
                self.database,
                self.telegram,
                self.trading,
                self.logging,
                self.mt5,
            )
            return True
        except Exception as e:
            raise ValueError(f"Configuration validation failed: {e}") from e
