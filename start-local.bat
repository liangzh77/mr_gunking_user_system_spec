@echo off
chcp 65001 >nul
REM =============================================================================
REM Windows本地Docker部署启动脚本
REM =============================================================================

echo ========================================
echo   MR游戏运营系统 - 本地Docker部署
echo ========================================
echo.

REM 检查Docker是否运行
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [错误] Docker未运行，请先启动Docker Desktop
    pause
    exit /b 1
)

echo [1/5] 停止并清理旧容器...
docker-compose down 2>nul

echo [2/5] 清理旧镜像（可选）...
docker-compose down --rmi local --volumes --remove-orphans 2>nul

echo [3/5] 构建Docker镜像...
docker-compose build

echo [4/5] 启动所有服务...
docker-compose up -d

echo [5/5] 等待服务启动...
timeout /t 15 >nul

echo.
echo ========================================
echo   部署完成！
echo ========================================
echo.
echo 📊 服务状态:
docker-compose ps
echo.
echo 🌐 访问地址:
echo   - 前端: http://localhost:5173
echo   - 后端API: http://localhost:8000
echo   - API文档: http://localhost:8000/docs
echo   - PgAdmin: http://localhost:5050
echo   - Redis Commander: http://localhost:8081
echo.
echo 📝 管理命令:
echo   - 查看日志: docker-compose logs -f
echo   - 停止服务: docker-compose down
echo   - 重启服务: docker-compose restart
echo.
echo 🔐 默认登录账号:
echo   - 超级管理员: superadmin / Admin123!@#
echo   - 测试管理员: testadmin / Test123!@#
echo.

pause
