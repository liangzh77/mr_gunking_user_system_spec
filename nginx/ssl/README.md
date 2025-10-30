# SSL证书目录

此目录用于存放SSL/TLS证书文件。

## 文件说明

生产环境需要放置以下文件：
- `fullchain.pem` - 完整证书链（包含证书和中间证书）
- `privkey.pem` - 私钥文件

## 获取证书

### 方式1：Let's Encrypt（推荐，免费）

```bash
# 安装Certbot
sudo apt install -y certbot

# 获取证书
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# 证书位置
# /etc/letsencrypt/live/yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/yourdomain.com/privkey.pem

# 复制到此目录
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem .
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem .
```

### 方式2：购买商业证书

从CA机构购买证书后，将证书文件重命名并放置到此目录。

### 方式3：自签名证书（仅测试）

```bash
# 生成自签名证书（有效期365天）
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout privkey.pem \
    -out fullchain.pem \
    -subj "/C=CN/ST=Beijing/L=Beijing/O=YourCompany/CN=yourdomain.com"
```

## 证书更新

Let's Encrypt证书有效期90天，需要定期更新：

```bash
# 测试自动更新
sudo certbot renew --dry-run

# 手动更新
sudo certbot renew

# 设置自动更新（添加到crontab）
0 2 * * * /usr/bin/certbot renew --quiet && docker-compose -f /path/to/docker-compose.yml restart nginx
```

## 安全注意事项

1. **私钥保护**：`privkey.pem` 文件必须设置严格权限
   ```bash
   chmod 600 privkey.pem
   chown root:root privkey.pem
   ```

2. **Git忽略**：此目录已在 `.gitignore` 中，证书文件不会被提交到版本控制

3. **备份**：定期备份证书文件到安全位置

4. **监控过期**：证书过期前30天开始提醒

## 验证证书

```bash
# 检查证书有效期
openssl x509 -in fullchain.pem -noout -dates

# 检查证书信息
openssl x509 -in fullchain.pem -noout -text

# 验证私钥和证书匹配
openssl x509 -noout -modulus -in fullchain.pem | openssl md5
openssl rsa -noout -modulus -in privkey.pem | openssl md5
# 两个MD5值应该相同
```

## 故障排查

### 证书不匹配

错误：`SSL: error:0B080074:x509 certificate routines`

解决：确保 `fullchain.pem` 和 `privkey.pem` 来自同一次证书申请

### 证书过期

错误：`certificate has expired`

解决：运行 `certbot renew` 更新证书

### 浏览器不信任

原因：
- 使用自签名证书
- 证书链不完整
- 域名不匹配

解决：使用Let's Encrypt或购买商业证书
