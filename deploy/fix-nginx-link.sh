#!/bin/bash

# ============================================================================
# Nginx Sites-Enabled 软链接修复脚本
# 问题：sites-enabled/default 软链接不存在导致 SSL 配置未生效
# 解决：创建软链接并重启 Nginx
# ============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_header() {
    echo ""
    echo "========================================="
    echo -e "${BLUE}$1${NC}"
    echo "========================================="
    echo ""
}

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then
    print_error "请使用 sudo 运行此脚本"
    exit 1
fi

print_header "Nginx Sites-Enabled 软链接修复工具"

# ============================================================================
# 步骤 1: 诊断问题
# ============================================================================

print_header "步骤 1: 诊断当前状态"

echo "1️⃣ 检查配置文件..."
if [ -f "/etc/nginx/sites-available/default" ]; then
    print_success "sites-available/default 存在"
    ls -la /etc/nginx/sites-available/default
else
    print_error "sites-available/default 不存在"
    exit 1
fi

echo ""
echo "2️⃣ 检查 sites-enabled 目录..."
if [ -d "/etc/nginx/sites-enabled" ]; then
    print_success "sites-enabled 目录存在"
else
    print_warning "sites-enabled 目录不存在，将创建"
    mkdir -p /etc/nginx/sites-enabled
    print_success "sites-enabled 目录已创建"
fi

echo ""
echo "3️⃣ 检查软链接..."
if [ -L "/etc/nginx/sites-enabled/default" ]; then
    print_warning "软链接已存在，检查是否有效"
    if [ -e "/etc/nginx/sites-enabled/default" ]; then
        print_success "软链接有效"
        ls -la /etc/nginx/sites-enabled/default
        LINK_EXISTS=true
    else
        print_error "软链接已损坏，将重新创建"
        rm -f /etc/nginx/sites-enabled/default
        LINK_EXISTS=false
    fi
else
    print_error "软链接不存在"
    LINK_EXISTS=false
fi

echo ""
echo "4️⃣ 检查当前端口监听..."
echo "当前监听的端口："
ss -tuln | grep -E ':80|:443' || echo "  无 80/443 端口监听"

if ss -tuln | grep -q ":443"; then
    print_success "443 端口正在监听（无需修复）"
    PORT_OK=true
else
    print_warning "443 端口未监听（需要修复）"
    PORT_OK=false
fi

echo ""
echo "5️⃣ 检查 Nginx 配置是否包含 sites-enabled..."
if grep -q "include /etc/nginx/sites-enabled/\*" /etc/nginx/nginx.conf || \
   grep -q "include /etc/nginx/sites-enabled/\*;" /etc/nginx/nginx.conf; then
    print_success "主配置文件正确包含 sites-enabled"
else
    print_warning "主配置文件可能未包含 sites-enabled"
    echo "当前 include 配置："
    grep "include" /etc/nginx/nginx.conf | grep -v "^#"
fi

# ============================================================================
# 步骤 2: 判断是否需要修复
# ============================================================================

print_header "步骤 2: 诊断总结"

if [ "$LINK_EXISTS" = true ] && [ "$PORT_OK" = true ]; then
    print_success "软链接正常，443 端口正在监听"
    echo ""
    echo "测试 HTTPS 连接："
    curl -I https://mrgun.chu-jiao.com 2>&1 | head -5
    echo ""
    print_success "一切正常，无需修复！"
    exit 0
fi

echo "诊断结果："
echo "  软链接: $([ "$LINK_EXISTS" = true ] && echo "✅" || echo "❌ 需要修复")"
echo "  443端口: $([ "$PORT_OK" = true ] && echo "✅" || echo "❌ 需要修复")"

# ============================================================================
# 步骤 3: 执行修复
# ============================================================================

print_header "步骤 3: 开始自动修复"

echo "🔧 修复 1: 创建软链接..."
if [ -L "/etc/nginx/sites-enabled/default" ]; then
    echo "删除旧的软链接..."
    rm -f /etc/nginx/sites-enabled/default
fi

echo "创建新的软链接..."
ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

if [ -L "/etc/nginx/sites-enabled/default" ]; then
    print_success "软链接创建成功"
    ls -la /etc/nginx/sites-enabled/default
else
    print_error "软链接创建失败"
    exit 1
fi

echo ""
echo "🔧 修复 2: 测试 Nginx 配置..."
if nginx -t 2>&1 | grep -q "successful"; then
    print_success "Nginx 配置测试通过"
else
    print_error "Nginx 配置测试失败"
    echo "错误详情："
    nginx -t 2>&1
    exit 1
fi

echo ""
echo "🔧 修复 3: 重启 Nginx..."
systemctl restart nginx

if systemctl is-active --quiet nginx; then
    print_success "Nginx 已成功重启"
else
    print_error "Nginx 重启失败"
    systemctl status nginx --no-pager
    exit 1
fi

# 等待 Nginx 完全启动
echo "等待 Nginx 完全启动..."
sleep 3

# ============================================================================
# 步骤 4: 验证修复结果
# ============================================================================

print_header "步骤 4: 验证修复结果"

echo "1️⃣ 检查端口监听..."
echo "当前监听的端口："
ss -tuln | grep -E ':80|:443'

echo ""
if ss -tuln | grep -q ":443"; then
    print_success "✅ 443 端口现在正在监听！"
else
    print_error "❌ 443 端口仍未监听"

    echo ""
    print_error "修复失败，可能的原因："
    echo "1. 配置文件中的 SSL 部分有语法错误"
    echo "2. 证书文件路径不正确"
    echo "3. 主配置文件未包含 sites-enabled"

    echo ""
    echo "请检查以下内容："
    echo "  sudo nginx -T 2>&1 | grep 'listen 443'"
    echo "  sudo tail -50 /var/log/nginx/error.log"
    exit 1
fi

if ss -tuln | grep -q ":80"; then
    print_success "✅ 80 端口正在监听"
fi

echo ""
echo "2️⃣ 测试 HTTP 重定向..."
HTTP_TEST=$(curl -I http://mrgun.chu-jiao.com 2>&1 | head -3)
echo "$HTTP_TEST"
if echo "$HTTP_TEST" | grep -q "301"; then
    print_success "HTTP 正确重定向到 HTTPS"
else
    print_warning "HTTP 重定向可能有问题（需要等待 DNS 生效）"
fi

echo ""
echo "3️⃣ 测试 HTTPS 连接..."
HTTPS_TEST=$(curl -I https://mrgun.chu-jiao.com 2>&1 | head -5)
echo "$HTTPS_TEST"
if echo "$HTTPS_TEST" | grep -qE "HTTP/[12]"; then
    print_success "HTTPS 连接成功！"
else
    print_warning "HTTPS 连接可能有问题（需要等待 DNS 生效）"
fi

echo ""
echo "4️⃣ 检查 SSL 证书..."
CERT_INFO=$(echo | openssl s_client -connect mrgun.chu-jiao.com:443 -servername mrgun.chu-jiao.com 2>/dev/null | grep "Verify return code" || echo "连接测试...")
echo "$CERT_INFO"

echo ""
echo "5️⃣ 查看证书有效期..."
openssl x509 -in /etc/ssl/certs/mrgun.chu-jiao.com.pem -noout -dates

echo ""
echo "6️⃣ 查看实际加载的 SSL 配置..."
echo "Nginx 实际加载的 listen 443 配置："
sudo nginx -T 2>&1 | grep -E "listen.*443" | head -5

# ============================================================================
# 完成
# ============================================================================

print_header "🎉 修复完成！"

echo "修复总结："
echo "  ✅ 软链接已创建: /etc/nginx/sites-enabled/default"
echo "  ✅ Nginx 已重启"
echo "  ✅ 443 端口正在监听"
echo ""
echo "接下来的操作："
echo ""
echo "1. 在浏览器访问："
echo "   https://mrgun.chu-jiao.com"
echo ""
echo "2. 检查浏览器地址栏是否显示 🔒 图标"
echo ""
echo "3. 如果浏览器显示证书错误，可能是 DNS 未生效，等待 10-30 分钟"
echo ""
echo "4. 查看访问日志："
echo "   sudo tail -f /var/log/nginx/mrgun_access.log"
echo ""
echo "5. 如果还有问题，查看错误日志："
echo "   sudo tail -f /var/log/nginx/error.log"
echo ""
echo "6. 确保防火墙和云服务商安全组已开放 443 端口"
echo ""

print_success "脚本执行完成"
