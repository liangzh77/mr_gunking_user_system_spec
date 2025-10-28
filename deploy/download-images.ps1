# =============================================================================
# Docker Images Download Script for Windows
# =============================================================================

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  Docker Image Download Tool" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker
Write-Host "Checking Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker version --format '{{.Server.Version}}' 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker not running"
    }
    Write-Host "[OK] Docker version: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Docker is not running" -ForegroundColor Red
    Write-Host "Please start Docker Desktop first" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""

# Create export directory
$exportDir = "C:\docker-images"
Write-Host "Creating export directory: $exportDir" -ForegroundColor Yellow
if (!(Test-Path $exportDir)) {
    New-Item -ItemType Directory -Path $exportDir | Out-Null
}
Write-Host "[OK] Directory created" -ForegroundColor Green

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  Select images to download" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Core images only (Required) - ~230 MB" -ForegroundColor White
Write-Host "   - Python 3.11 (Backend)" -ForegroundColor Gray
Write-Host "   - PostgreSQL 14 (Database)" -ForegroundColor Gray
Write-Host "   - Redis 7 (Cache)" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Core + Frontend - ~450 MB" -ForegroundColor White
Write-Host "   - Above + Node 18 + Nginx" -ForegroundColor Gray
Write-Host ""
Write-Host "3. All images (with monitoring) - ~1 GB" -ForegroundColor White
Write-Host "   - Above + Prometheus + Grafana" -ForegroundColor Gray
Write-Host ""

do {
    $choice = Read-Host "Please select (1/2/3)"
} while ($choice -notin @("1", "2", "3"))

# Define image lists
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

# Merge lists based on choice
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
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  Downloading images" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

$totalImages = $imagesToDownload.Count
$currentImage = 0

foreach ($image in $imagesToDownload.Keys) {
    $currentImage++
    Write-Host "[$currentImage/$totalImages] Downloading: $image" -ForegroundColor Yellow

    docker pull $image

    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Downloaded successfully" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Download failed" -ForegroundColor Red
    }

    Write-Host ""
}

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  Exporting images to tar files" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

$currentImage = 0

foreach ($image in $imagesToDownload.Keys) {
    $currentImage++
    $outputFile = $imagesToDownload[$image]
    $fullPath = Join-Path $exportDir $outputFile

    Write-Host "[$currentImage/$totalImages] Exporting: $image" -ForegroundColor Yellow
    Write-Host "  -> $outputFile" -ForegroundColor Gray

    docker save $image -o $fullPath

    if ($LASTEXITCODE -eq 0) {
        $fileSize = (Get-Item $fullPath).Length / 1MB
        $fileSizeRounded = [math]::Round($fileSize, 2)
        Write-Host "  [OK] Exported successfully ($fileSizeRounded MB)" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Export failed" -ForegroundColor Red
    }

    Write-Host ""
}

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  COMPLETE!" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Exported files:" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------------" -ForegroundColor Gray

$totalSize = 0
Get-ChildItem $exportDir -Filter "*.tar" | ForEach-Object {
    $sizeMB = [math]::Round($_.Length / 1MB, 2)
    $totalSize += $sizeMB
    Write-Host "  $($_.Name) ($sizeMB MB)" -ForegroundColor White
}

Write-Host "----------------------------------------------------------------------" -ForegroundColor Gray
Write-Host "  Total: $([math]::Round($totalSize, 2)) MB" -ForegroundColor Cyan
Write-Host ""

Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------------" -ForegroundColor Gray
Write-Host ""
Write-Host "Method 1: Upload using SCP (Recommended)" -ForegroundColor White
Write-Host "  Execute in PowerShell:" -ForegroundColor Gray
Write-Host "  cd C:\docker-images" -ForegroundColor Cyan
Write-Host "  scp *.tar root@YOUR_SERVER_IP:/root/docker-images/" -ForegroundColor Cyan
Write-Host ""
Write-Host "Method 2: Upload using WinSCP (GUI)" -ForegroundColor White
Write-Host "  1. Download WinSCP: https://winscp.net/" -ForegroundColor Gray
Write-Host "  2. Connect to your server" -ForegroundColor Gray
Write-Host "  3. Upload all .tar files from C:\docker-images" -ForegroundColor Gray
Write-Host "  4. Upload to /root/docker-images/ on server" -ForegroundColor Gray
Write-Host ""
Write-Host "After uploading, run on server:" -ForegroundColor White
Write-Host "  bash /root/import-and-deploy.sh" -ForegroundColor Cyan
Write-Host ""

# Ask if upload now
Write-Host "----------------------------------------------------------------------" -ForegroundColor Gray
$upload = Read-Host "Upload to server now? (y/n)"

if ($upload -eq "y") {
    Write-Host ""
    $serverIP = Read-Host "Enter server IP address"

    Write-Host ""
    Write-Host "Starting upload..." -ForegroundColor Yellow
    Write-Host "Note: You will need to enter server password" -ForegroundColor Gray
    Write-Host ""

    # Create directory on server
    ssh root@$serverIP "mkdir -p /root/docker-images"

    # Upload files
    scp "$exportDir\*.tar" root@${serverIP}:/root/docker-images/

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "[OK] Upload successful!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Now SSH to server and run deployment:" -ForegroundColor Yellow
        Write-Host "  ssh root@$serverIP" -ForegroundColor Cyan
        Write-Host "  bash /root/import-and-deploy.sh" -ForegroundColor Cyan
    } else {
        Write-Host ""
        Write-Host "[ERROR] Upload failed" -ForegroundColor Red
        Write-Host "Please use WinSCP to upload manually" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Press Enter to exit..." -ForegroundColor Gray
Read-Host
