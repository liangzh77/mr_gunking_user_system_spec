"""Update finance account passwords with compatible bcrypt"""
import sqlite3
from passlib.context import CryptContext

# Use same context as backend
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=10,
)

# Hash password using passlib (now with compatible bcrypt)
password = "finance123456"
hashed = pwd_context.hash(password)

print(f"New password hash: {hashed[:50]}...")

# Test verification
result = pwd_context.verify(password, hashed)
print(f"Verification test: {result}")

# Connect to database
conn = sqlite3.connect('mr_game_ops.db')
cursor = conn.cursor()

# Update passwords
cursor.execute('UPDATE finance_accounts SET password_hash = ? WHERE username = ?',
               (hashed, 'finance_wang'))
cursor.execute('UPDATE finance_accounts SET password_hash = ? WHERE username = ?',
               (hashed, 'finance_liu'))

conn.commit()

# Verify update
cursor.execute('SELECT username, substr(password_hash, 1, 30) FROM finance_accounts')
rows = cursor.fetchall()
print("\nUpdated accounts:")
for row in rows:
    print(f"  {row[0]}: {row[1]}...")

conn.close()

print("\n[SUCCESS] Finance account passwords updated with compatible bcrypt!")
print("Login credentials:")
print("  - finance_wang / finance123456")
print("  - finance_liu / finance123456")
