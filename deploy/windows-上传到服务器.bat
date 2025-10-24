@echo off
chcp 65001 >nul 2>&1
REM =============================================================================
REM Windows - 上传项目文件和镜像到服务器
REM =============================================================================

setlocal enabledelayedexpansion

echo ========================================================================
echo   MR游戏运营管理系统 - 文件上传工具
echo ========================================================================
echo.

REM 检查SCP是否可用
where scp >nul 2>&1
if errorlevel 1 (
    echo [错误] SCP命令不可用！
    echo.
    echo 请安装OpenSSH客户端：
    echo   Windows 10/11: 设置 ^> 应用 ^> 可选功能 ^> 添加功能 ^> OpenSSH客户端
    echo   或使用WinSCP图形界面工具: https://winscp.net/
    echo.
    pause
    exit /b 1
)

REM 获取服务器信息
echo 请输入服务器信息:
echo.
set /p SERVER_IP=服务器IP地址:
set /p SERVER_USER=SSH用户名 [默认: root]:

if "%SERVER_USER%"=="" set SERVER_USER=root

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo   服务器: %SERVER_USER%@%SERVER_IP%
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

REM 确认
set /p CONFIRM=确认开始上传？(Y/N):
if /i not "%CONFIRM%"=="Y" (
    echo 已取消
    pause
    exit /b 0
)

echo.
echo ========================================================================
echo   步骤1/3: 创建服务器目录
echo ========================================================================
echo.

ssh %SERVER_USER%@%SERVER_IP% "mkdir -p /root/docker-images /root/mr-game-ops-upload"

if errorlevel 1 (
    echo [错误] 无法连接到服务器！
    echo 请检查：
    echo   1. 服务器IP地址是否正确
    echo   2. SSH服务是否运行
    echo   3. 防火墙是否允许SSH连接
    echo.
    pause
    exit /b 1
)

echo [成功] 服务器目录已创建
echo.

REM 切换到项目根目录
cd /d "%~dp0\.."

echo ========================================================================
echo   步骤2/3: 上传Docker镜像 (如果存在)
echo ========================================================================
echo.

if exist "C:\docker-images\*.tar" (
    echo 正在上传Docker镜像...
    echo 提示: 这可能需要较长时间，取决于文件大小和网速
    echo.

    scp C:\docker-images\*.tar %SERVER_USER%@%SERVER_IP%:/root/docker-images/

    if errorlevel 1 (
        echo [警告] 镜像上传失败或未找到镜像文件
        echo 请确保镜像文件在: C:\docker-images\
        echo.
    ) else (
        echo [成功] 镜像文件已上传
        echo.
    )
) else (
    echo [跳过] 未找到Docker镜像文件: C:\docker-images\*.tar
    echo 如果已经上传过，可以忽略此警告
    echo.
)

echo ========================================================================
echo   步骤3/3: 上传项目文件
echo ========================================================================
echo.

echo 正在上传项目文件...
echo.

REM 上传backend
echo [1/3] 上传backend目录...
scp -r backend %SERVER_USER%@%SERVER_IP%:/root/mr-game-ops-upload/
if errorlevel 1 (
    echo [错误] backend上传失败
    pause
    exit /b 1
)
echo       [成功]

REM 上传frontend（如果存在）
if exist "frontend" (
    echo [2/3] 上传frontend目录...
    scp -r frontend %SERVER_USER%@%SERVER_IP%:/root/mr-game-ops-upload/
    if errorlevel 1 (
        echo [警告] frontend上传失败
    ) else (
        echo       [成功]
    )
) else (
    echo [2/3] [跳过] frontend目录不存在
)

REM 上传deploy
echo [3/3] 上传deploy目录...
scp -r deploy %SERVER_USER%@%SERVER_IP%:/root/mr-game-ops-upload/
if errorlevel 1 (
    echo [错误] deploy上传失败
    pause
    exit /b 1
)
echo       [成功]

echo.
echo ========================================================================
echo   上传完成！
echo ========================================================================
echo.
echo 服务器文件位置:
echo   - 项目文件: /root/mr-game-ops-upload/
echo   - 镜像文件: /root/docker-images/
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo   下一步: SSH到服务器并执行部署脚本
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 方法1: 使用PowerShell/CMD
echo   ssh %SERVER_USER%@%SERVER_IP%
echo   bash /root/mr-game-ops-upload/deploy/一键部署脚本-服务器端.sh
echo.
echo 方法2: 使用PuTTY等SSH客户端
echo   1. 连接到 %SERVER_IP%
echo   2. 执行: bash /root/mr-game-ops-upload/deploy/一键部署脚本-服务器端.sh
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

pause
