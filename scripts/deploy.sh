#!/bin/bash
# =============================================================================
# MR游戏运营管理系统 - 一键部署脚本
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_header() {
    echo -e "${PURPLE}============================================================================${NC}"
    echo -e "${PURPLE}  $1${NC}"
    echo -e "${PURPLE}============================================================================${NC}"
}

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

print_step() {
    echo -e "${CYAN}🔄 $1${NC}"
}

# 检查系统要求
check_requirements() {
    print_step "检查系统要求..."

    # 检查操作系统
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        print_success "操作系统: Linux"
    else
        print_warning "操作系统: 不是Linux，某些功能可能不可用"
    fi

    # 检查Docker
    if command -v docker &> /dev/null; then
        print_success "Docker: 已安装"
        docker_version=$(docker --version | cut -d' ' -f3)
        echo "   版本: $docker_version"
    else
        print_error "Docker: 未安装"
        print_info "请访问 https://docs.docker.com/get-docker/ 安装Docker"
        exit 1
    fi

    # 检查Docker Compose
    if command -v docker-compose &> /dev/null; then
        print_success "Docker Compose: 已安装"
        compose_version=$(docker-compose --version | cut -d' ' -f3)
        echo "   版本: $compose_version"
    else
        print_error "Docker Compose: 未安装"
        print_info "请安装Docker Compose"
        exit 1
    fi

    # 检查Python
    if command -v python3 &> /dev/null; then
        print_success "Python: 已安装"
        python_version=$(python3 --version)
        echo "   版本: $python_version"
    else
        print_error "Python: 未安装"
        print_info "请安装Python 3.11+"
        exit 1
    fi

    # 检查Node.js
    if command -v node &> /dev/null; then
        print_success "Node.js: 已安装"
        node_version=$(node --version)
        echo "   版本: $node_version"
    else
        print_error "Node.js: 未安装"
        print_info "请访问 https://nodejs.org/ 安装Node.js"
        exit 1
    fi

    # 检查可用内存
    total_mem=$(free -m | awk 'NR==2{printf "%.0f", $2}')
    if [ "$total_mem" -lt 2048 ]; then
        print_warning "内存: ${total_mem}MB (建议至少4GB)"
    else
        print_success "内存: ${total_mem}MB"
    fi

    # 检查可用磁盘空间
    available_space=$(df -BG . | awk 'NR==2{print $4}')
    if [ "${available_space%G}" -lt 10 ]; then
        print_warning "磁盘空间: ${available_space} (建议至少10GB)"
    else
        print_success "磁盘空间: ${available_space}"
    fi
}

# 创建项目目录结构
create_directories() {
    print_step "创建项目目录结构..."

    # 创建必要的目录
    mkdir -p logs/{backend,nginx,postgres,redis,archived}
    mkdir -p backups/{daily,weekly,monthly}
    mkdir -p uploads/{invoices,temp}
    mkdir -p data/{postgres,redis,nginx}
    mkdir -p ssl/{certs,private}
    mkdir -p monitoring/{prometheus,grafana,alertmanager}

    # 设置权限
    chmod 755 logs backups uploads data ssl monitoring
    chmod 600 ssl/private/*
    chmod 644 ssl/certs/*

    print_success "目录结构创建完成"
}

# 配置环境变量
setup_environment() {
    print_step "配置环境变量..."

    # 检查.env文件
    if [ ! -f ".env" ]; then
        print_info "创建开发环境配置文件..."
        cp .env.example .env
        print_warning "请编辑 .env 文件配置开发环境"
    fi

    # 检查生产环境配置
    if [ ! -f ".env.production" ]; then
        print_info "创建生产环境配置文件..."
        print_warning "请编辑 .env.production 文件配置生产环境"
    fi

    print_success "环境配置完成"
}

# 生成安全密钥
generate_secrets() {
    print_step "生成安全密钥..."

    # 检查是否需要生成密钥
    if grep -q "CHANGE_THIS" .env.production 2>/dev/null; then
        print_info "生成新的安全密钥..."

        # 生成SECRET_KEY
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
        sed -i "s/CHANGE_THIS_TO_RANDOM_STRING_AT_LEAST_32_CHARACTERS_LONG_PRODUCTION/$SECRET_KEY/g" .env.production

        # 生成JWT_SECRET_KEY
        JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
        sed -i "s/CHANGE_THIS_TO_ANOTHER_RANDOM_STRING_32_CHARS_PRODUCTION/$JWT_SECRET_KEY/g" .env.production

        # 生成ENCRYPTION_KEY
        ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_bytes(32).decode())")
        sed -i "s/CHANGE_THIS_32_BYTES_ENCRYPTION/$ENCRYPTION_KEY/g" .env.production

        # 生成数据库密码
        DB_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
        sed -i "s/CHANGE_THIS_PASSWORD/$DB_PASSWORD/g" .env.production

        # 生成Redis密码
        REDIS_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")
        sed -i "s/CHANGE_THIS_REDIS_PASSWORD/$REDIS_PASSWORD/g" .env.production

        print_success "安全密钥生成完成"
    else
        print_success "安全密钥已配置"
    fi
}

# 构建应用
build_application() {
    print_step "构建应用..."

    # 构建后端
    print_info "构建后端Docker镜像..."
    docker build -t mr_game_ops_backend:latest ./backend

    # 构建前端
    print_info "构建前端Docker镜像..."
    docker build -t mr_game_ops_frontend:latest ./frontend

    print_success "应用构建完成"
}

# 启动服务
start_services() {
    print_step "启动服务..."

    # 停止现有服务
    print_info "停止现有服务..."
    docker-compose -f docker-compose.yml down 2>/dev/null || true
    docker-compose -f docker-compose.yml down 2>/dev/null || true

    # 启动开发环境或生产环境
    if [ "$1" = "production" ]; then
        print_info "启动生产环境服务..."
        docker-compose -f docker-compose.yml up -d

        # 等待服务启动
        print_info "等待服务启动..."
        sleep 10

        # 检查服务状态
        print_info "检查服务状态..."
        docker-compose -f docker-compose.yml ps

        # 运行数据库迁移
        print_info "运行数据库迁移..."
        docker-compose -f docker-compose.yml exec -T backend python -m alembic upgrade head

        print_success "生产环境服务启动完成"
        print_info "访问地址:"
        print_info "  前端: http://localhost"
        print_info "  后端API: http://localhost/api/v1"
        print_info "  API文档: http://localhost/api/docs"

    else
        print_info "启动开发环境服务..."
        docker-compose -f docker-compose.yml up -d

        # 等待服务启动
        print_info "等待服务启动..."
        sleep 5

        print_success "开发环境服务启动完成"
        print_info "访问地址:"
        print_info "  前端: http://localhost:5173"
        print_info "  后端API: http://localhost:8000/api/v1"
        print_info "  API文档: http://localhost:8000/api/docs"
    fi
}

# 运行健康检查
health_check() {
    print_step "运行健康检查..."

    # 等待服务完全启动
    sleep 5

    # 检查后端健康状态
    if command -v curl &> /dev/null; then
        if [ "$1" = "production" ]; then
            backend_url="http://localhost/api/v1/health"
        else
            backend_url="http://localhost:8000/health"
        fi

        if curl -f "$backend_url" &> /dev/null; then
            print_success "后端服务健康检查通过"
        else
            print_error "后端服务健康检查失败"
            print_info "请检查服务日志: docker-compose logs backend"
            return 1
        fi
    else
        print_warning "curl未安装，跳过健康检查"
    fi
}

# 运行测试
run_tests() {
    print_step "运行测试..."

    # 运行后端测试
    if [ -d "tests" ]; then
        print_info "运行后端测试..."
        cd backend
        python -m pytest tests/ -v --tb=short || print_warning "部分测试失败"
        cd ..
    fi

    print_success "测试完成"
}

# 显示部署信息
show_deployment_info() {
    print_header "部署完成"

    print_info "📊 服务状态:"
    if [ "$1" = "production" ]; then
        docker-compose -f docker-compose.yml ps
    else
        docker-compose -f docker-compose.yml ps
    fi

    print_info "🔧 管理命令:"
    if [ "$1" = "production" ]; then
        echo "  查看日志: docker-compose -f docker-compose.yml logs [service]"
        echo "  重启服务: docker-compose -f docker-compose.yml restart [service]"
        echo "  停止服务: docker-compose -f docker-compose.yml down"
    else
        echo "  查看日志: docker-compose -f docker-compose.yml logs [service]"
        echo "  重启服务: docker-compose -f docker-compose.yml restart [service]"
        echo "  停止服务: docker-compose -f docker-compose.yml down"
    fi

    print_info "📚 文档地址:"
    echo "  API文档: http://localhost/api/docs"
    echo "  系统监控: http://localhost:3001 (如果已启用)"
    echo "  配置文档: README.md"

    if [ "$1" = "production" ]; then
        print_warning "🔒 生产环境提醒:"
        echo "  1. 确保已配置真实的SSL证书"
        echo "  2. 配置防火墙规则"
        echo "  3. 定期备份数据"
        echo "  4. 监控系统资源使用"
        echo "  5. 定期更新依赖包"
    fi
}

# 显示帮助信息
show_help() {
    echo "MR游戏运营管理系统 - 一键部署脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  production    部署生产环境"
    echo "  dev           部署开发环境 (默认)"
    echo "  build         仅构建应用"
    echo "  start         仅启动服务"
    echo "  test           运行测试"
    echo "  health        运行健康检查"
    echo "  clean         清理资源"
    echo "  help          显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                    # 部署开发环境"
    echo "  $0 production        # 部署生产环境"
    echo "  $0 build             # 构建应用"
    echo "  $0 clean             # 清理所有资源"
}

# 清理资源
clean_resources() {
    print_step "清理资源..."

    # 停止所有服务
    docker-compose -f docker-compose.yml down 2>/dev/null || true
    docker-compose -f docker-compose.yml down 2>/dev/null || true

    # 删除Docker镜像
    docker rmi mr_game_ops_backend:latest 2>/dev/null || true
    docker rmi mr_game_ops_frontend:latest 2>/dev/null || true

    # 清理未使用的Docker资源
    docker system prune -f

    print_success "资源清理完成"
}

# 主函数
main() {
    print_header "MR游戏运营管理系统 - 一键部署"

    case "${1:-dev}" in
        "production")
            check_requirements
            create_directories
            setup_environment
            generate_secrets
            build_application
            start_services production
            health_check production
            show_deployment_info production
            ;;
        "dev")
            check_requirements
            create_directories
            setup_environment
            build_application
            start_services dev
            health_check dev
            show_deployment_info dev
            ;;
        "build")
            build_application
            ;;
        "start")
            create_directories
            start_services "${2:-dev}"
            health_check "${2:-dev}"
            ;;
        "test")
            run_tests
            ;;
        "health")
            health_check "${2:-dev}"
            ;;
        "clean")
            clean_resources
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"