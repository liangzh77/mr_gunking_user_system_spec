@echo off
REM ============================================================================
REM 列出所有测试账户信息
REM 作者: 自动生成
REM 日期: 2025-10-28
REM ============================================================================

echo.
echo ============================================================================
echo MR游戏运营管理系统 - 账户信息查询
echo ============================================================================
echo.

REM 检查Docker是否运行
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] Docker未运行或未安装
    echo 请先启动Docker Desktop
    pause
    exit /b 1
)

REM 检查数据库容器是否运行
docker ps --filter "name=mr_game_ops_db" --format "{{.Names}}" | findstr "mr_game_ops_db" >nul
if %errorlevel% neq 0 (
    echo [错误] 数据库容器未运行
    echo 请先运行: docker-compose up -d
    pause
    exit /b 1
)

echo [提示] 正在连接数据库...
echo.

REM 设置SQL查询
set "SQL_QUERY=-- 管理员账号 SELECT 'Admin' as account_type, username, full_name as name, email, phone, role, is_active FROM admin_accounts UNION ALL SELECT 'Finance' as account_type, username, full_name as name, email, phone, role, is_active FROM finance_accounts UNION ALL SELECT 'Operator' as account_type, username, company_name as name, email, phone, 'operator' as role, is_active FROM operator_accounts ORDER BY account_type, username;"

REM 执行查询
echo ============================================================================
echo 所有账户列表
echo ============================================================================
echo.

docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops -c "SELECT 'Admin' as account_type, username, full_name as name, email, phone, role, is_active FROM admin_accounts UNION ALL SELECT 'Finance' as account_type, username, full_name as name, email, phone, role, is_active FROM finance_accounts UNION ALL SELECT 'Operator' as account_type, username, company_name as name, email, phone, 'operator' as role, is_active FROM operator_accounts ORDER BY account_type, username;"

echo.
echo ============================================================================
echo 管理员账号详情
echo ============================================================================
echo.

docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops -c "SELECT username, full_name, email, phone, role, permissions, is_active FROM admin_accounts ORDER BY username;"

echo.
echo ============================================================================
echo 财务账号详情
echo ============================================================================
echo.

docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops -c "SELECT username, full_name, email, phone, role, permissions, is_active FROM finance_accounts ORDER BY username;"

echo.
echo ============================================================================
echo 运营商账号详情
echo ============================================================================
echo.

docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops -c "SELECT username, company_name, email, phone, balance, total_recharge, is_active, created_at FROM operator_accounts ORDER BY created_at DESC;"

echo.
echo ============================================================================
echo 账户统计
echo ============================================================================
echo.

docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops -c "SELECT '管理员账号' as type, COUNT(*) as total, COUNT(*) FILTER (WHERE is_active = true) as active FROM admin_accounts UNION ALL SELECT '财务账号' as type, COUNT(*) as total, COUNT(*) FILTER (WHERE is_active = true) as active FROM finance_accounts UNION ALL SELECT '运营商账号' as type, COUNT(*) as total, COUNT(*) FILTER (WHERE is_active = true) as active FROM operator_accounts;"

echo.
echo ============================================================================
echo 查询完成！
echo ============================================================================
echo.
echo [提示] 所有账号密码请参考: backend\docs\ACCOUNTS_生产环境.md
echo.

pause
