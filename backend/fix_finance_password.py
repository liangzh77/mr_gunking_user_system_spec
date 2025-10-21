"""Fix finance account passwords using bcrypt"""
import sqlite3
import bcrypt

# Hash password using bcrypt with rounds=10 (same as backend)
password = "finance123456"
password_bytes = password.encode('utf-8')
salt = bcrypt.gensalt(rounds=10)
hashed = bcrypt.hashpw(password_bytes, salt).decode('utf-8')

print(f"New password hash: {hashed[:50]}...")

# Connect to database
conn = sqlite3.connect('mr_game_ops.db')
cursor = conn.cursor()

# Update passwords
cursor.execute('UPDATE finance_accounts SET password_hash = ? WHERE username = ?',
               (hashed, 'finance_wang'))
cursor.execute('UPDATE finance_accounts SET password_hash = ? WHERE username = ?',
               (hashed, 'finance_liu'))

conn.commit()
conn.close()

print("[SUCCESS] Updated finance account passwords!")
print("Test credentials:")
print("  - finance_wang / finance123456")
print("  - finance_liu / finance123456")
