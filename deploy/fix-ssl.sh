#!/bin/bash

# ============================================================================
# SSL 证书诊断和修复脚本
# 域名: mrgun.chu-jiao.com
# 使用方法: sudo bash fix-ssl.sh
# ============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

print_header "SSL 证书诊断和修复工具"

# ============================================================================
# 第一部分：诊断
# ============================================================================

print_header "第一步：系统诊断"

# 1. 检查证书文件
echo "1️⃣ 检查证书文件..."
CERT_OK=true
if [ -f "/etc/ssl/certs/mrgun.chu-jiao.com.pem" ]; then
    print_success "证书文件存在"
    ls -la /etc/ssl/certs/mrgun.chu-jiao.com.pem
else
    print_error "证书文件不存在: /etc/ssl/certs/mrgun.chu-jiao.com.pem"
    CERT_OK=false
fi

if [ -f "/etc/ssl/private/mrgun.chu-jiao.com.key" ]; then
    print_success "私钥文件存在"
    ls -la /etc/ssl/private/mrgun.chu-jiao.com.key
else
    print_error "私钥文件不存在: /etc/ssl/private/mrgun.chu-jiao.com.key"
    CERT_OK=false
fi

if [ "$CERT_OK" = false ]; then
    print_error "证书文件缺失，无法继续"
    exit 1
fi

echo ""

# 2. 检查 Nginx 配置文件
echo "2️⃣ 检查 Nginx 配置文件..."
NGINX_CONF="/etc/nginx/sites-available/default"

if [ ! -f "$NGINX_CONF" ]; then
    print_error "Nginx 配置文件不存在"
    exit 1
fi

# 检查文件格式
FILE_TYPE=$(file "$NGINX_CONF" | grep -o "CRLF" || echo "")
if [ -n "$FILE_TYPE" ]; then
    print_warning "配置文件包含 Windows 换行符 (CRLF)"
    NEED_FIX=true
else
    print_success "配置文件格式正常"
    NEED_FIX=false
fi

# 检查是否包含 SSL 配置
if grep -q "listen 443" "$NGINX_CONF"; then
    print_success "配置文件包含 SSL 配置"
else
    print_error "配置文件不包含 SSL 配置"
    exit 1
fi

echo ""

# 3. 测试 Nginx 配置
echo "3️⃣ 测试 Nginx 配置..."
if nginx -t 2>&1 | grep -q "successful"; then
    print_success "Nginx 配置测试通过"
    CONFIG_OK=true
else
    print_error "Nginx 配置测试失败"
    echo "错误详情："
    nginx -t 2>&1
    CONFIG_OK=false
fi

echo ""

# 4. 检查 Nginx 运行状态
echo "4️⃣ 检查 Nginx 运行状态..."
if systemctl is-active --quiet nginx; then
    print_success "Nginx 正在运行"
    NGINX_RUNNING=true
else
    print_error "Nginx 未运行"
    NGINX_RUNNING=false
fi

echo ""

# 5. 检查端口监听
echo "5️⃣ 检查端口监听状态..."
echo "当前监听端口："
ss -tuln | grep -E ':80|:443' || echo "  无相关端口监听"

if ss -tuln | grep -q ":443"; then
    print_success "443 端口正在监听"
    PORT_443_OK=true
else
    print_warning "443 端口未监听 - 需要修复！"
    PORT_443_OK=false
fi

if ss -tuln | grep -q ":80"; then
    print_success "80 端口正在监听"
else
    print_warning "80 端口未监听"
fi

echo ""

# 6. 检查错误日志
echo "6️⃣ 查看最近的 Nginx 错误日志..."
if [ -f "/var/log/nginx/error.log" ]; then
    echo "最后 10 行错误日志："
    tail -10 /var/log/nginx/error.log | grep -v "^$" || echo "  (无错误日志)"
else
    print_warning "错误日志不存在"
fi

echo ""

# ============================================================================
# 第二部分：诊断总结
# ============================================================================

print_header "诊断总结"

echo "证书文件: $([ "$CERT_OK" = true ] && echo "✅" || echo "❌")"
echo "配置格式: $([ "$NEED_FIX" = false ] && echo "✅" || echo "⚠️  需要修复")"
echo "配置测试: $([ "$CONFIG_OK" = true ] && echo "✅" || echo "❌")"
echo "Nginx 运行: $([ "$NGINX_RUNNING" = true ] && echo "✅" || echo "❌")"
echo "443 端口: $([ "$PORT_443_OK" = true ] && echo "✅" || echo "❌ 需要修复")"

echo ""

# ============================================================================
# 第三部分：自动修复
# ============================================================================

if [ "$PORT_443_OK" = true ] && [ "$CONFIG_OK" = true ]; then
    print_header "诊断结果：一切正常！"

    echo "测试 HTTPS 连接："
    curl -I https://mrgun.chu-jiao.com 2>&1 | head -5

    echo ""
    print_success "SSL 已正确配置，无需修复"
    exit 0
fi

print_header "开始自动修复"

read -p "检测到问题，是否开始自动修复？(y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "用户取消修复"
    exit 0
fi

# 修复步骤 1：转换换行符
if [ "$NEED_FIX" = true ] || [ "$CONFIG_OK" = false ]; then
    echo ""
    echo "🔧 修复 1: 转换配置文件换行符..."

    # 转换临时配置文件
    if [ -f "/tmp/nginx-ssl.conf" ]; then
        sed -i 's/\r$//' /tmp/nginx-ssl.conf
        print_success "临时配置文件换行符已转换"
    fi

    # 转换当前配置文件
    sed -i 's/\r$//' "$NGINX_CONF"
    print_success "当前配置文件换行符已转换"
fi

# 修复步骤 2：重新拷贝配置（如果临时文件存在）
if [ -f "/tmp/nginx-ssl.conf" ]; then
    echo ""
    echo "🔧 修复 2: 重新拷贝配置文件..."

    # 备份当前配置
    cp "$NGINX_CONF" "${NGINX_CONF}.backup.$(date +%Y%m%d_%H%M%S)"
    print_success "已备份当前配置"

    # 拷贝新配置
    cp /tmp/nginx-ssl.conf "$NGINX_CONF"
    print_success "已拷贝新配置"
fi

# 修复步骤 3：重新测试配置
echo ""
echo "🔧 修复 3: 测试 Nginx 配置..."
if nginx -t 2>&1 | grep -q "successful"; then
    print_success "配置测试通过"
else
    print_error "配置测试仍然失败"
    echo "错误详情："
    nginx -t 2>&1

    echo ""
    print_error "自动修复失败，请手动检查以下内容："
    echo "1. 证书文件路径是否正确"
    echo "2. 配置文件语法是否正确"
    echo "3. 查看详细错误日志: sudo tail -50 /var/log/nginx/error.log"
    exit 1
fi

# 修复步骤 4：重启 Nginx
echo ""
echo "🔧 修复 4: 重启 Nginx..."
systemctl restart nginx

if systemctl is-active --quiet nginx; then
    print_success "Nginx 已成功重启"
else
    print_error "Nginx 重启失败"
    systemctl status nginx --no-pager
    exit 1
fi

# 等待 Nginx 完全启动
sleep 2

# 修复步骤 5: 验证修复结果
echo ""
echo "🔧 修复 5: 验证修复结果..."

echo ""
echo "端口监听状态："
ss -tuln | grep -E ':80|:443'

echo ""
if ss -tuln | grep -q ":443"; then
    print_success "443 端口现在正在监听！"
else
    print_error "443 端口仍未监听"

    echo ""
    print_error "可能的原因："
    echo "1. 配置文件中的证书路径不正确"
    echo "2. SELinux 阻止了 Nginx 读取证书"
    echo "3. 防火墙问题"

    echo ""
    echo "请运行以下命令检查："
    echo "  sudo nginx -t"
    echo "  sudo tail -50 /var/log/nginx/error.log"
    echo "  sudo setenforce 0  # 临时关闭 SELinux 测试"
    exit 1
fi

# ============================================================================
# 第四部分：最终验证
# ============================================================================

print_header "最终验证"

echo "1️⃣ 测试 HTTP 重定向..."
HTTP_RESULT=$(curl -I http://mrgun.chu-jiao.com 2>&1 | head -3)
echo "$HTTP_RESULT"
if echo "$HTTP_RESULT" | grep -q "301"; then
    print_success "HTTP 正确重定向到 HTTPS"
else
    print_warning "HTTP 重定向可能有问题"
fi

echo ""
echo "2️⃣ 测试 HTTPS 连接..."
HTTPS_RESULT=$(curl -I https://mrgun.chu-jiao.com 2>&1 | head -5)
echo "$HTTPS_RESULT"
if echo "$HTTPS_RESULT" | grep -q "HTTP"; then
    print_success "HTTPS 连接成功"
else
    print_warning "HTTPS 连接可能有问题"
fi

echo ""
echo "3️⃣ 检查 SSL 证书..."
CERT_CHECK=$(echo | openssl s_client -connect mrgun.chu-jiao.com:443 -servername mrgun.chu-jiao.com 2>/dev/null | grep "Verify return code")
echo "$CERT_CHECK"
if echo "$CERT_CHECK" | grep -q "0 (ok)"; then
    print_success "SSL 证书验证通过"
else
    print_warning "SSL 证书验证可能有问题（可能需要等待 DNS 生效）"
fi

echo ""
echo "4️⃣ 查看证书有效期..."
openssl x509 -in /etc/ssl/certs/mrgun.chu-jiao.com.pem -noout -dates

# ============================================================================
# 完成
# ============================================================================

print_header "🎉 修复完成！"

echo "接下来的操作："
echo ""
echo "1. 在浏览器访问："
echo "   https://mrgun.chu-jiao.com"
echo ""
echo "2. 检查浏览器地址栏是否显示 🔒 图标"
echo ""
echo "3. 如果还有问题，查看日志："
echo "   sudo tail -f /var/log/nginx/error.log"
echo ""
echo "4. 检查防火墙是否开放 443 端口："
echo "   sudo ufw allow 443/tcp"
echo "   # 或"
echo "   sudo firewall-cmd --permanent --add-service=https"
echo "   sudo firewall-cmd --reload"
echo ""
echo "5. 如果是云服务器，检查安全组规则是否允许 443 端口"
echo ""

print_success "脚本执行完成"
