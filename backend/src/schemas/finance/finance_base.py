"""
财务相关的Pydantic Schemas (T162-T167)

包含:
- 财务登录请求/响应 (T162)
- 财务仪表盘schemas (T163)
- 退款审核schemas (T164)
- 发票审核schemas (T165)
- 财务报表schemas (T166)
- 审计日志schemas (T167)
"""
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
import re


# ========== T162: 财务登录相关 Schema ==========

class FinanceLoginRequest(BaseModel):
    """财务人员登录请求 (T162)

    契约定义: auth.yaml /auth/finance/login

    字段要求:
    - username: 财务人员用户名
    - password: 密码
    - captcha_key: 验证码key
    - captcha_code: 验证码
    """
    username: str = Field(
        ...,
        min_length=3,
        max_length=64,
        description="财务人员用户名",
        examples=["finance_zhang"]
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=32,
        description="密码",
        examples=["FinancePass123"]
    )

    captcha_key: str = Field(
        ...,
        min_length=1,
        description="验证码key",
        examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
    )

    captcha_code: str = Field(
        ...,
        min_length=4,
        max_length=4,
        description="验证码",
        examples=["AB12"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "username": "finance_zhang",
                    "password": "FinancePass123"
                }
            ]
        }
    }


class FinanceInfo(BaseModel):
    """财务人员基本信息 (T162)

    返回的财务人员信息（不含敏感字段）
    """
    finance_id: str = Field(
        ...,
        description="财务人员ID",
        examples=["fin_001"]
    )

    username: str = Field(
        ...,
        description="用户名",
        examples=["finance_zhang"]
    )

    full_name: str = Field(
        ...,
        description="真实姓名",
        examples=["张财务"]
    )

    role: str = Field(
        ...,
        description="角色: specialist/manager/auditor",
        examples=["specialist"]
    )

    email: str = Field(
        ...,
        description="邮箱地址",
        examples=["finance.zhang@example.com"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "finance_id": "fin_001",
                    "username": "finance_zhang",
                    "full_name": "张财务",
                    "role": "specialist",
                    "email": "finance.zhang@example.com"
                }
            ]
        }
    }


class FinanceLoginResponse(BaseModel):
    """财务人员登录响应 (T162)

    返回JWT Token和财务人员基本信息
    注意: 契约测试期望直接字段，不包装在data中
    """
    access_token: str = Field(
        ...,
        description="JWT访问令牌",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )

    token_type: str = Field(
        default="bearer",
        description="令牌类型",
        examples=["bearer"]
    )

    expires_in: int = Field(
        ...,
        description="令牌有效期（秒）",
        examples=[3600]
    )

    finance: FinanceInfo = Field(
        ...,
        description="财务人员信息"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 3600,
                    "finance": {
                        "finance_id": "fin_001",
                        "username": "finance_zhang",
                        "full_name": "张财务",
                        "role": "specialist",
                        "email": "finance.zhang@example.com"
                    }
                }
            ]
        }
    }


# ========== T163: 财务仪表盘相关 Schema ==========

class DashboardOverview(BaseModel):
    """今日收入概览 (T163)

    契约定义: finance.yaml GET /finance/dashboard
    """
    today_recharge: str = Field(
        ...,
        description="今日充值总额",
        examples=["15000.00"]
    )

    today_consumption: str = Field(
        ...,
        description="今日消费总额",
        examples=["12000.00"]
    )

    today_refund: str = Field(
        ...,
        description="今日退款总额",
        examples=["500.00"]
    )

    today_net_income: str = Field(
        ...,
        description="今日净收入（充值 - 退款）",
        examples=["14500.00"]
    )

    total_operators: int = Field(
        ...,
        description="总运营商数",
        examples=[150]
    )

    active_operators_today: int = Field(
        ...,
        description="今日活跃运营商数（有交易）",
        examples=[45]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "today_recharge": "15000.00",
                    "today_consumption": "12000.00",
                    "today_refund": "500.00",
                    "today_net_income": "14500.00",
                    "total_operators": 150,
                    "active_operators_today": 45
                }
            ]
        }
    }


class DailyTrendItem(BaseModel):
    """每日趋势数据项 (T163)

    单日的收入数据
    """
    trend_date: date = Field(
        ...,
        description="日期",
        examples=["2025-01-15"],
        alias="date"  # API中依然使用"date"
    )

    recharge: str = Field(
        ...,
        description="当日充值",
        examples=["15000.00"]
    )

    consumption: str = Field(
        ...,
        description="当日消费",
        examples=["12000.00"]
    )

    refund: str = Field(
        ...,
        description="当日退款",
        examples=["500.00"]
    )

    net_income: str = Field(
        ...,
        description="当日净收入",
        examples=["14500.00"]
    )

    model_config = {
        "populate_by_name": True  # 允许使用字段名或别名
    }


class TrendsSummary(BaseModel):
    """趋势汇总 (T163)

    本月汇总数据
    """
    total_recharge: str = Field(
        ...,
        description="总充值",
        examples=["350000.00"]
    )

    total_consumption: str = Field(
        ...,
        description="总消费",
        examples=["280000.00"]
    )

    total_refund: str = Field(
        ...,
        description="总退款",
        examples=["5000.00"]
    )

    total_net_income: str = Field(
        ...,
        description="总净收入",
        examples=["345000.00"]
    )


class DashboardTrends(BaseModel):
    """本月收入趋势 (T163)

    契约定义: finance.yaml GET /finance/dashboard/trends
    """
    month: str = Field(
        ...,
        description="月份（YYYY-MM）",
        examples=["2025-01"]
    )

    chart_data: List[DailyTrendItem] = Field(
        ...,
        description="每日趋势数据"
    )

    summary: TrendsSummary = Field(
        ...,
        description="本月汇总"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "month": "2025-01",
                    "chart_data": [
                        {
                            "date": "2025-01-15",
                            "recharge": "15000.00",
                            "consumption": "12000.00",
                            "refund": "500.00",
                            "net_income": "14500.00"
                        }
                    ],
                    "summary": {
                        "total_recharge": "350000.00",
                        "total_consumption": "280000.00",
                        "total_refund": "5000.00",
                        "total_net_income": "345000.00"
                    }
                }
            ]
        }
    }


class TopCustomer(BaseModel):
    """TOP客户项 (T163)

    单个TOP客户的数据
    """
    rank: int = Field(
        ...,
        description="排名",
        examples=[1]
    )

    operator_id: str = Field(
        ...,
        description="运营商ID",
        examples=["op_12345"]
    )

    operator_name: str = Field(
        ...,
        description="运营商名称",
        examples=["北京星空娱乐有限公司"]
    )

    category: str = Field(
        ...,
        description="客户分类: trial/normal/vip",
        examples=["vip"]
    )

    total_consumption: str = Field(
        ...,
        description="总消费额",
        examples=["25000.00"]
    )

    consumption_percentage: float = Field(
        ...,
        description="消费占比（百分比）",
        examples=[8.93]
    )

    total_sessions: int = Field(
        ...,
        description="总游戏场次",
        examples=[250]
    )


class TopCustomersResponse(BaseModel):
    """TOP客户列表响应 (T163)

    契约定义: finance.yaml GET /finance/top-customers
    """
    customers: List[TopCustomer] = Field(
        ...,
        description="TOP客户列表"
    )

    total_consumption: str = Field(
        ...,
        description="所有客户总消费额",
        examples=["280000.00"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "customers": [
                        {
                            "rank": 1,
                            "operator_id": "op_12345",
                            "operator_name": "北京星空娱乐有限公司",
                            "category": "vip",
                            "total_consumption": "25000.00",
                            "consumption_percentage": 8.93,
                            "total_sessions": 250
                        }
                    ],
                    "total_consumption": "280000.00"
                }
            ]
        }
    }


class CustomerFinanceDetails(BaseModel):
    """客户详细财务信息 (T163)

    契约定义: finance.yaml GET /finance/customers/{operator_id}/details
    """
    operator_id: str = Field(
        ...,
        description="运营商ID",
        examples=["op_12345"]
    )

    operator_name: str = Field(
        ...,
        description="运营商名称",
        examples=["北京星空娱乐有限公司"]
    )

    category: str = Field(
        ...,
        description="客户分类: trial/normal/vip",
        examples=["normal"]
    )

    current_balance: str = Field(
        ...,
        description="当前余额",
        examples=["100.00"]
    )

    total_recharged: str = Field(
        ...,
        description="累计充值",
        examples=["5000.00"]
    )

    total_consumed: str = Field(
        ...,
        description="累计消费",
        examples=["4800.00"]
    )

    total_refunded: str = Field(
        ...,
        description="累计退款",
        examples=["100.00"]
    )

    total_sessions: int = Field(
        ...,
        description="总游戏场次",
        examples=[120]
    )

    first_transaction_at: datetime = Field(
        ...,
        description="首次交易时间",
        examples=["2025-01-01T10:00:00.000Z"]
    )

    last_transaction_at: Optional[datetime] = Field(
        None,
        description="最后交易时间",
        examples=["2025-01-15T10:20:00.000Z"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "operator_id": "op_12345",
                    "operator_name": "北京星空娱乐有限公司",
                    "category": "normal",
                    "current_balance": "100.00",
                    "total_recharged": "5000.00",
                    "total_consumed": "4800.00",
                    "total_refunded": "100.00",
                    "total_sessions": 120,
                    "first_transaction_at": "2025-01-01T10:00:00.000Z",
                    "last_transaction_at": "2025-01-15T10:20:00.000Z"
                }
            ]
        }
    }


# ========== T164: 退款审核相关 Schema ==========

class RefundItemFinance(BaseModel):
    """退款记录项（财务视角）(T164)

    契约定义: finance.yaml RefundRequestFinance schema
    """
    refund_id: str = Field(
        ...,
        description="退款ID",
        examples=["refund_20250115_001"]
    )

    operator_id: str = Field(
        ...,
        description="运营商ID",
        examples=["op_12345"]
    )

    operator_name: str = Field(
        ...,
        description="运营商名称",
        examples=["北京星空娱乐有限公司"]
    )

    operator_category: Optional[str] = Field(
        None,
        description="客户分类: trial/normal/vip",
        examples=["normal"]
    )

    requested_amount: str = Field(
        ...,
        description="申请退款金额（申请时余额）",
        examples=["100.00"]
    )

    current_balance: str = Field(
        ...,
        description="当前账户余额（审核时实时余额）",
        examples=["80.00"]
    )

    actual_refund_amount: Optional[str] = Field(
        None,
        description="实际退款金额（审核通过后）",
        examples=[None]
    )

    status: str = Field(
        ...,
        description="审核状态: pending/approved/rejected",
        examples=["pending"]
    )

    reason: str = Field(
        ...,
        description="退款原因",
        examples=["业务调整，不再继续使用"]
    )

    reject_reason: Optional[str] = Field(
        None,
        description="拒绝原因",
        examples=[None]
    )

    reviewed_by: Optional[str] = Field(
        None,
        description="审核人ID",
        examples=[None]
    )

    reviewed_at: Optional[datetime] = Field(
        None,
        description="审核时间",
        examples=[None]
    )

    created_at: datetime = Field(
        ...,
        description="申请时间",
        examples=["2025-01-15T16:00:00.000Z"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "refund_id": "refund_20250115_001",
                    "operator_id": "op_12345",
                    "operator_name": "北京星空娱乐有限公司",
                    "operator_category": "normal",
                    "requested_amount": "100.00",
                    "current_balance": "80.00",
                    "actual_refund_amount": None,
                    "status": "pending",
                    "reason": "业务调整，不再继续使用",
                    "reject_reason": None,
                    "reviewed_by": None,
                    "reviewed_at": None,
                    "created_at": "2025-01-15T16:00:00.000Z"
                }
            ]
        }
    }


class RefundListResponse(BaseModel):
    """退款列表响应（分页）(T164)

    契约定义: finance.yaml GET /finance/refunds
    """
    page: int = Field(..., description="当前页码", ge=1)
    page_size: int = Field(..., description="每页数量", ge=1, le=100)
    total: int = Field(..., description="总记录数", ge=0)
    items: List[RefundItemFinance] = Field(..., description="退款记录列表")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "page": 1,
                    "page_size": 20,
                    "total": 1,
                    "items": [
                        {
                            "refund_id": "refund_20250115_001",
                            "operator_id": "op_12345",
                            "operator_name": "北京星空娱乐有限公司",
                            "operator_category": "normal",
                            "requested_amount": "100.00",
                            "current_balance": "80.00",
                            "actual_refund_amount": None,
                            "status": "pending",
                            "reason": "业务调整，不再继续使用",
                            "reject_reason": None,
                            "reviewed_by": None,
                            "reviewed_at": None,
                            "created_at": "2025-01-15T16:00:00.000Z"
                        }
                    ]
                }
            ]
        }
    }


class RefundDetailsResponse(BaseModel):
    """退款详情响应 (T164)

    契约定义: finance.yaml GET /finance/refunds/{refund_id}
    包含退款信息和运营商财务详情
    """
    refund_id: str
    operator_id: str
    operator_name: str
    operator_category: Optional[str] = None
    requested_amount: str
    current_balance: str
    actual_refund_amount: Optional[str] = None
    status: str
    reason: str
    reject_reason: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    # 额外的运营商财务详情
    operator_finance: CustomerFinanceDetails = Field(
        ...,
        description="运营商财务详细信息"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "refund_id": "refund_20250115_001",
                    "operator_id": "op_12345",
                    "operator_name": "北京星空娱乐有限公司",
                    "operator_category": "normal",
                    "requested_amount": "100.00",
                    "current_balance": "80.00",
                    "actual_refund_amount": None,
                    "status": "pending",
                    "reason": "业务调整，不再继续使用",
                    "reject_reason": None,
                    "reviewed_by": None,
                    "reviewed_at": None,
                    "created_at": "2025-01-15T16:00:00.000Z",
                    "operator_finance": {
                        "operator_id": "op_12345",
                        "operator_name": "北京星空娱乐有限公司",
                        "category": "normal",
                        "current_balance": "80.00",
                        "total_recharged": "5000.00",
                        "total_consumed": "4800.00",
                        "total_refunded": "100.00",
                        "total_sessions": 120,
                        "first_transaction_at": "2025-01-01T10:00:00.000Z",
                        "last_transaction_at": "2025-01-15T10:20:00.000Z"
                    }
                }
            ]
        }
    }


class RefundApproveRequest(BaseModel):
    """批准退款请求 (T164)

    契约定义: finance.yaml POST /finance/refunds/{refund_id}/approve
    """
    note: Optional[str] = Field(
        None,
        max_length=200,
        description="审批备注（可选）",
        examples=["退款已处理，退款金额: 80.00元（审核期间有新消费）"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "note": "退款已处理"
                }
            ]
        }
    }


class RefundApproveResponse(BaseModel):
    """批准退款响应 (T164)

    契约定义: finance.yaml POST /finance/refunds/{refund_id}/approve response
    """
    refund_id: str = Field(
        ...,
        description="退款ID",
        examples=["refund_20250115_001"]
    )

    requested_amount: Optional[str] = Field(
        None,
        description="申请金额",
        examples=["100.00"]
    )

    actual_refund_amount: str = Field(
        ...,
        description="实际退款金额",
        examples=["80.00"]
    )

    balance_after: str = Field(
        ...,
        description="退款后余额",
        examples=["0.00"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "refund_id": "refund_20250115_001",
                    "requested_amount": "100.00",
                    "actual_refund_amount": "80.00",
                    "balance_after": "0.00"
                }
            ]
        }
    }


class RefundRejectRequest(BaseModel):
    """拒绝退款请求 (T164)

    契约定义: finance.yaml POST /finance/refunds/{refund_id}/reject
    """
    reason: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="拒绝原因",
        examples=["退款原因不符合公司政策，建议继续使用或联系客服"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "reason": "退款原因不符合公司政策，建议继续使用或联系客服"
                }
            ]
        }
    }


# ========== T165: 发票审核相关 Schema ==========

class InvoiceItemFinance(BaseModel):
    """发票记录项（财务视角）(T165)

    契约定义: finance.yaml InvoiceRequestFinance schema
    """
    invoice_id: str = Field(
        ...,
        description="发票ID",
        examples=["inv_20250115_001"]
    )

    operator_id: str = Field(
        ...,
        description="运营商ID",
        examples=["op_12345"]
    )

    operator_name: str = Field(
        ...,
        description="运营商名称",
        examples=["北京星空娱乐有限公司"]
    )

    operator_category: Optional[str] = Field(
        None,
        description="客户分类: trial/normal/vip",
        examples=["normal"]
    )

    amount: str = Field(
        ...,
        description="开票金额",
        examples=["1000.00"]
    )

    invoice_title: str = Field(
        ...,
        description="发票抬头",
        examples=["北京星空娱乐有限公司"]
    )

    invoice_type: Optional[str] = Field(
        None,
        description="发票类型: vat_normal/vat_special",
        examples=["vat_normal"]
    )

    tax_id: str = Field(
        ...,
        description="纳税人识别号",
        examples=["91110000123456789X"]
    )

    email: Optional[str] = Field(
        None,
        description="接收邮箱",
        examples=["finance@example.com"]
    )

    status: str = Field(
        ...,
        description="审核状态: pending/approved/rejected",
        examples=["pending"]
    )

    reject_reason: Optional[str] = Field(
        None,
        description="拒绝原因（status=rejected时）",
        examples=[None]
    )

    invoice_number: Optional[str] = Field(
        None,
        description="发票号码（status=approved时）",
        examples=[None]
    )

    pdf_url: Optional[str] = Field(
        None,
        description="发票PDF下载链接（status=approved时）",
        examples=[None]
    )

    reviewed_by: Optional[str] = Field(
        None,
        description="审核人ID",
        examples=[None]
    )

    reviewed_at: Optional[datetime] = Field(
        None,
        description="审核时间",
        examples=[None]
    )

    requested_at: datetime = Field(
        ...,
        description="申请时间",
        examples=["2025-01-15T17:00:00.000Z"]
    )

    created_at: datetime = Field(
        ...,
        description="创建时间",
        examples=["2025-01-15T17:00:00.000Z"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "invoice_id": "inv_20250115_001",
                    "operator_id": "op_12345",
                    "operator_name": "北京星空娱乐有限公司",
                    "operator_category": "normal",
                    "amount": "1000.00",
                    "invoice_title": "北京星空娱乐有限公司",
                    "tax_id": "91110000123456789X",
                    "email": "finance@example.com",
                    "status": "pending",
                    "pdf_url": None,
                    "reviewed_by": None,
                    "reviewed_at": None,
                    "created_at": "2025-01-15T17:00:00.000Z"
                }
            ]
        }
    }


class InvoiceListResponse(BaseModel):
    """发票列表响应（分页）(T165)

    契约定义: finance.yaml GET /finance/invoices
    """
    page: int = Field(..., description="当前页码", ge=1)
    page_size: int = Field(..., description="每页数量", ge=1, le=100)
    total: int = Field(..., description="总记录数", ge=0)
    items: List[InvoiceItemFinance] = Field(..., description="发票记录列表")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "page": 1,
                    "page_size": 20,
                    "total": 1,
                    "items": [
                        {
                            "invoice_id": "inv_20250115_001",
                            "operator_id": "op_12345",
                            "operator_name": "北京星空娱乐有限公司",
                            "operator_category": "normal",
                            "amount": "1000.00",
                            "invoice_title": "北京星空娱乐有限公司",
                            "tax_id": "91110000123456789X",
                            "email": "finance@example.com",
                            "status": "pending",
                            "pdf_url": None,
                            "reviewed_by": None,
                            "reviewed_at": None,
                            "created_at": "2025-01-15T17:00:00.000Z"
                        }
                    ]
                }
            ]
        }
    }


class InvoiceApproveRequest(BaseModel):
    """批准发票请求 (T165)

    契约定义: finance.yaml POST /finance/invoices/{invoice_id}/approve
    """
    note: Optional[str] = Field(
        None,
        max_length=200,
        description="审批备注（可选）",
        examples=["发票已生成并发送至邮箱"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "note": "发票已生成并发送至邮箱"
                }
            ]
        }
    }


class InvoiceApproveResponse(BaseModel):
    """批准发票响应 (T165)

    契约定义: finance.yaml POST /finance/invoices/{invoice_id}/approve response
    """
    invoice_id: str = Field(
        ...,
        description="发票ID",
        examples=["inv_20250115_001"]
    )

    pdf_url: str = Field(
        ...,
        description="发票PDF下载链接",
        examples=["https://api.example.com/invoices/inv_20250115_001.pdf"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "invoice_id": "inv_20250115_001",
                    "pdf_url": "https://api.example.com/invoices/inv_20250115_001.pdf"
                }
            ]
        }
    }


# ========== T166: 财务报表相关 Schema ==========

class ReportGenerateRequest(BaseModel):
    """生成财务报表请求 (T166)

    契约定义: finance.yaml POST /finance/reports/generate
    """
    report_type: str = Field(
        ...,
        description="报表类型: daily/weekly/monthly/custom",
        examples=["monthly"]
    )

    start_date: date = Field(
        ...,
        description="开始日期",
        examples=["2025-01-01"]
    )

    end_date: date = Field(
        ...,
        description="结束日期",
        examples=["2025-01-31"]
    )

    format: str = Field(
        ...,
        description="报表格式: pdf/excel",
        examples=["pdf"]
    )

    include_sections: Optional[List[str]] = Field(
        None,
        description="包含的报表章节（可选，默认全部）",
        examples=[["income_summary", "top_customers", "usage_statistics"]]
    )

    @field_validator("report_type")
    @classmethod
    def validate_report_type(cls, v: str) -> str:
        """验证报表类型"""
        valid_types = ["daily", "weekly", "monthly", "custom"]
        if v not in valid_types:
            raise ValueError(f"报表类型必须是: {', '.join(valid_types)}")
        return v

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """验证报表格式"""
        valid_formats = ["pdf", "excel"]
        if v not in valid_formats:
            raise ValueError(f"报表格式必须是: {', '.join(valid_formats)}")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "report_type": "monthly",
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-31",
                    "format": "pdf",
                    "include_sections": ["income_summary", "top_customers", "usage_statistics"]
                }
            ]
        }
    }


class ReportGenerateResponse(BaseModel):
    """生成财务报表响应 (T166)

    契约定义: finance.yaml POST /finance/reports/generate response
    """
    report_id: str = Field(
        ...,
        description="报表ID",
        examples=["rpt_20250115_001"]
    )

    status: str = Field(
        ...,
        description="生成状态: generating/completed/failed",
        examples=["generating"]
    )

    estimated_time: int = Field(
        ...,
        description="预计完成时间（秒）",
        examples=[300]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "report_id": "rpt_20250115_001",
                    "status": "generating",
                    "estimated_time": 300
                }
            ]
        }
    }


class FinanceReportItem(BaseModel):
    """财务报表项 (T166)

    契约定义: finance.yaml FinanceReport schema
    """
    report_id: str = Field(
        ...,
        description="报表ID",
        examples=["rpt_20250115_001"]
    )

    report_type: str = Field(
        ...,
        description="报表类型: daily/weekly/monthly/custom",
        examples=["monthly"]
    )

    start_date: date = Field(
        ...,
        description="开始日期",
        examples=["2025-01-01"]
    )

    end_date: date = Field(
        ...,
        description="结束日期",
        examples=["2025-01-31"]
    )

    format: str = Field(
        ...,
        description="报表格式: pdf/excel",
        examples=["pdf"]
    )

    status: str = Field(
        ...,
        description="生成状态: generating/completed/failed",
        examples=["completed"]
    )

    file_size: Optional[int] = Field(
        None,
        description="文件大小（字节）",
        examples=[2457600]
    )

    download_url: Optional[str] = Field(
        None,
        description="下载链接（status=completed时）",
        examples=["https://api.example.com/finance/reports/rpt_20250115_001/download"]
    )

    error_message: Optional[str] = Field(
        None,
        description="错误信息（status=failed时）",
        examples=[None]
    )

    created_by: str = Field(
        ...,
        description="生成人ID",
        examples=["fin_001"]
    )

    created_at: datetime = Field(
        ...,
        description="创建时间",
        examples=["2025-01-15T18:00:00.000Z"]
    )

    completed_at: Optional[datetime] = Field(
        None,
        description="完成时间",
        examples=["2025-01-15T18:04:30.000Z"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "report_id": "rpt_20250115_001",
                    "report_type": "monthly",
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-31",
                    "format": "pdf",
                    "status": "completed",
                    "file_size": 2457600,
                    "download_url": "https://api.example.com/finance/reports/rpt_20250115_001/download",
                    "error_message": None,
                    "created_by": "fin_001",
                    "created_at": "2025-01-15T18:00:00.000Z",
                    "completed_at": "2025-01-15T18:04:30.000Z"
                }
            ]
        }
    }


class ReportListResponse(BaseModel):
    """报表列表响应（分页）(T166)

    契约定义: finance.yaml GET /finance/reports
    """
    page: int = Field(..., description="当前页码", ge=1)
    page_size: int = Field(..., description="每页数量", ge=1, le=100)
    total: int = Field(..., description="总记录数", ge=0)
    items: List[FinanceReportItem] = Field(..., description="报表列表")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "page": 1,
                    "page_size": 20,
                    "total": 1,
                    "items": [
                        {
                            "report_id": "rpt_20250115_001",
                            "report_type": "monthly",
                            "start_date": "2025-01-01",
                            "end_date": "2025-01-31",
                            "format": "pdf",
                            "status": "completed",
                            "file_size": 2457600,
                            "download_url": "https://api.example.com/finance/reports/rpt_20250115_001/download",
                            "error_message": None,
                            "created_by": "fin_001",
                            "created_at": "2025-01-15T18:00:00.000Z",
                            "completed_at": "2025-01-15T18:04:30.000Z"
                        }
                    ]
                }
            ]
        }
    }


# ========== 手动充值相关 Schema ==========

class RechargeRequest(BaseModel):
    """手动充值请求

    财务人员为运营商手动充值
    """
    operator_id: str = Field(
        ...,
        description="运营商ID",
        examples=["op_12345"]
    )

    amount: float = Field(
        ...,
        gt=0,
        description="充值金额（必须大于0）",
        examples=[1000.00]
    )

    description: Optional[str] = Field(
        None,
        max_length=200,
        description="充值备注（可选）",
        examples=["线下银行转账充值"]
    )

    payment_proof: Optional[str] = Field(
        None,
        description="付款凭证文件路径（可选）",
        examples=["uploads/payment_proofs/20250115_123456.jpg"]
    )


class RechargeResponse(BaseModel):
    """手动充值响应

    充值操作结果
    """
    transaction_id: str = Field(
        ...,
        description="交易记录ID",
        examples=["txn_20250115_001"]
    )

    operator_id: str = Field(
        ...,
        description="运营商ID",
        examples=["op_12345"]
    )

    operator_name: str = Field(
        ...,
        description="运营商名称",
        examples=["北京星空娱乐有限公司"]
    )

    amount: str = Field(
        ...,
        description="充值金额",
        examples=["1000.00"]
    )

    balance_before: str = Field(
        ...,
        description="充值前余额",
        examples=["500.00"]
    )

    balance_after: str = Field(
        ...,
        description="充值后余额",
        examples=["1500.00"]
    )

    description: Optional[str] = Field(
        None,
        description="充值备注",
        examples=["线下银行转账充值"]
    )

    created_at: datetime = Field(
        ...,
        description="充值时间",
        examples=["2025-01-15T19:00:00.000Z"]
    )


# ========== T167: 审计日志相关 Schema ==========

class AuditLogItem(BaseModel):
    """审计日志项 (T167)

    契约定义: finance.yaml AuditLog schema
    """
    log_id: str = Field(
        ...,
        description="日志ID",
        examples=["log_20250115_123456"]
    )

    finance_id: str = Field(
        ...,
        description="财务人员ID",
        examples=["fin_001"]
    )

    finance_name: str = Field(
        ...,
        description="财务人员姓名",
        examples=["张财务"]
    )

    operation_type: str = Field(
        ...,
        description="操作类型: refund_approve/refund_reject/invoice_approve/invoice_reject/report_generate/view_api_key",
        examples=["refund_approve"]
    )

    target_resource_id: str = Field(
        ...,
        description="目标资源ID（退款ID、发票ID等）",
        examples=["refund_20250115_001"]
    )

    operation_details: Dict[str, Any] = Field(
        ...,
        description="操作详情（JSON格式）",
        examples=[
            {
                "operator_id": "op_12345",
                "operator_name": "北京星空娱乐有限公司",
                "refund_amount": "80.00",
                "note": "退款已处理"
            }
        ]
    )

    ip_address: str = Field(
        ...,
        description="操作IP地址",
        examples=["192.168.1.100"]
    )

    user_agent: Optional[str] = Field(
        None,
        description="用户代理",
        examples=["Mozilla/5.0 (Windows NT 10.0; Win64; x64) ..."]
    )

    created_at: datetime = Field(
        ...,
        description="操作时间",
        examples=["2025-01-15T18:30:00.000Z"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "log_id": "log_20250115_123456",
                    "finance_id": "fin_001",
                    "finance_name": "张财务",
                    "operation_type": "refund_approve",
                    "target_resource_id": "refund_20250115_001",
                    "operation_details": {
                        "operator_id": "op_12345",
                        "operator_name": "北京星空娱乐有限公司",
                        "refund_amount": "80.00",
                        "note": "退款已处理"
                    },
                    "ip_address": "192.168.1.100",
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
                    "created_at": "2025-01-15T18:30:00.000Z"
                }
            ]
        }
    }


class AuditLogListResponse(BaseModel):
    """审计日志列表响应（分页）(T167)

    契约定义: finance.yaml GET /finance/audit-logs
    """
    page: int = Field(..., description="当前页码", ge=1)
    page_size: int = Field(..., description="每页数量", ge=1, le=100)
    total: int = Field(..., description="总记录数", ge=0)
    items: List[AuditLogItem] = Field(..., description="审计日志列表")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "page": 1,
                    "page_size": 20,
                    "total": 1,
                    "items": [
                        {
                            "log_id": "log_20250115_123456",
                            "finance_id": "fin_001",
                            "finance_name": "张财务",
                            "operation_type": "refund_approve",
                            "target_resource_id": "refund_20250115_001",
                            "operation_details": {
                                "operator_id": "op_12345",
                                "operator_name": "北京星空娱乐有限公司",
                                "refund_amount": "80.00",
                                "note": "退款已处理"
                            },
                            "ip_address": "192.168.1.100",
                            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
                            "created_at": "2025-01-15T18:30:00.000Z"
                        }
                    ]
                }
            ]
        }
    }
