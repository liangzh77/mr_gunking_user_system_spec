"""授权服务 (AuthService) - T044

此服务负责游戏授权请求的验证逻辑。

核心职责:
1. API Key验证 - 验证运营商身份
2. HMAC签名验证 - 防止请求篡改(已由中间件完成)
3. 应用授权检查 - 验证运营商是否有权使用应用
4. 玩家数量验证 - 验证玩家数在应用允许范围内
5. 运营点验证 - 验证运营点归属
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.application import Application
from ..models.authorization import OperatorAppAuthorization
from ..models.operator import OperatorAccount
from ..models.site import OperationSite


class AuthService:
    """授权验证服务

    负责游戏授权请求的各项验证逻辑。
    """

    def __init__(self, db: AsyncSession):
        """初始化授权服务

        Args:
            db: 数据库会话
        """
        self.db = db

    async def verify_operator_by_api_key(self, api_key: str) -> OperatorAccount:
        """通过API Key验证运营商身份

        验证逻辑:
        1. API Key存在且未被软删除
        2. 账户处于激活状态(is_active=True)
        3. 账户未被锁定(is_locked=False)

        Args:
            api_key: 运营商API Key

        Returns:
            OperatorAccount: 验证通过的运营商对象

        Raises:
            HTTPException 401: API Key无效或账户已注销
            HTTPException 403: 账户已锁定
        """
        # 查询运营商账户(排除软删除记录)
        stmt = select(OperatorAccount).where(
            OperatorAccount.api_key == api_key,
            OperatorAccount.deleted_at.is_(None)
        )
        result = await self.db.execute(stmt)
        operator = result.scalar_one_or_none()

        # 验证API Key存在
        if not operator:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error_code": "INVALID_API_KEY",
                    "message": "API Key不存在或已失效，请联系管理员"
                }
            )

        # 验证账户状态
        if not operator.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error_code": "ACCOUNT_DEACTIVATED",
                    "message": "账户已注销，无法使用授权服务"
                }
            )

        # 验证账户锁定状态
        if operator.is_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCOUNT_LOCKED",
                    "message": f"账户已被锁定，原因: {operator.locked_reason or '未知'}",
                    "details": {
                        "locked_at": operator.locked_at.isoformat() if operator.locked_at else None,
                        "locked_reason": operator.locked_reason
                    }
                }
            )

        return operator

    async def verify_site_ownership(
        self,
        site_id: UUID,
        operator_id: UUID
    ) -> OperationSite:
        """验证运营点归属

        确保运营点属于当前运营商。

        Args:
            site_id: 运营点ID
            operator_id: 运营商ID

        Returns:
            OperationSite: 验证通过的运营点对象

        Raises:
            HTTPException 404: 运营点不存在
            HTTPException 403: 运营点不属于该运营商
        """
        stmt = select(OperationSite).where(
            OperationSite.id == site_id,
            OperationSite.deleted_at.is_(None)
        )
        result = await self.db.execute(stmt)
        site = result.scalar_one_or_none()

        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "SITE_NOT_FOUND",
                    "message": f"运营点不存在: {site_id}"
                }
            )

        if site.operator_id != operator_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "SITE_NOT_OWNED",
                    "message": "该运营点不属于您，无权使用"
                }
            )

        if not site.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "SITE_INACTIVE",
                    "message": "该运营点已停用，无法发起授权"
                }
            )

        return site

    async def verify_application_authorization(
        self,
        application_id: UUID,
        operator_id: UUID
    ) -> tuple[Application, OperatorAppAuthorization]:
        """验证应用授权状态

        验证逻辑:
        1. 应用存在且处于上架状态
        2. 运营商已被授权使用该应用
        3. 授权未过期

        Args:
            application_id: 应用ID
            operator_id: 运营商ID

        Returns:
            tuple[Application, OperatorAppAuthorization]: (应用对象, 授权关系对象)

        Raises:
            HTTPException 404: 应用不存在
            HTTPException 403: 应用未授权或授权已过期
        """
        # 查询应用
        stmt = select(Application).where(Application.id == application_id)
        result = await self.db.execute(stmt)
        application = result.scalar_one_or_none()

        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "APP_NOT_FOUND",
                    "message": f"应用不存在: {application_id}"
                }
            )

        if not application.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "APP_INACTIVE",
                    "message": f"应用 '{application.app_name}' 已下架，暂不可用"
                }
            )

        # 查询授权关系
        stmt = select(OperatorAppAuthorization).where(
            OperatorAppAuthorization.operator_id == operator_id,
            OperatorAppAuthorization.application_id == application_id,
            OperatorAppAuthorization.is_active == True
        )
        result = await self.db.execute(stmt)
        authorization = result.scalar_one_or_none()

        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "APP_NOT_AUTHORIZED",
                    "message": f"您未被授权使用此应用，请联系管理员申请授权",
                    "details": {
                        "app_id": str(application_id),
                        "app_name": application.app_name
                    }
                }
            )

        # 验证授权是否过期
        if authorization.expires_at and authorization.expires_at < datetime.now(authorization.expires_at.tzinfo):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "AUTHORIZATION_EXPIRED",
                    "message": f"应用授权已过期，过期时间: {authorization.expires_at.isoformat()}",
                    "details": {
                        "app_name": application.app_name,
                        "expired_at": authorization.expires_at.isoformat()
                    }
                }
            )

        return application, authorization

    async def verify_player_count(
        self,
        player_count: int,
        application: Application
    ) -> None:
        """验证玩家数量是否在应用允许范围内

        Args:
            player_count: 请求的玩家数量
            application: 应用对象

        Raises:
            HTTPException 400: 玩家数量超出范围
        """
        if player_count < application.min_players or player_count > application.max_players:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "PLAYER_COUNT_OUT_OF_RANGE",
                    "message": f"玩家数量必须在{application.min_players}-{application.max_players}之间，当前请求: {player_count}人",
                    "details": {
                        "min_players": application.min_players,
                        "max_players": application.max_players,
                        "requested_players": player_count
                    }
                }
            )

    async def verify_session_id_format(self, session_id: str, operator_id: UUID) -> None:
        """验证会话ID格式 (FR-061)

        格式规则: {operatorId}_{timestamp}_{random16}
        - operatorId: 必须与当前运营商ID匹配
        - timestamp: Unix时间戳(秒)，不能早于当前时间5分钟以上
        - random16: 16位随机字符串

        Args:
            session_id: 会话ID
            operator_id: 运营商ID

        Raises:
            HTTPException 400: 会话ID格式错误
        """
        import re
        from datetime import datetime, timedelta

        # 验证基本格式
        pattern = r'^([a-zA-Z0-9\-]+)_(\d+)_([a-zA-Z0-9]{16})$'
        match = re.match(pattern, session_id)

        if not match:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_SESSION_ID_FORMAT",
                    "message": "会话ID格式错误，应为: {operatorId}_{timestamp}_{random16}",
                    "details": {
                        "session_id": session_id,
                        "expected_format": "{operatorId}_{timestamp}_{random16}"
                    }
                }
            )

        session_operator_id, timestamp_str, random_part = match.groups()

        # 验证operator_id匹配
        if session_operator_id != str(operator_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "SESSION_ID_OPERATOR_MISMATCH",
                    "message": "会话ID中的运营商ID与当前运营商不匹配",
                    "details": {
                        "session_operator_id": session_operator_id,
                        "current_operator_id": str(operator_id)
                    }
                }
            )

        # 验证时间戳(不能早于当前时间5分钟以上)
        try:
            session_timestamp = int(timestamp_str)
            current_timestamp = int(datetime.utcnow().timestamp())
            time_diff = current_timestamp - session_timestamp

            if time_diff > 300:  # 5分钟 = 300秒
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error_code": "SESSION_ID_EXPIRED",
                        "message": "会话ID时间戳已过期(超过5分钟)",
                        "details": {
                            "session_timestamp": session_timestamp,
                            "current_timestamp": current_timestamp,
                            "time_diff_seconds": time_diff,
                            "max_allowed_seconds": 300
                        }
                    }
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_SESSION_ID_TIMESTAMP",
                    "message": "会话ID中的时间戳格式错误"
                }
            )

        # 验证随机数长度
        if len(random_part) != 16:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_SESSION_ID_RANDOM",
                    "message": "会话ID随机部分必须为16位",
                    "details": {
                        "random_part": random_part,
                        "length": len(random_part),
                        "expected_length": 16
                    }
                }
            )
