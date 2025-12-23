"""
Cashback Manager - Trade-to-Earn Promo
First X users who trade $Y+ get $Z cashback
"""
import sqlite3
from datetime import datetime
from typing import Optional, Dict

# Promo settings
PROMO_ENABLED = True
CASHBACK_AMOUNT = 1.0  # $1 USDC
MIN_VOLUME = 10.0      # $10 minimum trade volume
MAX_USERS = 10         # First 10 users only

DB_PATH = "wallets.db"


def init_cashback_table():
    """Create cashback tracking table"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        CREATE TABLE IF NOT EXISTS cashback_tracking (
            telegram_id INTEGER PRIMARY KEY,
            total_volume REAL DEFAULT 0,
            cashback_earned REAL DEFAULT 0,
            cashback_paid BOOLEAN DEFAULT 0,
            first_trade_at TEXT,
            cashback_paid_at TEXT
        )
    """)
    
    conn.commit()
    conn.close()


def track_trade(telegram_id: int, amount: float) -> Dict:
    """
    Track user trade and check if eligible for cashback
    
    Returns:
        {
            'eligible': bool,
            'cashback_amount': float,
            'total_volume': float,
            'already_paid': bool
        }
    """
    if not PROMO_ENABLED:
        return {
            'eligible': False,
            'cashback_amount': 0,
            'total_volume': 0,
            'already_paid': False
        }
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get or create tracking record
    c.execute("""
        SELECT total_volume, cashback_paid 
        FROM cashback_tracking 
        WHERE telegram_id = ?
    """, (telegram_id,))
    
    result = c.fetchone()
    
    if result:
        total_volume, cashback_paid = result
        total_volume += amount
        
        # Update volume
        c.execute("""
            UPDATE cashback_tracking 
            SET total_volume = ?
            WHERE telegram_id = ?
        """, (total_volume, telegram_id))
    else:
        # New user
        total_volume = amount
        cashback_paid = False
        
        c.execute("""
            INSERT INTO cashback_tracking 
            (telegram_id, total_volume, first_trade_at)
            VALUES (?, ?, ?)
        """, (telegram_id, total_volume, datetime.now().isoformat()))
    
    conn.commit()
    
    # Check eligibility
    eligible = False
    cashback_amount = 0
    
    if not cashback_paid and total_volume >= MIN_VOLUME:
        # Check if still within limit
        c.execute("""
            SELECT COUNT(*) 
            FROM cashback_tracking 
            WHERE cashback_paid = 1
        """)
        
        paid_count = c.fetchone()[0]
        
        if paid_count < MAX_USERS:
            eligible = True
            cashback_amount = CASHBACK_AMOUNT
    
    conn.close()
    
    return {
        'eligible': eligible,
        'cashback_amount': cashback_amount,
        'total_volume': total_volume,
        'already_paid': cashback_paid
    }


def mark_cashback_paid(telegram_id: int):
    """Mark cashback as paid for user"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        UPDATE cashback_tracking 
        SET cashback_paid = 1,
            cashback_earned = ?,
            cashback_paid_at = ?
        WHERE telegram_id = ?
    """, (CASHBACK_AMOUNT, datetime.now().isoformat(), telegram_id))
    
    conn.commit()
    conn.close()


def get_promo_stats() -> Dict:
    """Get current promo statistics"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""
        SELECT 
            COUNT(*) as total_participants,
            COUNT(CASE WHEN cashback_paid = 1 THEN 1 END) as cashback_paid_count,
            SUM(total_volume) as total_volume,
            SUM(cashback_earned) as total_cashback_paid
        FROM cashback_tracking
    """)
    
    result = c.fetchone()
    conn.close()
    
    return {
        'total_participants': result[0] or 0,
        'cashback_paid_count': result[1] or 0,
        'total_volume': result[2] or 0,
        'total_cashback_paid': result[3] or 0,
        'remaining_spots': MAX_USERS - (result[1] or 0)
    }


def is_promo_active() -> bool:
    """Check if promo is still active"""
    if not PROMO_ENABLED:
        return False
    
    stats = get_promo_stats()
    return stats['remaining_spots'] > 0


# Initialize on import
init_cashback_table()
