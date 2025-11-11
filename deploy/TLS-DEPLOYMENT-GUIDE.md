# TLS 1.2+ 生产环境部署指南

## 📋 概述

本系统的 Nginx 配置已完全支持 **TLS 1.2 和 TLS 1.3**，符合以下安全标准：
- ✅ PCI DSS 3.2+ 合规
- ✅ GDPR 数据传输安全要求
- ✅ 国家信息安全等级保护要求

---

## 🔒 当前 TLS 配置

### 支持的协议版本
```nginx
ssl_protocols TLSv1.2 TLSv1.3;
```

- **TLS 1.2**: 最广泛支持，兼容 IE 11+、Android 4.4.2+、iOS 5+
- **TLS 1.3**: 最新标准，性能更好，安全性更高
- **禁用**: TLS 1.0/1.1（已过时且不安全）

### 密码套件（Cipher Suites）
```nginx
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';
```

**说明**：
- 所有密码套件都支持**前向保密（Forward Secrecy）**
- 优先使用 **AEAD 算法**（GCM、CHACHA20-POLY1305）
- 支持 **ECDHE** 和 **DHE** 密钥交换

---

## 🚀 生产环境部署步骤

### 1️⃣ 生成 SSL 证书

#### 方法 A：使用 Let's Encrypt（免费，推荐）

```bash
# 安装 Certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# 自动配置证书
sudo certbot --nginx -d mrgun.chu-jiao.com -d www.mrgun.chu-jiao.com

# 证书自动续期（Let's Encrypt 证书有效期 90 天）
sudo certbot renew --dry-run
```

#### 方法 B：使用阿里云/腾讯云证书

1. 在云平台控制台申请免费 SSL 证书（通常 1 年有效期）
2. 下载 Nginx 格式证书文件
3. 上传到服务器：
   ```bash
   /etc/nginx/ssl/mrgun.chu-jiao.com.crt  # 证书文件
   /etc/nginx/ssl/mrgun.chu-jiao.com.key  # 私钥文件
   /etc/nginx/ssl/chain.crt                # 中间证书链（可选）
   ```

#### 方法 C：使用商业证书（如 DigiCert、GlobalSign）

按照证书提供商的指南生成 CSR 并安装证书。

### 2️⃣ 生成 Diffie-Hellman 参数（增强安全性）

```bash
# 生成 2048 位 DH 参数（约 5 分钟）
sudo openssl dhparam -out /etc/nginx/ssl/dhparam.pem 2048

# 如需更高安全性，使用 4096 位（约 30 分钟）
# sudo openssl dhparam -out /etc/nginx/ssl/dhparam.pem 4096
```

### 3️⃣ 配置 Nginx

```bash
# 复制生产环境配置
sudo cp deploy/nginx-production.conf /etc/nginx/sites-available/mrgun

# 创建符号链接
sudo ln -s /etc/nginx/sites-available/mrgun /etc/nginx/sites-enabled/

# 删除默认配置
sudo rm /etc/nginx/sites-enabled/default

# 测试配置
sudo nginx -t

# 重新加载 Nginx
sudo systemctl reload nginx
```

### 4️⃣ 验证 TLS 配置

#### 在线检测工具
- **SSL Labs**: https://www.ssllabs.com/ssltest/
  - 期望评分：**A 或 A+**

#### 命令行测试
```bash
# 测试 TLS 1.2 连接
openssl s_client -connect mrgun.chu-jiao.com:443 -tls1_2

# 测试 TLS 1.3 连接
openssl s_client -connect mrgun.chu-jiao.com:443 -tls1_3

# 测试密码套件
nmap --script ssl-enum-ciphers -p 443 mrgun.chu-jiao.com
```

#### 浏览器测试
1. 访问 https://mrgun.chu-jiao.com
2. 点击地址栏左侧的锁图标
3. 查看证书详情，确认：
   - ✅ 证书有效
   - ✅ 使用 TLS 1.2 或 1.3
   - ✅ 密钥交换：ECDHE 或 DHE

---

## 🔧 Docker 环境配置

### 修改 docker-compose.yml

```yaml
nginx:
  image: nginx:1.25-alpine
  container_name: mr_game_ops_nginx
  ports:
    - "80:80"
    - "443:443"
  volumes:
    # 使用生产配置
    - ./deploy/nginx-production.conf:/etc/nginx/conf.d/default.conf:ro

    # SSL 证书（根据实际路径修改）
    - /etc/letsencrypt/live/mrgun.chu-jiao.com/fullchain.pem:/etc/nginx/ssl/mrgun.chu-jiao.com.crt:ro
    - /etc/letsencrypt/live/mrgun.chu-jiao.com/privkey.pem:/etc/nginx/ssl/mrgun.chu-jiao.com.key:ro
    - /etc/nginx/ssl/dhparam.pem:/etc/nginx/ssl/dhparam.pem:ro

    - nginx_logs:/var/log/nginx
  depends_on:
    - backend
    - frontend
  networks:
    - mr_network
  restart: unless-stopped
```

### 重启服务

```bash
docker-compose down
docker-compose up -d
```

---

## 📊 性能优化

### 1. 启用 HTTP/2
配置文件中已启用：
```nginx
listen 443 ssl http2;
```

### 2. OCSP Stapling
减少客户端证书验证时间：
```nginx
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
```

### 3. 会话复用
```nginx
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
```

---

## 🛡️ 安全加固

### 1. HSTS（强制 HTTPS）
```nginx
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
```

**说明**：
- `max-age=63072000`: 2 年有效期
- `includeSubDomains`: 包括所有子域名
- `preload`: 可提交到浏览器 HSTS 预加载列表

### 2. 禁用 API 文档（生产环境）
```nginx
location /docs {
    return 404;
}

location /redoc {
    return 404;
}
```

### 3. 内网访问限制
```nginx
location /metrics {
    allow 127.0.0.1;
    allow 172.16.0.0/12;
    deny all;

    proxy_pass http://backend:8000/metrics;
}
```

---

## 🧪 测试清单

部署后请完成以下测试：

- [ ] **SSL 证书有效**：浏览器无证书警告
- [ ] **TLS 1.2 可用**：`openssl s_client -tls1_2` 连接成功
- [ ] **TLS 1.3 可用**：`openssl s_client -tls1_3` 连接成功
- [ ] **TLS 1.1 禁用**：`openssl s_client -tls1_1` 连接失败
- [ ] **HTTP 重定向**：访问 http:// 自动跳转到 https://
- [ ] **HSTS 生效**：响应头包含 `Strict-Transport-Security`
- [ ] **SSL Labs 评分**：A 或 A+
- [ ] **功能测试**：登录、注册、短信验证码等功能正常
- [ ] **API 响应**：`curl -k https://mrgun.chu-jiao.com/health` 返回 200
- [ ] **静态资源**：前端页面正常加载

---

## 📱 客户端兼容性

### 支持的浏览器版本

| 浏览器 | 最低版本 | TLS 版本 |
|--------|---------|---------|
| Chrome | 30+ (2013) | TLS 1.2 |
| Firefox | 27+ (2014) | TLS 1.2 |
| Safari | 7+ (macOS 10.9) | TLS 1.2 |
| Edge | 全版本 | TLS 1.2 |
| IE | 11 (Windows 7+) | TLS 1.2 |
| iOS Safari | 5+ | TLS 1.2 |
| Android Chrome | 4.4.2+ | TLS 1.2 |

### 不支持的客户端
- ❌ IE 10 及更早版本
- ❌ Android 4.4.1 及更早版本
- ❌ Java 6/7（需升级到 Java 8+）
- ❌ OpenSSL 1.0.0 及更早版本

---

## 🔍 故障排查

### 问题 1：浏览器显示证书错误
**可能原因**：
- 证书文件路径错误
- 证书已过期
- 证书与域名不匹配

**解决方法**：
```bash
# 检查证书有效期
openssl x509 -in /etc/nginx/ssl/mrgun.chu-jiao.com.crt -noout -dates

# 检查证书域名
openssl x509 -in /etc/nginx/ssl/mrgun.chu-jiao.com.crt -noout -subject -ext subjectAltName

# 检查 Nginx 配置
sudo nginx -t
```

### 问题 2：TLS 握手失败
**可能原因**：
- 客户端不支持服务器的密码套件
- DH 参数文件缺失

**解决方法**：
```bash
# 检查 Nginx 错误日志
sudo tail -f /var/log/nginx/mrgun_error.log

# 生成 DH 参数
sudo openssl dhparam -out /etc/nginx/ssl/dhparam.pem 2048
```

### 问题 3：OCSP Stapling 失败
**可能原因**：
- 防火墙阻止 OCSP 请求
- DNS 解析器配置错误

**解决方法**：
```nginx
# 临时禁用 OCSP Stapling 测试
ssl_stapling off;
ssl_stapling_verify off;
```

---

## 📚 参考资料

- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [SSL Labs Best Practices](https://github.com/ssllabs/research/wiki/SSL-and-TLS-Deployment-Best-Practices)
- [OWASP Transport Layer Protection](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html)
- [PCI DSS Requirements](https://www.pcisecuritystandards.org/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)

---

## ✅ 总结

您的系统已经配置好 TLS 1.2/1.3 支持：

1. ✅ **已启用 TLS 1.2 和 TLS 1.3**
2. ✅ **已配置安全的密码套件**
3. ✅ **已禁用过时的 TLS 1.0/1.1**
4. ✅ **已添加安全头（HSTS、CSP 等）**
5. ✅ **已优化性能（HTTP/2、会话缓存）**

**下一步**：
- 获取正式 SSL 证书（Let's Encrypt 或商业证书）
- 生成 DH 参数文件
- 部署到生产服务器
- 运行安全测试（SSL Labs）

如有任何问题，请参考本文档的故障排查部分。
