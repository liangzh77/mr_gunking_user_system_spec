# 如何运行测试

## ✅ 快速开始 (推荐)

### 1. 准备环境

您的环境已经配置好了Python 3.12虚拟环境! 位置: `backend/.venv312/`

### 2. 运行测试

**Windows 用户:**

```cmd
cd backend
run_tests.bat
```

或者指定测试类型:

```cmd
run_tests.bat contract      # 只运行契约测试
run_tests.bat integration   # 只运行集成测试
run_tests.bat unit          # 只运行单元测试
run_tests.bat quick         # 快速测试(无覆盖率)
run_tests.bat smoke         # 冒烟测试(关键路径)
```

**Linux/Mac/Git Bash 用户:**

```bash
cd backend
export PYTHONPATH=.
.venv312/Scripts/pytest.exe -v
```

## 📊 测试覆盖范围

### User Story 1 - 游戏授权与实时计费

**✅ 契约测试 (T029)**
- `tests/contract/test_game_authorize.py` - 10个测试
- 验证API规范符合contracts/auth.yaml

**✅ 集成测试 (T030-T034, T033a)**
- `tests/integration/test_authorization_flow.py` - 9个测试 (完整授权流程)
- `tests/integration/test_insufficient_balance.py` - 6个测试 (余额不足场景)
- `tests/integration/test_session_idempotency.py` - 7个测试 (幂等性保护)
- `tests/integration/test_player_count_validation.py` - 8个测试 (玩家数量验证)
- `tests/integration/test_session_id_validation.py` - 10个测试 (会话ID格式FR-061)
- `tests/integration/test_concurrent_billing.py` - 7个测试 (并发扣费安全)

**✅ 单元测试 (T048-T049)**
- `tests/unit/services/test_auth_service.py` - 20+个测试 (AuthService)
- `tests/unit/services/test_billing_service.py` - 14个测试 (BillingService)

**总计: 约90+个测试用例**

## 🔍 查看测试结果

### 终端输出示例

**成功:**
```
tests/integration/test_authorization_flow.py::test_complete_authorization_flow_success PASSED [100%]
======================== 1 passed in 0.52s ========================
```

**失败:**
```
tests/integration/test_authorization_flow.py::test_complete_authorization_flow_success FAILED [100%]
AssertionError: assert 500 == 200
```

### 覆盖率报告

测试运行后会自动生成HTML覆盖率报告:

```cmd
cd backend
start htmlcov\index.html     # Windows
```

或在浏览器中打开: `backend/htmlcov/index.html`

## 🛠️ 运行特定测试

### 按文件运行

```cmd
cd backend
.venv312\Scripts\pytest.exe tests\integration\test_authorization_flow.py -v
```

### 按函数运行

```cmd
.venv312\Scripts\pytest.exe tests\integration\test_authorization_flow.py::test_complete_authorization_flow_success -v
```

### 按测试类运行

```cmd
.venv312\Scripts\pytest.exe tests\unit\services\test_auth_service.py::TestVerifyOperatorByApiKey -v
```

## ⚠️ 已知问题与解决方案

### 问题1: SQLite UUID类型不兼容 ✅ 已修复

**现象:**
```
sqlalchemy.exc.UnsupportedCompilationError: Compiler can't render element of type UUID
```

**原因:** PostgreSQL的UUID和JSONB类型在SQLite中不支持

**解决方案:** 已在 `tests/conftest.py` 中添加类型适配器:
- UUID → GUID (String(36))
- JSONB → JSON

### 问题2: Docstring转义序列错误 ✅ 已修复

**现象:**
```
SyntaxError: invalid escape sequence '\d'
```

**原因:** Docstring中包含正则表达式，反斜杠被Python解释为转义序列

**解决方案:** 已将affected docstrings改为raw string (r"""...)

### 问题3: 测试文件名冲突 ✅ 已修复

**现象:**
```
import file mismatch: imported module 'test_rate_limit' has this __file__ attribute...
```

**原因:** `tests/integration/test_rate_limit.py` 和 `tests/unit/middleware/test_rate_limit.py` 同名

**解决方案:** 已重命名单元测试文件为 `test_rate_limit_counter.py`

### 问题4: 路由未实现导致404错误

**现状:** 测试环境已经正常运行，但部分测试因API端点未完全实现而失败:
- `/v1/auth/game/authorize` - 返回404 (路由已定义但可能未注册到app)
- `/metrics` - 返回404 (Prometheus metrics端点未配置)

**待办:** 需要在src/main.py中正确注册所有路由

## 📝 推荐测试流程

### 1. 首次运行 - 完整测试

```cmd
cd backend
run_tests.bat
```

查看所有测试是否通过,并检查覆盖率报告。

### 2. 快速验证 - 冒烟测试

```cmd
run_tests.bat smoke
```

只运行3个关键测试,快速验证核心功能。

### 3. 分类测试 - 按类型运行

```cmd
run_tests.bat integration
```

专注于某一类测试进行调试。

### 4. 精准调试 - 单个测试

```cmd
.venv312\Scripts\pytest.exe tests\integration\test_authorization_flow.py::test_complete_authorization_flow_success -v -s
```

添加 `-s` 参数可以看到print输出,方便调试。

## 🎯 当前测试状态

**✅ 测试环境配置完成！**

运行测试命令：
```bash
cd backend
export PYTHONPATH=.
.venv312/Scripts/pytest.exe --tb=no -q
```

当前结果（2025-10-13）：

```
collected 114 items

29 failed, 16 passed, 69 errors in 7.49s

✅ 测试环境正常运行
✅ 所有测试成功收集
⚠️  失败和错误是预期的，原因如下：
```

### 失败/错误原因分析

**29个FAILED测试** - 返回404错误：
- 原因：API端点 `/v1/auth/game/authorize` 未实现或未正确注册
- 涉及文件：
  - `tests/contract/test_game_authorize.py` (4个)
  - `tests/contract/test_prometheus_metrics.py` (3个)
  - `tests/integration/test_*.py` (多个)

**69个ERROR测试** - fixture依赖失败：
- 原因：这些测试依赖于第一个测试成功创建的测试数据
- 一旦API实现后，这些测试会自动通过

**16个PASSED测试** ✅：
- 纯逻辑测试（不依赖API调用）
- 包括：schema验证、数据格式测试等

## 💡 提示

- **首次运行可能较慢** - pytest需要收集所有测试
- **使用 `-v` 查看详细输出** - 了解每个测试的名称和结果
- **使用 `--no-cov` 加快速度** - 跳过覆盖率计算
- **使用 `-k` 过滤测试** - 例如 `-k "test_valid"` 只运行名字包含"test_valid"的测试

## 📞 需要帮助?

如果遇到问题:

1. 检查Python版本: `.venv312\Scripts\python.exe --version` (应该是3.12.x)
2. 检查依赖: `.venv312\Scripts\pip.exe list | findstr "pytest fastapi sqlalchemy"`
3. 查看pytest.ini配置
4. 查看tests/conftest.py中的fixture定义

祝测试顺利! 🚀
