"""
AES-256-GCM加密工具类

功能：
- 对敏感数据进行AES-256-GCM加密/解密
- 支持多版本密钥以兼容密钥轮换
- 用于加密存储API Key、支付密钥等敏感信息
"""
import os
import base64
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import structlog

logger = structlog.get_logger(__name__)


class EncryptionError(Exception):
    """加密/解密操作失败异常"""
    pass


class EncryptionService:
    """
    AES-256-GCM加密服务

    特性：
    - 使用AEAD（认证加密）模式，提供机密性和完整性
    - 每次加密生成随机Nonce，确保相同明文产生不同密文
    - 支持密钥版本前缀，便于密钥轮换
    """

    def __init__(self, master_key: str, key_version: str = "v1"):
        """
        初始化加密服务

        Args:
            master_key: 主密钥（从环境变量MASTER_ENCRYPTION_KEY读取）
            key_version: 密钥版本标识（用于密钥轮换）

        Raises:
            ValueError: master_key为空或长度不足
        """
        if not master_key or len(master_key) < 32:
            raise ValueError(
                "Master key must be at least 32 characters long"
            )

        self.key_version = key_version
        self.master_key = master_key

        # 使用PBKDF2派生256位密钥
        self._cipher_key = self._derive_key(master_key)
        self._aesgcm = AESGCM(self._cipher_key)

        logger.info(
            "encryption_service_initialized",
            key_version=key_version,
            algorithm="AES-256-GCM"
        )

    def _derive_key(self, master_key: str, salt: Optional[bytes] = None) -> bytes:
        """
        使用PBKDF2从主密钥派生加密密钥

        Args:
            master_key: 主密钥字符串
            salt: 盐值（固定值，密钥轮换时更换）

        Returns:
            32字节的派生密钥
        """
        if salt is None:
            # 生产环境应使用固定盐值（与key_version关联）
            salt = b"mr_gunking_system_salt_" + self.key_version.encode('utf-8')

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256位密钥
            salt=salt,
            iterations=100000,  # OWASP推荐最小值
            backend=default_backend()
        )
        return kdf.derive(master_key.encode('utf-8'))

    def encrypt(self, plaintext: str) -> str:
        """
        加密明文数据

        加密流程：
        1. 生成随机96位Nonce
        2. 使用AES-256-GCM加密（附带认证标签）
        3. 拼接格式: VERSION:NONCE:CIPHERTEXT（Base64编码）

        Args:
            plaintext: 明文字符串

        Returns:
            Base64编码的加密结果（格式: v1:nonce_base64:ciphertext_base64）

        Raises:
            EncryptionError: 加密失败

        Example:
            >>> service = EncryptionService("my_secret_key_32_chars_long!!!")
            >>> encrypted = service.encrypt("api_key_123456")
            >>> print(encrypted)
            v1:AAAAAAAAAAAAAAAA:c2VjcmV0ZGF0YQ==...
        """
        try:
            # 1. 生成随机Nonce（96位 = 12字节）
            nonce = os.urandom(12)

            # 2. 加密（plaintext → bytes → ciphertext）
            plaintext_bytes = plaintext.encode('utf-8')
            ciphertext = self._aesgcm.encrypt(nonce, plaintext_bytes, None)

            # 3. Base64编码并拼接版本前缀
            nonce_b64 = base64.b64encode(nonce).decode('utf-8')
            ciphertext_b64 = base64.b64encode(ciphertext).decode('utf-8')

            result = f"{self.key_version}:{nonce_b64}:{ciphertext_b64}"

            logger.debug(
                "data_encrypted",
                key_version=self.key_version,
                plaintext_length=len(plaintext)
            )

            return result

        except Exception as e:
            logger.error(
                "encryption_failed",
                error=str(e),
                key_version=self.key_version
            )
            raise EncryptionError(f"Encryption failed: {e}")

    def decrypt(self, encrypted_data: str) -> str:
        """
        解密数据

        解密流程：
        1. 解析格式: VERSION:NONCE:CIPHERTEXT
        2. Base64解码Nonce和密文
        3. 使用AES-256-GCM解密并验证认证标签

        Args:
            encrypted_data: 加密的数据字符串

        Returns:
            明文字符串

        Raises:
            EncryptionError: 解密失败（密钥错误、数据被篡改等）

        Example:
            >>> decrypted = service.decrypt("v1:AAAA...:c2Vjc...")
            >>> print(decrypted)
            api_key_123456
        """
        try:
            # 1. 解析格式
            parts = encrypted_data.split(":")
            if len(parts) != 3:
                raise ValueError(
                    f"Invalid encrypted data format (expected 3 parts, got {len(parts)})"
                )

            version, nonce_b64, ciphertext_b64 = parts

            # 2. 检查密钥版本
            if version != self.key_version:
                logger.warning(
                    "key_version_mismatch",
                    expected=self.key_version,
                    found=version,
                    hint="May need to use legacy decryption key"
                )
                # 注意：生产环境应支持多版本密钥解密
                # 这里简化处理，仅记录警告

            # 3. Base64解码
            nonce = base64.b64decode(nonce_b64)
            ciphertext = base64.b64decode(ciphertext_b64)

            # 4. 解密
            plaintext_bytes = self._aesgcm.decrypt(nonce, ciphertext, None)
            plaintext = plaintext_bytes.decode('utf-8')

            logger.debug(
                "data_decrypted",
                key_version=version,
                plaintext_length=len(plaintext)
            )

            return plaintext

        except Exception as e:
            logger.error(
                "decryption_failed",
                error=str(e),
                data_prefix=encrypted_data[:20] if len(encrypted_data) >= 20 else encrypted_data
            )
            raise EncryptionError(f"Decryption failed: {e}")

    def decrypt_with_legacy_keys(
        self,
        encrypted_data: str,
        legacy_keys: dict[str, str]
    ) -> str:
        """
        支持密钥轮换的解密（尝试多个历史密钥）

        Args:
            encrypted_data: 加密数据
            legacy_keys: 历史密钥字典 {version: master_key}

        Returns:
            明文字符串

        Raises:
            EncryptionError: 所有密钥都无法解密

        Example:
            >>> legacy_keys = {
            ...     "v1": "old_key_32_characters_long!!!",
            ...     "v2": "new_key_32_characters_long!!!"
            ... }
            >>> plaintext = service.decrypt_with_legacy_keys(
            ...     encrypted_data, legacy_keys
            ... )
        """
        # 1. 解析密钥版本
        parts = encrypted_data.split(":")
        if len(parts) != 3:
            raise EncryptionError("Invalid encrypted data format")

        version = parts[0]

        # 2. 尝试使用对应版本的密钥
        if version in legacy_keys:
            try:
                legacy_service = EncryptionService(
                    legacy_keys[version],
                    key_version=version
                )
                return legacy_service.decrypt(encrypted_data)
            except EncryptionError:
                pass

        # 3. 尝试当前密钥
        try:
            return self.decrypt(encrypted_data)
        except EncryptionError:
            pass

        # 4. 尝试所有历史密钥
        for legacy_version, legacy_key in legacy_keys.items():
            try:
                legacy_service = EncryptionService(
                    legacy_key,
                    key_version=legacy_version
                )
                result = legacy_service.decrypt(encrypted_data)

                logger.info(
                    "decrypted_with_legacy_key",
                    data_version=version,
                    key_version=legacy_version,
                    hint="Consider re-encrypting with current key"
                )
                return result
            except EncryptionError:
                continue

        raise EncryptionError(
            "Failed to decrypt with current and all legacy keys"
        )


# 全局单例（从环境变量初始化）
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """
    获取全局加密服务单例

    从环境变量MASTER_ENCRYPTION_KEY读取主密钥

    Returns:
        EncryptionService实例

    Raises:
        RuntimeError: 环境变量未设置
    """
    global _encryption_service

    if _encryption_service is None:
        master_key = os.getenv("MASTER_ENCRYPTION_KEY")
        if not master_key:
            raise RuntimeError(
                "MASTER_ENCRYPTION_KEY environment variable not set. "
                "Please set it with at least 32 characters."
            )

        key_version = os.getenv("ENCRYPTION_KEY_VERSION", "v1")
        _encryption_service = EncryptionService(master_key, key_version)

    return _encryption_service


def encrypt_sensitive_data(plaintext: str) -> str:
    """
    加密敏感数据（便捷函数）

    Args:
        plaintext: 明文

    Returns:
        加密结果
    """
    service = get_encryption_service()
    return service.encrypt(plaintext)


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """
    解密敏感数据（便捷函数）

    Args:
        encrypted_data: 加密数据

    Returns:
        明文
    """
    service = get_encryption_service()
    return service.decrypt(encrypted_data)
