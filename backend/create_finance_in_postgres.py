"""Create finance accounts in PostgreSQL database"""
import asyncio
import sys
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Use same context as backend
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=10,
)

async def create_finance_accounts():
    """Create finance accounts in PostgreSQL."""

    # PostgreSQL connection string
    database_url = "postgresql+asyncpg://mr_admin:mr_secure_password_2024@localhost:5432/mr_game_ops"

    # Create async engine
    engine = create_async_engine(database_url, echo=False)

    # Create async session maker
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        try:
            print("\n[INFO] Creating finance accounts in PostgreSQL...\n")

            # Hash password
            finance_password_hash = pwd_context.hash("finance123456")
            print(f"Password hash: {finance_password_hash[:50]}...")

            # Finance accounts data
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
                    print(f"[WARN] Account {finance['username']} already exists, updating password...")
                    # Update password
                    await session.execute(
                        text("""
                            UPDATE finance_accounts
                            SET password_hash = :password_hash,
                                updated_at = :updated_at
                            WHERE username = :username
                        """),
                        {
                            "password_hash": finance["password_hash"],
                            "updated_at": finance["updated_at"],
                            "username": finance["username"]
                        }
                    )
                else:
                    # Insert new account
                    await session.execute(
                        text("""
                            INSERT INTO finance_accounts
                            (id, username, full_name, email, phone, password_hash, role,
                             permissions, is_active, created_at, updated_at)
                            VALUES (:id::uuid, :username, :full_name, :email, :phone, :password_hash,
                                    :role, :permissions::jsonb, :is_active, :created_at, :updated_at)
                        """),
                        finance
                    )
                    print(f"[SUCCESS] Created finance account: {finance['username']}")

            await session.commit()
            print("\n[SUCCESS] Finance accounts ready in PostgreSQL!")
            print("\nLogin credentials:")
            print("  - finance_wang / finance123456 (Finance Manager)")
            print("  - finance_liu / finance123456 (Finance Staff)")
            print("\n")

        except Exception as e:
            print(f"\n[ERROR] Error: {e}\n")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_finance_accounts())
