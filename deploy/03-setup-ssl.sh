#!/bin/bash

# =============================================================================
# MR游戏运营管理系统 - SSL证书配置脚本
# =============================================================================
# 说明: 此脚本用于配置Let's Encrypt免费SSL证书
# 使用方法: ./03-setup-ssl.sh yourdomain.com
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查参数
check_args() {
    if [ $# -ne 1 ]; then
        log_error "使用方法: $0 yourdomain.com"
        exit 1
    fi

    DOMAIN=$1
    log_info "配置域名: $DOMAIN"
}

# 检查是否为root用户
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "请使用root用户运行此脚本"
        exit 1
    fi
}

# 安装Certbot
install_certbot() {
    if ! command -v certbot &> /dev/null; then
        log_info "安装Certbot..."
        apt update
        apt install -y certbot python3-certbot-nginx
        log_success "Certbot安装完成"
    else
        log_info "Certbot已安装"
    fi
}

# 生成SSL证书
generate_ssl() {
    log_info "为域名 $DOMAIN 生成SSL证书..."

    # 停止Nginx服务
    systemctl stop nginx || true
    docker stop mr_game_ops_nginx || true

    # 生成证书
    certbot certonly --standalone -d $DOMAIN --email admin@$DOMAIN --agree-tos --non-interactive

    if [ $? -eq 0 ]; then
        log_success "SSL证书生成成功"
    else
        log_error "SSL证书生成失败"
        exit 1
    fi
}

# 配置自动续期
setup_auto_renewal() {
    log_info "配置SSL证书自动续期..."

    # 添加cron任务
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet --post-hook 'systemctl reload nginx'") | crontab

    log_success "SSL证书自动续期配置完成"
}

# 更新Nginx配置
update_nginx_config() {
    log_info "更新Nginx配置..."

    # 更新nginx.conf中的域名
    sed -i "s/yourdomain.com/$DOMAIN/g" /opt/mr-game-ops/config/nginx/nginx.conf

    # 复制Let's Encrypt证书
    cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem /opt/mr-game-ops/config/ssl/cert.pem
    cp /etc/letsencrypt/live/$DOMAIN/privkey.pem /opt/mr-game-ops/config/ssl/key.pem

    # 设置正确的权限
    chmod 644 /opt/mr-game-ops/config/ssl/cert.pem
    chmod 600 /opt/mr-game-ops/config/ssl/key.pem

    log_success "Nginx配置更新完成"
}

# 重启服务
restart_services() {
    log_info "重启服务..."

    # 重启Docker容器
    cd /opt/mr-game-ops
    docker-compose -f docker-compose.prod.yml restart nginx

    # 启动系统Nginx
    systemctl start nginx
    systemctl enable nginx

    log_success "服务重启完成"
}

# 测试SSL证书
test_ssl() {
    log_info "测试SSL证书..."

    # 等待服务启动
    sleep 10

    # 测试证书
    if curl -sS https://$DOMAIN | grep -q "html"; then
        log_success "SSL证书测试通过"
    else
        log_error "SSL证书测试失败"
        return 1
    fi
}

# 显示配置信息
show_ssl_info() {
    log_success "🔒 SSL证书配置完成！"
    echo
    echo "==================================="
    echo "📋 SSL证书信息"
    echo "==================================="
    echo "🌐 域名: $DOMAIN"
    echo "📄 证书路径: /etc/letsencrypt/live/$DOMAIN/"
    echo "🔄 自动续期: 每天12:00检查"
    echo "🌐 HTTPS地址: https://$DOMAIN"
    echo
    echo "📝 证书管理命令:"
    echo "  查看证书: certbot certificates"
    echo "  续期证书: certbot renew"
    echo "  撤销证书: certbot revoke --cert-path /etc/letsencrypt/live/$DOMAIN/fullchain.pem"
    echo "==================================="
}

# 主函数
main() {
    log_info "🔒 开始配置SSL证书..."

    check_args "$@"
    check_root
    install_certbot
    generate_ssl
    setup_auto_renewal
    update_nginx_config
    restart_services

    if test_ssl; then
        show_ssl_info
    else
        log_error "SSL配置失败，请检查日志"
        exit 1
    fi
}

# 执行主函数
main "$@"