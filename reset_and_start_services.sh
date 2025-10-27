#!/bin/bash

# =============================================================================
# MR游戏运营管理系统 - 服务清理重启脚本
# =============================================================================
# 停止所有相关服务，确保端口完全释放，然后重新启动
# =============================================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 配置变量
PROJECT_DIR="/opt/mr_gunking_user_system_spec"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
LOGS_DIR="$PROJECT_DIR/logs"
BACKEND_PORT=8001
FRONTEND_PORT=3000

log_info "开始服务清理重启流程..."
echo "项目目录: $PROJECT_DIR"
echo "后端目录: $BACKEND_DIR"
echo "前端目录: $FRONTEND_DIR"

# =============================================================================
# 1. 强制停止所有相关服务
# =============================================================================

log_info "步骤1: 强制停止所有相关服务..."

# 停止systemd服务
log_info "停止systemd服务..."
systemctl stop mr-game-ops-backend 2>/dev/null || log_warning "systemd后端服务未运行或停止失败"
systemctl stop mr-game-ops-frontend 2>/dev/null || log_warning "systemd前端服务未运行或停止失败"

# 停止nohup启动的服务
log_info "停止nohup启动的服务..."
pkill -f "uvicorn.*main:app" 2>/dev/null || log_warning "未找到uvicorn进程"
pkill -f "serve.*-s dist" 2>/dev/null || log_warning "未找到serve进程"
pkill -f "python.*main.py" 2>/dev/null || log_warning "未找到Python主进程"

# 强制杀死占用8001端口(原8000)的进程
log_info "强制杀死占用8001端口的进程..."
PID_8000=$(lsof -ti:$BACKEND_PORT 2>/dev/null || true)
if [ ! -z "$PID_8000" ]; then
    log_warning "发现占用端口$BACKEND_PORT的进程: $PID_8000"
    kill -9 $PID_8000 2>/dev/null || log_warning "无法强制杀死进程 $PID_8000"
    sleep 2
    # 再次检查
    PID_8000_AFTER=$(lsof -ti:$BACKEND_PORT 2>/dev/null || true)
    if [ ! -z "$PID_8000_AFTER" ]; then
        log_error "进程 $PID_8000_AFTER 仍然占用端口 $BACKEND_PORT"
        kill -9 $PID_8000_AFTER 2>/dev/null || true
    fi
else
    log_success "端口 $BACKEND_PORT 当前未被占用"
fi

# 强制杀死占用3000端口的进程
log_info "强制杀死占用3000端口的进程..."
PID_3000=$(lsof -ti:$FRONTEND_PORT 2>/dev/null || true)
if [ ! -z "$PID_3000" ]; then
    log_warning "发现占用端口$FRONTEND_PORT的进程: $PID_3000"
    kill -9 $PID_3000 2>/dev/null || log_warning "无法强制杀死进程 $PID_3000"
    sleep 2
else
    log_success "端口 $FRONTEND_PORT 当前未被占用"
fi

# 等待端口完全释放
log_info "等待端口完全释放..."
sleep 5

# =============================================================================
# 2. 清理PID文件和临时文件
# =============================================================================

log_info "步骤2: 清理PID文件和临时文件..."

# 清理PID文件
rm -f "$BACKEND_DIR/logs/backend.pid" 2>/dev/null || true
rm -f "$FRONTEND_DIR/logs/frontend.pid" 2>/dev/null || true
rm -f "$BACKEND_DIR/logs/nohup.out" 2>/dev/null || true
rm -f "$FRONTEND_DIR/logs/nohup.out" 2>/dev/null || true

# 清理可能的Python缓存
find "$BACKEND_DIR" -name "*.pyc" -delete 2>/dev/null || true
find "$BACKEND_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# =============================================================================
# 3. 验证端口已完全释放
# =============================================================================

log_info "步骤3: 验证端口已完全释放..."

# 检查8001端口(原8000)
if lsof -ti:$BACKEND_PORT >/dev/null 2>&1; then
    log_error "端口 $BACKEND_PORT 仍被占用！"
    lsof -ti:$BACKEND_PORT | xargs ps -p
    log_error "请手动检查并杀死这些进程"
    exit 1
else
    log_success "端口 $BACKEND_PORT 已完全释放"
fi

# 检查3000端口
if lsof -ti:$FRONTEND_PORT >/dev/null 2>&1; then
    log_error "端口 $FRONTEND_PORT 仍被占用！"
    lsof -ti:$FRONTEND_PORT | xargs ps -p
    log_error "请手动检查并杀死这些进程"
    exit 1
else
    log_success "端口 $FRONTEND_PORT 已完全释放"
fi

# =============================================================================
# 4. 重新启动服务
# =============================================================================

log_info "步骤4: 重新启动服务..."

# 确保日志目录存在
mkdir -p "$LOGS_DIR"
mkdir -p "$BACKEND_DIR/logs"
mkdir -p "$FRONTEND_DIR/logs"

# 启动后端服务
cd "$BACKEND_DIR"

# 检查虚拟环境（支持Windows和Linux路径）
VENV_ACTIVATED=false
if [ -f "venv_py312/Scripts/activate" ]; then
    log_info "激活Python 3.12虚拟环境(Windows路径)..."
    source venv_py312/Scripts/activate
    VENV_ACTIVATED=true
elif [ -f "venv/bin/activate" ]; then
    log_info "激活Python虚拟环境(Linux路径)..."
    source venv/bin/activate
    VENV_ACTIVATED=true
else
    log_error "未找到Python虚拟环境"
    log_info "期望路径: venv_py312/Scripts/activate 或 venv/bin/activate"
    exit 1
fi

# 验证Python版本
PYTHON_VERSION=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
log_info "Python版本: $PYTHON_VERSION"

# 配置环境变量
cat > .env.production << EOF
# 生产环境配置
DATABASE_URL=postgresql+asyncpg://mr_admin:mr_secure_password_2024@localhost:5432/mr_game_ops
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=$BACKEND_PORT
CORS_ORIGINS=http://localhost:$FRONTEND_PORT,https://https://mrgun.chu-jiao.com
EOF

log_info "启动后端服务..."
nohup uvicorn src.main:app --host 0.0.0.0 --port $BACKEND_PORT --env-file .env.production > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > logs/backend.pid
log_success "后端服务已启动 (PID: $BACKEND_PID)"

# 启动前端服务
cd "$FRONTEND_DIR"
if [ -f "dist/index.html" ]; then
    log_info "前端已构建，启动前端服务..."

    # 配置前端环境变量
    cat > .env.production << EOF
VITE_BACKEND_URL=http://localhost:$BACKEND_PORT
VITE_API_BASE_URL=http://localhost:$BACKEND_PORT/api/v1
EOF

    nohup serve -s dist -l $FRONTEND_PORT > logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > logs/frontend.pid
    log_success "前端服务已启动 (PID: $FRONTEND_PID)"
else
    log_warning "前端未构建，跳过前端服务启动"
fi

# =============================================================================
# 5. 验证服务启动状态
# =============================================================================

log_info "步骤5: 验证服务启动状态..."

# 等待服务启动
log_info "等待服务启动..."
sleep 10

# 检查后端服务
MAX_RETRIES=12
RETRY_COUNT=0
BACKEND_RUNNING=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s "http://localhost:$BACKEND_PORT/health" > /dev/null; then
        log_success "后端服务验证通过"
        BACKEND_RUNNING=true
        break
    else
        log_info "等待后端服务启动... ($((RETRY_COUNT + 1))/$MAX_RETRIES)"
        sleep 5
        RETRY_COUNT=$((RETRY_COUNT + 1))
    fi
done

if [ "$BACKEND_RUNNING" = false ]; then
    log_error "后端服务启动失败，请检查日志: $BACKEND_DIR/logs/backend.log"
    log_error "最近日志内容："
    tail -20 "$BACKEND_DIR/logs/backend.log" 2>/dev/null || echo "无法读取日志文件"
    exit 1
fi

# 检查前端服务
if [ -f "$FRONTEND_DIR/logs/frontend.pid" ]; then
    FRONTEND_PID=$(cat "$FRONTEND_DIR/logs/frontend.pid")
    if ps -p $FRONTEND_PID > /dev/null; then
        log_success "前端服务运行正常 (PID: $FRONTEND_PID)"
    else
        log_warning "前端服务可能未正常启动"
    fi
fi

# =============================================================================
# 6. 完成
# =============================================================================

log_success "🎉 服务清理重启完成！"

echo ""
echo "=========================================="
echo "服务状态总结："
echo "=========================================="
echo "后端服务: http://localhost:$BACKEND_PORT (原8000改为8001)"
echo "前端服务: http://localhost:$FRONTEND_PORT"
echo ""
echo "进程信息："
echo "后端PID: $(cat $BACKEND_DIR/logs/backend.pid 2>/dev/null || echo '未知')"
echo "前端PID: $(cat $FRONTEND_DIR/logs/frontend.pid 2>/dev/null || echo '未知')"
echo ""
echo "服务管理："
echo "查看后端日志: tail -f $BACKEND_DIR/logs/backend.log"
echo "查看前端日志: tail -f $FRONTEND_DIR/logs/frontend.log"
echo "停止后端服务: kill \$(cat $BACKEND_DIR/logs/backend.pid)"
echo "停止前端服务: kill \$(cat $FRONTEND_DIR/logs/frontend.pid)"
echo "=========================================="

log_success "服务清理重启脚本执行完成！"