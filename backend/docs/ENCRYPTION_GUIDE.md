# 敏感数据加密指南

本文档说明如何使用 AES-256-GCM 加密服务保护敏感数据。

## 概述

系统提供 `EncryptionService` 类，使用行业标准的 **AES-256-GCM** 算法加密敏感数据。

### 特性

- ✅ **AEAD (Authenticated Encryption with Associated Data)**
  - 提供机密性和完整性
  - 防止密文篡改

- ✅ **随机 Nonce**
  - 每次加密生成唯一 96位 Nonce
  - 相同明文产生不同密文

- ✅ **密钥轮换支持**
  - 版本前缀 (v1, v2, ...)
  - 向后兼容旧密钥

- ✅ **PBKDF2 密钥派生**
  - 100,000 迭代 (OWASP 推荐)
  - SHA-256 哈希函数

---

## 配置

### 1. 环境变量

在 `.env` 文件中设置主加密密钥：

```bash
# 至少 32 字符的随机字符串
ENCRYPTION_KEY=your-32-character-minimum-secret-key-here-change-in-production
```

**生成安全密钥:**

```bash
# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# OpenSSL
openssl rand -base64 32

# /dev/urandom
head -c 32 /dev/urandom | base64
```

### 2. 配置类

加密密钥已在 `src/core/config.py` 中定义：

```python
ENCRYPTION_KEY: str = Field(
    default="dev_encryption_key_32_bytes_long",
    min_length=32,
    max_length=32,
    description="32-byte encryption key for sensitive data (AES-256)",
)
```

---

## 基本使用

### 初始化加密服务

```python
from src.core.security.encryption import EncryptionService
from src.core import get_settings

settings = get_settings()

# 创建加密服务实例
encryption = EncryptionService(
    master_key=settings.ENCRYPTION_KEY,
    key_version="v1"
)
```

### 加密数据

```python
# 加密敏感字符串
plaintext = "sk_live_abc123xyz456"
ciphertext = encryption.encrypt(plaintext)

# 加密结果示例:
# "v1:aGVsbG8=:c29tZXRoaW5n..."
#  ↑   ↑        ↑
#  版本  Nonce    密文+认证标签
```

### 解密数据

```python
# 解密
decrypted = encryption.decrypt(ciphertext)
assert decrypted == plaintext
```

---

## 应用场景

### 场景 1: 加密 API Key (存储可逆)

**问题**: 第三方支付 API Key 需要可逆存储（用于发起支付请求）

**解决方案**:

```python
from src.core.security.encryption import EncryptionService
from src.core import get_settings

class PaymentService:
    def __init__(self):
        settings = get_settings()
        self.encryption = EncryptionService(
            master_key=settings.ENCRYPTION_KEY,
            key_version="v1"
        )

    async def store_api_key(self, operator_id: str, api_key: str):
        """存储加密的第三方 API Key"""
        encrypted_key = self.encryption.encrypt(api_key)

        # 存储到数据库
        await db.execute(
            "UPDATE payment_config SET api_key_encrypted = :key WHERE operator_id = :id",
            {"key": encrypted_key, "id": operator_id}
        )

    async def get_api_key(self, operator_id: str) -> str:
        """获取并解密 API Key"""
        result = await db.execute(
            "SELECT api_key_encrypted FROM payment_config WHERE operator_id = :id",
            {"id": operator_id}
        )
        encrypted_key = result.scalar()

        # 解密
        return self.encryption.decrypt(encrypted_key)
```

### 场景 2: 加密敏感日志数据

**问题**: 日志中可能包含敏感信息（如用户 ID、交易金额）

**解决方案**:

```python
def log_sensitive_operation(user_id: str, amount: Decimal):
    """记录敏感操作，加密用户 ID"""
    encryption = get_encryption_service()

    encrypted_user_id = encryption.encrypt(user_id)

    logger.info(
        "payment_processed",
        encrypted_user_id=encrypted_user_id,
        amount=str(amount)  # 金额不加密，用于分析
    )
```

### 场景 3: 加密数据库字段

**数据模型**:

```python
from sqlalchemy import Column, String
from sqlalchemy.ext.hybrid import hybrid_property

class PaymentConfig(Base):
    __tablename__ = "payment_configs"

    id = Column(UUID, primary_key=True)
    operator_id = Column(UUID, nullable=False)
    _api_key_encrypted = Column("api_key_encrypted", String, nullable=False)

    @hybrid_property
    def api_key(self) -> str:
        """解密 API Key"""
        encryption = get_encryption_service()
        return encryption.decrypt(self._api_key_encrypted)

    @api_key.setter
    def api_key(self, plaintext: str):
        """加密并存储 API Key"""
        encryption = get_encryption_service()
        self._api_key_encrypted = encryption.encrypt(plaintext)
```

**使用**:

```python
# 创建配置
config = PaymentConfig(
    id=uuid4(),
    operator_id=operator.id,
    api_key="sk_live_abc123"  # 自动加密
)
db.add(config)
await db.commit()

# 读取配置
config = await db.get(PaymentConfig, config_id)
decrypted_key = config.api_key  # 自动解密
```

### 场景 4: 加密导出文件

**问题**: 导出包含敏感数据的 Excel/CSV 文件

**解决方案**:

```python
async def export_sensitive_data(db: AsyncSession) -> bytes:
    """导出加密的数据文件"""
    encryption = get_encryption_service()

    # 查询敏感数据
    result = await db.execute(
        select(OperatorAccount).where(OperatorAccount.is_active == True)
    )
    operators = result.scalars().all()

    # 构建加密的导出数据
    export_data = []
    for op in operators:
        export_data.append({
            "encrypted_email": encryption.encrypt(op.email),
            "encrypted_phone": encryption.encrypt(op.phone),
            "operator_name": op.full_name  # 非敏感可不加密
        })

    # 生成 JSON
    import json
    return json.dumps(export_data, ensure_ascii=False).encode('utf-8')
```

---

## 密钥轮换

### 为什么需要密钥轮换？

- 🔐 降低密钥泄露风险
- 📅 合规要求 (某些标准要求定期轮换)
- 🛡️ 最小化单一密钥的影响范围

### 轮换流程

#### 1. 生成新密钥版本

```bash
# 生成 v2 密钥
ENCRYPTION_KEY_V2=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# 添加到环境变量
echo "ENCRYPTION_KEY_V2=$ENCRYPTION_KEY_V2" >> .env
```

#### 2. 支持多版本解密

```python
class MultiVersionEncryption:
    """支持多密钥版本的加密服务"""

    def __init__(self, keys: dict[str, str], current_version: str = "v2"):
        """
        Args:
            keys: 版本到密钥的映射 {"v1": "key1", "v2": "key2"}
            current_version: 当前用于加密的版本
        """
        self.current_version = current_version
        self.services = {
            version: EncryptionService(key, version)
            for version, key in keys.items()
        }

    def encrypt(self, plaintext: str) -> str:
        """使用当前版本加密"""
        return self.services[self.current_version].encrypt(plaintext)

    def decrypt(self, ciphertext: str) -> str:
        """自动检测版本并解密"""
        version = ciphertext.split(":")[0]  # 提取版本前缀
        if version not in self.services:
            raise ValueError(f"Unknown key version: {version}")
        return self.services[version].decrypt(ciphertext)
```

#### 3. 重新加密旧数据 (后台任务)

```python
async def reencrypt_old_data(db: AsyncSession):
    """重新加密使用旧密钥的数据"""
    multi_enc = MultiVersionEncryption(
        keys={"v1": old_key, "v2": new_key},
        current_version="v2"
    )

    # 查找使用 v1 加密的记录
    result = await db.execute(
        select(PaymentConfig).where(
            PaymentConfig.api_key_encrypted.like("v1:%")
        )
    )
    old_configs = result.scalars().all()

    for config in old_configs:
        # 解密 (使用 v1)
        plaintext = multi_enc.decrypt(config.api_key_encrypted)

        # 重新加密 (使用 v2)
        config.api_key_encrypted = multi_enc.encrypt(plaintext)

    await db.commit()
    print(f"Re-encrypted {len(old_configs)} records from v1 to v2")
```

---

## 安全最佳实践

### ✅ 应该做

1. **使用强随机密钥**
   ```bash
   # 至少 32 字节
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **密钥与代码分离**
   - 使用环境变量或密钥管理服务 (AWS KMS, HashiCorp Vault)
   - 不要硬编码密钥

3. **限制密钥访问**
   - 最小权限原则
   - 仅授权服务可访问

4. **定期轮换密钥**
   - 建议每 6-12 个月轮换一次
   - 或在怀疑泄露时立即轮换

5. **加密静态数据**
   - 数据库备份也应加密
   - 使用磁盘加密 (LUKS, BitLocker)

6. **审计日志**
   ```python
   logger.info(
       "sensitive_data_decrypted",
       data_type="api_key",
       key_version="v1",
       user_id=current_user.id
   )
   ```

### ❌ 不应该做

1. **不要在客户端加密**
   - 密钥暴露在前端代码中
   - 在服务器端加密

2. **不要重用 Nonce**
   - 系统自动生成随机 Nonce，不要手动指定

3. **不要跳过完整性验证**
   - AES-GCM 自动验证，不要忽略解密错误

4. **不要在日志中记录明文**
   ```python
   # 错误
   logger.info(f"API Key: {api_key}")

   # 正确
   logger.info("API Key encrypted", key_version="v1")
   ```

5. **不要使用弱密钥**
   ```python
   # 错误
   ENCRYPTION_KEY = "123456"  # 太短！

   # 正确
   ENCRYPTION_KEY = "8vN3X-kF7mP2qW9tZ5yH0jR4cL6sA1uD"  # 32+ 字符
   ```

---

## 性能考虑

### 基准测试

```python
import time
from src.core.security.encryption import EncryptionService

encryption = EncryptionService("test_key_32_characters_minimum!")

# 加密性能
plaintext = "sk_live_" + "a" * 100
iterations = 10000

start = time.time()
for _ in range(iterations):
    ciphertext = encryption.encrypt(plaintext)
end = time.time()

print(f"Encryption: {iterations / (end - start):.0f} ops/sec")

# 解密性能
start = time.time()
for _ in range(iterations):
    decrypted = encryption.decrypt(ciphertext)
end = time.time()

print(f"Decryption: {iterations / (end - start):.0f} ops/sec")
```

**预期性能** (现代 CPU):
- 加密: ~50,000 - 100,000 ops/sec
- 解密: ~50,000 - 100,000 ops/sec

### 优化建议

1. **缓存加密实例**
   ```python
   # 全局单例
   _encryption_service = None

   def get_encryption_service() -> EncryptionService:
       global _encryption_service
       if _encryption_service is None:
           settings = get_settings()
           _encryption_service = EncryptionService(settings.ENCRYPTION_KEY)
       return _encryption_service
   ```

2. **批量操作**
   ```python
   async def decrypt_batch(encrypted_values: list[str]) -> list[str]:
       encryption = get_encryption_service()
       return [encryption.decrypt(val) for val in encrypted_values]
   ```

3. **异步处理** (如果加密CPU密集)
   ```python
   import asyncio
   from concurrent.futures import ThreadPoolExecutor

   executor = ThreadPoolExecutor(max_workers=4)

   async def encrypt_async(plaintext: str) -> str:
       encryption = get_encryption_service()
       loop = asyncio.get_event_loop()
       return await loop.run_in_executor(executor, encryption.encrypt, plaintext)
   ```

---

## 合规性

### GDPR / CCPA

- ✅ 静态加密 (Encryption at Rest)
- ✅ 传输加密 (HTTPS)
- ✅ 数据最小化 (仅加密必要数据)
- ✅ "被遗忘权" (删除加密密钥 = 数据不可恢复)

### PCI DSS (支付卡行业)

- ✅ 要求 3.4: 加密存储的支付卡数据
- ✅ 要求 3.5: 保护加密密钥
- ✅ 要求 3.6: 完整记录密钥管理流程

### SOC 2

- ✅ 机密性: AES-256-GCM 加密
- ✅ 完整性: AEAD 认证标签
- ✅ 可用性: 支持密钥轮换和恢复

---

## 故障排查

### 问题 1: `ValueError: Master key must be at least 32 characters long`

**原因**: ENCRYPTION_KEY 不足 32 字符

**解决**:
```bash
# 生成新密钥
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 更新 .env
ENCRYPTION_KEY=<新生成的密钥>
```

### 问题 2: 解密失败 `EncryptionError: Decryption failed`

**可能原因**:
- 密文被篡改
- 使用错误的密钥版本
- 密文格式损坏

**解决**:
```python
try:
    decrypted = encryption.decrypt(ciphertext)
except EncryptionError as e:
    logger.error("Decryption failed", error=str(e), ciphertext_prefix=ciphertext[:20])
    # 使用备用策略或通知管理员
```

### 问题 3: 性能下降

**原因**: 频繁创建 EncryptionService 实例

**解决**: 使用全局单例（见性能优化部分）

---

## 测试

```python
import pytest
from src.core.security.encryption import EncryptionService, EncryptionError

def test_encryption_roundtrip():
    """测试加密/解密往返"""
    encryption = EncryptionService("test_key_minimum_32_characters!")

    plaintext = "sensitive_data_123"
    ciphertext = encryption.encrypt(plaintext)

    assert ciphertext != plaintext
    assert ciphertext.startswith("v1:")

    decrypted = encryption.decrypt(ciphertext)
    assert decrypted == plaintext

def test_tampered_ciphertext():
    """测试篡改检测"""
    encryption = EncryptionService("test_key_minimum_32_characters!")

    ciphertext = encryption.encrypt("test")
    tampered = ciphertext[:-10] + "hacked" + ciphertext[-4:]

    with pytest.raises(EncryptionError):
        encryption.decrypt(tampered)
```

---

## 参考资源

- [NIST Special Publication 800-38D](https://csrc.nist.gov/publications/detail/sp/800-38d/final) - AES-GCM 规范
- [OWASP Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
- [Cryptography.io Documentation](https://cryptography.io/en/latest/)
