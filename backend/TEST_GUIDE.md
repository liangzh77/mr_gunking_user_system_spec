# 测试运行指南

本文档说明如何运行User Story 1的测试套件。

## 前置条件

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 环境配置

确保有 `.env` 文件或环境变量配置(测试会使用内存数据库,不需要真实PostgreSQL):

```bash
# .env.test (可选)
DATABASE_URL=sqlite+aiosqlite:///:memory:
SECRET_KEY=test-secret-key
```

## 运行测试

### 方式1: 运行所有测试 (推荐首次运行)

```bash
cd backend
pytest
```

这会运行所有测试并生成覆盖率报告。

### 方式2: 按类型运行测试

#### 只运行契约测试 (T029)
```bash
cd backend
pytest tests/contract/ -v
```

#### 只运行集成测试 (T030-T034, T033a)
```bash
cd backend
pytest tests/integration/ -v
```

#### 只运行单元测试 (T048-T049)
```bash
cd backend
pytest tests/unit/ -v
```

### 方式3: 运行特定测试文件

```bash
cd backend

# 完整授权流程测试
pytest tests/integration/test_authorization_flow.py -v

# 余额不足场景测试
pytest tests/integration/test_insufficient_balance.py -v

# 会话ID幂等性测试
pytest tests/integration/test_session_idempotency.py -v

# 玩家数量验证测试
pytest tests/integration/test_player_count_validation.py -v

# 会话ID格式验证测试 (FR-061)
pytest tests/integration/test_session_id_validation.py -v

# 并发扣费测试
pytest tests/integration/test_concurrent_billing.py -v

# AuthService单元测试
pytest tests/unit/services/test_auth_service.py -v

# BillingService单元测试
pytest tests/unit/services/test_billing_service.py -v
```

### 方式4: 运行特定测试函数

```bash
cd backend

# 运行特定测试类中的特定方法
pytest tests/unit/services/test_auth_service.py::TestVerifyOperatorByApiKey::test_valid_api_key_success -v

# 运行特定测试函数
pytest tests/integration/test_authorization_flow.py::test_complete_authorization_flow_success -v
```

### 方式5: 使用markers运行

```bash
cd backend

# 只运行标记为integration的测试
pytest -m integration -v

# 只运行标记为unit的测试
pytest -m unit -v

# 只运行标记为contract的测试
pytest -m contract -v
```

## 测试输出说明

### 成功示例
```
tests/integration/test_authorization_flow.py::test_complete_authorization_flow_success PASSED [100%]

======================== 1 passed in 0.52s ========================
```

### 失败示例
```
tests/integration/test_authorization_flow.py::test_complete_authorization_flow_success FAILED [100%]

FAILED tests/integration/test_authorization_flow.py::test_complete_authorization_flow_success
AssertionError: assert 500 == 200
```

## 查看覆盖率报告

测试运行后会生成覆盖率报告:

### 1. 终端查看
```bash
cd backend
pytest --cov=src --cov-report=term-missing
```

输出示例:
```
---------- coverage: platform win32, python 3.13.7 -----------
Name                                 Stmts   Miss  Cover   Missing
------------------------------------------------------------------
src/services/auth_service.py           95      5    95%   45-49
src/services/billing_service.py        87      3    97%   156-158
------------------------------------------------------------------
TOTAL                                 182      8    96%
```

### 2. HTML报告查看
```bash
cd backend
pytest --cov=src --cov-report=html

# 然后打开浏览器查看
start htmlcov/index.html  # Windows
# 或
open htmlcov/index.html   # macOS/Linux
```

## 常见问题排查

### 问题1: 导入错误 (ModuleNotFoundError)

**错误信息:**
```
ModuleNotFoundError: No module named 'src'
```

**解决方案:**
```bash
# 确保在backend目录下运行
cd backend

# 或者设置PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"  # Linux/macOS
set PYTHONPATH=%PYTHONPATH%;%cd%          # Windows CMD
$env:PYTHONPATH="$env:PYTHONPATH;$(pwd)"  # Windows PowerShell
```

### 问题2: 数据库连接错误

**错误信息:**
```
sqlalchemy.exc.OperationalError: could not connect to database
```

**解决方案:**
测试使用内存数据库,不需要真实PostgreSQL。如果出现此错误,检查:
1. conftest.py中的TEST_DATABASE_URL配置
2. 确保安装了aiosqlite: `pip install aiosqlite`

### 问题3: Async错误

**错误信息:**
```
RuntimeError: Event loop is closed
```

**解决方案:**
确保pytest.ini中配置了:
```ini
[pytest]
asyncio_mode = auto
```

### 问题4: Fixture未找到

**错误信息:**
```
fixture 'test_db' not found
```

**解决方案:**
确保`tests/conftest.py`文件存在且包含test_db fixture定义。

## 测试数据说明

所有测试使用独立的测试数据,不会影响开发/生产数据库:

- **数据库**: SQLite内存数据库 (`:memory:`)
- **数据隔离**: 每个测试函数独立事务
- **自动清理**: 测试结束后自动回滚

## 持续集成建议

如果配置CI/CD,建议使用以下命令:

```bash
# 运行所有测试,生成覆盖率报告和JUnit XML
pytest --cov=src --cov-report=xml --cov-report=term --junitxml=test-results.xml

# 检查覆盖率阈值(配置在pytest.ini中: cov-fail-under=80)
# 如果覆盖率低于80%,pytest会返回失败状态码
```

## User Story 1测试清单

### 契约测试 (T029)
- [x] `test_game_authorize.py` - 10个契约验证测试

### 集成测试 (T030-T034, T033a)
- [x] `test_authorization_flow.py` - 完整授权流程 (9个测试)
- [x] `test_insufficient_balance.py` - 余额不足场景 (6个测试)
- [x] `test_session_idempotency.py` - 会话ID幂等性 (7个测试)
- [x] `test_player_count_validation.py` - 玩家数量验证 (8个测试)
- [x] `test_session_id_validation.py` - 会话ID格式验证 (10个测试)
- [x] `test_concurrent_billing.py` - 并发扣费处理 (7个测试)

### 单元测试 (T048-T049)
- [x] `test_auth_service.py` - AuthService (20+个测试)
- [x] `test_billing_service.py` - BillingService (14个测试)

**总计: 约90+个测试用例**

## 快速验证命令

### 一键运行所有User Story 1测试
```bash
cd backend
pytest tests/contract/test_game_authorize.py tests/integration/ tests/unit/services/test_auth_service.py tests/unit/services/test_billing_service.py -v
```

### 快速冒烟测试 (运行关键路径)
```bash
cd backend
pytest tests/integration/test_authorization_flow.py::test_complete_authorization_flow_success tests/integration/test_insufficient_balance.py::test_insufficient_balance_returns_402 tests/integration/test_session_idempotency.py::test_duplicate_session_id_no_double_charge -v
```

## 下一步

1. **首次运行**: 执行 `pytest -v` 查看所有测试结果
2. **修复失败**: 如有失败测试,查看错误信息进行修复
3. **检查覆盖率**: 查看HTML覆盖率报告,确保关键代码被测试
4. **提交代码**: 所有测试通过后提交代码

## 联系与反馈

如遇到问题,请检查:
1. Python版本 >= 3.11
2. 所有依赖已安装 (`pip list`)
3. 在正确的目录下运行 (`backend/`)
4. conftest.py文件存在
