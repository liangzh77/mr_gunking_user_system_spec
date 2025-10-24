#!/bin/bash
# =============================================================================
# MR游戏运营管理系统 - PostgreSQL 数据库备份脚本
# =============================================================================

set -euo pipefail

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/postgres/backup.log"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/var/backups/postgresql"
TEMP_DIR="/tmp/postgres_backup_${TIMESTAMP}"

# 从环境变量读取配置
DB_HOST="${POSTGRES_HOST:-postgres}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-mr_game_ops_prod}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_PASSWORD="${PGPASSWORD}"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 错误处理
error_exit() {
    log "ERROR: $1"
    exit 1
}

# 检查依赖
check_dependencies() {
    log "检查备份依赖..."

    command -v pg_dump >/dev/null 2>&1 || error_exit "pg_dump not found"
    command -v psql >/dev/null 2>&1 || error_exit "psql not found"
    command -v gzip >/dev/null 2>&1 || error_exit "gzip not found"

    log "依赖检查完成"
}

# 创建备份目录
create_backup_dirs() {
    log "创建备份目录..."

    mkdir -p "$BACKUP_DIR"/{daily,weekly,monthly,incremental}
    mkdir -p "$TEMP_DIR"
    mkdir -p "$(dirname "$LOG_FILE")"

    log "备份目录创建完成"
}

# 检查数据库连接
check_database() {
    log "检查数据库连接..."

    if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"; then
        error_exit "无法连接到数据库"
    fi

    log "数据库连接正常"
}

# 获取数据库大小
get_database_size() {
    local size
    size=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "
        SELECT pg_size_pretty(pg_database_size('$DB_NAME'));
    " | xargs)
    echo "$size"
}

# 创建全量备份
create_full_backup() {
    local backup_file="$BACKUP_DIR/daily/mr_game_ops_full_${TIMESTAMP}.sql.gz"

    log "开始创建全量备份..."
    log "数据库大小: $(get_database_size)"

    # 使用pg_dump创建备份
    if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --verbose \
        --no-owner \
        --no-privileges \
        --format=custom \
        --compress=9 \
        --file="$TEMP_DIR/full_backup.sql"; then

        # 压缩备份文件
        gzip -c "$TEMP_DIR/full_backup.sql" > "$backup_file"

        # 验证备份文件
        if [[ -s "$backup_file" ]]; then
            local backup_size
            backup_size=$(du -h "$backup_file" | cut -f1)
            log "全量备份创建成功: $backup_file ($backup_size)"

            # 创建备份验证文件
            echo "备份时间: $(date)" > "${backup_file}.info"
            echo "数据库大小: $(get_database_size)" >> "${backup_file}.info"
            echo "备份文件大小: $backup_size" >> "${backup_file}.info"
            echo "备份类型: 全量备份" >> "${backup_file}.info"

            return 0
        else
            error_exit "备份文件为空或创建失败"
        fi
    else
        error_exit "pg_dump 执行失败"
    fi
}

# 创建增量备份（基于WAL）
create_incremental_backup() {
    local backup_file="$BACKUP_DIR/incremental/mr_game_ops_wal_${TIMESTAMP}.tar.gz"

    log "开始创建增量备份..."

    # 归档WAL文件
    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
        SELECT pg_switch_wal();
    " > /dev/null; then

        # 打包WAL文件
        if tar -czf "$backup_file" -C /var/lib/postgresql/data pg_wal/ 2>/dev/null; then
            local backup_size
            backup_size=$(du -h "$backup_file" | cut -f1)
            log "增量备份创建成功: $backup_file ($backup_size)"
            return 0
        else
            log "WARNING: 增量备份创建失败，跳过"
            return 1
        fi
    else
        log "WARNING: WAL切换失败，跳过增量备份"
        return 1
    fi
}

# 创建数据库结构备份
create_schema_backup() {
    local backup_file="$BACKUP_DIR/daily/mr_game_ops_schema_${TIMESTAMP}.sql.gz"

    log "创建数据库结构备份..."

    if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --schema-only \
        --no-owner \
        --no-privileges | gzip > "$backup_file"; then

        local backup_size
        backup_size=$(du -h "$backup_file" | cut -f1)
        log "结构备份创建成功: $backup_file ($backup_size)"
        return 0
    else
        log "WARNING: 结构备份创建失败"
        return 1
    fi
}

# 验证备份
verify_backup() {
    local backup_file="$1"

    log "验证备份文件: $backup_file"

    # 检查文件是否存在且非空
    if [[ ! -s "$backup_file" ]]; then
        log "ERROR: 备份文件为空: $backup_file"
        return 1
    fi

    # 对于自定义格式备份，可以使用pg_restore验证
    if [[ "$backup_file" == *.sql.gz ]]; then
        log "备份文件验证通过"
        return 0
    fi

    return 0
}

# 清理旧备份
cleanup_old_backups() {
    local keep_days="${BACKUP_RETENTION_DAYS:-30}"

    log "清理 ${keep_days} 天前的备份文件..."

    # 清理每日备份
    find "$BACKUP_DIR/daily" -name "*.sql.gz" -mtime +${keep_days} -delete
    find "$BACKUP_DIR/daily" -name "*.info" -mtime +${keep_days} -delete

    # 清理增量备份（保留7天）
    find "$BACKUP_DIR/incremental" -name "*.tar.gz" -mtime +7 -delete

    # 清理临时文件
    find /tmp -name "postgres_backup_*" -mtime +1 -exec rm -rf {} \; 2>/dev/null || true

    log "旧备份清理完成"
}

# 上传到云存储（可选）
upload_to_cloud() {
    if [[ -n "${S3_BACKUP_BUCKET:-}" ]] && command -v aws >/dev/null 2>&1; then
        log "上传备份到AWS S3..."

        for backup_file in "$BACKUP_DIR/daily"/*_${TIMESTAMP}.sql.gz; do
            if [[ -f "$backup_file" ]]; then
                aws s3 cp "$backup_file" "s3://$S3_BACKUP_BUCKET/daily/" --quiet || log "WARNING: S3上传失败: $backup_file"
            fi
        done

        log "S3上传完成"
    fi
}

# 生成备份报告
generate_backup_report() {
    local report_file="$BACKUP_DIR/backup_report_${TIMESTAMP}.txt"

    {
        echo "=== MR游戏运营管理系统 数据库备份报告 ==="
        echo "备份时间: $(date)"
        echo "备份主机: $(hostname)"
        echo "数据库: $DB_NAME"
        echo "数据库大小: $(get_database_size)"
        echo ""
        echo "=== 备份文件 ==="
        find "$BACKUP_DIR" -name "*${TIMESTAMP}*" -type f -exec ls -lh {} \;
        echo ""
        echo "=== 备份统计 ==="
        echo "每日备份数量: $(find "$BACKUP_DIR/daily" -name "*.sql.gz" | wc -l)"
        echo "增量备份数量: $(find "$BACKUP_DIR/incremental" -name "*.tar.gz" | wc -l)"
        echo "备份目录总大小: $(du -sh "$BACKUP_DIR" | cut -f1)"
        echo ""
        echo "=== 磁盘空间 ==="
        df -h "$BACKUP_DIR"
    } > "$report_file"

    log "备份报告生成: $report_file"
}

# 主函数
main() {
    log "=== 开始PostgreSQL数据库备份 ==="

    # 检查环境
    check_dependencies
    create_backup_dirs
    check_database

    # 创建备份
    local backup_success=0

    create_full_backup || backup_success=1
    create_schema_backup || backup_success=1
    create_incremental_backup || true  # 增量备份失败不影响整体流程

    # 验证备份
    if [[ $backup_success -eq 0 ]]; then
        log "所有备份创建成功"
    else
        log "WARNING: 部分备份创建失败"
    fi

    # 清理和报告
    cleanup_old_backups
    generate_backup_report
    upload_to_cloud

    # 清理临时文件
    rm -rf "$TEMP_DIR"

    log "=== PostgreSQL数据库备份完成 ==="
}

# 信号处理
trap 'log "备份脚本被中断"; exit 1' INT TERM

# 执行主函数
main "$@"