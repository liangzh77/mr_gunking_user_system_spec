#!/bin/bash

# =============================================================================
# 服务器端 - 导入Docker镜像并自动部署
# =============================================================================
# 使用方法:
#   1. 确保已上传镜像文件到 /root/docker-images/
#   2. 执行: bash server-导入并部署.sh
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_step() { echo -e "${BLUE}==>${NC} $1"; }
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
print_info() { echo -e "${CYAN}ℹ${NC} $1"; }

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║     MR游戏运营管理系统 - 导入镜像并部署                            ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# 步骤1: 检查镜像文件
# ============================================================================
print_step "【步骤1/6】检查镜像文件..."

IMAGES_DIR="/root/docker-images"

if [ ! -d "$IMAGES_DIR" ]; then
    print_error "镜像目录不存在: $IMAGES_DIR"
    echo ""
    echo "请先上传镜像文件到服务器："
    echo "  scp C:\\docker-images\\*.tar root@服务器IP:/root/docker-images/"
    echo ""
    exit 1
fi

cd "$IMAGES_DIR"

TAR_COUNT=$(ls -1 *.tar 2>/dev/null | wc -l)

if [ "$TAR_COUNT" -eq 0 ]; then
    print_error "未找到任何 .tar 镜像文件"
    echo ""
    echo "请先上传镜像文件到: $IMAGES_DIR"
    exit 1
fi

print_success "找到 $TAR_COUNT 个镜像文件"
echo ""
echo "镜像文件列表:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ls -lh *.tar | awk '{print "  " $9 " (" $5 ")"}'
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ============================================================================
# 步骤2: 导入镜像
# ============================================================================
print_step "【步骤2/6】导入Docker镜像到本地仓库..."
echo ""

# 定义镜像映射（文件名 -> 镜像描述）
declare -A IMAGE_MAP=(
    ["python-3.11-slim.tar"]="Python 3.11 (后端运行环境)"
    ["postgres-14-alpine.tar"]="PostgreSQL 14 (数据库)"
    ["redis-7-alpine.tar"]="Redis 7 (缓存)"
    ["node-18-alpine.tar"]="Node 18 (前端构建环境)"
    ["nginx-alpine.tar"]="Nginx (Web服务器)"
    ["prometheus-latest.tar"]="Prometheus (监控)"
    ["grafana-latest.tar"]="Grafana (可视化)"
)

IMPORTED=0
FAILED=0

for tar_file in *.tar; do
    description="${IMAGE_MAP[$tar_file]:-未知镜像}"

    echo "  导入: $tar_file"
    echo "        $description"

    if docker load -i "$tar_file" > /dev/null 2>&1; then
        print_success "成功"
        ((IMPORTED++))
    else
        print_error "失败"
        ((FAILED++))
    fi
    echo ""
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  导入成功: $IMPORTED 个"
if [ "$FAILED" -gt 0 ]; then
    echo "  导入失败: $FAILED 个"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ "$IMPORTED" -eq 0 ]; then
    print_error "没有成功导入任何镜像，无法继续部署"
    exit 1
fi

print_success "镜像导入完成"

# 显示已导入的镜像
echo ""
echo "已导入的镜像:"
docker images | grep -E "python|postgres|redis|node|nginx|prometheus|grafana" | head -20

# ============================================================================
# 步骤3: 准备应用目录和配置
# ============================================================================
echo ""
print_step "【步骤3/6】准备应用配置..."

cd /opt/mr-game-ops

# 检查必需文件
if [ ! -f .env.prod ]; then
    print_error ".env.prod 配置文件不存在"
    echo "请确保已上传完整的应用文件到 /opt/mr-game-ops"
    exit 1
fi

# 修复Windows换行符
sed -i 's/\r$//' .env.prod 2>/dev/null || true
sed -i 's/\r$//' docker-compose.prod.yml 2>/dev/null || true

# 创建.env文件
if [ ! -f .env ]; then
    cp .env.prod .env
fi

# 加载环境变量
set -a
source .env
set +a

print_success "配置文件已加载"
echo "  数据库名: $POSTGRES_DB"
echo "  数据库用户: $POSTGRES_USER"

# 验证关键配置
echo ""
echo "验证关键配置..."

check_config() {
    local key=$1
    local value=$2
    local name=$3

    if [ -z "$value" ]; then
        print_error "$name 未配置"
        return 1
    elif [[ "$value" == *"CHANGE_ME"* ]]; then
        print_warning "$name 使用默认值（不安全）"
        return 0
    else
        print_success "$name 已配置"
        return 0
    fi
}

CONFIG_OK=true

check_config "POSTGRES_PASSWORD" "$POSTGRES_PASSWORD" "数据库密码" || CONFIG_OK=false
check_config "REDIS_PASSWORD" "$REDIS_PASSWORD" "Redis密码" || CONFIG_OK=false
check_config "ENCRYPTION_KEY" "$ENCRYPTION_KEY" "加密密钥" || CONFIG_OK=false
check_config "JWT_SECRET_KEY" "$JWT_SECRET_KEY" "JWT密钥" || CONFIG_OK=false

if [ "$CONFIG_OK" = false ]; then
    echo ""
    print_warning "部分配置缺失，建议修改 .env.prod 后重新部署"
    echo ""
    read -p "是否继续？(y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "已取消部署"
        exit 1
    fi
fi

# ============================================================================
# 步骤4: 修改Backend Dockerfile使用阿里云镜像源
# ============================================================================
echo ""
print_step "【步骤4/6】优化Backend Dockerfile..."

if [ -d backend ]; then
    cd backend

    # 备份原文件
    if [ -f Dockerfile.prod ]; then
        cp Dockerfile.prod Dockerfile.prod.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
    fi

    # 创建优化版Dockerfile
    cat > Dockerfile.prod << 'DOCKERFILE'
# 使用已导入的Python镜像
FROM python:3.11-slim

# 设置pip使用阿里云镜像（加速依赖安装）
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set install.trusted-host mirrors.aliyun.com

WORKDIR /app

# 设置apt使用阿里云镜像
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true && \
    apt-get update && apt-get install -y \
    gcc g++ libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

RUN mkdir -p logs uploads invoices && \
    chown -R appuser:appuser /app

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["gunicorn", "src.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
DOCKERFILE

    cd ..
    print_success "Backend Dockerfile已优化"
else
    print_warning "Backend目录不存在，跳过Dockerfile优化"
fi

# ============================================================================
# 步骤5: 构建并启动服务
# ============================================================================
echo ""
print_step "【步骤5/6】构建并启动服务..."

cd /opt/mr-game-ops

# 清理旧容器
echo "  清理旧容器..."
docker compose -f docker-compose.prod.yml down -v 2>/dev/null || true

# 构建应用
echo "  构建后端应用（需要5-10分钟）..."
echo "  正在安装Python依赖包..."
docker compose -f docker-compose.prod.yml build backend

if [ $? -ne 0 ]; then
    print_error "后端构建失败"
    echo ""
    echo "可能的原因："
    echo "  1. requirements.txt 中的包无法安装"
    echo "  2. 网络问题（即使使用了阿里云镜像）"
    echo "  3. 代码存在语法错误"
    echo ""
    echo "请查看错误信息并修复后重试"
    exit 1
fi

print_success "应用构建完成"

# 启动服务
echo ""
echo "  启动所有服务..."
docker compose -f docker-compose.prod.yml up -d

print_success "服务启动命令已执行"

# ============================================================================
# 步骤6: 等待并验证服务
# ============================================================================
echo ""
print_step "【步骤6/6】等待服务启动并验证..."

echo "  等待服务完全启动（60秒）..."
for i in {60..1}; do
    printf "\r  剩余 %2d 秒..." $i
    sleep 1
done
echo ""

# 查看容器状态
echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                    容器运行状态                                     ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""
docker compose -f docker-compose.prod.yml ps

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

# Backend API（多等几秒让它完全启动）
sleep 10
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
        echo "        ✓ 现在正常了"
    else
        echo "        ✗ 仍然无法访问"
        echo "        查看日志: docker logs mr_game_ops_backend_prod --tail=50"
    fi
else
    print_warning "HTTP $HEALTH_CODE"
    ALL_HEALTHY=false
fi

# ============================================================================
# 部署完成
# ============================================================================
echo ""
echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║                    🎉 部署完成！                                   ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s ip.sb 2>/dev/null || echo "无法获取")

echo "📋 部署信息摘要"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  服务器IP:      $SERVER_IP"
echo "  应用目录:      /opt/mr-game-ops"
echo "  配置文件:      /opt/mr-game-ops/.env"
echo ""
echo "🌐 访问地址"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  API健康检查:   http://$SERVER_IP:8000/health"
echo "  API文档:       http://$SERVER_IP:8000/docs"
echo ""
echo "🔧 常用管理命令"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  查看服务状态:  docker compose -f /opt/mr-game-ops/docker-compose.prod.yml ps"
echo "  查看所有日志:  docker compose -f /opt/mr-game-ops/docker-compose.prod.yml logs -f"
echo "  查看后端日志:  docker logs mr_game_ops_backend_prod -f"
echo "  重启所有服务:  docker compose -f /opt/mr-game-ops/docker-compose.prod.yml restart"
echo "  停止所有服务:  docker compose -f /opt/mr-game-ops/docker-compose.prod.yml down"
echo "  进入后端容器:  docker exec -it mr_game_ops_backend_prod bash"
echo ""
echo "📝 下一步操作"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  1. 测试API访问:"
echo "     curl http://localhost:8000/health"
echo ""
echo "  2. 初始化数据库:"
echo "     docker exec -it mr_game_ops_backend_prod bash"
echo "     cd /app"
echo "     python init_database.py  # 如果有此脚本"
echo "     exit"
echo ""
echo "  3. 创建管理员账户:"
echo "     docker exec -it mr_game_ops_backend_prod bash"
echo "     cd /app"
echo "     python create_admin_simple_v2.py  # 如果有此脚本"
echo "     exit"
echo ""

if [ "$ALL_HEALTHY" = true ]; then
    echo "✅ 所有核心服务运行正常！"
else
    echo "⚠️  部分服务存在问题，请查看上述日志"
    echo ""
    echo "常见问题排查："
    echo "  - Backend无法启动: 检查 requirements.txt 中的依赖是否都能安装"
    echo "  - 数据库连接失败: 检查 .env 中的数据库密码配置"
    echo "  - Redis连接失败: 检查 .env 中的Redis密码配置"
fi

echo ""
echo "🆘 如需帮助，查看完整日志："
echo "  docker compose -f /opt/mr-game-ops/docker-compose.prod.yml logs"
echo ""
