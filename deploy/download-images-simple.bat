@echo off
REM =============================================================================
REM Simple Docker Image Download Script for Windows
REM =============================================================================

echo ========================================================================
echo   Docker Image Download Tool (Simple Version)
echo ========================================================================
echo.

REM Check if Docker is running
docker version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running!
    echo Please start Docker Desktop first.
    pause
    exit /b 1
)

echo [OK] Docker is running
echo.

REM Create export directory
set EXPORT_DIR=C:\docker-images
if not exist "%EXPORT_DIR%" mkdir "%EXPORT_DIR%"
echo Export directory: %EXPORT_DIR%
echo.

REM Ask what to download
echo What would you like to download?
echo   1 = Core images only (230 MB)
echo   2 = Core + Frontend (450 MB)
echo   3 = All including monitoring (1 GB)
echo.
set /p CHOICE=Enter your choice (1/2/3):

echo.
echo ========================================================================
echo   Downloading Docker images...
echo ========================================================================
echo.

REM Download core images
echo [1/3] Downloading Python 3.11...
docker pull python:3.11-slim
echo.

echo [2/3] Downloading PostgreSQL 14...
docker pull postgres:14-alpine
echo.

echo [3/3] Downloading Redis 7...
docker pull redis:7-alpine
echo.

REM Download frontend images if needed
if "%CHOICE%"=="2" goto FRONTEND
if "%CHOICE%"=="3" goto FRONTEND
goto EXPORT

:FRONTEND
echo [4/5] Downloading Node 18...
docker pull node:18-alpine
echo.

echo [5/5] Downloading Nginx...
docker pull nginx:alpine
echo.

if "%CHOICE%"=="3" goto MONITORING
goto EXPORT

:MONITORING
echo [6/7] Downloading Prometheus...
docker pull prom/prometheus:latest
echo.

echo [7/7] Downloading Grafana...
docker pull grafana/grafana:latest
echo.

:EXPORT
echo ========================================================================
echo   Exporting images to tar files...
echo ========================================================================
echo.

cd /d "%EXPORT_DIR%"

echo Exporting Python...
docker save python:3.11-slim -o python-3.11-slim.tar
echo [OK] python-3.11-slim.tar
echo.

echo Exporting PostgreSQL...
docker save postgres:14-alpine -o postgres-14-alpine.tar
echo [OK] postgres-14-alpine.tar
echo.

echo Exporting Redis...
docker save redis:7-alpine -o redis-7-alpine.tar
echo [OK] redis-7-alpine.tar
echo.

if "%CHOICE%"=="1" goto DONE

echo Exporting Node...
docker save node:18-alpine -o node-18-alpine.tar
echo [OK] node-18-alpine.tar
echo.

echo Exporting Nginx...
docker save nginx:alpine -o nginx-alpine.tar
echo [OK] nginx-alpine.tar
echo.

if "%CHOICE%"=="2" goto DONE

echo Exporting Prometheus...
docker save prom/prometheus:latest -o prometheus-latest.tar
echo [OK] prometheus-latest.tar
echo.

echo Exporting Grafana...
docker save grafana/grafana:latest -o grafana-latest.tar
echo [OK] grafana-latest.tar
echo.

:DONE
echo ========================================================================
echo   COMPLETE!
echo ========================================================================
echo.

echo All files saved to: %EXPORT_DIR%
echo.
dir "%EXPORT_DIR%\*.tar"
echo.

echo ========================================================================
echo   Next Steps
echo ========================================================================
echo.
echo Upload to server using one of these methods:
echo.
echo Method 1: SCP Command
echo   cd C:\docker-images
echo   scp *.tar root@YOUR_SERVER_IP:/root/docker-images/
echo.
echo Method 2: WinSCP (GUI)
echo   Download from: https://winscp.net/
echo   Upload all .tar files to /root/docker-images/
echo.
echo After uploading, SSH to server and run:
echo   bash /root/import-and-deploy.sh
echo.

pause
