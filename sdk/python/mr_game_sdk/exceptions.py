"""MR游戏SDK异常类定义"""


class MRGameError(Exception):
    """MR游戏SDK基础异常类"""

    def __init__(self, message: str, error_code: str = None, response_data: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.response_data = response_data or {}

    def __str__(self):
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class MRGameAPIError(MRGameError):
    """API调用错误"""
    pass


class MRGameAuthError(MRGameError):
    """认证错误"""
    pass


class MRGameValidationError(MRGameError):
    """参数验证错误"""
    pass


class MRGameNetworkError(MRGameError):
    """网络连接错误"""
    pass


class MRGameRateLimitError(MRGameError):
    """频率限制错误"""
    pass


class MRGameInsufficientBalanceError(MRGameError):
    """余额不足错误"""
    pass