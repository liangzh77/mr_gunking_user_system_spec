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

    async def get_refunds(
        self,
        operator_id: UUID,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list, int]:
        """查询运营商退款记录(分页) (T075)

        Args:
            operator_id: 运营商ID
            page: 页码(从1开始)
            page_size: 每页数量

        Returns:
            tuple[list, int]: (退款记录列表, 总记录数)

        Raises:
            HTTPException 404: 运营商不存在
        """
        from ..models.refund import RefundRecord
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
            RefundRecord.operator_id == operator_id
        ]

        # 3. 查询总记录数
        count_stmt = select(func.count(RefundRecord.id)).where(*conditions)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # 4. 分页查询退款记录
        offset = (page - 1) * page_size
        stmt = (
            select(RefundRecord)
            .where(*conditions)
            .order_by(desc(RefundRecord.created_at))  # 按时间降序
            .offset(offset)
            .limit(page_size)
        )

        result = await self.db.execute(stmt)
        refunds = result.scalars().all()

        return list(refunds), total

    async def apply_refund(
        self,
        operator_id: UUID,
        reason: str
    ):
        """申请退款 (T074)

        业务规则:
        - 只退当前余额,已消费金额不退
        - 余额为0时无法申请
        - 退款状态初始为pending
        - requested_amount为申请时的余额

        Args:
            operator_id: 运营商ID
            reason: 退款原因

        Returns:
            RefundRecord: 新创建的退款申请记录

        Raises:
            HTTPException 400: 余额为0无法申请退款
            HTTPException 404: 运营商不存在
        """
        from ..models.refund import RefundRecord

        # 1. 验证运营商存在并获取余额
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

        # 2. 检查余额是否大于0
        if operator.balance <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_PARAMS",
                    "message": "当前余额为0，无法申请退款"
                }
            )

        # 3. 创建退款申请记录
        refund = RefundRecord(
            operator_id=operator_id,
            requested_amount=operator.balance,  # 申请时的余额
            status="pending",  # 初始状态为待审核
            refund_reason=reason
        )

        self.db.add(refund)
        await self.db.commit()
        await self.db.refresh(refund)

        return refund

    async def apply_invoice(
        self,
        operator_id: UUID,
        amount: str,
        invoice_title: str,
        tax_id: str,
        email: Optional[str] = None
    ):
        """申请开具发票 (T076)

        业务规则:
        - 开票金额不能超过已充值金额(total_recharged)
        - 税号格式已由schema验证(15-20位字母数字)
        - 发票状态初始为pending(待财务审核)
        - email可选,默认使用账户邮箱

        Args:
            operator_id: 运营商ID
            amount: 开票金额(字符串格式)
            invoice_title: 发票抬头
            tax_id: 纳税人识别号
            email: 接收邮箱(可选)

        Returns:
            InvoiceRecord: 新创建的发票申请记录

        Raises:
            HTTPException 400: 开票金额超过已充值金额
            HTTPException 404: 运营商不存在
        """
        from ..models.invoice import InvoiceRecord
        from ..models.transaction import TransactionRecord
        from decimal import Decimal

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

        # 2. 计算已充值总额(sum所有recharge类型交易)
        from sqlalchemy import func
        recharge_sum_stmt = select(
            func.sum(TransactionRecord.amount)
        ).where(
            TransactionRecord.operator_id == operator_id,
            TransactionRecord.transaction_type == "recharge"
        )
        recharge_result = await self.db.execute(recharge_sum_stmt)
        total_recharged = recharge_result.scalar() or Decimal("0.00")

        # 3. 验证开票金额不超过已充值金额
        invoice_amount = Decimal(amount)
        if invoice_amount > total_recharged:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_PARAMS",
                    "message": f"开票金额({amount}元)不能超过已充值金额({total_recharged}元)"
                }
            )

        # 4. 设置email(如果未提供则使用账户邮箱)
        final_email = email if email else operator.email

        # 5. 创建发票申请记录
        invoice = InvoiceRecord(
            operator_id=operator_id,
            amount=invoice_amount,
            invoice_title=invoice_title,
            tax_id=tax_id.upper(),  # 统一为大写
            email=final_email,
            status="pending"  # 初始状态为待审核
        )

        self.db.add(invoice)
        await self.db.commit()
        await self.db.refresh(invoice)

        return invoice

    async def get_invoices(
        self,
        operator_id: UUID,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list, int]:
        """查询运营商发票记录(分页) (T077)

        Args:
            operator_id: 运营商ID
            page: 页码(从1开始)
            page_size: 每页数量

        Returns:
            tuple[list, int]: (发票记录列表, 总记录数)

        Raises:
            HTTPException 404: 运营商不存在
        """
        from ..models.invoice import InvoiceRecord
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
            InvoiceRecord.operator_id == operator_id
        ]

        # 3. 查询总记录数
        count_stmt = select(func.count(InvoiceRecord.id)).where(*conditions)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # 4. 分页查询发票记录
        offset = (page - 1) * page_size
        stmt = (
            select(InvoiceRecord)
            .where(*conditions)
            .order_by(desc(InvoiceRecord.created_at))  # 按时间降序
            .offset(offset)
            .limit(page_size)
        )

        result = await self.db.execute(stmt)
        invoices = result.scalars().all()

        return list(invoices), total

    async def get_usage_records(
        self,
        operator_id: UUID,
        page: int = 1,
        page_size: int = 20,
        site_id: Optional[str] = None,
        app_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> tuple[list, int]:
        """查询运营商使用记录(分页) (T102/T110)

        Args:
            operator_id: 运营商ID
            page: 页码(从1开始)
            page_size: 每页数量
            site_id: 运营点ID筛选(可选)
            app_id: 应用ID筛选(可选)
            start_time: 开始时间(可选)
            end_time: 结束时间(可选)

        Returns:
            tuple[list, int]: (使用记录列表, 总记录数)

        Raises:
            HTTPException 404: 运营商不存在
        """
        from ..models.usage_record import UsageRecord
        from ..models.site import OperationSite
        from ..models.application import Application
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
            UsageRecord.operator_id == operator_id
        ]

        # 按运营点筛选
        if site_id:
            # 解析site_id: 支持 "site_<uuid>" 格式或直接UUID字符串
            try:
                if site_id.startswith("site_"):
                    site_uuid = UUID(site_id[5:])  # 提取 "site_" 后的UUID部分
                else:
                    site_uuid = UUID(site_id)
                conditions.append(UsageRecord.site_id == site_uuid)
            except ValueError:
                # 无效的UUID格式,忽略此筛选条件(返回空结果)
                conditions.append(UsageRecord.site_id == UUID('00000000-0000-0000-0000-000000000000'))

        # 按应用筛选
        if app_id:
            # 解析app_id: 支持 "app_<uuid>" 格式或直接UUID字符串
            try:
                if app_id.startswith("app_"):
                    app_uuid = UUID(app_id[4:])  # 提取 "app_" 后的UUID部分
                else:
                    app_uuid = UUID(app_id)
                conditions.append(UsageRecord.application_id == app_uuid)
            except ValueError:
                # 无效的UUID格式,忽略此筛选条件(返回空结果)
                conditions.append(UsageRecord.application_id == UUID('00000000-0000-0000-0000-000000000000'))

        # 时间范围筛选
        if start_time:
            conditions.append(UsageRecord.game_started_at >= start_time)
        if end_time:
            conditions.append(UsageRecord.game_started_at <= end_time)

        # 3. 查询总记录数
        count_stmt = select(func.count(UsageRecord.id)).where(*conditions)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # 4. 分页查询使用记录(联表查询site和application)
        offset = (page - 1) * page_size
        stmt = (
            select(UsageRecord)
            .where(*conditions)
            .order_by(desc(UsageRecord.game_started_at))  # 按游戏启动时间降序
            .offset(offset)
            .limit(page_size)
        )

        result = await self.db.execute(stmt)
        usage_records = result.scalars().all()

        return list(usage_records), total

    async def create_site(
        self,
        operator_id: UUID,
        name: str,
        address: str,
        description: Optional[str] = None
    ):
        """创建运营点 (T090/T092)

        Args:
            operator_id: 运营商ID
            name: 运营点名称
            address: 详细地址
            description: 运营点描述(可选)

        Returns:
            OperationSite: 新创建的运营点对象

        Raises:
            HTTPException 404: 运营商不存在
        """
        from ..models.site import OperationSite

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

        # 2. 创建运营点
        site = OperationSite(
            operator_id=operator_id,
            name=name,
            address=address,
            description=description
        )

        self.db.add(site)
        await self.db.commit()
        await self.db.refresh(site)

        return site

    async def get_sites(
        self,
        operator_id: UUID,
        include_deleted: bool = False
    ) -> list:
        """获取运营商的运营点列表 (T093)

        Args:
            operator_id: 运营商ID
            include_deleted: 是否包含已删除的运营点(默认false)

        Returns:
            list[OperationSite]: 运营点列表(按创建时间降序)

        Raises:
            HTTPException 404: 运营商不存在
        """
        from ..models.site import OperationSite
        from sqlalchemy import desc

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
            OperationSite.operator_id == operator_id
        ]

        # 是否包含已删除的运营点
        if not include_deleted:
            conditions.append(OperationSite.deleted_at.is_(None))

        # 3. 查询运营点列表(按创建时间降序)
        stmt = (
            select(OperationSite)
            .where(*conditions)
            .order_by(desc(OperationSite.created_at))
        )

        result = await self.db.execute(stmt)
        sites = result.scalars().all()

        return list(sites)

    async def update_site(
        self,
        operator_id: UUID,
        site_id: UUID,
        name: Optional[str] = None,
        address: Optional[str] = None,
        description: Optional[str] = None
    ):
        """更新运营点信息 (T095)

        Args:
            operator_id: 运营商ID
            site_id: 运营点ID
            name: 运营点名称(可选)
            address: 详细地址(可选)
            description: 运营点描述(可选)

        Returns:
            OperationSite: 更新后的运营点对象

        Raises:
            HTTPException 404: 运营商或运营点不存在
        """
        from ..models.site import OperationSite

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

        # 2. 查询运营点(必须属于该运营商且未删除)
        site_stmt = select(OperationSite).where(
            OperationSite.id == site_id,
            OperationSite.operator_id == operator_id,
            OperationSite.deleted_at.is_(None)
        )
        site_result = await self.db.execute(site_stmt)
        site = site_result.scalar_one_or_none()

        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "SITE_NOT_FOUND",
                    "message": "运营点不存在或无权限访问"
                }
            )

        # 3. 更新字段(仅更新提供的字段)
        if name is not None:
            site.name = name
        if address is not None:
            site.address = address
        if description is not None:
            site.description = description

        await self.db.commit()
        await self.db.refresh(site)

        return site

    async def delete_site(
        self,
        operator_id: UUID,
        site_id: UUID
    ) -> None:
        """删除运营点(软删除) (T096)

        Args:
            operator_id: 运营商ID
            site_id: 运营点ID

        Raises:
            HTTPException 404: 运营商或运营点不存在
        """
        from ..models.site import OperationSite

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

        # 2. 查询运营点(必须属于该运营商且未删除)
        site_stmt = select(OperationSite).where(
            OperationSite.id == site_id,
            OperationSite.operator_id == operator_id,
            OperationSite.deleted_at.is_(None)
        )
        site_result = await self.db.execute(site_stmt)
        site = site_result.scalar_one_or_none()

        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "SITE_NOT_FOUND",
                    "message": "运营点不存在或无权限访问"
                }
            )

        # 3. 软删除(设置deleted_at时间戳)
        site.deleted_at = datetime.now(timezone.utc)

        await self.db.commit()

    async def get_statistics_by_site(
        self,
        operator_id: UUID,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> list[dict]:
        """按运营点统计使用情况 (T112)

        聚合每个运营点的:
        - 总场次 (total_sessions)
        - 总玩家人次 (total_players)
        - 总消费 (total_cost)

        Args:
            operator_id: 运营商ID
            start_time: 开始时间(可选)
            end_time: 结束时间(可选)

        Returns:
            list[dict]: 各运营点的统计数据列表

        Raises:
            HTTPException 404: 运营商不存在
        """
        from ..models.usage_record import UsageRecord
        from ..models.site import OperationSite
        from sqlalchemy import func

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
            UsageRecord.operator_id == operator_id
        ]

        # 时间范围筛选
        if start_time:
            conditions.append(UsageRecord.game_started_at >= start_time)
        if end_time:
            conditions.append(UsageRecord.game_started_at <= end_time)

        # 3. 聚合查询: 按运营点分组统计
        stmt = (
            select(
                OperationSite.id.label('site_id'),
                OperationSite.name.label('site_name'),
                func.count(UsageRecord.id).label('total_sessions'),
                func.sum(UsageRecord.player_count).label('total_players'),
                func.sum(UsageRecord.total_cost).label('total_cost')
            )
            .select_from(UsageRecord)
            .join(OperationSite, UsageRecord.site_id == OperationSite.id)
            .where(*conditions)
            .group_by(OperationSite.id, OperationSite.name)
            .order_by(func.sum(UsageRecord.total_cost).desc())  # 按总消费降序
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        # 4. 格式化返回数据
        statistics = []
        for row in rows:
            statistics.append({
                "site_id": f"site_{row.site_id}",
                "site_name": row.site_name,
                "total_sessions": row.total_sessions or 0,
                "total_players": int(row.total_players or 0),
                "total_cost": str(row.total_cost or "0.00")
            })

        return statistics

    async def get_statistics_by_app(
        self,
        operator_id: UUID,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> list[dict]:
        """按应用统计使用情况 (T113)

        聚合每个应用的:
        - 总场次 (total_sessions)
        - 总玩家人次 (total_players)
        - 平均每场玩家数 (avg_players_per_session)
        - 总消费 (total_cost)

        Args:
            operator_id: 运营商ID
            start_time: 开始时间(可选)
            end_time: 结束时间(可选)

        Returns:
            list[dict]: 各应用的统计数据列表

        Raises:
            HTTPException 404: 运营商不存在
        """
        from ..models.usage_record import UsageRecord
        from ..models.application import Application
        from sqlalchemy import func

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
            UsageRecord.operator_id == operator_id
        ]

        # 时间范围筛选
        if start_time:
            conditions.append(UsageRecord.game_started_at >= start_time)
        if end_time:
            conditions.append(UsageRecord.game_started_at <= end_time)

        # 3. 聚合查询: 按应用分组统计
        stmt = (
            select(
                Application.id.label('app_id'),
                Application.app_name.label('app_name'),
                func.count(UsageRecord.id).label('total_sessions'),
                func.sum(UsageRecord.player_count).label('total_players'),
                func.sum(UsageRecord.total_cost).label('total_cost')
            )
            .select_from(UsageRecord)
            .join(Application, UsageRecord.application_id == Application.id)
            .where(*conditions)
            .group_by(Application.id, Application.app_name)
            .order_by(func.sum(UsageRecord.total_cost).desc())  # 按总消费降序
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        # 4. 格式化返回数据(包含平均每场玩家数)
        statistics = []
        for row in rows:
            total_sessions = row.total_sessions or 0
            total_players = int(row.total_players or 0)

            # 计算平均每场玩家数
            avg_players_per_session = round(total_players / total_sessions, 1) if total_sessions > 0 else 0.0

            statistics.append({
                "app_id": f"app_{row.app_id}",
                "app_name": row.app_name,
                "total_sessions": total_sessions,
                "total_players": total_players,
                "avg_players_per_session": avg_players_per_session,
                "total_cost": str(row.total_cost or "0.00")
            })

        return statistics

    async def get_consumption_statistics(
        self,
        operator_id: UUID,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        dimension: str = "day"
    ) -> dict:
        """按时间统计消费趋势 (T114)

        按day/week/month维度聚合:
        - chart_data: 时间序列数据点列表
        - summary: 汇总统计(总场次、总玩家、总消费、平均每场玩家数)

        Args:
            operator_id: 运营商ID
            start_time: 开始时间(可选)
            end_time: 结束时间(可选)
            dimension: 时间维度 (day/week/month)

        Returns:
            dict: {
                "dimension": str,
                "chart_data": list[dict],
                "summary": dict
            }

        Raises:
            HTTPException 404: 运营商不存在
        """
        from ..models.usage_record import UsageRecord
        from sqlalchemy import func, cast, Date

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
            UsageRecord.operator_id == operator_id
        ]

        # 时间范围筛选
        if start_time:
            conditions.append(UsageRecord.game_started_at >= start_time)
        if end_time:
            conditions.append(UsageRecord.game_started_at <= end_time)

        # 3. 根据dimension确定分组方式
        # 使用数据库兼容的函数: strftime对SQLite和PostgreSQL都兼容
        if dimension == "day":
            # 按日分组: DATE(game_started_at)
            date_trunc = cast(UsageRecord.game_started_at, Date).label('date')
        elif dimension == "week":
            # 按周分组: 使用strftime('%Y-W%W', game_started_at)
            # SQLite: strftime('%Y-W%W', datetime)
            # PostgreSQL也支持类似用法,或使用DATE_TRUNC
            date_trunc = func.strftime('%Y-W%W', UsageRecord.game_started_at).label('date')
        elif dimension == "month":
            # 按月分组: 使用strftime('%Y-%m', game_started_at)
            date_trunc = func.strftime('%Y-%m', UsageRecord.game_started_at).label('date')
        else:
            # 默认按日
            date_trunc = cast(UsageRecord.game_started_at, Date).label('date')

        # 4. 聚合查询: 按时间分组统计
        stmt = (
            select(
                date_trunc,
                func.count(UsageRecord.id).label('total_sessions'),
                func.sum(UsageRecord.player_count).label('total_players'),
                func.sum(UsageRecord.total_cost).label('total_cost')
            )
            .where(*conditions)
            .group_by(date_trunc)
            .order_by(date_trunc)  # 按时间升序
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        # 5. 格式化图表数据
        chart_data = []
        total_sessions_sum = 0
        total_players_sum = 0
        total_cost_sum = 0

        for row in rows:
            total_sessions = row.total_sessions or 0
            total_players = int(row.total_players or 0)
            total_cost = row.total_cost or 0

            # 累加汇总数据
            total_sessions_sum += total_sessions
            total_players_sum += total_players
            total_cost_sum += total_cost

            # 格式化日期为字符串
            if isinstance(row.date, str):
                # week/month分组时已经是字符串格式
                date_str = row.date
            elif isinstance(row.date, datetime):
                date_str = row.date.date().isoformat()
            else:
                date_str = row.date.isoformat()

            chart_data.append({
                "date": date_str,
                "total_sessions": total_sessions,
                "total_players": total_players,
                "total_cost": f"{float(total_cost):.2f}"  # 确保格式为"0.00"
            })

        # 6. 计算汇总数据
        avg_players_per_session = round(total_players_sum / total_sessions_sum, 1) if total_sessions_sum > 0 else 0.0

        summary = {
            "total_sessions": total_sessions_sum,
            "total_players": total_players_sum,
            "total_cost": f"{float(total_cost_sum):.2f}",  # 确保格式为"0.00"
            "avg_players_per_session": avg_players_per_session
        }

        return {
            "dimension": dimension,
            "chart_data": chart_data,
            "summary": summary
        }

    async def create_recharge_order(
        self,
        operator_id: UUID,
        amount: str,
        payment_method: str
    ):
        """创建充值订单 (T071)

        业务规则:
        - 充值金额已由schema验证(10-10000元,最多2位小数)
        - 生成唯一订单ID: ord_recharge_<timestamp>_<uuid>
        - 订单有效期: 30分钟
        - 返回支付二维码URL和支付页面URL(模拟)
        - 订单状态初始为pending

        Args:
            operator_id: 运营商ID
            amount: 充值金额(字符串格式)
            payment_method: 支付方式 (wechat/alipay)

        Returns:
            充值订单对象 (包含order_id, qr_code_url, expires_at等)

        Raises:
            HTTPException 404: 运营商不存在
        """
        from ..models.transaction import RechargeOrder
        from decimal import Decimal

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

        # 2. 生成订单ID: ord_recharge_<timestamp>_<short_uuid>
        import time
        from uuid import uuid4
        timestamp = int(time.time())
        short_uuid = str(uuid4())[:8]  # 取前8位UUID
        order_id = f"ord_recharge_{timestamp}_{short_uuid}"

        # 3. 计算订单过期时间(30分钟后)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

        # 4. 生成支付二维码URL和支付页面URL(模拟)
        # 实际环境中应调用支付平台API生成真实二维码
        qr_code_url = f"https://payment.example.com/qr/{order_id}"
        payment_url = f"https://payment.example.com/pay/{order_id}"

        # 5. 创建充值订单记录
        recharge_order = RechargeOrder(
            order_id=order_id,
            operator_id=operator_id,
            amount=Decimal(amount),
            payment_method=payment_method,
            qr_code_url=qr_code_url,
            payment_url=payment_url,
            status="pending",
            expires_at=expires_at
        )

        self.db.add(recharge_order)
        await self.db.commit()
        await self.db.refresh(recharge_order)

        return recharge_order

    async def get_authorized_applications(
        self,
        operator_id: UUID
    ) -> list:
        """查询运营商已授权的应用列表 (T097)

        返回运营商当前有权使用的应用列表,包括应用详情和授权信息。

        业务规则:
        - 只返回is_active=true的授权
        - 排除已过期的授权(expires_at < now)
        - 联表查询Application获取应用详情

        Args:
            operator_id: 运营商ID

        Returns:
            list[dict]: 已授权应用列表,包含应用信息和授权元数据

        Raises:
            HTTPException 404: 运营商不存在
        """
        from ..models.authorization import OperatorAppAuthorization
        from ..models.application import Application

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
            OperatorAppAuthorization.operator_id == operator_id,
            OperatorAppAuthorization.is_active == True
        ]

        # 排除已过期的授权
        current_time = datetime.now(timezone.utc)
        from sqlalchemy import or_
        conditions.append(
            or_(
                OperatorAppAuthorization.expires_at.is_(None),  # 永久授权
                OperatorAppAuthorization.expires_at > current_time  # 未过期
            )
        )

        # 3. 联表查询授权和应用信息
        stmt = (
            select(OperatorAppAuthorization, Application)
            .join(Application, OperatorAppAuthorization.application_id == Application.id)
            .where(*conditions)
            .order_by(OperatorAppAuthorization.authorized_at.desc())  # 按授权时间降序
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        # 4. 格式化返回数据
        applications = []
        for auth, app in rows:
            applications.append({
                "app_id": f"app_{app.id}",
                "app_code": app.app_code,
                "app_name": app.app_name,
                "description": app.description,
                "price_per_player": str(app.price_per_player),
                "min_players": app.min_players,
                "max_players": app.max_players,
                "authorized_at": auth.authorized_at.isoformat(),
                "expires_at": auth.expires_at.isoformat() if auth.expires_at else None,
                "is_active": auth.is_active
            })

        return applications

    async def create_application_request(
        self,
        operator_id: UUID,
        application_id: UUID,
        reason: str
    ):
        """申请应用授权 (T098)

        运营商申请使用某个应用的授权,需要管理员审批。

        业务规则:
        - 不能重复申请(同一应用只能有一条pending申请)
        - 不能申请已授权的应用
        - 应用必须存在且is_active=true

        Args:
            operator_id: 运营商ID
            application_id: 要申请的应用ID
            reason: 申请理由

        Returns:
            ApplicationRequest: 新创建的授权申请记录

        Raises:
            HTTPException 400: 不能重复申请或已授权
            HTTPException 404: 运营商或应用不存在
        """
        from ..models.app_request import ApplicationRequest
        from ..models.application import Application
        from ..models.authorization import OperatorAppAuthorization

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

        # 2. 验证应用存在且活跃
        app_stmt = select(Application).where(
            Application.id == application_id
        )
        app_result = await self.db.execute(app_stmt)
        application = app_result.scalar_one_or_none()

        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "APPLICATION_NOT_FOUND",
                    "message": "应用不存在"
                }
            )

        if not application.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "APPLICATION_INACTIVE",
                    "message": "该应用已下架,无法申请授权"
                }
            )

        # 3. 检查是否已有活跃授权
        auth_stmt = select(OperatorAppAuthorization).where(
            OperatorAppAuthorization.operator_id == operator_id,
            OperatorAppAuthorization.application_id == application_id,
            OperatorAppAuthorization.is_active == True
        )
        auth_result = await self.db.execute(auth_stmt)
        existing_auth = auth_result.scalar_one_or_none()

        if existing_auth:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "ALREADY_AUTHORIZED",
                    "message": "您已拥有该应用的授权,无需重复申请"
                }
            )

        # 4. 检查是否已有待审核的申请
        request_stmt = select(ApplicationRequest).where(
            ApplicationRequest.operator_id == operator_id,
            ApplicationRequest.application_id == application_id,
            ApplicationRequest.status == "pending"
        )
        request_result = await self.db.execute(request_stmt)
        existing_request = request_result.scalar_one_or_none()

        if existing_request:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "REQUEST_ALREADY_EXISTS",
                    "message": "该应用已有待审核的申请,请勿重复提交"
                }
            )

        # 5. 创建授权申请记录
        app_request = ApplicationRequest(
            operator_id=operator_id,
            application_id=application_id,
            request_reason=reason,
            status="pending"
        )

        self.db.add(app_request)
        await self.db.commit()
        await self.db.refresh(app_request)

        return app_request

    async def get_application_requests(
        self,
        operator_id: UUID,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list, int]:
        """查询运营商的授权申请列表 (T099)

        返回运营商所有的应用授权申请记录,包括pending/approved/rejected状态。

        Args:
            operator_id: 运营商ID
            page: 页码(从1开始)
            page_size: 每页数量

        Returns:
            tuple[list, int]: (申请记录列表, 总记录数)

        Raises:
            HTTPException 404: 运营商不存在
        """
        from ..models.app_request import ApplicationRequest
        from ..models.application import Application
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
            ApplicationRequest.operator_id == operator_id
        ]

        # 3. 查询总记录数
        count_stmt = select(func.count(ApplicationRequest.id)).where(*conditions)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # 4. 分页查询申请记录(联表查询application)
        offset = (page - 1) * page_size
        stmt = (
            select(ApplicationRequest)
            .where(*conditions)
            .order_by(desc(ApplicationRequest.created_at))  # 按创建时间降序
            .offset(offset)
            .limit(page_size)
        )

        result = await self.db.execute(stmt)
        requests = result.scalars().all()

        return list(requests), total

    async def get_usage_record(
        self,
        operator_id: UUID,
        record_id: UUID
    ):
        """获取单条使用记录详情 (T111)

        返回指定ID的使用记录详细信息,包括关联的运营点和应用信息。

        Args:
            operator_id: 运营商ID
            record_id: 使用记录ID

        Returns:
            UsageRecord: 使用记录对象(含关联的site和application)

        Raises:
            HTTPException 404: 运营商或使用记录不存在
            HTTPException 403: 无权访问该记录
        """
        from ..models.usage_record import UsageRecord
        from ..models.site import OperationSite
        from ..models.application import Application

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

        # 2. 查询使用记录(必须属于该运营商)
        stmt = select(UsageRecord).where(
            UsageRecord.id == record_id,
            UsageRecord.operator_id == operator_id
        )
        result = await self.db.execute(stmt)
        usage_record = result.scalar_one_or_none()

        if not usage_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "USAGE_RECORD_NOT_FOUND",
                    "message": "使用记录不存在或无权访问"
                }
            )

        return usage_record

    async def get_player_distribution_statistics(
        self,
        operator_id: UUID,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> dict:
        """玩家数量分布统计 (T115)

        统计不同玩家数量的游戏场次分布,用于分析运营商最常见的游戏规模。

        返回数据:
        - distribution: 各玩家数量的场次、占比、总消费
        - total_sessions: 总场次
        - most_common_player_count: 最常见的玩家数

        Args:
            operator_id: 运营商ID
            start_time: 开始时间(可选)
            end_time: 结束时间(可选)

        Returns:
            dict: {
                "distribution": list[dict],
                "total_sessions": int,
                "most_common_player_count": int
            }

        Raises:
            HTTPException 404: 运营商不存在
        """
        from ..models.usage_record import UsageRecord
        from sqlalchemy import func

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
            UsageRecord.operator_id == operator_id
        ]

        # 时间范围筛选
        if start_time:
            conditions.append(UsageRecord.game_started_at >= start_time)
        if end_time:
            conditions.append(UsageRecord.game_started_at <= end_time)

        # 3. 聚合查询: 按玩家数量分组统计
        stmt = (
            select(
                UsageRecord.player_count,
                func.count(UsageRecord.id).label('session_count'),
                func.sum(UsageRecord.total_cost).label('total_cost')
            )
            .where(*conditions)
            .group_by(UsageRecord.player_count)
            .order_by(UsageRecord.player_count)  # 按玩家数升序
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        # 4. 计算总场次
        total_sessions = sum(row.session_count for row in rows)

        # 5. 格式化返回数据
        distribution = []
        most_common_count = 0
        max_sessions = 0

        for row in rows:
            session_count = row.session_count or 0
            total_cost = row.total_cost or 0

            # 计算占比
            percentage = round((session_count / total_sessions * 100), 1) if total_sessions > 0 else 0.0

            # 找出最常见的玩家数
            if session_count > max_sessions:
                max_sessions = session_count
                most_common_count = row.player_count

            distribution.append({
                "player_count": row.player_count,
                "session_count": session_count,
                "percentage": percentage,
                "total_cost": f"{float(total_cost):.2f}"
            })

        return {
            "distribution": distribution,
            "total_sessions": total_sessions,
            "most_common_player_count": most_common_count if total_sessions > 0 else 0
        }
