#!/bin/bash
# =============================================================================
# MR游戏运营管理系统 - Redis 集群管理脚本
# =============================================================================

set -euo pipefail

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd"
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

# 启动Redis集群
start_redis() {
    print_header "启动Redis集群"

    # 创建必要的目录
    mkdir -p data/redis/{master,slave1,slave2}
    mkdir -p logs/redis/{master,slave1,slave2,sentinel1,sentinel2,sentinel3}
    mkdir -p backups/redis

    # 启动服务
    print_info "启动Redis主节点..."
    docker-compose -f "$COMPOSE_FILE" up -d redis-master

    print_info "等待主节点启动..."
    sleep 10

    print_info "启动Redis从节点..."
    docker-compose -f "$COMPOSE_FILE" up -d redis-slave-1 redis-slave-2

    print_info "等待从节点启动..."
    sleep 10

    print_info "启动Redis Sentinel..."
    docker-compose -f "$COMPOSE_FILE" up -d redis-sentinel-1 redis-sentinel-2 redis-sentinel-3

    print_info "等待Sentinel启动..."
    sleep 15

    # 检查服务状态
    check_redis_cluster_status

    if [[ $? -eq 0 ]]; then
        print_success "Redis集群启动成功"

        # 显示集群信息
        show_cluster_info
    else
        print_error "Redis集群启动失败"
        docker-compose -f "$COMPOSE_FILE" logs
        exit 1
    fi
}

# 停止Redis集群
stop_redis() {
    print_header "停止Redis集群"

    docker-compose -f "$COMPOSE_FILE" down

    if [[ $? -eq 0 ]]; then
        print_success "Redis集群已停止"
    else
        print_error "停止Redis集群失败"
        exit 1
    fi
}

# 重启Redis集群
restart_redis() {
    print_header "重启Redis集群"

    stop_redis
    sleep 5
    start_redis
}

# 查看服务状态
status_redis() {
    print_header "Redis集群状态"

    docker-compose -f "$COMPOSE_FILE" ps

    echo ""
    print_info "集群详情:"
    show_cluster_status
    show_redis_info
    show_memory_usage
}

# 检查Redis集群状态
check_redis_cluster_status() {
    local master_status
    local slave1_status
    local slave2_status
    local sentinel1_status
    local sentinel2_status
    local sentinel3_status

    # 检查主节点
    print_info "检查主节点状态..."
    if docker-compose -f "$COMPOSE_FILE" exec -T redis-master redis-cli ping | grep -q "PONG"; then
        master_status="UP"
        print_success "主节点: 运行正常"
    else
        master_status="DOWN"
        print_error "主节点: 无法连接"
    fi

    # 检查从节点1
    print_info "检查从节点1状态..."
    if docker-compose -f "$COMPOSE_FILE" exec -T redis-slave-1 redis-cli ping | grep -q "PONG"; then
        slave1_status="UP"
        print_success "从节点1: 运行正常"
    else
        slave1_status="DOWN"
        print_error "从节点1: 无法连接"
    fi

    # 检查从节点2
    print_info "检查从节点2状态..."
    if docker-compose -f "$COMPOSE_FILE" exec -T redis-slave-2 redis-cli ping | grep -q "PONG"; then
        slave2_status="UP"
        print_success "从节点2: 运行正常"
    else
        slave2_status="DOWN"
        print_error "从节点2: 无法连接"
    fi

    # 检查Sentinel节点
    print_info "检查Sentinel节点状态..."
    local sentinel_count=0
    for i in {1..3}; do
        if docker-compose -f "$COMPOSE_FILE" exec -T redis-sentinel-$i redis-cli -p $((26378 + i - 1)) ping | grep -q "PONG"; then
            ((sentinel_count++))
        fi
    done

    if [[ $sentinel_count -eq 3 ]]; then
        print_success "Sentinel节点: 全部运行正常 ($sentinel_count/3)"
    else
        print_warning "Sentinel节点: 仅 $sentinel_count/3 运行正常"
    fi

    # 返回整体状态
    if [[ "$master_status" == "UP" && "$slave1_status" == "UP" && "$slave2_status" == "UP" ]]; then
        return 0
    else
        return 1
    fi
}

# 显示集群信息
show_cluster_info() {
    print_info "Redis集群信息:"

    # 主节点信息
    echo ""
    print_info "主节点 (redis-master):"
    docker-compose -f "$COMPOSE_FILE" exec -T redis-master redis-cli info server | head -n 10

    # 从节点信息
    echo ""
    print_info "从节点1 (redis-slave-1):"
    docker-compose -f "$COMPOSE_FILE" exec -T redis-slave-1 redis-cli info replication | grep -E "(role|connected_slave|master_host|master_port)"

    echo ""
    print_info "从节点2 (redis-slave-2):"
    docker-compose -f "$COMPOSE_FILE" exec -T redis-slave-2 redis-cli info replication | grep -E "(role|connected_slave|master_host|master_port)"

    # Sentinel信息
    echo ""
    print_info "Sentinel信息:"
    for i in {1..3}; do
        if docker-compose -f "$COMPOSE_FILE" exec -T redis-sentinel-$i redis-cli -p $((26378 + i - 1)) sentinel masters > /dev/null 2>&1; then
            echo "  Sentinel-$i: $(docker-compose -f "$COMPOSE_FILE" exec -T redis-sentinel-$i redis-cli -p $((26378 + i - 1)) sentinel masters | grep -v 'name' | awk '{print $2, $3, $4}')"
        fi
    done
}

# 显示Redis状态
show_redis_status() {
    print_info "Redis服务器状态:"

    # 主节点状态
    echo ""
    docker-compose -f "$COMPOSE_FILE" exec -T redis-master redis-cli info server | grep -E "(uptime|connected_clients|used_memory:|total_commands_processed)"

    # 数据库信息
    echo ""
    docker-compose -f "$COMPOSE_FILE" exec -T redis-master redis-cli info keyspace | head -n 10
}

# 显示内存使用情况
show_memory_usage() {
    print_info "内存使用情况:"

    # 主节点内存
    local master_memory
    master_memory=$(docker-compose -f "$COMPOSE_FILE" exec -T redis-master redis-cli info memory | grep "used_memory_human" | awk '{print $2}')
    print_info "主节点内存使用: $master_memory"

    # 从节点内存
    local slave1_memory
    slave1_memory=$(docker-compose -f "$COMPOSE_FILE" exec -T redis-slave-1 redis-cli info memory | grep "used_memory_human" | awk '{print $2}')
    print_info "从节点1内存使用: $slave1_memory"

    local slave2_memory
    slave2_memory=$(docker-compose -f "$COMPOSE_FILE" exec -T redis-slave-2 redis-cli info memory | grep "used_memory_human" | awk '{print $2}')
    print_info "从节点2内存使用: $slave2_memory"
}

# 连接到Redis
connect_redis() {
    local node="${1:-master}"
    local port="${2:-6379}"

    print_info "连接到Redis节点: $node (端口: $port)"

    case "$node" in
        "master")
            docker-compose -f "$COMPOSE_FILE" exec redis-master redis-cli
            ;;
        "slave1")
            docker-compose -f "$COMPOSE_FILE" exec redis-slave-1 redis-cli
            ;;
        "slave2")
            docker-compose -f "$COMPOSE_FILE" exec redis-slave-2 redis-cli
            ;;
        "sentinel1")
            docker-compose -f "$COMPOSE_FILE" exec redis-sentinel-1 redis-cli -p 26379
            ;;
        "sentinel2")
            docker-compose - f "$COMPOSE_FILE" exec redis-sentinel-2 redis-cli -p 26380
            ;;
        "sentinel3")
            docker-compose -f "$COMPOSE_FILE" exec redis-sentinel-3 redis-cli -p 26381
            ;;
        *)
            print_error "未知节点: $node"
            print_info "可用节点: master, slave1, slave2, sentinel1, sentinel2, sentinel3"
            exit 1
            ;;
    esac
}

# 执行Redis命令
execute_redis_command() {
    local node="${1:-master}"
    shift
    local command="$@"

    if [[ -z "$command" ]]; then
        print_error "请指定Redis命令"
        print_info "用法: $0 execute <node> <command>"
        exit 1
    fi

    print_info "在节点 $node 上执行命令: $command"

    case "$node" in
        "master")
            docker-compose -f "$COMPOSE_FILE" exec -T redis-master redis-cli "$command"
            ;;
        "slave1")
            docker-compose -f "$COMPOSE_FILE" exec -T redis-slave-1 redis-cli "$command"
            ;;
        "slave2")
            docker-compose -f "$COMPOSE_FILE" exec -T redis-slave-2 redis-cli "$command"
            ;;
        "sentinel1")
            docker-compose -f "$COMPOSE_FILE" exec -T redis-sentinel-1 redis-cli -p 26379 "$command"
            ;;
        "sentinel2")
            docker-compose -f "$COMPOSE_FILE" exec -T redis-sentinel-2 redis-cli -p 26380 "$command"
            ;;
        "sentinel3")
            docker-compose -f "$COMPOSE_FILE" exec -T redis-sentinel-3 redis-cli -p 26381 "$command"
            ;;
        *)
            print_error "未知节点: $node"
            exit 1
            ;;
    esac
}

# 创建备份
create_backup() {
    print_header "创建Redis备份"

    # 创建备份目录
    backup_dir="backups/redis/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"

    print_info "开始创建备份..."

    # 备份主节点数据
    if docker-compose -f "$COMPOSE_FILE" exec -T redis-master redis-cli --rdb /backup_dir/dump_$(date +%Y%m%d_%H%M%S).rdb; then
        print_success "主节点备份创建成功"
    else
        print_error "主节点备份失败"
        exit 1
    fi

    # 备份配置文件
    docker-compose -f "$COMPOSE_FILE" exec -T redis-master cat /usr/local/etc/redis/redis.conf > "$backup_dir/redis.conf"
    docker-compose -f "$COMPOSE_FILE" exec -T redis-sentinel-1 cat /usr/local/etc/redis/sentinel.conf > "$backup_dir/sentinel.conf"

    print_info "备份完成: $backup_dir"
}

# 清理数据
clear_redis() {
    local node="${1:-master}"

    print_warning "这将清空Redis节点 $node 的所有数据，确认继续吗？(y/N)"
    read -r confirmation
    if [[ "$confirmation" != "y" && "$confirmation" != "Y" ]]; then
        print_info "操作已取消"
        exit 0
    fi

    print_header "清空Redis节点: $node"

    case "$node" in
        "master")
            docker-compose -f "$COMPOSE_FILE" exec -T redis-master redis-cli FLUSHALL
            ;;
        "slave1")
            print_error "不能直接清空从节点数据"
            exit 1
            ;;
        "slave2")
            print_error "不能直接清空从节点数据"
            exit 1
            ;;
        *)
            print_error "未知节点: $node"
            exit 1
            ;;
    esac

    print_success "数据清空完成"
}

# 监控Redis
monitor_redis() {
    print_header "Redis集群监控"

    print_info "持续监控Redis集群状态 (按 Ctrl+C 退出)..."

    while true; do
        clear
        echo "=== Redis集群监控 - $(date) ==="
        echo ""

        # 显示集群状态
        if check_redis_cluster_status; then
            print_success "集群状态: 正常"
        else
            print_error "集群状态: 异常"
        fi

        echo ""
        print_info "连接数: $(docker-compose -f "$COMPOSE_FILE" exec -T redis-master redis-cli info clients | grep 'connected_clients' | awk '{print $2}')"
        print_info "内存使用: $(docker-compose -f "$COMPOSE_FILE" exec -T redis-master redis-cli info memory | grep 'used_memory_human' | awk '{print $2}')"
        print_info "命令数: $(docker-compose -f "$COMPOSE_FILE" exec -T redis-master redis-cli info stats | grep 'total_commands_processed' | awk '{print $2}')"
        print_info "键数量: $(docker-compose -f "$COMPOSE_FILE" exec -T redis-master redis-cli info keyspace | grep '^db' | awk '{sum $2}')"

        echo ""
        print_info "10秒后刷新..."
        sleep 10
    done
}

# 查看日志
logs_redis() {
    local service="${1:-}"
    local lines="${2:-50}"

    if [[ -z "$service" ]]; then
        print_header "Redis服务日志 (最近${lines}行)"
        docker-compose -f "$COMPOSE_FILE" logs --tail="$lines"
    else
        print_header "Redis $service 服务日志"
        docker-compose -f "$COMPOSE_FILE" logs --tail="$lines" "$service"
    fi
}

# 性能测试
performance_test() {
    print_header "Redis性能测试"

    print_info "执行Redis性能测试..."

    # 基准测试
    echo "1. SET/GET 性能测试..."
    local start_time end_time
    start_time=$(date +%s%N)
    for i in {1..1000}; do
        docker-compose -f "$COMPOSE_FILE" exec -T redis-master redis-cli set test_key_$i "test_value_$i" > /dev/null
    done
    end_time=$(date +%s%N)
    local set_time=$((($end_time - $start_time) / 1000000))
    print_info "1000次SET操作耗时: ${set_time}ms"

    start_time=$(date +%s%N)
    for i in {1..1000}; do
        docker-compose -f "$COMPOSE_FILE" exec -T redis-master redis-cli get test_key_$i > /dev/null
    done
    end_time=$(date +%s%N)
    local get_time=$((($end_time - $start_time) / 1000000))
    print_info "1000次GET操作耗时: ${get_time}ms"

    # 并发测试
    echo ""
    print_info "并发性能测试 (10个并发连接, 每个100次操作)..."
    for i in {1..10}; do
        (
            for j in {1..100}; do
                docker-compose -f "$COMPOSE_FILE" exec -T redis-master redis-cli set concurrent_test_${i}_${j} "value_${i}_${j}" > /dev/null
                docker-compose -f "$COMPOSE_FILE" exec -T redis-master redis-cli get concurrent_test_${i}_${j} > /dev/null
            done
        ) &
    done

    wait
    print_success "并发测试完成"

    # 清理测试数据
    docker-compose -f "$COMPOSE_FILE" exec -T redis-master redis-cli del test_key_* > /dev/null
    docker-compose -f "$COMPOSE_FILE" exec -T redis-master redis-cli del concurrent_test_* > /dev/null
}

# 故障转移测试
failover_test() {
    print_header "Redis故障转移测试"

    print_warning "这将停止主节点并触发故障转移，确认继续吗？(y/N)"
    read -r confirmation
    if [[ "$confirmation" != "y" && "$confirmation" != "Y" ]]; then
        print_info "操作已取消"
        exit 0
    fi

    print_info "停止主节点以触发故障转移..."
    docker-compose -f "$COMPOSE_FILE" stop redis-master

    print_info "等待故障转移完成..."
    sleep 30

    print_info "检查故障转移结果..."
    if docker-compose -f "$COMPOSE_FILE" exec -T redis-slave-1 redis-cli info replication | grep "role:master" > /dev/null; then
        print_success "故障转移成功! 从节点1成为新的主节点"
    else
        print_error "故障转移失败"
    fi

    print_info "恢复原主节点..."
    docker-compose -f "$COMPOSE_FILE" start redis-master
    sleep 15

    print_info "等待重新同步完成..."
    sleep 30

    print_success "故障转移测试完成"
}

# 显示帮助信息
show_help() {
    echo "MR游戏运营管理系统 - Redis集群管理脚本"
    echo ""
    echo "用法: $0 <命令> [选项]"
    echo ""
    echo "命令:"
    echo "  start              启动Redis集群"
    echo "  stop               停止Redis集群"
    echo "  restart            重启Redis集群"
    echo "  status             查看集群状态"
    echo "  connect [node]     连接到Redis节点"
    echo "  execute <node>     在指定节点执行命令"
    echo "  backup             创建集群备份"
    echo "  clear [node]       清空节点数据"
    echo "  monitor            监控集群状态"
    "  logs [service]      查看服务日志"
    echo "  performance        性能测试"
    echo "  failover           故障转移测试"
    echo "  help               显示帮助信息"
    echo ""
    echo "可用节点:"
    echo "  master, slave1, slave2, sentinel1, sentinel2, sentinel3"
    echo ""
    echo "示例:"
    echo "  $0 start           # 启动Redis集群"
    echo "  $0 connect master  # 连接到主节点"
    echo "  $0 execute master 'SET key value' # 在主节点执行命令"
    echo "  $0 backup          # 创建备份"
    echo "  $0 monitor         # 监控集群状态"
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
            start_redis
            ;;
        "stop")
            stop_redis
            ;;
        "restart")
            restart_redis
            ;;
        "status")
            status_redis
            ;;
        "connect")
            connect_redis "${2:-master}"
            ;;
        "execute")
            execute_redis_command "${2:-master}" "${@:3}"
            ;;
        "backup")
            create_backup
            ;;
        "clear")
            clear_redis "${2:-master}"
            ;;
        "monitor")
            monitor_redis
            ;;
        "logs")
            logs_redis "${2:-}" "${3:-50}"
            ;;
        "performance")
            performance_test
            ;;
        "failover")
            failover_test
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