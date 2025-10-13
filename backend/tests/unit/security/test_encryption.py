"""
单元测试：加密工具类

测试目标(T026b)：
- 验证加密可逆性
- 验证密钥轮换兼容性
- 验证错误密钥解密失败
"""
import pytest
from src.core.security.encryption import (
    EncryptionService,
    EncryptionError,
    encrypt_sensitive_data,
    decrypt_sensitive_data
)


class TestEncryptionService:
    """测试EncryptionService类"""

    def test_encrypt_decrypt_round_trip(self):
        """测试加密解密往返（可逆性）"""
        # Arrange
        master_key = "test_master_key_32_characters!!"
        service = EncryptionService(master_key, key_version="v1")
        plaintext = "api_key_1234567890abcdef"

        # Act
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)

        # Assert
        assert decrypted == plaintext, "解密后应恢复原始明文"
        assert encrypted != plaintext, "密文不应等于明文"
        assert encrypted.startswith("v1:"), "密文应包含版本前缀"

    def test_encrypt_produces_different_ciphertext(self):
        """测试相同明文产生不同密文（随机Nonce）"""
        # Arrange
        master_key = "test_master_key_32_characters!!"
        service = EncryptionService(master_key)
        plaintext = "same_plaintext"

        # Act
        encrypted1 = service.encrypt(plaintext)
        encrypted2 = service.encrypt(plaintext)

        # Assert
        assert encrypted1 != encrypted2, "相同明文每次应产生不同密文（Nonce随机）"
        assert service.decrypt(encrypted1) == plaintext
        assert service.decrypt(encrypted2) == plaintext

    def test_decrypt_with_wrong_key_fails(self):
        """测试错误密钥解密失败"""
        # Arrange
        key1 = "correct_key_32_characters_long!"
        key2 = "wrong_key_32_characters_long!!!"
        service1 = EncryptionService(key1)
        service2 = EncryptionService(key2)

        plaintext = "secret_data"
        encrypted = service1.encrypt(plaintext)

        # Act & Assert
        with pytest.raises(EncryptionError, match="Decryption failed"):
            service2.decrypt(encrypted)

    def test_decrypt_with_tampered_data_fails(self):
        """测试篡改数据解密失败（认证加密）"""
        # Arrange
        master_key = "test_master_key_32_characters!!"
        service = EncryptionService(master_key)
        plaintext = "important_data"
        encrypted = service.encrypt(plaintext)

        # Act: 篡改密文的一个字符
        tampered = encrypted[:-1] + "X"

        # Assert
        with pytest.raises(EncryptionError, match="Decryption failed"):
            service.decrypt(tampered)

    def test_decrypt_with_invalid_format_fails(self):
        """测试无效格式解密失败"""
        # Arrange
        master_key = "test_master_key_32_characters!!"
        service = EncryptionService(master_key)

        invalid_formats = [
            "not_encrypted_data",
            "v1:only_two_parts",
            "v1:::empty_parts",
            ""
        ]

        # Act & Assert
        for invalid_data in invalid_formats:
            with pytest.raises(EncryptionError):
                service.decrypt(invalid_data)

    def test_key_rotation_with_legacy_keys(self):
        """测试密钥轮换兼容性"""
        # Arrange
        old_key = "old_master_key_32_characters!!"
        new_key = "new_master_key_32_characters!!"

        old_service = EncryptionService(old_key, key_version="v1")
        new_service = EncryptionService(new_key, key_version="v2")

        plaintext = "data_encrypted_with_old_key"

        # Act: 用旧密钥加密
        encrypted_with_old_key = old_service.encrypt(plaintext)

        # Assert: 用新服务+历史密钥解密
        legacy_keys = {
            "v1": old_key,
            "v2": new_key
        }
        decrypted = new_service.decrypt_with_legacy_keys(
            encrypted_with_old_key,
            legacy_keys
        )
        assert decrypted == plaintext, "应能用历史密钥解密旧数据"

    def test_key_rotation_decrypts_with_current_key_first(self):
        """测试密钥轮换优先使用当前密钥"""
        # Arrange
        current_key = "current_key_32_characters_long!"
        legacy_key = "legacy_key_32_characters_long!"

        current_service = EncryptionService(current_key, key_version="v2")
        plaintext = "new_data"

        # Act: 用当前密钥加密
        encrypted = current_service.encrypt(plaintext)

        # Assert: 即使提供历史密钥，也应优先用当前密钥成功解密
        legacy_keys = {"v1": legacy_key}
        decrypted = current_service.decrypt_with_legacy_keys(
            encrypted,
            legacy_keys
        )
        assert decrypted == plaintext

    def test_encrypt_empty_string(self):
        """测试加密空字符串"""
        # Arrange
        master_key = "test_master_key_32_characters!!"
        service = EncryptionService(master_key)

        # Act
        encrypted = service.encrypt("")
        decrypted = service.decrypt(encrypted)

        # Assert
        assert decrypted == "", "空字符串应能正确加密和解密"

    def test_encrypt_unicode_characters(self):
        """测试加密Unicode字符"""
        # Arrange
        master_key = "test_master_key_32_characters!!"
        service = EncryptionService(master_key)
        plaintext = "中文测试数据🔐"

        # Act
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)

        # Assert
        assert decrypted == plaintext, "Unicode字符应能正确加密和解密"

    def test_master_key_validation(self):
        """测试主密钥长度验证"""
        # Act & Assert
        with pytest.raises(ValueError, match="at least 32 characters"):
            EncryptionService("short_key")

        with pytest.raises(ValueError):
            EncryptionService("")


class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_encrypt_decrypt_sensitive_data_with_env_key(self, monkeypatch):
        """测试全局加密/解密函数（需设置环境变量）"""
        # Arrange
        test_key = "test_env_key_32_characters_long!"
        monkeypatch.setenv("MASTER_ENCRYPTION_KEY", test_key)
        monkeypatch.setenv("ENCRYPTION_KEY_VERSION", "v1")

        # 重置全局单例
        import src.core.security.encryption as enc_module
        enc_module._encryption_service = None

        plaintext = "sensitive_api_key"

        # Act
        encrypted = encrypt_sensitive_data(plaintext)
        decrypted = decrypt_sensitive_data(encrypted)

        # Assert
        assert decrypted == plaintext
        assert encrypted.startswith("v1:")

    def test_get_encryption_service_without_env_key_fails(self, monkeypatch):
        """测试未设置环境变量时抛出异常"""
        # Arrange
        monkeypatch.delenv("MASTER_ENCRYPTION_KEY", raising=False)

        # 重置全局单例
        import src.core.security.encryption as enc_module
        enc_module._encryption_service = None

        # Act & Assert
        from src.core.security.encryption import get_encryption_service
        with pytest.raises(RuntimeError, match="MASTER_ENCRYPTION_KEY"):
            get_encryption_service()


@pytest.fixture
def cleanup_global_service():
    """清理全局单例（避免测试间干扰）"""
    yield
    import src.core.security.encryption as enc_module
    enc_module._encryption_service = None
