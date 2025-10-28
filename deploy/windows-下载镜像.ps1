# =============================================================================
# Windows端 - 自动下载并导出Docker镜像
# =============================================================================
# 使用方法:
#   1. 以管理员身份打开PowerShell
#   2. 执行: .\windows-下载镜像.ps1
# =============================================================================

Write-Host "╔════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     MR游戏运营管理系统 - Docker镜像下载工具                        ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# 检查Docker是否运行
Write-Host "检查Docker环境..." -ForegroundColor Yellow
try {
    $dockerVersion = docker version --format '{{.Server.Version}}' 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker未运行"
    }
    Write-Host "✓ Docker版本: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker未运行或未安装" -ForegroundColor Red
    Write-Host "请先启动Docker Desktop" -ForegroundColor Yellow
    Read-Host "按Enter键退出"
    exit 1
}

Write-Host ""

# 创建导出目录
$exportDir = "C:\docker-images"
Write-Host "创建导出目录: $exportDir" -ForegroundColor Yellow
if (!(Test-Path $exportDir)) {
    New-Item -ItemType Directory -Path $exportDir | Out-Null
}
Write-Host "✓ 目录已创建" -ForegroundColor Green

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  请选择要下载的镜像                                                ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. 只下载核心镜像（必需）- 约230 MB" -ForegroundColor White
Write-Host "   - Python 3.11 (后端)" -ForegroundColor Gray
Write-Host "   - PostgreSQL 14 (数据库)" -ForegroundColor Gray
Write-Host "   - Redis 7 (缓存)" -ForegroundColor Gray
Write-Host ""
Write-Host "2. 核心 + 前端镜像 - 约450 MB" -ForegroundColor White
Write-Host "   - 包含上述 + Node 18 + Nginx" -ForegroundColor Gray
Write-Host ""
Write-Host "3. 全部镜像（含监控）- 约1 GB" -ForegroundColor White
Write-Host "   - 包含上述 + Prometheus + Grafana" -ForegroundColor Gray
Write-Host ""

do {
    $choice = Read-Host "请选择 (1/2/3)"
} while ($choice -notin @("1", "2", "3"))

# 定义镜像列表
$coreImages = @{
    "python:3.11-slim" = "python-3.11-slim.tar"
    "postgres:14-alpine" = "postgres-14-alpine.tar"
    "redis:7-alpine" = "redis-7-alpine.tar"
}

$frontendImages = @{
    "node:18-alpine" = "node-18-alpine.tar"
    "nginx:alpine" = "nginx-alpine.tar"
}

$monitorImages = @{
    "prom/prometheus:latest" = "prometheus-latest.tar"
    "grafana/grafana:latest" = "grafana-latest.tar"
}

# 根据选择合并镜像列表
$imagesToDownload = $coreImages.Clone()

if ($choice -eq "2" -or $choice -eq "3") {
    foreach ($key in $frontendImages.Keys) {
        $imagesToDownload[$key] = $frontendImages[$key]
    }
}

if ($choice -eq "3") {
    foreach ($key in $monitorImages.Keys) {
        $imagesToDownload[$key] = $monitorImages[$key]
    }
}

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  开始下载镜像                                                      ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$totalImages = $imagesToDownload.Count
$currentImage = 0

foreach ($image in $imagesToDownload.Keys) {
    $currentImage++
    Write-Host "[$currentImage/$totalImages] 下载: $image" -ForegroundColor Yellow

    docker pull $image

    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ 下载成功" -ForegroundColor Green
    } else {
        Write-Host "  ✗ 下载失败" -ForegroundColor Red
    }

    Write-Host ""
}

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  导出镜像为tar文件                                                 ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$currentImage = 0

foreach ($image in $imagesToDownload.Keys) {
    $currentImage++
    $outputFile = $imagesToDownload[$image]
    $fullPath = Join-Path $exportDir $outputFile

    Write-Host "[$currentImage/$totalImages] 导出: $image" -ForegroundColor Yellow
    Write-Host "  -> $outputFile" -ForegroundColor Gray

    docker save $image -o $fullPath

    if ($LASTEXITCODE -eq 0) {
        $fileSize = (Get-Item $fullPath).Length / 1MB
        Write-Host "  ✓ 导出成功 ($([math]::Round($fileSize, 2)) MB)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ 导出失败" -ForegroundColor Red
    }

    Write-Host ""
}

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  ✓ 完成！                                                          ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

Write-Host "导出的文件列表:" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

$totalSize = 0
Get-ChildItem $exportDir -Filter "*.tar" | ForEach-Object {
    $sizeMB = [math]::Round($_.Length / 1MB, 2)
    $totalSize += $sizeMB
    Write-Host "  $($_.Name)" -NoNewline -ForegroundColor White
    Write-Host " ($sizeMB MB)" -ForegroundColor Gray
}

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "  总计: $([math]::Round($totalSize, 2)) MB" -ForegroundColor Cyan
Write-Host ""

Write-Host "下一步操作:" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""
Write-Host "方法1: 使用SCP上传（推荐）" -ForegroundColor White
Write-Host "  在PowerShell中执行:" -ForegroundColor Gray
Write-Host "  cd C:\docker-images" -ForegroundColor Cyan
Write-Host "  scp *.tar root@你的服务器IP:/root/docker-images/" -ForegroundColor Cyan
Write-Host ""
Write-Host "方法2: 使用WinSCP图形界面上传" -ForegroundColor White
Write-Host "  1. 下载WinSCP: https://winscp.net/" -ForegroundColor Gray
Write-Host "  2. 连接到服务器" -ForegroundColor Gray
Write-Host "  3. 上传 C:\docker-images 目录下所有 .tar 文件" -ForegroundColor Gray
Write-Host "  4. 上传到服务器的 /root/docker-images/ 目录" -ForegroundColor Gray
Write-Host ""
Write-Host "上传完成后，在服务器上执行部署脚本:" -ForegroundColor White
Write-Host "  bash /root/import-and-deploy.sh" -ForegroundColor Cyan
Write-Host ""

# 询问是否现在上传
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
$upload = Read-Host "是否现在上传到服务器？(y/n)"

if ($upload -eq "y") {
    Write-Host ""
    $serverIP = Read-Host "请输入服务器IP地址"

    Write-Host ""
    Write-Host "开始上传..." -ForegroundColor Yellow
    Write-Host "提示: 需要输入服务器root密码" -ForegroundColor Gray
    Write-Host ""

    # 先在服务器创建目录
    ssh root@$serverIP "mkdir -p /root/docker-images"

    # 上传文件
    scp "$exportDir\*.tar" root@${serverIP}:/root/docker-images/

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✓ 上传成功！" -ForegroundColor Green
        Write-Host ""
        Write-Host "现在可以SSH到服务器执行部署:" -ForegroundColor Yellow
        Write-Host "  ssh root@$serverIP" -ForegroundColor Cyan
        Write-Host "  bash /root/import-and-deploy.sh" -ForegroundColor Cyan
    } else {
        Write-Host ""
        Write-Host "✗ 上传失败" -ForegroundColor Red
        Write-Host "请使用WinSCP手动上传" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "按Enter键退出..." -ForegroundColor Gray
Read-Host
