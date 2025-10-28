#!/usr/bin/env python3
"""Initialize database with default admin accounts."""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))

from sqlalchemy import select
from src.db.session import init_db, get_db_context
from src.models.admin import AdminAccount
from src.core.utils.password import hash_password


async def create_initial_admins():
    """Create initial admin accounts if they don't exist."""

    # Initialize database connection
    init_db()

    async with get_db_context() as session:
        # Check if any admin exists
        result = await session.execute(select(AdminAccount))
        existing_admins = result.scalars().all()

        if existing_admins:
            print(f"❌ Admin accounts already exist ({len(existing_admins)} found). Skipping initialization.")
            return

        print("🔧 Creating initial admin accounts...")

        # Create super admin
        super_admin = AdminAccount(
            username="superadmin",
            password_hash=hash_password("Admin123!@#"),
            full_name="Super Administrator",
            email="superadmin@mrgameops.com",
            phone="10000000000",
            role="super_admin",
            permissions=[],
            is_active=True,
        )

        # Create test admin
        test_admin = AdminAccount(
            username="testadmin",
            password_hash=hash_password("Test123!@#"),
            full_name="Test Administrator",
            email="testadmin@mrgameops.com",
            phone="10000000001",
            role="admin",
            permissions=[],
            is_active=True,
        )

        session.add(super_admin)
        session.add(test_admin)

        await session.commit()

        print("✅ Initial admin accounts created successfully!")
        print("\n📋 Login credentials:")
        print("  - Super Admin: superadmin / Admin123!@#")
        print("  - Test Admin:  testadmin / Test123!@#")


if __name__ == "__main__":
    asyncio.run(create_initial_admins())
