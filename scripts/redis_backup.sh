#!/bin/bash
# =============================================================================
# MR游戏运营管理系统 - Redis 备份脚本
# 自动备份Redis数据并管理备份文件
# =============================================================================

set -euo pipefail

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${BACKUPS_PATH:-./backups/redis}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"
COMPOSE_FILE="$SCRIPT_DIR/../docker-compose.redis.yml"
ENV_FILE="$SCRIPT_DIR/../.env.redis"

# 保留备份数量
KEEP_BACKUPS=7

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印函数
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "${BLUE}============================================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}============================================================================${NC}"
}

# 检查依赖
check_dependencies() {
    print_info "检查依赖..."

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose 未安装"
        exit 1
    fi

    if [[ ! -f "$COMPOSE_FILE" ]]; then
        print_error "Docker Compose 文件不存在: $COMPOSE_FILE"
        exit 1
    fi

    if [[ -f "$ENV_FILE" ]]; then
        export $(grep -v '^#' "$ENV_FILE" | xargs)
    fi

    print_success "依赖检查完成"
}

# 创建备份目录
create_backup_dir() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="$BACKUP_DIR/$timestamp"

    mkdir -p "$backup_path"
    echo "$backup_path"
}

# 获取Redis容器名称
get_redis_container() {
    local container=$(docker-compose -f "$COMPOSE_FILE" ps -q redis-master | head -1)
    if [[ -z "$container" ]]; then
        print_error "Redis主节点容器未运行"
        exit 1
    fi
    echo "$container"
}

# 创建RDB备份
create_rdb_backup() {
    local backup_path="$1"
    local container="$2"
    local timestamp=$(date +%Y%m%d_%H%M%S)

    print_info "创建RDB快照备份..."

    # 触发BGSAVE
    if docker exec "$container" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" BGSAVE > /dev/null 2>&1; then
        print_info "等待BGSAVE完成..."

        # 等待BGSAVE完成
        while true; do
            local lastsave=$(docker exec "$container" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" LASTSAVE)
            local status=$(docker exec "$container" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" INFO persistence | grep "rdb_bgsave_in_progress")

            if [[ "$status" == *"rdb_bgsave_in_progress:0"* ]]; then
                break
            fi

            print_info "备份进行中..."
            sleep 5
        done

        # 复制RDB文件
        if docker cp "$container:/data/dump.rdb" "$backup_path/dump_$timestamp.rdb"; then
            print_success "RDB备份创建成功: dump_$timestamp.rdb"
        else
            print_error "RDB备份创建失败"
            return 1
        fi
    else
        print_error "无法触发BGSAVE"
        return 1
    fi
}

# 创建AOF备份
create_aof_backup() {
    local backup_path="$1"
    local container="$2"
    local timestamp=$(date +%Y%m%d_%H%M%S)

    print_info "创建AOF备份..."

    # 检查AOF是否启用
    local aof_enabled=$(docker exec "$container" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" CONFIG GET appendonly | tail -1)

    if [[ "$aof_enabled" == "yes" ]]; then
        if docker cp "$container:/data/appendonly.aof" "$backup_path/appendonly_$timestamp.aof"; then
            print_success "AOF备份创建成功: appendonly_$timestamp.aof"
        else
            print_warning "AOF备份创建失败"
        fi
    else
        print_info "AOF未启用，跳过AOF备份"
    fi
}

# 创建配置文件备份
create_config_backup() {
    local backup_path="$1"
    local timestamp=$(date +%Y%m%d_%H%M%S)

    print_info "备份配置文件..."

    # 备份Redis配置
    if docker cp "$(get_redis_container):/usr/local/etc/redis/redis.conf" "$backup_path/redis_$timestamp.conf"; then
        print_success "Redis配置备份成功"
    fi

    # 备份Sentinel配置
    local sentinel_container=$(docker-compose -f "$COMPOSE_FILE" ps -q redis-sentinel-1 | head -1)
    if [[ -n "$sentinel_container" ]]; then
        if docker cp "$sentinel_container:/usr/local/etc/redis/sentinel.conf" "$backup_path/sentinel_$timestamp.conf"; then
            print_success "Sentinel配置备份成功"
        fi
    fi

    # 备份环境变量文件
    if [[ -f "$ENV_FILE" ]]; then
        cp "$ENV_FILE" "$backup_path/env_$timestamp.redis"
        print_success "环境变量备份成功"
    fi

    # 备份Docker Compose文件
    if [[ -f "$COMPOSE_FILE" ]]; then
        cp "$COMPOSE_FILE" "$backup_path/docker-compose_$timestamp.redis.yml"
        print_success "Docker Compose文件备份成功"
    fi
}

# 创建数据导出备份
create_data_export() {
    local backup_path="$1"
    local timestamp=$(date +%Y%m%d_%H%M%S)

    print_info "创建数据导出备份..."

    # 使用redis-cli --rdb 或 redis-dump 工具
    local container=$(get_redis_container)

    # 创建JSON格式的数据导出
    docker exec "$container" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" --scan --pattern "*" > "$backup_path/keys_$timestamp.txt"

    # 导出所有键值对
    print_info "导出键值对数据..."
    while IFS= read -r key; do
        if [[ -n "$key" ]]; then
            local type=$(docker exec "$container" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" TYPE "$key")
            local ttl=$(docker exec "$container" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" TTL "$key")

            case "$type" in
                "string")
                    local value=$(docker exec "$container" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" --raw GET "$key")
                    echo "SET \"$key\" \"$value\"" >> "$backup_path/data_$timestamp.redis"
                    ;;
                "hash")
                    docker exec "$container" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" HGETALL "$key" | \
                    awk '{if(NR%2==1) printf "HSET \"%s\" \"%s\" ", key, $1; else printf "\"%s\"\n", $1}' key="$key" >> "$backup_path/data_$timestamp.redis"
                    ;;
                "list")
                    local len=$(docker exec "$container" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" LLEN "$key")
                    for ((i=0; i<len; i++)); do
                        local value=$(docker exec "$container" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" --raw LINDEX "$key" $i)
                        echo "LPUSH \"$key\" \"$value\"" >> "$backup_path/data_$timestamp.redis"
                    done
                    ;;
                "set")
                    docker exec "$container" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" SMEMBERS "$key" | \
                    awk '{printf "SADD \"%s\" \"%s\"\n", key, $1}' key="$key" >> "$backup_path/data_$timestamp.redis"
                    ;;
                "zset")
                    docker exec "$container" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" ZRANGE "$key" 0 -1 WITHSCORES | \
                    awk '{if(NR%2==1) printf "ZADD \"%s\" %s ", key, $2; else printf "\"%s\"\n", $1}' key="$key" >> "$backup_path/data_$timestamp.redis"
                    ;;
            esac

            # 设置TTL（如果有过期时间）
            if [[ "$ttl" -gt 0 ]]; then
                echo "EXPIRE \"$key\" $ttl" >> "$backup_path/data_$timestamp.redis"
            fi
        fi
    done < "$backup_path/keys_$timestamp.txt"

    print_success "数据导出备份创建成功"
}

# 创建备份元数据
create_backup_metadata() {
    local backup_path="$1"
    local timestamp=$(date +%Y%m%d_%H%M%S)

    print_info "创建备份元数据..."

    cat > "$backup_path/metadata.json" << EOF
{
    "backup_time": "$(date -Iseconds)",
    "backup_type": "full",
    "redis_version": "$(docker exec $(get_redis_container) redis-cli --no-auth-warning -a "$REDIS_PASSWORD" INFO server | grep 'redis_version' | cut -d: -f2 | tr -d '\r')",
    "total_keys": $(docker exec $(get_redis_container) redis-cli --no-auth-warning -a "$REDIS_PASSWORD" DBSIZE),
    "memory_usage": "$(docker exec $(get_redis_container) redis-cli --no-auth-warning -a "$REDIS_PASSWORD" INFO memory | grep 'used_memory_human' | cut -d: -f2 | tr -d '\r')",
    "backup_files": [
        "dump_$timestamp.rdb",
        "appendonly_$timestamp.aof",
        "data_$timestamp.redis",
        "keys_$timestamp.txt",
        "redis_$timestamp.conf",
        "sentinel_$timestamp.conf",
        "env_$timestamp.redis",
        "docker-compose_$timestamp.redis.yml"
    ],
    "backup_size_mb": $(du -sm "$backup_path" | cut -f1)
}
EOF

    print_success "备份元数据创建成功"
}

# 压缩备份
compress_backup() {
    local backup_path="$1"
    local archive_name=$(basename "$backup_path").tar.gz

    print_info "压缩备份文件..."

    cd "$(dirname "$backup_path")"
    tar -czf "$archive_name" "$(basename "$backup_path")"

    if [[ $? -eq 0 ]]; then
        print_success "备份压缩成功: $archive_name"
        echo "$(pwd)/$archive_name"
    else
        print_error "备份压缩失败"
        return 1
    fi
}

# 清理旧备份
cleanup_old_backups() {
    print_info "清理旧备份文件（保留最近 $KEEP_BACKUPS 个备份）..."

    # 清理未压缩的备份目录
    find "$BACKUP_DIR" -maxdepth 1 -type d -name "[0-9]*" -mtime +1 -exec rm -rf {} \; 2>/dev/null || true

    # 清理旧的压缩备份
    local backup_count=$(find "$BACKUP_DIR" -maxdepth 1 -name "*.tar.gz" | wc -l)

    if [[ $backup_count -gt $KEEP_BACKUPS ]]; then
        find "$BACKUP_DIR" -maxdepth 1 -name "*.tar.gz" -type f -printf '%T@ %p\n' | \
        sort -n | head -n -$KEEP_BACKUPS | cut -d' ' -f2- | xargs rm -f

        print_success "已清理 $((backup_count - KEEP_BACKUPS)) 个旧备份文件"
    fi
}

# 验证备份
verify_backup() {
    local archive_file="$1"

    print_info "验证备份文件完整性..."

    if [[ -f "$archive_file" ]]; then
        # 检查文件大小
        local file_size=$(stat -f%z "$archive_file" 2>/dev/null || stat -c%s "$archive_file" 2>/dev/null)

        if [[ $file_size -gt 1000 ]]; then
            # 测试压缩文件完整性
            if tar -tzf "$archive_file" > /dev/null 2>&1; then
                print_success "备份文件验证通过"
                return 0
            else
                print_error "备份文件损坏"
                return 1
            fi
        else
            print_error "备份文件过小，可能备份失败"
            return 1
        fi
    else
        print_error "备份文件不存在"
        return 1
    fi
}

# 上传到云存储（可选）
upload_to_cloud() {
    local archive_file="$1"

    # 如果配置了AWS S3，可以上传备份
    if [[ -n "${S3_REDIS_BACKUP_BUCKET:-}" && -n "${AWS_ACCESS_KEY_ID:-}" ]]; then
        print_info "上传备份到AWS S3..."

        if command -v aws &> /dev/null; then
            local filename=$(basename "$archive_file")
            aws s3 cp "$archive_file" "s3://$S3_REDIS_BACKUP_BUCKET/redis/$filename"

            if [[ $? -eq 0 ]]; then
                print_success "备份已上传到S3: s3://$S3_REDIS_BACKUP_BUCKET/redis/$filename"
            else
                print_warning "S3上传失败"
            fi
        else
            print_warning "AWS CLI未安装，跳过S3上传"
        fi
    fi
}

# 发送通知
send_notification() {
    local status="$1"
    local backup_file="$2"

    # 可以集成邮件、Slack等通知方式
    if [[ "$status" == "success" ]]; then
        print_success "Redis备份完成: $backup_file"
        # 这里可以添加成功通知逻辑
    else
        print_error "Redis备份失败"
        # 这里可以添加失败通知逻辑
    fi
}

# 主备份函数
perform_backup() {
    print_header "开始Redis备份"

    # 检查依赖
    check_dependencies

    # 创建备份目录
    local backup_path
    backup_path=$(create_backup_dir)
    print_info "备份目录: $backup_path"

    # 执行备份
    local success=true

    create_rdb_backup "$backup_path" "$(get_redis_container)" || success=false
    create_aof_backup "$backup_path" "$(get_redis_container)" || success=false
    create_config_backup "$backup_path" || success=false
    create_data_export "$backup_path" || success=false
    create_backup_metadata "$backup_path" || success=false

    if [[ "$success" == "true" ]]; then
        # 压缩备份
        local archive_file
        archive_file=$(compress_backup "$backup_path")

        if [[ $? -eq 0 && -n "$archive_file" ]]; then
            # 验证备份
            if verify_backup "$archive_file"; then
                # 清理临时文件和旧备份
                rm -rf "$backup_path"
                cleanup_old_backups

                # 上传到云存储
                upload_to_cloud "$archive_file"

                # 发送成功通知
                send_notification "success" "$archive_file"

                print_success "Redis备份完成"
                return 0
            fi
        fi
    fi

    # 发送失败通知
    send_notification "failure" ""
    print_error "Redis备份失败"
    return 1
}

# 显示帮助信息
show_help() {
    echo "MR游戏运营管理系统 - Redis备份脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help          显示帮助信息"
    echo "  -v, --verify        验证最新备份文件"
    echo "  -l, --list          列出所有备份文件"
    echo "  -c, --cleanup       清理旧备份文件"
    echo "  --dry-run          模拟运行（不实际执行备份）"
    echo ""
    echo "环境变量:"
    echo "  REDIS_PASSWORD      Redis密码"
    echo "  REDIS_HOST          Redis主机地址"
    echo "  REDIS_PORT          Redis端口"
    echo "  BACKUPS_PATH        备份目录路径"
    echo "  KEEP_BACKUPS        保留备份数量"
    echo "  S3_REDIS_BACKUP_BUCKET  S3存储桶名称"
    echo ""
    echo "示例:"
    echo "  $0                  # 执行完整备份"
    echo "  $0 --verify         # 验证最新备份"
    echo "  $0 --list           # 列出备份文件"
    echo "  $0 --cleanup        # 清理旧备份"
}

# 验证备份文件
verify_latest_backup() {
    local latest_backup=$(find "$BACKUP_DIR" -maxdepth 1 -name "*.tar.gz" -type f -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)

    if [[ -n "$latest_backup" ]]; then
        print_info "验证最新备份: $(basename "$latest_backup")"
        verify_backup "$latest_backup"
    else
        print_warning "未找到备份文件"
    fi
}

# 列出备份文件
list_backups() {
    print_header "Redis备份文件列表"

    if [[ -d "$BACKUP_DIR" ]]; then
        find "$BACKUP_DIR" -maxdepth 1 -name "*.tar.gz" -type f -exec ls -lh {} \; | \
        awk '{print $5, $6, $7, $8, $9}' | sort -k9
    else
        print_warning "备份目录不存在"
    fi
}

# 主函数
main() {
    case "${1:-backup}" in
        "backup")
            perform_backup
            ;;
        "--verify"|"-v")
            verify_latest_backup
            ;;
        "--list"|"-l")
            list_backups
            ;;
        "--cleanup"|"-c")
            cleanup_old_backups
            ;;
        "--dry-run")
            print_info "模拟运行模式 - 不会执行实际备份"
            print_info "将执行以下操作:"
            print_info "1. 检查Redis连接"
            print_info "2. 创建RDB备份"
            print_info "3. 创建AOF备份"
            print_info "4. 备份配置文件"
            print_info "5. 导出数据"
            print_info "6. 压缩备份文件"
            print_info "7. 清理旧备份"
            ;;
        "--help"|"-h")
            show_help
            ;;
        *)
            print_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"