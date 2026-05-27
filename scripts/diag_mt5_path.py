"""Diagnose MT5 path= argument with dual terminals running.

Run this with BOTH Broker A and Broker B terminals open in Windows.
Output tells us whether mt5.initialize(path=...) can target a specific
terminal when multiple are running, or whether MT5 Python is strictly
single-instance and picks the first running terminal it finds.
"""

import MetaTrader5 as mt5

BROKER_A = r"C:\Program Files\MetaTrader 5\Broker A\terminal64.exe"
BROKER_B = r"C:\Program Files\MetaTrader 5\Broker B\terminal64.exe"


def probe(label: str, **init_kwargs) -> None:
    print(f"=== {label} ===")
    if mt5.initialize(**init_kwargs):
        info = mt5.terminal_info()
        acc = mt5.account_info()
        print(f"  terminal_info.path: {info.path if info else None}")
        print(f"  account.login:      {acc.login if acc else None}")
        print(f"  account.server:     {acc.server if acc else None}")
        print(f"  account.name:       {acc.name if acc else None}")
        mt5.shutdown()
    else:
        print(f"  Failed: {mt5.last_error()}")
    print()


probe("Test 1: No path (default)")
probe("Test 2: path=Broker A", path=BROKER_A)
probe("Test 3: path=Broker B", path=BROKER_B)
