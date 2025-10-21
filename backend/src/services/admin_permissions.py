"""Admin permission management utilities."""

from typing import List, Dict, Any, Set
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.admin import AdminAccount
from ..core.exceptions import ForbiddenException


class AdminPermissionChecker:
    """Admin permission checker utility class."""

    # 定义权限常量
    PERMISSIONS = {
        # 运营商管理权限
        "operator:create": "创建运营商账户",
        "operator:view": "查看运营商列表",
        "operator:edit": "编辑运营商信息",
        "operator:delete": "删除运营商账户",
        "operator:reset_api_key": "重置运营商API密钥",

        # 应用管理权限
        "application:create": "创建应用",
        "application:view": "查看应用列表",
        "application:edit": "编辑应用信息",
        "application:delete": "删除应用",
        "application:authorize": "授权应用给运营商",

        # 应用申请审核权限
        "application_request:view": "查看应用申请",
        "application_request:approve": "批准应用申请",
        "application_request:reject": "拒绝应用申请",

        # 运营点管理权限
        "site:view": "查看运营点",
        "site:create": "创建运营点",
        "site:edit": "编辑运营点",
        "site:delete": "删除运营点",

        # 交易和财务查看权限
        "transaction:view": "查看交易记录",
        "usage:view": "查看使用记录",
        "balance:view": "查看账户余额",

        # 系统管理权限
        "admin:view": "查看管理员列表",
        "admin:create": "创建管理员账户",
        "admin:edit": "编辑管理员信息",
        "admin:delete": "删除管理员账户",
        "system:statistics": "查看系统统计",
    }

    # 角色默认权限
    ROLE_PERMISSIONS = {
        "super_admin": list(PERMISSIONS.keys()),  # 超级管理员拥有所有权限

        "admin": [
            # 运营商管理
            "operator:view", "operator:create", "operator:edit", "operator:reset_api_key",
            # 应用管理
            "application:view", "application:create", "application:edit", "application:authorize",
            # 申请审核
            "application_request:view", "application_request:approve", "application_request:reject",
            # 运营点管理
            "site:view", "site:create", "site:edit",
            # 查看权限
            "transaction:view", "usage:view", "balance:view",
            # 系统统计
            "system:statistics",
        ],

        "operator_manager": [
            # 运营商管理（受限）
            "operator:view", "operator:edit",
            # 应用管理（受限）
            "application:view", "application:authorize",
            # 申请审核
            "application_request:view", "application_request:approve", "application_request:reject",
            # 查看权限
            "transaction:view", "usage:view", "balance:view",
        ],

        "auditor": [
            # 只读权限
            "operator:view", "application:view", "application_request:view",
            "site:view", "transaction:view", "usage:view", "balance:view",
            "system:statistics",
        ],
    }

    @classmethod
    def get_role_permissions(cls, role: str) -> Set[str]:
        """获取角色的默认权限

        Args:
            role: 管理员角色

        Returns:
            权限集合
        """
        return set(cls.ROLE_PERMISSIONS.get(role, []))

    @classmethod
    async def check_admin_permission(
        cls,
        db: AsyncSession,
        admin_id: UUID,
        required_permission: str
    ) -> bool:
        """检查管理员是否有特定权限

        Args:
            db: 数据库会话
            admin_id: 管理员ID
            required_permission: 需要的权限

        Returns:
            是否有权限
        """
        # 查询管理员信息
        result = await db.execute(
            select(AdminAccount).where(AdminAccount.id == admin_id)
        )
        admin = result.scalar_one_or_none()

        if not admin:
            return False

        if not admin.is_active:
            return False

        # 获取角色权限
        role_permissions = cls.get_role_permissions(admin.role)

        # 获取个人权限（如果有的话）
        personal_permissions = set(admin.permissions or [])

        # 合并权限
        all_permissions = role_permissions.union(personal_permissions)

        # 检查是否有所需权限
        return required_permission in all_permissions

    @classmethod
    async def require_permission(
        cls,
        db: AsyncSession,
        admin_id: UUID,
        required_permission: str
    ) -> None:
        """要求管理员有特定权限，如果没有则抛出异常

        Args:
            db: 数据库会话
            admin_id: 管理员ID
            required_permission: 需要的权限

        Raises:
            ForbiddenException: 如果没有权限
        """
        has_permission = await cls.check_admin_permission(db, admin_id, required_permission)

        if not has_permission:
            permission_name = cls.PERMISSIONS.get(required_permission, required_permission)
            raise ForbiddenException(
                f"权限不足，需要权限: {permission_name} ({required_permission})"
            )

    @classmethod
    async def get_admin_permissions(
        cls,
        db: AsyncSession,
        admin_id: UUID
    ) -> Dict[str, Any]:
        """获取管理员的所有权限信息

        Args:
            db: 数据库会话
            admin_id: 管理员ID

        Returns:
            权限信息字典
        """
        # 查询管理员信息
        result = await db.execute(
            select(AdminAccount).where(AdminAccount.id == admin_id)
        )
        admin = result.scalar_one_or_none()

        if not admin:
            return {}

        # 获取角色权限
        role_permissions = cls.get_role_permissions(admin.role)

        # 获取个人权限
        personal_permissions = set(admin.permissions or [])

        # 合并权限
        all_permissions = role_permissions.union(personal_permissions)

        return {
            "role": admin.role,
            "role_permissions": list(role_permissions),
            "personal_permissions": list(personal_permissions),
            "all_permissions": list(all_permissions),
            "permission_details": {
                perm: cls.PERMISSIONS.get(perm, perm)
                for perm in all_permissions
            }
        }

    @classmethod
    def validate_permission(cls, permission: str) -> bool:
        """验证权限是否有效

        Args:
            permission: 权限名称

        Returns:
            是否有效
        """
        return permission in cls.PERMISSIONS

    @classmethod
    def validate_role(cls, role: str) -> bool:
        """验证角色是否有效

        Args:
            role: 角色名称

        Returns:
            是否有效
        """
        return role in cls.ROLE_PERMISSIONS