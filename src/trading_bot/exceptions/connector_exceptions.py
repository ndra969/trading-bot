"""
General connector exceptions.

Exceptions for connector operations across different platforms.
"""


class ConnectorError(Exception):
    """Base exception for connector errors."""

    pass


class ConnectionFailedError(ConnectorError):
    """Exception raised when connection fails."""

    def __init__(self, connector: str, reason: str):
        self.connector = connector
        self.reason = reason
        super().__init__(f"Connection to {connector} failed: {reason}")


class DataRetrievalError(ConnectorError):
    """Exception raised when data retrieval fails."""

    def __init__(self, source: str, data_type: str, reason: str):
        self.source = source
        self.data_type = data_type
        self.reason = reason
        super().__init__(f"Failed to retrieve {data_type} from {source}: {reason}")
