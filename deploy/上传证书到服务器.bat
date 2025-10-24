@echo off
chcp 65001 >nul
echo ========================================
echo   SSL 证书上传脚本
echo   域名: mrgun.chu-jiao.com
echo ========================================
echo.

REM 👇 请在这里填写你的服务器 IP 地址
set SERVER_IP=YOUR_SERVER_IP_HERE
set SERVER_USER=root

echo 请输入服务器 IP 地址（当前：%SERVER_IP%）：
set /p INPUT_IP=
if not "%INPUT_IP%"=="" set SERVER_IP=%INPUT_IP%

echo.
echo 开始上传文件到 %SERVER_USER%@%SERVER_IP% ...
echo.

REM 上传 SSL 证书文件
echo [1/3] 上传 SSL 证书 (.pem)...
scp "21088616_mrgun.chu-jiao.com_nginx\mrgun.chu-jiao.com.pem" %SERVER_USER%@%SERVER_IP%:/tmp/

if errorlevel 1 (
    echo ❌ 证书上传失败！
    pause
    exit /b 1
)
echo ✅ 证书上传成功

REM 上传 SSL 私钥文件
echo [2/3] 上传 SSL 私钥 (.key)...
scp "21088616_mrgun.chu-jiao.com_nginx\mrgun.chu-jiao.com.key" %SERVER_USER%@%SERVER_IP%:/tmp/

if errorlevel 1 (
    echo ❌ 私钥上传失败！
    pause
    exit /b 1
)
echo ✅ 私钥上传成功

REM 上传 Nginx 配置文件
echo [3/3] 上传 Nginx 配置文件...
scp "nginx-ssl.conf" %SERVER_USER%@%SERVER_IP%:/tmp/

if errorlevel 1 (
    echo ❌ 配置文件上传失败！
    pause
    exit /b 1
)
echo ✅ 配置文件上传成功

echo.
echo ========================================
echo   所有文件上传完成！
echo ========================================
echo.
echo 文件已上传到服务器的 /tmp/ 目录：
echo   - /tmp/mrgun.chu-jiao.com.pem
echo   - /tmp/mrgun.chu-jiao.com.key
echo   - /tmp/nginx-ssl.conf
echo.
echo 接下来请 SSH 登录服务器，执行以下命令：
echo.
echo   ssh %SERVER_USER%@%SERVER_IP%
echo.
echo 然后按照 "部署SSL证书-说明.md" 继续操作。
echo.
echo 快速部署命令（在服务器上执行）：
echo ========================================
echo   # 1. 移动证书到正确位置
echo   sudo mkdir -p /etc/ssl/certs /etc/ssl/private
echo   sudo mv /tmp/mrgun.chu-jiao.com.pem /etc/ssl/certs/
echo   sudo mv /tmp/mrgun.chu-jiao.com.key /etc/ssl/private/
echo.
echo   # 2. 设置权限
echo   sudo chmod 644 /etc/ssl/certs/mrgun.chu-jiao.com.pem
echo   sudo chmod 600 /etc/ssl/private/mrgun.chu-jiao.com.key
echo.
echo   # 3. 备份并替换配置
echo   sudo cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup
echo   sudo cp /tmp/nginx-ssl.conf /etc/nginx/sites-available/default
echo.
echo   # 4. 测试并重启 Nginx
echo   sudo nginx -t
echo   sudo nginx -s reload
echo.
echo   # 5. 验证 HTTPS
echo   curl -I https://mrgun.chu-jiao.com
echo ========================================
echo.
pause
