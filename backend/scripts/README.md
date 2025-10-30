# 管理脚本使用说明

本目录包含用于管理 MR 游戏运营管理系统账号的脚本。

## 📁 脚本列表

| 脚本文件 | 功能说明 |
|---------|---------|
| `create_admin_simple.py` | 创建初始管理员账号 |
| `create_admin.py` | 创建管理员账号（完整版） |
| `change_password.py` | 修改任意用户密码 |
| `manage_finance_user.py` | 管理财务用户（创建/修改密码/列表） |

## 🚀 使用方法

### 在容器中执行脚本

所有脚本都需要在 backend 容器中执行：

```bash
# 通用格式
docker exec mr_game_ops_backend_prod python /app/scripts/<脚本名>.py [参数]
```

---

## 📖 详细使用说明

### 1. 创建初始管理员（首次部署时使用）

```bash
docker exec mr_game_ops_backend_prod python /app/scripts/create_admin_simple.py
```

**默认凭据**：
- 用户名: `admin`
- 密码: `admin123`
- 角色: `super_admin`

---

### 2. 修改用户密码

```bash
# 修改管理员密码
docker exec mr_game_ops_backend_prod python /app/scripts/change_password.py admin NewPassword123!

# 修改财务用户密码
docker exec mr_game_ops_backend_prod python /app/scripts/change_password.py finance001 NewPassword456!
```

**参数说明**：
- 第1个参数：用户名
- 第2个参数：新密码

---

### 3. 管理财务用户

#### 3.1 创建财务用户

```bash
docker exec mr_game_ops_backend_prod python /app/scripts/manage_finance_user.py create <用户名> <密码> <姓名> [邮箱] [手机]
```

**示例**：
```bash
# 完整参数
docker exec mr_game_ops_backend_prod python /app/scripts/manage_finance_user.py create finance001 Finance123! 张财务 zhang@example.com 13800138001

# 最少参数（邮箱和手机使用默认值）
docker exec mr_game_ops_backend_prod python /app/scripts/manage_finance_user.py create finance001 Finance123! 张财务
```

**财务用户权限**：
- `finance:read` - 查看财务信息
- `finance:recharge` - 充值操作
- `finance:refund` - 退款操作
- `invoice:read` - 查看发票
- `invoice:create` - 创建发票
- `statistics:read` - 查看统计数据

#### 3.2 修改财务用户密码

```bash
docker exec mr_game_ops_backend_prod python /app/scripts/manage_finance_user.py password <用户名> <新密码>
```

**示例**：
```bash
docker exec mr_game_ops_backend_prod python /app/scripts/manage_finance_user.py password finance001 NewPass789!
```

#### 3.3 列出所有用户

```bash
docker exec mr_game_ops_backend_prod python /app/scripts/manage_finance_user.py list
```

**输出示例**：
```
当前用户列表：
----------------------------------------------------------------------------------------------------
用户名           姓名            角色            邮箱                      状态     创建时间
----------------------------------------------------------------------------------------------------
admin           系统管理员       super_admin     admin@mrgameops.com       激活     2025-10-24 07:55:34
finance001      张财务          finance         zhang@example.com         激活     2025-10-24 12:00:00
----------------------------------------------------------------------------------------------------
总计: 2 个用户
```

---

## 🔒 安全建议

1. **首次部署后立即修改管理员密码**：
   ```bash
   docker exec mr_game_ops_backend_prod python /app/scripts/change_password.py admin YourStrongPassword!
   ```

2. **使用强密码**：
   - 至少 12 个字符
   - 包含大小写字母、数字和特殊字符
   - 不要使用常见单词或生日

3. **定期更换密码**：
   - 建议每 3-6 个月更换一次

4. **财务用户管理**：
   - 为每个财务人员创建独立账号
   - 离职时立即禁用账号

---

## ⚠️ 注意事项

1. **数据库连接**：
   - 所有脚本使用硬编码的数据库凭据
   - 如果修改了数据库密码，需要更新脚本中的连接字符串

2. **执行环境**：
   - 必须在 backend 容器中执行
   - 确保容器正在运行

3. **权限**：
   - 只有具有容器访问权限的管理员才能执行这些脚本

---

## 🛠️ 故障排查

### 问题：找不到模块 'src'

**原因**：脚本路径配置问题

**解决**：确保在容器的 `/app` 目录下执行脚本

### 问题：数据库连接失败

**原因**：数据库凭据不正确或数据库未启动

**解决**：
1. 检查数据库容器状态：`docker compose -f docker-compose.yml ps`
2. 检查数据库密码是否正确

### 问题：用户已存在

**原因**：尝试创建已存在的用户名

**解决**：
1. 使用不同的用户名
2. 或使用 `change_password.py` 修改现有用户的密码
