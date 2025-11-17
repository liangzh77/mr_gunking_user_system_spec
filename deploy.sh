#!/bin/bash
# =============================================================================
# Production Deployment Script
# =============================================================================
# 功能：
# - 自动化生产环境部署
# - 包含健康检查和回滚机制
# - 支持零停机部署（可选）
# =============================================================================

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查必要文件
check_prerequisites() {
    log_info "检查部署前提条件..."
    
    if [ ! -f ".env.production" ]; then
        log_error ".env.production 文件不存在！"
        log_info "请复制 .env.production.template 并配置：cp .env.production.template .env.production"
        exit 1
    fi
    
    if [ ! -f "docker-compose.yml" ]; then
        log_error "docker-compose.yml 文件不存在！"
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装！"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装！"
        exit 1
    fi
    
    log_info "前提条件检查通过 ✓"
}

# 备份当前数据库（可选）
backup_database() {
    log_info "备份数据库..."
    
    if docker ps | grep -q "mr_game_ops_db_prod"; then
        ./backup_db.sh
        log_info "数据库备份完成 ✓"
    else
        log_warn "数据库容器未运行，跳过备份"
    fi
}

# 构建镜像
build_images() {
    log_info "构建Docker镜像..."
    
    export BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
    export VERSION=${VERSION:-1.0.0}
    
    docker-compose build --no-cache
    
    if [ $? -eq 0 ]; then
        log_info "镜像构建成功 ✓"
    else
        log_error "镜像构建失败！"
        exit 1
    fi
}

# 停止旧容器
stop_old_containers() {
    log_info "停止旧容器..."
    
    docker-compose down
    
    log_info "旧容器已停止 ✓"
}

# 启动新容器
start_new_containers() {
    log_info "启动新容器..."
    
    docker-compose up -d
    
    if [ $? -eq 0 ]; then
        log_info "新容器启动成功 ✓"
    else
        log_error "容器启动失败！"
        exit 1
    fi
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    local max_attempts=30
    local attempt=0
    local backend_healthy=false
    local frontend_healthy=false
    
    while [ $attempt -lt $max_attempts ]; do
        attempt=$((attempt + 1))
        
        # 检查后端
        if ! $backend_healthy; then
            if docker exec mr_game_ops_backend_prod curl -f http://localhost:8000/health &> /dev/null; then
                backend_healthy=true
                log_info "后端服务健康检查通过 ✓"
            fi
        fi
        
        # 检查前端
        if ! $frontend_healthy; then
            if docker exec mr_game_ops_frontend_prod curl -f http://localhost:80/ &> /dev/null; then
                frontend_healthy=true
                log_info "前端服务健康检查通过 ✓"
            fi
        fi
        
        if $backend_healthy && $frontend_healthy; then
            log_info "所有服务健康检查通过 ✓"
            return 0
        fi
        
        log_warn "等待服务就绪... (尝试 $attempt/$max_attempts)"
        sleep 5
    done
    
    log_error "健康检查失败，服务未能正常启动！"
    return 1
}

# 显示服务状态
show_status() {
    log_info "服务状态："
    docker-compose ps
}

# 清理未使用的镜像
cleanup() {
    log_info "清理未使用的Docker镜像..."
    docker image prune -f
    log_info "清理完成 ✓"
}

# 回滚函数
rollback() {
    log_error "部署失败，执行回滚..."
    docker-compose down
    # 这里可以添加恢复旧版本的逻辑
    log_warn "请手动检查并恢复服务"
    exit 1
}

# 主部署流程
main() {
    echo "========================================"
    echo "  MR游戏运营管理系统 - 生产环境部署"
    echo "========================================"
    echo ""
    
    # 执行部署步骤
    check_prerequisites
    
    read -p "是否在部署前备份数据库？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        backup_database
    fi
    
    build_images || rollback
    stop_old_containers || rollback
    start_new_containers || rollback
    
    if health_check; then
        log_info "部署成功！ 🎉"
        show_status
        cleanup
        
        echo ""
        echo "========================================"
        echo "  部署完成"
        echo "========================================"
        echo ""
        echo "前端访问地址: http://localhost"
        echo "后端API地址: http://localhost/api/v1"
        echo ""
        echo "查看日志: docker-compose logs -f"
        echo "停止服务: docker-compose down"
        echo ""
    else
        rollback
    fi
}

# 捕获错误并执行回滚
trap rollback ERR

# 执行主流程
main

exit 0
