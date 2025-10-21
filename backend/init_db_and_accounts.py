"""Initialize database and create accounts"""
import sqlite3
import bcrypt
from uuid import uuid4
from datetime import datetime

# Connect to database
conn = sqlite3.connect('mr_game_ops.db')
cursor = conn.cursor()

# Create finance_accounts table
cursor.execute('''
CREATE TABLE IF NOT EXISTS finance_accounts (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    role TEXT NOT NULL,
    permissions TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    last_login_at TEXT,
    last_login_ip TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    created_by TEXT
)
''')

# Hash password
password = "finance123456"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')

now = datetime.utcnow().isoformat()

# Insert finance accounts
accounts = [
    (str(uuid4()), 'finance_wang', hashed, 'Wang Min', '13800138010', 'wang.min@mr-game-ops.com',
     'finance_manager', '["transaction:all", "invoice:all", "refund:approve"]', 1, None, None, now, now, None),
    (str(uuid4()), 'finance_liu', hashed, 'Liu Fang', '13800138011', 'liu.fang@mr-game-ops.com',
     'finance_staff', '["transaction:view", "invoice:manage"]', 1, None, None, now, now, None),
]

for account in accounts:
    try:
        cursor.execute('''
            INSERT INTO finance_accounts
            (id, username, password_hash, full_name, phone, email, role, permissions,
             is_active, last_login_at, last_login_ip, created_at, updated_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', account)
        print(f"[SUCCESS] Created finance account: {account[1]}")
    except sqlite3.IntegrityError:
        print(f"[WARN] Account {account[1]} already exists")

conn.commit()
conn.close()

print("\n[SUCCESS] Finance accounts created successfully!")
print("Login credentials:")
print("  - finance_wang / finance123456 (Finance Manager)")
print("  - finance_liu / finance123456 (Finance Staff)")
