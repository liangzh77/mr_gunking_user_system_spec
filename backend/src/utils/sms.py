"""短信服务模块

支持多种短信服务提供商:
- mock: 模拟短信(开发测试用,输出到日志)
- aliyun: 阿里云短信服务

通过环境变量 SMS_PROVIDER 配置使用哪种服务商。
"""

import logging
import random
import string
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class SMSProvider(ABC):
    """短信服务提供商抽象基类"""

    @abstractmethod
    async def send_verification_code(self, phone: str, code: str) -> bool:
        """发送验证码短信

        Args:
            phone: 手机号
            code: 验证码

        Returns:
            bool: 发送是否成功
        """
        pass


class MockSMSProvider(SMSProvider):
    """模拟短信服务(开发测试用)

    将验证码输出到日志,不实际发送短信。
    """

    async def send_verification_code(self, phone: str, code: str) -> bool:
        """发送验证码(模拟)

        Args:
            phone: 手机号
            code: 验证码

        Returns:
            bool: 始终返回 True
        """
        logger.info(f"📱 [模拟短信] 手机号: {phone} | 验证码: {code} | 5分钟内有效")
        logger.info(f"=" * 60)
        return True


class AliyunSMSProvider(SMSProvider):
    """阿里云短信服务"""

    def __init__(
        self,
        access_key_id: str,
        access_key_secret: str,
        sign_name: str,
        template_code: str
    ):
        """初始化阿里云短信服务

        Args:
            access_key_id: 阿里云AccessKey ID
            access_key_secret: 阿里云AccessKey Secret
            sign_name: 短信签名
            template_code: 短信模板CODE
        """
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.sign_name = sign_name
        self.template_code = template_code

        # 延迟导入,避免没有安装SDK时报错
        try:
            from alibabacloud_dysmsapi20170525.client import Client
            from alibabacloud_tea_openapi import models as open_api_models
            from alibabacloud_dysmsapi20170525 import models as dysmsapi_models

            self.Client = Client
            self.open_api_models = open_api_models
            self.dysmsapi_models = dysmsapi_models

            # 创建客户端
            config = open_api_models.Config(
                access_key_id=access_key_id,
                access_key_secret=access_key_secret
            )
            config.endpoint = 'dysmsapi.aliyuncs.com'
            self.client = Client(config)

            logger.info("阿里云短信服务初始化成功")

        except ImportError:
            logger.error(
                "阿里云短信SDK未安装。请运行: pip install alibabacloud_dysmsapi20170525"
            )
            raise

    async def send_verification_code(self, phone: str, code: str) -> bool:
        """发送验证码短信

        Args:
            phone: 手机号
            code: 验证码

        Returns:
            bool: 发送是否成功
        """
        try:
            request = self.dysmsapi_models.SendSmsRequest(
                phone_numbers=phone,
                sign_name=self.sign_name,
                template_code=self.template_code,
                template_param=f'{{"code":"{code}"}}'  # 模板参数
            )

            response = self.client.send_sms(request)

            if response.body.code == 'OK':
                logger.info(f"✅ 短信发送成功: {phone}")
                return True
            else:
                logger.error(
                    f"❌ 短信发送失败: {phone} | "
                    f"错误码: {response.body.code} | "
                    f"错误信息: {response.body.message}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ 短信发送异常: {phone} | 错误: {str(e)}")
            return False


class SMSService:
    """短信服务统一接口"""

    def __init__(self, provider: SMSProvider):
        """初始化短信服务

        Args:
            provider: 短信服务提供商实例
        """
        self.provider = provider

    def generate_code(self, length: int = 6) -> str:
        """生成随机验证码

        Args:
            length: 验证码长度(默认6位)

        Returns:
            str: 数字验证码
        """
        return ''.join(random.choices(string.digits, k=length))

    async def send_verification_code(self, phone: str, code: Optional[str] = None) -> str:
        """发送验证码短信

        Args:
            phone: 手机号
            code: 验证码(如果为None则自动生成)

        Returns:
            str: 验证码(用于存储到Redis)

        Raises:
            Exception: 短信发送失败时抛出
        """
        if code is None:
            code = self.generate_code()

        success = await self.provider.send_verification_code(phone, code)

        if not success:
            raise Exception("短信发送失败")

        return code


# 全局短信服务实例
_sms_service: Optional[SMSService] = None


def init_sms_service(
    provider_type: str = "mock",
    access_key_id: Optional[str] = None,
    access_key_secret: Optional[str] = None,
    sign_name: Optional[str] = None,
    template_code: Optional[str] = None
) -> SMSService:
    """初始化短信服务

    Args:
        provider_type: 服务提供商类型 (mock/aliyun)
        access_key_id: 阿里云AccessKey ID (aliyun模式必需)
        access_key_secret: 阿里云AccessKey Secret (aliyun模式必需)
        sign_name: 短信签名 (aliyun模式必需)
        template_code: 短信模板CODE (aliyun模式必需)

    Returns:
        SMSService: 短信服务实例
    """
    global _sms_service

    if provider_type == "mock":
        provider = MockSMSProvider()
    elif provider_type == "aliyun":
        if not all([access_key_id, access_key_secret, sign_name, template_code]):
            raise ValueError(
                "阿里云短信服务需要提供: "
                "access_key_id, access_key_secret, sign_name, template_code"
            )
        provider = AliyunSMSProvider(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            sign_name=sign_name,
            template_code=template_code
        )
    else:
        raise ValueError(f"不支持的短信服务提供商: {provider_type}")

    _sms_service = SMSService(provider)
    logger.info(f"短信服务初始化完成: {provider_type}")
    return _sms_service


def get_sms_service() -> SMSService:
    """获取短信服务实例

    Returns:
        SMSService: 短信服务实例

    Raises:
        RuntimeError: 如果短信服务未初始化
    """
    if _sms_service is None:
        raise RuntimeError(
            "短信服务未初始化。请先调用 init_sms_service() 初始化服务。"
        )
    return _sms_service
