"""MR游戏运营管理系统 Python SDK

为头显Server提供游戏授权、计费功能的Python SDK。
"""

from .client import MRGameClient
from .exceptions import (
    MRGameAPIError,
    MRGameAuthError,
    MRGameValidationError,
    MRGameNetworkError,
)
from .models import (
    AuthorizeResponse,
    EndSessionResponse,
    BalanceResponse,
    TransactionListResponse,
    TransactionItem,
)

__version__ = "1.0.0"
__author__ = "MR游戏团队"
__email__ = "support@mr-game.com"

__all__ = [
    # Main client
    "MRGameClient",
    # Exceptions
    "MRGameAPIError",
    "MRGameAuthError",
    "MRGameValidationError",
    "MRGameNetworkError",
    # Response models
    "AuthorizeResponse",
    "EndSessionResponse",
    "BalanceResponse",
    "TransactionListResponse",
    "TransactionItem",
]