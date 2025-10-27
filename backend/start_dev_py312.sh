#!/bin/bash
# MR 游戏运营管理系统 - 开发环境启动脚本 (Python 3.12版本)
# 使用方法: ./start_dev_py312.sh

echo "========================================"
echo "MR 游戏运营管理系统 - 开发服务器启动 (Python 3.12)"
echo "========================================"
echo ""

# 检查是否在 backend 目录
if [ -f "src/main.py" ]; then
    echo "[√] 当前在 backend 目录"
    BACKEND_DIR=$(pwd)
elif [ -f "backend/src/main.py" ]; then
    echo "[√] 当前在项目根目录，切换到 backend"
    cd backend
    BACKEND_DIR=$(pwd)
else
    echo "[×] 错误: 找不到 backend/src/main.py"
    echo "请在项目根目录或 backend 目录下运行此脚本"
    exit 1
fi

echo "[√] 后端目录: $BACKEND_DIR"
echo ""

# 检查Python 3.12虚拟环境
if [ -d "venv_py312" ]; then
    echo "[√] 使用Python 3.12虚拟环境: venv_py312"
    source venv_py312/Scripts/activate
else
    echo "[×] 错误: 未找到Python 3.12虚拟环境 venv_py312"
    echo "请先创建Python 3.12虚拟环境"
    exit 1
fi

echo ""
echo "[√] 检查Python版本..."
PYTHON_VERSION=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "[√] Python版本: $PYTHON_VERSION"

if [[ "$PYTHON_VERSION" != "3.12" ]]; then
    echo "[×] 错误: 需要Python 3.12，当前版本: $PYTHON_VERSION"
    exit 1
fi

echo ""
echo "[√] 检查依赖..."
python -c "import uvicorn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[×] 错误: uvicorn 未安装"
    echo "请运行: pip install -r requirements.txt"
    exit 1
fi

echo "[√] 依赖检查通过"
echo ""
echo "========================================"
echo "正在启动开发服务器..."
echo "========================================"
echo ""
echo "服务地址:"
echo "  - API 文档: http://localhost:8000/api/docs"
echo "  - ReDoc:    http://localhost:8000/api/redoc"
echo "  - 健康检查: http://localhost:8000/health"
echo ""
echo "按 Ctrl+C 停止服务器"
echo "========================================"
echo ""

# 启动 uvicorn
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 如果启动失败
if [ $? -ne 0 ]; then
    echo ""
    echo "[×] 服务器启动失败"
    echo ""
    echo "故障排查:"
    echo "1. 检查数据库是否运行: docker-compose up -d postgres"
    echo "2. 检查 Redis 是否运行: docker-compose up -d redis"
    echo "3. 检查环境变量: 复制 .env.example 到 .env"
    echo "4. 检查端口占用: lsof -i :8000"
    echo ""
    exit 1
fi