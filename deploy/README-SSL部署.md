# SSL 证书部署 - 快速开始

## 📦 文件清单

本目录包含以下文件：

```
deploy/
├── 21088616_mrgun.chu-jiao.com_nginx/
│   ├── mrgun.chu-jiao.com.pem          # SSL 证书文件
│   └── mrgun.chu-jiao.com.key          # SSL 私钥文件
├── nginx-ssl.conf                       # Nginx SSL 配置文件（已配置好）
├── 上传证书到服务器.bat                 # Windows 一键上传脚本
├── deploy-ssl.sh                        # Linux 自动部署脚本
├── 部署SSL证书-说明.md                  # 详细部署说明
└── README-SSL部署.md                    # 本文件
```

## 🚀 三步完成部署

### 方式 A：自动部署（推荐）

#### 第 1 步：上传文件（在 Windows 本地）

1. 双击运行 `上传证书到服务器.bat`
2. 输入你的服务器 IP 地址
3. 等待文件上传完成

#### 第 2 步：自动部署（在 Linux 服务器）

```bash
# SSH 登录服务器
ssh root@your-server-ip

# 上传部署脚本（如果还没上传）
# 或者手动创建：nano /tmp/deploy-ssl.sh，然后粘贴脚本内容

# 运行自动部署脚本
sudo bash /tmp/deploy-ssl.sh
```

#### 第 3 步：验证部署

```bash
# 测试 HTTPS
curl -I https://mrgun.chu-jiao.com

# 在浏览器访问
# https://mrgun.chu-jiao.com
```

---

### 方式 B：手动部署

如果自动脚本失败，按照以下步骤手动部署：

#### 1. 上传证书（在 Windows）

双击运行 `上传证书到服务器.bat`，或者手动执行：

```bash
scp "21088616_mrgun.chu-jiao.com_nginx\mrgun.chu-jiao.com.pem" root@YOUR_SERVER_IP:/tmp/
scp "21088616_mrgun.chu-jiao.com_nginx\mrgun.chu-jiao.com.key" root@YOUR_SERVER_IP:/tmp/
scp "nginx-ssl.conf" root@YOUR_SERVER_IP:/tmp/
```

#### 2. 配置证书（在 Linux 服务器）

```bash
# SSH 登录
ssh root@your-server-ip

# 移动证书到系统目录
sudo mv /tmp/mrgun.chu-jiao.com.pem /etc/ssl/certs/
sudo mv /tmp/mrgun.chu-jiao.com.key /etc/ssl/private/

# 设置权限
sudo chmod 644 /etc/ssl/certs/mrgun.chu-jiao.com.pem
sudo chmod 600 /etc/ssl/private/mrgun.chu-jiao.com.key
```

#### 3. 配置 Nginx

```bash
# 备份原配置
sudo cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup

# 替换配置
sudo cp /tmp/nginx-ssl.conf /etc/nginx/sites-available/default

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo nginx -s reload
```

#### 4. 验证

```bash
# 测试 HTTPS
curl -I https://mrgun.chu-jiao.com
```

---

## ⚙️ 需要修改的配置

如果你的环境和默认配置不同，需要修改以下内容：

### 1. FastAPI 后端端口

**默认**：8000

如果你的 FastAPI 运行在其他端口（如 8001），修改：

```bash
sudo nano /etc/nginx/sites-available/default

# 找到这行（第 95 行左右）：
proxy_pass http://127.0.0.1:8000;

# 改成你的端口：
proxy_pass http://127.0.0.1:8001;
```

**如何查看 FastAPI 端口**：
```bash
ps aux | grep uvicorn
# 或
sudo netstat -tuln | grep python
```

### 2. 前端文件路径

**默认**：`/var/www/mrgun`

如果你的前端文件在其他位置，修改：

```bash
sudo nano /etc/nginx/sites-available/default

# 找到这行（第 82 行左右）：
root /var/www/mrgun;

# 改成实际路径，例如：
root /home/youruser/frontend/dist;
```

**如何查找前端文件**：
```bash
find /home -name "index.html" 2>/dev/null | grep -v node_modules
find /var/www -name "index.html" 2>/dev/null
```

### 3. 上传文件目录

**默认**：`/opt/mr-game-ops/data/uploads/` 和 `/opt/mr-game-ops/data/invoices/`

修改方法：

```bash
sudo nano /etc/nginx/sites-available/default

# 找到第 159 和 172 行左右，修改为实际路径
```

修改后，记得重新加载 Nginx：
```bash
sudo nginx -t && sudo nginx -s reload
```

---

## ✅ 部署检查清单

部署完成后，检查以下项目：

- [ ] 证书文件存在：`ls -la /etc/ssl/certs/mrgun.chu-jiao.com.pem`
- [ ] 私钥文件存在：`ls -la /etc/ssl/private/mrgun.chu-jiao.com.key`
- [ ] 证书权限正确：pem 文件 644，key 文件 600
- [ ] Nginx 配置测试通过：`sudo nginx -t`
- [ ] 防火墙已开放：`sudo ufw status | grep 443`
- [ ] Nginx 正在运行：`sudo systemctl status nginx`
- [ ] 端口 443 监听中：`sudo netstat -tuln | grep :443`
- [ ] HTTPS 访问正常：`curl -I https://mrgun.chu-jiao.com`
- [ ] HTTP 自动跳转：`curl -I http://mrgun.chu-jiao.com`（返回 301）
- [ ] 浏览器显示 🔒 图标

---

## 🚨 常见问题

### 1. 上传脚本提示"scp 不是内部或外部命令"

**解决**：安装 OpenSSH 客户端

- Windows 10/11：设置 → 应用 → 可选功能 → 添加功能 → OpenSSH 客户端
- 或者手动使用 WinSCP、FileZilla 等工具上传

### 2. nginx -t 报错：找不到证书文件

**检查**：
```bash
ls -la /etc/ssl/certs/mrgun.chu-jiao.com.pem
ls -la /etc/ssl/private/mrgun.chu-jiao.com.key
```

**解决**：确保文件已上传且路径正确

### 3. 浏览器显示"不安全"

**可能原因**：
- DNS 还未生效（等待 24-48 小时）
- 证书域名不匹配
- 证书已过期

**检查证书**：
```bash
openssl x509 -in /etc/ssl/certs/mrgun.chu-jiao.com.pem -noout -text | grep "Subject:"
openssl x509 -in /etc/ssl/certs/mrgun.chu-jiao.com.pem -noout -dates
```

### 4. 502 Bad Gateway

**原因**：后端服务未运行

**检查**：
```bash
# 检查 FastAPI 是否运行
ps aux | grep uvicorn
ps aux | grep gunicorn

# 检查端口
sudo netstat -tuln | grep :8000
```

**启动后端**：
```bash
cd /path/to/your/backend
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### 5. 无法访问（连接超时）

**检查防火墙**：
```bash
# Ubuntu/Debian
sudo ufw allow 443/tcp
sudo ufw allow 80/tcp

# CentOS/RHEL
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --reload
```

**检查云服务商安全组**：
- 确保安全组规则允许 80 和 443 端口入站

---

## 📊 验证工具

### 命令行验证

```bash
# 1. 测试 HTTPS 连接
curl -I https://mrgun.chu-jiao.com

# 2. 测试 HTTP 重定向
curl -I http://mrgun.chu-jiao.com

# 3. 查看证书详情
openssl s_client -connect mrgun.chu-jiao.com:443 -servername mrgun.chu-jiao.com

# 4. 查看证书过期时间
echo | openssl s_client -connect mrgun.chu-jiao.com:443 2>/dev/null | openssl x509 -noout -dates

# 5. 验证证书和私钥匹配
openssl x509 -noout -modulus -in /etc/ssl/certs/mrgun.chu-jiao.com.pem | openssl md5
openssl rsa -noout -modulus -in /etc/ssl/private/mrgun.chu-jiao.com.key | openssl md5
# 两个 MD5 值应该相同
```

### 在线验证工具

- **SSL Labs**：https://www.ssllabs.com/ssltest/
  - 输入域名：mrgun.chu-jiao.com
  - 查看 SSL 评分（目标 A 或 A+）

- **SSL Checker**：https://www.sslshopper.com/ssl-checker.html
  - 检查证书链完整性

---

## 📝 日志查看

```bash
# Nginx 访问日志
sudo tail -f /var/log/nginx/mrgun_access.log

# Nginx 错误日志
sudo tail -f /var/log/nginx/mrgun_error.log

# Nginx 主错误日志
sudo tail -f /var/log/nginx/error.log

# 系统日志
sudo journalctl -u nginx -f
```

---

## 🔄 恢复备份

如果配置出错，恢复备份：

```bash
# 查看备份文件
ls -la /etc/nginx/sites-available/*.backup*

# 恢复备份（替换 YYYYMMDD 为实际日期）
sudo cp /etc/nginx/sites-available/default.backup.YYYYMMDD /etc/nginx/sites-available/default

# 重新加载
sudo nginx -s reload
```

---

## 📞 需要帮助？

如果遇到问题，收集以下信息：

```bash
# 1. 系统信息
cat /etc/os-release

# 2. Nginx 版本
nginx -v

# 3. 证书文件状态
ls -la /etc/ssl/certs/mrgun.chu-jiao.com.pem
ls -la /etc/ssl/private/mrgun.chu-jiao.com.key

# 4. Nginx 配置测试
sudo nginx -t 2>&1

# 5. 端口监听状态
sudo netstat -tuln | grep -E ':80|:443'

# 6. Nginx 错误日志
sudo tail -50 /var/log/nginx/error.log

# 7. 防火墙状态
sudo ufw status
# 或
sudo firewall-cmd --list-all
```

---

## 🎯 快速命令参考

```bash
# 测试 Nginx 配置
sudo nginx -t

# 重新加载 Nginx（不中断服务）
sudo nginx -s reload

# 重启 Nginx
sudo systemctl restart nginx

# 查看 Nginx 状态
sudo systemctl status nginx

# 启用 Nginx 开机自启
sudo systemctl enable nginx

# 查看端口监听
sudo netstat -tuln | grep :443

# 测试 HTTPS
curl -I https://mrgun.chu-jiao.com

# 查看证书信息
openssl x509 -in /etc/ssl/certs/mrgun.chu-jiao.com.pem -noout -text

# 查看证书过期时间
openssl x509 -in /etc/ssl/certs/mrgun.chu-jiao.com.pem -noout -dates
```

---

**祝部署顺利！** 🎉
