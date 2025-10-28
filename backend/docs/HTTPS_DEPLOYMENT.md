# HTTPS 部署指南

本文档说明如何在生产环境中配置 HTTPS 和 TLS 1.3。

## 概述

系统使用以下安全策略：
- **HTTPS 强制重定向**: 通过反向代理 (Nginx/CloudFlare) 处理
- **安全响应头**: 由应用中间件自动添加
- **TLS 1.3**: 推荐配置，向下兼容 TLS 1.2

## 架构

```
[客户端] --HTTPS--> [Nginx/CloudFlare] --HTTP--> [FastAPI App]
                          ↓
                    TLS 终止点
                    HTTPS 重定向
```

---

## 1. Nginx 反向代理配置

### 完整配置示例

创建 `/etc/nginx/sites-available/mr-game-ops.conf`:

```nginx
# HTTP -> HTTPS 重定向
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com www.yourdomain.com;

    # ACME challenge for Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS 服务器
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL 证书 (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # TLS 1.3 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';

    # SSL session cache
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/yourdomain.com/chain.pem;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;

    # Security headers (backup - app also sets these)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # 上传文件大小限制
    client_max_body_size 10M;

    # 代理到 FastAPI 应用
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        # Proxy headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;

        # WebSocket support (if needed)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 静态文件 (如果有)
    location /static/ {
        alias /var/www/mr-game-ops/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API 文档 (仅在非生产环境)
    # location /api/docs {
    #     deny all;
    # }

    # 健康检查 (不需要 HTTPS)
    location /health {
        proxy_pass http://127.0.0.1:8000;
        access_log off;
    }
}
```

### 启用配置

```bash
# 创建符号链接
sudo ln -s /etc/nginx/sites-available/mr-game-ops.conf /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重新加载 Nginx
sudo systemctl reload nginx
```

---

## 2. 获取 SSL 证书 (Let's Encrypt)

### 安装 Certbot

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install certbot python3-certbot-nginx

# CentOS/RHEL
sudo yum install certbot python3-certbot-nginx
```

### 自动获取证书

```bash
# 自动配置 (推荐)
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# 手动配置
sudo certbot certonly --webroot -w /var/www/certbot \
    -d yourdomain.com -d www.yourdomain.com
```

### 自动续期

```bash
# 测试续期
sudo certbot renew --dry-run

# 添加 cron job
echo "0 0,12 * * * root python3 -c 'import random; import time; time.sleep(random.random() * 3600)' && certbot renew -q" | sudo tee -a /etc/crontab > /dev/null
```

---

## 3. CloudFlare 配置 (可选)

如果使用 CloudFlare 作为 CDN/WAF:

### 3.1 SSL/TLS 模式

CloudFlare Dashboard → SSL/TLS → Overview:
- 选择 **"Full (strict)"** 模式
- 确保 CloudFlare 到源服务器也使用 HTTPS

### 3.2 最低 TLS 版本

CloudFlare Dashboard → SSL/TLS → Edge Certificates:
- Minimum TLS Version: **TLS 1.2**
- TLS 1.3: **启用**

### 3.3 Always Use HTTPS

CloudFlare Dashboard → SSL/TLS → Edge Certificates:
- Always Use HTTPS: **启用**

### 3.4 HSTS

CloudFlare Dashboard → SSL/TLS → Edge Certificates:
- Enable HSTS: **启用**
- Max Age: **12 months**
- Include subdomains: **启用**
- Preload: **启用**

---

## 4. 应用配置

### 环境变量

```bash
# .env
ENVIRONMENT=production
DEBUG=False

# CORS origins (使用 HTTPS)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### 验证安全头

应用自动添加以下安全响应头：

| Header | Value | 作用 |
|--------|-------|------|
| Strict-Transport-Security | max-age=31536000; includeSubDomains; preload | 强制 HTTPS 1年 |
| X-Content-Type-Options | nosniff | 防止 MIME 嗅探 |
| X-Frame-Options | DENY | 防止点击劫持 |
| X-XSS-Protection | 1; mode=block | 启用 XSS 过滤 |
| Content-Security-Policy | (见代码) | 限制资源加载 |
| Referrer-Policy | strict-origin-when-cross-origin | 控制 Referrer |
| Permissions-Policy | (见代码) | 禁用危险功能 |

---

## 5. 测试与验证

### 5.1 测试 HTTPS 重定向

```bash
# 应该返回 301 重定向
curl -I http://yourdomain.com

# 应该返回 200 OK
curl -I https://yourdomain.com
```

### 5.2 测试 TLS 配置

```bash
# 使用 testssl.sh
./testssl.sh https://yourdomain.com

# 使用 nmap
nmap --script ssl-enum-ciphers -p 443 yourdomain.com
```

### 5.3 在线 SSL 测试

访问以下服务测试 SSL 配置：

1. **SSL Labs**: https://www.ssllabs.com/ssltest/
   - 目标评分: **A+**

2. **Security Headers**: https://securityheaders.com/
   - 目标评分: **A+**

3. **Mozilla Observatory**: https://observatory.mozilla.org/
   - 目标评分: **A+**

### 5.4 验证安全头

```bash
# 检查响应头
curl -I https://yourdomain.com/health

# 应该看到所有安全头
```

---

## 6. 性能优化

### 6.1 启用 HTTP/2

Nginx 配置已包含 `http2` 指令：
```nginx
listen 443 ssl http2;
```

### 6.2 启用 OCSP Stapling

已在 Nginx 配置中启用，减少客户端 OCSP 查询。

### 6.3 调整 SSL Session Cache

```nginx
# 适当增大缓存以提升性能
ssl_session_cache shared:SSL:20m;
ssl_session_timeout 1h;
```

---

## 7. 故障排查

### 问题 1: 重定向循环

**症状**: 浏览器报告 "Too many redirects"

**原因**: Nginx 和应用都在做 HTTPS 重定向

**解决**:
- 检查应用使用 `SecurityHeadersMiddleware`（不做重定向）
- 确保 Nginx 正确设置 `X-Forwarded-Proto`

### 问题 2: Mixed Content 警告

**症状**: 浏览器控制台显示 "Mixed Content" 警告

**原因**: HTTPS 页面加载 HTTP 资源

**解决**:
- 确保所有 API 调用使用 HTTPS
- 更新前端代码，使用相对 URL 或 HTTPS URL

### 问题 3: 证书过期

**症状**: 浏览器显示证书无效

**解决**:
```bash
# 检查证书有效期
sudo certbot certificates

# 手动续期
sudo certbot renew
```

---

## 8. 最佳实践

✅ **必须做:**
1. 使用 TLS 1.2+ (推荐 TLS 1.3)
2. 启用 HSTS (至少 6 个月)
3. 定期更新 SSL 证书
4. 禁用弱加密套件
5. 启用 OCSP Stapling

✅ **建议做:**
1. 启用 HTTP/2 或 HTTP/3
2. 使用 CloudFlare WAF
3. 实施 CAA DNS 记录
4. 监控证书过期时间
5. 定期运行 SSL 扫描

❌ **不要做:**
1. 使用自签名证书（生产环境）
2. 支持 TLS 1.0/1.1
3. 使用弱密码套件
4. 忽略证书过期警告
5. 在代码中硬编码 SSL 证书路径

---

## 9. 合规性

### GDPR / CCPA
- ✅ 传输加密 (HTTPS)
- ✅ 数据保护

### PCI DSS (如果处理支付)
- ✅ TLS 1.2+
- ✅ 强加密套件
- ✅ 安全响应头

### SOC 2
- ✅ 传输层安全
- ✅ 访问控制

---

## 10. 监控与告警

建议监控以下指标：

```bash
# 证书过期时间
*/6 * * * * /usr/local/bin/check_cert_expiry.sh

# SSL 配置评分
0 0 * * 0 /usr/local/bin/ssl_labs_scan.sh

# 安全头检查
0 0 * * * /usr/local/bin/check_security_headers.sh
```

---

## 参考资源

- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [OWASP Transport Layer Protection](https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html)
- [Nginx SSL Optimization](https://nginx.org/en/docs/http/configuring_https_servers.html)
