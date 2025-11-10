@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ====================================
echo 头显Server API 性能测试工具
echo ====================================
echo.

REM 设置默认值
set "SERVER_TYPE="
set "TEST_COUNT=10"
set "DELAY_SECONDS=1"

REM 选择服务器
echo 请选择测试服务器:
echo [1] 生产服务器 (https://mrgun.chu-jiao.com)
echo [2] 开发服务器 (https://10.10.3.9)
echo.
set /p SERVER_TYPE="请输入选项 (1 或 2): "

if "%SERVER_TYPE%"=="1" (
    set "BASE_URL=https://mrgun.chu-jiao.com/api/v1"
    echo 已选择: 生产服务器
) else if "%SERVER_TYPE%"=="2" (
    set "BASE_URL=https://10.10.3.9/api/v1"
    echo 已选择: 开发服务器
) else (
    echo 无效选项，使用默认: 生产服务器
    set "BASE_URL=https://mrgun.chu-jiao.com/api/v1"
)
echo.

REM 输入测试次数
set /p TEST_COUNT="请输入测试次数 (默认10次): "
if "%TEST_COUNT%"=="" set "TEST_COUNT=10"
echo.

REM 输入测试间隔
set /p DELAY_SECONDS="请输入测试间隔秒数 (默认1秒): "
if "%DELAY_SECONDS%"=="" set "DELAY_SECONDS=1"
echo.

echo ====================================
echo 测试配置:
echo - 服务器: %BASE_URL%
echo - 测试次数: %TEST_COUNT%
echo - 测试间隔: %DELAY_SECONDS% 秒
echo ====================================
echo.
pause

REM 启动Python测试脚本
cd /d "%~dp0"
python test_headset_api.py --base-url "%BASE_URL%" --count %TEST_COUNT% --delay %DELAY_SECONDS% --username operator1 --password operator123

pause
