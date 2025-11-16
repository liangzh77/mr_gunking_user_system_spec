"""Common API endpoints (captcha, health check, etc.)."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from ...core import get_redis
from ...utils.captcha import generate_captcha, image_to_base64
from ...utils.sms import get_sms_service

router = APIRouter(prefix="/common", tags=["common"])


# ==================== Request/Response Models ====================

class SendSMSRequest(BaseModel):
    """发送短信验证码请求"""
    phone: str = Field(..., min_length=11, max_length=11, description="手机号")


class SendSMSResponse(BaseModel):
    """发送短信验证码响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="提示信息")
    sms_key: str = Field(..., description="短信验证码key,用于后续验证")


@router.get("/captcha")
async def get_captcha(
    redis: Redis = Depends(get_redis)
):
    """Generate captcha image.

    Returns:
        CaptchaResponse with captcha_key and base64 encoded image
    """
    captcha_key, captcha_text, image_bytes = generate_captcha()

    # Store captcha in Redis with 5 minutes expiration
    await redis.setex(
        f"captcha:{captcha_key}",
        300,  # 5 minutes
        captcha_text.upper()  # Store as uppercase for case-insensitive comparison
    )

    # Convert image to base64
    image_base64 = image_to_base64(image_bytes)

    return {
        "captcha_key": captcha_key,
        "image_base64": image_base64
    }


@router.post("/sms/send", response_model=SendSMSResponse)
async def send_sms_code(
    request: SendSMSRequest,
    redis: Redis = Depends(get_redis)
):
    """发送短信验证码

    Args:
        request: 发送短信请求(包含手机号)
        redis: Redis连接

    Returns:
        SendSMSResponse: 包含sms_key用于后续验证

    Raises:
        HTTPException 400: 手机号格式错误
        HTTPException 429: 发送频率过高
        HTTPException 500: 短信发送失败
    """
    import re
    import uuid

    phone = request.phone

    # 验证手机号格式
    if not re.match(r"^1[3-9]\d{9}$", phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_PHONE",
                "message": "手机号格式错误"
            }
        )

    # 检查发送频率限制(60秒内只能发送一次)
    rate_limit_key = f"sms:rate_limit:{phone}"
    if await redis.exists(rate_limit_key):
        ttl = await redis.ttl(rate_limit_key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error_code": "TOO_FREQUENT",
                "message": f"发送过于频繁,请{ttl}秒后再试"
            }
        )

    try:
        # 生成验证码
        sms_service = get_sms_service()
        code = sms_service.generate_code(6)  # 6位数字验证码

        # 发送短信
        await sms_service.send_verification_code(phone, code)

        # 生成sms_key
        sms_key = str(uuid.uuid4())

        # 存储验证码到Redis (5分钟过期)
        await redis.setex(
            f"sms:code:{sms_key}",
            300,  # 5 minutes
            f"{phone}:{code}"  # 存储格式: "手机号:验证码"
        )

        # 设置发送频率限制 (60秒)
        await redis.setex(rate_limit_key, 60, "1")

        return SendSMSResponse(
            success=True,
            message="验证码已发送,5分钟内有效",
            sms_key=sms_key
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "SMS_SEND_FAILED",
                "message": f"短信发送失败: {str(e)}"
            }
        )


async def verify_captcha(
    captcha_key: str,
    captcha_code: str,
    redis: Redis
) -> bool:
    """Verify captcha code.

    Args:
        captcha_key: Captcha key from generation
        captcha_code: User input captcha code
        redis: Redis connection

    Returns:
        True if captcha is valid, False otherwise
    """
    import os

    # 开发/测试环境：允许跳过验证码或使用绕过码
    # 生产环境：必须提供有效验证码
    environment = os.getenv("ENVIRONMENT", "production").lower()
    if environment in ["development", "testing"]:
        # 开发/测试环境可以不输入验证码，或使用绕过码 "0000"
        if not captcha_code or captcha_code == "0000":
            return True

    if not captcha_key or not captcha_code:
        return False

    # Get stored captcha from Redis
    stored_captcha = await redis.get(f"captcha:{captcha_key}")

    if not stored_captcha:
        # Captcha expired or not found
        return False

    # Delete captcha after verification (one-time use)
    await redis.delete(f"captcha:{captcha_key}")

    # Compare case-insensitively
    # Redis already returns string due to decode_responses=True in connection config
    return stored_captcha.upper() == captcha_code.upper()


async def verify_sms_code(
    sms_key: str,
    sms_code: str,
    phone: str,
    redis: Redis
) -> bool:
    """验证短信验证码

    Args:
        sms_key: 短信验证码key
        sms_code: 用户输入的验证码
        phone: 手机号
        redis: Redis连接

    Returns:
        bool: 验证是否成功
    """
    if not sms_key or not sms_code or not phone:
        return False

    # 从Redis获取存储的验证码
    stored_data = await redis.get(f"sms:code:{sms_key}")

    if not stored_data:
        # 验证码不存在或已过期
        return False

    # 删除验证码(一次性使用)
    await redis.delete(f"sms:code:{sms_key}")

    # 解析存储的数据: "手机号:验证码"
    try:
        stored_phone, stored_code = stored_data.split(":", 1)
    except ValueError:
        return False

    # 验证手机号和验证码是否匹配
    return stored_phone == phone and stored_code == sms_code
