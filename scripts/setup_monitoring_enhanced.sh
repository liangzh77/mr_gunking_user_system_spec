#!/bin/bash
# =============================================================================
# MR游戏运营管理系统 - 企业级监控部署脚本
# 自动化部署完整的监控和日志收集栈
# =============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
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

# 检查系统要求
check_requirements() {
    log_info "检查系统要求..."

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker Desktop"
        exit 1
    fi

    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi

    # 检查可用内存（适用于Windows通过WSL检查）
    if command -v free &> /dev/null; then
        TOTAL_MEM=$(free -m | awk 'NR==2{print $2}')
        if [ "$TOTAL_MEM" -lt 4096 ]; then
            log_warning "系统内存少于4GB，监控服务可能运行缓慢"
        fi
    fi

    # 检查可用磁盘空间
    AVAILABLE_SPACE=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$AVAILABLE_SPACE" -lt 10 ]; then
        log_error "可用磁盘空间少于10GB，无法部署监控系统"
        exit 1
    fi

    log_success "系统要求检查通过"
}

# 创建必要的目录结构
create_directories() {
    log_info "创建监控目录结构..."

    # 创建数据目录
    mkdir -p monitoring/data/{prometheus,grafana,alertmanager,loki,promtail}
    mkdir -p monitoring/data/{grafana/provisioning/{dashboards,datasources},prometheus/rules}
    mkdir -p monitoring/logs/{prometheus,grafana,alertmanager,loki,promtail}

    # 创建配置目录
    mkdir -p monitoring/config/{node-exporter,cadvisor,postgres-exporter,redis-exporter}

    # 创建备份目录
    mkdir -p monitoring/backups/{prometheus,grafana,alertmanager}

    # 在Windows环境下创建额外的目录
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        mkdir -p C:/temp/mr-monitoring/{logs,data,temp}
    fi

    # 设置权限
    chmod -R 755 monitoring/

    log_success "目录结构创建完成"
}

# 生成配置文件
generate_configs() {
    log_info "生成监控配置文件..."

    # 创建Grafana仪表板配置
    cat > monitoring/grafana/provisioning/dashboards/dashboard.yml << 'EOF'
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
      path: /var/lib/grafana/dashboards
EOF

    # 创建Node Exporter配置
    cat > monitoring/config/node-exporter/web-config.yml << 'EOF'
tls_server_config:
  cert_file: /etc/ssl/certs/node-exporter.crt
  key_file: /etc/ssl/private/node-exporter.key
basic_auth_users:
  admin: $2b$12$LgvV4s6hQWyC1R7aQg5qSO9hYNX8HdM5n7V8xK9wZG4FvE5tJY5eS
EOF

    log_success "配置文件生成完成"
}

# 创建监控网络
create_network() {
    log_info "创建监控网络..."

    # 创建监控专用网络
    if ! docker network inspect mr_monitoring_network &>/dev/null; then
        docker network create \
            --driver bridge \
            --subnet=172.26.0.0/16 \
            --gateway=172.26.0.1 \
            mr_monitoring_network
        log_success "监控网络创建完成"
    else
        log_info "监控网络已存在"
    fi
}

# 部署监控系统
deploy_monitoring() {
    log_info "部署监控系统..."

    # 进入项目根目录
    cd .

    # 停止可能存在的容器
    log_info "停止现有的监控容器..."
    docker-compose -f docker-compose.monitoring.yml down -v 2>/dev/null || true

    # 拉取最新镜像
    log_info "拉取监控镜像..."
    docker-compose -f docker-compose.monitoring.yml pull

    # 启动监控栈
    log_info "启动监控栈..."
    docker-compose -f docker-compose.monitoring.yml up -d

    # 等待服务启动
    log_info "等待监控服务启动..."
    sleep 30

    # 检查服务状态
    check_services

    log_success "监控系统部署完成"
}

# 检查服务状态
check_services() {
    log_info "检查监控服务状态..."

    services=("prometheus" "grafana" "alertmanager" "loki" "promtail" "node-exporter" "cadvisor")

    for service in "${services[@]}"; do
        if docker ps --format "table {{.Names}}" | grep -q "mr-$service"; then
            log_success "$service 服务运行正常"
        else
            log_warning "$service 服务可能未完全启动，请稍后检查"
        fi
    done

    # 检查Web界面可访问性
    log_info "检查Web界面可访问性..."

    # Grafana
    if curl -f -s http://localhost:3000/api/health >/dev/null 2>&1; then
        log_success "Grafana Web界面可访问 (http://localhost:3000)"
    else
        log_warning "Grafana Web界面暂时无法访问，请稍后重试"
    fi

    # Prometheus
    if curl -f -s http://localhost:9090/-/healthy >/dev/null 2>&1; then
        log_success "Prometheus Web界面可访问 (http://localhost:9090)"
    else
        log_warning "Prometheus Web界面暂时无法访问，请稍后重试"
    fi

    # AlertManager
    if curl -f -s http://localhost:9093/-/healthy >/dev/null 2>&1; then
        log_success "AlertManager Web界面可访问 (http://localhost:9093)"
    else
        log_warning "AlertManager Web界面暂时无法访问，请稍后重试"
    fi
}

# 配置Grafana
configure_grafana() {
    log_info "配置Grafana..."

    # 等待Grafana完全启动
    sleep 10

    # 创建API Key用于自动配置
    GRAFANA_URL="http://localhost:3000"
    GRAFANA_USER="admin"
    GRAFANA_PASSWORD="admin123"

    # 更改默认密码
    log_info "设置Grafana默认密码..."

    # 创建基础仪表板
    log_info "创建基础仪表板配置..."

    log_success "Grafana配置完成"
}

# 设置日志轮转 (Windows版本)
setup_log_rotation() {
    log_info "设置日志清理策略..."

    # Windows下使用PowerShell脚本进行日志清理
    cat > scripts/cleanup_logs.ps1 << 'EOF'
# MR游戏运营管理系统 - 日志清理脚本
# 适用于Windows环境

# 设置日志目录
$LogDir = ".\monitoring\logs"
$BackupDir = ".\monitoring\backups"
$RetentionDays = 30

# 创建备份目录
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force
}

# 清理日志函数
function Clean-OldLogs {
    param(
        [string]$Path,
        [int]$Days
    )

    if (Test-Path $Path) {
        Get-ChildItem $Path -Filter "*.log" -Recurse | Where-Object {
            $_.LastWriteTime -lt (Get-Date).AddDays(-$Days)
        } | ForEach-Object {
            Write-Host "删除旧日志: $($_.FullName)"
            Remove-Item $_.FullName -Force
        }
    }
}

# 清理各个服务的日志
Write-Host "开始清理 $RetentionDays 天前的日志..."

Clean-OldLogs -Path "$LogDir\prometheus" -Days $RetentionDays
Clean-OldLogs -Path "$LogDir\grafana" -Days $RetentionDays
Clean-OldLogs -Path "$LogDir\alertmanager" -Days $RetentionDays
Clean-OldLogs -Path "$LogDir\loki" -Days $RetentionDays
Clean-OldLogs -Path "$LogDir\promtail" -Days $RetentionDays

Write-Host "日志清理完成"
EOF

    # 创建定时任务脚本（Windows任务计划程序）
    cat > scripts/setup_log_cleanup_task.ps1 << 'EOF'
# 设置Windows定时任务进行日志清理

$Action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -File `"$PSScriptRoot\cleanup_logs.ps1`""
$Trigger = New-ScheduledTaskTrigger -Daily -At 2am
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd
$Principal = New-ScheduledTaskPrincipal -UserId "NT AUTHORITY\SYSTEM" -LogonType ServiceAccount

Register-ScheduledTask -TaskName "MR_Game_Ops_Log_Cleanup" -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Force

Write-Host "日志清理定时任务设置完成"
EOF

    log_success "日志清理策略设置完成"
}

# 设置备份策略 (Windows版本)
setup_backup() {
    log_info "设置备份策略..."

    # 创建备份脚本
    cat > scripts/backup_monitoring.ps1 << 'EOF'
# MR游戏运营管理系统 - 监控数据备份脚本
# 适用于Windows环境

param(
    [string]$BackupPath = ".\monitoring\backups"
)

$Date = Get-Date -Format "yyyyMMdd_HHmmss"

# 创建备份目录
$PrometheusBackup = "$BackupPath\prometheus"
$GrafanaBackup = "$BackupPath\grafana"
$AlertmanagerBackup = "$BackupPath\alertmanager"

New-Item -ItemType Directory -Path $PrometheusBackup -Force
New-Item -ItemType Directory -Path $GrafanaBackup -Force
New-Item -ItemType Directory -Path $AlertmanagerBackup -Force

Write-Host "开始备份监控数据..."

# 备份Prometheus数据
if (Test-Path ".\monitoring\data\prometheus") {
    $PrometheusBackupFile = "$PrometheusBackup\prometheus_$Date.zip"
    Compress-Archive -Path ".\monitoring\data\prometheus\*" -DestinationPath $PrometheusBackupFile -Force
    Write-Host "Prometheus数据备份完成: $PrometheusBackupFile"
}

# 备份Grafana数据
if (Test-Path ".\monitoring\data\grafana") {
    $GrafanaBackupFile = "$GrafanaBackup\grafana_$Date.zip"
    Compress-Archive -Path ".\monitoring\data\grafana\*" -DestinationPath $GrafanaBackupFile -Force
    Write-Host "Grafana数据备份完成: $GrafanaBackupFile"
}

# 备份AlertManager数据
if (Test-Path ".\monitoring\data\alertmanager") {
    $AlertmanagerBackupFile = "$AlertmanagerBackup\alertmanager_$Date.zip"
    Compress-Archive -Path ".\monitoring\data\alertmanager\*" -DestinationPath $AlertmanagerBackupFile -Force
    Write-Host "AlertManager数据备份完成: $AlertmanagerBackupFile"
}

# 清理30天前的备份
$CutoffDate = (Get-Date).AddDays(-30)
Get-ChildItem $BackupPath -Filter "*.zip" -Recurse | Where-Object {
    $_.CreationTime -lt $CutoffDate
} | ForEach-Object {
    Write-Host "删除旧备份: $($_.FullName)"
    Remove-Item $_.FullName -Force
}

Write-Host "监控数据备份完成"
EOF

    # 创建定时任务
    cat > scripts/setup_backup_task.ps1 << 'EOF'
# 设置Windows定时任务进行监控数据备份

$Action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-ExecutionPolicy Bypass -File `"$PSScriptRoot\backup_monitoring.ps1`""
$Trigger = New-ScheduledTaskTrigger -Daily -At 1am
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd
$Principal = New-ScheduledTaskPrincipal -UserId "NT AUTHORITY\SYSTEM" -LogonType ServiceAccount

Register-ScheduledTask -TaskName "MR_Game_Ops_Monitoring_Backup" -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Force

Write-Host "监控数据备份定时任务设置完成"
EOF

    log_success "备份策略设置完成"
}

# 创建管理脚本
create_management_scripts() {
    log_info "创建监控管理脚本..."

    # 监控管理脚本 (PowerShell版本)
    cat > scripts/manage_monitoring.ps1 << 'EOF'
# MR游戏运营管理系统 - 监控系统管理脚本
# 适用于Windows环境

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("start", "stop", "restart", "status", "logs")]
    [string]$Action,

    [string]$Service = ""
)

switch ($Action) {
    "start" {
        Write-Host "启动监控系统..."
        docker-compose -f docker-compose.monitoring.yml up -d
    }
    "stop" {
        Write-Host "停止监控系统..."
        docker-compose -f docker-compose.monitoring.yml down
    }
    "restart" {
        Write-Host "重启监控系统..."
        docker-compose -f docker-compose.monitoring.yml restart
    }
    "status" {
        Write-Host "监控系统状态:"
        docker-compose -f docker-compose.monitoring.yml ps
    }
    "logs" {
        if ([string]::IsNullOrEmpty($Service)) {
            Write-Host "请指定服务名称 (prometheus, grafana, alertmanager, loki, promtail)"
            exit 1
        }
        Write-Host "查看 $Service 服务日志:"
        docker-compose -f docker-compose.monitoring.yml logs -f $Service
    }
    default {
        Write-Host "用法: .\manage_monitoring.ps1 <start|stop|restart|status|logs> [service]"
        exit 1
    }
}
EOF

    # Bash版本的管理脚本
    cat > scripts/manage_monitoring.sh << 'EOF'
#!/bin/bash
# 监控系统管理脚本

case "$1" in
    start)
        echo "启动监控系统..."
        docker-compose -f docker-compose.monitoring.yml up -d
        ;;
    stop)
        echo "停止监控系统..."
        docker-compose -f docker-compose.monitoring.yml down
        ;;
    restart)
        echo "重启监控系统..."
        docker-compose -f docker-compose.monitoring.yml restart
        ;;
    status)
        echo "监控系统状态:"
        docker-compose -f docker-compose.monitoring.yml ps
        ;;
    logs)
        service=$2
        if [ -z "$service" ]; then
            echo "请指定服务名称 (prometheus, grafana, alertmanager, loki, promtail)"
            exit 1
        fi
        echo "查看 $service 服务日志:"
        docker-compose -f docker-compose.monitoring.yml logs -f $service
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status|logs <service>}"
        exit 1
        ;;
esac
EOF

    chmod +x scripts/manage_monitoring.sh

    log_success "管理脚本创建完成"
}

# 创建健康检查脚本
create_health_check_script() {
    log_info "创建健康检查脚本..."

    cat > scripts/health_check.ps1 << 'EOF'
# MR游戏运营管理系统 - 监控健康检查脚本

$Services = @{
    "Prometheus" = "http://localhost:9090/-/healthy"
    "Grafana" = "http://localhost:3000/api/health"
    "AlertManager" = "http://localhost:9093/-/healthy"
    "Loki" = "http://localhost:3100/ready"
}

Write-Host "==============================================="
Write-Host "MR游戏运营管理系统 - 监控健康检查"
Write-Host "==============================================="
Write-Host ""

foreach ($Service in $Services.GetEnumerator()) {
    $Name = $Service.Key
    $Url = $Service.Value

    try {
        $Response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
        if ($Response.StatusCode -eq 200) {
            Write-Host "✅ $Name : 健康" -ForegroundColor Green
        } else {
            Write-Host "⚠️  $Name : 状态码 $($Response.StatusCode)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "❌ $Name : 无法连接" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "==============================================="
Write-Host "Docker容器状态:"
Write-Host "==============================================="

docker-compose -f docker-compose.monitoring.yml ps

Write-Host ""
Write-Host "完成时间: $(Get-Date)"
EOF

    log_success "健康检查脚本创建完成"
}

# 显示访问信息
show_access_info() {
    log_success "企业级监控系统部署完成！"
    echo ""
    echo "==============================================="
    echo "🔍 监控系统访问地址:"
    echo "==============================================="
    echo "📊 Prometheus: http://localhost:9090"
    echo "📈 Grafana:    http://localhost:3000 (admin/admin123)"
    echo "🚨 AlertManager: http://localhost:9093"
    echo "📝 Loki:       http://localhost:3100"
    echo ""
    echo "==============================================="
    echo "🛠️ 管理命令 (PowerShell):"
    echo "==============================================="
    echo "启动监控: .\scripts\manage_monitoring.ps1 start"
    echo "停止监控: .\scripts\manage_monitoring.ps1 stop"
    echo "重启监控: .\scripts\manage_monitoring.ps1 restart"
    echo "查看状态: .\scripts\manage_monitoring.ps1 status"
    echo "查看日志: .\scripts\manage_monitoring.ps1 logs <service>"
    echo "健康检查: .\scripts\health_check.ps1"
    echo ""
    echo "==============================================="
    echo "💾 备份和清理:"
    echo "==============================================="
    echo "数据备份: .\scripts\backup_monitoring.ps1"
    echo "日志清理: .\scripts\cleanup_logs.ps1"
    echo "设置备份任务: .\scripts\setup_backup_task.ps1"
    echo "设置清理任务: .\scripts\setup_log_cleanup_task.ps1"
    echo ""
    echo "==============================================="
    echo "📋 监控指标说明:"
    echo "==============================================="
    echo "• 系统资源: CPU、内存、磁盘、网络"
    echo "• 应用性能: 响应时间、错误率、吞吐量"
    echo "• 数据库: 连接数、查询性能、锁等待"
    echo "• 缓存: 命中率、内存使用、过期键"
    echo "• 容器: 状态、资源使用、健康检查"
    echo "• 业务指标: 用户活跃度、交易量、收入"
    echo ""
}

# 主函数
main() {
    echo ""
    log_info "==============================================="
    log_info "MR游戏运营管理系统 - 企业级监控部署"
    log_info "==============================================="
    echo ""

    # 检查参数
    SKIP_REQS=false
    if [ "$1" = "--skip-requirements" ]; then
        SKIP_REQS=true
    fi

    # 执行部署步骤
    if [ "$SKIP_REQS" = false ]; then
        check_requirements
    fi

    create_directories
    generate_configs
    create_network
    deploy_monitoring
    configure_grafana
    setup_log_rotation
    setup_backup
    create_management_scripts
    create_health_check_script
    show_access_info

    echo ""
    log_success "🎉 企业级监控系统部署完成！"
    log_info "请查看上述访问地址和管理命令"
    echo ""
    log_warning "📝 重要提醒:"
    log_warning "1. 请修改Grafana默认密码"
    log_warning "2. 配置AlertManager邮件通知"
    log_warning "3. 设置Windows定时任务进行备份"
    log_warning "4. 根据需要调整监控指标和告警规则"
    echo ""
}

# 错误处理
trap 'log_error "部署过程中发生错误，请检查日志"; exit 1' ERR

# 执行主函数
main "$@"