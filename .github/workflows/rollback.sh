#!/bin/bash
# =============================================================================
# 回滚脚本 - 紧急情况下回滚到上一个版本
# =============================================================================
# 用法: ./rollback.sh <host> <user> [commit_hash]
# 示例: ./rollback.sh prod.example.com deploy abc1234
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

HOST=$1
USER=$2
COMMIT=$3  # 可选,指定回滚到的commit

if [ -z "$HOST" ] || [ -z "$USER" ]; then
    log_error "用法: $0 <host> <user> [commit_hash]"
    exit 1
fi

log_warning "=========================================="
log_warning "⚠️  准备执行回滚操作"
log_warning "目标服务器: $USER@$HOST"
log_warning "=========================================="

read -p "确认要回滚吗? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    log_info "回滚已取消"
    exit 0
fi

ssh -o StrictHostKeyChecking=no $USER@$HOST << ENDSSH
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "\${BLUE}ℹ️  \$1\${NC}"; }
log_success() { echo -e "\${GREEN}✅ \$1\${NC}"; }
log_warning() { echo -e "\${YELLOW}⚠️  \$1\${NC}"; }

PROJECT_DIR="/opt/mr_gunking_user_system_spec"
COMPOSE_FILE="docker-compose.yml"
BACKUP_DIR="/var/backups/mr_game_ops"

cd \$PROJECT_DIR

log_info "当前版本: \$(git rev-parse HEAD)"
log_info "当前分支: \$(git branch --show-current)"

# 确定回滚目标
if [ -z "$COMMIT" ]; then
    # 回滚到上一个commit
    TARGET_COMMIT=\$(git rev-parse HEAD~1)
    log_warning "将回滚到上一个版本: \$TARGET_COMMIT"
else
    TARGET_COMMIT=$COMMIT
    log_warning "将回滚到指定版本: \$TARGET_COMMIT"
fi

# 检查commit是否存在
if ! git cat-file -e \$TARGET_COMMIT 2>/dev/null; then
    log_error "commit不存在: \$TARGET_COMMIT"
    exit 1
fi

# 停止服务
log_info "停止当前服务..."
docker-compose -f \$COMPOSE_FILE down

# 回滚代码
log_info "回滚代码到 \$TARGET_COMMIT..."
git reset --hard \$TARGET_COMMIT

# 重新构建镜像
log_info "重新构建Docker镜像..."
docker-compose -f \$COMPOSE_FILE build

# 启动服务
log_info "启动服务..."
docker-compose -f \$COMPOSE_FILE up -d

# 等待服务启动
sleep 15

# 健康检查
log_info "执行健康检查..."
if docker-compose -f \$COMPOSE_FILE exec -T backend curl -f http://localhost:8000/health 2>/dev/null | grep -q "ok"; then
    log_success "回滚成功!"
    log_info "当前版本: \$(git rev-parse HEAD)"
else
    log_error "回滚后服务异常!"
    docker-compose -f \$COMPOSE_FILE logs --tail=50 backend
    exit 1
fi

log_success "回滚完成"
docker-compose -f \$COMPOSE_FILE ps

ENDSSH

log_success "回滚操作完成!"
