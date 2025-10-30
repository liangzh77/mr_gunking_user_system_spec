# MR游戏运营管理系统 - MVP发布计划

**计划类型**: 快速MVP发布
**目标时间**: 1-2周
**当前进度**: 75% (267/356任务已完成)

---

## 📊 MVP范围定义

### ✅ 已完成核心功能 (保留)

#### 运营商端 (100%完成)
- ✅ 用户注册/登录/个人信息管理
- ✅ 充值功能 (支付宝/微信支付集成)
- ✅ 运营点管理 (CRUD)
- ✅ 应用授权申请
- ✅ 已授权应用查看
- ✅ 使用记录查询
- ✅ 统计分析(按应用/按运营点)
- ✅ 交易记录查看
- ✅ 退款申请
- ✅ 发票管理
- ✅ 消息中心

#### 管理员端 (78%完成)
- ✅ 管理员登录
- ✅ 运营商列表与详情查看
- ✅ 应用管理 (创建/编辑/删除)
- ✅ 授权申请审批
- ✅ 全局交易监控
- ⚠️ **授权管理** (需补充前端页面)

#### 财务端 (75%完成)
- ✅ 财务人员登录
- ✅ 财务仪表盘
- ✅ 退款审核列表
- ✅ 发票审核列表
- ✅ 财务报表生成
- ✅ 审计日志查询

### 🚫 MVP阶段排除功能

以下功能标记为[P]低优先级,MVP阶段不实现:

1. **US5部分管理功能**:
   - API Key查看/重置
   - 运营商分类管理
   - 系统公告发布

2. **US7全局统计**:
   - 跨维度分析
   - 玩家分布统计
   - 全局仪表盘

3. **部分契约测试和集成测试**

---

## 🎯 MVP发布待办事项

### 第一阶段: 功能补全 (3-4天)

#### Task 1: 补充管理员授权管理页面 ⭐ 优先级最高

**后端状态**: ✅ 已完成
- `POST /api/v1/admin/authorizations` - 授权应用
- `DELETE /api/v1/admin/authorizations/{id}` - 撤销授权

**前端任务**:
1. 创建授权管理页面组件
   - 文件: `frontend/src/pages/admin/Authorizations.vue`
   - 功能: 查看所有授权记录、授权新应用、撤销授权

2. 添加路由配置
   - 文件: `frontend/src/router/index.ts`
   - 路径: `/admin/authorizations`

3. 更新侧边栏菜单
   - 文件: `frontend/src/components/admin/AdminSidebar.vue` (如果存在)
   - 添加"授权管理"菜单项

**验收标准**:
- [ ] 授权列表正常显示
- [ ] 可以为运营商授权应用
- [ ] 可以撤销已有授权
- [ ] E2E测试T327通过

---

#### Task 2: 创建测试数据 (可选)

为演示目的创建一些业务数据:

```sql
-- 创建退款申请测试数据
INSERT INTO refund_records (id, operator_id, requested_amount, refund_reason, status, created_at, updated_at)
VALUES (
  gen_random_uuid(),
  (SELECT id FROM operator_accounts WHERE username = 'test_operator' LIMIT 1),
  500.00,
  '测试退款申请 - 充值错误',
  'pending',
  CURRENT_TIMESTAMP,
  CURRENT_TIMESTAMP
);

-- 创建发票申请测试数据
INSERT INTO invoice_records (id, operator_id, invoice_type, amount, tax_number, status, created_at, updated_at)
VALUES (
  gen_random_uuid(),
  (SELECT id FROM operator_accounts WHERE username = 'test_operator' LIMIT 1),
  'VAT',
  1000.00,
  '91110000XXXX',
  'pending',
  CURRENT_TIMESTAMP,
  CURRENT_TIMESTAMP
);
```

**目的**: 让T332和T334可以正常测试

---

### 第二阶段: 生产环境准备 (2-3天)

#### Task 3: 配置生产环境

**3.1 更新docker-compose.yml**

检查并更新生产环境配置:

```yaml
services:
  postgres:
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}  # 从环境变量读取
    volumes:
      - postgres_prod_data:/var/lib/postgresql/data
    restart: always

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile  # 生产Dockerfile
    environment:
      ENVIRONMENT: production
      DEBUG: "false"
      SECRET_KEY: ${SECRET_KEY}
      ENCRYPTION_KEY: ${ENCRYPTION_KEY}
    command: gunicorn src.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
    restart: always

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile  # 生产Dockerfile (nginx)
    restart: always
```

**3.2 创建.env.production**

```bash
# 数据库
POSTGRES_PASSWORD=<strong-production-password>
DATABASE_URL=postgresql+asyncpg://mr_admin:${POSTGRES_PASSWORD}@postgres:5432/mr_game_ops

# Redis
REDIS_PASSWORD=<strong-redis-password>
REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0

# 应用密钥
SECRET_KEY=<生成的256位密钥>
ENCRYPTION_KEY=<生成的32位密钥>

# 支付配置
ALIPAY_APP_ID=<真实的支付宝AppID>
ALIPAY_PRIVATE_KEY=<真实的私钥>
WECHAT_MCHID=<真实的微信商户号>
WECHAT_API_V3_KEY=<真实的APIv3密钥>

# 环境
ENVIRONMENT=production
DEBUG=false
```

**3.3 创建生产Dockerfile**

`backend/Dockerfile` (生产版):
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# 复制代码
COPY . .

# 非root用户运行
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["gunicorn", "src.main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

`frontend/Dockerfile` (生产版):
```dockerfile
# 构建阶段
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# 生产阶段
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**3.4 配置Nginx**

`frontend/nginx.conf`:
```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # SPA路由支持
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API代理
    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 静态资源缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

---

#### Task 4: 数据库备份策略

**4.1 自动备份脚本**

`scripts/backup_db.sh`:
```bash
#!/bin/bash
set -e

BACKUP_DIR="/backups/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/mr_game_ops_${TIMESTAMP}.sql"

mkdir -p ${BACKUP_DIR}

docker exec mr_game_ops_db pg_dump -U mr_admin mr_game_ops > ${BACKUP_FILE}

gzip ${BACKUP_FILE}

# 保留最近7天的备份
find ${BACKUP_DIR} -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: ${BACKUP_FILE}.gz"
```

**4.2 配置cron定时任务**

```bash
# 每天凌晨2点备份
0 2 * * * /path/to/scripts/backup_db.sh >> /var/log/mr_backup.log 2>&1
```

---

#### Task 5: 监控和日志

**5.1 健康检查端点**

确保以下端点可用:
- `GET /health` - 应用健康状态
- `GET /health/db` - 数据库连接状态
- `GET /health/redis` - Redis连接状态

**5.2 日志收集**

配置日志持久化:
```yaml
services:
  backend:
    volumes:
      - ./logs/backend:/app/logs

  postgres:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

**5.3 简单监控脚本**

`scripts/health_check.sh`:
```bash
#!/bin/bash

BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:80"

# 检查后端
if curl -f -s "${BACKEND_URL}/health" > /dev/null; then
    echo "✅ Backend is healthy"
else
    echo "❌ Backend is down"
    # 发送告警邮件或钉钉通知
fi

# 检查前端
if curl -f -s "${FRONTEND_URL}" > /dev/null; then
    echo "✅ Frontend is accessible"
else
    echo "❌ Frontend is down"
fi

# 检查数据库
if docker exec mr_game_ops_db pg_isready -U mr_admin > /dev/null; then
    echo "✅ Database is ready"
else
    echo "❌ Database is not ready"
fi
```

---

### 第三阶段: UAT用户验收测试 (3-5天)

#### Task 6: 准备UAT环境

**6.1 部署到UAT服务器**

```bash
# 拉取最新代码
git pull origin 001-mr-v2

# 构建并启动
docker-compose -f docker-compose.yml up -d --build

# 运行数据库迁移
docker-compose exec backend alembic upgrade head

# 导入种子数据
docker-compose exec backend python scripts/seed_data.py
```

**6.2 创建UAT测试账号**

```sql
-- 运营商测试账号
INSERT INTO operator_accounts (username, full_name, email, phone, password_hash)
VALUES ('uat_operator', 'UAT测试运营商', 'uat@test.com', '13800000001', '<bcrypt_hash>');

-- 管理员测试账号
INSERT INTO admin_accounts (username, full_name, email, password_hash, role)
VALUES ('uat_admin', 'UAT测试管理员', 'uat_admin@test.com', '<bcrypt_hash>', 'super_admin');

-- 财务测试账号
INSERT INTO finance_accounts (username, full_name, email, password_hash, role)
VALUES ('uat_finance', 'UAT测试财务', 'uat_finance@test.com', '<bcrypt_hash>', 'accountant');
```

---

#### Task 7: UAT测试清单

**7.1 运营商端测试**

- [ ] 注册新账号
- [ ] 登录并查看仪表盘
- [ ] 创建运营点
- [ ] 申请应用授权
- [ ] 充值测试 (使用沙箱环境)
- [ ] 查看使用记录
- [ ] 申请退款
- [ ] 申请发票
- [ ] 查看统计数据

**7.2 管理员端测试**

- [ ] 登录管理员账号
- [ ] 查看运营商列表
- [ ] 创建新应用
- [ ] 审批授权申请
- [ ] **使用新增的授权管理页面**
- [ ] 查看交易记录

**7.3 财务端测试**

- [ ] 登录财务账号
- [ ] 查看仪表盘
- [ ] 审核退款申请
- [ ] 审核发票申请
- [ ] 生成财务报表
- [ ] 查看审计日志

**7.4 集成测试**

- [ ] 完整业务流程: 注册 → 充值 → 申请授权 → 审批 → 使用 → 消费 → 退款
- [ ] 权限控制: 测试各角色只能访问授权的功能
- [ ] 支付流程: 测试支付宝/微信支付回调
- [ ] 数据一致性: 验证余额、交易记录、统计数据的一致性

---

### 第四阶段: 生产发布 (1-2天)

#### Task 8: 生产发布检查清单

**8.1 发布前检查**

- [ ] 所有UAT问题已修复
- [ ] 数据库备份已配置
- [ ] 监控和告警已设置
- [ ] 生产环境配置已审查
- [ ] SSL证书已配置 (如果有域名)
- [ ] 防火墙规则已配置
- [ ] DNS记录已配置 (如果有域名)

**8.2 发布步骤**

```bash
# 1. 备份现有数据 (如果是升级)
./scripts/backup_db.sh

# 2. 拉取生产代码
git checkout 001-mr-v2
git pull origin 001-mr-v2

# 3. 构建并启动生产环境
docker-compose -f docker-compose.yml down
docker-compose -f docker-compose.yml up -d --build

# 4. 运行数据库迁移
docker-compose -f docker-compose.yml exec backend alembic upgrade head

# 5. 导入种子数据 (仅首次部署)
docker-compose -f docker-compose.yml exec backend python scripts/seed_data.py

# 6. 健康检查
./scripts/health_check.sh

# 7. 查看日志
docker-compose -f docker-compose.yml logs -f
```

**8.3 回滚计划**

如果发现严重问题:
```bash
# 停止新版本
docker-compose -f docker-compose.yml down

# 恢复数据库备份
docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops < /backups/postgres/mr_game_ops_YYYYMMDD_HHMMSS.sql

# 切换到上一个稳定版本
git checkout <previous-stable-commit>
docker-compose -f docker-compose.yml up -d --build
```

---

## 📝 MVP发布时间表

| 阶段 | 任务 | 负责人 | 预计时间 | 状态 |
|------|------|--------|----------|------|
| **阶段1** | 补充授权管理页面 | 开发 | 1-2天 | ⏳ 待开始 |
| **阶段1** | 创建测试数据 | 开发 | 0.5天 | ⏳ 待开始 |
| **阶段2** | 生产环境配置 | DevOps | 1天 | ⏳ 待开始 |
| **阶段2** | 备份策略配置 | DevOps | 0.5天 | ⏳ 待开始 |
| **阶段2** | 监控和日志配置 | DevOps | 0.5天 | ⏳ 待开始 |
| **阶段3** | 部署UAT环境 | DevOps | 0.5天 | ⏳ 待开始 |
| **阶段3** | UAT测试执行 | QA/业务 | 2-3天 | ⏳ 待开始 |
| **阶段3** | Bug修复 | 开发 | 1-2天 | ⏳ 待开始 |
| **阶段4** | 生产发布准备 | DevOps | 0.5天 | ⏳ 待开始 |
| **阶段4** | 生产发布 | DevOps | 0.5天 | ⏳ 待开始 |
| **总计** | | | **10-14天** | |

---

## 🎯 成功标准

MVP发布成功的标准:

1. ✅ 所有核心功能可用 (运营商端14功能 + 管理员端7功能 + 财务端6功能)
2. ✅ E2E测试通过率 100% (40/40)
3. ✅ UAT测试无阻塞性Bug
4. ✅ 系统稳定性 > 99% (24小时监控)
5. ✅ 关键页面加载时间 < 2秒
6. ✅ 数据库自动备份正常运行
7. ✅ 监控和告警机制正常

---

## 📋 MVP后续迭代规划

MVP发布后,根据用户反馈进行迭代开发:

### V1.1 (MVP+1个月)
- 补充US7全局统计功能
- 优化性能和用户体验
- 增加更多报表类型

### V1.2 (MVP+2个月)
- 系统公告功能
- API Key管理
- 更多支付方式

### V2.0 (MVP+3-4个月)
- 移动端适配
- 高级权限管理
- 数据导出功能

---

**下一步行动**: 开始实施Task 1 - 补充管理员授权管理页面

**是否需要我现在开始实现授权管理页面?**
