@echo off
REM E2E 测试快速运行脚本
REM 用法: run-e2e-tests.bat [localhost|production] [ui|headless]

echo ========================================
echo MR Gunking User System - E2E Tests
echo ========================================
echo.

REM 检查参数
set ENV=%1
set MODE=%2

if "%ENV%"=="" set ENV=localhost
if "%MODE%"=="" set MODE=ui

REM 验证环境参数
if not "%ENV%"=="localhost" if not "%ENV%"=="production" (
    echo Error: Invalid environment. Use 'localhost' or 'production'
    echo Usage: run-e2e-tests.bat [localhost^|production] [ui^|headless]
    exit /b 1
)

REM 验证模式参数
if not "%MODE%"=="ui" if not "%MODE%"=="headless" (
    echo Error: Invalid mode. Use 'ui' or 'headless'
    echo Usage: run-e2e-tests.bat [localhost^|production] [ui^|headless]
    exit /b 1
)

echo Environment: %ENV%
echo Mode: %MODE%
echo.

REM 检查是否安装了依赖
if not exist "node_modules\" (
    echo Installing dependencies...
    call npm install
    echo.
)

REM 检查是否安装了 Playwright 浏览器
if not exist "node_modules\.playwright\" (
    echo Installing Playwright browsers...
    call npx playwright install
    echo.
)

REM 运行测试
echo Starting E2E tests...
echo.

if "%MODE%"=="ui" (
    call npm run test:%ENV%:ui
) else (
    call npm run test:%ENV%
)

echo.
echo ========================================
echo Test execution completed
echo ========================================
echo.
echo To view test report: npm run test:report
echo To view trace: npm run test:show-report
echo.
