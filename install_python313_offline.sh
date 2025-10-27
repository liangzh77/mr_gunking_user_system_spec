#!/bin/bash

# =============================================================================
# 离线安装Python 3.13脚本（不依赖apt包管理器）
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

log_info "开始离线安装Python 3.13..."

# 检查必要的编译工具是否存在
log_info "检查编译环境..."

# 检查gcc
if ! command -v gcc &> /dev/null; then
    log_error "gcc未安装，请先手动安装gcc"
    log_info "可以尝试: apt-get install gcc (如果apt可用)"
    exit 1
fi

# 检查make
if ! command -v make &> /dev/null; then
    log_error "make未安装，请先手动安装make"
    log_info "可以尝试: apt-get install make (如果apt可用)"
    exit 1
fi

log_success "编译环境检查通过"

# 下载Python 3.13.7
cd /tmp
log_info "下载Python 3.13.7源码..."

# 如果wget不可用，尝试curl
if command -v wget &> /dev/null; then
    wget https://www.python.org/ftp/python/3.13.7/Python-3.13.7.tgz
elif command -v curl &> /dev/null; then
    curl -O https://www.python.org/ftp/python/3.13.7/Python-3.13.7.tgz
else
    log_error "需要wget或curl来下载Python源码"
    exit 1
fi

# 解压
log_info "解压Python源码..."
tar xzf Python-3.13.7.tgz
cd Python-3.13.7

# 配置编译选项（最小依赖）
log_info "配置编译选项..."
./configure --enable-optimizations --prefix=/usr/local/python3.13 \
    --with-ensurepip=install \
    --enable-loadable-sqlite-extensions \
    --with-openssl=/usr/lib/ssl

# 编译（使用所有CPU核心）
log_info "编译Python 3.13（这需要一些时间，请耐心等待）..."
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

    # 验证pip是否可用
    if /usr/local/python3.13/bin/python3.13 -m pip --version &> /dev/null; then
        log_success "pip也安装成功！"
    else
        log_warning "pip可能需要手动安装"
    fi
else
    log_error "Python 3.13安装失败，当前版本: $PYTHON_VERSION"
    exit 1
fi

# 创建软链接以便直接使用pip3
ln -sf /usr/local/python3.13/bin/python3.13 /usr/local/bin/python3.13
ln -sf /usr/local/python3.13/bin/pip3.13 /usr/local/bin/pip3.13

# 清理临时文件
log_info "清理临时文件..."
cd /opt/mr_gunking_user_system_spec
rm -rf /tmp/Python-3.13.7*

log_success "Python 3.13离线安装完成！"
log_info "现在可以运行: sudo ./start_services_direct.sh"
log_info "验证命令: python3 --version 和 pip3 --version"