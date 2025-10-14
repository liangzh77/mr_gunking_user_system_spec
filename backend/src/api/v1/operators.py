"""运营商个人信息管理API接口 (T069, T070)

此模块定义运营商个人信息相关的API端点。

端点:
- GET /v1/operators/me - 获取当前运营商个人信息 (T069)
- PUT /v1/operators/me - 更新当前运营商个人信息 (T070)

认证方式:
- JWT Token认证 (Authorization: Bearer {token})
- 用户类型要求: operator
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_db, require_operator
from ...schemas.operator import (
    OperatorProfile,
    OperatorUpdateRequest,
)
from ...services.operator import OperatorService

router = APIRouter(prefix="/operators", tags=["运营商"])


@router.get(
    "/me",
    response_model=OperatorProfile,
    status_code=status.HTTP_200_OK,
    responses={
        401: {
            "description": "未认证或Token无效/过期"
        },
        403: {
            "description": "权限不足(非运营商用户)"
        },
        404: {
            "description": "运营商不存在"
        }
    },
    summary="获取个人信息",
    description="""
    获取当前登录运营商的完整个人信息。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: operator

    **响应数据**:
    - operator_id: 运营商ID (UUID)
    - username: 用户名
    - name: 真实姓名或公司名
    - phone: 联系电话
    - email: 邮箱地址
    - category: 客户分类 (trial/normal/vip)
    - balance: 账户余额(字符串格式,精确到分)
    - is_active: 账户状态 (true=正常, false=已注销)
    - is_locked: 锁定状态 (true=已锁定, false=正常)
    - last_login_at: 最近登录时间 (可能为null)
    - created_at: 创建时间

    **注意事项**:
    - 不返回敏感信息如密码hash、API Key
    - balance为字符串避免浮点精度问题
    """
)
async def get_profile(
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> OperatorProfile:
    """获取运营商个人信息API (T069)

    Args:
        token: JWT Token payload (包含sub=operator_id, user_type=operator)
        db: 数据库会话

    Returns:
        OperatorProfile: 运营商详细信息

    Raises:
        HTTPException 401: 未认证或Token无效
        HTTPException 403: 权限不足
        HTTPException 404: 运营商不存在
    """
    operator_service = OperatorService(db)

    # 从token中提取operator_id
    operator_id_str = token.get("sub")
    if not operator_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "INVALID_TOKEN",
                "message": "Token中缺少用户ID"
            }
        )

    try:
        operator_id = UUID(operator_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_OPERATOR_ID",
                "message": f"无效的运营商ID格式: {operator_id_str}"
            }
        )

    # 调用服务层获取个人信息
    try:
        profile = await operator_service.get_profile(operator_id)
        return profile

    except HTTPException:
        # 重新抛出服务层异常(如404)
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"获取个人信息失败: {str(e)}"
            }
        )


@router.put(
    "/me",
    response_model=OperatorProfile,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "请求参数错误(字段格式不正确)"
        },
        401: {
            "description": "未认证或Token无效/过期"
        },
        403: {
            "description": "权限不足(非运营商用户)"
        },
        404: {
            "description": "运营商不存在"
        }
    },
    summary="更新个人信息",
    description="""
    更新当前登录运营商的个人信息。

    **认证要求**:
    - Authorization: Bearer {JWT_TOKEN}
    - 用户类型: operator

    **允许更新的字段** (所有字段都是可选的):
    - name: 真实姓名或公司名 (2-50字符)
    - phone: 联系电话 (11位中国手机号)
    - email: 邮箱地址 (标准邮箱格式)

    **不允许更新的字段**:
    - username: 用户名 (创建后不可修改)
    - password: 密码 (请使用专用的修改密码接口)
    - balance: 余额 (通过充值/扣费接口修改)
    - category: 客户分类 (由管理员或系统自动调整)
    - is_active, is_locked: 账户状态 (由管理员或系统管理)

    **部分更新**:
    - 可以只提供需要更新的字段
    - 未提供的字段保持不变
    - 空body不会更新任何字段

    **响应数据**:
    - 返回更新后的完整个人信息 (OperatorProfile)
    """
)
async def update_profile(
    request: OperatorUpdateRequest,
    token: dict = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
) -> OperatorProfile:
    """更新运营商个人信息API (T070)

    Args:
        request: 更新请求数据 (name, phone, email都是可选)
        token: JWT Token payload
        db: 数据库会话

    Returns:
        OperatorProfile: 更新后的完整个人信息

    Raises:
        HTTPException 400: 参数格式错误
        HTTPException 401: 未认证或Token无效
        HTTPException 403: 权限不足
        HTTPException 404: 运营商不存在
    """
    operator_service = OperatorService(db)

    # 从token中提取operator_id
    operator_id_str = token.get("sub")
    if not operator_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "INVALID_TOKEN",
                "message": "Token中缺少用户ID"
            }
        )

    try:
        operator_id = UUID(operator_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_OPERATOR_ID",
                "message": f"无效的运营商ID格式: {operator_id_str}"
            }
        )

    # 调用服务层更新个人信息
    try:
        updated_profile = await operator_service.update_profile(operator_id, request)
        return updated_profile

    except HTTPException:
        # 重新抛出服务层异常
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": f"更新个人信息失败: {str(e)}"
            }
        )
