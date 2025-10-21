#!/usr/bin/env python3
"""Simple script to create initial admin accounts using raw SQL."""

import asyncio
import sys
import os
from pathlib import Path
import uuid

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))

from src.core.utils.password import hash_password
from src.db.session import init_db, get_engine
from sqlalchemy import text


async def create_initial_admins():
    """Create initial admin accounts using raw SQL."""

    # Initialize database connection
    init_db()
    engine = get_engine()

    # Generate password hashes
    superadmin_hash = hash_password("Admin123!@#")
    testadmin_hash = hash_password("Test123!@#")

    async with engine.begin() as conn:
        # Check if any admin exists
        result = await conn.execute(text("SELECT COUNT(*) FROM admin_accounts"))
        count = result.scalar()

        if count > 0:
            print(f"❌ Admin accounts already exist ({count} found). Skipping initialization.")
            return

        print("🔧 Creating initial admin accounts...")

        # Create super admin
        await conn.execute(
            text("""
                INSERT INTO admin_accounts
                (id, username, password_hash, full_name, email, phone, role, permissions, is_active)
                VALUES
                (:id, :username, :password_hash, :full_name, :email, :phone, :role, :permissions, :is_active)
            """),
            {
                "id": str(uuid.uuid4()),
                "username": "superadmin",
                "password_hash": superadmin_hash,
                "full_name": "Super Administrator",
                "email": "superadmin@mrgameops.com",
                "phone": "10000000000",
                "role": "super_admin",
                "permissions": "[]",
                "is_active": True,
            }
        )

        # Create test admin
        await conn.execute(
            text("""
                INSERT INTO admin_accounts
                (id, username, password_hash, full_name, email, phone, role, permissions, is_active)
                VALUES
                (:id, :username, :password_hash, :full_name, :email, :phone, :role, :permissions, :is_active)
            """),
            {
                "id": str(uuid.uuid4()),
                "username": "testadmin",
                "password_hash": testadmin_hash,
                "full_name": "Test Administrator",
                "email": "testadmin@mrgameops.com",
                "phone": "10000000001",
                "role": "admin",
                "permissions": "[]",
                "is_active": True,
            }
        )

        print("✅ Initial admin accounts created successfully!")
        print("\n📋 Login credentials:")
        print("  - Super Admin: superadmin / Admin123!@#")
        print("  - Test Admin:  testadmin / Test123!@#")


if __name__ == "__main__":
    asyncio.run(create_initial_admins())
