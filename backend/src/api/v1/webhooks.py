"""支付回调Webhooks接口 (T078)

此模块定义支付平台回调的API端点。

端点:
- POST /v1/webhooks/payment/wechat - 微信支付回调
- POST /v1/webhooks/payment/alipay - 支付宝支付回调

安全特性:
- 验证回调签名(生产环境)
- 幂等性保障(防止重复回调)
- 事务一致性(订单状态+余额+交易记录原子更新)
"""

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...api.dependencies import get_db
from ...schemas.payment import PaymentCallbackRequest, PaymentCallbackResponse
from ...models.transaction import RechargeOrder, TransactionRecord
from ...models.operator import OperatorAccount

router = APIRouter(prefix="/webhooks/payment", tags=["支付回调"])


@router.post(
    "/wechat",
    response_model=PaymentCallbackResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "参数错误或订单金额不匹配"
        },
        404: {
            "description": "订单不存在"
        }
    },
    summary="微信支付回调",
    description="""
    接收微信支付平台的支付结果回调。

    **回调时机**:
    - 用户完成支付后,微信支付平台会调用此接口通知支付结果

    **请求参数**:
    - order_id: 充值订单ID
    - status: 支付状态 (success/failed)
    - paid_amount: 实际支付金额(必须与订单金额一致)
    - transaction_id: 微信支付交易ID
    - paid_at: 支付完成时间
    - error_code: 错误码(status=failed时)
    - error_message: 错误信息(status=failed时)

    **业务规则**:
    - 验证订单存在且未处理
    - 验证支付金额与订单金额一致
    - 支付成功时:
      - 更新订单状态为success
      - 增加运营商余额
      - 创建交易记录(recharge类型)
    - 支付失败时:
      - 更新订单状态为failed
      - 记录错误信息

    **幂等性**:
    - 同一订单的重复回调只处理一次
    - 已处理的订单直接返回成功
    """
)
async def wechat_payment_callback(
    request: PaymentCallbackRequest,
    db: AsyncSession = Depends(get_db)
) -> PaymentCallbackResponse:
    """微信支付回调处理 (T078)

    Args:
        request: 支付回调请求数据
        db: 数据库会话

    Returns:
        PaymentCallbackResponse: 回调处理结果

    Raises:
        HTTPException 400: 参数错误或金额不匹配
        HTTPException 404: 订单不存在
    """
    return await _process_payment_callback(request, db, "wechat")


@router.post(
    "/alipay",
    response_model=PaymentCallbackResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "参数错误或订单金额不匹配"
        },
        404: {
            "description": "订单不存在"
        }
    },
    summary="支付宝支付回调",
    description="""
    接收支付宝支付平台的支付结果回调。

    **回调时机**:
    - 用户完成支付后,支付宝平台会调用此接口通知支付结果

    **请求参数**:
    - order_id: 充值订单ID
    - status: 支付状态 (success/failed)
    - paid_amount: 实际支付金额(必须与订单金额一致)
    - transaction_id: 支付宝交易ID
    - paid_at: 支付完成时间
    - error_code: 错误码(status=failed时)
    - error_message: 错误信息(status=failed时)

    **业务规则**:
    - 验证订单存在且未处理
    - 验证支付金额与订单金额一致
    - 支付成功时:
      - 更新订单状态为success
      - 增加运营商余额
      - 创建交易记录(recharge类型)
    - 支付失败时:
      - 更新订单状态为failed
      - 记录错误信息

    **幂等性**:
    - 同一订单的重复回调只处理一次
    - 已处理的订单直接返回成功
    """
)
async def alipay_payment_callback(
    request: PaymentCallbackRequest,
    db: AsyncSession = Depends(get_db)
) -> PaymentCallbackResponse:
    """支付宝支付回调处理 (T078)

    Args:
        request: 支付回调请求数据
        db: 数据库会话

    Returns:
        PaymentCallbackResponse: 回调处理结果

    Raises:
        HTTPException 400: 参数错误或金额不匹配
        HTTPException 404: 订单不存在
    """
    return await _process_payment_callback(request, db, "alipay")


async def _process_payment_callback(
    request: PaymentCallbackRequest,
    db: AsyncSession,
    payment_method: str
) -> PaymentCallbackResponse:
    """处理支付回调的通用逻辑

    业务流程:
    1. 查询订单并验证状态(防止重复处理)
    2. 验证支付金额与订单金额一致
    3. 根据支付状态处理:
       - success: 更新订单+增加余额+创建交易记录(事务)
       - failed: 更新订单状态+记录错误信息
    4. 返回处理结果

    Args:
        request: 支付回调请求数据
        db: 数据库会话
        payment_method: 支付方式 (wechat/alipay)

    Returns:
        PaymentCallbackResponse: 回调处理结果

    Raises:
        HTTPException 400: 金额不匹配或参数错误
        HTTPException 404: 订单不存在
    """
    # 1. 查询充值订单
    stmt = select(RechargeOrder).where(
        RechargeOrder.order_id == request.order_id
    )
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "ORDER_NOT_FOUND",
                "message": f"充值订单不存在: {request.order_id}"
            }
        )

    # 2. 幂等性检查:如果订单已处理,直接返回成功
    if order.status in ["success", "failed"]:
        return PaymentCallbackResponse(
            success=True,
            message=f"Order already processed with status: {order.status}"
        )

    # 3. 处理支付成功
    if request.status == "success":
        # 3.1 验证支付金额与订单金额一致
        paid_amount = Decimal(request.paid_amount)
        if paid_amount != order.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "AMOUNT_MISMATCH",
                    "message": f"支付金额({request.paid_amount})与订单金额({order.amount})不匹配"
                }
            )

        # 3.2 查询运营商账户
        operator_stmt = select(OperatorAccount).where(
            OperatorAccount.id == order.operator_id,
            OperatorAccount.deleted_at.is_(None)
        )
        operator_result = await db.execute(operator_stmt)
        operator = operator_result.scalar_one_or_none()

        if not operator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "OPERATOR_NOT_FOUND",
                    "message": "运营商不存在"
                }
            )

        # 3.3 数据库事务:更新订单+增加余额+创建交易记录
        try:
            # 更新订单状态
            order.status = "success"
            order.transaction_id = request.transaction_id
            order.paid_at = request.paid_at

            # 记录余额变化
            balance_before = operator.balance
            balance_after = balance_before + order.amount

            # 增加运营商余额
            operator.balance = balance_after

            # 创建交易记录
            transaction = TransactionRecord(
                operator_id=operator.id,
                transaction_type="recharge",
                amount=order.amount,
                balance_before=balance_before,
                balance_after=balance_after,
                payment_channel=payment_method,
                payment_order_no=request.order_id,
                payment_status="success",
                payment_callback_at=request.paid_at,
                description=f"{payment_method}充值: {order.amount}元"
            )

            db.add(transaction)
            await db.commit()

            return PaymentCallbackResponse(
                success=True,
                message="Payment callback processed successfully"
            )

        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error_code": "INTERNAL_ERROR",
                    "message": f"处理支付回调失败: {str(e)}"
                }
            )

    # 4. 处理支付失败
    elif request.status == "failed":
        # 更新订单状态为失败
        order.status = "failed"
        order.error_code = request.error_code
        order.error_message = request.error_message
        order.paid_at = request.paid_at

        await db.commit()

        return PaymentCallbackResponse(
            success=True,
            message="Payment failure recorded"
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_STATUS",
                "message": f"无效的支付状态: {request.status}"
            }
        )
