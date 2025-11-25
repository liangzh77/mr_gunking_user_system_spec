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

    sms_key: str = Field(
        ...,
        min_length=1,
        description="短信验证码key(从发送短信接口获取)",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )

    sms_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="短信验证码(6位数字)",
        examples=["123456"]
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

    transaction_type: str = Field(
        ...,
        description="交易类型: recharge/consumption/refund"
    )

    amount: str = Field(
        ...,
        description="交易金额(字符串格式，充值和退款为正，消费为负)"
    )

    balance_before: str = Field(
        ...,
        description="交易前余额"
    )

    balance_after: str = Field(
        ...,
        description="交易后余额"
    )

    description: Optional[str] = Field(
        None,
        description="交易描述"
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
                    "transaction_type": "consumption",
                    "amount": "-50.00",
                    "balance_before": "500.00",
                    "balance_after": "450.00",
                    "description": "游戏消费：测试游戏 - 2人",
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


class RefundApplyRequest(BaseModel):
    """退款申请请求 (T074)

    契约定义: operator.yaml POST /operators/me/refunds

    字段要求:
    - amount: 可选，退款金额，不提供则退还全部余额
    - reason: 1-500字符,退款原因说明
    """
    amount: Optional[Decimal] = Field(
        None,
        gt=0,
        description="退款金额（可选，不提供则退还全部余额）",
        examples=[100.00]
    )

    reason: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="退款原因",
        examples=["业务调整，不再继续使用服务"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "reason": "业务调整，不再继续使用服务"
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


# ========== 使用记录详情相关 Schema ==========

class HeadsetDeviceDetail(BaseModel):
    """头显设备详情"""

    device_id: str = Field(..., description="设备ID")
    device_name: Optional[str] = Field(None, description="设备名称")
    start_time: Optional[datetime] = Field(None, description="设备开始时间")
    end_time: Optional[datetime] = Field(None, description="设备结束时间")
    process_info: Optional[str] = Field(None, description="设备过程信息")


class GameSessionDetail(BaseModel):
    """游戏局详情"""

    session_number: int = Field(..., description="局号(第几局)")
    start_time: Optional[datetime] = Field(None, description="游戏开始时间")
    end_time: Optional[datetime] = Field(None, description="游戏结束时间")
    process_info: Optional[str] = Field(None, description="游戏过程信息(YAML/JSON格式)")
    headset_devices: list[HeadsetDeviceDetail] = Field(default_factory=list, description="头显设备列表")


class UsageDetail(UsageItem):
    """使用记录详细信息(扩展UsageItem)"""

    game_sessions: list[GameSessionDetail] = Field(
        default_factory=list,
        description="游戏局列表"
    )


# ========== 运营点管理相关 Schema (T087/T092-T096) ==========

class SiteCreateRequest(BaseModel):
    """创建运营点请求 (T087/T092)

    契约定义: operator.yaml POST /operators/me/sites

    字段要求:
    - name: 2-50字符,运营点名称
    - address: 5-200字符,详细地址
    - description: 0-500字符,可选描述
    """
    name: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="运营点名称",
        examples=["北京朝阳门店"]
    )

    address: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description="详细地址",
        examples=["北京市朝阳区建国路88号"]
    )

    description: Optional[str] = Field(
        None,
        max_length=500,
        description="运营点描述(可选)",
        examples=["朝阳区旗舰店，面积300平米"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "北京朝阳门店",
                    "address": "北京市朝阳区建国路88号",
                    "description": "朝阳区旗舰店，面积300平米"
                }
            ]
        }
    }


class SiteUpdateRequest(BaseModel):
    """更新运营点请求 (T087/T094)

    契约定义: operator.yaml PUT /operators/me/sites/{site_id}

    所有字段都是可选的,只更新提供的字段
    """
    name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=50,
        description="运营点名称"
    )

    address: Optional[str] = Field(
        None,
        min_length=5,
        max_length=200,
        description="详细地址"
    )

    description: Optional[str] = Field(
        None,
        max_length=500,
        description="运营点描述"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "北京朝阳旗舰店",
                    "address": "北京市朝阳区建国路88号",
                    "description": "朝阳区旗舰店，面积300平米，设备已升级"
                }
            ]
        }
    }


class SiteResponse(BaseModel):
    """运营点响应对象 (T087)

    契约定义: operator.yaml OperationSite schema

    返回运营点完整信息
    """
    site_id: str = Field(
        ...,
        description="运营点ID(格式: site_<uuid>)"
    )

    name: str = Field(
        ...,
        description="运营点名称"
    )

    address: str = Field(
        ...,
        description="详细地址"
    )

    description: Optional[str] = Field(
        None,
        description="运营点描述"
    )

    is_deleted: bool = Field(
        ...,
        description="是否已删除(逻辑删除标记)"
    )

    created_at: datetime = Field(
        ...,
        description="创建时间"
    )

    updated_at: datetime = Field(
        ...,
        description="更新时间"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "site_id": "site_beijing_001",
                    "name": "北京朝阳门店",
                    "address": "北京市朝阳区建国路88号",
                    "description": "朝阳区旗舰店，面积300平米",
                    "is_deleted": False,
                    "created_at": "2025-01-01T10:00:00.000Z",
                    "updated_at": "2025-01-15T14:30:00.000Z"
                }
            ]
        }
    }


class SiteListResponse(BaseModel):
    """运营点列表响应 (T093)

    契约定义: operator.yaml GET /operators/me/sites

    返回运营商所有运营点(非分页)
    """
    sites: list[SiteResponse] = Field(
        ...,
        description="运营点列表"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "sites": [
                        {
                            "site_id": "site_beijing_001",
                            "name": "北京朝阳门店",
                            "address": "北京市朝阳区建国路88号",
                            "description": "朝阳区旗舰店，面积300平米",
                            "is_deleted": False,
                            "created_at": "2025-01-01T10:00:00.000Z",
                            "updated_at": "2025-01-15T14:30:00.000Z"
                        },
                        {
                            "site_id": "site_shanghai_001",
                            "name": "上海浦东门店",
                            "address": "上海市浦东新区世纪大道100号",
                            "description": None,
                            "is_deleted": False,
                            "created_at": "2025-01-05T09:00:00.000Z",
                            "updated_at": "2025-01-05T09:00:00.000Z"
                        }
                    ]
                }
            ]
        }
    }


# ========== 应用授权相关 Schema (T088-T089/T097-T099) ==========

class AuthorizedApplicationItem(BaseModel):
    """已授权应用项 (T089/T097)

    运营商已获得授权的应用信息
    """
    app_id: str = Field(
        ...,
        description="应用ID(格式: app_<uuid>)"
    )

    app_code: str = Field(
        ...,
        description="应用唯一标识符"
    )

    app_name: str = Field(
        ...,
        description="应用名称"
    )

    description: Optional[str] = Field(
        None,
        description="应用描述"
    )

    price_per_player: str = Field(
        ...,
        description="当前单人价格(字符串格式)"
    )

    min_players: int = Field(
        ...,
        description="最小玩家数"
    )

    max_players: int = Field(
        ...,
        description="最大玩家数"
    )

    authorized_at: datetime = Field(
        ...,
        description="授权时间"
    )

    expires_at: Optional[datetime] = Field(
        None,
        description="授权到期时间(null表示永久授权)"
    )

    is_active: bool = Field(
        ...,
        description="授权状态"
    )

    launch_exe_path: Optional[str] = Field(
        None,
        description="自定义协议名称，用于启动头显Server应用，如 mrgun"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "app_id": "app_space_adventure_001",
                    "app_code": "space_adventure_v1",
                    "app_name": "太空探险",
                    "description": "VR太空探险游戏,支持2-8人协作",
                    "price_per_player": "10.00",
                    "min_players": 2,
                    "max_players": 8,
                    "authorized_at": "2025-01-01T10:00:00.000Z",
                    "expires_at": None,
                    "is_active": True
                }
            ]
        }
    }


class AuthorizedApplicationListResponse(BaseModel):
    """已授权应用列表响应 (T097)

    契约定义: operator.yaml GET /operators/me/applications

    返回运营商所有已授权的应用
    """
    applications: list[AuthorizedApplicationItem] = Field(
        ...,
        description="已授权应用列表"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "applications": [
                        {
                            "app_id": "app_space_adventure_001",
                            "app_code": "space_adventure_v1",
                            "app_name": "太空探险",
                            "description": "VR太空探险游戏,支持2-8人协作",
                            "price_per_player": "10.00",
                            "min_players": 2,
                            "max_players": 8,
                            "authorized_at": "2025-01-01T10:00:00.000Z",
                            "expires_at": None,
                            "is_active": True
                        },
                        {
                            "app_id": "app_star_war_001",
                            "app_code": "star_war_v2",
                            "app_name": "星际战争",
                            "description": "多人对战VR射击游戏",
                            "price_per_player": "12.00",
                            "min_players": 4,
                            "max_players": 10,
                            "authorized_at": "2025-01-05T14:00:00.000Z",
                            "expires_at": "2025-12-31T23:59:59.000Z",
                            "is_active": True
                        }
                    ]
                }
            ]
        }
    }


class ApplicationRequestCreate(BaseModel):
    """应用授权申请请求 (T088/T098)

    契约定义: operator.yaml POST /operators/me/applications/requests

    字段要求:
    - app_id: 应用ID(格式: app_<uuid>)
    - mode_ids: 申请的模式ID列表
    - reason: 10-500字符,申请理由
    """
    app_id: str = Field(
        ...,
        min_length=4,
        description="应用ID(格式: app_<uuid> 或纯UUID)",
        examples=["app_space_adventure_001"]
    )

    mode_ids: list[UUID] = Field(
        ...,
        min_length=1,
        description="申请的模式ID列表（至少选择一个）"
    )

    reason: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="申请理由",
        examples=["我们门店新增了VR设备，希望为用户提供太空探险游戏体验"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "app_id": "app_space_adventure_001",
                    "mode_ids": ["323e4567-e89b-12d3-a456-426614174000", "423e4567-e89b-12d3-a456-426614174000"],
                    "reason": "我们门店新增了VR设备，希望为用户提供太空探险游戏体验"
                }
            ]
        }
    }


class ApplicationRequestItem(BaseModel):
    """应用授权申请记录项 (T088/T099)

    运营商的应用授权申请记录
    """
    request_id: str = Field(
        ...,
        description="申请ID(格式: req_<uuid>)"
    )

    app_id: str = Field(
        ...,
        description="应用ID"
    )

    app_code: str = Field(
        ...,
        description="应用唯一标识符"
    )

    app_name: str = Field(
        ...,
        description="应用名称"
    )

    reason: str = Field(
        ...,
        description="申请理由"
    )

    status: str = Field(
        ...,
        description="审核状态: pending/approved/rejected"
    )

    reject_reason: Optional[str] = Field(
        None,
        description="拒绝原因(status=rejected时)"
    )

    reviewed_by: Optional[str] = Field(
        None,
        description="审核人ID(管理员)"
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
                    "request_id": "req_20250115_001",
                    "app_id": "app_space_adventure_001",
                    "app_name": "太空探险",
                    "reason": "我们门店新增了VR设备，希望为用户提供太空探险游戏体验",
                    "status": "approved",
                    "reject_reason": None,
                    "reviewed_by": "admin_001",
                    "reviewed_at": "2025-01-16T10:00:00.000Z",
                    "created_at": "2025-01-15T15:00:00.000Z"
                }
            ]
        }
    }


class ApplicationRequestListResponse(BaseModel):
    """应用授权申请列表响应(分页) (T099)

    契约定义: operator.yaml GET /operators/me/applications/requests

    返回运营商的所有授权申请记录
    """
    page: int = Field(..., description="当前页码", ge=1)
    page_size: int = Field(..., description="每页数量", ge=1, le=100)
    total: int = Field(..., description="总记录数", ge=0)
    items: list[ApplicationRequestItem] = Field(..., description="申请记录列表")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "page": 1,
                    "page_size": 20,
                    "total": 2,
                    "items": [
                        {
                            "request_id": "req_20250115_001",
                            "app_id": "app_space_adventure_001",
                            "app_name": "太空探险",
                            "reason": "我们门店新增了VR设备，希望为用户提供太空探险游戏体验",
                            "status": "approved",
                            "reject_reason": None,
                            "reviewed_by": "admin_001",
                            "reviewed_at": "2025-01-16T10:00:00.000Z",
                            "created_at": "2025-01-15T15:00:00.000Z"
                        },
                        {
                            "request_id": "req_20250110_002",
                            "app_id": "app_star_war_001",
                            "app_name": "星际战争",
                            "reason": "计划引入多人对战游戏丰富用户体验",
                            "status": "pending",
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
