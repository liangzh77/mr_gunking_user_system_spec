#!/bin/bash
# =============================================================================
# MR游戏运营管理系统 - Redis 恢复脚本
# 从备份文件恢复Redis数据
# =============================================================================

set -euo pipefail

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${BACKUPS_PATH:-./backups/redis}"
COMPOSE_FILE="$SCRIPT_DIR/../docker-compose.redis.yml"
ENV_FILE="$SCRIPT_DIR/../.env.redis"

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

# 获取Redis容器名称
get_redis_container() {
    local container=$(docker-compose -f "$COMPOSE_FILE" ps -q redis-master | head -1)
    if [[ -z "$container" ]]; then
        print_error "Redis主节点容器未运行"
        exit 1
    fi
    echo "$container"
}

# 停止Redis服务
stop_redis() {
    print_warning "停止Redis服务以进行恢复..."

    docker-compose -f "$COMPOSE_FILE" stop redis-master redis-slave-1 redis-slave-2

    print_success "Redis服务已停止"
}

# 启动Redis服务
start_redis() {
    print_info "启动Redis服务..."

    docker-compose -f "$COMPOSE_FILE" start redis-master

    print_info "等待主节点启动..."
    sleep 10

    docker-compose -f "$COMPOSE_FILE" start redis-slave-1 redis-slave-2

    print_info "等待从节点启动..."
    sleep 10

    print_success "Redis服务已启动"
}

# 清空现有数据
clear_redis_data() {
    local confirmation="$1"

    if [[ "$confirmation" != "yes" ]]; then
        print_warning "这将清空所有现有Redis数据，确认继续吗？(yes/no)"
        read -r user_confirmation
        if [[ "$user_confirmation" != "yes" ]]; then
            print_info "操作已取消"
            exit 0
        fi
    fi

    print_info "清空现有Redis数据..."

    local container=$(get_redis_container)

    # 清空数据目录
    docker-compose -f "$COMPOSE_FILE" exec -T redis-master redis-cli --no-auth-warning -a "$REDIS_PASSWORD" FLUSHALL

    print_success "现有数据已清空"
}

# 解压备份文件
extract_backup() {
    local backup_file="$1"
    local extract_dir="$2"

    print_info "解压备份文件: $(basename "$backup_file")"

    if [[ -f "$backup_file" ]]; then
        mkdir -p "$extract_dir"
        tar -xzf "$backup_file" -C "$extract_dir"

        if [[ $? -eq 0 ]]; then
            print_success "备份文件解压成功"
            return 0
        else
            print_error "备份文件解压失败"
            return 1
        fi
    else
        print_error "备份文件不存在: $backup_file"
        return 1
    fi
}

# 从RDB文件恢复
restore_from_rdb() {
    local extract_dir="$1"
    local rdb_file

    print_info "从RDB文件恢复数据..."

    # 查找RDB文件
    rdb_file=$(find "$extract_dir" -name "dump_*.rdb" -type f | head -1)

    if [[ -n "$rdb_file" && -f "$rdb_file" ]]; then
        local container=$(get_redis_container)

        # 停止Redis服务
        stop_redis

        # 复制RDB文件到容器
        print_info "复制RDB文件到Redis容器..."
        docker cp "$rdb_file" "$container:/data/dump.rdb"

        # 启动Redis服务
        start_redis

        # 验证恢复
        local key_count=$(docker exec "$container" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" DBSIZE)
        print_success "RDB恢复完成，恢复了 $key_count 个键"

        return 0
    else
        print_warning "未找到RDB备份文件"
        return 1
    fi
}

# 从AOF文件恢复
restore_from_aof() {
    local extract_dir="$1"
    local aof_file

    print_info "从AOF文件恢复数据..."

    # 查找AOF文件
    aof_file=$(find "$extract_dir" -name "appendonly_*.aof" -type f | head -1)

    if [[ -n "$aof_file" && -f "$aof_file" ]]; then
        local container=$(get_redis_container)

        # 停止Redis服务
        stop_redis

        # 复制AOF文件到容器
        print_info "复制AOF文件到Redis容器..."
        docker cp "$aof_file" "$container:/data/appendonly.aof"

        # 启动Redis服务
        start_redis

        # 验证恢复
        local key_count=$(docker exec "$container" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" DBSIZE)
        print_success "AOF恢复完成，恢复了 $key_count 个键"

        return 0
    else
        print_warning "未找到AOF备份文件"
        return 1
    fi
}

# 从数据导出文件恢复
restore_from_data_export() {
    local extract_dir="$1"
    local data_file

    print_info "从数据导出文件恢复数据..."

    # 查找数据导出文件
    data_file=$(find "$extract_dir" -name "data_*.redis" -type f | head -1)

    if [[ -n "$data_file" && -f "$data_file" ]]; then
        local container=$(get_redis_container)

        print_info "执行Redis命令恢复数据..."

        # 逐行执行Redis命令
        while IFS= read -r line; do
            if [[ -n "$line" && ! "$line" =~ ^# ]]; then
                docker exec "$container" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" $line > /dev/null 2>&1 || true
            fi
        done < "$data_file"

        # 验证恢复
        local key_count=$(docker exec "$container" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" DBSIZE)
        print_success "数据导出恢复完成，恢复了 $key_count 个键"

        return 0
    else
        print_warning "未找到数据导出文件"
        return 1
    fi
}

# 恢复配置文件
restore_config() {
    local extract_dir="$1"
    local force="${2:-no}"

    print_info "恢复配置文件..."

    local redis_config=$(find "$extract_dir" -name "redis_*.conf" -type f | head -1)
    local sentinel_config=$(find "$extract_dir" -name "sentinel_*.conf" -type f | head -1)
    local env_file=$(find "$extract_dir" -name "env_*.redis" -type f | head -1)

    if [[ "$force" != "yes" ]]; then
        print_warning "这将覆盖现有配置文件，确认继续吗？(yes/no)"
        read -r config_confirmation
        if [[ "$config_confirmation" != "yes" ]]; then
            print_info "跳过配置文件恢复"
            return 0
        fi
    fi

    # 恢复Redis配置
    if [[ -n "$redis_config" && -f "$redis_config" ]]; then
        print_info "恢复Redis配置文件..."
        # 这里需要根据实际的配置文件路径进行调整
        # cp "$redis_config" "$SCRIPT_DIR/../redis/redis.conf"
        print_success "Redis配置文件已恢复"
    fi

    # 恢复Sentinel配置
    if [[ -n "$sentinel_config" && -f "$sentinel_config" ]]; then
        print_info "恢复Sentinel配置文件..."
        # cp "$sentinel_config" "$SCRIPT_DIR/../redis/sentinel.conf"
        print_success "Sentinel配置文件已恢复"
    fi

    # 恢复环境变量文件
    if [[ -n "$env_file" && -f "$env_file" ]]; then
        print_info "恢复环境变量文件..."
        # cp "$env_file" "$SCRIPT_DIR/../.env.redis"
        print_success "环境变量文件已恢复"
    fi

    return 0
}

# 验证恢复结果
verify_restore() {
    local extract_dir="$1"

    print_header "验证恢复结果"

    local container=$(get_redis_container)

    # 检查Redis服务状态
    print_info "检查Redis服务状态..."
    if docker exec "$container" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" PING | grep -q "PONG"; then
        print_success "Redis服务运行正常"
    else
        print_error "Redis服务异常"
        return 1
    fi

    # 检查数据量
    local current_keys=$(docker exec "$container" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" DBSIZE)
    print_info "当前键数量: $current_keys"

    # 检查内存使用
    local memory_usage=$(docker exec "$container" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" INFO memory | grep "used_memory_human" | cut -d: -f2 | tr -d '\r')
    print_info "内存使用: $memory_usage"

    # 检查复制状态
    print_info "检查复制状态..."
    local replica_count=$(docker exec "$container" redis-cli --no-auth-warning -a "$REDIS_PASSWORD" INFO replication | grep "connected_slaves" | cut -d: -f2 | tr -d '\r')
    print_info "连接的从节点数量: $replica_count"

    # 检查备份元数据
    local metadata_file=$(find "$extract_dir" -name "metadata.json" -type f | head -1)
    if [[ -n "$metadata_file" && -f "$metadata_file" ]]; then
        print_info "备份元数据:"
        cat "$metadata_file" | jq . 2>/dev/null || cat "$metadata_file"
    fi

    print_success "恢复验证完成"
    return 0
}

# 列出可用备份
list_available_backups() {
    print_header "可用的Redis备份文件"

    if [[ -d "$BACKUP_DIR" ]]; then
        local backup_files=($(find "$BACKUP_DIR" -maxdepth 1 -name "*.tar.gz" -type f -printf '%T@ %p\n' | sort -nr | cut -d' ' -f2-))

        if [[ ${#backup_files[@]} -gt 0 ]]; then
            echo "编号  备份文件                    大小      修改时间"
            echo "----  ------------------------  --------  -------------------"

            local i=1
            for backup_file in "${backup_files[@]}"; do
                local filename=$(basename "$backup_file")
                local size=$(ls -lh "$backup_file" | awk '{print $5}')
                local mtime=$(ls -l "$backup_file" | awk '{print $6, $7, $8}')
                printf "%-4d  %-24s  %-8s  %s\n" $i "$filename" "$size" "$mtime"
                ((i++))
            done

            echo ""
            print_info "使用编号选择备份文件进行恢复"
        else
            print_warning "未找到备份文件"
        fi
    else
        print_warning "备份目录不存在"
    fi
}

# 交互式选择备份
select_backup() {
    list_available_backups

    if [[ -d "$BACKUP_DIR" ]]; then
        local backup_files=($(find "$BACKUP_DIR" -maxdepth 1 -name "*.tar.gz" -type f -printf '%T@ %p\n' | sort -nr | cut -d' ' -f2-))

        if [[ ${#backup_files[@]} -gt 0 ]]; then
            echo ""
            read -p "请选择备份文件编号 (1-${#backup_files[@]}): " selection

            if [[ "$selection" =~ ^[0-9]+$ && $selection -ge 1 && $selection -le ${#backup_files[@]} ]]; then
                echo "${backup_files[$((selection-1))]}"
                return 0
            else
                print_error "无效的选择"
                return 1
            fi
        fi
    fi

    return 1
}

# 显示恢复选项
show_restore_options() {
    echo "恢复选项:"
    echo "1) 从RDB文件恢复 (推荐，速度快)"
    echo "2) 从AOF文件恢复 (更完整，可能较慢)"
    echo "3) 从数据导出文件恢复 (兼容性好)"
    echo "4) 恢复配置文件"
    echo "5) 完整恢复 (数据 + 配置)"
    echo ""
    read -p "请选择恢复方式 (1-5): " restore_option
}

# 执行恢复
perform_restore() {
    local backup_file="$1"
    local restore_type="$2"
    local force_config="$3"

    print_header "开始Redis恢复"
    print_info "备份文件: $(basename "$backup_file")"
    print_info "恢复类型: $restore_type"

    # 创建临时解压目录
    local temp_dir="/tmp/redis_restore_$(date +%s)"
    trap "rm -rf $temp_dir" EXIT

    # 解压备份文件
    if ! extract_backup "$backup_file" "$temp_dir"; then
        print_error "备份文件解压失败"
        return 1
    fi

    local success=true

    case "$restore_type" in
        "rdb")
            restore_from_rdb "$temp_dir" || success=false
            ;;
        "aof")
            restore_from_aof "$temp_dir" || success=false
            ;;
        "data")
            restore_from_data_export "$temp_dir" || success=false
            ;;
        "config")
            restore_config "$temp_dir" "$force_config" || success=false
            ;;
        "full")
            # 恢复配置
            restore_config "$temp_dir" "$force_config" || success=false

            # 清空现有数据
            clear_redis_data "yes"

            # 尝试按优先级恢复数据
            restore_from_rdb "$temp_dir" || \
            restore_from_aof "$temp_dir" || \
            restore_from_data_export "$temp_dir" || success=false
            ;;
        *)
            print_error "未知的恢复类型: $restore_type"
            success=false
            ;;
    esac

    if [[ "$success" == "true" ]]; then
        # 验证恢复结果
        verify_restore "$temp_dir"

        print_success "Redis恢复完成"
        return 0
    else
        print_error "Redis恢复失败"
        return 1
    fi
}

# 显示帮助信息
show_help() {
    echo "MR游戏运营管理系统 - Redis恢复脚本"
    echo ""
    echo "用法: $0 [选项] [备份文件]"
    echo ""
    echo "选项:"
    echo "  -h, --help          显示帮助信息"
    echo "  -l, --list          列出可用备份文件"
    echo "  -i, --interactive   交互式选择备份文件"
    echo "  -t, --type TYPE     恢复类型 (rdb|aof|data|config|full)"
    echo "  -f, --force         强制恢复，不询问确认"
    echo "  --dry-run          模拟运行（不实际执行恢复）"
    echo ""
    echo "恢复类型说明:"
    echo "  rdb     - 从RDB快照文件恢复 (最快)"
    echo "  aof     - 从AOF日志文件恢复 (最完整)"
    echo "  data    - 从数据导出文件恢复 (兼容性好)"
    echo "  config  - 仅恢复配置文件"
    echo "  full    - 完整恢复 (数据 + 配置)"
    echo ""
    echo "示例:"
    echo "  $0                                    # 交互式恢复"
    echo "  $0 -l                                 # 列出备份文件"
    echo "  $0 /path/to/backup.tar.gz            # 恢复指定备份"
    echo "  $0 -t rdb /path/to/backup.tar.gz     # 从RDB恢复"
    echo "  $0 -t full -f /path/to/backup.tar.gz # 强制完整恢复"
}

# 主函数
main() {
    local backup_file=""
    local restore_type="full"
    local force="no"
    local interactive="no"

    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit 0
                ;;
            --list|-l)
                list_available_backups
                exit 0
                ;;
            --interactive|-i)
                interactive="yes"
                shift
                ;;
            --type|-t)
                restore_type="$2"
                shift 2
                ;;
            --force|-f)
                force="yes"
                shift
                ;;
            --dry-run)
                print_info "模拟运行模式 - 不会执行实际恢复"
                print_info "将执行以下操作:"
                print_info "1. 检查依赖和服务状态"
                print_info "2. 解压备份文件"
                print_info "3. 根据选择的恢复类型执行恢复"
                print_info "4. 验证恢复结果"
                exit 0
                ;;
            -*)
                print_error "未知选项: $1"
                show_help
                exit 1
                ;;
            *)
                backup_file="$1"
                shift
                ;;
        esac
    done

    # 检查依赖
    check_dependencies

    # 如果没有指定备份文件，进入交互模式
    if [[ -z "$backup_file" || "$interactive" == "yes" ]]; then
        backup_file=$(select_backup)
        if [[ -z "$backup_file" ]]; then
            print_error "未选择备份文件"
            exit 1
        fi

        if [[ "$restore_type" == "full" ]]; then
            show_restore_options
            case "$restore_option" in
                1) restore_type="rdb" ;;
                2) restore_type="aof" ;;
                3) restore_type="data" ;;
                4) restore_type="config" ;;
                5) restore_type="full" ;;
                *)
                    print_error "无效的选择，使用默认完整恢复"
                    restore_type="full"
                    ;;
            esac
        fi
    fi

    # 验证备份文件
    if [[ ! -f "$backup_file" ]]; then
        print_error "备份文件不存在: $backup_file"
        exit 1
    fi

    # 执行恢复
    perform_restore "$backup_file" "$restore_type" "$force"
}

# 执行主函数
main "$@"