#!/bin/bash

# ============================================================================
# SSL 证书自动部署脚本
# 域名: mrgun.chu-jiao.com
# 使用方法: sudo bash deploy-ssl.sh
# ============================================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印函数
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

echo "========================================"
echo "  SSL 证书自动部署脚本"
echo "  域名: mrgun.chu-jiao.com"
echo "========================================"
echo ""

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then
    print_error "请使用 sudo 运行此脚本"
    exit 1
fi

# 步骤 1：检查证书文件是否存在
echo "步骤 1/7: 检查证书文件..."
if [ ! -f "/tmp/mrgun.chu-jiao.com.pem" ]; then
    print_error "证书文件不存在: /tmp/mrgun.chu-jiao.com.pem"
    echo "请先运行 Windows 批处理脚本上传证书文件"
    exit 1
fi

if [ ! -f "/tmp/mrgun.chu-jiao.com.key" ]; then
    print_error "私钥文件不存在: /tmp/mrgun.chu-jiao.com.key"
    echo "请先运行 Windows 批处理脚本上传私钥文件"
    exit 1
fi

if [ ! -f "/tmp/nginx-ssl.conf" ]; then
    print_error "Nginx 配置文件不存在: /tmp/nginx-ssl.conf"
    echo "请先运行 Windows 批处理脚本上传配置文件"
    exit 1
fi

print_success "所有文件检查通过"

# 步骤 2：创建目录
echo ""
echo "步骤 2/7: 创建证书目录..."
mkdir -p /etc/ssl/certs
mkdir -p /etc/ssl/private
print_success "目录创建成功"

# 步骤 3：移动证书文件
echo ""
echo "步骤 3/7: 移动证书文件..."

# 如果证书已存在，先备份
if [ -f "/etc/ssl/certs/mrgun.chu-jiao.com.pem" ]; then
    cp /etc/ssl/certs/mrgun.chu-jiao.com.pem /etc/ssl/certs/mrgun.chu-jiao.com.pem.backup.$(date +%Y%m%d_%H%M%S)
    print_warning "已备份旧证书文件"
fi

if [ -f "/etc/ssl/private/mrgun.chu-jiao.com.key" ]; then
    cp /etc/ssl/private/mrgun.chu-jiao.com.key /etc/ssl/private/mrgun.chu-jiao.com.key.backup.$(date +%Y%m%d_%H%M%S)
    print_warning "已备份旧私钥文件"
fi

# 移动文件
mv /tmp/mrgun.chu-jiao.com.pem /etc/ssl/certs/
mv /tmp/mrgun.chu-jiao.com.key /etc/ssl/private/
print_success "证书文件移动成功"

# 步骤 4：设置权限
echo ""
echo "步骤 4/7: 设置文件权限..."
chmod 644 /etc/ssl/certs/mrgun.chu-jiao.com.pem
chmod 600 /etc/ssl/private/mrgun.chu-jiao.com.key
chown root:root /etc/ssl/certs/mrgun.chu-jiao.com.pem
chown root:root /etc/ssl/private/mrgun.chu-jiao.com.key
print_success "权限设置成功"

# 验证权限
echo ""
echo "证书文件权限："
ls -la /etc/ssl/certs/mrgun.chu-jiao.com.pem
ls -la /etc/ssl/private/mrgun.chu-jiao.com.key

# 步骤 5：备份并替换 Nginx 配置
echo ""
echo "步骤 5/7: 备份并替换 Nginx 配置..."

# 检查 Nginx 配置文件位置
if [ -f "/etc/nginx/sites-available/default" ]; then
    NGINX_CONF="/etc/nginx/sites-available/default"
elif [ -f "/etc/nginx/conf.d/default.conf" ]; then
    NGINX_CONF="/etc/nginx/conf.d/default.conf"
else
    print_error "找不到 Nginx 配置文件"
    exit 1
fi

# 备份原配置
cp "$NGINX_CONF" "${NGINX_CONF}.backup.$(date +%Y%m%d_%H%M%S)"
print_success "已备份原 Nginx 配置: ${NGINX_CONF}.backup.$(date +%Y%m%d_%H%M%S)"

# 替换配置
cp /tmp/nginx-ssl.conf "$NGINX_CONF"
print_success "Nginx 配置已更新"

# 步骤 6：检查需要修改的配置
echo ""
echo "步骤 6/7: 检查配置..."
print_warning "请确认以下配置是否正确："
echo ""

# 检查前端路径
echo "📁 前端文件路径："
grep "root /var/www/mrgun;" "$NGINX_CONF" || echo "  (未找到默认配置)"

# 检查 FastAPI 端口
echo ""
echo "🔌 FastAPI 后端端口："
grep "proxy_pass http://127.0.0.1:" "$NGINX_CONF" | head -1 || echo "  (未找到)"

# 检查上传目录
echo ""
echo "📤 上传文件目录："
grep "alias /opt/mr-game-ops/data/uploads/" "$NGINX_CONF" || echo "  (未找到)"

echo ""
print_warning "如果上述路径不正确，请手动编辑配置文件："
echo "  sudo nano $NGINX_CONF"
echo ""

read -p "配置是否正确？继续部署请按回车，退出请按 Ctrl+C..."

# 步骤 7：测试并重启 Nginx
echo ""
echo "步骤 7/7: 测试并重启 Nginx..."

# 测试 Nginx 配置
if nginx -t; then
    print_success "Nginx 配置测试通过"
else
    print_error "Nginx 配置测试失败，请检查配置文件"
    print_info "恢复备份: cp ${NGINX_CONF}.backup.$(date +%Y%m%d)* $NGINX_CONF"
    exit 1
fi

# 开放防火墙端口
echo ""
echo "检查防火墙..."
if command -v ufw &> /dev/null; then
    ufw allow 80/tcp 2>/dev/null || true
    ufw allow 443/tcp 2>/dev/null || true
    print_success "已开放 80 和 443 端口 (ufw)"
elif command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-service=http 2>/dev/null || true
    firewall-cmd --permanent --add-service=https 2>/dev/null || true
    firewall-cmd --reload 2>/dev/null || true
    print_success "已开放 80 和 443 端口 (firewalld)"
else
    print_warning "未检测到防火墙，请手动开放 80 和 443 端口"
fi

# 重启 Nginx
echo ""
echo "重启 Nginx..."
if systemctl restart nginx; then
    print_success "Nginx 重启成功"
else
    print_error "Nginx 重启失败"
    exit 1
fi

# 确保 Nginx 开机自启
systemctl enable nginx 2>/dev/null || true

# 验证部署
echo ""
echo "========================================"
echo "  部署完成！开始验证..."
echo "========================================"
echo ""

# 检查端口监听
echo "🔍 检查端口监听状态："
if netstat -tuln | grep :443 &> /dev/null || ss -tuln | grep :443 &> /dev/null; then
    print_success "443 端口正在监听"
else
    print_error "443 端口未监听"
fi

if netstat -tuln | grep :80 &> /dev/null || ss -tuln | grep :80 &> /dev/null; then
    print_success "80 端口正在监听"
else
    print_error "80 端口未监听"
fi

# 检查证书
echo ""
echo "🔐 检查 SSL 证书："
if openssl s_client -connect localhost:443 -servername mrgun.chu-jiao.com </dev/null 2>/dev/null | grep "Verify return code: 0" &> /dev/null; then
    print_success "SSL 证书验证通过"
else
    print_warning "SSL 证书验证失败（可能需要等待 DNS 生效）"
fi

# 检查证书过期时间
echo ""
echo "📅 证书有效期："
openssl x509 -in /etc/ssl/certs/mrgun.chu-jiao.com.pem -noout -dates 2>/dev/null || print_error "无法读取证书日期"

echo ""
echo "========================================"
echo "  🎉 部署成功！"
echo "========================================"
echo ""
echo "接下来的步骤："
echo ""
echo "1. 在浏览器访问："
echo "   https://mrgun.chu-jiao.com"
echo ""
echo "2. 测试 HTTPS 连接："
echo "   curl -I https://mrgun.chu-jiao.com"
echo ""
echo "3. 测试 HTTP 重定向："
echo "   curl -I http://mrgun.chu-jiao.com"
echo ""
echo "4. 查看 Nginx 日志："
echo "   sudo tail -f /var/log/nginx/mrgun_access.log"
echo "   sudo tail -f /var/log/nginx/mrgun_error.log"
echo ""
echo "5. 查看 Nginx 状态："
echo "   sudo systemctl status nginx"
echo ""
print_info "如果遇到问题，查看部署文档: 部署SSL证书-说明.md"
echo ""
