"""Seed data script for initial database setup.

This script creates initial test accounts and system configurations:
- 1 super admin account
- 2 regular admin accounts
- 2 finance accounts
- 3 operator accounts (VIP, Standard, Trial tiers)
- Initial system configurations
"""

import asyncio
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.core import hash_password, get_settings


async def create_seed_data():
    """Create seed data in the database."""
    settings = get_settings()

    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=True,
    )

    # Create async session maker
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        try:
            print("\n🌱 Starting seed data creation...\n")

            # ========== System Configurations ==========
            print("📝 Creating system configurations...")
            system_configs = [
                {
                    "id": uuid4(),
                    "config_key": "balance_threshold",
                    "config_value": "100.00",
                    "value_type": "float",
                    "category": "business",
                    "description": "Low balance alert threshold (yuan)",
                    "is_editable": True,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                },
                {
                    "id": uuid4(),
                    "config_key": "session_timeout_minutes",
                    "config_value": "30",
                    "value_type": "integer",
                    "category": "security",
                    "description": "User session timeout in minutes",
                    "is_editable": True,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                },
                {
                    "id": uuid4(),
                    "config_key": "payment_timeout_minutes",
                    "config_value": "5",
                    "value_type": "integer",
                    "category": "business",
                    "description": "Payment callback timeout in minutes",
                    "is_editable": True,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                },
            ]

            for config in system_configs:
                await session.execute(
                    text("""
                        INSERT INTO system_configs
                        (id, config_key, config_value, value_type, category, description,
                         is_editable, created_at, updated_at)
                        VALUES (:id, :config_key, :config_value, :value_type, :category,
                                :description, :is_editable, :created_at, :updated_at)
                    """),
                    config
                )
            print(f"✅ Created {len(system_configs)} system configurations\n")

            # ========== Admin Accounts ==========
            print("👤 Creating admin accounts...")
            admin_password_hash = hash_password("admin123456")

            admin_accounts = [
                {
                    "id": uuid4(),
                    "username": "superadmin",
                    "full_name": "Super Administrator",
                    "email": "superadmin@mr-game-ops.com",
                    "phone": "13800138000",
                    "password_hash": admin_password_hash,
                    "role": "super_admin",
                    "permissions": '["system:all"]',
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                },
                {
                    "id": uuid4(),
                    "username": "admin_zhang",
                    "full_name": "Zhang Wei",
                    "email": "zhang.wei@mr-game-ops.com",
                    "phone": "13800138001",
                    "password_hash": admin_password_hash,
                    "role": "admin",
                    "permissions": '["operator:manage", "app:review"]',
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                },
                {
                    "id": uuid4(),
                    "username": "admin_li",
                    "full_name": "Li Na",
                    "email": "li.na@mr-game-ops.com",
                    "phone": "13800138002",
                    "password_hash": admin_password_hash,
                    "role": "admin",
                    "permissions": '["operator:view", "app:view"]',
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                },
            ]

            for admin in admin_accounts:
                await session.execute(
                    text("""
                        INSERT INTO admin_accounts
                        (id, username, full_name, email, phone, password_hash, role,
                         permissions, is_active, created_at, updated_at)
                        VALUES (:id, :username, :full_name, :email, :phone, :password_hash,
                                :role, :permissions::jsonb, :is_active, :created_at, :updated_at)
                    """),
                    admin
                )
            print(f"✅ Created {len(admin_accounts)} admin accounts")
            print(f"   📧 superadmin / admin123456 (super admin)\n")

            # ========== Finance Accounts ==========
            print("💰 Creating finance accounts...")
            finance_password_hash = hash_password("finance123456")

            # Get first admin ID for created_by
            first_admin_id = admin_accounts[0]["id"]

            finance_accounts = [
                {
                    "id": uuid4(),
                    "username": "finance_wang",
                    "full_name": "Wang Min",
                    "email": "wang.min@mr-game-ops.com",
                    "phone": "13800138010",
                    "password_hash": finance_password_hash,
                    "role": "finance_manager",
                    "permissions": '["transaction:all", "invoice:all", "refund:approve"]',
                    "is_active": True,
                    "created_by": first_admin_id,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                },
                {
                    "id": uuid4(),
                    "username": "finance_liu",
                    "full_name": "Liu Fang",
                    "email": "liu.fang@mr-game-ops.com",
                    "phone": "13800138011",
                    "password_hash": finance_password_hash,
                    "role": "finance_staff",
                    "permissions": '["transaction:view", "invoice:manage"]',
                    "is_active": True,
                    "created_by": first_admin_id,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                },
            ]

            for finance in finance_accounts:
                await session.execute(
                    text("""
                        INSERT INTO finance_accounts
                        (id, username, full_name, email, phone, password_hash, role,
                         permissions, is_active, created_by, created_at, updated_at)
                        VALUES (:id, :username, :full_name, :email, :phone, :password_hash,
                                :role, :permissions::jsonb, :is_active, :created_by, :created_at, :updated_at)
                    """),
                    finance
                )
            print(f"✅ Created {len(finance_accounts)} finance accounts")
            print(f"   📧 finance_wang / finance123456\n")

            # ========== Operator Accounts ==========
            print("🎮 Creating operator accounts...")
            operator_password_hash = hash_password("operator123456")

            operators = [
                {
                    "id": uuid4(),
                    "username": "operator_vip",
                    "full_name": "VIP Game Studio",
                    "phone": "13800138020",
                    "email": "vip@game-studio.com",
                    "password_hash": operator_password_hash,
                    "api_key": secrets.token_urlsafe(32),
                    "api_key_hash": hash_password(secrets.token_urlsafe(32)),
                    "balance": 5000.00,
                    "customer_tier": "vip",
                    "is_active": True,
                    "is_locked": False,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                },
                {
                    "id": uuid4(),
                    "username": "operator_standard",
                    "full_name": "Standard Game Company",
                    "phone": "13800138021",
                    "email": "standard@game-company.com",
                    "password_hash": operator_password_hash,
                    "api_key": secrets.token_urlsafe(32),
                    "api_key_hash": hash_password(secrets.token_urlsafe(32)),
                    "balance": 1000.00,
                    "customer_tier": "standard",
                    "is_active": True,
                    "is_locked": False,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                },
                {
                    "id": uuid4(),
                    "username": "operator_trial",
                    "full_name": "Trial Gaming Studio",
                    "phone": "13800138022",
                    "email": "trial@gaming-studio.com",
                    "password_hash": operator_password_hash,
                    "api_key": secrets.token_urlsafe(32),
                    "api_key_hash": hash_password(secrets.token_urlsafe(32)),
                    "balance": 50.00,
                    "customer_tier": "trial",
                    "is_active": True,
                    "is_locked": False,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                },
            ]

            for operator in operators:
                await session.execute(
                    text("""
                        INSERT INTO operator_accounts
                        (id, username, full_name, phone, email, password_hash, api_key,
                         api_key_hash, balance, customer_tier, is_active, is_locked,
                         created_at, updated_at)
                        VALUES (:id, :username, :full_name, :phone, :email, :password_hash,
                                :api_key, :api_key_hash, :balance, :customer_tier, :is_active,
                                :is_locked, :created_at, :updated_at)
                    """),
                    operator
                )
            print(f"✅ Created {len(operators)} operator accounts")
            print(f"   📧 operator_vip / operator123456 (VIP tier, 5000¥)")
            print(f"   📧 operator_standard / operator123456 (Standard tier, 1000¥)")
            print(f"   📧 operator_trial / operator123456 (Trial tier, 50¥)\n")

            # Commit all changes
            await session.commit()

            print("✅ All seed data created successfully!\n")
            print("=" * 60)
            print("🎉 Database seeding completed!")
            print("=" * 60)
            print("\n📝 Test Accounts Summary:")
            print("-" * 60)
            print("Admin Accounts:")
            print("  superadmin / admin123456 (Super Admin)")
            print("  admin_zhang / admin123456 (Admin)")
            print("  admin_li / admin123456 (Admin)")
            print("\nFinance Accounts:")
            print("  finance_wang / finance123456 (Finance Manager)")
            print("  finance_liu / finance123456 (Finance Staff)")
            print("\nOperator Accounts:")
            print("  operator_vip / operator123456 (VIP, Balance: 5000¥)")
            print("  operator_standard / operator123456 (Standard, Balance: 1000¥)")
            print("  operator_trial / operator123456 (Trial, Balance: 50¥)")
            print("-" * 60)

        except Exception as e:
            print(f"\n❌ Error creating seed data: {e}")
            await session.rollback()
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_seed_data())
