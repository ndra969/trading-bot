#!/usr/bin/env python3
"""
Simple Database Migration Script

Creates tables directly without Alembic complexity.
"""

import os

import psycopg2
from dotenv import load_dotenv


def get_connection():
    """Get PostgreSQL connection"""
    env = os.getenv("TRADING_BOT_ENV", "development").lower()
    env_file = f".env.{env}" if env != "development" else ".env.dev"
    load_dotenv(env_file)

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not found")

    # Parse database URL
    # postgresql+asyncpg://user:pass@localhost:5432/db
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    return psycopg2.connect(db_url)


def create_tables():
    """Create all required tables"""

    print("=" * 60)
    print("Simple Database Migration")
    print("=" * 60)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Drop existing tables if they exist
        print("[INFO] Dropping existing tables...")
        cursor.execute("DROP TABLE IF EXISTS position_updates CASCADE")
        cursor.execute("DROP TABLE IF EXISTS trades CASCADE")
        cursor.execute("DROP TABLE IF EXISTS supply_demand_zones CASCADE")

        # Create supply_demand_zones table
        print("[INFO] Creating supply_demand_zones table...")
        cursor.execute(
            """
            CREATE TABLE supply_demand_zones (
                id SERIAL PRIMARY KEY,
                zone_id VARCHAR(50) UNIQUE NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                zone_type VARCHAR(10) NOT NULL,  -- 'demand' or 'supply'
                high_price FLOAT(10) NOT NULL,
                low_price FLOAT(10) NOT NULL,
                entry_price FLOAT(10),
                strength FLOAT(2) DEFAULT 50.0,
                confluence_score FLOAT(2) DEFAULT 0.0,
                touched_count INTEGER DEFAULT 0,
                timeframe VARCHAR(10),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                last_touched TIMESTAMP WITH TIME ZONE,
                is_active BOOLEAN DEFAULT TRUE,
                trend_direction VARCHAR(10),
                market_session VARCHAR(20),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """
        )

        # Create indexes
        print("[INFO] Creating indexes...")
        cursor.execute("CREATE INDEX idx_supply_demand_zones_symbol ON supply_demand_zones(symbol)")
        cursor.execute(
            "CREATE INDEX idx_supply_demand_zones_zone_id ON supply_demand_zones(zone_id)"
        )
        cursor.execute(
            "CREATE INDEX idx_supply_demand_zones_strength ON supply_demand_zones(strength)"
        )

        # Create trades table
        print("[INFO] Creating trades table...")
        cursor.execute(
            """
            CREATE TABLE trades (
                id SERIAL PRIMARY KEY,
                trade_id VARCHAR(50) UNIQUE NOT NULL,
                symbol VARCHAR(20) NOT NULL,
                direction VARCHAR(10) NOT NULL,  -- 'BUY' or 'SELL'
                entry_price FLOAT(10) NOT NULL,
                stop_loss FLOAT(10) NOT NULL,
                take_profit FLOAT(10),
                volume FLOAT(8) NOT NULL,
                risk_amount FLOAT(2) NOT NULL,
                potential_profit FLOAT(2),
                pip_size FLOAT(10) NOT NULL,
                pip_value_per_lot FLOAT(4) NOT NULL,
                current_price FLOAT(10),
                current_profit_pips FLOAT(4),
                current_pnl_usd FLOAT(2),
                status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
                opened_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                closed_at TIMESTAMP WITH TIME ZONE,
                close_price FLOAT(10),
                exit_price FLOAT(10),
                strategy_name VARCHAR(100),
                confluence_score FLOAT(2),
                entry_zone_id INTEGER,
                exit_zone_id INTEGER,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                FOREIGN KEY (entry_zone_id) REFERENCES supply_demand_zones(id),
                FOREIGN KEY (exit_zone_id) REFERENCES supply_demand_zones(id)
            )
        """
        )

        # Create trades indexes
        cursor.execute("CREATE INDEX idx_trades_symbol ON trades(symbol)")
        cursor.execute("CREATE INDEX idx_trades_trade_id ON trades(trade_id)")
        cursor.execute("CREATE INDEX idx_trades_status ON trades(status)")

        # Create position_updates table
        print("[INFO] Creating position_updates table...")
        cursor.execute(
            """
            CREATE TABLE position_updates (
                id SERIAL PRIMARY KEY,
                trade_id INTEGER NOT NULL,
                update_type VARCHAR(20) NOT NULL,  -- 'OPEN', 'CLOSE', 'MODIFY', etc.
                old_stop_loss FLOAT(10),
                old_take_profit FLOAT(10),
                old_volume FLOAT(8),
                new_stop_loss FLOAT(10),
                new_take_profit FLOAT(10),
                new_volume FLOAT(8),
                reason TEXT,
                triggered_by VARCHAR(50),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE
            )
        """
        )

        # Create position_updates indexes
        cursor.execute("CREATE INDEX idx_position_updates_trade_id ON position_updates(trade_id)")
        cursor.execute(
            "CREATE INDEX idx_position_updates_created_at ON position_updates(created_at)"
        )

        conn.commit()
        print("[SUCCESS] All tables created successfully!")

        # Show table info
        print("\n[INFO] Database Tables Created:")
        cursor.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        tables = cursor.fetchall()
        for table in tables:
            print(f"  - {table[0]}")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Failed to create tables: {e}")
        raise
    finally:
        conn.close()


def test_connection():
    """Test database connection"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        print(f"[SUCCESS] Connected to PostgreSQL: {version[0]}")
        conn.close()
        return True
    except Exception as e:
        print(f"[ERROR] Failed to connect: {e}")
        return False


if __name__ == "__main__":
    if test_connection():
        create_tables()
    else:
        print("[ERROR] Cannot proceed with migration")
