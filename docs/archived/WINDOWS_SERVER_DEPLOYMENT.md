# Windows服务器生产部署指南

本指南专门针对使用**Windows Server**进行生产部署的场景。

---

## ⚠️ 重要建议

### 核心建议：考虑改用Linux服务器

**强烈建议使用Linux服务器**（Ubuntu 20.04/22.04 LTS）进行生产部署，原因如下：

| 对比项 | Linux服务器 | Windows服务器 |
|--------|------------|--------------|
| **Docker支持** | 原生支持，性能最优 | 需要WSL2或Hyper-V |
| **性能** | 更优（尤其是容器） | 较慢（虚拟化开销） |
| **成本** | 通常更低 | 许可证费用更高 |
| **社区支持** | 大量Docker部署案例 | 案例较少 |
| **维护复杂度** | 简单 | 复杂 |
| **推荐度** | ⭐⭐⭐⭐⭐ | ⭐⭐ |

---

## 方案对比

### 方案A：Windows Server + WSL2 + Docker Desktop（推荐）

**适用场景：**
- 必须使用Windows Server
- 有公网域名
- 需要HTTPS

**步骤概要：**
1. 安装WSL2
2. 安装Docker Desktop for Windows
3. 配置Docker使用WSL2后端
4. 按照Linux部署流程进行

**优点：**
- 接近Linux性能
- 可使用现有Docker配置
- 开发调试方便

**缺点：**
- 需要Windows Server 2019+
- 额外的虚拟化开销
- 某些网络配置较复杂

---

### 方案B：Windows Server + IIS + 传统部署（不推荐）

**适用场景：**
- 企业政策要求Windows IIS
- 不允许使用Docker

**说明：**
本项目设计时已针对Docker优化，传统Windows IIS部署需要大量修改：
- 使用IIS而不是Nginx
- Python通过WSGI配置到IIS
- PostgreSQL需要Windows版本
- 前端需要重新构建流程

**不推荐原因：**
- 配置复杂度极高
- 性能不如Linux
- 维护成本大

---

## 方案A详细步骤：Windows Server + Docker

### 前置要求

```
- Windows Server 2019或2022（推荐2022）
- 4核+ CPU
- 8GB+ RAM
- 60GB+ 硬盘
- 公网IP + 域名
- 管理员权限
```

### 步骤1：启用WSL2

```powershell
# 以管理员身份运行PowerShell

# 启用WSL功能
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

# 启用虚拟机平台
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# 重启服务器
Restart-Computer
```

### 步骤2：安装WSL2更新包

重启后：

```powershell
# 下载并安装WSL2 Linux内核更新包
# https://aka.ms/wsl2kernel

# 设置WSL2为默认版本
wsl --set-default-version 2

# 安装Ubuntu发行版
wsl --install -d Ubuntu-22.04
```

### 步骤3：安装Docker Desktop

1. 下载Docker Desktop for Windows：https://www.docker.com/products/docker-desktop/
2. 安装时选择"Use WSL2 instead of Hyper-V"
3. 安装完成后重启服务器
4. 启动Docker Desktop
5. 进入Settings → General → 确认"Use the WSL 2 based engine"已勾选

### 步骤4：验证安装

```powershell
# 验证Docker
docker --version
docker-compose --version

# 测试运行
docker run hello-world
```

### 步骤5：克隆项目

```powershell
# 在Windows上
cd C:\
git clone <你的仓库URL> mr_game_ops
cd mr_game_ops
```

### 步骤6：配置环境变量

```powershell
# 编辑backend\.env.production
notepad backend\.env.production

# 修改以下配置（使用步骤7生成的密钥）：
# SECRET_KEY=...
# JWT_SECRET_KEY=...
# ENCRYPTION_KEY=...（必须32字符）
# DATABASE_URL=postgresql+asyncpg://mr_admin:你的强密码@postgres:5432/mr_game_ops
# REDIS_PASSWORD=你的Redis密码
# CORS_ORIGINS=["https://你的域名.com"]
# DEBUG=false
# ENVIRONMENT=production
```

### 步骤7：生成密钥

```powershell
# 使用Python生成密钥
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('ENCRYPTION_KEY=' + secrets.token_urlsafe(24)[:32])"
python -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(16))"
python -c "import secrets; print('REDIS_PASSWORD=' + secrets.token_urlsafe(16))"

# 保存这些输出，填入.env.production文件
```

### 步骤8：配置SSL证书（Windows版Let's Encrypt）

#### 方式1：使用win-acme（推荐）

```powershell
# 下载win-acme
# https://github.com/win-acme/win-acme/releases

# 解压到C:\win-acme
cd C:\win-acme

# 运行并按提示操作
.\wacs.exe

# 选择：
# N - Create new certificate (simple for IIS)
# 输入你的域名
# 输入邮箱
# 证书会自动生成到C:\win-acme\Certificates

# 复制证书到项目目录
copy "C:\win-acme\Certificates\你的域名.com\*.*" "C:\mr_game_ops\nginx\ssl\"
```

#### 方式2：使用自签名证书（仅测试）

```powershell
cd C:\mr_game_ops\nginx\ssl

# 使用OpenSSL（需要先安装）
# 或使用PowerShell生成
$cert = New-SelfSignedCertificate -DnsName "你的域名.com" -CertStoreLocation "cert:\LocalMachine\My"
$pwd = ConvertTo-SecureString -String "password123" -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath ".\certificate.pfx" -Password $pwd

# 转换为PEM格式（需要OpenSSL）
openssl pkcs12 -in certificate.pfx -out fullchain.pem -nodes
openssl pkcs12 -in certificate.pfx -nocerts -out privkey.pem -nodes
```

### 步骤9：修改Nginx配置

```powershell
notepad nginx\conf.d\mr_game_ops.conf

# 修改：
# server_name 你的域名.com;
```

### 步骤10：启动服务

```powershell
# 设置环境变量
$env:POSTGRES_PASSWORD="你的数据库密码"
$env:REDIS_PASSWORD="你的Redis密码"

# 启动服务
docker-compose -f docker-compose.yml up -d

# 查看状态
docker-compose -f docker-compose.yml ps
```

### 步骤11：初始化数据库

```powershell
# 等待30秒让服务完全启动
Start-Sleep -Seconds 30

# 运行数据库迁移
docker exec mr_game_ops_backend_prod alembic upgrade head

# 初始化数据
docker exec mr_game_ops_backend_prod python init_data.py
```

### 步骤12：配置Windows防火墙

```powershell
# 允许HTTP和HTTPS
New-NetFirewallRule -DisplayName "Allow HTTP" -Direction Inbound -LocalPort 80 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "Allow HTTPS" -Direction Inbound -LocalPort 443 -Protocol TCP -Action Allow
```

### 步骤13：验证部署

```powershell
# 测试健康检查
Invoke-WebRequest -Uri http://localhost:8000/health

# 访问
# https://你的域名.com
```

---

## Windows特有问题及解决方案

### 问题1：路径问题

**症状：** Docker挂载Windows路径失败

**解决：**
```yaml
# docker-compose.yml中
volumes:
  - C:/mr_game_ops/backend:/app  # 使用正斜杠
  # 而不是 C:\mr_game_ops\backend:/app
```

### 问题2：性能问题

**症状：** Docker容器运行缓慢

**解决：**
1. 确保WSL2正确配置
2. 将项目文件放在WSL2文件系统中而不是Windows文件系统
3. 调整Docker Desktop资源限制（Settings → Resources）

### 问题3：网络问题

**症状：** 容器间无法通信

**解决：**
```powershell
# 检查Docker网络
docker network ls
docker network inspect mr_gunking_user_system_spec_mr_network

# 重启Docker Desktop
Restart-Service com.docker.service
```

### 问题4：端口冲突

**症状：** 端口80/443被IIS占用

**解决：**
```powershell
# 停止IIS
Stop-Service W3SVC

# 或修改docker-compose.yml使用其他端口
ports:
  - "8080:80"   # HTTP
  - "8443:443"  # HTTPS
```

---

## 维护和监控

### 日志查看

```powershell
# 查看所有服务日志
docker-compose -f docker-compose.yml logs -f

# 查看特定服务
docker-compose -f docker-compose.yml logs -f backend

# 导出日志
docker-compose -f docker-compose.yml logs > logs.txt
```

### 数据库备份

```powershell
# 备份
docker exec mr_game_ops_db_prod pg_dump -U mr_admin mr_game_ops > backup_$(Get-Date -Format "yyyyMMdd").sql

# 压缩
Compress-Archive -Path backup_*.sql -DestinationPath backups\backup_$(Get-Date -Format "yyyyMMdd").zip

# 恢复
Get-Content backup_20251016.sql | docker exec -i mr_game_ops_db_prod psql -U mr_admin mr_game_ops
```

### 定期任务（计划任务）

```powershell
# 创建每日备份计划任务
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-File C:\mr_game_ops\scripts\backup.ps1"
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "MR Game Ops Backup" -Description "Daily database backup"
```

---

## 性能优化

### Docker资源限制

在Docker Desktop → Settings → Resources中调整：

```
CPU: 4核（推荐至少2核）
内存: 4GB（推荐至少8GB）
磁盘: 60GB
```

### Windows Server优化

```powershell
# 禁用不必要的服务
Set-Service -Name "WSearch" -StartupType Disabled
Set-Service -Name "SysMain" -StartupType Disabled

# 优化网络
Set-NetAdapterAdvancedProperty -Name "Ethernet" -DisplayName "Jumbo Packet" -DisplayValue "9014 Bytes"
```

---

## 常见命令速查

```powershell
# 启动服务
docker-compose -f docker-compose.yml up -d

# 停止服务
docker-compose -f docker-compose.yml down

# 重启服务
docker-compose -f docker-compose.yml restart

# 查看状态
docker-compose -f docker-compose.yml ps

# 查看资源使用
docker stats

# 进入容器
docker exec -it mr_game_ops_backend_prod bash

# 查看日志
docker-compose -f docker-compose.yml logs -f backend

# 更新部署
git pull
docker-compose -f docker-compose.yml build
docker-compose -f docker-compose.yml up -d
docker exec mr_game_ops_backend_prod alembic upgrade head
```

---

## 迁移到Linux服务器

如果后续决定迁移到Linux服务器：

### 步骤1：数据备份

```powershell
# 在Windows服务器上
docker exec mr_game_ops_db_prod pg_dump -U mr_admin mr_game_ops > database_export.sql
```

### 步骤2：在Linux服务器上部署

```bash
# 在Linux服务器上
# 按照 docs/DEPLOYMENT.md 部署
docker-compose -f docker-compose.yml up -d

# 恢复数据
cat database_export.sql | docker exec -i mr_game_ops_db_prod psql -U mr_admin mr_game_ops
```

### 步骤3：DNS切换

将域名DNS记录指向新的Linux服务器IP

---

## 支持和帮助

- **完整部署文档**：`docs/DEPLOYMENT.md`
- **快速参考**：`docs/PRODUCTION_QUICKSTART.md`
- **实战指南**：`docs/PRODUCTION_DEPLOYMENT_GUIDE.md`

---

## 总结

**Windows Server部署可行，但不是最优选择。**

推荐顺序：
1. ⭐⭐⭐⭐⭐ **Linux服务器 + Docker**（最推荐）
2. ⭐⭐⭐ **Windows Server + WSL2 + Docker**（可接受）
3. ⭐ **Windows Server + IIS + 传统部署**（不推荐）

如有可能，请考虑使用Linux服务器进行生产部署，以获得更好的性能、稳定性和社区支持。

---

**最后更新**：2025-10-16
