@echo off
REM =============================================================================
REM Upload Project Files to Server (English Version - No Encoding Issues)
REM =============================================================================

setlocal enabledelayedexpansion

echo ========================================================================
echo   MR Game Ops System - Upload Tool
echo ========================================================================
echo.

REM Check SCP
where scp >nul 2>&1
if errorlevel 1 (
    echo [ERROR] SCP not found!
    echo.
    echo Please install OpenSSH Client:
    echo   Windows 10/11: Settings ^> Apps ^> Optional Features ^> Add OpenSSH Client
    echo   Or use WinSCP: https://winscp.net/
    echo.
    pause
    exit /b 1
)

REM Get server info
echo Enter server information:
echo.
set /p SERVER_IP=Server IP:
set /p SERVER_USER=SSH Username [default: root]:

if "%SERVER_USER%"=="" set SERVER_USER=root

echo.
echo ========================================================================
echo   Server: %SERVER_USER%@%SERVER_IP%
echo ========================================================================
echo.

REM Confirm
set /p CONFIRM=Start upload? (Y/N):
if /i not "%CONFIRM%"=="Y" (
    echo Cancelled
    pause
    exit /b 0
)

echo.
echo ========================================================================
echo   Step 1/3: Create server directories
echo ========================================================================
echo.

ssh %SERVER_USER%@%SERVER_IP% "mkdir -p /root/docker-images /root/mr-game-ops-upload"

if errorlevel 1 (
    echo [ERROR] Cannot connect to server!
    echo Please check:
    echo   1. Server IP is correct
    echo   2. SSH service is running
    echo   3. Firewall allows SSH
    echo.
    pause
    exit /b 1
)

echo [OK] Directories created
echo.

REM Go to project root
cd /d "%~dp0\.."

echo ========================================================================
echo   Step 2/3: Upload Docker images
echo ========================================================================
echo.

if exist "C:\docker-images\*.tar" (
    echo Uploading Docker images...
    echo This may take a while...
    echo.

    scp C:\docker-images\*.tar %SERVER_USER%@%SERVER_IP%:/root/docker-images/

    if errorlevel 1 (
        echo [WARNING] Image upload failed
        echo.
    ) else (
        echo [OK] Images uploaded
        echo.
    )
) else (
    echo [SKIP] No Docker images found in C:\docker-images\
    echo.
)

echo ========================================================================
echo   Step 3/3: Upload project files
echo ========================================================================
echo.

echo Uploading project files...
echo.

REM Upload backend
echo [1/3] Uploading backend...
scp -r backend %SERVER_USER%@%SERVER_IP%:/root/mr-game-ops-upload/
if errorlevel 1 (
    echo [ERROR] Backend upload failed
    pause
    exit /b 1
)
echo       [OK]

REM Upload frontend
if exist "frontend" (
    echo [2/3] Uploading frontend...
    scp -r frontend %SERVER_USER%@%SERVER_IP%:/root/mr-game-ops-upload/
    if errorlevel 1 (
        echo [WARNING] Frontend upload failed
    ) else (
        echo       [OK]
    )
) else (
    echo [2/3] [SKIP] frontend directory not found
)

REM Upload deploy
echo [3/3] Uploading deploy...
scp -r deploy %SERVER_USER%@%SERVER_IP%:/root/mr-game-ops-upload/
if errorlevel 1 (
    echo [ERROR] Deploy upload failed
    pause
    exit /b 1
)
echo       [OK]

echo.
echo ========================================================================
echo   Upload Complete!
echo ========================================================================
echo.
echo Server file locations:
echo   - Project files: /root/mr-game-ops-upload/
echo   - Docker images: /root/docker-images/
echo.
echo ========================================================================
echo   Next: SSH to server and run deployment script
echo ========================================================================
echo.
echo Method 1: Using PowerShell/CMD
echo   ssh %SERVER_USER%@%SERVER_IP%
echo   bash /root/mr-game-ops-upload/deploy/一键部署脚本-服务器端.sh
echo.
echo Method 2: Using PuTTY
echo   1. Connect to %SERVER_IP%
echo   2. Run: bash /root/mr-game-ops-upload/deploy/一键部署脚本-服务器端.sh
echo.
echo ========================================================================
echo.

pause
