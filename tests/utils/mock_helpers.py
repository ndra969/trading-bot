"""
Mock helpers for testing.

Provides mock objects for MT5 and other external dependencies.
"""

from datetime import datetime


class MockMT5:
    """Mock MetaTrader5 for testing."""

    # Constants
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TYPE_BUY_LIMIT = 2
    ORDER_TYPE_SELL_LIMIT = 3
    ORDER_TYPE_BUY_STOP = 4
    ORDER_TYPE_SELL_STOP = 5

    POSITION_TYPE_BUY = 0
    POSITION_TYPE_SELL = 1

    TRADE_ACTION_DEAL = 1
    TRADE_ACTION_PENDING = 5
    TRADE_ACTION_SLTP = 2

    TRADE_RETCODE_DONE = 10009

    ORDER_TIME_GTC = 0
    ORDER_FILLING_IOC = 1

    TIMEFRAME_M1 = 1
    TIMEFRAME_M5 = 5
    TIMEFRAME_M15 = 15
    TIMEFRAME_M30 = 30
    TIMEFRAME_H1 = 60
    TIMEFRAME_H4 = 240
    TIMEFRAME_D1 = 1440
    TIMEFRAME_W1 = 10080
    TIMEFRAME_MN1 = 43200

    COPY_TICKS_ALL = 0
    COPY_TICKS_INFO = 1
    COPY_TICKS_TRADE = 2

    def __init__(self):
        self.is_initialized = False
        self.is_logged_in = False
        self._terminal_info = None
        self._account_info = None
        self._symbols = {}
        self._positions = []
        self._orders = []
        self._error = (0, "Success")

    def initialize(self, path: str = None, timeout: int = 30) -> bool:
        """Mock MT5 initialize."""
        self.is_initialized = True
        return True

    def shutdown(self) -> None:
        """Mock MT5 shutdown."""
        self.is_initialized = False
        self.is_logged_in = False

    def login(self, login: int, password: str, server: str, timeout: int = 30) -> bool:
        """Mock MT5 login."""
        self.is_logged_in = True
        return True

    def terminal_info(self):
        """Mock terminal info."""
        if not self.is_initialized:
            return None

        class TerminalInfo:
            def __init__(self):
                self.connected = True
                self.trade_allowed = True
                self.name = "Mock Terminal"

            def _asdict(self):
                return {
                    "connected": self.connected,
                    "trade_allowed": self.trade_allowed,
                    "name": self.name,
                }

        return TerminalInfo()

    def account_info(self):
        """Mock account info."""
        if not self.is_initialized:
            return None

        class AccountInfo:
            def __init__(self):
                self.login = 12345
                self.balance = 10000.0
                self.equity = 10000.0
                self.margin = 0.0
                self.margin_free = 10000.0
                self.margin_level = 0.0
                self.profit = 0.0
                self.leverage = 100
                self.currency = "USD"
                self.server = "MockServer"
                self.company = "MockBroker"
                self.trade_allowed = True
                self.trade_mode = 0  # DEMO

            def _asdict(self):
                return {
                    "login": self.login,
                    "balance": self.balance,
                    "equity": self.equity,
                    "margin": self.margin,
                    "margin_free": self.margin_free,
                    "margin_level": self.margin_level,
                    "profit": self.profit,
                    "leverage": self.leverage,
                    "currency": self.currency,
                    "server": self.server,
                    "company": self.company,
                    "trade_allowed": self.trade_allowed,
                    "trade_mode": self.trade_mode,
                }

        return AccountInfo()

    def version(self):
        """Mock MT5 version."""
        return (5, 0, 0, 3000, "2024.01.01")

    def last_error(self):
        """Mock last error."""
        return self._error

    def symbols_get(self, symbol: str = None):
        """Mock symbols get."""
        if symbol:
            if symbol in self._symbols:
                return [self._symbols[symbol]]
            return None

        # Return default symbols
        class Symbol:
            def __init__(self, name):
                self.name = name

        return [Symbol("EURUSD"), Symbol("GBPUSD"), Symbol("USDJPY")]

    def symbol_info(self, symbol: str):
        """Mock symbol info."""

        class SymbolInfo:
            def __init__(self, symbol_name):
                self.name = symbol_name
                self.visible = True
                self.trade_mode = 4  # FULL
                self.description = f"{symbol_name} Description"
                self.digits = 5
                self.point = 0.00001
                self.trade_tick_size = 0.00001
                self.trade_tick_value = 1.0
                self.trade_contract_size = 100000.0
                self.volume_min = 0.01
                self.volume_max = 100.0
                self.volume_step = 0.01
                self.swap_long = -0.5
                self.swap_short = 0.3
                self.currency_base = symbol_name[:3]
                self.currency_profit = symbol_name[3:]
                self.currency_margin = symbol_name[:3]
                self.bid = 1.10000
                self.ask = 1.10010
                self.spread = 1.0

            def _asdict(self):
                return vars(self)

        return SymbolInfo(symbol)

    def symbol_select(self, symbol: str, enable: bool = True) -> bool:
        """Mock symbol select."""
        return True

    def positions_get(self, symbol: str = None, ticket: int = None):
        """Mock positions get."""
        if ticket:
            for pos in self._positions:
                if pos["ticket"] == ticket:

                    class Position:
                        def __init__(self, data):
                            for k, v in data.items():
                                setattr(self, k, v)

                        def _asdict(self):
                            return vars(self)

                    return [Position(pos)]
            return None

        if symbol:
            filtered = [p for p in self._positions if p["symbol"] == symbol]
            if not filtered:
                return None

            class Position:
                def __init__(self, data):
                    for k, v in data.items():
                        setattr(self, k, v)

                def _asdict(self):
                    return vars(self)

            return [Position(p) for p in filtered]

        if not self._positions:
            return None

        class Position:
            def __init__(self, data):
                for k, v in data.items():
                    setattr(self, k, v)

            def _asdict(self):
                return vars(self)

        return [Position(p) for p in self._positions]

    def order_send(self, request: dict):
        """Mock order send."""

        class OrderResult:
            def __init__(self):
                self.retcode = MockMT5.TRADE_RETCODE_DONE
                self.deal = 12345
                self.order = 12345
                self.volume = request.get("volume", 0.01)
                self.price = request.get("price", 1.10000)
                self.comment = "Success"

            def _asdict(self):
                return {
                    "retcode": self.retcode,
                    "deal": self.deal,
                    "order": self.order,
                    "volume": self.volume,
                    "price": self.price,
                    "comment": self.comment,
                }

        return OrderResult()

    def copy_rates_from_pos(self, symbol: str, timeframe: int, start_pos: int, count: int):
        """Mock copy rates."""
        from .data_generators import generate_ohlcv_data

        return generate_ohlcv_data(count)

    def copy_rates_range(self, symbol: str, timeframe: int, date_from: datetime, date_to: datetime):
        """Mock copy rates range."""
        from .data_generators import generate_ohlcv_data

        return generate_ohlcv_data(100)

    def symbol_info_tick(self, symbol: str):
        """Mock symbol info tick."""

        class Tick:
            def __init__(self):
                self.time = int(datetime.now().timestamp())
                self.bid = 1.10000
                self.ask = 1.10010
                self.last = 1.10005
                self.volume = 1

            def _asdict(self):
                return vars(self)

        return Tick()

    def copy_ticks_from_pos(self, symbol: str, start_pos: int, count: int, flags: int):
        """Mock copy ticks."""
        from .data_generators import generate_tick_data

        return generate_tick_data(count)
