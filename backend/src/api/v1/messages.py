"""运营商消息通知API endpoints

提供运营商查询和管理消息通知的接口
"""

from typing import Optional
from uuid import UUID as PyUUID
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...api.dependencies import get_db, require_operator
from ...models.operator import OperatorAccount
from ...services.message_service import MessageService
from ...schemas.message import (
    MessageListResponse,
    MessageItem,
    UnreadCountResponse,
    MessageMarkReadResponse,
    MessageMarkAllReadResponse,
    MessageDeleteResponse
)

router = APIRouter(prefix="/messages", tags=["运营商消息"])


@router.get(
    "",
    response_model=MessageListResponse,
    summary="获取消息列表",
    description="运营商查询自己的消息通知列表,支持按已读状态和消息类型筛选"
)
async def get_messages(
    is_read: Optional[bool] = Query(None, description="是否已读筛选(不传=全部)"),
    message_type: Optional[str] = Query(None, description="消息类型筛选(不传=全部)"),
    page: int = Query(1, ge=1, description="页码(从1开始)"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(require_operator)
):
    """获取运营商消息列表(分页)

    支持按以下条件筛选:
    - is_read: 已读/未读/全部
    - message_type: refund_approved, refund_rejected, invoice_approved, invoice_rejected, system_announcement
    """
    # 从token中提取operator_id
    operator_id_str = token.get("sub")
    if not operator_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token中缺少用户ID"
        )

    try:
        operator_id = PyUUID(operator_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的运营商ID格式: {operator_id_str}"
        )

    message_service = MessageService(db)

    messages, total = await message_service.get_messages(
        operator_id=operator_id,
        is_read=is_read,
        message_type=message_type,
        page=page,
        page_size=page_size
    )

    # 转换为响应格式
    items = [
        MessageItem(
            message_id=str(msg.id),
            message_type=msg.message_type,
            title=msg.title,
            content=msg.content,
            related_type=msg.related_type,
            related_id=str(msg.related_id) if msg.related_id else None,
            is_read=msg.is_read,
            read_at=msg.read_at,
            created_at=msg.created_at
        )
        for msg in messages
    ]

    return MessageListResponse(
        page=page,
        page_size=page_size,
        total=total,
        items=items
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="获取未读消息数量",
    description="获取当前运营商的未读消息数量"
)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(require_operator)
):
    """获取未读消息数量"""
    # 从token中提取operator_id
    operator_id_str = token.get("sub")
    if not operator_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token中缺少用户ID"
        )

    try:
        operator_id = PyUUID(operator_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的运营商ID格式: {operator_id_str}"
        )

    message_service = MessageService(db)

    unread_count = await message_service.get_unread_count(
        operator_id=operator_id
    )

    return UnreadCountResponse(unread_count=unread_count)


@router.post(
    "/{message_id}/read",
    response_model=MessageMarkReadResponse,
    summary="标记消息为已读",
    description="将指定消息标记为已读"
)
async def mark_message_as_read(
    message_id: str,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(require_operator)
):
    """标记消息为已读"""
    # 从token中提取operator_id
    operator_id_str = token.get("sub")
    if not operator_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token中缺少用户ID"
        )

    try:
        operator_id = PyUUID(operator_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的运营商ID格式: {operator_id_str}"
        )

    message_service = MessageService(db)

    # 转换为UUID
    try:
        message_uuid = PyUUID(message_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的消息ID格式: {message_id}"
        )

    message = await message_service.mark_as_read(
        message_id=message_uuid,
        operator_id=operator_id
    )

    await db.commit()

    return MessageMarkReadResponse(
        message_id=str(message.id),
        read_at=message.read_at
    )


@router.post(
    "/read-all",
    response_model=MessageMarkAllReadResponse,
    summary="标记所有消息为已读",
    description="将所有未读消息标记为已读"
)
async def mark_all_messages_as_read(
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(require_operator)
):
    """标记所有消息为已读"""
    # 从token中提取operator_id
    operator_id_str = token.get("sub")
    if not operator_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token中缺少用户ID"
        )

    try:
        operator_id = PyUUID(operator_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的运营商ID格式: {operator_id_str}"
        )

    message_service = MessageService(db)

    marked_count = await message_service.mark_all_as_read(
        operator_id=operator_id
    )

    await db.commit()

    return MessageMarkAllReadResponse(marked_count=marked_count)


@router.delete(
    "/{message_id}",
    response_model=MessageDeleteResponse,
    summary="删除消息",
    description="删除指定的消息"
)
async def delete_message(
    message_id: str,
    db: AsyncSession = Depends(get_db),
    token: dict = Depends(require_operator)
):
    """删除消息"""
    # 从token中提取operator_id
    operator_id_str = token.get("sub")
    if not operator_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token中缺少用户ID"
        )

    try:
        operator_id = PyUUID(operator_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的运营商ID格式: {operator_id_str}"
        )

    message_service = MessageService(db)

    # 转换为UUID
    try:
        message_uuid = PyUUID(message_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的消息ID格式: {message_id}"
        )

    await message_service.delete_message(
        message_id=message_uuid,
        operator_id=operator_id
    )

    await db.commit()

    return MessageDeleteResponse()
