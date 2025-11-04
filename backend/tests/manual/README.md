# 手动测试脚本

本目录包含用于手动测试头显Server API的脚本。

## 脚本说明

### 1. create_test_operator.py
创建测试运营商账号。

**用途**: 快速创建一个新的测试运营商账号。

**使用方法**:
```bash
python backend/tests/manual/create_test_operator.py
```

**输出**:
- 运营商用户名和密码
- Operator ID
- API Key

---

### 2. setup_test_data.py
准备完整的测试数据（运营点、应用授权）。

**用途**: 为已有的测试运营商创建运营点并申请应用授权。

**使用方法**:
```bash
python backend/tests/manual/setup_test_data.py
```

**前置条件**:
- 已创建测试运营商账号（使用 create_test_operator.py）
- 修改脚本中的 USERNAME 和 PASSWORD

**后续步骤**:
1. 在数据库中给账号充值
2. 使用管理员账号审批应用授权申请

---

### 3. test_headset_api.py
完整的头显Server API测试套件。

**用途**: 测试所有头显Server相关的API接口。

**测试覆盖**:
1. ✅ 运营商登录
2. ✅ 获取运营商信息（运营点、已授权应用）
3. ✅ 创建Headset Token
4. ⚠️ 预授权查询（可选）
5. ✅ 游戏授权（核心接口）
6. ⚠️ 上传游戏Session（可选）

**使用方法**:
```bash
python backend/tests/manual/test_headset_api.py
```

**前置条件**:
- 后端服务运行在 http://localhost:8000
- 已完成测试数据准备（使用 setup_test_data.py）
- 测试账号已充值且应用已授权

**测试账号信息**:
- 用户名: headset_test_op
- 密码: Test123456
- 应用: APP_20251030_002（记事本）

---

## 完整测试流程

### 首次测试设置

1. **创建测试账号**:
   ```bash
   python backend/tests/manual/create_test_operator.py
   ```

2. **准备测试数据**:
   ```bash
   python backend/tests/manual/setup_test_data.py
   ```

3. **手动充值** (使用数据库或管理员界面):
   ```sql
   UPDATE operator_accounts
   SET balance = 1000.00
   WHERE username = 'headset_test_op';
   ```

4. **授权应用** (使用数据库或管理员审批):
   ```sql
   INSERT INTO operator_app_authorizations (
       id, operator_id, application_id, is_active
   ) VALUES (
       gen_random_uuid(),
       (SELECT id FROM operator_accounts WHERE username = 'headset_test_op'),
       (SELECT id FROM applications WHERE app_code = 'APP_20251030_002'),
       true
   );
   ```

5. **运行测试**:
   ```bash
   python backend/tests/manual/test_headset_api.py
   ```

### 后续测试

如果测试数据已经准备好，直接运行：
```bash
python backend/tests/manual/test_headset_api.py
```

---

## 测试结果说明

### 成功标记
- ✅ 绿色勾号 - 测试通过
- ❌ 红色叉号 - 测试失败
- ℹ️ 黄色信息 - 调试信息

### 常见问题

**Q: 预授权查询失败（500错误）**
A: 这是后端已知bug，不影响核心功能测试。

**Q: 上传Session失败**
A: 后端代码有bug（missing 'select' import），需要修复。

**Q: 余额不足**
A: 重新给测试账号充值。

**Q: 应用未授权**
A: 检查应用授权是否已审批通过。

---

## 开发说明

这些脚本使用 `requests` 库直接调用 HTTP API，不依赖任何内部模块。

**依赖**:
- Python 3.8+
- requests library

**修改测试账号**:
编辑各脚本中的常量：
```python
USERNAME = "headset_test_op"
PASSWORD = "Test123456"
BASE_URL = "http://localhost:8000/api/v1"
```
