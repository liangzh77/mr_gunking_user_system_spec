"""
运营商服务 (OperatorService) - T062

此服务提供运营商账户管理的核心业务逻辑:
1. 注册 - 创建新运营商账户并生成API Key
2. 登录 - 验证凭证并返回JWT Token
3. 个人信息管理 - 查询和更新运营商信息

安全特性:
- 密码使用bcrypt哈希存储
- API Key生成使用安全随机数
- JWT Token用于Web端认证
- 支持账户锁定和注销
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security.jwt import create_access_token
from ..core.utils.password import hash_password, verify_password
from ..models.operator import OperatorAccount
from ..schemas.operator import (
    OperatorProfile,
    OperatorRegisterRequest,
    OperatorRegisterData,
    OperatorUpdateRequest,
)
from ..schemas.auth import LoginResponse, LoginData, OperatorInfo


class OperatorService:
    """运营商服务类

    提供运营商账户的CRUD操作和认证功能
    """

    def __init__(self, db: AsyncSession):
        """初始化服务

        Args:
            db: 数据库会话
        """
        self.db = db

    @staticmethod
    def _generate_api_key() -> str:
        """生成64位安全随机API Key

        使用密码学安全的随机数生成器(secrets模块)

        Returns:
            str: 64位十六进制字符串
        """
        return secrets.token_hex(32)  # 32字节 = 64位十六进制

    async def _check_username_exists(self, username: str) -> bool:
        """检查用户名是否已存在(排除软删除)

        Args:
            username: 用户名

        Returns:
            bool: 存在返回True,不存在返回False
        """
        stmt = select(OperatorAccount).where(
            OperatorAccount.username == username,
            OperatorAccount.deleted_at.is_(None)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def register(
        self,
        request: OperatorRegisterRequest
    ) -> OperatorRegisterData:
        """注册新运营商账户

        流程:
        1. 验证用户名唯一性
        2. 哈希密码
        3. 生成API Key和哈希
        4. 创建账户记录
        5. 返回账户信息和API Key(明文,仅此一次)

        Args:
            request: 注册请求数据

        Returns:
            OperatorRegisterData: 包含operator_id和api_key的数据对象

        Raises:
            HTTPException 400: 用户名已存在
        """
        # 1. 检查用户名是否已存在
        if await self._check_username_exists(request.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "USERNAME_EXISTS",
                    "message": "用户名已被注册,请更换"
                }
            )

        # 2. 哈希密码
        password_hash = hash_password(request.password)

        # 3. 生成API Key
        api_key = self._generate_api_key()
        api_key_hash = hash_password(api_key)  # 哈希存储

        # 4. 创建运营商账户
        operator = OperatorAccount(
            username=request.username,
            full_name=request.name,
            phone=request.phone,
            email=request.email,
            password_hash=password_hash,
            api_key=api_key,  # 明文存储(用于API Key认证)
            api_key_hash=api_key_hash,
            customer_tier="trial",  # 新注册默认试用客户
            balance=0.00,
            is_active=True,
            is_locked=False
        )

        self.db.add(operator)
        await self.db.commit()
        await self.db.refresh(operator)

        # 5. 返回响应数据(API Key仅此一次返回明文)
        return OperatorRegisterData(
            operator_id=f"op_{operator.id}",
            username=operator.username,
            api_key=api_key,  # 明文,仅显示一次
            category=operator.customer_tier,
            balance=str(operator.balance),
            created_at=operator.created_at
        )

    async def login(
        self,
        username: str,
        password: str,
        login_ip: Optional[str] = None
    ) -> LoginResponse:
        """运营商登录

        流程:
        1. 查找用户(排除软删除)
        2. 验证密码
        3. 检查账户状态(是否注销/锁定)
        4. 生成JWT Token
        5. 更新最近登录信息
        6. 返回Token和用户信息

        Args:
            username: 用户名
            password: 密码(明文)
            login_ip: 登录IP地址(可选)

        Returns:
            LoginResponse: 包含access_token和operator信息

        Raises:
            HTTPException 401: 用户名或密码错误
            HTTPException 403: 账户已注销
        """
        # 1. 查找用户(排除软删除)
        stmt = select(OperatorAccount).where(
            OperatorAccount.username == username,
            OperatorAccount.deleted_at.is_(None)
        )
        result = await self.db.execute(stmt)
        operator = result.scalar_one_or_none()

        # 2. 验证用户存在且密码正确
        if not operator or not verify_password(password, operator.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error_code": "UNAUTHORIZED",
                    "message": "用户名或密码错误"
                }
            )

        # 3. 检查账户状态
        if not operator.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCOUNT_DEACTIVATED",
                    "message": "账户已注销,无法登录"
                }
            )

        if operator.is_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCOUNT_LOCKED",
                    "message": f"账户已被锁定,原因: {operator.locked_reason or '安全原因'}"
                }
            )

        # 4. 生成JWT Token (30天有效期)
        token_expires = timedelta(days=30)
        access_token = create_access_token(
            subject=str(operator.id),
            user_type="operator",
            expires_delta=token_expires,
            additional_claims={
                "username": operator.username,
                "category": operator.customer_tier
            }
        )

        # 5. 更新最近登录信息
        operator.last_login_at = datetime.now(timezone.utc)
        if login_ip:
            operator.last_login_ip = login_ip
        await self.db.commit()

        # 6. 返回登录响应
        return LoginResponse(
            success=True,
            data=LoginData(
                access_token=access_token,
                token_type="Bearer",
                expires_in=int(token_expires.total_seconds()),  # 2592000秒 = 30天
                operator=OperatorInfo(
                    operator_id=f"op_{operator.id}",
                    username=operator.username,
                    name=operator.full_name,
                    category=operator.customer_tier
                )
            )
        )

    async def get_profile(self, operator_id: UUID) -> OperatorProfile:
        """获取运营商个人信息

        Args:
            operator_id: 运营商ID

        Returns:
            OperatorProfile: 运营商详细信息

        Raises:
            HTTPException 404: 运营商不存在
        """
        stmt = select(OperatorAccount).where(
            OperatorAccount.id == operator_id,
            OperatorAccount.deleted_at.is_(None)
        )
        result = await self.db.execute(stmt)
        operator = result.scalar_one_or_none()

        if not operator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "OPERATOR_NOT_FOUND",
                    "message": "运营商不存在"
                }
            )

        return OperatorProfile(
            operator_id=operator.id,
            username=operator.username,
            name=operator.full_name,
            phone=operator.phone,
            email=operator.email,
            category=operator.customer_tier,
            balance=str(operator.balance),
            is_active=operator.is_active,
            is_locked=operator.is_locked,
            last_login_at=operator.last_login_at,
            created_at=operator.created_at
        )

    async def update_profile(
        self,
        operator_id: UUID,
        request: OperatorUpdateRequest
    ) -> OperatorProfile:
        """更新运营商个人信息

        允许更新: 姓名、电话、邮箱
        不允许更新: 用户名、密码、余额、客户分类等

        Args:
            operator_id: 运营商ID
            request: 更新请求数据

        Returns:
            OperatorProfile: 更新后的运营商信息

        Raises:
            HTTPException 404: 运营商不存在
        """
        stmt = select(OperatorAccount).where(
            OperatorAccount.id == operator_id,
            OperatorAccount.deleted_at.is_(None)
        )
        result = await self.db.execute(stmt)
        operator = result.scalar_one_or_none()

        if not operator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "OPERATOR_NOT_FOUND",
                    "message": "运营商不存在"
                }
            )

        # 更新字段(仅更新提供的字段)
        if request.name is not None:
            operator.full_name = request.name
        if request.phone is not None:
            operator.phone = request.phone
        if request.email is not None:
            operator.email = request.email

        await self.db.commit()
        await self.db.refresh(operator)

        return OperatorProfile(
            operator_id=operator.id,
            username=operator.username,
            name=operator.full_name,
            phone=operator.phone,
            email=operator.email,
            category=operator.customer_tier,
            balance=str(operator.balance),
            is_active=operator.is_active,
            is_locked=operator.is_locked,
            last_login_at=operator.last_login_at,
            created_at=operator.created_at
        )

    async def deactivate_account(self, operator_id: UUID) -> None:
        """注销运营商账户(软删除)

        注销后:
        - 账户标记为已注销(is_active=false)
        - 设置deleted_at时间戳
        - 无法登录
        - 数据保留(合规要求)

        Args:
            operator_id: 运营商ID

        Raises:
            HTTPException 404: 运营商不存在
            HTTPException 400: 账户余额不为0
        """
        stmt = select(OperatorAccount).where(
            OperatorAccount.id == operator_id,
            OperatorAccount.deleted_at.is_(None)
        )
        result = await self.db.execute(stmt)
        operator = result.scalar_one_or_none()

        if not operator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "OPERATOR_NOT_FOUND",
                    "message": "运营商不存在"
                }
            )

        # 检查余额是否为0
        if operator.balance > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "BALANCE_NOT_ZERO",
                    "message": f"账户余额不为0(当前余额: {operator.balance}元),请先申请退款"
                }
            )

        # 软删除
        operator.is_active = False
        operator.deleted_at = datetime.now(timezone.utc)

        await self.db.commit()

    async def regenerate_api_key(self, operator_id: UUID) -> str:
        """重新生成API Key

        旧API Key立即失效,返回新API Key(明文,仅此一次)

        Args:
            operator_id: 运营商ID

        Returns:
            str: 新的64位API Key(明文)

        Raises:
            HTTPException 404: 运营商不存在
        """
        stmt = select(OperatorAccount).where(
            OperatorAccount.id == operator_id,
            OperatorAccount.deleted_at.is_(None)
        )
        result = await self.db.execute(stmt)
        operator = result.scalar_one_or_none()

        if not operator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "OPERATOR_NOT_FOUND",
                    "message": "运营商不存在"
                }
            )

        # 生成新API Key
        new_api_key = self._generate_api_key()
        new_api_key_hash = hash_password(new_api_key)

        # 更新数据库
        operator.api_key = new_api_key
        operator.api_key_hash = new_api_key_hash

        await self.db.commit()

        return new_api_key  # 返回明文,仅此一次

    async def get_transactions(
        self,
        operator_id: UUID,
        page: int = 1,
        page_size: int = 20,
        transaction_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> tuple[list, int]:
        """查询运营商交易记录(分页) (T073)

        Args:
            operator_id: 运营商ID
            page: 页码(从1开始)
            page_size: 每页数量
            transaction_type: 交易类型过滤 (recharge/consumption/all)
            start_time: 开始时间(可选)
            end_time: 结束时间(可选)

        Returns:
            tuple[list, int]: (交易记录列表, 总记录数)

        Raises:
            HTTPException 404: 运营商不存在
        """
        from ..models.transaction import TransactionRecord
        from sqlalchemy import func, desc

        # 1. 验证运营商存在
        operator_stmt = select(OperatorAccount).where(
            OperatorAccount.id == operator_id,
            OperatorAccount.deleted_at.is_(None)
        )
        operator_result = await self.db.execute(operator_stmt)
        operator = operator_result.scalar_one_or_none()

        if not operator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "OPERATOR_NOT_FOUND",
                    "message": "运营商不存在"
                }
            )

        # 2. 构建查询条件
        conditions = [
            TransactionRecord.operator_id == operator_id
        ]

        # 交易类型过滤
        if transaction_type and transaction_type != "all":
            conditions.append(TransactionRecord.transaction_type == transaction_type)

        # 时间范围过滤
        if start_time:
            conditions.append(TransactionRecord.created_at >= start_time)
        if end_time:
            conditions.append(TransactionRecord.created_at <= end_time)

        # 3. 查询总记录数
        count_stmt = select(func.count(TransactionRecord.id)).where(*conditions)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # 4. 分页查询交易记录
        offset = (page - 1) * page_size
        stmt = (
            select(TransactionRecord)
            .where(*conditions)
            .order_by(desc(TransactionRecord.created_at))  # 按时间降序
            .offset(offset)
            .limit(page_size)
        )

        result = await self.db.execute(stmt)
        transactions = result.scalars().all()

        return list(transactions), total
