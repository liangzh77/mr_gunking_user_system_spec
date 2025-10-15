"""SQLAlchemy ORM Models

此包包含所有数据库表的SQLAlchemy模型定义。

User Story 1 - 游戏授权与实时计费:
- OperatorAccount: 运营商账户
- Application: 可授权的MR游戏应用
- OperationSite: 运营点(线下门店)
- UsageRecord: 游戏会话使用记录
- TransactionRecord: 资金交易记录
- OperatorAppAuthorization: 运营商应用授权关系

User Story 2 - 运营商账户与财务管理:
- RefundRecord: 退款申请记录
- InvoiceRecord: 发票申请记录

User Story 3 - 运营点与应用授权管理:
- ApplicationRequest: 应用授权申请记录

User Story 5 - 管理员权限与应用配置:
- AdminAccount: 管理员账户
"""

from .admin import AdminAccount
from .app_request import ApplicationRequest
from .application import Application
from .authorization import OperatorAppAuthorization
from .invoice import InvoiceRecord
from .operator import OperatorAccount
from .refund import RefundRecord
from .site import OperationSite
from .transaction import TransactionRecord
from .usage_record import UsageRecord

__all__ = [
    "AdminAccount",
    "OperatorAccount",
    "Application",
    "OperationSite",
    "UsageRecord",
    "TransactionRecord",
    "OperatorAppAuthorization",
    "RefundRecord",
    "InvoiceRecord",
    "ApplicationRequest",
]
