@echo off
echo ==========================================
echo 测试端口改动影响
echo 前端: 80端口, 后端: 8001端口
echo ==========================================

echo.
echo 1. 启动后端服务在8001端口...
cd /d "%~dp0backend"
start "Backend Server" cmd /k "python -m uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload --env-file .env.development"

echo.
echo 2. 等待后端启动...
timeout /t 5 /nobreak > nul

echo.
echo 3. 测试后端API...
curl -X POST "http://localhost:8001/api/v1/admin/login" -H "Content-Type: application/json" -d "{\"username\": \"superadmin\", \"password\": \"admin123456\"}"

echo.
echo 4. 启动前端服务在80端口...
cd /d "%~dp0frontend"
echo 注意: 80端口可能需要管理员权限，如果失败会自动切换到8080端口
start "Frontend Server" cmd /k "npm run dev"

echo.
echo 5. 等待前端启动...
timeout /t 10 /nobreak > nul

echo.
echo ==========================================
echo 测试完成！
echo 前端地址: http://localhost:80 (或 http://localhost:8080)
echo 后端地址: http://localhost:8001
echo ==========================================
echo.
echo 请尝试登录:
echo 用户名: superadmin
echo 密码: admin123456
echo.
pause