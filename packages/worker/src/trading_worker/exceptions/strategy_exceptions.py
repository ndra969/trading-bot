"""
Strategy-specific exceptions.

Custom exception classes for strategy-related errors.
"""


class StrategyException(Exception):
    """Base exception for strategy errors."""

    pass


class ZoneDetectionError(StrategyException):
    """Exception raised when zone detection fails."""

    pass


class ZoneValidationError(StrategyException):
    """Exception raised when zone validation fails."""

    pass


class InsufficientDataError(StrategyException):
    """Exception raised when insufficient data for analysis."""

    pass


class SignalGenerationError(StrategyException):
    """Exception raised when signal generation fails."""

    pass


class ConfluenceCalculationError(StrategyException):
    """Exception raised when confluence calculation fails."""

    pass
