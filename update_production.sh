#!/bin/bash
# 生产环境更新脚本
# 使用方法: ./update_production.sh

set -e  # 遇到错误立即退出

echo "=========================================="
echo "开始生产环境更新流程"
echo "=========================================="
echo ""

# 1. 备份数据库
echo "1. 备份数据库..."
mkdir -p database_backups
BACKUP_FILE="database_backups/backup_$(date +%Y%m%d_%H%M%S).sql"
docker-compose exec -T postgres pg_dump -U mr_admin mr_game_ops > "$BACKUP_FILE"
echo "✓ 数据库已备份到: $BACKUP_FILE"
echo ""

# 2. 拉取最新代码
echo "2. 拉取最新代码..."
git pull origin 001-mr-v2
echo "✓ 代码已更新"
echo ""

# 3. 检查当前数据库版本
echo "3. 检查当前数据库版本..."
docker-compose exec backend alembic current
echo ""

# 4. 重新构建并启动容器
echo "4. 重新构建并启动容器..."
docker-compose up -d --build
echo "✓ 容器已重建"
echo ""

# 5. 等待后端容器启动
echo "5. 等待后端容器启动..."
sleep 15
echo "✓ 等待完成"
echo ""

# 6. 应用数据库迁移
echo "6. 应用数据库迁移..."
docker-compose exec backend alembic upgrade head
echo "✓ 数据库迁移已应用"
echo ""

# 7. 检查新的数据库版本
echo "7. 检查新的数据库版本..."
docker-compose exec backend alembic current
echo ""

# 8. 重启后端容器
echo "8. 重启后端容器..."
docker-compose restart backend
sleep 5
echo "✓ 后端容器已重启"
echo ""

# 9. 检查容器状态
echo "9. 检查容器状态..."
docker-compose ps
echo ""

# 10. 查看后端日志
echo "10. 查看后端日志 (最近50行)..."
docker-compose logs backend --tail 50
echo ""

echo "=========================================="
echo "✓ 生产环境更新完成!"
echo "备份文件: $BACKUP_FILE"
echo "=========================================="
