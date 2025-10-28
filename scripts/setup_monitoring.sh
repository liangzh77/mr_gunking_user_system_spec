#!/bin/bash
# =============================================================================
# MR游戏运营管理系统 - 监控和日志收集配置脚本
# =============================================================================

set -e

echo "🚀 开始配置MR游戏运营管理系统监控和日志收集..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查是否为root用户
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_error "请不要以root用户运行此脚本"
        exit 1
    fi
}

# 创建必要的目录
create_directories() {
    print_info "创建监控和日志目录..."

    # 创建日志目录
    sudo mkdir -p /var/log/mr_game_ops/{backend,nginx,postgres,redis}
    sudo mkdir -p /var/log/mr_game_ops/archived

    # 创建监控目录
    sudo mkdir -p /opt/mr_game_ops/monitoring/{prometheus,grafana,alertmanager}
    sudo mkdir -p /opt/mr_game_ops/data/{prometheus,grafana,postgres,redis}

    # 创建备份目录
    sudo mkdir -p /var/backups/mr_game_ops/{daily,weekly,monthly}

    # 设置权限
    sudo chown -R $USER:$USER /var/log/mr_game_ops/archived
    sudo chown -R $USER:$USER /var/backups/mr_game_ops
    sudo chown -R $USER:$USER /opt/mr_game_ops

    print_success "目录创建完成"
}

# 安装Docker和Docker Compose
install_docker() {
    if command -v docker &> /dev/null; then
        print_info "Docker已安装，跳过..."
        return
    fi

    print_info "安装Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER

    print_info "安装Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose

    print_success "Docker安装完成"
}

# 配置日志轮转
setup_log_rotation() {
    print_info "配置日志轮转..."

    sudo tee /etc/logrotate.d/mr_game_ops > /dev/null <<EOF
/var/log/mr_game_ops/backend/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        docker kill -s USR1 mr_game_ops_backend_prod
    endscript
}

/var/log/mr_game_ops/nginx/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 nginx nginx
    postrotate
        docker kill -s USR1 mr_game_ops_nginx
    endscript
}

/var/log/mr_game_ops/postgres/*.log {
    weekly
    missingok
    rotate 4
    compress
    delaycompress
    notifempty
    create 644 postgres postgres
}

/var/log/mr_game_ops/redis/*.log {
    weekly
    missingok
    rotate 4
    compress
    delaycompress
    notifempty
    create 644 redis redis
}
EOF

    print_success "日志轮转配置完成"
}

# 配置Prometheus监控
setup_prometheus() {
    print_info "配置Prometheus监控..."

    mkdir -p monitoring/prometheus

    cat > monitoring/prometheus/prometheus.yml <<EOF
# Prometheus配置文件
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  # Prometheus自身监控
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # 应用监控
  - job_name: 'mr_game_ops_backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  # Nginx监控
  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:9113']
    scrape_interval: 10s

  # PostgreSQL监控
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
    scrape_interval: 10s

  # Redis监控
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
    scrape_interval: 10s

  # Node Exporter (系统监控)
  - job_name: 'node_exporter'
    static_configs:
      - targets: ['node-exporter:9100']
    scrape_interval: 10s
EOF

    cat > monitoring/prometheus/alert_rules.yml <<EOF
# Prometheus告警规则
groups:
  - name: mr_game_ops_alerts
    rules:
      # 高错误率告警
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "高错误率告警"
          description: "错误率超过10%: {{ $value }}"

      # 高响应时间告警
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "高响应时间告警"
          description: "95%响应时间超过1秒: {{ $value }}s"

      # 系统资源告警
      - alert: HighCPUUsage
        expr: 100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "高CPU使用率告警"
          description: "CPU使用率超过80%: {{ $value }}%"

      - alert: HighMemoryUsage
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 80
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "高内存使用率告警"
          description: "内存使用率超过80%: {{ $value }}%"

      - alert: HighDiskUsage
        expr: (node_filesystem_size_bytes - node_filesystem_free_bytes) / node_filesystem_size_bytes * 100 > 85
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "高磁盘使用率告警"
          description: "磁盘使用率超过85%: {{ $value }}%"

      # 应用宕机告警
      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "服务宕机告警"
          description: "服务 {{ $labels.job }} 宕机"

      # 数据库连接告警
      - alert: DatabaseConnectionHigh
        expr: pg_stat_activity_count > 80
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "数据库连接数过高"
          description: "活跃连接数: {{ $value }}"

      # Redis内存使用告警
      - alert: RedisMemoryHigh
        expr: redis_memory_used_bytes / redis_memory_max_bytes * 100 > 80
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Redis内存使用率过高"
          description: "内存使用率: {{ $value }}%"
EOF

    print_success "Prometheus配置完成"
}

# 配置Grafana仪表板
setup_grafana() {
    print_info "配置Grafana仪表板..."

    mkdir -p monitoring/grafana/provisioning/{dashboards,datasources}

    # 配置数据源
    cat > monitoring/grafana/provisioning/datasources/prometheus.yml <<EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
EOF

    # 配置仪表板
    cat > monitoring/grafana/provisioning/dashboards/dashboard.yml <<EOF
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
EOF

    print_success "Grafana配置完成"
}

# 配置AlertManager
setup_alertmanager() {
    print_info "配置AlertManager..."

    mkdir -p monitoring/alertmanager

    cat > monitoring/alertmanager/alertmanager.yml <<EOF
# AlertManager配置
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@yourdomain.com'
  smtp_auth_username: 'alerts@yourdomain.com'
  smtp_auth_password: 'your_smtp_password'

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
    - match:
        severity: warning
      receiver: 'warning-alerts'

receivers:
  - name: 'web.hook'
    webhook_configs:
      - url: 'http://localhost:5001/'

  - name: 'critical-alerts'
    email_configs:
      - to: 'admin@yourdomain.com'
        subject: '[CRITICAL] MR游戏运营管理系统告警'
        body: |
          {{ range .Alerts }}
          告警: {{ .Annotations.summary }}
          描述: {{ .Annotations.description }}
          时间: {{ .StartsAt }}
          {{ end }}

  - name: 'warning-alerts'
    email_configs:
      - to: 'ops@yourdomain.com'
        subject: '[WARNING] MR游戏运营管理系统告警'
        body: |
          {{ range .Alerts }}
          告警: {{ .Annotations.summary }}
          描述: {{ .Annotations.description }}
          时间: {{ .StartsAt }}
          {{ end }}

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'cluster', 'service']
EOF

    print_success "AlertManager配置完成"
}

# 创建Docker Compose监控服务
create_monitoring_compose() {
    print_info "创建监控服务Docker Compose文件..."

    cat > docker-compose.monitoring.yml <<EOF
version: '3.8'

services:
  # Prometheus监控服务
  prometheus:
    image: prom/prometheus:latest
    container_name: mr_game_ops_prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus:/etc/prometheus
      - prometheus_data:/prometheus
    networks:
      - mr_network_prod
    restart: unless-stopped

  # Grafana可视化服务
  grafana:
    image: grafana/grafana:latest
    container_name: mr_game_ops_grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123456
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
    networks:
      - mr_network_prod
    restart: unless-stopped
    depends_on:
      - prometheus

  # AlertManager告警服务
  alertmanager:
    image: prom/alertmanager:latest
    container_name: mr_game_ops_alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager:/etc/alertmanager
      - alertmanager_data:/alertmanager
    networks:
      - mr_network_prod
    restart: unless-stopped
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'

  # Node Exporter (系统监控)
  node-exporter:
    image: prom/node-exporter:latest
    container_name: mr_game_ops_node_exporter
    ports:
      - "9100:9100"
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    networks:
      - mr_network_prod
    restart: unless-stopped

  # PostgreSQL Exporter
  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    container_name: mr_game_ops_postgres_exporter
    ports:
      - "9187:9187"
    environment:
      DATA_SOURCE_NAME: "postgresql://postgres_exporter:export_password@postgres:5432/mr_game_ops?sslmode=disable"
    networks:
      - mr_network_prod
    restart: unless-stopped
    depends_on:
      - postgres

  # Redis Exporter
  redis-exporter:
    image: oliver006/redis_exporter:latest
    container_name: mr_game_ops_redis_exporter
    ports:
      - "9121:9121"
    environment:
      REDIS_ADDR: "redis://redis:6379"
      REDIS_PASSWORD: "CHANGE_THIS_REDIS_PASSWORD"
    networks:
      - mr_network_prod
    restart: unless-stopped
    depends_on:
      - redis

volumes:
  prometheus_data:
    driver: local
  grafana_data:
    driver: local
  alertmanager_data:
    driver: local

networks:
  mr_network_prod:
    external: true
EOF

    print_success "监控服务Docker Compose文件创建完成"
}

# 创建启动脚本
create_start_script() {
    print_info "创建监控启动脚本..."

    cat > scripts/start_monitoring.sh <<'EOF'
#!/bin/bash
# 启动MR游戏运营管理系统监控服务

set -e

echo "🚀 启动MR游戏运营管理系统监控服务..."

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker未运行，请先启动Docker"
    exit 1
fi

# 检查主应用是否运行
if ! docker ps | grep -q "mr_game_ops_backend_prod"; then
    echo "❌ 主应用未运行，请先启动主应用"
    echo "运行: docker-compose -f docker-compose.prod.yml up -d"
    exit 1
fi

# 启动监控服务
echo "📊 启动Prometheus监控服务..."
docker-compose -f docker-compose.monitoring.yml up -d prometheus

echo "📈 启动Grafana可视化服务..."
docker-compose -f docker-compose.monitoring.yml up -d grafana

echo "🚨 启动AlertManager告警服务..."
docker-compose -f docker-compose.monitoring.yml up -d alertmanager

echo "🖥️  启动系统监控..."
docker-compose -f docker-compose.monitoring.yml up -d node-exporter

echo "🗄️  启动数据库监控..."
docker-compose -f docker-compose.monitoring.yml up -d postgres-exporter

echo "💾 启动Redis监控..."
docker-compose -f docker-compose.monitoring.yml up -d redis-exporter

echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose -f docker-compose.monitoring.yml ps

echo "✅ 监控服务启动完成!"
echo ""
echo "📊 访问地址:"
echo "   Prometheus: http://localhost:9090"
echo "   Grafana: http://localhost:3001 (admin/admin123456)"
echo "   AlertManager: http://localhost:9093"
echo ""
echo "📝 提示: 请根据实际情况修改配置文件中的告警通知设置"
EOF

    chmod +x scripts/start_monitoring.sh

    print_success "监控启动脚本创建完成"
}

# 创建备份脚本
create_backup_script() {
    print_info "创建备份脚本..."

    cat > scripts/backup.sh <<'EOF'
#!/bin/bash
# MR游戏运营管理系统备份脚本

set -e

BACKUP_DIR="/var/backups/mr_game_ops"
DATE=$(date +%Y%m%d_%H%M%S)
DB_BACKUP_FILE="$BACKUP_DIR/daily/mr_game_ops_db_$DATE.sql"
REDIS_BACKUP_FILE="$BACKUP_DIR/daily/mr_game_ops_redis_$DATE.rdb"

echo "🔄 开始备份MR游戏运营管理系统数据..."

# 创建备份目录
mkdir -p "$BACKUP_DIR/daily" "$BACKUP_DIR/weekly" "$BACKUP_DIR/monthly"

# 备份PostgreSQL数据库
echo "🗄️  备份PostgreSQL数据库..."
docker exec mr_game_ops_db_prod pg_dump -U mr_admin mr_game_ops > "$DB_BACKUP_FILE"

# 备份Redis数据
echo "💾 备份Redis数据..."
docker exec mr_game_ops_redis_prod redis-cli BGSAVE
sleep 2
docker cp mr_game_ops_redis_prod:/data/dump.rdb "$REDIS_BACKUP_FILE"

# 备份上传的文件
echo "📁 备份上传文件..."
UPLOAD_BACKUP_DIR="$BACKUP_DIR/daily/uploads_$DATE"
mkdir -p "$UPLOAD_BACKUP_DIR"
docker cp mr_game_ops_backend_prod:/var/www/mr_game_ops/uploads/* "$UPLOAD_BACKUP_DIR/" 2>/dev/null || true

# 压缩备份
echo "🗜️  压缩备份文件..."
tar -czf "$BACKUP_DIR/daily/mr_game_ops_full_$DATE.tar.gz" \
    -C "$BACKUP_DIR/daily" \
    "mr_game_ops_db_$DATE.sql" \
    "mr_game_ops_redis_$DATE.rdb" \
    "uploads_$DATE/" \
    2>/dev/null || true

# 清理临时文件
rm -f "$DB_BACKUP_FILE" "$REDIS_BACKUP_FILE"
rm -rf "$UPLOAD_BACKUP_DIR"

# 清理旧备份 (保留30天)
echo "🧹 清理30天前的备份..."
find "$BACKUP_DIR/daily" -name "*.tar.gz" -mtime +30 -delete
find "$BACKUP_DIR/weekly" -name "*.tar.gz" -mtime +90 -delete
find "$BACKUP_DIR/monthly" -name "*.tar.gz" -mtime +365 -delete

echo "✅ 备份完成: $BACKUP_DIR/daily/mr_game_ops_full_$DATE.tar.gz"
EOF

    chmod +x scripts/backup.sh

    # 添加到crontab
    (crontab -l 2>/dev/null; echo "0 2 * * * $(pwd)/scripts/backup.sh") | crontab -

    print_success "备份脚本创建完成并添加到定时任务"
}

# 主函数
main() {
    print_info "MR游戏运营管理系统 - 监控和日志收集配置"

    check_root

    create_directories
    setup_log_rotation
    setup_prometheus
    setup_grafana
    setup_alertmanager
    create_monitoring_compose
    create_start_script
    create_backup_script

    print_success "🎉 监控和日志收集配置完成!"
    echo ""
    echo "📋 下一步操作:"
    echo "   1. 运行监控服务: ./scripts/start_monitoring.sh"
    echo "   2. 访问Grafana: http://localhost:3001 (admin/admin123456)"
    echo "   3. 配置告警通知 (邮件/Slack)"
    echo "   4. 设置定期备份: ./scripts/backup.sh"
    echo ""
    echo "📊 监控指标包括:"
    echo "   - 应用性能指标 (响应时间、错误率)"
    echo "   - 系统资源指标 (CPU、内存、磁盘)"
    echo "   - 数据库性能指标"
    echo "   - Redis缓存指标"
    echo "   - 业务指标 (用户数、交易量等)"
}

# 运行主函数
main "$@"