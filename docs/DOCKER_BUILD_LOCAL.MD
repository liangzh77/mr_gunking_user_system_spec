## 方案1：构建后推送到Docker Registry（推荐）

### 步骤1：本地构建并打标签
```bash
# 在本地使用生产环境配置构建
docker-compose build frontend backend

# 给镜像打标签（准备推送到Docker Hub或阿里云容器镜像服务）
docker tag mr_gunking_user_system_spec-backend:latest your-registry/mr-backend:v2.0
docker tag mr_gunking_user_system_spec-frontend:latest your-registry/mr-frontend:v2.0
```

### 步骤2：推送到镜像仓库
```bash
# 推送到Docker Hub
docker push your-registry/mr-backend:v2.0
docker push your-registry/mr-frontend:v2.0
```

### 步骤3：生产服务器拉取
```bash
# 在生产服务器上
docker pull your-registry/mr-backend:v2.0
docker pull your-registry/mr-frontend:v2.0

# 重新标记为本地名称
docker tag your-registry/mr-backend:v2.0 mr_gunking_user_system_spec-backend:latest
docker tag your-registry/mr-frontend:v2.0 mr_gunking_user_system_spec-frontend:latest

# 重启服务
docker-compose up -d
```

---

## 方案2：保存镜像为文件传输（不需要Registry）

### 步骤1：本地构建
```bash
# 在本地使用生产环境配置构建
docker-compose build frontend backend
```

### 步骤2：导出镜像为tar文件
```bash
# 导出backend镜像
docker save mr_gunking_user_system_spec-backend:latest -o backend-v2.0.tar

# 导出frontend镜像
docker save mr_gunking_user_system_spec-frontend:latest -o frontend-v2.0.tar
```

### 步骤3：上传到生产服务器
```bash
# 使用scp上传
scp backend-v2.0.tar root@mrgun.chu-jiao.com:/tmp/
scp frontend-v2.0.tar root@mrgun.chu-jiao.com:/tmp/
```

### 步骤4：生产服务器导入镜像
```bash
# SSH到生产服务器
ssh root@mrgun.chu-jiao.com

# 导入镜像
docker load -i /tmp/backend-v2.0.tar
docker load -i /tmp/frontend-v2.0.tar

# 清理tar文件
rm /tmp/backend-v2.0.tar /tmp/frontend-v2.0.tar

# 重启服务
cd /opt/mr_gunking_user_system_spec
docker-compose down
docker-compose up -d
```

---

## 我的推荐

使用方案2（镜像文件传输），因为：
- ✅ 不需要配置Docker Registry
- ✅ 简单直接
- ✅ 适合小团队

### 完整命令流程：
```bash
# === 本地执行 ===
cd C:\liangz77\python_projects\github_projects\mr_gunking_user_system_spec

# 1. 使用生产环境配置构建
docker-compose build frontend backend

# 2. 导出镜像
docker save mr_gunking_user_system_spec-backend:latest -o backend-v2.0.tar
docker save mr_gunking_user_system_spec-frontend:latest -o frontend-v2.0.tar

# 3. 上传到服务器
scp backend-v2.0.tar root@mrgun.chu-jiao.com:/tmp/
scp frontend-v2.0.tar root@mrgun.chu-jiao.com:/tmp/

# === 生产服务器执行 ===
ssh root@mrgun.chu-jiao.com
cd /opt/mr_gunking_user_system_spec

# 4. 导入镜像
docker load -i /tmp/backend-v2.0.tar
docker load -i /tmp/frontend-v2.0.tar

# 5. 重启服务
docker-compose down
docker-compose up -ds

# 6. 执行数据库迁移
docker-compose exec backend alembic upgrade head

# 7. 验证
docker-compose ps
curl -k https://mrgun.chu-jiao.com/api/v1/health
```