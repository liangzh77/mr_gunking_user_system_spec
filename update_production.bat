@echo off
REM 生产环境更新脚本 (Windows版本)
REM 使用方法: update_production.bat

echo ==========================================
echo 开始生产环境更新流程
echo ==========================================
echo.

REM 1. 备份数据库
echo 1. 备份数据库...
if not exist database_backups mkdir database_backups
set BACKUP_FILE=database_backups\backup_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%.sql
set BACKUP_FILE=%BACKUP_FILE: =0%
docker-compose exec -T postgres pg_dump -U mr_admin mr_game_ops > "%BACKUP_FILE%"
if errorlevel 1 goto :error
echo √ 数据库已备份到: %BACKUP_FILE%
echo.

REM 2. 拉取最新代码
echo 2. 拉取最新代码...
git pull origin 001-mr-v2
if errorlevel 1 goto :error
echo √ 代码已更新
echo.

REM 3. 检查当前数据库版本
echo 3. 检查当前数据库版本...
docker-compose exec backend alembic current
echo.

REM 4. 重新构建并启动容器
echo 4. 重新构建并启动容器...
docker-compose up -d --build
if errorlevel 1 goto :error
echo √ 容器已重建
echo.

REM 5. 等待后端容器启动
echo 5. 等待后端容器启动...
timeout /t 15 /nobreak > nul
echo √ 等待完成
echo.

REM 6. 应用数据库迁移
echo 6. 应用数据库迁移...
docker-compose exec backend alembic upgrade head
if errorlevel 1 goto :migration_error
echo √ 数据库迁移已应用
echo.

REM 7. 检查新的数据库版本
echo 7. 检查新的数据库版本...
docker-compose exec backend alembic current
echo.

REM 8. 重启后端容器
echo 8. 重启后端容器...
docker-compose restart backend
timeout /t 5 /nobreak > nul
echo √ 后端容器已重启
echo.

REM 9. 检查容器状态
echo 9. 检查容器状态...
docker-compose ps
echo.

REM 10. 查看后端日志
echo 10. 查看后端日志 (最近50行)...
docker-compose logs backend --tail 50
echo.

echo ==========================================
echo √ 生产环境更新完成!
echo 备份文件: %BACKUP_FILE%
echo ==========================================
goto :end

:migration_error
echo.
echo ==========================================
echo X 数据库迁移失败!
echo ==========================================
echo.
echo 正在尝试恢复...
echo 请手动检查并恢复数据库:
echo docker-compose exec -T postgres psql -U mr_admin mr_game_ops ^< %BACKUP_FILE%
echo.
pause
exit /b 1

:error
echo.
echo ==========================================
echo X 更新过程中出现错误!
echo ==========================================
echo.
pause
exit /b 1

:end
pause
