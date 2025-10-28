"""
HMAC签名验证中间件

功能：
- 验证请求的HMAC-SHA256签名防止篡改
- 支持时间戳验证防重放攻击
- 按照签名规范构造待签名字符串
"""
import hmac
import hashlib
import time
from typing import Optional
from fastapi import Request, HTTPException, status
import structlog

logger = structlog.get_logger(__name__)


class HMACSignature:
    """HMAC签名验证依赖"""

    def __init__(
        self,
        signature_header: str = "X-Signature",
        timestamp_header: str = "X-Timestamp",
        nonce_header: str = "X-Nonce",
        max_timestamp_diff: int = 300  # 5分钟
    ):
        """
        Args:
            signature_header: 签名所在的请求头名称
            timestamp_header: 时间戳所在的请求头名称
            nonce_header: 随机数所在的请求头名称
            max_timestamp_diff: 允许的最大时间戳偏差（秒）
        """
        self.signature_header = signature_header
        self.timestamp_header = timestamp_header
        self.nonce_header = nonce_header
        self.max_timestamp_diff = max_timestamp_diff

    async def __call__(self, request: Request) -> dict:
        """
        验证HMAC签名

        签名算法：
        1. 构造待签名字符串：HTTP_METHOD + "\n" + REQUEST_PATH + "\n" + TIMESTAMP + "\n" + NONCE + "\n" + BODY
        2. 使用API Secret计算HMAC-SHA256
        3. 对比请求头中的签名

        Args:
            request: FastAPI请求对象

        Returns:
            包含验证结果的字典

        Raises:
            HTTPException: 签名验证失败时抛出401
        """
        # 1. 提取必需的请求头
        signature = request.headers.get(self.signature_header)
        timestamp = request.headers.get(self.timestamp_header)
        nonce = request.headers.get(self.nonce_header)

        # 2. 验证必需字段存在
        if not signature:
            logger.warning(
                "hmac_signature_missing",
                path=request.url.path,
                client_ip=request.client.host
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Missing {self.signature_header} header"
            )

        if not timestamp:
            logger.warning(
                "hmac_timestamp_missing",
                path=request.url.path,
                client_ip=request.client.host
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Missing {self.timestamp_header} header"
            )

        if not nonce:
            logger.warning(
                "hmac_nonce_missing",
                path=request.url.path,
                client_ip=request.client.host
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Missing {self.nonce_header} header"
            )

        # 3. 验证时间戳（防重放攻击）
        try:
            request_timestamp = int(timestamp)
        except ValueError:
            logger.warning(
                "hmac_timestamp_invalid",
                timestamp=timestamp,
                path=request.url.path
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid timestamp format (must be Unix timestamp)"
            )

        current_timestamp = int(time.time())
        timestamp_diff = abs(current_timestamp - request_timestamp)

        if timestamp_diff > self.max_timestamp_diff:
            logger.warning(
                "hmac_timestamp_expired",
                timestamp_diff=timestamp_diff,
                max_allowed=self.max_timestamp_diff,
                path=request.url.path
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Request timestamp expired (max {self.max_timestamp_diff}s difference)"
            )

        # 4. 验证Nonce长度（防止过短的随机数）
        if len(nonce) < 16:
            logger.warning(
                "hmac_nonce_too_short",
                nonce_length=len(nonce),
                path=request.url.path
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nonce must be at least 16 characters"
            )

        # 5. 获取API Secret（从request.state.operator获取，需先执行API Key认证）
        if not hasattr(request.state, "operator"):
            logger.error(
                "hmac_no_operator",
                path=request.url.path,
                detail="API Key authentication must be performed before HMAC verification"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication order error"
            )

        operator = request.state.operator
        api_secret = operator.api_key  # 注意：生产环境应使用单独的api_secret字段

        # 6. 读取请求体
        body = await request.body()
        body_str = body.decode('utf-8') if body else ""

        # 7. 构造待签名字符串
        sign_string = self._build_sign_string(
            method=request.method,
            path=str(request.url.path),
            timestamp=timestamp,
            nonce=nonce,
            body=body_str
        )

        # 8. 计算期望的签名
        expected_signature = self._compute_hmac(api_secret, sign_string)

        # 9. 对比签名（恒定时间比较防时序攻击）
        if not hmac.compare_digest(signature, expected_signature):
            logger.warning(
                "hmac_signature_mismatch",
                operator_id=str(operator.id),
                expected=expected_signature[:16] + "...",
                received=signature[:16] + "...",
                path=request.url.path
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid HMAC signature"
            )

        # 10. 验证成功
        logger.info(
            "hmac_verified",
            operator_id=str(operator.id),
            timestamp=timestamp,
            path=request.url.path
        )

        return {
            "verified": True,
            "timestamp": request_timestamp,
            "nonce": nonce
        }

    def _build_sign_string(
        self,
        method: str,
        path: str,
        timestamp: str,
        nonce: str,
        body: str
    ) -> str:
        """
        构造待签名字符串

        格式: METHOD\nPATH\nTIMESTAMP\nNONCE\nBODY

        Args:
            method: HTTP方法（GET/POST等）
            path: 请求路径（不含query参数）
            timestamp: Unix时间戳字符串
            nonce: 随机数
            body: 请求体内容

        Returns:
            待签名字符串
        """
        return f"{method}\n{path}\n{timestamp}\n{nonce}\n{body}"

    def _compute_hmac(self, secret: str, message: str) -> str:
        """
        计算HMAC-SHA256签名

        Args:
            secret: 密钥（API Secret）
            message: 待签名消息

        Returns:
            十六进制签名字符串
        """
        return hmac.new(
            secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()


def generate_signature(
    method: str,
    path: str,
    timestamp: int,
    nonce: str,
    body: str,
    api_secret: str
) -> str:
    """
    生成HMAC签名（工具函数，用于客户端SDK）

    Args:
        method: HTTP方法
        path: 请求路径
        timestamp: Unix时间戳
        nonce: 随机数
        body: 请求体
        api_secret: API密钥

    Returns:
        十六进制签名字符串

    Example:
        >>> signature = generate_signature(
        ...     method="POST",
        ...     path="/v1/auth/game/authorize",
        ...     timestamp=1728540000,
        ...     nonce="a1b2c3d4e5f6g7h8",
        ...     body='{"app_code":"space_adventure","player_count":5}',
        ...     api_secret="your_api_secret_here"
        ... )
    """
    sign_string = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body}"
    return hmac.new(
        api_secret.encode('utf-8'),
        sign_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
