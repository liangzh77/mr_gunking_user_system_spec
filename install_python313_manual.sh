#!/bin/bash

# =============================================================================
# 手动安装Python 3.13脚本（用于生产服务器）
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

log_info "开始手动安装Python 3.13..."

# 安装编译依赖
log_info "安装编译依赖..."
apt-get update
apt-get install -y gcc openssl-devel bzip2-devel libffi-devel zlib-devel \
    readline-devel sqlite-devel wget build-essential checkinstall

# 下载Python 3.13.7
cd /tmp
log_info "下载Python 3.13.7..."
wget https://www.python.org/ftp/python/3.13.7/Python-3.13.7.tgz

# 解压
log_info "解压Python源码..."
tar xzf Python-3.13.7.tgz
cd Python-3.13.7

# 配置编译选项
log_info "配置编译选项..."
./configure --enable-optimizations --prefix=/usr/local/python3.13

# 编译（使用所有CPU核心）
log_info "编译Python 3.13（这需要一些时间）..."
make -j$(nproc)

# 安装
log_info "安装Python 3.13..."
make altinstall

# 创建系统链接
log_info "创建系统命令链接..."
update-alternatives --install /usr/bin/python3 python3 /usr/local/python3.13/bin/python3.13 1
update-alternatives --install /usr/bin/python python /usr/local/python3.13/bin/python3.13 1

# 验证安装
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if [[ "$PYTHON_VERSION" == "3.13" ]]; then
    log_success "Python 3.13安装成功！版本: $PYTHON_VERSION"
else
    log_error "Python 3.13安装失败，当前版本: $PYTHON_VERSION"
    exit 1
fi

# 清理临时文件
log_info "清理临时文件..."
cd /opt/mr_gunking_user_system_spec
rm -rf /tmp/Python-3.13.7*

log_success "Python 3.13手动安装完成！"
log_info "现在可以运行: sudo ./start_services_direct.sh"