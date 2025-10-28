# MR游戏运营管理系统 - 系统运维手册

## 目录
1. [系统架构概述](#系统架构概述)
2. [部署环境准备](#部署环境准备)
3. [系统部署指南](#系统部署指南)
4. [日常运维操作](#日常运维操作)
5. [监控和告警](#监控和告警)
6. [备份和恢复](#备份和恢复)
7. [性能调优](#性能调优)
8. [故障处理](#故障处理)
9. [安全管理](#安全管理)
10. [维护计划](#维护计划)

---

## 系统架构概述

### 整体架构

```mermaid
graph TB
    subgraph "用户层"
        A[Web浏览器]
        B[移动端]
        C[API客户端]
    end

    subgraph "负载均衡层"
        D[Nginx负载均衡器]
    end

    subgraph "应用层"
        E[前端应用]
        F[后端API服务]
        G[WebSocket服务]
    end

    subgraph "数据层"
        H[PostgreSQL主库]
        I[PostgreSQL从库]
        J[Redis缓存]
        K[文件存储]
    end

    subgraph "监控层"
        L[Prometheus]
        M[Grafana]
        N[AlertManager]
        O[ELK日志系统]
    end

    A --> D
    B --> D
    C --> D
    D --> E
    D --> F
    D --> G
    F --> H
    F --> I
    F --> J
    F --> K
    L --> M
    L --> N
    F --> O
```

### 技术栈

#### 前端技术
- **框架**：Vue 3 + TypeScript
- **UI组件**：Element Plus
- **构建工具**：Vite
- **状态管理**：Pinia
- **路由管理**：Vue Router

#### 后端技术
- **框架**：FastAPI + Python 3.11+
- **数据库**：PostgreSQL 14+
- **缓存**：Redis 6+
- **ORM**：SQLAlchemy 2.0+
- **认证**：JWT + HMAC-SHA256

#### 基础设施
- **容器化**：Docker + Docker Compose
- **负载均衡**：Nginx
- **监控**：Prometheus + Grafana
- **日志**：ELK Stack
- **CI/CD**：GitLab CI

---

## 部署环境准备

### 硬件要求

#### 最小配置
```yaml
应用服务器:
  CPU: 4核
  内存: 8GB
  硬盘: 100GB SSD
  网络: 100Mbps

数据库服务器:
  CPU: 8核
  内存: 16GB
  硬盘: 500GB SSD
  网络: 1Gbps

缓存服务器:
  CPU: 4核
  内存: 8GB
  硬盘: 50GB SSD
  网络: 1Gbps
```

#### 推荐配置
```yaml
应用服务器:
  CPU: 8核
  内存: 16GB
  硬盘: 200GB SSD
  网络: 1Gbps

数据库服务器:
  CPU: 16核
  内存: 32GB
  硬盘: 1TB SSD
  网络: 10Gbps

缓存服务器:
  CPU: 8核
  内存: 32GB
  硬盘: 100GB SSD
  网络: 10Gbps
```

### 软件要求

#### 操作系统
```yaml
推荐系统:
  - CentOS 8.x
  - Ubuntu 20.04 LTS
  - Red Hat Enterprise Linux 8.x

要求:
  - 内核版本 4.0+
  - 系统更新至最新
  - 防火墙配置正确
```

#### 必需软件
```yaml
基础软件:
  - Docker 20.10+
  - Docker Compose 2.0+
  - Git 2.25+
  - Nginx 1.20+

数据库:
  - PostgreSQL 14+
  - Redis 6+

监控工具:
  - Prometheus
  - Grafana
  - AlertManager
```

### 网络配置

#### 端口要求
```yaml
对外服务端口:
  - 80: HTTP服务
  - 443: HTTPS服务
  - 8000: API服务（内部）
  - 3000: 前端服务（内部）

内部服务端口:
  - 5432: PostgreSQL
  - 6379: Redis
  - 9090: Prometheus
  - 3001: Grafana

安全要求:
  - 关闭不必要端口
  - 配置防火墙规则
  - 启用SSL证书
  - 配置访问控制
```

---

## 系统部署指南

### 快速部署

#### 1. 环境检查
```bash
# 检查Docker版本
docker --version
docker-compose --version

# 检查系统资源
free -h
df -h

# 检查网络连接
ping 8.8.8.8
```

#### 2. 代码部署
```bash
# 克隆代码仓库
git clone https://github.com/your-org/mr-game-ops.git
cd mr-game-ops

# 检出对应版本
git checkout v1.0.0

# 复制配置文件
cp .env.example .env
cp docker-compose.prod.yml.example docker-compose.prod.yml
```

#### 3. 配置修改
```bash
# 编辑环境配置
vim .env

# 关键配置项
DATABASE_URL=postgresql://user:password@postgres:5432/mr_game_ops
REDIS_URL=redis://redis:6379/0
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=https://yourdomain.com
```

#### 4. 启动服务
```bash
# 启动数据库
docker-compose -f docker-compose.postgres.yml up -d

# 等待数据库就绪
sleep 30

# 启动应用
docker-compose -f docker-compose.prod.yml up -d

# 启动监控
docker-compose -f docker-compose.monitoring.yml up -d
```

### 详细部署步骤

#### 1. 基础环境配置

##### 安装Docker
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# CentOS/RHEL
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io
sudo systemctl start docker
sudo systemctl enable docker
```

##### 安装Docker Compose
```bash
# 下载Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.12.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker-compose --version
```

#### 2. 数据库部署

##### PostgreSQL部署
```bash
# 创建数据目录
sudo mkdir -p /opt/mr-game-ops/postgres/{data,logs,backup}
sudo chown -R 999:999 /opt/mr-game-ops/postgres

# 启动PostgreSQL
docker-compose -f docker-compose.postgres.yml up -d

# 检查服务状态
docker-compose -f docker-compose.postgres.yml ps

# 连接数据库测试
docker exec -it mr_game_ops_db_prod psql -U mr_admin -d mr_game_ops
```

##### 数据库初始化
```bash
# 进入后端容器
docker exec -it mr_game_ops_backend_prod bash

# 运行数据库迁移
alembic upgrade head

# 创建初始数据
python scripts/init_data.py

# 退出容器
exit
```

#### 3. Redis部署

##### Redis主从配置
```bash
# 创建Redis配置目录
mkdir -p redis/{config,data,logs}

# 启动Redis集群
docker-compose -f docker-compose.redis.yml up -d

# 检查Redis状态
docker exec -it mr_game_ops_redis_master redis-cli info replication
```

#### 4. 应用部署

##### 构建应用镜像
```bash
# 构建后端镜像
cd backend
docker build -t mr-game-ops-backend:v1.0.0 .

# 构建前端镜像
cd ../frontend
docker build -t mr-game-ops-frontend:v1.0.0 .
```

##### 配置Nginx
```bash
# 复制Nginx配置
sudo cp nginx/mr-game-ops.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/mr-game-ops.conf /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
```

##### 启动应用服务
```bash
# 启动应用
docker-compose -f docker-compose.prod.yml up -d

# 检查服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

#### 5. 监控部署

##### 部署监控服务
```bash
# 启动监控栈
./scripts/setup_monitoring.sh

# 检查监控服务
docker-compose -f docker-compose.monitoring.yml ps
```

##### 配置Grafana
```bash
# 访问Grafana
# http://your-domain:3000
# 默认用户名/密码: admin/admin123

# 导入监控仪表板
# 配置数据源
# 设置告警规则
```

---

## 日常运维操作

### 服务管理

#### 查看服务状态
```bash
# 查看所有容器状态
docker-compose -f docker-compose.prod.yml ps

# 查看资源使用情况
docker stats

# 查看系统负载
top
htop
```

#### 重启服务
```bash
# 重启单个服务
docker-compose -f docker-compose.prod.yml restart backend

# 重启所有服务
docker-compose -f docker-compose.prod.yml restart

# 优雅关闭服务
docker-compose -f docker-compose.prod.yml down
```

#### 更新服务
```bash
# 拉取最新代码
git pull origin main

# 重新构建镜像
docker-compose -f docker-compose.prod.yml build

# 滚动更新
docker-compose -f docker-compose.prod.yml up -d --no-deps backend
```

### 日志管理

#### 查看日志
```bash
# 查看应用日志
docker-compose -f docker-compose.prod.yml logs -f backend

# 查看最近100行日志
docker-compose -f docker-compose.prod.yml logs --tail=100 backend

# 查看特定时间段的日志
docker-compose -f docker-compose.prod.yml logs --since="2023-01-01T00:00:00" backend
```

#### 日志轮转
```bash
# 配置日志轮转
sudo vim /etc/logrotate.d/mr-game-ops

# 手动执行日志轮转
sudo logrotate -f /etc/logrotate.d/mr-game-ops
```

### 数据库维护

#### 数据库备份
```bash
# 每日备份脚本
./scripts/backup_database.sh

# 手动备份
docker exec mr_game_ops_db_prod pg_dump -U mr_admin mr_game_ops > backup_$(date +%Y%m%d).sql

# 查看备份文件
ls -la /opt/mr-game-ops/postgres/backup/
```

#### 数据库优化
```bash
# 连接数据库
docker exec -it mr_game_ops_db_prod psql -U mr_admin -d mr_game_ops

# 查看数据库状态
SELECT * FROM pg_stat_activity;
SELECT * FROM pg_stat_database;

# 重建索引
REINDEX DATABASE mr_game_ops;

# 更新统计信息
ANALYZE;
```

### 缓存管理

#### Redis管理
```bash
# 连接Redis
docker exec -it mr_game_ops_redis_master redis-cli

# 查看Redis信息
INFO replication
INFO memory
INFO stats

# 清理过期键
redis-cli --scan --pattern "expired:*" | xargs redis-cli del

# 重启Redis
docker-compose -f docker-compose.redis.yml restart redis_master
```

---

## 监控和告警

### 系统监控

#### 关键指标
```yaml
系统指标:
  - CPU使用率
  - 内存使用率
  - 磁盘使用率
  - 网络流量
  - 系统负载

应用指标:
  - 响应时间
  - 错误率
  - 并发用户数
  - 吞吐量
  - 可用性

数据库指标:
  - 连接数
  - 查询性能
  - 锁等待
  - 缓存命中率
```

#### Prometheus配置
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'mr-game-ops'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s
```

#### Grafana仪表板
```yaml
系统监控:
  - CPU/内存/磁盘使用率
  - 网络流量监控
  - 系统负载监控

应用监控:
  - API响应时间
  - 错误率统计
  - 用户活跃度

业务监控:
  - 用户注册数
  - 交易量统计
  - 收入数据
```

### 告警配置

#### 告警规则
```yaml
# alert_rules.yml
groups:
  - name: mr-game-ops-alerts
    rules:
      - alert: HighCPUUsage
        expr: 100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"
          description: "CPU usage is above 80% for more than 2 minutes"

      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service is down"
          description: "Service {{ $labels.job }} is down"
```

#### 告警通知
```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'alerts@mr-gaming.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
  - name: 'web.hook'
    email_configs:
      - to: 'admin@mr-gaming.com'
        subject: '[MR Gaming] Alert: {{ .GroupLabels.alertname }}'
        body: |
          {{ range .Alerts }}
          Alert: {{ .Annotations.summary }}
          Description: {{ .Annotations.description }}
          {{ end }}
```

---

## 备份和恢复

### 备份策略

#### 数据备份
```bash
#!/bin/bash
# backup_database.sh

BACKUP_DIR="/opt/mr-game-ops/postgres/backup"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="mr_game_ops"
DB_USER="mr_admin"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 数据库备份
docker exec mr_game_ops_db_prod pg_dump -U $DB_USER $DB_NAME | gzip > $BACKUP_DIR/db_backup_$DATE.sql.gz

# 删除7天前的备份
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete

echo "Database backup completed: $BACKUP_DIR/db_backup_$DATE.sql.gz"
```

#### 应用备份
```bash
#!/bin/bash
# backup_application.sh

BACKUP_DIR="/opt/mr-game-ops/backup"
DATE=$(date +%Y%m%d_%H%M%S)

# 备份配置文件
tar -czf $BACKUP_DIR/config_$DATE.tar.gz .env docker-compose*.yml nginx/

# 备份上传文件
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz uploads/

# 备份日志文件
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz logs/

echo "Application backup completed"
```

#### 自动备份配置
```bash
# 添加到crontab
crontab -e

# 每天凌晨2点备份数据库
0 2 * * * /opt/mr-game-ops/scripts/backup_database.sh

# 每周日凌晨3点备份应用
0 3 * * 0 /opt/mr-game-ops/scripts/backup_application.sh
```

### 恢复流程

#### 数据库恢复
```bash
#!/bin/bash
# restore_database.sh

BACKUP_FILE=$1
DB_NAME="mr_game_ops"
DB_USER="mr_admin"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# 停止应用服务
docker-compose -f docker-compose.prod.yml stop backend

# 恢复数据库
gunzip -c $BACKUP_FILE | docker exec -i mr_game_ops_db_prod psql -U $DB_USER $DB_NAME

# 重启应用服务
docker-compose -f docker-compose.prod.yml start backend

echo "Database restore completed"
```

#### 应用恢复
```bash
#!/bin/bash
# restore_application.sh

BACKUP_DIR=$1

if [ -z "$BACKUP_DIR" ]; then
    echo "Usage: $0 <backup_directory>"
    exit 1
fi

# 恢复配置文件
tar -xzf $BACKUP_DIR/config_*.tar.gz

# 恢复上传文件
tar -xzf $BACKUP_DIR/uploads_*.tar.gz

# 重启服务
docker-compose -f docker-compose.prod.yml restart

echo "Application restore completed"
```

---

## 性能调优

### 系统优化

#### Linux内核参数
```bash
# /etc/sysctl.conf
# 网络优化
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.ipv4.tcp_congestion_control = bbr

# 文件描述符限制
fs.file-max = 1000000

# 应用配置
echo "* soft nofile 65535" >> /etc/security/limits.conf
echo "* hard nofile 65535" >> /etc/security/limits.conf
```

#### Docker优化
```yaml
# /etc/docker/daemon.json
{
  "storage-driver": "overlay2",
  "storage-opts": [
    "overlay2.override_kernel_check=true"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
```

### 数据库优化

#### PostgreSQL配置
```bash
# postgresql.conf
# 内存配置
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# 连接配置
max_connections = 200
superuser_reserved_connections = 3

# 检查点配置
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100

# 日志配置
log_min_duration_statement = 1000
log_checkpoints = on
log_connections = on
log_disconnections = on
```

#### 索引优化
```sql
-- 创建复合索引
CREATE INDEX idx_user_status_created ON operator_accounts(status, created_at);
CREATE INDEX idx_transaction_status_date ON transaction_records(status, created_at);

-- 分析查询性能
EXPLAIN ANALYZE SELECT * FROM operator_accounts WHERE status = 'active';

-- 重建索引
REINDEX INDEX CONCURRENTLY idx_user_status_created;
```

### Redis优化

#### Redis配置
```bash
# redis.conf
# 内存配置
maxmemory 2gb
maxmemory-policy allkeys-lru

# 持久化配置
save 900 1
save 300 10
save 60 10000

# 网络配置
tcp-keepalive 300
timeout 0

# 安全配置
requirepass your_redis_password
```

#### 连接池优化
```python
# Redis连接池配置
REDIS_POOL = redis.ConnectionPool(
    host='redis',
    port=6379,
    db=0,
    password='your_redis_password',
    max_connections=50,
    retry_on_timeout=True
)
```

---

## 故障处理

### 常见故障

#### 服务无法启动
```bash
# 检查容器状态
docker-compose -f docker-compose.prod.yml ps

# 查看容器日志
docker-compose -f docker-compose.prod.yml logs backend

# 检查端口占用
netstat -tulpn | grep :8000

# 检查资源使用
docker stats
```

#### 数据库连接失败
```bash
# 检查数据库状态
docker exec mr_game_ops_db_prod pg_isready

# 查看数据库日志
docker logs mr_game_ops_db_prod

# 检查连接数
docker exec mr_game_ops_db_prod psql -U mr_admin -c "SELECT count(*) FROM pg_stat_activity;"

# 重启数据库
docker-compose -f docker-compose.postgres.yml restart
```

#### 性能问题
```bash
# 检查系统负载
top
htop
iotop

# 检查网络延迟
ping your-domain.com
traceroute your-domain.com

# 检查磁盘I/O
iostat -x 1
```

### 故障排查流程

#### 1. 问题定位
```bash
# 确认问题范围
- 检查用户反馈
- 确认影响范围
- 收集错误信息

# 查看系统状态
docker-compose ps
docker stats
docker logs
```

#### 2. 原因分析
```bash
# 分析日志
grep -i error /var/log/mr-game-ops/*.log
journalctl -u docker

# 检查配置
docker-compose config
cat .env
```

#### 3. 解决问题
```bash
# 重启服务
docker-compose restart

# 回滚版本
git checkout previous_version
docker-compose up -d

# 联系支持
# 收集相关信息
# 提交工单
```

---

## 安全管理

### 系统安全

#### 防火墙配置
```bash
# UFW配置
sudo ufw enable
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 5432/tcp
sudo ufw deny 6379/tcp
```

#### SSH安全
```bash
# /etc/ssh/sshd_config
Port 22
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
```

#### 用户权限
```bash
# 创建运维用户
sudo useradd -m ops
sudo usermod -aG sudo ops
sudo usermod -aG docker ops

# 配置SSH密钥
sudo mkdir -p /home/ops/.ssh
sudo cp authorized_keys /home/ops/.ssh/
sudo chown -R ops:ops /home/ops/.ssh
```

### 应用安全

#### SSL证书配置
```bash
# 使用Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo crontab -e
0 12 * * * /usr/bin/certbot renew --quiet
```

#### 环境变量安全
```bash
# 设置文件权限
chmod 600 .env
chown root:root .env

# 使用Docker secrets
echo "your_secret_key" | docker secret create db_password -
```

#### 数据库安全
```sql
-- 创建只读用户
CREATE USER readonly_user WITH PASSWORD 'strong_password';
GRANT CONNECT ON DATABASE mr_game_ops TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;

-- 限制连接数
ALTER USER readonly_user CONNECTION LIMIT 10;
```

---

## 维护计划

### 日常维护

#### 每日检查清单
```yaml
系统检查:
  - [ ] 检查服务状态
  - [ ] 查看系统负载
  - [ ] 检查磁盘空间
  - [ ] 查看错误日志

应用检查:
  - [ ] 检查API响应时间
  - [ ] 查看用户登录情况
  - [ ] 检查数据同步状态
  - [ ] 查看业务指标

安全检查:
  - [ ] 检查登录异常
  - [ ] 查看安全日志
  - [ ] 检查系统更新
  - [ ] 验证备份状态
```

#### 每周维护任务
```yaml
系统维护:
  - [ ] 清理日志文件
  - [ ] 更新系统补丁
  - [ ] 检查备份完整性
  - [ ] 优化数据库

应用维护:
  - [ ] 更新应用版本
  - [ ] 性能分析
  - [ ] 用户反馈处理
  - [ ] 功能测试
```

#### 每月维护任务
```yaml
系统审计:
  - [ ] 安全扫描
  - [ ] 性能评估
  - [ ] 容量规划
  - [ ] 灾难恢复演练

文档更新:
  - [ ] 更新运维文档
  - [ ] 记录变更日志
  - [ ] 培训材料更新
  - [ ] 知识库维护
```

### 预防性维护

#### 容量管理
```bash
# 监控磁盘使用
df -h
du -sh /opt/mr-game-ops/*

# 监控数据库大小
docker exec mr_game_ops_db_prod psql -U mr_admin -c "SELECT pg_size_pretty(pg_database_size('mr_game_ops'));"

# 监控日志大小
find /var/log -name "*.log" -exec ls -lh {} \;
```

#### 性能监控
```bash
# 设置性能基线
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health

# 定期性能测试
./scripts/performance_test.sh

# 分析性能趋势
grep "response_time" /var/log/mr-game-ops/performance.log
```

---

## 附录

### A. 有用命令

#### Docker命令
```bash
# 查看容器
docker ps -a

# 进入容器
docker exec -it container_name bash

# 查看日志
docker logs container_name

# 清理资源
docker system prune -a
```

#### 数据库命令
```bash
# 连接数据库
docker exec -it postgres psql -U user -d database

# 备份数据库
docker exec postgres pg_dump -U user database > backup.sql

# 恢复数据库
docker exec -i postgres psql -U user database < backup.sql
```

#### 系统命令
```bash
# 查看系统信息
uname -a
df -h
free -h
top

# 查看网络状态
netstat -tulpn
ss -tulpn

# 查看进程
ps aux
pstree
```

### B. 配置文件模板

#### Nginx配置
```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### C. 联系信息

```
技术支持热线：400-xxx-xxxx
紧急联系电话：186-xxxx-xxxx
技术支持邮箱：support@mr-gaming.com
项目经理：project-manager@mr-gaming.com
```

---

**文档版本**：v1.0
**更新日期**：2025-10-22
**维护团队**：MR游戏运营管理系统运维部