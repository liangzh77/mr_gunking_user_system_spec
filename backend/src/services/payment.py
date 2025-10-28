"""支付服务 (PaymentService) - T063

此服务提供支付集成和充值事务处理的核心业务逻辑:
1. 微信支付集成 - 生成支付订单和二维码
2. 支付宝集成 - 生成支付订单和二维码
3. 支付回调验证 - 验证签名和金额一致性
4. 充值事务处理 - 原子更新订单+余额+交易记录

安全特性:
- 支付回调签名验证 (生产环境必须启用)
- 幂等性保障 (防止重复充值)
- 事务一致性 (订单+余额+交易记录原子更新)
- 金额验证 (支付金额必须与订单金额一致)
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID
import time
import hashlib
import hmac

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.operator import OperatorAccount
from ..models.transaction import RechargeOrder, TransactionRecord


class PaymentService:
    """支付服务类

    提供微信支付、支付宝支付集成和充值事务处理功能
    """

    def __init__(self, db: AsyncSession):
        """初始化服务

        Args:
            db: 数据库会话
        """
        self.db = db

    async def create_recharge_order(
        self,
        operator_id: UUID,
        amount: Decimal,
        payment_method: str
    ) -> RechargeOrder:
        """创建充值订单 (T071辅助)

        业务规则:
        - 充值金额已由schema验证(10-10000元,最多2位小数)
        - 生成唯一订单ID: ord_recharge_<timestamp>_<uuid>
        - 订单有效期: 30分钟
        - 调用支付平台API生成支付二维码(模拟)
        - 订单状态初始为pending

        Args:
            operator_id: 运营商ID
            amount: 充值金额
            payment_method: 支付方式 (wechat/alipay)

        Returns:
            RechargeOrder: 充值订单对象

        Raises:
            HTTPException 404: 运营商不存在
            HTTPException 500: 支付平台调用失败
        """
        # 1. 验证运营商存在
        operator_stmt = select(OperatorAccount).where(
            OperatorAccount.id == operator_id,
            OperatorAccount.deleted_at.is_(None)
        )
        operator_result = await self.db.execute(operator_stmt)
        operator = operator_result.scalar_one_or_none()

        if not operator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "OPERATOR_NOT_FOUND",
                    "message": "运营商不存在"
                }
            )

        # 2. 生成订单ID: ord_recharge_<timestamp>_<short_uuid>
        from uuid import uuid4
        timestamp = int(time.time())
        short_uuid = str(uuid4())[:8]
        order_id = f"ord_recharge_{timestamp}_{short_uuid}"

        # 3. 计算订单过期时间(30分钟后)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

        # 4. 调用支付平台API生成支付二维码
        # 实际环境中应调用微信/支付宝SDK,这里模拟返回
        qr_code_url, payment_url = await self._generate_payment_qr(
            order_id=order_id,
            amount=amount,
            payment_method=payment_method
        )

        # 5. 创建充值订单记录
        recharge_order = RechargeOrder(
            order_id=order_id,
            operator_id=operator_id,
            amount=amount,
            payment_method=payment_method,
            qr_code_url=qr_code_url,
            payment_url=payment_url,
            status="pending",
            expires_at=expires_at
        )

        self.db.add(recharge_order)
        await self.db.commit()
        await self.db.refresh(recharge_order)

        return recharge_order

    async def _generate_payment_qr(
        self,
        order_id: str,
        amount: Decimal,
        payment_method: str
    ) -> tuple[str, str]:
        """生成支付二维码URL和支付页面URL

        实际环境中应调用微信/支付宝SDK生成真实二维码。
        这里模拟返回示例URL。

        Args:
            order_id: 订单ID
            amount: 支付金额
            payment_method: 支付方式 (wechat/alipay)

        Returns:
            tuple[str, str]: (二维码URL, 支付页面URL)

        Raises:
            HTTPException 500: 支付平台调用失败
        """
        # TODO: 集成真实支付平台SDK
        # 微信支付: from wechatpayv3 import WeChatPay
        # 支付宝: from alipay import AliPay

        # 模拟生成支付URL
        if payment_method == "wechat":
            qr_code_url = f"https://payment.wechat.com/qr/{order_id}"
            payment_url = f"https://payment.wechat.com/pay/{order_id}"
        elif payment_method == "alipay":
            qr_code_url = f"https://qr.alipay.com/{order_id}"
            payment_url = f"https://openapi.alipay.com/gateway.do?order_id={order_id}"
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error_code": "INVALID_PAYMENT_METHOD",
                    "message": f"不支持的支付方式: {payment_method}"
                }
            )

        return qr_code_url, payment_url

    async def process_payment_callback(
        self,
        order_id: str,
        status_value: str,
        paid_amount: Decimal,
        transaction_id: str,
        paid_at: datetime,
        payment_method: str,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        signature: Optional[str] = None
    ) -> dict:
        """处理支付回调 (T078辅助)

        业务流程:
        1. 验证回调签名 (生产环境必须验证)
        2. 查询订单并验证状态(防止重复处理)
        3. 验证支付金额与订单金额一致
        4. 根据支付状态处理:
           - success: 更新订单+增加余额+创建交易记录(事务)
           - failed: 更新订单状态+记录错误信息
        5. 返回处理结果

        Args:
            order_id: 充值订单ID
            status_value: 支付状态 (success/failed)
            paid_amount: 实际支付金额
            transaction_id: 支付平台交易ID
            paid_at: 支付完成时间
            payment_method: 支付方式 (wechat/alipay)
            error_code: 错误码(失败时)
            error_message: 错误信息(失败时)
            signature: 回调签名

        Returns:
            dict: {
                "success": bool,
                "message": str
            }

        Raises:
            HTTPException 400: 金额不匹配或签名验证失败
            HTTPException 404: 订单不存在
            HTTPException 500: 数据库事务失败
        """
        # 1. 验证回调签名 (生产环境必须启用)
        # TODO: 实现真实签名验证逻辑
        # if signature:
        #     await self._verify_payment_signature(
        #         order_id, paid_amount, transaction_id, signature, payment_method
        #     )

        # 2. 查询充值订单
        stmt = select(RechargeOrder).where(
            RechargeOrder.order_id == order_id
        )
        result = await self.db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "ORDER_NOT_FOUND",
                    "message": f"充值订单不存在: {order_id}"
                }
            )

        # 3. 幂等性检查:如果订单已处理,直接返回成功
        if order.status in ["success", "failed"]:
            return {
                "success": True,
                "message": f"Order already processed with status: {order.status}"
            }

        # 4. 处理支付成功
        if status_value == "success":
            # 4.1 验证支付金额与订单金额一致
            if paid_amount != order.amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error_code": "AMOUNT_MISMATCH",
                        "message": f"支付金额({paid_amount})与订单金额({order.amount})不匹配"
                    }
                )

            # 4.2 查询运营商账户
            operator_stmt = select(OperatorAccount).where(
                OperatorAccount.id == order.operator_id,
                OperatorAccount.deleted_at.is_(None)
            )
            operator_result = await self.db.execute(operator_stmt)
            operator = operator_result.scalar_one_or_none()

            if not operator:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error_code": "OPERATOR_NOT_FOUND",
                        "message": "运营商不存在"
                    }
                )

            # 4.3 数据库事务:更新订单+增加余额+创建交易记录
            try:
                # 更新订单状态
                order.status = "success"
                order.transaction_id = transaction_id
                order.paid_at = paid_at

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
                    payment_order_no=order_id,
                    payment_status="success",
                    payment_callback_at=paid_at,
                    description=f"{payment_method}充值: {order.amount}元"
                )

                self.db.add(transaction)
                await self.db.commit()

                return {
                    "success": True,
                    "message": "Payment callback processed successfully"
                }

            except Exception as e:
                await self.db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error_code": "TRANSACTION_FAILED",
                        "message": f"处理支付回调失败: {str(e)}"
                    }
                )

        # 5. 处理支付失败
        elif status_value == "failed":
            # 更新订单状态为失败
            order.status = "failed"
            order.error_code = error_code
            order.error_message = error_message
            order.paid_at = paid_at

            await self.db.commit()

            return {
                "success": True,
                "message": "Payment failure recorded"
            }

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_STATUS",
                    "message": f"无效的支付状态: {status_value}"
                }
            )

    async def _verify_payment_signature(
        self,
        order_id: str,
        paid_amount: Decimal,
        transaction_id: str,
        signature: str,
        payment_method: str
    ) -> None:
        """验证支付回调签名

        防止伪造回调攻击,生产环境必须启用此验证。

        Args:
            order_id: 订单ID
            paid_amount: 支付金额
            transaction_id: 交易ID
            signature: 回调签名
            payment_method: 支付方式

        Raises:
            HTTPException 400: 签名验证失败
        """
        # TODO: 实现真实签名验证逻辑
        # 微信支付: 使用API密钥进行HMAC-SHA256签名验证
        # 支付宝: 使用RSA公钥验证签名

        # 示例:微信支付签名验证逻辑
        # if payment_method == "wechat":
        #     from ..core.config import settings
        #     api_key = settings.WECHAT_PAY_API_KEY
        #     sign_string = f"order_id={order_id}&paid_amount={paid_amount}&transaction_id={transaction_id}&key={api_key}"
        #     expected_signature = hashlib.md5(sign_string.encode()).hexdigest().upper()
        #
        #     if signature != expected_signature:
        #         raise HTTPException(
        #             status_code=status.HTTP_400_BAD_REQUEST,
        #             detail={
        #                 "error_code": "INVALID_SIGNATURE",
        #                 "message": "支付回调签名验证失败"
        #             }
        #         )

        pass  # 模拟环境跳过签名验证
