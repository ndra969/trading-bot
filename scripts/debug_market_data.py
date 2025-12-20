#!/usr/bin/env python3
"""
Debug Market Data Script

This script helps debug market data format issues
that prevent proper zone detection in the trading bot.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

from src.trading_bot.connectors.mt5_connector import MT5Connector
from src.trading_bot.data.database import get_database_manager

async def debug_market_data():
    """Debug market data retrieval and format"""

    try:
        print("🔍 DEBUG: Starting market data debug...")

        # Initialize MT5 connector
        mt5_config = {
            'login': 'dummy',
            'password': 'dummy',
            'server': 'dummy'
        }

        mt5 = MT5Connector(mt5_config)
        await mt5.initialize()

        if not mt5.is_connected():
            print("❌ MT5 connection failed")
            return

        print("✅ MT5 connected successfully")

        # Get available symbols
        try:
            symbols = await mt5.get_symbols()
            print(f"✅ Available symbols: {symbols}")
        except Exception as e:
            print(f"❌ Error getting symbols: {e}")
            return

        # Test different market data requests
        test_cases = [
            {
                'name': 'Correct OHLCV Format',
                'request': 'get_market_data',
                'data': {
                    'EURUSD': {
                        'open': 1.1000,
                        'high': 1.1050,
                        'low': 1.0950,
                        'close': 1.0980,
                        'volume': 1000,
                        'time': [1645495200, 1645495260, 1645495300]
                    }
                },
                'expected': 'Dictionary with numpy arrays for OHLCV data'
            },
            {
                'name': 'Missing Volume',
                'request': 'get_market_data',
                'data': {
                    'EURUSD': {
                        'open': 1.1000,
                        'high': 1.1050,
                        'low': 1.0950,
                        'close': 1.0980,
                        'time': 1645495200  # Missing time array
                    }
                },
                'expected': 'Dictionary with time array and volume field'
            }
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📋 Test Case {i}: {test_case['name']}")

            try:
                data = await mt5.get_market_data(symbols)
                symbol_data = data.get(test_case['request'], {}).get('EURUSD', {})

                print(f"📊 Market Data Format:")
                print(f"  Type: {type(symbol_data).__name__}")
                print(f"  Keys: {list(symbol_data.keys())}")
                print(f"  Expected: {test_case['expected']}")
                print(f"  Match: {symbol_data == test_case['data']}")

                if symbol_data and test_case['expected']:
                    print(f"✅ SUCCESS: {test_case['name']}")
                else:
                    print(f"❌ FAILED: {test_case['name']}")

            except Exception as e:
                print(f"❌ ERROR: {e}")

        print("\n🔍 CONCLUSION:")
        print("1. OHLCV format needs volume and time arrays")
        print("2. Time zone data needs proper structure")
        print("3. Market data provider needs debugging")
        print("4. Consider adding market data validation")

        # Test with real connection
        print("\n📡 Testing with real connection...")

        try:
            real_config = {
                'login': os.getenv('MT5_LOGIN', 'demo'),
                'password': os.getenv('MT5_PASSWORD', 'demo'),
                'server': os.getenv('MT5_SERVER', 'demo')
            }

            real_mt5 = MT5Connector(real_config)
            await real_mt5.initialize()

            if real_mt5.is_connected():
                real_data = await real_mt5.get_market_data(symbols)
                print(f"✅ Real connection successful")
                print(f"📊 Real Market Data:")
                symbol_data = real_data.get('EURUSD', {})
                print(f"  Type: {type(symbol_data).__name__}")
                print(f"  Keys: {list(symbol_data.keys())}")

                if symbol_data:
                    print(f"✅ SUCCESS: Real market data retrieved")
                else:
                    print(f"❌ FAILED: No real market data available")

        except Exception as e:
            print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(debug_market_data())
