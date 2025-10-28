#!/bin/bash
# =============================================================================
# MR游戏运营系统 - 自动部署脚本
# =============================================================================
# 用法: ./deploy.sh <host> <user> <environment> [branch]
# 示例: ./deploy.sh prod.example.com deploy production main
# =============================================================================

set -e  # 遇到错误立即退出
set -o pipefail  # 管道命令中任何一个失败都退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 参数
HOST=$1
USER=$2
ENVIRONMENT=$3
BRANCH=${4:-main}
PROJECT_DIR="/opt/mr_gunking_user_system_spec"
BACKUP_DIR="/var/backups/mr_game_ops"
COMPOSE_FILE="docker-compose.prod.yml"

# 检查参数
if [ -z "$HOST" ] || [ -z "$USER" ] || [ -z "$ENVIRONMENT" ]; then
    echo -e "${RED}❌ 错误: 缺少必需参数${NC}"
    echo "用法: $0 <host> <user> <environment> [branch]"
    echo "示例: $0 prod.example.com deploy production main"
    exit 1
fi

# 日志函数
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 记录部署开始时间
DEPLOY_START=$(date +%s)

log_info "=========================================="
log_info "开始部署到 $ENVIRONMENT 环境"
log_info "目标服务器: $USER@$HOST"
log_info "分支: $BRANCH"
log_info "时间: $(date '+%Y-%m-%d %H:%M:%S')"
log_info "=========================================="

# SSH到服务器执行部署
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 $USER@$HOST << ENDSSH
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "\${BLUE}ℹ️  \$1\${NC}"; }
log_success() { echo -e "\${GREEN}✅ \$1\${NC}"; }
log_warning() { echo -e "\${YELLOW}⚠️  \$1\${NC}"; }
log_error() { echo -e "\${RED}❌ \$1\${NC}"; }

# ==================== 1. 环境检查 ====================
log_info "步骤 1/10: 检查部署环境..."

if [ ! -d "$PROJECT_DIR" ]; then
    log_error "项目目录不存在: $PROJECT_DIR"
    exit 1
fi

cd $PROJECT_DIR

# 检查Docker是否运行
if ! docker info >/dev/null 2>&1; then
    log_error "Docker未运行或未安装"
    exit 1
fi

# 检查docker-compose
if ! command -v docker-compose &> /dev/null; then
    log_error "docker-compose未安装"
    exit 1
fi

log_success "环境检查通过"

# ==================== 2. 数据库备份 ====================
log_info "步骤 2/10: 备份数据库..."

# 创建备份目录
mkdir -p $BACKUP_DIR

# 生成备份文件名
BACKUP_FILE="$BACKUP_DIR/db_backup_\$(date +%Y%m%d_%H%M%S).sql"

# 备份PostgreSQL数据库
if docker-compose -f $COMPOSE_FILE ps postgres | grep -q Up; then
    log_info "正在备份数据库到: \$BACKUP_FILE"
    docker-compose -f $COMPOSE_FILE exec -T postgres pg_dump \
        -U \${POSTGRES_USER:-mr_admin} \
        -d \${POSTGRES_DB:-mr_game_ops} \
        > "\$BACKUP_FILE" 2>/dev/null || log_warning "数据库备份失败(如果是首次部署可忽略)"

    if [ -f "\$BACKUP_FILE" ]; then
        gzip "\$BACKUP_FILE"
        log_success "数据库备份完成: \${BACKUP_FILE}.gz"
    fi
else
    log_warning "PostgreSQL容器未运行,跳过备份"
fi

# 保留最近30天的备份
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete

# ==================== 3. 拉取最新代码 ====================
log_info "步骤 3/10: 拉取最新代码..."

# 保存当前commit hash
OLD_COMMIT=\$(git rev-parse HEAD)
log_info "当前版本: \$OLD_COMMIT"

# 拉取最新代码
git fetch origin
git reset --hard origin/$BRANCH
git checkout $BRANCH
git pull origin $BRANCH

NEW_COMMIT=\$(git rev-parse HEAD)
log_info "新版本: \$NEW_COMMIT"

if [ "\$OLD_COMMIT" = "\$NEW_COMMIT" ]; then
    log_warning "代码无变化,但继续部署"
else
    log_success "代码更新完成"
    log_info "变更内容:"
    git log --oneline --graph --decorate -5
fi

# ==================== 4. 环境配置检查 ====================
log_info "步骤 4/10: 检查环境配置..."

if [ ! -f "backend/.env.production" ]; then
    log_error "生产环境配置文件不存在: backend/.env.production"
    exit 1
fi

# 检查关键配置
if grep -q "CHANGE_THIS" backend/.env.production; then
    log_error "检测到未修改的默认密码,请检查 .env.production"
    exit 1
fi

log_success "环境配置检查通过"

# ==================== 5. 拉取Docker镜像 ====================
log_info "步骤 5/10: 拉取最新Docker镜像..."

docker-compose -f $COMPOSE_FILE pull || log_warning "镜像拉取失败,使用本地镜像"

log_success "镜像准备完成"

# ==================== 6. 构建新镜像 ====================
log_info "步骤 6/10: 构建Docker镜像..."

# 构建后端镜像
docker-compose -f $COMPOSE_FILE build --no-cache backend

# 构建前端镜像
docker-compose -f $COMPOSE_FILE build --no-cache frontend

log_success "镜像构建完成"

# ==================== 7. 停止旧服务 ====================
log_info "步骤 7/10: 优雅停止旧服务..."

# 获取运行中的容器
RUNNING_CONTAINERS=\$(docker-compose -f $COMPOSE_FILE ps -q)

if [ ! -z "\$RUNNING_CONTAINERS" ]; then
    log_info "停止现有容器..."
    docker-compose -f $COMPOSE_FILE down --timeout 30
    log_success "旧服务已停止"
else
    log_info "没有运行中的容器"
fi

# ==================== 8. 启动新服务 ====================
log_info "步骤 8/10: 启动新服务..."

# 启动所有服务
docker-compose -f $COMPOSE_FILE up -d

# 等待服务启动
log_info "等待服务启动..."
sleep 15

# 检查容器状态
log_info "容器状态:"
docker-compose -f $COMPOSE_FILE ps

log_success "新服务已启动"

# ==================== 9. 数据库迁移 ====================
log_info "步骤 9/10: 执行数据库迁移..."

# 等待数据库就绪
log_info "等待数据库就绪..."
sleep 10

# 执行迁移
if docker-compose -f $COMPOSE_FILE exec -T backend alembic upgrade head; then
    log_success "数据库迁移完成"
else
    log_error "数据库迁移失败!"
    log_warning "正在回滚..."
    docker-compose -f $COMPOSE_FILE down
    # 这里可以添加恢复备份的逻辑
    exit 1
fi

# ==================== 10. 健康检查 ====================
log_info "步骤 10/10: 执行健康检查..."

# 等待应用完全启动
sleep 10

# 检查后端健康
BACKEND_HEALTH=\$(docker-compose -f $COMPOSE_FILE exec -T backend curl -f http://localhost:8000/health 2>/dev/null || echo "FAIL")

if echo "\$BACKEND_HEALTH" | grep -q "ok"; then
    log_success "后端服务健康检查通过"
else
    log_error "后端服务健康检查失败!"
    log_info "后端日志:"
    docker-compose -f $COMPOSE_FILE logs --tail=50 backend

    log_warning "部署可能失败,请检查日志"
    exit 1
fi

# 检查前端
if curl -f http://localhost:80 >/dev/null 2>&1; then
    log_success "前端服务健康检查通过"
else
    log_warning "前端服务可能未就绪,请稍后检查"
fi

# 检查数据库
if docker-compose -f $COMPOSE_FILE exec -T postgres pg_isready -U \${POSTGRES_USER:-mr_admin} >/dev/null 2>&1; then
    log_success "数据库健康检查通过"
else
    log_warning "数据库健康检查失败"
fi

# 检查Redis
if docker-compose -f $COMPOSE_FILE exec -T redis redis-cli ping | grep -q PONG; then
    log_success "Redis健康检查通过"
else
    log_warning "Redis健康检查失败"
fi

# ==================== 清理 ====================
log_info "清理未使用的Docker资源..."
docker system prune -f --volumes >/dev/null 2>&1 || true

log_success "资源清理完成"

# ==================== 部署完成 ====================
echo ""
echo "=========================================="
log_success "🎉 部署成功完成!"
echo "=========================================="
echo "环境: $ENVIRONMENT"
echo "版本: \$NEW_COMMIT"
echo "时间: \$(date '+%Y-%m-%d %H:%M:%S')"
echo ""
log_info "服务状态:"
docker-compose -f $COMPOSE_FILE ps
echo ""
log_info "访问地址:"
echo "  - 前端: http://$HOST"
echo "  - 后端API: http://$HOST/api/v1"
echo "  - API文档: http://$HOST/api/v1/docs"
echo ""
log_warning "请及时查看日志确保服务正常运行:"
echo "  docker-compose -f $COMPOSE_FILE logs -f"
echo "=========================================="

ENDSSH

# 检查SSH执行结果
SSH_EXIT_CODE=$?

if [ $SSH_EXIT_CODE -eq 0 ]; then
    # 计算部署耗时
    DEPLOY_END=$(date +%s)
    DEPLOY_DURATION=$((DEPLOY_END - DEPLOY_START))

    echo ""
    log_success "=========================================="
    log_success "部署到 $ENVIRONMENT 环境完成!"
    log_success "总耗时: ${DEPLOY_DURATION}秒"
    log_success "=========================================="
    exit 0
else
    log_error "=========================================="
    log_error "部署失败! 退出代码: $SSH_EXIT_CODE"
    log_error "=========================================="
    exit $SSH_EXIT_CODE
fi
