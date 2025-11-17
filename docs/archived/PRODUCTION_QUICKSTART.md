# 生产环境快速部署指南

这是一个快速参考文档，适用于有经验的系统管理员快速部署MR游戏运营管理系统。

详细说明请参考 [DEPLOYMENT.md](./DEPLOYMENT.md)

## 🚀 5分钟快速部署（Docker方式）

### 1. 环境准备

```bash
# Ubuntu 20.04/22.04 LTS
sudo apt update && sudo apt install -y git curl docker.io docker-compose ufw

# 配置防火墙
sudo ufw allow 22,80,443/tcp && sudo ufw enable

# 克隆项目
git clone <repository-url> && cd mr_gunking_user_system_spec
```

### 2. 配置环境变量

```bash
# 生成密钥
python3 -c "import secrets; print(secrets.token_urlsafe(32))" # SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))" # JWT_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(24)[:32])" # ENCRYPTION_KEY

# 编辑配置
cd backend
cp .env.production .env
vim .env  # 修改所有 CHANGE_THIS_* 占位符
```

**⚠️ 必须修改**:
- `SECRET_KEY`
- `JWT_SECRET_KEY`
- `ENCRYPTION_KEY`
- `DATABASE_URL` 中的密码
- `REDIS_PASSWORD`
- `CORS_ORIGINS` 为你的域名

### 3. 配置SSL证书

```bash
# Let's Encrypt
sudo apt install -y certbot
sudo certbot certonly --standalone -d yourdomain.com

# 复制证书到nginx目录
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ../nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ../nginx/ssl/
```

### 4. 启动服务

```bash
cd ..

# 设置密码环境变量
export POSTGRES_PASSWORD=YOUR_DB_PASSWORD
export REDIS_PASSWORD=YOUR_REDIS_PASSWORD

# 启动
docker-compose up -d

# 初始化数据库
docker exec -it mr_game_ops_backend_prod alembic upgrade head
docker exec -it mr_game_ops_backend_prod python init_data.py
```

### 5. 验证

```bash
# 检查服务
docker-compose ps

# 测试健康检查
curl http://localhost:8000/health

# 测试前端
curl https://yourdomain.com
```

**默认管理员账户**: `admin` / `Admin123`

---

## 📋 配置检查清单

### 安全配置
- [ ] 修改所有默认密码和密钥
- [ ] `.env` 文件权限设置为 600
- [ ] `DEBUG=false`
- [ ] CORS仅允许生产域名
- [ ] SSL证书配置且有效
- [ ] 防火墙规则正确（仅80/443/22）

### 数据库配置
- [ ] PostgreSQL密码强度 >= 16字符
- [ ] 数据库连接池大小适当（默认20）
- [ ] 自动备份配置（每日）

### Redis配置
- [ ] Redis密码强度 >= 16字符
- [ ] 持久化启用（AOF）
- [ ] 内存限制配置（默认512MB）

### Nginx配置
- [ ] `server_name` 改为实际域名
- [ ] SSL证书路径正确
- [ ] 限流规则适当

### 监控和日志
- [ ] 日志轮转配置
- [ ] 健康检查脚本（cron每5分钟）
- [ ] 磁盘空间监控

---

## 🔧 常用命令

### Docker操作

```bash
# 查看日志
docker-compose logs -f backend

# 重启服务
docker-compose restart backend

# 查看资源使用
docker stats

# 进入容器
docker exec -it mr_game_ops_backend_prod bash
```

### 数据库操作

```bash
# 备份
docker exec mr_game_ops_db_prod pg_dump -U mr_admin mr_game_ops | gzip > backup_$(date +%Y%m%d).sql.gz

# 恢复
gunzip -c backup_YYYYMMDD.sql.gz | docker exec -i mr_game_ops_db_prod psql -U mr_admin mr_game_ops

# 查看连接数
docker exec mr_game_ops_db_prod psql -U mr_admin -d mr_game_ops -c "SELECT count(*) FROM pg_stat_activity;"
```

### 更新部署

```bash
# 拉取代码
git pull origin production

# 重新构建并更新
docker-compose build
docker-compose up -d

# 运行迁移
docker exec -it mr_game_ops_backend_prod alembic upgrade head
```

---

## 🚨 紧急处理

### 服务无响应

```bash
# 检查服务状态
docker-compose ps

# 查看资源使用
docker stats
free -h
df -h

# 重启服务
docker-compose restart
```

### 数据库性能问题

```bash
# 查看慢查询
docker exec mr_game_ops_db_prod psql -U mr_admin -d mr_game_ops -c "
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 seconds'
ORDER BY duration DESC;
"

# 分析表
docker exec mr_game_ops_db_prod psql -U mr_admin -d mr_game_ops -c "ANALYZE;"
```

### Redis内存不足

```bash
# 检查内存使用
docker exec mr_game_ops_redis_prod redis-cli -a YOUR_PASSWORD INFO memory

# 清空过期键
docker exec mr_game_ops_redis_prod redis-cli -a YOUR_PASSWORD FLUSHDB
```

---

## 📊 性能调优

### 后端Worker数量

```bash
# 编辑docker-compose.yml
WORKERS: "4"  # 推荐: (CPU核心数 * 2) + 1
```

### PostgreSQL连接池

```env
# backend/.env
DATABASE_POOL_SIZE=20      # 增加至40（高负载）
DATABASE_MAX_OVERFLOW=10   # 增加至20
```

### Redis内存限制

```bash
# 编辑docker-compose.yml
--maxmemory 512mb  # 根据可用内存调整
```

---

## 🔍 监控指标

### 关键指标

| 指标 | 正常范围 | 告警阈值 |
|------|---------|---------|
| API响应时间 | < 100ms (P95) | > 2s |
| CPU使用率 | < 70% | > 90% |
| 内存使用率 | < 80% | > 90% |
| 磁盘使用率 | < 70% | > 85% |
| 数据库连接数 | < 50 | > 80 |
| 错误率 | < 1% | > 5% |

### 监控命令

```bash
# CPU和内存
docker stats --no-stream

# 磁盘
df -h

# 网络
netstat -an | grep ESTABLISHED | wc -l

# 应用健康
curl -w "@curl-format.txt" http://localhost:8000/health
```

---

## 📞 问题排查

### 1. 检查日志

```bash
# 后端错误日志
docker logs mr_game_ops_backend_prod --tail 100

# Nginx错误日志
docker logs mr_game_ops_nginx --tail 100

# 数据库日志
docker logs mr_game_ops_db_prod --tail 100
```

### 2. 测试连通性

```bash
# 测试数据库
docker exec mr_game_ops_backend_prod python -c "
from src.core.config import settings
print(settings.DATABASE_URL)
"

# 测试Redis
docker exec mr_game_ops_backend_prod python -c "
from src.core.config import settings
print(settings.REDIS_URL)
"

# 测试API
curl -v http://localhost:8000/health
```

### 3. 常见错误码

| 错误码 | 原因 | 解决方案 |
|--------|-----|---------|
| 502 | 后端服务未运行 | 检查backend容器状态 |
| 500 | 应用内部错误 | 查看backend日志 |
| 503 | 服务不可用 | 检查资源使用情况 |
| 504 | 请求超时 | 增加timeout配置 |

---

## 📚 文档索引

- **完整部署指南**: [DEPLOYMENT.md](./DEPLOYMENT.md)
- **开发指南**: [../README.md](../README.md)
- **API文档**: https://yourdomain.com/api/docs
- **功能规格**: [../specs/001-mr/spec.md](../specs/001-mr/spec.md)

---

**最后更新**: 2025-10-16
