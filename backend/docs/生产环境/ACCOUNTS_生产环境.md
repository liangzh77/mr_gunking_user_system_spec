# 测试账号文档

本文档列出了开发和测试环境中可用的预置测试账号。

## 管理员账号

### 超级管理员
- **用户名**: `superadmin`
- **密码**: `Admin@123`
- **角色**: 超级管理员 (super_admin)
- **权限**: 全部权限
- **姓名**: 系统管理员
- **邮箱**: admin@example.com
- **手机**: 13800138000
- **登录入口**: http://localhost:5173/admin/login

### 普通管理员
- **用户名**: `admin`
- **密码**: `Admin@123`
- **角色**: 管理员 (admin)
- **权限**: 运营商管理、应用管理、财务查看
- **姓名**: 张管理
- **邮箱**: zhang@example.com
- **手机**: 13800138001
- **登录入口**: http://localhost:5173/admin/login

### 系统配置管理员
- **用户名**: `admin_li`
- **密码**: `Admin@123`
- **角色**: 管理员 (admin)
- **权限**: 系统配置、运营商查看
- **姓名**: 李管理
- **邮箱**: li@example.com
- **手机**: 13800138002
- **登录入口**: http://localhost:5173/admin/login

## 财务账号

### 财务专员 - 王
- **用户名**: `finance_wang`
- **密码**: `Admin@123` (已修复)
- **角色**: 财务专员 (specialist)
- **权限**: 充值审核、发票查看、财务报表查看
- **姓名**: 王财务
- **邮箱**: wang@example.com
- **手机**: 13800138003
- **登录入口**: http://localhost:5173/finance/login
- **备注**: ⚠️ 种子数据中的密码hash需要修复

### 财务专员 - 刘
- **用户名**: `finance_liu`
- **密码**: `Admin@123` (需要同样修复)
- **角色**: 财务专员 (specialist)
- **权限**: 发票管理、财务报表查看
- **姓名**: 刘财务
- **邮箱**: liu@example.com
- **手机**: 13800138004
- **登录入口**: http://localhost:5173/finance/login
- **备注**: ⚠️ 种子数据中的密码hash需要修复

## 运营商账号

### 测试运营商 (E2E测试创建)
- **用户名**: `testoperator001`
- **密码**: `TestPass123`
- **姓名/公司**: 测试运营商公司
- **邮箱**: testop001@example.com
- **手机**: 13900139001
- **登录入口**: http://localhost:5173/operator/login
- **备注**: 通过注册页面创建的测试账号

## 修复财务账号密码

如果财务账号无法登录，执行以下SQL命令修复密码：

```sql
-- 连接到数据库
docker exec -it mr_game_ops_db psql -U mr_admin -d mr_game_ops

-- 复制管理员密码hash到财务账号
UPDATE finance_accounts
SET password_hash = (SELECT password_hash FROM admin_accounts WHERE username = 'superadmin')
WHERE username = 'finance_wang';

UPDATE finance_accounts
SET password_hash = (SELECT password_hash FROM admin_accounts WHERE username = 'superadmin')
WHERE username = 'finance_liu';

-- 退出数据库
\q
```

修复后，财务账号密码将与管理员账号一致：`Admin@123`

## 快速访问链接

### 开发环境 (Docker)
- **运营商登录**: http://localhost:5173/operator/login
- **运营商注册**: http://localhost:5173/operator/register
- **管理员登录**: http://localhost:5173/admin/login
- **财务登录**: http://localhost:5173/finance/login
- **API文档**: http://localhost:8000/api/docs
- **健康检查**: http://localhost:8000/health

### 数据库管理工具
- **PgAdmin**: http://localhost:5050
  - 邮箱: admin@mrgameops.com
  - 密码: admin_password
- **Redis Commander**: http://localhost:8081

## 安全提示

⚠️ **重要**: 这些账号仅用于开发和测试环境！

- 生产环境部署前必须修改所有默认密码
- 禁用或删除测试账号
- 使用强密码策略
- 启用多因素认证（如果支持）
- 定期审计账号权限

## 相关文件

- 种子数据脚本: `backend/scripts/seed_data.sql`
- 密码工具: `backend/src/core/utils/password.py`
- 环境配置: `backend/.env.development`

## 更新日志

- **2025-10-28**: 创建测试账号文档
- **2025-10-28**: 修复财务账号密码配置问题
- **2025-10-28**: 添加E2E测试创建的运营商账号

## 使用 PgAdmin 查看账户信息

### 1. 登录 PgAdmin

访问 http://localhost:5050 并使用以下凭据登录：
- **邮箱**: `admin@mrgameops.com`
- **密码**: `admin_password`

### 2. 连接到数据库服务器

首次使用需要添加服务器连接：

1. 点击左侧 "Add New Server"（或右键 "Servers" → "Register" → "Server"）
2. 在 **General** 标签页:
   - **Name**: `MR Game Ops DB`
3. 在 **Connection** 标签页:
   - **Host name/address**: `postgres`（Docker容器名称）
   - **Port**: `5432`
   - **Maintenance database**: `mr_game_ops`
   - **Username**: `mr_admin`
   - **Password**: `mr_secure_password_2024`
   - ✅ 勾选 "Save password"
4. 点击 "Save"

### 3. 查看账户信息

连接成功后，按以下路径导航：

```
Servers
  └─ MR Game Ops DB
      └─ Databases
          └─ mr_game_ops
              └─ Schemas
                  └─ public
                      └─ Tables
```

#### 方法1: 直接查看表数据

右键点击表名 → "View/Edit Data" → "All Rows"

- **admin_accounts** - 管理员账号
- **finance_accounts** - 财务账号
- **operator_accounts** - 运营商账号

#### 方法2: 使用 SQL 查询

1. 右键点击 `mr_game_ops` 数据库
2. 选择 "Query Tool"（或按 Alt+Shift+Q）
3. 执行以下 SQL 语句

**查看所有管理员账号**:
```sql
SELECT username, full_name, email, phone, role, is_active
FROM admin_accounts
ORDER BY username;
```

**查看所有财务账号**:
```sql
SELECT username, full_name, email, phone, role, is_active
FROM finance_accounts
ORDER BY username;
```

**查看所有运营商账号**:
```sql
SELECT username, company_name, email, phone, balance, total_recharge, is_active
FROM operator_accounts
ORDER BY created_at DESC;
```

**查看所有账号（汇总视图）**:
```sql
SELECT 'Admin' as account_type, username, full_name as name,
       email, phone, role, is_active
FROM admin_accounts
UNION ALL
SELECT 'Finance' as account_type, username, full_name as name,
       email, phone, role, is_active
FROM finance_accounts
UNION ALL
SELECT 'Operator' as account_type, username, company_name as name,
       email, phone, 'operator' as role, is_active
FROM operator_accounts
ORDER BY account_type, username;
```

### 4. 关于密码字段

**重要**: 数据库中的 `password_hash` 字段存储的是 bcrypt 加密后的哈希值，类似：

```
$2b$12$Vx7X1BhBCDhR9i3EnKftwuXrWgbpFqrVfc3vbOIacp.8y3D0Y3mWG
```

这是正常的安全设计，**无法从哈希值反推出明文密码**。所有账号的明文密码请参考本文档开头的账号列表。

### 5. PgAdmin 快捷操作

- **运行查询**: F5 或点击 ▶️ 按钮
- **格式化 SQL**: Ctrl+Shift+F
- **清空查询**: Ctrl+L
- **保存查询**: Ctrl+S
- **导出结果**: 点击下载图标 💾

## 快速管理工具

### Windows 管理脚本

**文件**: `backend/docs/manage_accounts_生产环境.bat`

这是一个交互式账户管理工具，提供以下功能：

#### 功能列表

1. **查看所有账户** - 显示所有账户类型的汇总列表
2. **查看管理员账户详情** - 显示管理员权限和详细信息
3. **查看财务账户详情** - 显示财务人员权限和详细信息
4. **查看运营商账户详情** - 显示运营商余额和创建时间
5. **重置账户密码** - 将任意账户密码重置为 `Admin@123`
6. **删除账户** - 软删除账户（设置为 inactive 或 deleted_at）

#### 使用方法

```cmd
cd backend\docs
manage_accounts_生产环境.bat
```

#### 重置密码示例

1. 选择菜单选项 `5` (重置账户密码)
2. 选择账户类型 (1=管理员, 2=财务, 3=运营商)
3. 输入用户名，例如: `finance_wang`
4. 确认操作 (Y/N)
5. 密码将被重置为: `Admin@123`

#### 删除账户示例

1. 选择菜单选项 `6` (删除账户)
2. 选择账户类型
3. 输入用户名
4. 输入 `DELETE` 确认删除
5. 账户将被设置为 inactive 状态

⚠️ **安全提示**:
- 删除操作需要输入 `DELETE` 确认，防止误操作
- 运营商账户使用软删除 (设置 `deleted_at` 字段)
- 管理员和财务账户设置为 `is_active = false`
- 删除操作不会真正删除数据库记录
