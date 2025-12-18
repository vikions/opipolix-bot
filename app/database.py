"""
Модуль для работы с базой данных
Используем SQLite для простоты (можно потом переключить на PostgreSQL)
"""
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any

# Имя файла БД
DB_FILE = "opipolix.db"


class Database:
    """Класс для работы с БД"""
    
    def __init__(self, db_file: str = DB_FILE):
        self.db_file = db_file
        self.init_database()
    
    def get_connection(self):
        """Создает подключение к БД"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row  # Для доступа по имени колонки
        return conn
    
    def init_database(self):
        """Создает таблицы если их нет"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Таблица кошельков пользователей
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
        
        # Таблица авто-ордеров
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
        
        # Таблица истории транзакций
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
            cursor.execute("""
                INSERT INTO user_wallets 
                (telegram_id, eoa_address, eoa_private_key, safe_address)
                VALUES (?, ?, ?, ?)
            """, (telegram_id, eoa_address, eoa_private_key, safe_address))
            
            conn.commit()
            conn.close()
            return True
            
        except sqlite3.IntegrityError:
            # Кошелек уже существует
            conn.close()
            return False
    
    def update_safe_address(self, telegram_id: int, safe_address: str) -> bool:
        """Обновить Safe адрес"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
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


# Тест
def test_database():
    """Тест базы данных"""
    print("🧪 Testing database...\n")
    
    db = Database()
    
    # Тест 1: Создание кошелька
    test_telegram_id = 999999999
    
    wallet = db.get_wallet(test_telegram_id)
    if wallet:
        print(f"Wallet exists: {wallet['eoa_address']}")
    else:
        success = db.create_wallet(
            telegram_id=test_telegram_id,
            eoa_address="0xTEST123",
            eoa_private_key="encrypted_test_key",
            safe_address="0xSAFE123"
        )
        print(f"Created wallet: {success}")
    
    # Тест 2: Создание авто-ордера
    order_id = db.create_auto_order(
        telegram_id=test_telegram_id,
        market_alias="metamask",
        trigger_type="price_above",
        trigger_value=0.05,
        side="BUY",
        amount=10.0
    )
    print(f"Created auto-order: {order_id}")
    
    # Тест 3: Получение авто-ордеров
    orders = db.get_user_auto_orders(test_telegram_id)
    print(f"User has {len(orders)} active orders")
    
    print("\n✅ Database tests completed!")


if __name__ == "__main__":
    test_database()