"""授权相关的Pydantic Schemas (T041, T058)

此模块定义授权相关API的请求和响应数据模型:
1. 游戏授权 (T041): /auth/game/authorize
2. 运营商登录 (T058): /auth/operators/login

关键验证:
- session_id格式 (FR-061): {operatorId}_{13位毫秒时间戳}_{16位随机字符}
  * operatorId必须匹配请求的运营商ID
  * timestamp为13位Unix毫秒时间戳，在当前时间前后5分钟内
  * random为16位字母数字字符
- player_count范围: 1-100
- 金额字段使用字符串(避免浮点精度问题)
- JWT Token格式: Bearer {token}
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator
import re


# ==================== 登录相关模型 (T058) ====================


class OperatorLoginRequest(BaseModel):
    """运营商登录请求 (T058)

    契约定义: auth.yaml /auth/operators/login

    字段要求:
    - username: 必填,用户名
    - password: 必填,密码
    - captcha_key: 必填,验证码key
    - captcha_code: 必填,验证码
    """
    username: str = Field(
        ...,
        min_length=1,
        description="用户名",
        examples=["operator1"]
    )

    password: str = Field(
        ...,
        min_length=1,
        description="密码",
        examples=["operator123"]
    )

    captcha_key: str = Field(
        ...,
        min_length=1,
        description="验证码key",
        examples=["test-captcha-key"]
    )

    captcha_code: str = Field(
        ...,
        min_length=4,
        max_length=4,
        description="验证码 (开发/测试环境可使用0000)",
        examples=["0000"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "operator1",
                    "password": "operator123",
                    "captcha_key": "test-captcha-key",
                    "captcha_code": "0000"
                }
            ]
        }
    }


class OperatorInfo(BaseModel):
    """运营商基本信息(登录响应中)"""
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

    name: str = Field(
        ...,
        description="真实姓名或公司名",
        examples=["北京星空娱乐有限公司"]
    )

    category: str = Field(
        ...,
        description="客户分类: trial/standard/vip",
        examples=["standard"]
    )

    @field_validator("category")
    @classmethod
    def validate_category_enum(cls, v: str) -> str:
        """验证客户分类枚举值"""
        valid_categories = ["trial", "standard", "vip"]
        if v not in valid_categories:
            raise ValueError(f"无效的客户分类: {v}, 必须是 {valid_categories} 之一")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "operator_id": "op_12345",
                    "username": "operator_beijing_01",
                    "name": "北京星空娱乐有限公司",
                    "category": "normal"
                }
            ]
        }
    }


class LoginData(BaseModel):
    """登录成功响应数据"""
    access_token: str = Field(
        ...,
        description="JWT Token",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )

    token_type: str = Field(
        default="Bearer",
        description="Token类型",
        examples=["Bearer"]
    )

    expires_in: int = Field(
        ...,
        description="Token有效期(秒),30天=2592000秒",
        examples=[2592000]
    )

    operator: OperatorInfo = Field(
        ...,
        description="运营商信息"
    )

    @field_validator("access_token")
    @classmethod
    def validate_jwt_format(cls, v: str) -> str:
        """验证JWT Token格式(应该有3部分由.分隔)"""
        if v.count(".") != 2:
            raise ValueError("JWT Token格式错误,应包含3部分由.分隔")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "Bearer",
                    "expires_in": 2592000,
                    "operator": {
                        "operator_id": "op_12345",
                        "username": "operator_beijing_01",
                        "name": "北京星空娱乐有限公司",
                        "category": "normal"
                    }
                }
            ]
        }
    }


class LoginResponse(BaseModel):
    """登录成功响应包装 (T058)

    标准响应格式:
    {
        "success": true,
        "data": {...}
    }
    """
    success: bool = Field(
        default=True,
        description="请求是否成功"
    )

    data: LoginData = Field(
        ...,
        description="登录数据"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "data": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "Bearer",
                        "expires_in": 2592000,
                        "operator": {
                            "operator_id": "op_12345",
                            "username": "operator_beijing_01",
                            "name": "北京星空娱乐有限公司",
                            "category": "normal"
                        }
                    }
                }
            ]
        }
    }


# ==================== 请求模型 ====================


class GameAuthorizeRequest(BaseModel):
    """游戏授权请求体

    请求参数验证:
    - app_code: 应用代码(非空)
    - site_id: 运营点ID(非空)
    - player_count: 玩家数量(1-100)
    - headset_ids: 头显设备ID列表(可选)
    """

    app_code: str = Field(
        ...,
        description="应用代码",
        min_length=1,
        examples=["APP_20251030_001"]
    )

    site_id: str = Field(
        ...,
        description="运营点ID",
        min_length=1,
        examples=["site_beijing_001"]
    )

    player_count: int = Field(
        ...,
        description="玩家数量",
        ge=1,
        le=100,
        examples=[5]
    )

    application_mode_id: str = Field(
        ...,
        description="应用模式ID",
        min_length=1,
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )

    mode_name: str = Field(
        ...,
        description="应用模式名称(用于服务器校验)",
        min_length=1,
        max_length=64,
        examples=["5分钟"]
    )

    headset_ids: Optional[list[str]] = Field(
        default=None,
        description="头显设备ID列表(可选)",
        examples=[["headset_001", "headset_002"]]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "app_code": "APP_20251030_001",
                "site_id": "site_beijing_001",
                "player_count": 5,
                "application_mode_id": "550e8400-e29b-41d4-a716-446655440000",
                "mode_name": "5分钟",
                "headset_ids": ["headset_001", "headset_002"]
            }
        }


# ==================== 响应模型 ====================


class GameAuthorizeData(BaseModel):
    """授权成功响应数据

    响应字段:
    - session_id: 会话ID(幂等性标识)
    - app_name: 应用名称
    - player_count: 玩家数量
    - unit_price: 单人价格(字符串,避免浮点问题)
    - total_cost: 总费用(字符串)
    - balance_after: 扣费后余额(字符串)
    - authorized_at: 授权时间(ISO 8601)
    """

    session_id: str = Field(
        ...,
        description="会话ID (格式: {operatorId}_{13位毫秒时间戳}_{16位随机字符})",
        pattern=r'^[a-zA-Z0-9\-]+_\d{13}_[a-zA-Z0-9]{16}$',
        examples=["op_12345_1704067200000_a1b2c3d4e5f6g7h8"]
    )

    app_name: str = Field(
        ...,
        description="应用名称",
        examples=["太空探险"]
    )

    player_count: int = Field(
        ...,
        description="玩家数量",
        ge=1,
        examples=[5]
    )

    unit_price: str = Field(
        ...,
        description="单人价格(字符串格式,避免浮点精度问题)",
        pattern=r'^\d+\.\d{2}$',
        examples=["10.00"]
    )

    total_cost: str = Field(
        ...,
        description="总费用",
        pattern=r'^\d+\.\d{2}$',
        examples=["50.00"]
    )

    balance_after: str = Field(
        ...,
        description="扣费后账户余额",
        pattern=r'^\d+\.\d{2}$',
        examples=["450.00"]
    )

    authorized_at: datetime = Field(
        ...,
        description="授权时间(ISO 8601格式)",
        examples=["2025-01-01T12:30:00.000Z"]
    )

    @field_validator('session_id')
    @classmethod
    def validate_session_id_format(cls, v: str) -> str:
        """验证session_id格式: {operatorId}_{13位毫秒时间戳}_{16位随机字符}"""
        pattern = r'^[a-zA-Z0-9\-]+_\d{13}_[a-zA-Z0-9]{16}$'
        if not re.match(pattern, v):
            raise ValueError(
                f"session_id格式错误,应为: {{operatorId}}_{{13位毫秒时间戳}}_{{16位随机字符}}, 当前值: {v}"
            )
        return v

    @field_validator('unit_price', 'total_cost', 'balance_after')
    @classmethod
    def validate_decimal_string(cls, v: str) -> str:
        """验证金额字符串格式(保留2位小数)"""
        try:
            decimal_value = Decimal(v)
            # 确保格式为 X.XX (2位小数)
            if decimal_value.as_tuple().exponent != -2:
                raise ValueError(f"金额必须保留2位小数, 当前值: {v}")
            return v
        except Exception:
            raise ValueError(f"金额格式错误, 当前值: {v}")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "op_12345_1704067200_a1b2c3d4e5f6g7h8",
                "app_name": "太空探险",
                "player_count": 5,
                "unit_price": "10.00",
                "total_cost": "50.00",
                "balance_after": "450.00",
                "authorized_at": "2025-01-01T12:30:00.000Z"
            }
        }


class GameAuthorizeResponse(BaseModel):
    """授权成功响应包装

    标准响应格式:
    {
        "success": true,
        "data": {...}
    }
    """

    success: bool = Field(
        default=True,
        description="请求是否成功"
    )

    data: GameAuthorizeData = Field(
        ...,
        description="授权数据"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "session_id": "op_12345_1704067200_a1b2c3d4e5f6g7h8",
                    "app_name": "太空探险",
                    "player_count": 5,
                    "unit_price": "10.00",
                    "total_cost": "50.00",
                    "balance_after": "450.00",
                    "authorized_at": "2025-01-01T12:30:00.000Z"
                }
            }
        }


# ==================== 错误响应模型 ====================


class ErrorDetail(BaseModel):
    """错误详情(可选)"""

    min_players: Optional[int] = None
    max_players: Optional[int] = None
    requested_players: Optional[int] = None
    current_balance: Optional[str] = None
    required_amount: Optional[str] = None
    shortage: Optional[str] = None
    app_id: Optional[str] = None
    app_name: Optional[str] = None
    server_time: Optional[int] = None
    request_time: Optional[int] = None
    max_diff_seconds: Optional[int] = None
    limit: Optional[int] = None
    window_seconds: Optional[int] = None
    retry_after: Optional[int] = None


class ErrorResponse(BaseModel):
    """标准错误响应

    错误代码:
    - PLAYER_COUNT_OUT_OF_RANGE: 玩家数量超出范围
    - INVALID_SIGNATURE: HMAC签名无效
    - TIMESTAMP_EXPIRED: 时间戳过期
    - INVALID_API_KEY: API Key无效
    - INSUFFICIENT_BALANCE: 余额不足
    - APP_NOT_AUTHORIZED: 应用未授权
    - RATE_LIMIT_EXCEEDED: 请求频率超限
    """

    error_code: str = Field(
        ...,
        description="错误代码",
        examples=["INSUFFICIENT_BALANCE"]
    )

    message: str = Field(
        ...,
        description="错误消息",
        examples=["账户余额不足,当前余额: 30.00元,需要: 50.00元"]
    )

    details: Optional[ErrorDetail] = Field(
        default=None,
        description="错误详情(可选)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "error_code": "INSUFFICIENT_BALANCE",
                "message": "账户余额不足,当前余额: 30.00元,需要: 50.00元",
                "details": {
                    "current_balance": "30.00",
                    "required_amount": "50.00",
                    "shortage": "20.00"
                }
            }
        }


# ==================== 游戏预授权 (Pre-Authorize) ====================


class GamePreAuthorizeData(BaseModel):
    """游戏预授权响应数据(不扣费,仅检查授权资格)"""

    can_authorize: bool = Field(
        ...,
        description="是否可以授权",
        examples=[True]
    )

    app_code: str = Field(
        ...,
        description="应用代码",
        examples=["APP_20251030_001"]
    )

    app_name: str = Field(
        ...,
        description="应用名称",
        examples=["太空探险"]
    )

    player_count: int = Field(
        ...,
        description="玩家数量",
        ge=1,
        examples=[5]
    )

    unit_price: str = Field(
        ...,
        description="单人价格",
        pattern=r'^\d+\.\d{2}$',
        examples=["10.00"]
    )

    total_cost: str = Field(
        ...,
        description="总费用",
        pattern=r'^\d+\.\d{2}$',
        examples=["50.00"]
    )

    current_balance: str = Field(
        ...,
        description="当前账户余额",
        pattern=r'^\d+\.\d{2}$',
        examples=["450.00"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "can_authorize": True,
                "app_name": "太空探险",
                "player_count": 5,
                "unit_price": "10.00",
                "total_cost": "50.00",
                "current_balance": "450.00"
            }
        }


class GamePreAuthorizeResponse(BaseModel):
    """游戏预授权响应包装"""

    success: bool = Field(
        default=True,
        description="请求是否成功"
    )

    data: GamePreAuthorizeData = Field(
        ...,
        description="预授权数据"
    )


# ==================== 游戏Session上传 ====================


class HeadsetDeviceRecord(BaseModel):
    """头显设备记录"""

    device_id: str = Field(
        ...,
        description="设备ID",
        min_length=1,
        examples=["headset_001"]
    )

    device_name: Optional[str] = Field(
        default=None,
        description="设备名称(可选)",
        examples=["头显设备1"]
    )

    start_time: Optional[datetime] = Field(
        default=None,
        description="设备开始时间(可选)",
        examples=["2025-01-01T12:30:00.000Z"]
    )

    end_time: Optional[datetime] = Field(
        default=None,
        description="设备结束时间(可选)",
        examples=["2025-01-01T13:00:00.000Z"]
    )

    process_info: Optional[str] = Field(
        default=None,
        description="设备过程信息(可选,YAML/JSON格式)",
        examples=["score: 1500\nkills: 10"]
    )


class GameSessionUploadRequest(BaseModel):
    """游戏Session上传请求"""

    session_id: str = Field(
        ...,
        description="会话ID(授权时返回的session_id)",
        min_length=1,
        examples=["op_12345_1704067200000_a1b2c3d4e5f6g7h8"]
    )

    start_time: Optional[datetime] = Field(
        default=None,
        description="游戏开始时间(可选)",
        examples=["2025-01-01T12:30:00.000Z"]
    )

    end_time: Optional[datetime] = Field(
        default=None,
        description="游戏结束时间(可选)",
        examples=["2025-01-01T13:00:00.000Z"]
    )

    process_info: Optional[str] = Field(
        default=None,
        description="游戏过程信息(可选,YAML/JSON格式)",
        examples=["total_rounds: 5\nwinners: [player1, player3]"]
    )

    headset_devices: Optional[list[HeadsetDeviceRecord]] = Field(
        default=None,
        description="头显设备记录列表(可选)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "op_12345_1704067200000_a1b2c3d4e5f6g7h8",
                "start_time": "2025-01-01T12:30:00.000Z",
                "end_time": "2025-01-01T13:00:00.000Z",
                "process_info": "total_rounds: 5\nwinners: [player1, player3]",
                "headset_devices": [
                    {
                        "device_id": "headset_001",
                        "device_name": "头显设备1",
                        "start_time": "2025-01-01T12:30:00.000Z",
                        "end_time": "2025-01-01T13:00:00.000Z",
                        "process_info": "score: 1500\nkills: 10"
                    }
                ]
            }
        }


class GameSessionUploadResponse(BaseModel):
    """游戏Session上传响应"""

    success: bool = Field(
        default=True,
        description="请求是否成功"
    )

    message: str = Field(
        ...,
        description="响应消息",
        examples=["游戏信息上传成功"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "游戏信息上传成功"
            }
        }
