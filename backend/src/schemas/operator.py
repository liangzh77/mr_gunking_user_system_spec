"""
运营商相关的Pydantic Schemas

包含:
- 运营商注册请求/响应
- 运营商个人信息
- 运营商列表
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Union
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, field_serializer, model_validator
import re


# ========== 注册相关 Schema ==========

class OperatorRegisterRequest(BaseModel):
    """运营商注册请求 (T057)

    契约定义: auth.yaml /auth/operators/register

    字段要求:
    - username: 3-20字符,仅字母数字下划线
    - password: 8-32字符,需包含大小写字母和数字
    - name: 2-50字符,真实姓名或公司名
    - phone: 11位中国手机号
    - email: 标准邮箱格式
    """
    username: str = Field(
        ...,
        min_length=3,
        max_length=20,
        description="用户名(唯一,3-20字符,字母数字下划线)",
        examples=["operator_beijing_01"]
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=32,
        description="密码(8-32字符,需包含大小写字母和数字)",
        examples=["StrongPass123"]
    )

    name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="真实姓名或公司名",
        examples=["北京星空娱乐有限公司"]
    )

    phone: str = Field(
        ...,
        min_length=11,
        max_length=11,
        description="联系电话",
        examples=["13800138000"]
    )

    email: EmailStr = Field(
        ...,
        description="邮箱地址",
        examples=["operator@example.com"]
    )

    @field_validator("username")
    @classmethod
    def validate_username_format(cls, v: str) -> str:
        """验证用户名格式:仅包含字母、数字、下划线"""
        if not re.match(r"^[a-zA-Z0-9_]{3,20}$", v):
            raise ValueError("用户名必须是3-20个字符,仅包含字母、数字、下划线")
        return v

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """验证密码强度:必须包含大小写字母和数字"""
        if not re.search(r"[A-Z]", v):
            raise ValueError("密码必须包含大小写字母和数字,长度8-32字符")
        if not re.search(r"[a-z]", v):
            raise ValueError("密码必须包含大小写字母和数字,长度8-32字符")
        if not re.search(r"\d", v):
            raise ValueError("密码必须包含大小写字母和数字,长度8-32字符")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone_format(cls, v: str) -> str:
        """验证手机号格式:11位中国手机号"""
        if not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式错误,请输入11位有效的中国手机号")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "operator_beijing_01",
                    "password": "StrongPass123",
                    "name": "北京星空娱乐有限公司",
                    "phone": "13800138000",
                    "email": "operator@example.com"
                }
            ]
        }
    }


class OperatorRegisterData(BaseModel):
    """运营商注册响应数据部分 (T057)

    返回新创建的运营商基本信息和API Key
    注意:API Key仅在注册时返回一次,请妥善保存
    """
    operator_id: str = Field(
        ...,
        description="运营商ID",
        examples=["op_12345"]
    )

    username: str = Field(
        ...,
        description="用户名",
        examples=["operator_beijing_01"]
    )

    api_key: str = Field(
        ...,
        description="API Key(请妥善保存,仅显示一次)",
        examples=["a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2"]
    )

    category: str = Field(
        ...,
        description="客户分类",
        examples=["trial"]
    )

    balance: str = Field(
        ...,
        description="初始余额",
        examples=["0.00"]
    )

    created_at: datetime = Field(
        ...,
        description="创建时间",
        examples=["2025-01-01T10:00:00.000Z"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "operator_id": "op_12345",
                    "username": "operator_beijing_01",
                    "api_key": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2",
                    "category": "trial",
                    "balance": "0.00",
                    "created_at": "2025-01-01T10:00:00.000Z"
                }
            ]
        }
    }


class OperatorRegisterResponse(BaseModel):
    """运营商注册响应包装 (T057)

    标准响应格式:
    {
        "success": true,
        "message": "注册成功",
        "data": {...}
    }
    """
    success: bool = Field(
        default=True,
        description="请求是否成功"
    )

    message: str = Field(
        default="注册成功",
        description="响应消息"
    )

    data: OperatorRegisterData = Field(
        ...,
        description="注册数据"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "message": "注册成功",
                    "data": {
                        "operator_id": "op_12345",
                        "username": "operator_beijing_01",
                        "api_key": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2",
                        "category": "trial",
                        "balance": "0.00",
                        "created_at": "2025-01-01T10:00:00.000Z"
                    }
                }
            ]
        }
    }


# ========== 个人信息相关 Schema ==========

class OperatorProfile(BaseModel):
    """运营商个人信息 (T057)

    用于返回运营商详细信息(不包含敏感信息如密码、API Key)
    """
    operator_id: UUID = Field(
        ...,
        description="运营商ID"
    )

    username: str = Field(
        ...,
        description="用户名"
    )

    name: str = Field(
        ...,
        description="真实姓名或公司名"
    )

    phone: str = Field(
        ...,
        description="联系电话"
    )

    email: str = Field(
        ...,
        description="邮箱地址"
    )

    category: str = Field(
        ...,
        description="客户分类: trial/standard/vip"
    )

    balance: str = Field(
        ...,
        description="账户余额(元)"
    )

    is_active: bool = Field(
        ...,
        description="账户状态:true=正常,false=已注销"
    )

    is_locked: bool = Field(
        ...,
        description="账户锁定状态"
    )

    last_login_at: Optional[datetime] = Field(
        None,
        description="最近登录时间"
    )

    created_at: datetime = Field(
        ...,
        description="创建时间"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "operator_id": "550e8400-e29b-41d4-a716-446655440000",
                    "username": "operator_beijing_01",
                    "name": "北京星空娱乐有限公司",
                    "phone": "13800138000",
                    "email": "operator@example.com",
                    "category": "normal",
                    "balance": "1000.00",
                    "is_active": True,
                    "is_locked": False,
                    "last_login_at": "2025-01-15T10:00:00.000Z",
                    "created_at": "2025-01-01T10:00:00.000Z"
                }
            ]
        }
    }


class OperatorUpdateRequest(BaseModel):
    """运营商信息更新请求

    允许运营商更新部分个人信息
    所有字段都是可选的
    """
    name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=50,
        description="真实姓名或公司名"
    )

    phone: Optional[str] = Field(
        None,
        min_length=11,
        max_length=11,
        description="联系电话"
    )

    email: Optional[EmailStr] = Field(
        None,
        description="邮箱地址"
    )

    @field_validator("phone")
    @classmethod
    def validate_phone_format(cls, v: Optional[str]) -> Optional[str]:
        """验证手机号格式"""
        if v is not None and not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式错误")
        return v


# ========== 列表相关 Schema ==========

class OperatorListItem(BaseModel):
    """运营商列表项(简化信息)

    用于管理员查看运营商列表
    """
    operator_id: UUID
    username: str
    name: str = Field(..., alias="full_name")
    category: str = Field(..., alias="customer_tier")
    balance: str
    is_active: bool
    is_locked: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }


class OperatorListResponse(BaseModel):
    """运营商列表响应(分页)"""
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    total: int = Field(..., description="总记录数")
    items: list[OperatorListItem] = Field(..., description="运营商列表")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "page": 1,
                    "page_size": 20,
                    "total": 50,
                    "items": [
                        {
                            "operator_id": "550e8400-e29b-41d4-a716-446655440000",
                            "username": "operator_beijing_01",
                            "name": "北京星空娱乐有限公司",
                            "category": "normal",
                            "balance": "1000.00",
                            "is_active": True,
                            "is_locked": False,
                            "created_at": "2025-01-01T10:00:00.000Z",
                            "last_login_at": "2025-01-15T10:00:00.000Z"
                        }
                    ]
                }
            ]
        }
    }


# ========== 余额相关 Schema (T072) ==========

class BalanceResponse(BaseModel):
    """运营商余额查询响应 (T072)

    返回运营商当前余额和客户分类信息
    """
    balance: str = Field(
        ...,
        description="账户余额(元,字符串格式)"
    )

    category: str = Field(
        ...,
        description="客户分类: trial/normal/vip"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "balance": "1250.50",
                    "category": "normal"
                }
            ]
        }
    }


# ========== 交易记录相关 Schema (T073) ==========

class TransactionItem(BaseModel):
    """交易记录项 (T073)

    单条交易记录的详细信息
    """
    transaction_id: str = Field(
        ...,
        description="交易ID"
    )

    type: str = Field(
        ...,
        description="交易类型: recharge/consumption"
    )

    amount: str = Field(
        ...,
        description="交易金额(字符串格式)"
    )

    balance_after: str = Field(
        ...,
        description="交易后余额"
    )

    created_at: datetime = Field(
        ...,
        description="交易时间"
    )

    related_usage_id: Optional[str] = Field(
        None,
        description="关联使用记录ID(消费类型)"
    )

    payment_method: Optional[str] = Field(
        None,
        description="支付方式(充值类型): wechat/alipay"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "transaction_id": "txn_20250115_123456",
                    "type": "consumption",
                    "amount": "50.00",
                    "balance_after": "450.00",
                    "created_at": "2025-01-15T12:30:00.000Z",
                    "related_usage_id": "usage_20250115_001",
                    "payment_method": None
                }
            ]
        }
    }


class TransactionListResponse(BaseModel):
    """交易记录列表响应(分页) (T073)

    返回分页的交易记录列表
    """
    page: int = Field(..., description="当前页码", ge=1)
    page_size: int = Field(..., description="每页数量", ge=1, le=100)
    total: int = Field(..., description="总记录数", ge=0)
    items: list[TransactionItem] = Field(..., description="交易记录列表")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "page": 1,
                    "page_size": 20,
                    "total": 2,
                    "items": [
                        {
                            "transaction_id": "txn_20250115_123456",
                            "type": "consumption",
                            "amount": "50.00",
                            "balance_after": "450.00",
                            "created_at": "2025-01-15T12:30:00.000Z",
                            "related_usage_id": "usage_20250115_001",
                            "payment_method": None
                        },
                        {
                            "transaction_id": "txn_20250110_789012",
                            "type": "recharge",
                            "amount": "500.00",
                            "balance_after": "500.00",
                            "created_at": "2025-01-10T10:00:00.000Z",
                            "related_usage_id": None,
                            "payment_method": "wechat"
                        }
                    ]
                }
            ]
        }
    }


# ========== 退款记录相关 Schema (T075) ==========

class RefundItem(BaseModel):
    """退款记录项 (T075)

    单条退款申请记录的详细信息
    """
    refund_id: str = Field(
        ...,
        description="退款ID"
    )

    requested_amount: str = Field(
        ...,
        description="申请退款金额(申请时的余额,字符串格式)"
    )

    actual_refund_amount: Optional[str] = Field(
        None,
        description="实际退款金额(审核时的余额)"
    )

    status: str = Field(
        ...,
        description="审核状态: pending/approved/rejected"
    )

    reason: str = Field(
        ...,
        description="退款原因"
    )

    reject_reason: Optional[str] = Field(
        None,
        description="拒绝原因(status=rejected时)"
    )

    reviewed_by: Optional[str] = Field(
        None,
        description="审核人ID"
    )

    reviewed_at: Optional[datetime] = Field(
        None,
        description="审核时间"
    )

    created_at: datetime = Field(
        ...,
        description="申请时间"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "refund_id": "refund_20250115_001",
                    "requested_amount": "100.00",
                    "actual_refund_amount": "80.00",
                    "status": "approved",
                    "reason": "业务调整，不再继续使用",
                    "reject_reason": None,
                    "reviewed_by": "fin_001",
                    "reviewed_at": "2025-01-16T10:00:00.000Z",
                    "created_at": "2025-01-15T15:00:00.000Z"
                }
            ]
        }
    }


class RefundListResponse(BaseModel):
    """退款记录列表响应(分页) (T075)

    返回分页的退款申请记录列表
    """
    page: int = Field(..., description="当前页码", ge=1)
    page_size: int = Field(..., description="每页数量", ge=1, le=100)
    total: int = Field(..., description="总记录数", ge=0)
    items: list[RefundItem] = Field(..., description="退款记录列表")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "page": 1,
                    "page_size": 20,
                    "total": 2,
                    "items": [
                        {
                            "refund_id": "refund_20250115_001",
                            "requested_amount": "100.00",
                            "actual_refund_amount": "80.00",
                            "status": "approved",
                            "reason": "业务调整，不再继续使用",
                            "reject_reason": None,
                            "reviewed_by": "fin_001",
                            "reviewed_at": "2025-01-16T10:00:00.000Z",
                            "created_at": "2025-01-15T15:00:00.000Z"
                        },
                        {
                            "refund_id": "refund_20250110_002",
                            "requested_amount": "200.00",
                            "actual_refund_amount": None,
                            "status": "pending",
                            "reason": "测试退款申请",
                            "reject_reason": None,
                            "reviewed_by": None,
                            "reviewed_at": None,
                            "created_at": "2025-01-10T14:00:00.000Z"
                        }
                    ]
                }
            ]
        }
    }


# ========== 使用记录相关 Schema (T102/T110) ==========

class UsageItem(BaseModel):
    """使用记录项 (T102)

    单条游戏使用记录的详细信息
    """
    usage_id: str = Field(
        ...,
        description="使用记录ID"
    )

    session_id: str = Field(
        ...,
        description="会话ID(幂等性标识)"
    )

    site_id: str = Field(
        ...,
        description="运营点ID"
    )

    site_name: str = Field(
        ...,
        description="运营点名称"
    )

    app_id: str = Field(
        ...,
        description="应用ID"
    )

    app_name: str = Field(
        ...,
        description="应用名称"
    )

    player_count: int = Field(
        ...,
        description="玩家数量"
    )

    unit_price: str = Field(
        ...,
        description="单人价格(历史快照,字符串格式)"
    )

    total_cost: str = Field(
        ...,
        description="总费用(字符串格式)"
    )

    game_duration: Optional[int] = Field(
        None,
        description="游戏时长(秒,可选)"
    )

    created_at: datetime = Field(
        ...,
        description="授权时间(游戏启动时间)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "usage_id": "usage_20250115_001",
                    "session_id": "op_12345_1704067200_a1b2c3d4e5f6g7h8",
                    "site_id": "site_beijing_001",
                    "site_name": "北京朝阳门店",
                    "app_id": "app_space_adventure_001",
                    "app_name": "太空探险",
                    "player_count": 5,
                    "unit_price": "10.00",
                    "total_cost": "50.00",
                    "game_duration": 1800,
                    "created_at": "2025-01-15T12:30:00.000Z"
                }
            ]
        }
    }


class UsageListResponse(BaseModel):
    """使用记录列表响应(分页) (T102)

    返回分页的使用记录列表
    """
    page: int = Field(..., description="当前页码", ge=1)
    page_size: int = Field(..., description="每页数量", ge=1, le=100)
    total: int = Field(..., description="总记录数", ge=0)
    items: list[UsageItem] = Field(..., description="使用记录列表")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "page": 1,
                    "page_size": 20,
                    "total": 2,
                    "items": [
                        {
                            "usage_id": "usage_20250115_001",
                            "session_id": "op_12345_1704067200_a1b2c3d4e5f6g7h8",
                            "site_id": "site_beijing_001",
                            "site_name": "北京朝阳门店",
                            "app_id": "app_space_adventure_001",
                            "app_name": "太空探险",
                            "player_count": 5,
                            "unit_price": "10.00",
                            "total_cost": "50.00",
                            "game_duration": 1800,
                            "created_at": "2025-01-15T12:30:00.000Z"
                        },
                        {
                            "usage_id": "usage_20250114_002",
                            "session_id": "op_12345_1703980800_b2c3d4e5f6g7h8i9",
                            "site_id": "site_shanghai_001",
                            "site_name": "上海浦东门店",
                            "app_id": "app_star_war_001",
                            "app_name": "星际战争",
                            "player_count": 8,
                            "unit_price": "12.00",
                            "total_cost": "96.00",
                            "game_duration": 2400,
                            "created_at": "2025-01-14T15:20:00.000Z"
                        }
                    ]
                }
            ]
        }
    }
