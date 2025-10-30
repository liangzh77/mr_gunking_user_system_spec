#!/bin/bash
set -e

# 颜色定义
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo -e "  MR游戏运营管理系统 - 离线部署"
echo -e "==========================================${NC}"
echo ""

# ============================================================================
# 步骤1: 加载Docker镜像
# ============================================================================
echo -e "${YELLOW}[1/6] 加载Docker镜像...${NC}"
IMAGES_DIR="/root/docker-images"

if [ ! -d "$IMAGES_DIR" ]; then
    echo -e "${RED}错误: 镜像目录 $IMAGES_DIR 不存在${NC}"
    exit 1
fi

# 必需的镜像文件
REQUIRED_IMAGES=(
    "postgres-14-alpine.tar"
    "redis-7-alpine.tar"
    "python-3.12-slim.tar"
    "node-18-alpine.tar"
    "nginx-alpine.tar"
)

LOADED=0
FAILED=0

for img in "${REQUIRED_IMAGES[@]}"; do
    IMG_PATH="$IMAGES_DIR/$img"
    if [ -f "$IMG_PATH" ]; then
        echo -n "  加载: $img ... "
        if docker load -i "$IMG_PATH" > /dev/null 2>&1; then
            echo -e "${GREEN}✓${NC}"
            LOADED=$((LOADED + 1))
        else
            echo -e "${RED}✗${NC}"
            FAILED=$((FAILED + 1))
        fi
    else
        echo -e "  ${RED}✗ 文件不存在: $img${NC}"
        FAILED=$((FAILED + 1))
    fi
done

if [ $FAILED -gt 0 ]; then
    echo -e "${RED}错误: 有 $FAILED 个镜像加载失败${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 成功加载 $LOADED/${#REQUIRED_IMAGES[@]} 个镜像${NC}"
echo ""

# 显示已加载的镜像
echo "已加载的镜像:"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep -E "postgres|redis|python|node|nginx|REPOSITORY"
echo ""

# ============================================================================
# 步骤2: 检查项目目录
# ============================================================================
echo -e "${YELLOW}[2/6] 检查项目环境...${NC}"

if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}错误: 未找到 docker-compose.yml${NC}"
    echo "请确保在项目根目录 /opt/mr_gunking_user_system_spec 执行此脚本"
    exit 1
fi

echo -e "${GREEN}✓ 项目目录正确${NC}"
echo ""

# ============================================================================
# 步骤3: 配置环境变量
# ============================================================================
echo -e "${YELLOW}[3/6] 配置环境变量...${NC}"

if [ ! -f ".env.production" ]; then
    echo -e "${YELLOW}未找到 .env.production 配置文件${NC}"

    if [ -f "configure_env.sh" ]; then
        echo "发现自动配置脚本"
        read -p "是否运行自动配置? (y/n): " run_config
        if [ "$run_config" = "y" ]; then
            ./configure_env.sh
        else
            echo ""
            echo "请手动配置:"
            echo "  1. cp .env.production.template .env.production"
            echo "  2. nano .env.production"
            echo "  3. 修改必要的配置项"
            exit 1
        fi
    else
        echo -e "${RED}请先创建配置文件${NC}"
        echo "  1. cp .env.production.template .env.production"
        echo "  2. nano .env.production"
        exit 1
    fi
fi

echo -e "${GREEN}✓ 配置文件已就绪${NC}"
echo ""

# ============================================================================
# 步骤4: 停止旧服务
# ============================================================================
echo -e "${YELLOW}[4/6] 检查并停止旧服务...${NC}"

if docker-compose -f docker-compose.yml ps -q 2>/dev/null | grep -q .; then
    echo "发现运行中的服务,正在停止..."
    docker-compose -f docker-compose.yml down
    echo -e "${GREEN}✓ 旧服务已停止${NC}"
else
    echo "没有运行中的服务"
fi
echo ""

# ============================================================================
# 步骤5: 构建应用镜像
# ============================================================================
echo -e "${YELLOW}[5/6] 构建应用镜像...${NC}"
echo "这可能需要5-10分钟,请耐心等待..."
echo ""

# 设置构建参数
export BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
export VERSION="1.0.0"

# 构建后端
echo -e "${BLUE}构建后端服务...${NC}"
if docker-compose -f docker-compose.yml build --no-cache backend; then
    echo -e "${GREEN}✓ 后端构建成功${NC}"
else
    echo -e "${RED}✗ 后端构建失败${NC}"
    echo "请查看错误信息并修复"
    exit 1
fi
echo ""

# 构建前端
echo -e "${BLUE}构建前端服务...${NC}"
if docker-compose -f docker-compose.yml build --no-cache frontend; then
    echo -e "${GREEN}✓ 前端构建成功${NC}"
else
    echo -e "${RED}✗ 前端构建失败${NC}"
    echo "请查看错误信息并修复"
    exit 1
fi
echo ""

# ============================================================================
# 步骤6: 启动所有服务
# ============================================================================
echo -e "${YELLOW}[6/6] 启动服务...${NC}"

if docker-compose -f docker-compose.yml up -d; then
    echo -e "${GREEN}✓ 服务启动成功${NC}"
else
    echo -e "${RED}✗ 服务启动失败${NC}"
    echo "查看日志: docker-compose -f docker-compose.yml logs"
    exit 1
fi
echo ""

# 等待服务就绪
echo -e "${YELLOW}等待服务启动(30秒)...${NC}"
for i in {30..1}; do
    echo -ne "\r剩余: $i 秒  "
    sleep 1
done
echo ""
echo ""

# ============================================================================
# 显示部署结果
# ============================================================================
echo -e "${BLUE}=========================================="
echo -e "  部署完成!"
echo -e "==========================================${NC}"
echo ""

# 获取服务器IP
SERVER_IP=$(hostname -I | awk '{print $1}')

# 显示服务状态
echo -e "${YELLOW}服务状态:${NC}"
docker-compose -f docker-compose.yml ps
echo ""

# 显示访问信息
echo -e "${GREEN}=========================================="
echo -e "  访问信息"
echo -e "==========================================${NC}"
echo ""
echo "前端地址:   http://$SERVER_IP"
echo "后端API:    http://$SERVER_IP:8000"
echo "健康检查:   http://$SERVER_IP:8000/health"
echo "API文档:    http://$SERVER_IP:8000/docs"
echo ""

# 测试健康检查
echo -e "${YELLOW}测试服务健康状态...${NC}"
sleep 5

if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
    HEALTH_STATUS=$(curl -s http://localhost:8000/health)
    echo -e "${GREEN}✓ 后端服务运行正常${NC}"
    echo "  $HEALTH_STATUS"
else
    echo -e "${RED}✗ 后端服务可能未就绪${NC}"
    echo "  请稍后访问或查看日志"
fi
echo ""

# 显示管理命令
echo -e "${GREEN}=========================================="
echo -e "  常用管理命令"
echo -e "==========================================${NC}"
echo ""
echo "查看所有日志:"
echo "  docker-compose -f docker-compose.yml logs -f"
echo ""
echo "查看后端日志:"
echo "  docker-compose -f docker-compose.yml logs -f backend"
echo ""
echo "查看前端日志:"
echo "  docker-compose -f docker-compose.yml logs -f frontend"
echo ""
echo "重启服务:"
echo "  docker-compose -f docker-compose.yml restart"
echo ""
echo "停止服务:"
echo "  docker-compose -f docker-compose.yml down"
echo ""
echo "查看容器状态:"
echo "  docker-compose -f docker-compose.yml ps"
echo ""

# 保存部署信息
DEPLOY_INFO="DEPLOY_INFO.txt"
cat > "$DEPLOY_INFO" << INFO_EOF
========================================
  MR游戏运营管理系统 - 部署信息
========================================
部署时间: $(date)
部署方式: 离线部署
服务器IP: $SERVER_IP
版本: $VERSION

访问地址:
  前端:     http://$SERVER_IP
  后端API:  http://$SERVER_IP:8000
  健康检查: http://$SERVER_IP:8000/health
  API文档:  http://$SERVER_IP:8000/docs

服务列表:
$(docker-compose -f docker-compose.yml ps)

管理命令:
  查看日志: docker-compose -f docker-compose.yml logs -f
  重启服务: docker-compose -f docker-compose.yml restart
  停止服务: docker-compose -f docker-compose.yml down
  服务状态: docker-compose -f docker-compose.yml ps

配置文件:
  环境配置: .env.production
  Docker配置: docker-compose.yml

数据备份:
  数据库备份: docker exec mr_game_ops_db_prod pg_dump -U mr_admin mr_game_ops > backup.sql

========================================
INFO_EOF

echo -e "${GREEN}部署信息已保存到: $DEPLOY_INFO${NC}"
echo ""

