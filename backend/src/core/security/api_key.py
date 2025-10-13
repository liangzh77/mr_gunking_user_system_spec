"""
API Key认证中间件

功能：
- 验证头显Server的API Key身份
- 从请求头提取API Key
- 查询数据库验证API Key有效性
- 设置request.state.operator_id供后续使用
"""
from typing import Optional
from fastapi import Request, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

logger = structlog.get_logger(__name__)


class APIKeyAuth:
    """API Key认证依赖"""

    def __init__(self, header_name: str = "X-API-Key"):
        """
        Args:
            header_name: API Key所在的请求头名称
        """
        self.header_name = header_name

    async def __call__(
        self,
        request: Request,
        db: AsyncSession
    ) -> dict:
        """
        验证API Key并返回运营商信息

        Args:
            request: FastAPI请求对象
            db: 数据库会话

        Returns:
            包含operator_id和operator_account的字典

        Raises:
            HTTPException: API Key无效或缺失时抛出401
        """
        # 1. 提取API Key
        api_key = request.headers.get(self.header_name)
        if not api_key:
            logger.warning(
                "api_key_missing",
                path=request.url.path,
                client_ip=request.client.host
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API Key is required in X-API-Key header",
                headers={"WWW-Authenticate": "ApiKey"}
            )

        # 2. 查询数据库验证API Key
        from src.models.operator import OperatorAccount  # 延迟导入避免循环依赖

        result = await db.execute(
            select(OperatorAccount)
            .where(OperatorAccount.api_key == api_key)
            .where(OperatorAccount.deleted_at.is_(None))  # 排除已删除账户
        )
        operator = result.scalar_one_or_none()

        # 3. 验证运营商存在且账户状态正常
        if not operator:
            logger.warning(
                "api_key_invalid",
                api_key_prefix=api_key[:8] if len(api_key) >= 8 else "***",
                client_ip=request.client.host,
                path=request.url.path
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Key",
                headers={"WWW-Authenticate": "ApiKey"}
            )

        # 4. 检查账户状态
        if not operator.is_active:
            logger.warning(
                "operator_inactive",
                operator_id=str(operator.id),
                username=operator.username,
                client_ip=request.client.host
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operator account is inactive"
            )

        # 5. 检查账户锁定状态（异常检测触发）
        if operator.is_locked:
            logger.warning(
                "operator_locked",
                operator_id=str(operator.id),
                username=operator.username,
                locked_reason=operator.locked_reason,
                client_ip=request.client.host
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account locked: {operator.locked_reason or 'Security reasons'}"
            )

        # 6. 记录认证成功
        logger.info(
            "api_key_authenticated",
            operator_id=str(operator.id),
            username=operator.username,
            customer_tier=operator.customer_tier,
            client_ip=request.client.host
        )

        # 7. 设置request.state供后续中间件和端点使用
        request.state.operator_id = operator.id
        request.state.operator = operator

        return {
            "operator_id": operator.id,
            "operator_account": operator
        }


def verify_api_key_hash(plain_api_key: str, stored_hash: str) -> bool:
    """
    验证API Key哈希（使用bcrypt）

    注意：当前实现使用明文比对，生产环境应使用bcrypt.checkpw()

    Args:
        plain_api_key: 明文API Key
        stored_hash: 数据库存储的哈希值

    Returns:
        验证通过返回True，否则False
    """
    import bcrypt
    return bcrypt.checkpw(
        plain_api_key.encode('utf-8'),
        stored_hash.encode('utf-8')
    )


async def get_operator_from_api_key(
    api_key: str,
    db: AsyncSession
) -> Optional[object]:
    """
    根据API Key查询运营商账户（工具函数）

    Args:
        api_key: API Key字符串
        db: 数据库会话

    Returns:
        OperatorAccount对象或None
    """
    from src.models.operator import OperatorAccount

    result = await db.execute(
        select(OperatorAccount)
        .where(OperatorAccount.api_key == api_key)
        .where(OperatorAccount.deleted_at.is_(None))
        .where(OperatorAccount.is_active == True)
        .where(OperatorAccount.is_locked == False)
    )
    return result.scalar_one_or_none()
