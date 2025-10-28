#!/bin/bash
# =============================================================================
# Database Backup Script
# =============================================================================
# 功能：
# - 自动备份PostgreSQL数据库
# - 支持自动清理旧备份
# - 可配置为cron定时任务
# =============================================================================

set -e  # 遇到错误立即退出

# 配置
BACKUP_DIR="./backups"
CONTAINER_NAME="mr_game_ops_db_prod"
DB_USER="${DB_USER:-mr_admin}"
DB_NAME="${DB_NAME:-mr_game_ops}"
RETENTION_DAYS=7  # 保留最近7天的备份
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup_${DB_NAME}_${DATE}.sql"
COMPRESSED_FILE="${BACKUP_FILE}.gz"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 创建备份目录
mkdir -p "$BACKUP_DIR"

log_info "开始数据库备份..."
log_info "数据库: $DB_NAME"
log_info "备份文件: $COMPRESSED_FILE"

# 检查容器是否运行
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    log_error "数据库容器 $CONTAINER_NAME 未运行！"
    exit 1
fi

# 执行备份
log_info "导出数据库..."
if docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" -d "$DB_NAME" --clean --if-exists > "$BACKUP_FILE"; then
    log_info "数据库导出成功 ✓"
else
    log_error "数据库导出失败！"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# 压缩备份文件
log_info "压缩备份文件..."
if gzip "$BACKUP_FILE"; then
    log_info "备份文件压缩完成 ✓"
else
    log_error "备份文件压缩失败！"
    exit 1
fi

# 获取备份文件大小
BACKUP_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
log_info "备份文件大小: $BACKUP_SIZE"

# 清理旧备份
log_info "清理 $RETENTION_DAYS 天前的旧备份..."
DELETED_COUNT=$(find "$BACKUP_DIR" -name "backup_${DB_NAME}_*.sql.gz" -type f -mtime +$RETENTION_DAYS -delete -print | wc -l)

if [ "$DELETED_COUNT" -gt 0 ]; then
    log_info "已删除 $DELETED_COUNT 个旧备份文件"
else
    log_info "没有需要清理的旧备份"
fi

# 显示当前备份列表
log_info "当前备份列表:"
ls -lh "$BACKUP_DIR"/backup_${DB_NAME}_*.sql.gz 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'

log_info "数据库备份完成！ ✓"

echo ""
echo "========================================"
echo "  备份摘要"
echo "========================================"
echo "备份文件: $COMPRESSED_FILE"
echo "文件大小: $BACKUP_SIZE"
echo "保留期限: $RETENTION_DAYS 天"
echo ""
echo "恢复命令:"
echo "  gunzip -c $COMPRESSED_FILE | docker exec -i $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME"
echo ""

exit 0
