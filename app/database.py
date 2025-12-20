"""
Модуль для работы с базой данных
PostgreSQL для продакшн (Railway) с поддержкой SQLite для локальной разработки
"""
import os
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Определяем тип БД
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
    """Класс для работы с БД (PostgreSQL или SQLite)"""
    
    def __init__(self):
        self.use_postgres = USE_POSTGRES
        self.init_database()
    
    def get_connection(self):
        """Создает подключение к БД"""
        if self.use_postgres:
            # PostgreSQL connection
            conn = psycopg2.connect(DATABASE_URL)
            return conn
        else:
            # SQLite connection
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            return conn
    
    def init_database(self):
        """Создает таблицы если их нет"""
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
        
        conn.commit()
        conn.close()
        print("✅ Database initialized!")
    
    # ===== WALLET METHODS =====
    
    def get_wallet(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получить кошелек пользователя"""
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
        """Создать новый кошелек"""
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
        """Получить все активные авто-ордера"""
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
        """Получить авто-ордера пользователя"""
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
        """Обновить статус авто-ордера"""
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
    
    # ===== TRANSACTION METHODS =====
    
    def add_transaction(self, telegram_id: int, market_alias: str,
                       side: str, amount: float, price: float, 
                       tx_hash: str = None) -> int:
        """Добавить транзакцию в историю"""
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
        """Получить историю транзакций пользователя"""
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
