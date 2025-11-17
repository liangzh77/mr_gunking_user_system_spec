#!/bin/bash

# =============================================================================
# MR游戏运营管理系统 - 一键自动部署脚本 V2 (改进版)
# =============================================================================
# 改进点:
#   - 添加超时机制，防止docker load卡住
#   - 显示详细错误信息，不隐藏输出
#   - 更好的错误处理
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# 输出函数
print_header() { echo -e "${MAGENTA}╔════════════════════════════════════════════════════════════════════╗${NC}"; echo -e "${MAGENTA}║${NC} $1"; echo -e "${MAGENTA}╚════════════════════════════════════════════════════════════════════╝${NC}"; }
print_step() { echo -e "${BLUE}==>${NC} $1"; }
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
print_info() { echo -e "${CYAN}ℹ${NC} $1"; }

# 错误处理
error_exit() {
    print_error "$1"
    echo ""
    echo "部署失败。请查看上述错误信息并修复后重试。"
    exit 1
}

print_header "    MR游戏运营管理系统 - 一键自动部署工具 V2    "
echo ""

# =============================================================================
# 步骤0: 前置检查
# =============================================================================
print_step "【步骤0/8】环境检查..."
echo ""

# 检查Docker
if ! command -v docker &> /dev/null; then
    error_exit "Docker未安装！请先安装Docker。"
fi

if ! docker ps &> /dev/null; then
    error_exit "Docker服务未运行！请启动Docker服务: systemctl start docker"
fi

print_success "Docker已安装并运行"

# 检查docker-compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    error_exit "Docker Compose未安装！请先安装Docker Compose。"
fi

print_success "Docker Compose已安装"

# 检查curl
if ! command -v curl &> /dev/null; then
    print_warning "curl未安装，正在安装..."
    apt-get update -qq && apt-get install -y curl -qq
fi

# 检查timeout命令
if ! command -v timeout &> /dev/null; then
    print_warning "timeout命令不可用，将不使用超时机制"
    TIMEOUT_CMD=""
else
    TIMEOUT_CMD="timeout 300"  # 5分钟超时
fi

print_success "环境检查通过"

# =============================================================================
# 步骤1: 自动检测脚本所在目录
# =============================================================================
echo ""
print_step "【步骤1/8】检测项目文件..."
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(dirname "$SCRIPT_DIR")"

print_info "脚本位置: $SCRIPT_DIR"
print_info "项目根目录: $SOURCE_DIR"

# 验证关键文件
MISSING_FILES=()

[ ! -d "$SOURCE_DIR/backend" ] && MISSING_FILES+=("backend/")
[ ! -d "$SOURCE_DIR/deploy" ] && MISSING_FILES+=("deploy/")
[ ! -f "$SOURCE_DIR/deploy/docker-compose.yml" ] && MISSING_FILES+=("deploy/docker-compose.yml")
[ ! -f "$SOURCE_DIR/deploy/.env.prod" ] && MISSING_FILES+=("deploy/.env.prod")

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
    print_error "以下关键文件/目录缺失:"
    for file in "${MISSING_FILES[@]}"; do
        echo "  - $file"
    done
    echo ""
    error_exit "请确保上传了完整的项目文件"
fi

print_success "项目文件检测完成"

# =============================================================================
# 步骤2: 检查并导入Docker镜像（改进版）
# =============================================================================
echo ""
print_step "【步骤2/8】检查Docker镜像..."
echo ""

IMAGES_DIR="/root/docker-images"

if [ ! -d "$IMAGES_DIR" ]; then
    print_warning "镜像目录不存在: $IMAGES_DIR"
    echo ""
    read -p "是否跳过镜像导入？(如果已经导入过，输入y) [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error_exit "请先上传镜像文件到: $IMAGES_DIR"
    fi
    print_warning "跳过镜像导入步骤"
    SKIP_IMPORT=true
else
    SKIP_IMPORT=false
fi

if [ "$SKIP_IMPORT" = false ]; then
    cd "$IMAGES_DIR"
    TAR_COUNT=$(ls -1 *.tar 2>/dev/null | wc -l)

    if [ "$TAR_COUNT" -eq 0 ]; then
        print_warning "未找到 .tar 镜像文件"
        read -p "是否跳过镜像导入？(如果已经导入过，输入y) [y/N]: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            error_exit "请先上传镜像文件"
        fi
    else
        print_success "找到 $TAR_COUNT 个镜像文件"
        echo ""
        echo "镜像文件列表:"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ls -lh *.tar | awk '{printf "  %-40s %10s\n", $9, $5}'
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""

        # 检查磁盘空间
        echo "检查磁盘空间..."
        df -h /var/lib/docker
        echo ""

        # 导入镜像（改进版：显示详细输出，添加超时）
        print_info "开始导入镜像（每个镜像最长5分钟）..."
        echo ""

        IMPORTED=0
        FAILED=0
        SKIPPED=0

        for tar_file in *.tar; do
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo "正在导入: $tar_file"
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

            # 检查文件大小
            FILE_SIZE=$(ls -lh "$tar_file" | awk '{print $5}')
            echo "文件大小: $FILE_SIZE"

            # 使用timeout防止卡住，显示详细输出
            if [ -n "$TIMEOUT_CMD" ]; then
                if $TIMEOUT_CMD docker load -i "$tar_file" 2>&1; then
                    echo -e "${GREEN}✓ 导入成功${NC}"
                    ((IMPORTED++))
                else
                    EXIT_CODE=$?
                    if [ $EXIT_CODE -eq 124 ]; then
                        echo -e "${RED}✗ 导入超时（5分钟）${NC}"
                        echo "  建议: 检查镜像文件是否损坏或磁盘空间是否足够"
                        ((FAILED++))
                    else
                        echo -e "${RED}✗ 导入失败 (退出码: $EXIT_CODE)${NC}"
                        ((FAILED++))
                    fi
                fi
            else
                # 没有timeout命令，直接导入
                if docker load -i "$tar_file" 2>&1; then
                    echo -e "${GREEN}✓ 导入成功${NC}"
                    ((IMPORTED++))
                else
                    echo -e "${RED}✗ 导入失败${NC}"
                    ((FAILED++))
                fi
            fi

            echo ""
        done

        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "  导入成功: $IMPORTED 个"
        [ "$FAILED" -gt 0 ] && echo "  导入失败: $FAILED 个"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""

        if [ "$IMPORTED" -eq 0 ]; then
            error_exit "没有成功导入任何镜像"
        fi

        print_success "镜像导入完成"

        # 显示已导入的镜像
        echo ""
        echo "已导入的镜像列表:"
        docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | head -20
    fi
fi

# =============================================================================
# 步骤3: 创建应用目录结构
# =============================================================================
echo ""
print_step "【步骤3/8】创建应用目录结构..."
echo ""

APP_DIR="/opt/mr-game-ops"

print_info "应用目录: $APP_DIR"

# 创建主要目录
mkdir -p "$APP_DIR"/{backend,frontend,deploy,config,data,logs,backups}
mkdir -p "$APP_DIR"/config/{nginx,prometheus,grafana}
mkdir -p "$APP_DIR"/data/{postgres,redis,prometheus,grafana,uploads,invoices}
mkdir -p "$APP_DIR"/logs/{nginx,backend}

print_success "目录结构创建完成"

# =============================================================================
# 步骤4: 复制应用文件
# =============================================================================
echo ""
print_step "【步骤4/8】复制应用文件到部署目录..."
echo ""

# 复制backend
if [ -d "$SOURCE_DIR/backend" ]; then
    print_info "复制backend目录..."
    cp -rf "$SOURCE_DIR/backend"/* "$APP_DIR/backend/" || error_exit "backend复制失败"
    print_success "backend文件已复制"
fi

# 复制frontend（如果存在）
if [ -d "$SOURCE_DIR/frontend" ]; then
    print_info "复制frontend目录..."
    cp -rf "$SOURCE_DIR/frontend"/* "$APP_DIR/frontend/" || error_exit "frontend复制失败"
    print_success "frontend文件已复制"
else
    print_warning "未找到frontend目录，跳过"
fi

# 复制deploy配置
if [ -d "$SOURCE_DIR/deploy" ]; then
    print_info "复制deploy配置..."
    cp -f "$SOURCE_DIR/deploy/.env.prod" "$APP_DIR/" || error_exit ".env.prod复制失败"
    cp -f "$SOURCE_DIR/deploy/docker-compose.yml" "$APP_DIR/" || error_exit "docker-compose.yml复制失败"

    # 复制nginx配置（如果存在）
    if [ -d "$SOURCE_DIR/deploy/config/nginx" ]; then
        cp -rf "$SOURCE_DIR/deploy/config/nginx"/* "$APP_DIR/config/nginx/" 2>/dev/null || true
        print_success "nginx配置已复制"
    fi

    print_success "配置文件已复制"
fi

# 修复换行符问题
sed -i 's/\r$//' "$APP_DIR/.env.prod" 2>/dev/null || true
sed -i 's/\r$//' "$APP_DIR/docker-compose.yml" 2>/dev/null || true

# 创建.env文件
cp -f "$APP_DIR/.env.prod" "$APP_DIR/.env"
print_success "环境配置文件已准备"

# =============================================================================
# 步骤5: 优化Backend Dockerfile
# =============================================================================
echo ""
print_step "【步骤5/8】准备Backend Dockerfile..."
echo ""

cat > "$APP_DIR/backend/Dockerfile.prod" << 'DOCKERFILE_CONTENT'
FROM python:3.11-slim

WORKDIR /app

# 设置pip使用阿里云镜像源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set install.trusted-host mirrors.aliyun.com

# 安装系统依赖
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list 2>/dev/null || true && \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# 创建非root用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 复制requirements并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# 复制应用代码
COPY . .

# 创建必要目录并设置权限
RUN mkdir -p logs uploads invoices && \
    chown -R appuser:appuser /app

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["gunicorn", "src.main:app", \
     "-w", "4", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
DOCKERFILE_CONTENT

print_success "Backend Dockerfile已创建"

# =============================================================================
# 步骤6: 加载并验证配置
# =============================================================================
echo ""
print_step "【步骤6/8】加载配置文件..."
echo ""

cd "$APP_DIR"

# 加载环境变量
set -a
source .env.prod
set +a

print_success "配置已加载"
echo ""
echo "当前配置:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  数据库: $POSTGRES_DB"
echo "  用户: $POSTGRES_USER"
echo "  环境: ${ENVIRONMENT:-production}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 验证关键配置
echo ""
print_info "验证安全配置..."

CONFIG_WARNINGS=0

check_config_secure() {
    local name=$1
    local value=$2

    if [ -z "$value" ]; then
        print_error "$name 未配置"
        ((CONFIG_WARNINGS++))
    elif [[ "$value" == *"CHANGE"* ]] || [[ "$value" == *"yourdomain"* ]]; then
        print_warning "$name 使用默认值（建议修改）"
        ((CONFIG_WARNINGS++))
    else
        print_success "$name 已配置"
    fi
}

check_config_secure "数据库密码" "$POSTGRES_PASSWORD"
check_config_secure "Redis密码" "$REDIS_PASSWORD"
check_config_secure "加密密钥" "$ENCRYPTION_KEY"
check_config_secure "JWT密钥" "$JWT_SECRET_KEY"

if [ "$CONFIG_WARNINGS" -gt 0 ]; then
    echo ""
    print_warning "发现 $CONFIG_WARNINGS 个配置警告"
    echo ""
    read -p "是否继续部署？生产环境建议先修改配置 (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "已取消部署。请修改 $APP_DIR/.env.prod 后重新运行此脚本。"
        exit 0
    fi
fi

# =============================================================================
# 步骤7: 构建并启动服务
# =============================================================================
echo ""
print_step "【步骤7/8】构建并启动服务..."
echo ""

cd "$APP_DIR"

# 停止旧容器
print_info "停止旧容器..."
docker compose down -v 2>/dev/null || true
print_success "旧容器已停止"

echo ""
print_info "构建应用镜像（首次构建需要5-10分钟）..."
echo ""

# 构建backend
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  构建Backend..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if ! docker compose build backend; then
    echo ""
    print_error "Backend构建失败"
    echo ""
    echo "可能的原因:"
    echo "  1. requirements.txt 中的包无法安装"
    echo "  2. 网络问题"
    echo "  3. 代码存在语法错误"
    echo ""
    echo "请检查错误信息后修复"
    exit 1
fi

print_success "Backend构建完成"

# 启动所有服务
echo ""
print_info "启动所有服务..."
echo ""

if ! docker compose up -d; then
    error_exit "服务启动失败"
fi

print_success "服务启动命令已执行"

# =============================================================================
# 步骤8: 等待并验证服务
# =============================================================================
echo ""
print_step "【步骤8/8】等待服务启动并验证..."
echo ""

print_info "等待服务完全启动（60秒）..."

for i in {60..1}; do
    printf "\r  剩余 %2d 秒..." $i
    sleep 1
done
echo ""

# 显示容器状态
echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                    容器运行状态                                     ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

docker compose ps

# 健康检查
echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                    服务健康检查                                     ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

ALL_HEALTHY=true

# PostgreSQL
echo -n "  [1/3] PostgreSQL数据库: "
if docker exec mr_game_ops_db_prod pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null 2>&1; then
    print_success "正常"
else
    print_error "失败"
    ALL_HEALTHY=false
    echo "        查看日志: docker logs mr_game_ops_db_prod"
fi

# Redis
echo -n "  [2/3] Redis缓存: "
if docker exec mr_game_ops_redis_prod redis-cli -a "$REDIS_PASSWORD" --no-auth-warning ping 2>/dev/null | grep -q PONG; then
    print_success "正常"
else
    print_error "失败"
    ALL_HEALTHY=false
    echo "        查看日志: docker logs mr_game_ops_redis_prod"
fi

# Backend API
sleep 15
echo -n "  [3/3] Backend API: "

HEALTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")

if [ "$HEALTH_CODE" = "200" ]; then
    print_success "正常 (HTTP $HEALTH_CODE)"
elif [ "$HEALTH_CODE" = "000" ]; then
    print_warning "无法连接（可能还在启动中）"
    ALL_HEALTHY=false
    echo ""
    echo "        等待30秒后重试..."
    sleep 30
    HEALTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null || echo "000")
    if [ "$HEALTH_CODE" = "200" ]; then
        echo "        ✓ 现在正常了 (HTTP 200)"
        ALL_HEALTHY=true
    else
        echo "        ✗ 仍然无法访问 (HTTP $HEALTH_CODE)"
        echo "        查看日志: docker logs mr_game_ops_backend_prod --tail=50"
    fi
else
    print_warning "HTTP $HEALTH_CODE"
    ALL_HEALTHY=false
    echo "        查看日志: docker logs mr_game_ops_backend_prod --tail=50"
fi

# =============================================================================
# 部署完成
# =============================================================================
echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                    🎉 部署完成！                                   ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ip.sb 2>/dev/null || echo "无法自动获取")

echo "📋 部署信息摘要"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  服务器IP:      $SERVER_IP"
echo "  应用目录:      $APP_DIR"
echo "  配置文件:      $APP_DIR/.env.prod"
echo ""
echo "🌐 访问地址"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  API健康检查:   http://$SERVER_IP:8000/health"
echo "  API文档:       http://$SERVER_IP:8000/docs"
echo ""

if [ "$ALL_HEALTHY" = true ]; then
    echo "✅ 所有核心服务运行正常！"
else
    echo "⚠️  部分服务存在问题，请查看上述日志"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "脚本执行完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
