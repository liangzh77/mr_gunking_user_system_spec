# =============================================================================
# PowerShell - 上传项目文件到服务器 (推荐使用，无乱码问题)
# =============================================================================

# 设置控制台编码为UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  MR游戏运营管理系统 - 文件上传工具 (PowerShell版)" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

# 检查SCP
if (-not (Get-Command scp -ErrorAction SilentlyContinue)) {
    Write-Host "[错误] SCP命令不可用！" -ForegroundColor Red
    Write-Host ""
    Write-Host "请安装OpenSSH客户端：" -ForegroundColor Yellow
    Write-Host "  Windows 10/11: 设置 > 应用 > 可选功能 > 添加功能 > OpenSSH客户端" -ForegroundColor Yellow
    Write-Host "  或使用WinSCP图形界面工具: https://winscp.net/" -ForegroundColor Yellow
    Write-Host ""
    pause
    exit 1
}

# 获取服务器信息
Write-Host "请输入服务器信息:" -ForegroundColor Green
Write-Host ""

$ServerIP = Read-Host "服务器IP地址"
$ServerUser = Read-Host "SSH用户名 [默认: root]"

if ([string]::IsNullOrWhiteSpace($ServerUser)) {
    $ServerUser = "root"
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
Write-Host "  服务器: $ServerUser@$ServerIP" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
Write-Host ""

# 确认
$Confirm = Read-Host "确认开始上传？(Y/N)"
if ($Confirm -ne "Y" -and $Confirm -ne "y") {
    Write-Host "已取消" -ForegroundColor Yellow
    pause
    exit 0
}

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  步骤1/3: 创建服务器目录" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

# 创建服务器目录
$CreateDirCmd = "mkdir -p /root/docker-images /root/mr-game-ops-upload"
ssh "$ServerUser@$ServerIP" $CreateDirCmd

if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] 无法连接到服务器！" -ForegroundColor Red
    Write-Host "请检查：" -ForegroundColor Yellow
    Write-Host "  1. 服务器IP地址是否正确" -ForegroundColor Yellow
    Write-Host "  2. SSH服务是否运行" -ForegroundColor Yellow
    Write-Host "  3. 防火墙是否允许SSH连接" -ForegroundColor Yellow
    Write-Host ""
    pause
    exit 1
}

Write-Host "[成功] 服务器目录已创建" -ForegroundColor Green
Write-Host ""

# 获取项目根目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "项目根目录: $ProjectRoot" -ForegroundColor Gray
Write-Host ""

# 切换到项目根目录
Set-Location $ProjectRoot

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  步骤2/3: 上传Docker镜像 (如果存在)" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

if (Test-Path "C:\docker-images\*.tar") {
    Write-Host "正在上传Docker镜像..." -ForegroundColor Yellow
    Write-Host "提示: 这可能需要较长时间，取决于文件大小和网速" -ForegroundColor Gray
    Write-Host ""

    scp C:\docker-images\*.tar "$ServerUser@$ServerIP:/root/docker-images/"

    if ($LASTEXITCODE -eq 0) {
        Write-Host "[成功] 镜像文件已上传" -ForegroundColor Green
    } else {
        Write-Host "[警告] 镜像上传失败" -ForegroundColor Yellow
    }
    Write-Host ""
} else {
    Write-Host "[跳过] 未找到Docker镜像文件: C:\docker-images\*.tar" -ForegroundColor Yellow
    Write-Host "如果已经上传过，可以忽略此警告" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  步骤3/3: 上传项目文件" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "正在上传项目文件..." -ForegroundColor Yellow
Write-Host ""

# 上传backend
Write-Host "[1/3] 上传backend目录..." -ForegroundColor Cyan
scp -r backend "$ServerUser@$ServerIP:/root/mr-game-ops-upload/"
if ($LASTEXITCODE -eq 0) {
    Write-Host "      [成功]" -ForegroundColor Green
} else {
    Write-Host "[错误] backend上传失败" -ForegroundColor Red
    pause
    exit 1
}

# 上传frontend
if (Test-Path "frontend") {
    Write-Host "[2/3] 上传frontend目录..." -ForegroundColor Cyan
    scp -r frontend "$ServerUser@$ServerIP:/root/mr-game-ops-upload/"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "      [成功]" -ForegroundColor Green
    } else {
        Write-Host "      [警告] frontend上传失败" -ForegroundColor Yellow
    }
} else {
    Write-Host "[2/3] [跳过] frontend目录不存在" -ForegroundColor Yellow
}

# 上传deploy
Write-Host "[3/3] 上传deploy目录..." -ForegroundColor Cyan
scp -r deploy "$ServerUser@$ServerIP:/root/mr-game-ops-upload/"
if ($LASTEXITCODE -eq 0) {
    Write-Host "      [成功]" -ForegroundColor Green
} else {
    Write-Host "[错误] deploy上传失败" -ForegroundColor Red
    pause
    exit 1
}

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Green
Write-Host "  ✅ 上传完成！" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Green
Write-Host ""

Write-Host "服务器文件位置:" -ForegroundColor Cyan
Write-Host "  - 项目文件: /root/mr-game-ops-upload/" -ForegroundColor White
Write-Host "  - 镜像文件: /root/docker-images/" -ForegroundColor White
Write-Host ""

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
Write-Host "  下一步: SSH到服务器并执行部署脚本" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
Write-Host ""

Write-Host "方法1: 使用PowerShell/CMD" -ForegroundColor Cyan
Write-Host "  ssh $ServerUser@$ServerIP" -ForegroundColor White
Write-Host "  bash /root/mr-game-ops-upload/deploy/一键部署脚本-服务器端.sh" -ForegroundColor White
Write-Host ""

Write-Host "方法2: 使用PuTTY等SSH客户端" -ForegroundColor Cyan
Write-Host "  1. 连接到 $ServerIP" -ForegroundColor White
Write-Host "  2. 执行: bash /root/mr-game-ops-upload/deploy/一键部署脚本-服务器端.sh" -ForegroundColor White
Write-Host ""

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow
Write-Host ""

pause
