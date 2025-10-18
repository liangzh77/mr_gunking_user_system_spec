# CI/CD 配置指南

本文档说明如何配置和使用 GitHub Actions CI/CD pipeline。

## 概述

项目包含两个主要的 GitHub Actions workflow：

1. **CI/CD Pipeline** (`ci.yml`) - 主要构建和部署流程
2. **PR Check** (`pr-check.yml`) - Pull Request 自动检查

---

## Workflow 功能

### CI/CD Pipeline (`ci.yml`)

**触发条件**:
- Push 到 `main`, `001-mr`, `develop` 分支
- Pull Request 到 `main` 分支
- 手动触发

**包含的 Jobs**:

1. **代码质量检查**
   - Black 代码格式检查
   - Ruff 代码检查
   - MyPy 类型检查

2. **后端测试**
   - 单元测试（并行执行）
   - 集成测试
   - 契约测试
   - 测试覆盖率报告

3. **安全扫描**
   - Safety 依赖安全扫描
   - Bandit 代码安全扫描

4. **Docker 镜像构建**
   - 多阶段构建
   - 推送到 Docker Hub（仅 main 分支）
   - 构建缓存优化

5. **性能测试**（仅 main 分支）
   - 性能基准测试
   - 性能报告上传

6. **自动部署**（可选）
   - Staging 环境（develop 分支）
   - Production 环境（main 分支）

### PR Check (`pr-check.yml`)

**功能**:
- PR 标题格式检查（Conventional Commits）
- 代码变更分析
- 快速代码检查
- 代码复杂度分析
- PR 大小标记
- 测试覆盖率报告

---

## 配置 Secrets

在 GitHub 仓库设置中添加以下 Secrets：

### 必需的 Secrets

```
Settings → Secrets and variables → Actions → New repository secret
```

| Secret 名称 | 说明 | 示例 |
|------------|------|------|
| `DOCKER_USERNAME` | Docker Hub 用户名 | `your_username` |
| `DOCKER_PASSWORD` | Docker Hub 密码或 Token | `your_token` |

### 部署相关 Secrets（可选）

| Secret 名称 | 说明 |
|------------|------|
| `STAGING_HOST` | Staging 服务器地址 |
| `STAGING_USER` | Staging SSH 用户名 |
| `STAGING_SSH_KEY` | Staging SSH 私钥 |
| `PROD_HOST` | 生产服务器地址 |
| `PROD_USER` | 生产 SSH 用户名 |
| `PROD_SSH_KEY` | 生产 SSH 私钥 |

---

## 本地测试

### 1. 代码格式检查

```bash
cd backend

# Black 格式化
black src tests

# Ruff 检查
ruff check src tests

# MyPy 类型检查
mypy src --ignore-missing-imports
```

### 2. 运行测试

```bash
cd backend

# 单元测试
pytest tests/unit -v

# 集成测试
pytest tests/integration -v

# 契约测试
pytest tests/contract -v

# 测试覆盖率
pytest tests/unit --cov=src --cov-report=html
open htmlcov/index.html
```

### 3. 构建 Docker 镜像

```bash
# 构建后端镜像
docker build -t mr-game-ops-backend:test -f backend/Dockerfile backend/

# 测试镜像
docker run --rm mr-game-ops-backend:test python --version
```

---

## PR 提交规范

### Conventional Commits 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type（必需）**:
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试相关
- `build`: 构建系统
- `ci`: CI/CD 配置
- `chore`: 其他杂项

**Scope（可选）**:
- `backend`
- `frontend`
- `deployment`
- `docs`
- `test`

**示例**:
```
feat(backend): 添加用户认证功能

实现了基于 JWT 的用户认证系统，包括登录、注册和 Token 刷新。

Closes #123
```

---

## 使用 GitHub Actions Act 本地测试

### 安装 Act

```bash
# macOS
brew install act

# Linux
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Windows (使用 Chocolatey)
choco install act-cli
```

### 本地运行 Workflow

```bash
# 运行所有 jobs
act

# 运行特定 job
act -j backend-tests

# 使用 secrets
act -s DOCKER_USERNAME=your_username -s DOCKER_PASSWORD=your_token

# 只测试不推送
act --dryrun
```

---

## 监控和调试

### 查看 Workflow 运行

```
GitHub Repo → Actions → 选择 Workflow Run
```

### 下载构建产物

```
Workflow Run → Artifacts → Download
```

**可用的 Artifacts**:
- `security-reports` - 安全扫描报告
- `performance-reports` - 性能测试报告
- `coverage-report` - 测试覆盖率报告

### 重新运行 Workflow

```
Workflow Run → Re-run all jobs
```

---

## 状态徽章

在 README.md 中添加状态徽章：

```markdown
[![CI/CD](https://github.com/username/repo/actions/workflows/ci.yml/badge.svg)](https://github.com/username/repo/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/username/repo/branch/main/graph/badge.svg)](https://codecov.io/gh/username/repo)
```

---

## 性能优化

### 1. 缓存依赖

```yaml
- uses: actions/setup-python@v4
  with:
    python-version: '3.11'
    cache: 'pip'  # 自动缓存 pip 依赖
```

### 2. 并行测试

```yaml
- name: 运行单元测试
  run: pytest tests/unit -n auto  # 使用所有可用 CPU 核心
```

### 3. Docker 构建缓存

```yaml
- uses: docker/build-push-action@v5
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

---

## 自定义部署脚本

### SSH 部署示例

编辑 `ci.yml` 中的部署 job：

```yaml
deploy-production:
  name: 部署到生产环境
  runs-on: ubuntu-latest
  needs: [docker-build, performance-tests]
  if: github.ref == 'refs/heads/main'
  environment: production

  steps:
  - name: 检出代码
    uses: actions/checkout@v4

  - name: 设置 SSH
    uses: webfactory/ssh-agent@v0.8.0
    with:
      ssh-private-key: ${{ secrets.PROD_SSH_KEY }}

  - name: 部署
    run: |
      ssh -o StrictHostKeyChecking=no ${{ secrets.PROD_USER }}@${{ secrets.PROD_HOST }} << 'EOF'
        cd /opt/mr-game-ops
        git pull origin main
        docker-compose -f docker-compose.prod.yml pull
        docker-compose -f docker-compose.prod.yml up -d --no-deps backend
        docker-compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
      EOF
```

---

## 通知配置

### Slack 通知

```yaml
- name: Slack 通知
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    text: 'CI/CD Pipeline 完成'
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
  if: always()
```

### 钉钉通知

```yaml
- name: 钉钉通知
  uses: zcong1993/actions-ding@master
  with:
    dingToken: ${{ secrets.DING_TOKEN }}
    body: |
      {
        "msgtype": "text",
        "text": {
          "content": "CI/CD Pipeline 完成: ${{ job.status }}"
        }
      }
  if: always()
```

---

## 故障排查

### 常见问题

**1. 测试失败**
- 检查数据库服务是否正常启动
- 确认环境变量配置正确
- 查看完整测试日志

**2. Docker 推送失败**
- 验证 Docker Hub credentials
- 检查镜像标签格式
- 确认仓库访问权限

**3. 部署失败**
- 检查 SSH 连接
- 验证服务器权限
- 查看部署日志

### 调试技巧

**启用 Debug 日志**:
```
Settings → Secrets → New repository secret
Name: ACTIONS_RUNNER_DEBUG
Value: true
```

**使用 tmate 远程调试**:
```yaml
- name: Setup tmate session
  uses: mxschmitt/action-tmate@v3
  if: ${{ failure() }}
```

---

## 最佳实践

1. **✅ 小而频繁的提交**
   - 每个 PR 专注于单一功能
   - 保持 PR 在 500 行以内

2. **✅ 完整的测试覆盖**
   - 确保新功能有测试
   - 保持覆盖率 ≥ 80%

3. **✅ 遵循代码规范**
   - 提交前运行 Black 和 Ruff
   - 修复所有代码检查问题

4. **✅ 有意义的提交信息**
   - 使用 Conventional Commits
   - 说明"为什么"而不仅是"是什么"

5. **✅ 定期更新依赖**
   - 每月检查依赖更新
   - 及时修复安全漏洞

---

## 参考资源

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Codecov 文档](https://docs.codecov.com/)
- [Docker Build Push Action](https://github.com/docker/build-push-action)

---

**配置完成后**，每次 Push 或 PR 都会自动触发 CI/CD pipeline。

查看运行状态：`https://github.com/your-org/your-repo/actions`

---

**文档版本**: 1.0
**最后更新**: 2025-10-18
