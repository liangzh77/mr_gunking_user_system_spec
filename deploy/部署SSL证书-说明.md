# SSL 证书部署说明

## 📦 准备好的文件

本目录包含以下文件：
- `21088616_mrgun.chu-jiao.com_nginx/mrgun.chu-jiao.com.pem` - SSL 证书
- `21088616_mrgun.chu-jiao.com_nginx/mrgun.chu-jiao.com.key` - SSL 私钥
- `nginx-ssl.conf` - Nginx 配置文件

## 🚀 部署步骤

### 步骤 1：上传证书到服务器

```bash
# 从你的本地 Windows 上传证书到 Linux 服务器
# 请替换 YOUR_SERVER_IP 为你的服务器 IP 地址

# 上传证书文件
scp "C:\liangz77\python_projects\github_projects\mr_gunking_user_system_spec\deploy\21088616_mrgun.chu-jiao.com_nginx\mrgun.chu-jiao.com.pem" root@YOUR_SERVER_IP:/etc/ssl/certs/

# 上传私钥文件
scp "C:\liangz77\python_projects\github_projects\mr_gunking_user_system_spec\deploy\21088616_mrgun.chu-jiao.com_nginx\mrgun.chu-jiao.com.key" root@YOUR_SERVER_IP:/etc/ssl/private/

# 上传 Nginx 配置
scp "C:\liangz77\python_projects\github_projects\mr_gunking_user_system_spec\deploy\nginx-ssl.conf" root@YOUR_SERVER_IP:/tmp/
```

### 步骤 2：SSH 登录服务器

```bash
ssh root@YOUR_SERVER_IP
```

### 步骤 3：设置证书权限

```bash
# 设置证书文件权限
sudo chmod 644 /etc/ssl/certs/mrgun.chu-jiao.com.pem
sudo chown root:root /etc/ssl/certs/mrgun.chu-jiao.com.pem

# 设置私钥文件权限（只有 root 可读）
sudo chmod 600 /etc/ssl/private/mrgun.chu-jiao.com.key
sudo chown root:root /etc/ssl/private/mrgun.chu-jiao.com.key

# 验证文件存在且权限正确
ls -la /etc/ssl/certs/mrgun.chu-jiao.com.pem
ls -la /etc/ssl/private/mrgun.chu-jiao.com.key
```

应该显示：
```
-rw-r--r-- 1 root root 3842 ... /etc/ssl/certs/mrgun.chu-jiao.com.pem
-rw------- 1 root root 1675 ... /etc/ssl/private/mrgun.chu-jiao.com.key
```

### 步骤 4：备份原配置文件

```bash
# 备份原 Nginx 配置（重要！）
sudo cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup.$(date +%Y%m%d)

# 查看备份
ls -la /etc/nginx/sites-available/
```

### 步骤 5：替换 Nginx 配置

```bash
# 将新配置复制到 Nginx 配置目录
sudo cp /tmp/nginx-ssl.conf /etc/nginx/sites-available/default

# 验证配置文件
cat /etc/nginx/sites-available/default | head -20
```

### 步骤 6：修改配置中的路径（重要！）

根据你的实际情况，需要修改配置文件中的以下内容：

```bash
sudo nano /etc/nginx/sites-available/default
```

**需要确认/修改的地方**：

1. **前端文件路径**（第 82 行）：
   ```nginx
   root /var/www/mrgun;  # 👈 改成你前端文件的实际路径
   ```

2. **FastAPI 端口**（第 95 行）：
   ```nginx
   proxy_pass http://127.0.0.1:8000;  # 👈 如果不是 8000 端口，改成实际端口
   ```

3. **上传文件目录**（第 159 行）：
   ```nginx
   alias /opt/mr-game-ops/data/uploads/;  # 👈 改成实际路径
   ```

4. **发票文件目录**（第 172 行）：
   ```nginx
   alias /opt/mr-game-ops/data/invoices/;  # 👈 改成实际路径
   ```

**如何找到这些路径？**

```bash
# 查找前端文件
find /home -name "index.html" 2>/dev/null | grep -v node_modules
find /var/www -name "index.html" 2>/dev/null
find /opt -name "index.html" 2>/dev/null

# 查看 FastAPI 运行端口
ps aux | grep uvicorn
ps aux | grep gunicorn
sudo netstat -tuln | grep python

# 查找上传目录
find / -type d -name "uploads" 2>/dev/null
find / -type d -name "invoices" 2>/dev/null
```

### 步骤 7：测试 Nginx 配置

```bash
# 测试配置语法
sudo nginx -t

# 应该显示：
# nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
# nginx: configuration file /etc/nginx/nginx.conf test is successful
```

**如果测试失败**，查看错误信息：
```bash
# 查看详细错误
sudo nginx -t 2>&1

# 常见错误排查
# 1. 证书文件不存在 -> 检查步骤 3
# 2. 前端路径不存在 -> 修改 root 路径
# 3. 端口冲突 -> 检查其他服务是否占用 80/443 端口
```

### 步骤 8：开放防火墙端口

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw status

# 或 CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 步骤 9：重启 Nginx

```bash
# 如果测试通过，重新加载配置
sudo nginx -s reload

# 或者重启服务
sudo systemctl restart nginx

# 检查 Nginx 状态
sudo systemctl status nginx

# 确保 Nginx 开机自启
sudo systemctl enable nginx
```

### 步骤 10：验证 HTTPS

```bash
# 1. 测试 HTTPS 连接
curl -I https://mrgun.chu-jiao.com

# 应该返回 200 OK 或 301/302

# 2. 测试 HTTP 重定向
curl -I http://mrgun.chu-jiao.com

# 应该返回 301 重定向到 https://

# 3. 查看证书信息
openssl s_client -connect mrgun.chu-jiao.com:443 -servername mrgun.chu-jiao.com | grep "Verify return code"

# 应该显示：Verify return code: 0 (ok)

# 4. 查看证书过期时间
echo | openssl s_client -connect mrgun.chu-jiao.com:443 2>/dev/null | openssl x509 -noout -dates

# 5. 检查端口监听
sudo netstat -tuln | grep :443
sudo netstat -tuln | grep :80
```

## ✅ 验证清单

部署完成后，检查以下项目：

- [ ] 证书文件已上传到 `/etc/ssl/certs/` 和 `/etc/ssl/private/`
- [ ] 证书权限设置正确（644 和 600）
- [ ] Nginx 配置文件已替换
- [ ] 配置中的路径已根据实际情况修改
- [ ] `nginx -t` 测试通过
- [ ] 防火墙已开放 80 和 443 端口
- [ ] Nginx 已重启
- [ ] `curl https://mrgun.chu-jiao.com` 返回正常
- [ ] HTTP 自动跳转到 HTTPS
- [ ] 浏览器访问显示 🔒 图标

## 🚨 如果出现问题

### 问题 1：证书错误

```bash
# 检查证书是否正确
openssl x509 -in /etc/ssl/certs/mrgun.chu-jiao.com.pem -noout -text | grep "Subject:"
# 应该显示：Subject: CN=mrgun.chu-jiao.com

# 检查私钥是否匹配证书
openssl x509 -noout -modulus -in /etc/ssl/certs/mrgun.chu-jiao.com.pem | openssl md5
openssl rsa -noout -modulus -in /etc/ssl/private/mrgun.chu-jiao.com.key | openssl md5
# 两个 MD5 值应该相同
```

### 问题 2：无法访问

```bash
# 检查 Nginx 是否运行
sudo systemctl status nginx

# 检查端口是否监听
sudo netstat -tuln | grep :443

# 查看 Nginx 错误日志
sudo tail -f /var/log/nginx/mrgun_error.log

# 查看访问日志
sudo tail -f /var/log/nginx/mrgun_access.log
```

### 问题 3：502 Bad Gateway

```bash
# 检查后端服务是否运行
ps aux | grep -E "uvicorn|gunicorn|python.*main"

# 检查后端端口
sudo netstat -tuln | grep :8000

# 启动后端服务（如果没运行）
# cd /path/to/your/backend
# uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### 恢复备份

如果配置有问题，恢复原配置：

```bash
# 恢复备份
sudo cp /etc/nginx/sites-available/default.backup.YYYYMMDD /etc/nginx/sites-available/default

# 重新加载
sudo nginx -s reload
```

## 📞 需要帮助？

如果遇到问题，收集以下信息：

```bash
# 1. Nginx 版本
nginx -v

# 2. 系统信息
cat /etc/os-release

# 3. 错误日志
sudo tail -50 /var/log/nginx/error.log

# 4. Nginx 配置测试结果
sudo nginx -t 2>&1

# 5. 证书信息
ls -la /etc/ssl/certs/mrgun.chu-jiao.com.pem
ls -la /etc/ssl/private/mrgun.chu-jiao.com.key
```

## 🎯 快速部署命令汇总

```bash
# 在服务器上执行（假设证书已上传到 /tmp/）

# 1. 移动证书到正确位置
sudo mv /tmp/mrgun.chu-jiao.com.pem /etc/ssl/certs/
sudo mv /tmp/mrgun.chu-jiao.com.key /etc/ssl/private/

# 2. 设置权限
sudo chmod 644 /etc/ssl/certs/mrgun.chu-jiao.com.pem
sudo chmod 600 /etc/ssl/private/mrgun.chu-jiao.com.key

# 3. 备份并替换配置
sudo cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup
sudo mv /tmp/nginx-ssl.conf /etc/nginx/sites-available/default

# 4. 测试并重启
sudo nginx -t && sudo nginx -s reload

# 5. 验证
curl -I https://mrgun.chu-jiao.com
```
