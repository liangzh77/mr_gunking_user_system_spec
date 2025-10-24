#!/bin/bash
# =============================================================================
# MR游戏运营管理系统 - PostgreSQL 数据库管理脚本
# =============================================================================

set -euo pipefail

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/../docker-compose.postgres.yml"
ENV_FILE="$SCRIPT_DIR/../.env.postgres"

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

# 检查Docker和Docker Compose
check_dependencies() {
    print_info "检查依赖..."

    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose 未安装"
        exit 1
    fi

    if [[ ! -f "$COMPOSE_FILE" ]]; then
        print_error "Docker Compose 文件不存在: $COMPOSE_FILE"
        exit 1
    fi

    if [[ ! -f "$ENV_FILE" ]]; then
        print_error "环境变量文件不存在: $ENV_FILE"
        exit 1
    fi

    print_success "依赖检查完成"
}

# 启动PostgreSQL服务
start_postgres() {
    print_header "启动PostgreSQL服务"

    # 创建必要的目录
    mkdir -p data/postgres logs/postgres backups/postgres

    # 启动服务
    docker-compose -f "$COMPOSE_FILE" up -d postgres

    print_info "等待PostgreSQL服务启动..."
    sleep 10

    # 检查服务状态
    if docker-compose -f "$COMPOSE_FILE" ps postgres | grep -q "Up"; then
        print_success "PostgreSQL服务启动成功"

        # 显示连接信息
        print_info "连接信息:"
        print_info "  主机: localhost"
        print_info "  端口: ${POSTGRES_PORT:-5432}"
        print_info "  数据库: ${POSTGRES_DB:-mr_game_ops_prod}"
        print_info "  用户: ${POSTGRES_USER:-postgres}"
        print_warning "请确保已修改 .env.postgres 中的默认密码!"
    else
        print_error "PostgreSQL服务启动失败"
        docker-compose -f "$COMPOSE_FILE" logs postgres
        exit 1
    fi
}

# 停止PostgreSQL服务
stop_postgres() {
    print_header "停止PostgreSQL服务"

    docker-compose -f "$COMPOSE_FILE" down postgres

    if [[ $? -eq 0 ]]; then
        print_success "PostgreSQL服务已停止"
    else
        print_error "停止PostgreSQL服务失败"
        exit 1
    fi
}

# 重启PostgreSQL服务
restart_postgres() {
    print_header "重启PostgreSQL服务"

    stop_postgres
    sleep 5
    start_postgres
}

# 查看服务状态
status_postgres() {
    print_header "PostgreSQL服务状态"

    docker-compose -f "$COMPOSE_FILE" ps

    echo ""
    print_info "服务详情:"
    docker-compose -f "$COMPOSE_FILE" ps postgres | tail -n +3 | while IFS= read -r line; do
        if [[ -n "$line" ]]; then
            echo "$line"
        fi
    done

    # 检查数据库连接
    echo ""
    print_info "数据库连接测试..."
    if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U postgres; then
        print_success "数据库连接正常"
    else
        print_warning "数据库连接失败"
    fi
}

# 查看日志
logs_postgres() {
    print_header "PostgreSQL服务日志"

    if [[ -n "${1:-}" ]]; then
        docker-compose -f "$COMPOSE_FILE" logs --tail="$1" postgres
    else
        docker-compose -f "$COMPOSE_FILE" logs -f postgres
    fi
}

# 连接到数据库
connect_postgres() {
    print_info "连接到PostgreSQL数据库..."

    docker-compose -f "$COMPOSE_FILE" exec postgres psql -U postgres -d mr_game_ops_prod
}

# 执行SQL文件
execute_sql() {
    local sql_file="$1"

    if [[ -z "$sql_file" ]]; then
        print_error "请指定SQL文件"
        print_info "用法: $0 execute <sql_file>"
        exit 1
    fi

    if [[ ! -f "$sql_file" ]]; then
        print_error "SQL文件不存在: $sql_file"
        exit 1
    fi

    print_info "执行SQL文件: $sql_file"

    docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -d mr_game_ops_prod < "$sql_file"

    if [[ $? -eq 0 ]]; then
        print_success "SQL文件执行成功"
    else
        print_error "SQL文件执行失败"
        exit 1
    fi
}

# 创建备份
create_backup() {
    print_header "创建数据库备份"

    docker-compose -f "$COMPOSE_FILE" exec postgres backup.sh

    if [[ $? -eq 0 ]]; then
        print_success "备份创建成功"

        # 显示备份文件
        print_info "备份文件:"
        docker-compose -f "$COMPOSE_FILE" exec postgres ls -la /var/backups/postgresql/daily/ | tail -n +2
    else
        print_error "备份创建失败"
        exit 1
    fi
}

# 恢复备份
restore_backup() {
    local backup_file="$1"

    if [[ -z "$backup_file" ]]; then
        print_error "请指定备份文件"
        print_info "用法: $0 restore <backup_file>"
        exit 1
    fi

    print_warning "恢复操作将覆盖当前数据库，确认继续吗？(y/N)"
    read -r confirmation
    if [[ "$confirmation" != "y" && "$confirmation" != "Y" ]]; then
        print_info "操作已取消"
        exit 0
    fi

    print_header "恢复数据库备份: $backup_file"

    # 停止应用服务
    print_info "停止应用服务..."
    docker-compose -f "$COMPOSE_FILE" down postgres

    # 删除现有数据
    print_info "清理现有数据..."
    docker volume rm mr_game_ops_postgres-data 2>/dev/null || true

    # 启动新的数据库实例
    print_info "启动新的数据库实例..."
    docker-compose -f "$COMPOSE_FILE" up -d postgres
    sleep 15

    # 恢复备份
    print_info "恢复备份数据..."
    if docker cp "$backup_file" mr_game_ops_postgres_prod:/tmp/restore.sql.gz; then
        docker-compose -f "$COMPOSE_FILE" exec postgres gunzip -c /tmp/restore.sql.gz | \
        docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -d mr_game_ops_prod

        if [[ $? -eq 0 ]]; then
            print_success "数据库恢复成功"
            print_info "清理临时文件..."
            docker-compose -f "$COMPOSE_FILE" exec postgres rm -f /tmp/restore.sql.gz
        else
            print_error "数据库恢复失败"
            exit 1
        fi
    else
        print_error "复制备份文件失败"
        exit 1
    fi
}

# 数据库维护
maintenance_postgres() {
    print_header "数据库维护操作"

    print_info "执行VACUUM ANALYZE..."
    docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -d mr_game_ops_prod -c "VACUUM ANALYZE;"

    print_info "更新统计信息..."
    docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -d mr_game_ops_prod -c "ANALYZE;"

    print_info "重建索引..."
    docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -d mr_game_ops_prod -c "REINDEX DATABASE mr_game_ops_prod;"

    print_success "数据库维护完成"
}

# 性能监控
monitor_postgres() {
    print_header "PostgreSQL性能监控"

    print_info "数据库连接数:"
    docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -d mr_game_ops_prod -c "
        SELECT count(*) as active_connections
        FROM pg_stat_activity
        WHERE state = 'active';
    "

    print_info "数据库大小:"
    docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -d mr_game_ops_prod -c "
        SELECT pg_size_pretty(pg_database_size('mr_game_ops_prod')) as database_size;
    "

    print_info "表大小排行:"
    docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -d mr_game_ops_prod -c "
        SELECT
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        LIMIT 10;
    "

    print_info "慢查询:"
    docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -d mr_game_ops_prod -c "
        SELECT
            query,
            calls,
            total_time,
            mean_time,
            rows
        FROM pg_stat_statements
        ORDER BY mean_time DESC
        LIMIT 5;
    " 2>/dev/null || print_info "慢查询监控未启用 (需要 pg_stat_statements 扩展)"
}

# 清理日志
cleanup_logs() {
    print_header "清理PostgreSQL日志"

    # 清理Docker日志
    print_info "清理Docker容器日志..."
    docker-compose -f "$COMPOSE_FILE" exec postgres sh -c "
        find /var/log/postgresql -name '*.log' -mtime +7 -delete
    " 2>/dev/null || true

    # 清理旧的备份文件
    print_info "清理30天前的备份文件..."
    docker-compose -f "$COMPOSE_FILE" exec postgres sh -c "
        find /var/backups/postgresql -name '*.sql.gz' -mtime +30 -delete
        find /var/backups/postgresql -name '*.tar.gz' -mtime +7 -delete
    " 2>/dev/null || true

    print_success "日志清理完成"
}

# 显示帮助信息
show_help() {
    echo "MR游戏运营管理系统 - PostgreSQL数据库管理脚本"
    echo ""
    echo "用法: $0 <命令> [选项]"
    echo ""
    echo "命令:"
    echo "  start              启动PostgreSQL服务"
    echo "  stop               停止PostgreSQL服务"
    echo "  restart            重启PostgreSQL服务"
    echo "  status             查看服务状态"
    echo "  logs [lines]       查看服务日志"
    echo "  connect            连接到数据库"
    echo "  execute <file>     执行SQL文件"
    echo "  backup             创建数据库备份"
    echo "  restore <file>     恢复数据库备份"
    echo "  maintenance        数据库维护"
    echo "  monitor            性能监控"
    echo "  cleanup            清理日志"
    echo "  help               显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 start           # 启动PostgreSQL服务"
    echo "  $0 logs 100         # 查看最近100行日志"
    echo "  $0 execute init.sql # 执行初始化脚本"
    echo "  $0 backup          # 创建备份"
    echo ""
    echo "配置文件:"
    echo "  Docker Compose: $COMPOSE_FILE"
    echo "  环境变量: $ENV_FILE"
}

# 主函数
main() {
    # 检查依赖
    check_dependencies

    # 加载环境变量
    if [[ -f "$ENV_FILE" ]]; then
        export $(grep -v '^#' "$ENV_FILE" | xargs)
    fi

    # 处理命令
    case "${1:-help}" in
        "start")
            start_postgres
            ;;
        "stop")
            stop_postgres
            ;;
        "restart")
            restart_postgres
            ;;
        "status")
            status_postgres
            ;;
        "logs")
            logs_postgres "${2:-}"
            ;;
        "connect")
            connect_postgres
            ;;
        "execute")
            execute_sql "${2:-}"
            ;;
        "backup")
            create_backup
            ;;
        "restore")
            restore_backup "${2:-}"
            ;;
        "maintenance")
            maintenance_postgres
            ;;
        "monitor")
            monitor_postgres
            ;;
        "cleanup")
            cleanup_logs
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"