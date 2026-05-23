
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

def generate_data(symbol, timeframe, n_candles=1000):
    start_time = datetime(2024, 1, 1, 0, 0, 0)
    
    if timeframe == 'H1':
        delta = timedelta(hours=1)
    else: # M30
        delta = timedelta(minutes=30)

    timestamps = [start_time + i * delta for i in range(n_candles)]
    
    # Generate somewhat realistic looking price data (random walk)
    # Start at 2000.0 (Gold-ish)
    price = 2000.0
    
    data = []
    
    np.random.seed(42)
    
    for i, ts in enumerate(timestamps):
        # Random move logic
        move = np.random.normal(0, 2.0) # Mean 0, Std 2.0
        
        # Add some trend to create zones
        if 200 < i < 300: # Uptrend
            move += 1.0
        if 500 < i < 600: # Downtrend
            move -= 1.0
            
        open_p = price
        close_p = price + move
        high_p = max(open_p, close_p) + abs(np.random.normal(0, 1.0))
        low_p = min(open_p, close_p) - abs(np.random.normal(0, 1.0))
        
        volume = int(abs(np.random.normal(1000, 200)))
        
        data.append({
            'timestamp': ts.strftime('%Y-%m-%d %H:%M:%S'),
            'open': round(open_p, 2),
            'high': round(high_p, 2),
            'low': round(low_p, 2),
            'close': round(close_p, 2),
            'volume': volume,
            'tick_volume': volume,
            'spread': 10,
            'real_volume': 0
        })
        
        price = close_p

    df = pd.DataFrame(data)
    
    # Create directory if not exists
    os.makedirs('data/raw', exist_ok=True)
    
    filename = f"data/raw/{symbol}_{timeframe}.csv"
    df.to_csv(filename, index=False)
    print(f"Generated {filename} with {n_candles} rows.")

if __name__ == "__main__":
    # Generate synced data
    # H1: 500 candles
    # M30: 1000 candles
    generate_data("XAUUSD", "H1", 500)
    generate_data("XAUUSD", "M30", 1000)
