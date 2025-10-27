@echo off
chcp 65001 > nul
REM ============================================================================
REM 账户管理工具 - 生产环境
REM 功能: 查看、重置密码、删除账户
REM 作者: 自动生成
REM 日期: 2025-10-28
REM ============================================================================

:MENU
cls
echo.
echo ============================================================================
echo MR游戏运营管理系统 - 账户管理工具
echo ============================================================================
echo.
echo 请选择操作:
echo.
echo [1] 查看所有账户
echo [2] 查看管理员账户详情
echo [3] 查看财务账户详情
echo [4] 查看运营商账户详情
echo [5] 重置账户密码
echo [6] 删除账户
echo [0] 退出
echo.
echo ============================================================================
set /p choice="请输入选项 (0-6): "

if "%choice%"=="1" goto LIST_ALL
if "%choice%"=="2" goto LIST_ADMIN
if "%choice%"=="3" goto LIST_FINANCE
if "%choice%"=="4" goto LIST_OPERATOR
if "%choice%"=="5" goto RESET_PASSWORD
if "%choice%"=="6" goto DELETE_ACCOUNT
if "%choice%"=="0" goto EXIT
echo 无效选项，请重新选择！
timeout /t 2 > nul
goto MENU

REM ============================================================================
REM 查看所有账户
REM ============================================================================
:LIST_ALL
cls
echo.
echo ============================================================================
echo 所有账户列表
echo ============================================================================
echo.

docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops -c "SELECT 'Admin' as account_type, username, full_name as name, email, phone, role, is_active FROM admin_accounts UNION ALL SELECT 'Finance' as account_type, username, full_name as name, email, phone, role, is_active FROM finance_accounts UNION ALL SELECT 'Operator' as account_type, username, full_name as name, email, phone, 'operator' as role, is_active FROM operator_accounts ORDER BY account_type, username;"

echo.
echo ============================================================================
echo 账户统计
echo ============================================================================
echo.

docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops -c "SELECT 'Admin' as type, COUNT(*) as total, COUNT(*) FILTER (WHERE is_active = true) as active FROM admin_accounts UNION ALL SELECT 'Finance' as type, COUNT(*) as total, COUNT(*) FILTER (WHERE is_active = true) as active FROM finance_accounts UNION ALL SELECT 'Operator' as type, COUNT(*) as total, COUNT(*) FILTER (WHERE is_active = true) as active FROM operator_accounts;"

echo.
pause
goto MENU

REM ============================================================================
REM 查看管理员账户详情
REM ============================================================================
:LIST_ADMIN
cls
echo.
echo ============================================================================
echo 管理员账号详情
echo ============================================================================
echo.

docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops -c "SELECT username, full_name, email, phone, role, permissions, is_active FROM admin_accounts ORDER BY username;"

echo.
pause
goto MENU

REM ============================================================================
REM 查看财务账户详情
REM ============================================================================
:LIST_FINANCE
cls
echo.
echo ============================================================================
echo 财务账号详情
echo ============================================================================
echo.

docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops -c "SELECT username, full_name, email, phone, role, permissions, is_active FROM finance_accounts ORDER BY username;"

echo.
pause
goto MENU

REM ============================================================================
REM 查看运营商账户详情
REM ============================================================================
:LIST_OPERATOR
cls
echo.
echo ============================================================================
echo 运营商账号详情
echo ============================================================================
echo.

docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops -c "SELECT username, full_name, email, phone, balance, is_active, created_at FROM operator_accounts ORDER BY created_at DESC;"

echo.
pause
goto MENU

REM ============================================================================
REM 重置账户密码
REM ============================================================================
:RESET_PASSWORD
cls
echo.
echo ============================================================================
echo 重置账户密码
echo ============================================================================
echo.
echo 请选择账户类型:
echo.
echo [1] 管理员账户 (admin_accounts)
echo [2] 财务账户 (finance_accounts)
echo [3] 运营商账户 (operator_accounts)
echo [0] 返回主菜单
echo.
set /p acc_type="请输入选项 (0-3): "

if "%acc_type%"=="0" goto MENU
if "%acc_type%"=="1" set table_name=admin_accounts
if "%acc_type%"=="2" set table_name=finance_accounts
if "%acc_type%"=="3" set table_name=operator_accounts

if not defined table_name (
    echo 无效选项！
    timeout /t 2 > nul
    goto RESET_PASSWORD
)

echo.
set /p username="请输入要重置密码的用户名: "

if "%username%"=="" (
    echo 用户名不能为空！
    timeout /t 2 > nul
    goto RESET_PASSWORD
)

echo.
echo 提示: 默认密码为 Admin@123
echo.
set /p confirm="确认重置用户 [%username%] 的密码吗? (Y/N): "

if /i not "%confirm%"=="Y" (
    echo 操作已取消。
    timeout /t 2 > nul
    goto MENU
)

echo.
echo 正在重置密码...
echo.

REM 使用 superadmin 的密码哈希 (Admin@123)
docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops -c "UPDATE %table_name% SET password_hash = (SELECT password_hash FROM admin_accounts WHERE username = 'superadmin') WHERE username = '%username%';"

if %errorlevel% equ 0 (
    echo.
    echo ============================================================================
    echo 密码重置成功！
    echo ============================================================================
    echo.
    echo 账户: %username%
    echo 新密码: Admin@123
    echo.
) else (
    echo.
    echo 密码重置失败！请检查用户名是否存在。
    echo.
)

pause
goto MENU

REM ============================================================================
REM 删除账户
REM ============================================================================
:DELETE_ACCOUNT
cls
echo.
echo ============================================================================
echo 删除账户 (软删除)
echo ============================================================================
echo.
echo 警告: 此操作将停用账户，不会真正删除数据！
echo.
echo 请选择账户类型:
echo.
echo [1] 管理员账户 (admin_accounts)
echo [2] 财务账户 (finance_accounts)
echo [3] 运营商账户 (operator_accounts - 使用软删除)
echo [0] 返回主菜单
echo.
set /p del_type="请输入选项 (0-3): "

if "%del_type%"=="0" goto MENU
if "%del_type%"=="1" set del_table=admin_accounts
if "%del_type%"=="2" set del_table=finance_accounts
if "%del_type%"=="3" set del_table=operator_accounts

if not defined del_table (
    echo 无效选项！
    timeout /t 2 > nul
    goto DELETE_ACCOUNT
)

echo.
set /p del_username="请输入要删除的用户名: "

if "%del_username%"=="" (
    echo 用户名不能为空！
    timeout /t 2 > nul
    goto DELETE_ACCOUNT
)

echo.
echo 警告: 即将停用账户 [%del_username%]
echo.
set /p del_confirm="确认删除吗? 输入 DELETE 确认: "

if /i not "%del_confirm%"=="DELETE" (
    echo 操作已取消。
    timeout /t 2 > nul
    goto MENU
)

echo.
echo 正在删除账户...
echo.

REM 对运营商使用软删除，其他账户设置为 inactive
if "%del_table%"=="operator_accounts" (
    docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops -c "UPDATE %del_table% SET deleted_at = CURRENT_TIMESTAMP, is_active = false WHERE username = '%del_username%';"
) else (
    docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops -c "UPDATE %del_table% SET is_active = false WHERE username = '%del_username%';"
)

if %errorlevel% equ 0 (
    echo.
    echo ============================================================================
    echo 账户删除成功！
    echo ============================================================================
    echo.
    echo 账户: %del_username%
    echo 状态: 已停用
    echo.
) else (
    echo.
    echo 账户删除失败！请检查用户名是否存在。
    echo.
)

pause
goto MENU

REM ============================================================================
REM 退出
REM ============================================================================
:EXIT
cls
echo.
echo ============================================================================
echo 感谢使用 MR游戏运营管理系统 - 账户管理工具
echo ============================================================================
echo.
exit /b 0
