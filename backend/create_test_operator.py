#!/usr/bin/env python3
"""创建测试运营商账户"""
import sqlite3
import bcrypt
from uuid import uuid4
from datetime import datetime, timezone

# 连接数据库
conn = sqlite3.connect('mr_game_ops.db')
cursor = conn.cursor()

# 创建operator_accounts表（如果不存在）
cursor.execute('''
CREATE TABLE IF NOT EXISTS operator_accounts (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    api_key TEXT UNIQUE NOT NULL,
    api_key_hash TEXT UNIQUE NOT NULL,
    balance REAL NOT NULL DEFAULT 0.0,
    customer_tier TEXT NOT NULL DEFAULT 'basic',
    is_active INTEGER NOT NULL DEFAULT 1,
    is_locked INTEGER NOT NULL DEFAULT 0,
    locked_reason TEXT,
    locked_at TEXT,
    last_login_at TEXT,
    last_login_ip TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    CHECK (customer_tier IN ('basic', 'premium', 'enterprise'))
)
''')

# 创建applications表（如果不存在）
cursor.execute('''
CREATE TABLE IF NOT EXISTS applications (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    app_key TEXT UNIQUE NOT NULL,
    app_secret TEXT NOT NULL,
    callback_url TEXT,
    description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,
    FOREIGN KEY (created_by) REFERENCES operator_accounts(id)
)
''')

# Hash密码
password = "admin123"
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')

# 生成API Key
api_key = f"mr_test_{uuid4().hex}"
api_key_hash = bcrypt.hashpw(api_key.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')

now = datetime.now(timezone.utc).isoformat()

# 创建测试运营商账户
try:
    cursor.execute('''
        INSERT INTO operator_accounts
        (id, username, password_hash, full_name, phone, email, api_key, api_key_hash,
         balance, customer_tier, is_active, is_locked, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        str(uuid4()), 'admin', hashed, 'Test Operator', '13800138000', 'admin@test.com',
        api_key, api_key_hash, 10000.0, 'premium', 1, 0, now, now
    ))

    print(f"Successfully created test operator account:")
    print(f"   Username: admin")
    print(f"   Password: {password}")
    print(f"   API Key: {api_key}")

except sqlite3.IntegrityError as e:
    print(f"Account may already exist: {e}")

# 创建测试应用
try:
    app_id = str(uuid4())
    app_key = f"game_app_{uuid4().hex}"
    app_secret = f"secret_{uuid4().hex}"

    cursor.execute('''
        INSERT INTO applications
        (id, name, app_key, app_secret, description, callback_url, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        app_id, 'MR游戏测试应用', app_key, app_secret, '用于测试的游戏应用',
        'http://localhost:3000/callback', 1, now, now
    ))

    print(f"Successfully created test application:")
    print(f"   App Name: MR Game Test App")
    print(f"   App Key: {app_key}")
    print(f"   App Secret: {app_secret}")

except sqlite3.IntegrityError as e:
    print(f"Application may already exist: {e}")

# 提交并关闭
conn.commit()
conn.close()

print("\nInitialization completed!")