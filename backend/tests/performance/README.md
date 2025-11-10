# 性能测试指南 (T284)

本目录包含 MR 游戏运营管理系统的性能测试脚本和基准数据。

## 测试工具

### 1. Locust - 负载测试工具

使用 [Locust](https://locust.io/) 进行性能测试和负载测试。

### 2. 头显API测试工具 (新增)

专门用于测试头显Server对接的3个核心API接口的性能和可靠性：

- **预授权查询** (pre-authorize)
- **游戏授权** (authorize)
- **上传游戏会话数据** (session/upload)

#### 快速使用

**Windows系统 - 使用批处理脚本（推荐）**:

```bash
cd backend/tests/performance
test_headset_api.bat
```

脚本会引导你选择：
- 服务器类型（生产/开发）
- 测试次数
- 测试间隔

**直接使用Python脚本**:

```bash
cd backend/tests/performance

# 生产服务器测试
python test_headset_api.py \
    --base-url https://mrgun.chu-jiao.com/api/v1 \
    --username operator1 \
    --password operator123 \
    --count 20 \
    --delay 1.0

# 开发服务器测试
python test_headset_api.py \
    --base-url https://10.10.3.9/api/v1 \
    --username operator1 \
    --password operator123 \
    --count 10 \
    --delay 0.5
```

#### 测试报告

测试完成后会自动显示统计报告：

```
接口名称             成功率       平均延迟     最小延迟     最大延迟
----------------------------------------------------------------------
预授权查询           95.0%        120ms       85ms        250ms
游戏授权             100.0%       150ms       110ms       300ms
上传会话数据         100.0%       80ms        60ms        150ms
```

#### 参数说明

- `--base-url`: API基础URL（必需）
- `--username`: 运营商用户名（必需）
- `--password`: 运营商密码（必需）
- `--count`: 测试次数，默认10次
- `--delay`: 测试间隔秒数，默认1.0秒

#### 依赖要求

```bash
pip install requests urllib3
```

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install locust
```

### 2. 启动后端服务

```bash
# 确保后端服务运行在 http://localhost:8000
uvicorn src.main:app --reload
```

### 3. 运行性能测试

#### Web UI 模式 (推荐)

```bash
cd backend
locust -f tests/performance/locustfile.py --host=http://localhost:8000
```

然后访问 `http://localhost:8089` 查看 Locust Web UI，配置并开始测试。

#### 命令行模式

```bash
# 100 个并发用户，每秒生成 10 个用户，运行 1 分钟
locust -f tests/performance/locustfile.py \
    --host=http://localhost:8000 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 1m \
    --headless
```

#### 生成 HTML 报告

```bash
locust -f tests/performance/locustfile.py \
    --host=http://localhost:8000 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 1m \
    --headless \
    --html=performance_report.html
```

## 测试场景

### 1. 运营商用户 (OperatorUser)

模拟运营商的典型操作流程，权重分配：

- **游戏授权验证** (50%): 最频繁的核心操作
- **余额查询** (20%): 较频繁的查询操作
- **运营点查询** (15%): 定期查询运营点信息
- **交易记录查询** (10%): 查看交易历史
- **已授权应用查询** (5%): 偶尔查询

### 2. 管理员用户 (AdminUser)

模拟管理员的后台操作，权重分配：

- **查询运营商列表** (30%): 主要管理操作
- **查询应用列表** (20%): 应用管理

## 性能目标

| API 端点 | P50 | P95 | P99 | RPS 目标 |
|---------|-----|-----|-----|---------|
| 游戏授权验证 | < 100ms | < 200ms | < 500ms | > 100 |
| 运营商登录 | < 150ms | < 300ms | < 600ms | > 50 |
| 余额查询 | < 80ms | < 150ms | < 300ms | > 200 |
| 运营点查询 | < 100ms | < 200ms | < 400ms | > 100 |
| 交易记录查询 | < 150ms | < 250ms | < 500ms | > 80 |

## 测试数据准备

在运行性能测试前，需要准备测试数据：

### 创建测试账户

```bash
# 使用脚本批量创建测试运营商账户
python scripts/create_test_accounts.py --count 100
```

### 准备测试数据

```sql
-- 创建测试应用
INSERT INTO applications (app_code, app_name, price_per_player_per_hour)
VALUES
  ('GAME_001', '测试游戏1', 10.00),
  ('GAME_002', '测试游戏2', 15.00),
  ('GAME_003', '测试游戏3', 20.00);

-- 为测试账户充值
UPDATE operator_accounts
SET balance = 1000.00
WHERE username LIKE 'test_operator_%';
```

## 性能基准

查看 `BASELINE.md` 获取当前系统的性能基准数据。

## 常见测试场景

### 1. 负载测试

测试系统在预期负载下的性能表现：

```bash
locust -f tests/performance/locustfile.py \
    --host=http://localhost:8000 \
    --users 50 \
    --spawn-rate 5 \
    --run-time 5m \
    --headless
```

### 2. 压力测试

找出系统的性能瓶颈：

```bash
locust -f tests/performance/locustfile.py \
    --host=http://localhost:8000 \
    --users 500 \
    --spawn-rate 50 \
    --run-time 3m \
    --headless
```

### 3. 峰值测试

模拟突发流量：

```bash
locust -f tests/performance/locustfile.py \
    --host=http://localhost:8000 \
    --users 200 \
    --spawn-rate 100 \
    --run-time 2m \
    --headless
```

### 4. 浸泡测试 (Soak Test)

长时间运行，检测内存泄漏等问题：

```bash
locust -f tests/performance/locustfile.py \
    --host=http://localhost:8000 \
    --users 30 \
    --spawn-rate 3 \
    --run-time 30m \
    --headless
```

## 性能优化建议

如果性能测试未达到目标，可以考虑以下优化：

1. **数据库优化**
   - 添加索引
   - 优化查询 (使用 explain analyze)
   - 调整连接池大小

2. **缓存优化**
   - 使用 Redis 缓存热点数据
   - 实现查询结果缓存

3. **应用优化**
   - 减少数据库查询次数
   - 使用异步处理
   - 优化 ORM 查询 (避免 N+1 问题)

4. **基础设施优化**
   - 增加 Gunicorn workers 数量
   - 使用负载均衡
   - 垂直/水平扩展

## CI/CD 集成

性能测试已集成到 CI/CD pipeline 中，在 main 分支 push 时自动运行：

```yaml
# .github/workflows/ci.yml
performance-tests:
  name: 性能基准测试
  runs-on: ubuntu-latest
  if: github.ref == 'refs/heads/main'
  steps:
    - name: 运行性能测试
      run: |
        pytest tests/performance -v -m benchmark
```

## 参考资源

- [Locust 官方文档](https://docs.locust.io/)
- [性能测试最佳实践](https://locust.io/best-practices)
- [MR 系统性能优化指南](../../docs/performance_optimization.md)
