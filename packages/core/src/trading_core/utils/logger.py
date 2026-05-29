"""
Logging System

Structured logging using Loguru with file rotation and formatting.
"""

import sys
from pathlib import Path

from loguru import logger


def setup_logger(
    log_file: str = "./logs/trading_bot.log",
    level: str = "INFO",
    rotation: str = "10 MB",
    retention: int = 5,
    format_string: str | None = None,
) -> None:
    """
    Setup logging configuration.

    Args:
        log_file: Path to log file
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        rotation: Log rotation size
        retention: Number of backup files to keep
        format_string: Custom format string
    """
    # Remove default logger
    logger.remove()

    # Default format
    if format_string is None:
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

    # Add console handler
    logger.add(
        sys.stderr,
        format=format_string,
        level=level,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Add file handler with rotation
    logger.add(
        log_file,
        format=format_string,
        level=level,
        rotation=rotation,
        retention=retention,
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True,  # Thread-safe logging
        catch=True,  # Catch exceptions in logging handler
        serialize=False,  # Don't serialize (faster)
    )

    logger.info(f"Logger initialized - Level: {level}, File: {log_file}")


def get_logger(name: str):
    """
    Get a logger instance with a specific name.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logger.bind(name=name)
