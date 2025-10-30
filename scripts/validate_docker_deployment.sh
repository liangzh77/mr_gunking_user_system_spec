#!/bin/bash
# =============================================================================
# Docker部署验证脚本
# =============================================================================
# 用途：自动验证Docker Compose配置和部署流程
# 用法：./validate_docker_deployment.sh [dev|prod]
# =============================================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查步骤函数
check_step() {
    local description=$1
    local command=$2

    echo ""
    log_info "检查: $description"

    if eval "$command"; then
        log_success "$description - 通过"
        return 0
    else
        log_error "$description - 失败"
        return 1
    fi
}

# 环境选择
ENV=${1:-dev}
if [ "$ENV" != "dev" ] && [ "$ENV" != "prod" ]; then
    log_error "无效的环境参数。使用方法: $0 [dev|prod]"
    exit 1
fi

COMPOSE_FILE="docker-compose.yml"
if [ "$ENV" == "prod" ]; then
    COMPOSE_FILE="docker-compose.yml"
fi

log_info "开始验证 ${ENV} 环境的Docker部署配置"
log_info "使用配置文件: $COMPOSE_FILE"

# =============================================================================
# 1. 前置检查
# =============================================================================
echo ""
echo "================================="
echo "阶段 1: 前置环境检查"
echo "================================="

check_step "Docker已安装" "command -v docker &> /dev/null"
check_step "Docker Compose已安装" "command -v docker-compose &> /dev/null"
check_step "Docker服务运行中" "docker info &> /dev/null"

# =============================================================================
# 2. 配置文件验证
# =============================================================================
echo ""
echo "================================="
echo "阶段 2: 配置文件验证"
echo "================================="

check_step "docker-compose.yml语法正确" "docker-compose -f $COMPOSE_FILE config > /dev/null"

if [ "$ENV" == "dev" ]; then
    check_step "开发环境配置文件存在" "test -f backend/.env.development"
else
    check_step "生产环境配置文件存在" "test -f backend/.env.production"
    check_step "环境变量POSTGRES_PASSWORD已设置" "test -n \"\$POSTGRES_PASSWORD\""
    check_step "环境变量REDIS_PASSWORD已设置" "test -n \"\$REDIS_PASSWORD\""
fi

# =============================================================================
# 3. Dockerfile验证
# =============================================================================
echo ""
echo "================================="
echo "阶段 3: Dockerfile验证"
echo "================================="

if [ "$ENV" == "dev" ]; then
    check_step "后端开发Dockerfile存在" "test -f backend/Dockerfile.dev"
    check_step "前端开发Dockerfile存在" "test -f frontend/Dockerfile.dev"
else
    check_step "后端生产Dockerfile存在" "test -f backend/Dockerfile"
    check_step "前端生产Dockerfile存在" "test -f frontend/Dockerfile"
fi

# =============================================================================
# 4. 构建镜像测试
# =============================================================================
echo ""
echo "================================="
echo "阶段 4: Docker镜像构建测试"
echo "================================="

log_info "开始构建Docker镜像（这可能需要几分钟）..."

if docker-compose -f $COMPOSE_FILE build --no-cache 2>&1 | tee /tmp/docker_build.log; then
    log_success "Docker镜像构建成功"
else
    log_error "Docker镜像构建失败，请检查 /tmp/docker_build.log"
    exit 1
fi

# =============================================================================
# 5. 启动服务测试
# =============================================================================
echo ""
echo "================================="
echo "阶段 5: 服务启动测试"
echo "================================="

log_info "停止可能存在的旧容器..."
docker-compose -f $COMPOSE_FILE down -v 2>/dev/null || true

log_info "启动所有服务..."
if docker-compose -f $COMPOSE_FILE up -d; then
    log_success "所有服务已启动"
else
    log_error "服务启动失败"
    exit 1
fi

# 等待服务启动
log_info "等待服务初始化（30秒）..."
sleep 30

# =============================================================================
# 6. 服务健康检查
# =============================================================================
echo ""
echo "================================="
echo "阶段 6: 服务健康检查"
echo "================================="

# 检查容器状态
log_info "检查容器运行状态..."
docker-compose -f $COMPOSE_FILE ps

# 数据库健康检查
check_step "PostgreSQL数据库健康" \
    "docker-compose -f $COMPOSE_FILE exec -T postgres pg_isready -U mr_admin"

# Redis健康检查
if [ "$ENV" == "dev" ]; then
    check_step "Redis服务健康" \
        "docker-compose -f $COMPOSE_FILE exec -T redis redis-cli ping | grep -q PONG"
else
    check_step "Redis服务健康（带密码）" \
        "docker-compose -f $COMPOSE_FILE exec -T redis redis-cli -a \$REDIS_PASSWORD ping | grep -q PONG"
fi

# 后端API健康检查
log_info "等待后端API启动（额外10秒）..."
sleep 10

check_step "后端API响应" \
    "curl -f -s http://localhost:8000/health | grep -q healthy"

# =============================================================================
# 7. 数据库初始化测试
# =============================================================================
echo ""
echo "================================="
echo "阶段 7: 数据库初始化测试"
echo "================================="

BACKEND_CONTAINER=$(docker-compose -f $COMPOSE_FILE ps -q backend)

log_info "运行数据库迁移..."
if docker exec $BACKEND_CONTAINER alembic upgrade head; then
    log_success "数据库迁移成功"
else
    log_error "数据库迁移失败"
    docker-compose -f $COMPOSE_FILE logs backend
    exit 1
fi

log_info "运行初始化脚本..."
if docker exec $BACKEND_CONTAINER python init_data.py; then
    log_success "数据初始化成功"
else
    log_error "数据初始化失败"
    exit 1
fi

# =============================================================================
# 8. API功能测试
# =============================================================================
echo ""
echo "================================="
echo "阶段 8: API功能测试"
echo "================================="

# 测试管理员登录
log_info "测试管理员登录..."
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/auth/admins/login \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "Admin123"}')

if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    log_success "管理员登录成功"
    TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    log_info "获取到访问令牌: ${TOKEN:0:20}..."
else
    log_error "管理员登录失败"
    echo "响应: $LOGIN_RESPONSE"
fi

# 测试应用列表API
log_info "测试应用列表API..."
APPS_RESPONSE=$(curl -s http://localhost:8000/api/v1/applications)
if echo "$APPS_RESPONSE" | grep -q "app_name"; then
    log_success "应用列表API正常"
else
    log_warning "应用列表API可能有问题"
fi

# =============================================================================
# 9. 前端测试（如果有）
# =============================================================================
if [ "$ENV" == "dev" ]; then
    echo ""
    echo "================================="
    echo "阶段 9: 前端服务测试"
    echo "================================="

    log_info "等待前端服务启动（10秒）..."
    sleep 10

    check_step "前端服务响应" \
        "curl -f -s http://localhost:5173 > /dev/null"
fi

# =============================================================================
# 10. 日志检查
# =============================================================================
echo ""
echo "================================="
echo "阶段 10: 日志检查"
echo "================================="

log_info "检查服务日志（最后10行）..."
echo ""
echo "--- PostgreSQL日志 ---"
docker-compose -f $COMPOSE_FILE logs --tail=10 postgres

echo ""
echo "--- Redis日志 ---"
docker-compose -f $COMPOSE_FILE logs --tail=10 redis

echo ""
echo "--- 后端日志 ---"
docker-compose -f $COMPOSE_FILE logs --tail=10 backend

# =============================================================================
# 11. 资源使用情况
# =============================================================================
echo ""
echo "================================="
echo "阶段 11: 资源使用情况"
echo "================================="

log_info "容器资源使用统计:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

# =============================================================================
# 12. 网络连接测试
# =============================================================================
echo ""
echo "================================="
echo "阶段 12: 网络连接测试"
echo "================================="

log_info "检查容器网络连接..."
NETWORK_NAME=$(docker-compose -f $COMPOSE_FILE config | grep -A 1 "networks:" | tail -n 1 | tr -d ' ')
docker network inspect ${NETWORK_NAME} > /dev/null 2>&1 && log_success "Docker网络正常"

# =============================================================================
# 总结
# =============================================================================
echo ""
echo "================================="
echo "验证完成总结"
echo "================================="

log_success "所有验证步骤完成！"
echo ""
log_info "运行中的容器:"
docker-compose -f $COMPOSE_FILE ps

echo ""
log_info "访问地址:"
echo "  - 后端API: http://localhost:8000/api/docs"
echo "  - 健康检查: http://localhost:8000/health"
if [ "$ENV" == "dev" ]; then
    echo "  - 前端应用: http://localhost:5173"
    echo "  - PgAdmin: http://localhost:5050"
    echo "  - Redis Commander: http://localhost:8081"
fi

echo ""
log_info "默认账户:"
echo "  - 管理员: admin / Admin123"

echo ""
log_info "常用命令:"
echo "  - 查看日志: docker-compose -f $COMPOSE_FILE logs -f [service]"
echo "  - 停止服务: docker-compose -f $COMPOSE_FILE down"
echo "  - 重启服务: docker-compose -f $COMPOSE_FILE restart [service]"
echo "  - 进入容器: docker-compose -f $COMPOSE_FILE exec [service] bash"

echo ""
log_success "验证脚本执行完成！"
