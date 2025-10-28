@echo off
REM MR 游戏运营管理系统 - 开发环境启动脚本
REM 使用方法: 在项目根目录或 backend 目录下运行此脚本

echo ========================================
echo MR 游戏运营管理系统 - 开发服务器启动
echo ========================================
echo.

REM 检查是否在 backend 目录
if exist "src\main.py" (
    echo [√] 当前在 backend 目录
    set "BACKEND_DIR=%CD%"
) else if exist "backend\src\main.py" (
    echo [√] 当前在项目根目录，切换到 backend
    cd backend
    set "BACKEND_DIR=%CD%"
) else (
    echo [×] 错误: 找不到 backend/src/main.py
    echo 请在项目根目录或 backend 目录下运行此脚本
    pause
    exit /b 1
)

echo [√] 后端目录: %BACKEND_DIR%
echo.

REM 检查虚拟环境
if exist ".venv312\Scripts\activate.bat" (
    echo [√] 使用虚拟环境: .venv312
    call .venv312\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo [√] 使用虚拟环境: .venv
    call .venv\Scripts\activate.bat
) else (
    echo [!] 警告: 未找到虚拟环境，使用系统 Python
)

echo.
echo [√] 检查依赖...
python -c "import uvicorn" 2>nul
if errorlevel 1 (
    echo [×] 错误: uvicorn 未安装
    echo 请运行: pip install -r requirements.txt
    pause
    exit /b 1
)

echo [√] 依赖检查通过
echo.
echo ========================================
echo 正在启动开发服务器...
echo ========================================
echo.
echo 服务地址:
echo   - API 文档: http://localhost:8000/api/docs
echo   - ReDoc:    http://localhost:8000/api/redoc
echo   - 健康检查: http://localhost:8000/health
echo.
echo 按 Ctrl+C 停止服务器
echo ========================================
echo.

REM 启动 uvicorn
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

REM 如果启动失败
if errorlevel 1 (
    echo.
    echo [×] 服务器启动失败
    echo.
    echo 故障排查:
    echo 1. 检查数据库是否运行: docker-compose up -d postgres
    echo 2. 检查 Redis 是否运行: docker-compose up -d redis
    echo 3. 检查环境变量: 复制 .env.example 到 .env
    echo 4. 检查端口占用: netstat -ano ^| findstr :8000
    echo.
    pause
    exit /b 1
)
