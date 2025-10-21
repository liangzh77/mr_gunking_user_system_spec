"""Test password verification"""
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=10,
)

password = "finance123456"
hashed = "$2b$10$HGwsM4HAJPMs93JCGJUjeOGecH8M3.GtPU67TiXAr4lGMjC.NhDfq"

print(f"Testing password: {password}")
print(f"Against hash: {hashed[:50]}...")

try:
    result = pwd_context.verify(password, hashed)
    print(f"\nVerification result: {result}")
except Exception as e:
    print(f"\nError: {e}")
