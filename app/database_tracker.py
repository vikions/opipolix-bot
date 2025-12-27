"""
Database methods for address tracking
"""
from database import Database
from typing import List, Dict, Optional


class TrackerDatabase:
    """Database methods for Opinion address tracker"""
    
    def __init__(self, db: Database):
        self.db = db
        self._init_tracker_tables()
    
    def _init_tracker_tables(self):
        """Initialize tracked_addresses table"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        if self.db.use_postgres:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tracked_addresses (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT NOT NULL,
                    address VARCHAR(42) NOT NULL,
                    platform VARCHAR(20) DEFAULT 'opinion',
                    nickname VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(telegram_id, address, platform)
                )
            """)
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tracked_addresses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER NOT NULL,
                    address TEXT NOT NULL,
                    platform TEXT DEFAULT 'opinion',
                    nickname TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(telegram_id, address, platform)
                )
            """)
        
        conn.commit()
        conn.close()
    
    def add_tracked_address(self, telegram_id: int, address: str, 
                          platform: str = 'opinion', nickname: str = None) -> bool:
        """Add address to track"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            if self.db.use_postgres:
                cursor.execute("""
                    INSERT INTO tracked_addresses 
                    (telegram_id, address, platform, nickname)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (telegram_id, address, platform) DO UPDATE
                    SET nickname = EXCLUDED.nickname
                """, (telegram_id, address, platform, nickname))
            else:
                cursor.execute("""
                    INSERT OR REPLACE INTO tracked_addresses 
                    (telegram_id, address, platform, nickname)
                    VALUES (?, ?, ?, ?)
                """, (telegram_id, address, platform, nickname))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding tracked address: {e}")
            conn.close()
            return False
    
    def get_tracked_addresses(self, telegram_id: int, 
                             platform: str = 'opinion') -> List[Dict]:
        """Get all tracked addresses for user"""
        conn = self.db.get_connection()
        
        if self.db.use_postgres:
            from psycopg2.extras import RealDictCursor
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT * FROM tracked_addresses 
                WHERE telegram_id = %s AND platform = %s
                ORDER BY created_at DESC
            """, (telegram_id, platform))
        else:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tracked_addresses 
                WHERE telegram_id = ? AND platform = ?
                ORDER BY created_at DESC
            """, (telegram_id, platform))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def remove_tracked_address(self, telegram_id: int, address: str, 
                              platform: str = 'opinion') -> bool:
        """Remove tracked address"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        if self.db.use_postgres:
            cursor.execute("""
                DELETE FROM tracked_addresses 
                WHERE telegram_id = %s AND address = %s AND platform = %s
            """, (telegram_id, address, platform))
        else:
            cursor.execute("""
                DELETE FROM tracked_addresses 
                WHERE telegram_id = ? AND address = ? AND platform = ?
            """, (telegram_id, address, platform))
        
        conn.commit()
        conn.close()
        return True
