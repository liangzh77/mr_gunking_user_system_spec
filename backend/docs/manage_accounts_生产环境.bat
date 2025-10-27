@echo off
chcp 65001 > nul
REM ============================================================================
REM Account Management Tool - Production Environment
REM Features: View, Reset Password, Delete Accounts
REM Author: Auto-generated
REM Date: 2025-10-28
REM ============================================================================

:MENU
cls
echo.
echo ============================================================================
echo MR Game Ops System - Account Management Tool
echo ============================================================================
echo.
echo Please select an operation:
echo.
echo [1] View All Accounts
echo [2] View Admin Accounts Details
echo [3] View Finance Accounts Details
echo [4] View Operator Accounts Details
echo [5] Reset Account Password
echo [6] Delete Account
echo [0] Exit
echo.
echo ============================================================================
set /p choice="Enter option (0-6): "

if "%choice%"=="1" goto LIST_ALL
if "%choice%"=="2" goto LIST_ADMIN
if "%choice%"=="3" goto LIST_FINANCE
if "%choice%"=="4" goto LIST_OPERATOR
if "%choice%"=="5" goto RESET_PASSWORD
if "%choice%"=="6" goto DELETE_ACCOUNT
if "%choice%"=="0" goto EXIT
echo Invalid option, please try again!
timeout /t 2 > nul
goto MENU

REM ============================================================================
REM View All Accounts
REM ============================================================================
:LIST_ALL
cls
echo.
echo ============================================================================
echo All Accounts List
echo ============================================================================
echo.

docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops -c "SELECT 'Admin' as account_type, username, full_name as name, email, phone, role, is_active FROM admin_accounts UNION ALL SELECT 'Finance' as account_type, username, full_name as name, email, phone, role, is_active FROM finance_accounts UNION ALL SELECT 'Operator' as account_type, username, full_name as name, email, phone, 'operator' as role, is_active FROM operator_accounts ORDER BY account_type, username;"

echo.
echo ============================================================================
echo Account Statistics
echo ============================================================================
echo.

docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops -c "SELECT 'Admin' as type, COUNT(*) as total, COUNT(*) FILTER (WHERE is_active = true) as active FROM admin_accounts UNION ALL SELECT 'Finance' as type, COUNT(*) as total, COUNT(*) FILTER (WHERE is_active = true) as active FROM finance_accounts UNION ALL SELECT 'Operator' as type, COUNT(*) as total, COUNT(*) FILTER (WHERE is_active = true) as active FROM operator_accounts;"

echo.
pause
goto MENU

REM ============================================================================
REM View Admin Accounts Details
REM ============================================================================
:LIST_ADMIN
cls
echo.
echo ============================================================================
echo Admin Accounts Details
echo ============================================================================
echo.

docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops -c "SELECT username, full_name, email, phone, role, permissions, is_active FROM admin_accounts ORDER BY username;"

echo.
pause
goto MENU

REM ============================================================================
REM View Finance Accounts Details
REM ============================================================================
:LIST_FINANCE
cls
echo.
echo ============================================================================
echo Finance Accounts Details
echo ============================================================================
echo.

docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops -c "SELECT username, full_name, email, phone, role, permissions, is_active FROM finance_accounts ORDER BY username;"

echo.
pause
goto MENU

REM ============================================================================
REM View Operator Accounts Details
REM ============================================================================
:LIST_OPERATOR
cls
echo.
echo ============================================================================
echo Operator Accounts Details
echo ============================================================================
echo.

docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops -c "SELECT username, full_name, email, phone, balance, is_active, created_at FROM operator_accounts ORDER BY created_at DESC;"

echo.
pause
goto MENU

REM ============================================================================
REM Reset Account Password
REM ============================================================================
:RESET_PASSWORD
cls
echo.
echo ============================================================================
echo Reset Account Password
echo ============================================================================
echo.
echo Please select account type:
echo.
echo [1] Admin Account (admin_accounts)
echo [2] Finance Account (finance_accounts)
echo [3] Operator Account (operator_accounts)
echo [0] Back to Main Menu
echo.
set /p acc_type="Enter option (0-3): "

if "%acc_type%"=="0" goto MENU
if "%acc_type%"=="1" set table_name=admin_accounts
if "%acc_type%"=="2" set table_name=finance_accounts
if "%acc_type%"=="3" set table_name=operator_accounts

if not defined table_name (
    echo Invalid option!
    timeout /t 2 > nul
    goto RESET_PASSWORD
)

echo.
set /p username="Enter username to reset password: "

if "%username%"=="" (
    echo Username cannot be empty!
    timeout /t 2 > nul
    goto RESET_PASSWORD
)

echo.
echo Note: Default password is Admin@123
echo.
set /p confirm="Confirm reset password for user [%username%]? (Y/N): "

if /i not "%confirm%"=="Y" (
    echo Operation cancelled.
    timeout /t 2 > nul
    goto MENU
)

echo.
echo Resetting password...
echo.

REM Use superadmin's password hash (Admin@123)
docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops -c "UPDATE %table_name% SET password_hash = (SELECT password_hash FROM admin_accounts WHERE username = 'superadmin') WHERE username = '%username%';"

if %errorlevel% equ 0 (
    echo.
    echo ============================================================================
    echo Password reset successfully!
    echo ============================================================================
    echo.
    echo Account: %username%
    echo New Password: Admin@123
    echo.
) else (
    echo.
    echo Password reset failed! Please check if username exists.
    echo.
)

pause
goto MENU

REM ============================================================================
REM Delete Account
REM ============================================================================
:DELETE_ACCOUNT
cls
echo.
echo ============================================================================
echo Delete Account (Soft Delete)
echo ============================================================================
echo.
echo WARNING: This operation will deactivate the account, not delete data!
echo.
echo Please select account type:
echo.
echo [1] Admin Account (admin_accounts)
echo [2] Finance Account (finance_accounts)
echo [3] Operator Account (operator_accounts - uses soft delete)
echo [0] Back to Main Menu
echo.
set /p del_type="Enter option (0-3): "

if "%del_type%"=="0" goto MENU
if "%del_type%"=="1" set del_table=admin_accounts
if "%del_type%"=="2" set del_table=finance_accounts
if "%del_type%"=="3" set del_table=operator_accounts

if not defined del_table (
    echo Invalid option!
    timeout /t 2 > nul
    goto DELETE_ACCOUNT
)

echo.
set /p del_username="Enter username to delete: "

if "%del_username%"=="" (
    echo Username cannot be empty!
    timeout /t 2 > nul
    goto DELETE_ACCOUNT
)

echo.
echo WARNING: About to deactivate account [%del_username%]
echo.
set /p del_confirm="Confirm deletion? Type DELETE to confirm: "

if /i not "%del_confirm%"=="DELETE" (
    echo Operation cancelled.
    timeout /t 2 > nul
    goto MENU
)

echo.
echo Deleting account...
echo.

REM Use soft delete for operators, set inactive for others
if "%del_table%"=="operator_accounts" (
    docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops -c "UPDATE %del_table% SET deleted_at = CURRENT_TIMESTAMP, is_active = false WHERE username = '%del_username%';"
) else (
    docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops -c "UPDATE %del_table% SET is_active = false WHERE username = '%del_username%';"
)

if %errorlevel% equ 0 (
    echo.
    echo ============================================================================
    echo Account deleted successfully!
    echo ============================================================================
    echo.
    echo Account: %del_username%
    echo Status: Deactivated
    echo.
) else (
    echo.
    echo Account deletion failed! Please check if username exists.
    echo.
)

pause
goto MENU

REM ============================================================================
REM Exit
REM ============================================================================
:EXIT
cls
echo.
echo ============================================================================
echo Thank you for using MR Game Ops System - Account Management Tool
echo ============================================================================
echo.
exit /b 0
