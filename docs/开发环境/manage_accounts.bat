@echo off
REM =============================================================================
REM MR游戏运营管理系统 - 开发环境账户管理工具
REM =============================================================================
REM Usage:
REM   manage_accounts.bat              - Show interactive menu
REM   manage_accounts.bat list         - List all accounts
REM   manage_accounts.bat help         - Show help message
REM =============================================================================

chcp 65001 >nul
setlocal EnableDelayedExpansion

SET BACKEND_CONTAINER=mr_game_ops_backend
SET SCRIPT_DIR=%~dp0scripts

REM Check if container is running
docker ps --format "{{.Names}}" | findstr /C:"%BACKEND_CONTAINER%" >nul 2>&1
if errorlevel 1 (
    echo [Error] Backend container is not running
    echo Please start services: docker-compose up -d
    exit /b 1
)

REM Execute command if provided
if not "%1"=="" (
    if "%1"=="list" goto cmd_list
    if "%1"=="help" goto cmd_help
    echo Unknown command: %1
    goto cmd_help
)

REM Interactive menu
:menu
cls
echo =========================================
echo    MR Account Management Tool
echo =========================================
echo.
echo 1. List all accounts
echo 2. Create admin account
echo 3. Create operator account
echo 4. Create finance account
echo 5. Delete account
echo 6. Reset password
echo 7. Enable/Disable account
echo 8. Change admin role
echo 9. Batch create operators
echo 0. Exit
echo.
echo =========================================
set /p choice="Please select [0-9]: "

if "%choice%"=="1" goto menu_list
if "%choice%"=="2" goto menu_create_admin
if "%choice%"=="3" goto menu_create_operator
if "%choice%"=="4" goto menu_create_finance
if "%choice%"=="5" goto menu_delete
if "%choice%"=="6" goto menu_reset_password
if "%choice%"=="7" goto menu_toggle_active
if "%choice%"=="8" goto menu_change_role
if "%choice%"=="9" goto menu_batch_create
if "%choice%"=="0" goto exit_program

echo [Error] Invalid choice!
pause
goto menu

REM ===== Command handlers =====
:cmd_list
echo.
type "%SCRIPT_DIR%\list_accounts.py" | docker exec -i %BACKEND_CONTAINER% python3
echo.
goto end

:cmd_help
echo.
echo Usage: manage_accounts.bat [command]
echo.
echo Commands:
echo   list      - List all accounts
echo   help      - Show this help message
echo.
goto end

REM ===== Menu handlers =====
:menu_list
echo.
type "%SCRIPT_DIR%\list_accounts.py" | docker exec -i %BACKEND_CONTAINER% python3
echo.
pause
goto menu

:menu_create_admin
echo.
echo === Create Admin Account ===
echo.
set /p username="Username: "
set /p password="Password: "
set /p full_name="Full Name: "
set /p email="Email: "
set /p phone="Phone: "
echo.
echo Role:
echo   1. super_admin
echo   2. admin
set /p role_choice="Select [1/2]: "
if "%role_choice%"=="1" (
    set role=super_admin
) else (
    set role=admin
)
echo.
echo Creating admin account...
type "%SCRIPT_DIR%\create_admin_env.py" | docker exec -i -e ACCOUNT_USERNAME=%username% -e ACCOUNT_PASSWORD=%password% -e ACCOUNT_FULLNAME=%full_name% -e ACCOUNT_EMAIL=%email% -e ACCOUNT_PHONE=%phone% -e ACCOUNT_ROLE=%role% %BACKEND_CONTAINER% python3 2>&1
echo.
pause
goto menu

:menu_create_operator
echo.
echo === Create Operator Account ===
echo.
set /p username="Username: "
set /p password="Password: "
set /p full_name="Full Name: "
set /p email="Email: "
set /p phone="Phone: "
set /p balance="Initial Balance [1000]: "
if "%balance%"=="" set balance=1000
echo.
echo Creating operator account...
type "%SCRIPT_DIR%\create_operator_env.py" | docker exec -i -e ACCOUNT_USERNAME=%username% -e ACCOUNT_PASSWORD=%password% -e ACCOUNT_FULLNAME=%full_name% -e ACCOUNT_EMAIL=%email% -e ACCOUNT_PHONE=%phone% -e ACCOUNT_BALANCE=%balance% %BACKEND_CONTAINER% python3 2>&1
echo.
pause
goto menu

:menu_create_finance
echo.
echo === Create Finance Account ===
echo.
set /p username="Username: "
set /p password="Password: "
set /p full_name="Full Name: "
set /p email="Email: "
set /p phone="Phone: "
echo.
echo Role:
echo   1. specialist
echo   2. manager
echo   3. auditor
set /p role_choice="Select [1/2/3]: "
if "%role_choice%"=="1" (
    set role=specialist
) else if "%role_choice%"=="2" (
    set role=manager
) else (
    set role=auditor
)
echo.
echo Creating finance account...
type "%SCRIPT_DIR%\create_finance_env.py" | docker exec -i -e ACCOUNT_USERNAME=%username% -e ACCOUNT_PASSWORD=%password% -e ACCOUNT_FULLNAME=%full_name% -e ACCOUNT_EMAIL=%email% -e ACCOUNT_PHONE=%phone% -e ACCOUNT_ROLE=%role% %BACKEND_CONTAINER% python3 2>&1
echo.
pause
goto menu

:menu_delete
echo.
echo === Delete Account ===
echo [Warning] This operation cannot be undone!
echo.
echo Account Type:
echo   1. Admin
echo   2. Operator
echo   3. Finance
set /p type_choice="Select [1/2/3]: "
if "%type_choice%"=="1" (
    set account_type=admin
    set type_name=Admin
) else if "%type_choice%"=="2" (
    set account_type=operator
    set type_name=Operator
) else (
    set account_type=finance
    set type_name=Finance
)
set /p username="Username: "
echo.
set /p confirm="Confirm delete %type_name% account '%username%'? [y/N]: "
if /i not "%confirm%"=="y" (
    echo [Cancelled]
    pause
    goto menu
)
echo.
echo Deleting account...
type "%SCRIPT_DIR%\delete_account_env.py" | docker exec -i -e ACCOUNT_TYPE=%account_type% -e ACCOUNT_USERNAME=%username% %BACKEND_CONTAINER% python3 2>&1
echo.
pause
goto menu

:menu_reset_password
echo.
echo === Reset Password ===
echo.
echo Account Type:
echo   1. Admin
echo   2. Operator
echo   3. Finance
set /p type_choice="Select [1/2/3]: "
if "%type_choice%"=="1" (
    set account_type=admin
) else if "%type_choice%"=="2" (
    set account_type=operator
) else (
    set account_type=finance
)
set /p username="Username: "
set /p new_password="New Password: "
echo.
echo Resetting password...
type "%SCRIPT_DIR%\reset_password_env.py" | docker exec -i -e ACCOUNT_TYPE=%account_type% -e ACCOUNT_USERNAME=%username% -e ACCOUNT_PASSWORD=%new_password% %BACKEND_CONTAINER% python3 2>&1
echo.
pause
goto menu

:menu_toggle_active
echo.
echo === Enable/Disable Account ===
echo.
echo Account Type:
echo   1. Admin
echo   2. Operator
echo   3. Finance
set /p type_choice="Select [1/2/3]: "
if "%type_choice%"=="1" (
    set account_type=admin
) else if "%type_choice%"=="2" (
    set account_type=operator
) else (
    set account_type=finance
)
set /p username="Username: "
echo.
echo Action:
echo   1. Enable
echo   2. Disable
set /p action="Select [1/2]: "
if "%action%"=="1" (
    set is_active=true
) else (
    set is_active=false
)
echo.
echo Updating account status...
type "%SCRIPT_DIR%\toggle_active_env.py" | docker exec -i -e ACCOUNT_TYPE=%account_type% -e ACCOUNT_USERNAME=%username% -e ACCOUNT_ACTIVE=%is_active% %BACKEND_CONTAINER% python3 2>&1
echo.
pause
goto menu

:menu_change_role
echo.
echo === Change Admin Role ===
echo.
set /p username="Username: "
echo.
echo New Role:
echo   1. super_admin
echo   2. admin
set /p role_choice="Select [1/2]: "
if "%role_choice%"=="1" (
    set new_role=super_admin
) else (
    set new_role=admin
)
echo.
echo Changing admin role...
type "%SCRIPT_DIR%\change_admin_role_env.py" | docker exec -i -e ACCOUNT_USERNAME=%username% -e ACCOUNT_ROLE=%new_role% %BACKEND_CONTAINER% python3 2>&1
echo.
pause
goto menu

:menu_batch_create
echo.
echo === Batch Create Operators ===
echo.
echo CSV file format:
echo username,password,full_name,email,phone,initial_balance
echo.
set /p csv_file="CSV file path: "
if not exist "%csv_file%" (
    echo [Error] File not found: %csv_file%
    pause
    goto menu
)
echo.
echo Copying CSV to container...
docker cp "%csv_file%" %BACKEND_CONTAINER%:/tmp/operators_batch.csv 2>&1
echo Batch creating operators...
type "%SCRIPT_DIR%\batch_create_operators.py" | docker exec -i %BACKEND_CONTAINER% python3 2>&1
docker exec %BACKEND_CONTAINER% rm /tmp/operators_batch.csv 2>&1
echo.
pause
goto menu

:exit_program
echo.
echo Goodbye!
goto end

:end
endlocal
