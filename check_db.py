"""
Проверка структуры БД
"""
import sqlite3

DB_FILE = "opipolix.db"

conn = sqlite3.connect(DB_FILE)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Проверяем структуру таблицы
cursor.execute("PRAGMA table_info(user_wallets)")
columns = cursor.fetchall()

print("📊 Columns in user_wallets table:")
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

# Проверяем есть ли записи
cursor.execute("SELECT * FROM user_wallets")
rows = cursor.fetchall()

print(f"\n💾 Total wallets: {len(rows)}")

if rows:
    print("\n🔍 First wallet:")
    wallet = dict(rows[0])
    for key, value in wallet.items():
        if 'private_key' in key.lower():
            print(f"  {key}: [ENCRYPTED]")
        else:
            print(f"  {key}: {value}")

conn.close()
