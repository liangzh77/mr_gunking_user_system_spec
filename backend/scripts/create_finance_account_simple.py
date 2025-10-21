"""
Simple script to create finance accounts directly in the database.
"""
import asyncio
import sys
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
import bcrypt

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def get_database_url():
    """Get database URL from environment or use default."""
    import os
    return os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./mr_game_ops.db")


async def create_finance_accounts():
    """Create finance accounts."""
    database_url = get_database_url()

    # Create async engine
    engine = create_async_engine(
        database_url,
        echo=False,
    )

    # Create async session maker
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        try:
            print("\n[INFO] Creating finance accounts...\n")

            # Hash password
            finance_password_hash = hash_password("finance123456")

            # Set created_by to None (can be updated later)
            created_by = None

            # Create finance accounts
            finance_accounts = [
                {
                    "id": str(uuid4()),
                    "username": "finance_wang",
                    "full_name": "Wang Min",
                    "email": "wang.min@mr-game-ops.com",
                    "phone": "13800138010",
                    "password_hash": finance_password_hash,
                    "role": "finance_manager",
                    "permissions": '["transaction:all", "invoice:all", "refund:approve"]',
                    "is_active": True,
                    "created_by": created_by,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                },
                {
                    "id": str(uuid4()),
                    "username": "finance_liu",
                    "full_name": "Liu Fang",
                    "email": "liu.fang@mr-game-ops.com",
                    "phone": "13800138011",
                    "password_hash": finance_password_hash,
                    "role": "finance_staff",
                    "permissions": '["transaction:view", "invoice:manage"]',
                    "is_active": True,
                    "created_by": created_by,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                },
            ]

            for finance in finance_accounts:
                # Check if account already exists
                result = await session.execute(
                    text("SELECT username FROM finance_accounts WHERE username = :username"),
                    {"username": finance["username"]}
                )
                if result.first():
                    print(f"[WARN] Account {finance['username']} already exists, skipping...")
                    continue

                # Insert
                await session.execute(
                    text("""
                        INSERT INTO finance_accounts
                        (id, username, full_name, email, phone, password_hash, role,
                         permissions, is_active, created_by, created_at, updated_at)
                        VALUES (:id, :username, :full_name, :email, :phone, :password_hash,
                                :role, :permissions::jsonb, :is_active, :created_by::uuid,
                                :created_at, :updated_at)
                    """),
                    finance
                )
                print(f"[SUCCESS] Created finance account: {finance['username']}")

            await session.commit()
            print("\n[SUCCESS] Finance accounts created successfully!\n")
            print("Login credentials:")
            print("  - finance_wang / finance123456 (Finance Manager)")
            print("  - finance_liu / finance123456 (Finance Staff)")
            print("\n")

        except Exception as e:
            print(f"\n[ERROR] Error: {e}\n")
            await session.rollback()
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_finance_accounts())
