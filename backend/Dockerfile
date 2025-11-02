# =============================================================================
# Multi-stage Dockerfile for Production
# =============================================================================
# 阶段1: 构建阶段 - 编译依赖
# 阶段2: 运行阶段 - 最小化镜像
# 优化: 使用国内镜像源加速下载
# =============================================================================

# ============== 阶段1: 构建阶段 ==============
FROM python:3.12-slim AS builder

# 使用阿里云镜像源加速apt (Debian 12 Bookworm)
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# 设置工作目录
WORKDIR /app

# 配置pip使用清华镜像加速
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖到特定目录
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============== 阶段2: 运行阶段 ==============
FROM python:3.12-slim

# 使用阿里云镜像源
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# 配置pip使用清华镜像（运行阶段也需要）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 构建参数
ARG BUILD_DATE
ARG VERSION

# 元数据标签
LABEL maintainer="MR Game Ops Team" \
      version="${VERSION}" \
      build_date="${BUILD_DATE}" \
      description="MR Game Ops Backend Service - Production"

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/usr/local/bin:$PATH" \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

# 创建非root用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 从构建阶段复制Python包
COPY --from=builder /install /usr/local

# 复制应用代码
COPY --chown=appuser:appuser . .

# 创建必要的目录
RUN mkdir -p /app/logs /app/uploads /app/invoices && \
    chown -R appuser:appuser /app/logs /app/uploads /app/invoices

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--log-level", "warning"]
