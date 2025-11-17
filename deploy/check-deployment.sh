#!/bin/bash

# =============================================================================
# 部署验证脚本 - 检查所有服务是否正常运行
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_check() {
    echo -n "  检查 $1... "
}

print_ok() {
    echo -e "${GREEN}✓ 正常${NC}"
}

print_fail() {
    echo -e "${RED}✗ 失败${NC}"
    echo -e "    ${YELLOW}$1${NC}"
}

print_warn() {
    echo -e "${YELLOW}⚠ 警告${NC}"
    echo -e "    ${YELLOW}$1${NC}"
}

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║              MR游戏运营管理系统 - 部署验证检查                     ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

cd /opt/mr-game-ops

# 加载环境变量
if [ -f .env.prod ]; then
    set -a
    source .env.prod
    set +a
else
    echo "错误: 未找到.env.prod配置文件"
    exit 1
fi

# ============================================================================
# 1. 检查Docker服务
# ============================================================================
echo "【1】Docker环境检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

print_check "Docker是否运行"
if docker ps > /dev/null 2>&1; then
    print_ok
else
    print_fail "Docker未运行，请执行: sudo systemctl start docker"
    exit 1
fi

print_check "Docker Compose版本"
if docker compose version > /dev/null 2>&1; then
    VERSION=$(docker compose version --short)
    echo -e "${GREEN}✓ $VERSION${NC}"
else
    print_fail "Docker Compose未安装"
    exit 1
fi

echo ""

# ============================================================================
# 2. 检查容器状态
# ============================================================================
echo "【2】容器运行状态检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

CONTAINERS=(
    "mr_game_ops_db_prod:PostgreSQL数据库"
    "mr_game_ops_redis_prod:Redis缓存"
    "mr_game_ops_backend_prod:后端API"
    "mr_game_ops_frontend_prod:前端应用"
    "mr_game_ops_nginx:Nginx网关"
    "mr_game_ops_prometheus:Prometheus监控"
    "mr_game_ops_grafana:Grafana可视化"
)

ALL_RUNNING=true

for item in "${CONTAINERS[@]}"; do
    IFS=':' read -r container_name display_name <<< "$item"
    print_check "$display_name"

    if docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
        STATUS=$(docker inspect --format='{{.State.Status}}' $container_name 2>/dev/null || echo "not found")
        if [ "$STATUS" = "running" ]; then
            print_ok
        else
            print_fail "容器状态: $STATUS"
            ALL_RUNNING=false
        fi
    else
        print_fail "容器未运行"
        ALL_RUNNING=false
    fi
done

echo ""

# ============================================================================
# 3. 检查服务健康状态
# ============================================================================
echo "【3】服务健康状态检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# PostgreSQL
print_check "PostgreSQL连接"
if docker exec mr_game_ops_db_prod pg_isready -U $POSTGRES_USER -d $POSTGRES_DB > /dev/null 2>&1; then
    print_ok
else
    print_fail "数据库连接失败"
    ALL_RUNNING=false
fi

# Redis
print_check "Redis连接"
if docker exec mr_game_ops_redis_prod redis-cli -a "$REDIS_PASSWORD" --no-auth-warning ping 2>/dev/null | grep -q PONG; then
    print_ok
else
    print_fail "Redis连接失败"
    ALL_RUNNING=false
fi

# Backend API
print_check "后端API健康检查"
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
if [ "$HEALTH_RESPONSE" = "200" ]; then
    print_ok
elif [ "$HEALTH_RESPONSE" = "000" ]; then
    print_fail "无法连接到API，容器可能还在启动中"
else
    print_fail "API返回错误: HTTP $HEALTH_RESPONSE"
fi

# API文档
print_check "API文档访问"
DOCS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs 2>/dev/null || echo "000")
if [ "$DOCS_RESPONSE" = "200" ]; then
    print_ok
else
    print_warn "API文档无法访问"
fi

# Grafana
print_check "Grafana监控面板"
GRAFANA_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3001 2>/dev/null || echo "000")
if [ "$GRAFANA_RESPONSE" = "200" ] || [ "$GRAFANA_RESPONSE" = "302" ]; then
    print_ok
else
    print_warn "Grafana无法访问"
fi

# Prometheus
print_check "Prometheus监控"
PROM_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:9090 2>/dev/null || echo "000")
if [ "$PROM_RESPONSE" = "200" ]; then
    print_ok
else
    print_warn "Prometheus无法访问"
fi

echo ""

# ============================================================================
# 4. 检查数据库表
# ============================================================================
echo "【4】数据库结构检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

print_check "数据库是否已初始化"
TABLE_COUNT=$(docker exec mr_game_ops_db_prod psql -U $POSTGRES_USER -d $POSTGRES_DB -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | tr -d ' ')

if [ "$TABLE_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ 已创建 $TABLE_COUNT 个表${NC}"
else
    print_warn "数据库未初始化，需要运行数据库迁移"
fi

echo ""

# ============================================================================
# 5. 检查资源使用
# ============================================================================
echo "【5】系统资源使用检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "  容器资源使用情况:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep mr_game_ops

echo ""

# ============================================================================
# 6. 检查网络端口
# ============================================================================
echo "【6】网络端口检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

PORTS=("80:HTTP" "443:HTTPS" "3001:Grafana" "9090:Prometheus")

for item in "${PORTS[@]}"; do
    IFS=':' read -r port service <<< "$item"
    print_check "$service端口($port)"

    if ss -tuln | grep -q ":$port "; then
        print_ok
    else
        print_warn "端口未监听"
    fi
done

echo ""

# ============================================================================
# 7. 检查日志
# ============================================================================
echo "【7】日志错误检查（最近50行）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

print_check "后端错误日志"
ERROR_COUNT=$(docker logs mr_game_ops_backend_prod 2>&1 | tail -50 | grep -i "error\|exception\|fatal" | wc -l)
if [ "$ERROR_COUNT" -eq 0 ]; then
    print_ok
else
    print_warn "发现 $ERROR_COUNT 个错误，请检查日志"
fi

echo ""

# ============================================================================
# 总结
# ============================================================================
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                       检查完成                                     ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

if [ "$ALL_RUNNING" = true ]; then
    echo -e "${GREEN}✓ 所有核心服务运行正常${NC}"
    echo ""
    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "localhost")
    echo "🌐 访问地址:"
    echo "  - API健康检查: http://$SERVER_IP:8000/health"
    echo "  - API文档: http://$SERVER_IP:8000/docs"
    echo "  - Grafana: http://$SERVER_IP:3001 (admin / $GRAFANA_PASSWORD)"
    echo ""
else
    echo -e "${RED}✗ 部分服务存在问题，请检查日志${NC}"
    echo ""
    echo "查看详细日志:"
    echo "  docker compose -f /opt/mr-game-ops/docker-compose.yml logs"
    echo ""
fi

echo "📝 完整日志命令:"
echo "  cd /opt/mr-game-ops"
echo "  docker compose logs -f [服务名]"
echo ""
echo "可用服务名: postgres, redis, backend, frontend, nginx, prometheus, grafana"
echo ""
