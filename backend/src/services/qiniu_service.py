"""七牛云存储服务

提供文件上传功能，支持APK文件上传到七牛云存储。
"""

import re
from typing import Optional
from urllib.parse import quote
from qiniu import Auth, put_data, put_file, etag
from qiniu import config as qiniu_config
import tempfile
import os

from ..core.config import settings

# 设置七牛云上传超时时间（单位：秒）
# 对于大文件上传，需要足够长的超时时间
qiniu_config.set_default(
    connection_timeout=60000,  # 连接超时1000分钟
    connection_retries=5,      # 重试5次
)


class QiniuService:
    """七牛云存储服务类"""

    def __init__(self):
        """初始化七牛云认证"""
        self.access_key = settings.QINIU_ACCESS_KEY
        self.secret_key = settings.QINIU_SECRET_KEY
        self.bucket_name = settings.QINIU_BUCKET_NAME
        self.download_url = settings.QINIU_DOWNLOAD_URL
        self.auth = Auth(self.access_key, self.secret_key)

    def get_upload_token(self, key: Optional[str] = None, expires: int = 3600) -> str:
        """获取上传凭证

        Args:
            key: 上传文件的key，如果为None则由七牛生成
            expires: 凭证有效期（秒），默认1小时

        Returns:
            上传凭证字符串
        """
        return self.auth.upload_token(self.bucket_name, key, expires)

    def upload_file(self, file_data: bytes, key: str) -> tuple[bool, str]:
        """上传文件到七牛云

        对于大文件(>10MB)，使用临时文件方式上传以提高稳定性

        Args:
            file_data: 文件二进制数据
            key: 文件在七牛云中的key（路径）

        Returns:
            (成功标志, 文件URL或错误信息)
        """
        # 对于大文件使用临时文件上传
        file_size = len(file_data)
        use_temp_file = file_size > 10 * 1024 * 1024  # 大于10MB使用文件上传

        # 增加token有效期到2小时
        token = self.get_upload_token(key, expires=7200)

        try:
            if use_temp_file:
                # 写入临时文件后上传
                with tempfile.NamedTemporaryFile(delete=False, suffix='.apk') as tmp_file:
                    tmp_file.write(file_data)
                    tmp_path = tmp_file.name

                try:
                    ret, info = put_file(token, key, tmp_path)
                finally:
                    # 清理临时文件
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
            else:
                ret, info = put_data(token, key, file_data)

            if ret is not None and 'key' in ret:
                # 构建文件访问URL
                file_url = f"{self.download_url}/{ret['key']}"
                return True, file_url
            else:
                # 获取更详细的错误信息
                error_msg = "Unknown error"
                if info:
                    if hasattr(info, 'text_body') and info.text_body:
                        error_msg = info.text_body
                    elif hasattr(info, 'error') and info.error:
                        error_msg = info.error
                    elif hasattr(info, 'status_code'):
                        error_msg = f"HTTP {info.status_code}"
                return False, f"Upload failed: {error_msg}"
        except Exception as e:
            return False, f"Upload exception: {str(e)}"

    def get_private_download_url(self, key: str, expires: int = 3600) -> str:
        """生成私有空间的下载URL

        Args:
            key: 文件在七牛云中的key（路径）
            expires: URL有效期（秒），默认1小时

        Returns:
            带签名的私有下载URL
        """
        # URL编码key中的中文和特殊字符
        encoded_key = quote(key, safe='/')
        base_url = f"{self.download_url}/{encoded_key}"
        private_url = self.auth.private_download_url(base_url, expires=expires)
        return private_url

    def get_download_url(self, key: str, private: bool = True, expires: int = 3600) -> str:
        """获取文件下载URL

        Args:
            key: 文件在七牛云中的key（路径）
            private: 是否是私有空间，默认True
            expires: 私有空间URL有效期（秒），默认1小时

        Returns:
            下载URL
        """
        if private:
            return self.get_private_download_url(key, expires)
        else:
            encoded_key = quote(key, safe='/')
            return f"{self.download_url}/{encoded_key}"

    @staticmethod
    def extract_version_from_filename(filename: str) -> Optional[str]:
        """从文件名中提取版本号

        支持的格式：
        - AppName_1.0.3.apk
        - AppName-1.0.3.apk
        - AppName_v1.0.3.apk
        - AppName-v1.0.3.apk

        Args:
            filename: APK文件名

        Returns:
            版本号字符串（如 "1.0.3"），提取失败返回None
        """
        # 移除 .apk 后缀
        name = filename.lower()
        if name.endswith('.apk'):
            name = name[:-4]

        # 尝试匹配版本号模式
        patterns = [
            r'[_-]v?(\d+\.\d+\.\d+)$',  # name_1.0.3 或 name-v1.0.3
            r'[_-]v?(\d+\.\d+)$',        # name_1.0 或 name-v1.0
        ]

        for pattern in patterns:
            match = re.search(pattern, name)
            if match:
                return match.group(1)

        return None


# 全局服务实例
qiniu_service = QiniuService()
