
import os
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")  # PostgreSQL URL from Railway
USE_POSTGRES = DATABASE_URL is not None

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    print("🐘 Using PostgreSQL")
else:
    import sqlite3
    print("📁 Using SQLite (local development)")
    DB_FILE = "opipolix.db"


class Database:
    
    
    def __init__(self):
        self.use_postgres = USE_POSTGRES
        self.init_database()
    
    def get_connection(self):
        """Создает подключение к БД"""
        if self.use_postgres:
            
            conn = psycopg2.connect(DATABASE_URL)
            return conn
        else:
            
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            return conn
    
    def init_database(self):
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if self.use_postgres:
            # PostgreSQL syntax
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_wallets (
                    telegram_id BIGINT PRIMARY KEY,
                    eoa_address TEXT NOT NULL,
                    eoa_private_key TEXT NOT NULL,
                    safe_address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS auto_orders (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT NOT NULL,
                    market_alias TEXT NOT NULL,
                    trigger_type TEXT NOT NULL,
                    trigger_value REAL NOT NULL,
                    side TEXT NOT NULL,
                    amount REAL NOT NULL,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    executed_at TIMESTAMP,
                    FOREIGN KEY (telegram_id) REFERENCES user_wallets(telegram_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT NOT NULL,
                    market_alias TEXT NOT NULL,
                    side TEXT NOT NULL,
                    amount REAL NOT NULL,
                    price REAL NOT NULL,
                    tx_hash TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (telegram_id) REFERENCES user_wallets(telegram_id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS opinion_alerts (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT NOT NULL,
                    market_id INTEGER NOT NULL,
                    alert_type TEXT NOT NULL,
                    trigger_percent REAL NOT NULL,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    triggered_at TIMESTAMP
                )
            """)
        else:
            # SQLite syntax
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_wallets (
                    telegram_id INTEGER PRIMARY KEY,
                    eoa_address TEXT NOT NULL,
                    eoa_private_key TEXT NOT NULL,
                    safe_address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS auto_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    market_alias TEXT NOT NULL,
                    trigger_type TEXT NOT NULL,
                    trigger_value REAL NOT NULL,
                    side TEXT NOT NULL,
                    amount REAL NOT NULL,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    executed_at TIMESTAMP,
                    FOREIGN KEY (telegram_id) REFERENCES user_wallets(telegram_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    market_alias TEXT NOT NULL,
                    side TEXT NOT NULL,
                    amount REAL NOT NULL,
                    price REAL NOT NULL,
                    tx_hash TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (telegram_id) REFERENCES user_wallets(telegram_id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS opinion_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    market_id INTEGER NOT NULL,
                    alert_type TEXT NOT NULL,
                    trigger_percent REAL NOT NULL,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    triggered_at TIMESTAMP
                )
            """)
        
        conn.commit()
        conn.close()
        print("✅ Database initialized!")
    
    # ===== WALLET METHODS =====
    
    def get_wallet(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        
        conn = self.get_connection()
        
        if self.use_postgres:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                "SELECT * FROM user_wallets WHERE telegram_id = %s",
                (telegram_id,)
            )
        else:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM user_wallets WHERE telegram_id = ?",
                (telegram_id,)
            )
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def create_wallet(self, telegram_id: int, eoa_address: str, 
                     eoa_private_key: str, safe_address: str = None) -> bool:
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if self.use_postgres:
                cursor.execute("""
                    INSERT INTO user_wallets 
                    (telegram_id, eoa_address, eoa_private_key, safe_address)
                    VALUES (%s, %s, %s, %s)
                """, (telegram_id, eoa_address, eoa_private_key, safe_address))
            else:
                cursor.execute("""
                    INSERT INTO user_wallets 
                    (telegram_id, eoa_address, eoa_private_key, safe_address)
                    VALUES (?, ?, ?, ?)
                """, (telegram_id, eoa_address, eoa_private_key, safe_address))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error creating wallet: {e}")
            conn.close()
            return False
    
    def update_safe_address(self, telegram_id: int, safe_address: str) -> bool:
        """Обновить Safe адрес"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if self.use_postgres:
            cursor.execute("""
                UPDATE user_wallets 
                SET safe_address = %s, updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = %s
            """, (safe_address, telegram_id))
        else:
            cursor.execute("""
                UPDATE user_wallets 
                SET safe_address = ?, updated_at = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            """, (safe_address, telegram_id))
        
        conn.commit()
        conn.close()
        return True
    
    # ===== AUTO ORDER METHODS =====
    
    def create_auto_order(self, telegram_id: int, market_alias: str,
                         trigger_type: str, trigger_value: float,
                         side: str, amount: float) -> int:
        """Создать авто-ордер"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if self.use_postgres:
            cursor.execute("""
                INSERT INTO auto_orders 
                (telegram_id, market_alias, trigger_type, trigger_value, side, amount)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (telegram_id, market_alias, trigger_type, trigger_value, side, amount))
            order_id = cursor.fetchone()[0]
        else:
            cursor.execute("""
                INSERT INTO auto_orders 
                (telegram_id, market_alias, trigger_type, trigger_value, side, amount)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (telegram_id, market_alias, trigger_type, trigger_value, side, amount))
            order_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return order_id
    
    def get_active_auto_orders(self):
        
        conn = self.get_connection()
        
        if self.use_postgres:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM auto_orders 
            WHERE status = 'active'
            ORDER BY created_at DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_user_auto_orders(self, telegram_id: int):
        
        conn = self.get_connection()
        
        if self.use_postgres:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT * FROM auto_orders 
                WHERE telegram_id = %s AND status = 'active'
                ORDER BY created_at DESC
            """, (telegram_id,))
        else:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM auto_orders 
                WHERE telegram_id = ? AND status = 'active'
                ORDER BY created_at DESC
            """, (telegram_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def update_auto_order_status(self, order_id: int, status: str):
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if self.use_postgres:
            cursor.execute("""
                UPDATE auto_orders 
                SET status = %s, executed_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (status, order_id))
        else:
            cursor.execute("""
                UPDATE auto_orders 
                SET status = ?, executed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, order_id))
        
        conn.commit()
        conn.close()
    
    # ===== OPINION ALERT METHODS =====
    
    def create_opinion_alert(
        self,
        telegram_id: int,
        market_id: int,
        alert_type: str,
        trigger_percent: float
    ) -> int:
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if self.use_postgres:
            cursor.execute("""
                INSERT INTO opinion_alerts
                (telegram_id, market_id, alert_type, trigger_percent)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (telegram_id, market_id, alert_type, trigger_percent))
            alert_id = cursor.fetchone()[0]
        else:
            cursor.execute("""
                INSERT INTO opinion_alerts
                (telegram_id, market_id, alert_type, trigger_percent)
                VALUES (?, ?, ?, ?)
            """, (telegram_id, market_id, alert_type, trigger_percent))
            alert_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return alert_id
    
    def get_user_opinion_alerts(self, telegram_id: int) -> list:
        
        conn = self.get_connection()
        
        if self.use_postgres:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT * FROM opinion_alerts
                WHERE telegram_id = %s
                ORDER BY created_at DESC
            """, (telegram_id,))
        else:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM opinion_alerts
                WHERE telegram_id = ?
                ORDER BY created_at DESC
            """, (telegram_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_active_opinion_alerts(self) -> list:
        
        conn = self.get_connection()
        
        if self.use_postgres:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM opinion_alerts
            WHERE status = 'active'
            ORDER BY created_at DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def update_opinion_alert_status(self, alert_id: int, status: str):
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if status == 'triggered':
            if self.use_postgres:
                cursor.execute("""
                    UPDATE opinion_alerts
                    SET status = %s, triggered_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (status, alert_id))
            else:
                cursor.execute("""
                    UPDATE opinion_alerts
                    SET status = ?, triggered_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, alert_id))
        else:
            if self.use_postgres:
                cursor.execute("""
                    UPDATE opinion_alerts
                    SET status = %s
                    WHERE id = %s
                """, (status, alert_id))
            else:
                cursor.execute("""
                    UPDATE opinion_alerts
                    SET status = ?
                    WHERE id = ?
                """, (status, alert_id))
        
        conn.commit()
        conn.close()
    
    # ===== TRANSACTION METHODS =====
    
    def add_transaction(self, telegram_id: int, market_alias: str,
                       side: str, amount: float, price: float, 
                       tx_hash: str = None) -> int:
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if self.use_postgres:
            cursor.execute("""
                INSERT INTO transactions 
                (telegram_id, market_alias, side, amount, price, tx_hash)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (telegram_id, market_alias, side, amount, price, tx_hash))
            tx_id = cursor.fetchone()[0]
        else:
            cursor.execute("""
                INSERT INTO transactions 
                (telegram_id, market_alias, side, amount, price, tx_hash)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (telegram_id, market_alias, side, amount, price, tx_hash))
            tx_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return tx_id
    
    def get_user_transactions(self, telegram_id: int, limit: int = 10):
        
        conn = self.get_connection()
        
        if self.use_postgres:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT * FROM transactions 
                WHERE telegram_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (telegram_id, limit))
        else:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM transactions 
                WHERE telegram_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (telegram_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
