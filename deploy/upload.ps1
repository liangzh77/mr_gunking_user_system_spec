# Simple Upload Script
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "MR Game Ops - Upload Tool" -ForegroundColor Cyan
Write-Host ""

$ServerIP = Read-Host "Server IP"
$ServerUser = Read-Host "SSH User (default: root)"

if ([string]::IsNullOrWhiteSpace($ServerUser)) {
    $ServerUser = "root"
}

Write-Host ""
Write-Host "Server: $ServerUser@$ServerIP" -ForegroundColor Yellow
Write-Host ""

$Confirm = Read-Host "Start upload? (Y/N)"
if ($Confirm -ne "Y" -and $Confirm -ne "y") {
    Write-Host "Cancelled" -ForegroundColor Yellow
    pause
    exit 0
}

Write-Host ""
Write-Host "Creating server directories..." -ForegroundColor Cyan
ssh "${ServerUser}@${ServerIP}" "mkdir -p /root/docker-images /root/mr-game-ops-upload"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Cannot connect to server!" -ForegroundColor Red
    pause
    exit 1
}

Write-Host "OK: Directories created" -ForegroundColor Green
Write-Host ""

# Get project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host "Project root: $ProjectRoot" -ForegroundColor Gray
Write-Host ""

# Upload docker images
Write-Host "Uploading Docker images (if exists)..." -ForegroundColor Cyan
if (Test-Path "C:\docker-images\*.tar") {
    scp "C:\docker-images\*.tar" "${ServerUser}@${ServerIP}:/root/docker-images/"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK: Images uploaded" -ForegroundColor Green
    }
} else {
    Write-Host "SKIP: No images found" -ForegroundColor Yellow
}

Write-Host ""

# Upload backend
Write-Host "Uploading backend..." -ForegroundColor Cyan
scp -r backend "${ServerUser}@${ServerIP}:/root/mr-game-ops-upload/"
if ($LASTEXITCODE -eq 0) {
    Write-Host "OK: Backend uploaded" -ForegroundColor Green
} else {
    Write-Host "ERROR: Backend upload failed" -ForegroundColor Red
    pause
    exit 1
}

# Upload frontend
if (Test-Path "frontend") {
    Write-Host "Uploading frontend..." -ForegroundColor Cyan
    scp -r frontend "${ServerUser}@${ServerIP}:/root/mr-game-ops-upload/"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK: Frontend uploaded" -ForegroundColor Green
    }
}

# Upload deploy
Write-Host "Uploading deploy..." -ForegroundColor Cyan
scp -r deploy "${ServerUser}@${ServerIP}:/root/mr-game-ops-upload/"
if ($LASTEXITCODE -eq 0) {
    Write-Host "OK: Deploy uploaded" -ForegroundColor Green
} else {
    Write-Host "ERROR: Deploy upload failed" -ForegroundColor Red
    pause
    exit 1
}

Write-Host ""
Write-Host "Upload Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. SSH to server:" -ForegroundColor White
Write-Host "     ssh ${ServerUser}@${ServerIP}" -ForegroundColor White
Write-Host ""
Write-Host "  2. Copy files to /opt/mr-game-ops:" -ForegroundColor White
Write-Host "     cp -r /root/mr-game-ops-upload/* /opt/mr-game-ops/" -ForegroundColor White
Write-Host ""
Write-Host "  3. Build and start frontend:" -ForegroundColor White
Write-Host "     cd /opt/mr-game-ops" -ForegroundColor White
Write-Host "     docker compose build frontend" -ForegroundColor White
Write-Host "     docker compose up -d" -ForegroundColor White
Write-Host ""

pause
