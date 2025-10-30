# 生产环境管理脚本

本目录包含生产环境的账户管理脚本和文档。

## 📁 文件说明

| 文件名 | 说明 |
|--------|------|
| `账户管理-生产环境.md` | 详细的账户管理手册 |
| `manage_accounts.sh` | 账户管理自动化脚本（Linux/Mac） |
| `README.md` | 本文件 |

## 🚀 快速开始

### Linux / Mac 用户

#### 1. 上传脚本到生产服务器

```bash
# 方法1：使用 git（推荐）
cd /opt/mr_gunking_user_system_spec
git pull origin 001-mr-v2

# 方法2：使用 scp 上传
scp docs/生产环境/manage_accounts.sh root@your-server:/opt/mr_gunking_user_system_spec/docs/生产环境/
```

#### 2. 赋予执行权限

```bash
cd /opt/mr_gunking_user_system_spec/docs/生产环境
chmod +x manage_accounts.sh
```

#### 3. 运行脚本

**交互式菜单模式：**
```bash
./manage_accounts.sh
```

会显示如下菜单：
```
=========================================
   MR游戏运营管理系统 - 账户管理
=========================================

1. 查看所有管理员账户
2. 查看所有运营商账户
3. 创建管理员账户
4. 创建运营商账户
5. 重置账户密码
6. 启用/禁用账户
7. 修改管理员角色
8. 批量创建运营商
9. 导出账户信息
0. 退出
```

**命令行模式：**
```bash
# 列出所有管理员
./manage_accounts.sh list-admins

# 列出所有运营商
./manage_accounts.sh list-operators

# 创建管理员（交互式输入）
./manage_accounts.sh create-admin

# 创建运营商（交互式输入）
./manage_accounts.sh create-operator

# 重置密码（交互式输入）
./manage_accounts.sh reset-password
```

## 📋 功能详解

### 1. 查看所有管理员账户

显示所有管理员的详细信息，包括：
- 用户名
- 姓名
- 邮箱
- 角色（super_admin / admin）
- 状态（激活/禁用）
- 创建时间

### 2. 查看所有运营商账户

显示所有运营商的详细信息，包括：
- 用户名
- 姓名
- 邮箱
- 电话
- 账户余额
- 状态（激活/禁用）
- 创建时间

### 3. 创建管理员账户

交互式创建管理员账户，需要输入：
- 用户名（唯一，不能重复）
- 密码（建议使用强密码）
- 姓名
- 邮箱
- 电话
- 角色选择（super_admin 或 admin）

### 4. 创建运营商账户

交互式创建运营商账户，需要输入：
- 用户名（唯一，不能重复）
- 密码（建议使用强密码）
- 运营商名称
- 邮箱
- 电话
- 初始余额（默认1000元）

### 5. 重置账户密码

重置管理员或运营商的密码：
1. 选择账户类型（管理员/运营商）
2. 输入用户名
3. 输入新密码
4. 确认重置

### 6. 启用/禁用账户

启用或禁用账户：
1. 选择账户类型
2. 输入用户名
3. 选择操作（启用/禁用）

禁用的账户无法登录系统。

### 7. 修改管理员角色

修改管理员的角色权限：
1. 输入用户名
2. 选择新角色（super_admin / admin）

### 8. 批量创建运营商

从 CSV 文件批量导入运营商账户。

**CSV 格式：**
```csv
username,password,full_name,email,phone,initial_balance
operator1,Pass123!,运营商一,op1@example.com,13800000001,1000
operator2,Pass123!,运营商二,op2@example.com,13800000002,2000
operator3,Pass123!,运营商三,op3@example.com,13800000003,1500
```

**使用步骤：**
1. 准备 CSV 文件（如 operators.csv）
2. 运行脚本选择"8"
3. 输入 CSV 文件路径
4. 脚本自动批量创建

### 9. 导出账户信息

将账户信息导出为 CSV 文件，可选择：
- 仅导出管理员账户
- 仅导出运营商账户
- 导出所有账户

导出文件会保存在当前目录，文件名格式：
- `admins_20250128_143022.csv`
- `operators_20250128_143022.csv`

## 🔐 安全注意事项

1. **脚本权限**：
   - 确保脚本只有管理员可以执行
   - 建议设置权限：`chmod 700 manage_accounts.sh`

2. **密码安全**：
   - 首次部署后立即修改所有默认密码
   - 使用强密码（至少12位，包含大小写字母、数字、特殊字符）
   - 定期更换密码（建议每3个月）

3. **账户审计**：
   - 定期检查账户列表
   - 禁用不活跃的账户
   - 监控异常登录

4. **导出文件**：
   - 导出的 CSV 文件包含敏感信息
   - 使用后及时删除或加密保存
   - 不要上传到公开的版本控制系统

5. **日志记录**：
   - 所有账户操作都会记录在数据库日志中
   - 定期检查审计日志

## 🛠️ 故障排除

### 问题1：脚本报错"后端容器未运行"

**解决方法：**
```bash
# 检查容器状态
docker-compose -f docker-compose.yml ps

# 如果未运行，启动服务
docker-compose -f docker-compose.yml up -d
```

### 问题2：脚本报错"权限不足"

**解决方法：**
```bash
# 赋予执行权限
chmod +x manage_accounts.sh

# 或使用 bash 执行
bash manage_accounts.sh
```

### 问题3：创建账户时提示"用户名已存在"

**解决方法：**
```bash
# 先查看现有账户
./manage_accounts.sh list-admins
./manage_accounts.sh list-operators

# 使用不同的用户名重试
```

### 问题4：无法连接到数据库

**解决方法：**
```bash
# 检查数据库容器状态
docker-compose -f docker-compose.yml ps postgres

# 查看数据库日志
docker-compose -f docker-compose.yml logs postgres

# 重启数据库（谨慎操作）
docker-compose -f docker-compose.yml restart postgres
```

## 📚 相关文档

- [账户管理详细手册](./账户管理-生产环境.md)
- [生产环境部署指南](./生产环境部署指南.md)
- [离线部署指南](./离线部署指南.md)

## 💡 使用示例

### 示例1：查看所有账户

```bash
# 查看管理员
./manage_accounts.sh list-admins

# 查看运营商
./manage_accounts.sh list-operators
```

### 示例2：创建新管理员

```bash
./manage_accounts.sh create-admin

# 按提示输入：
# 用户名: zhang_admin
# 密码: MySecure123!@#
# 姓名: 张三
# 邮箱: zhang@example.com
# 电话: 13800138001
# 角色: 2 (admin)
```

### 示例3：重置超级管理员密码

```bash
./manage_accounts.sh reset-password

# 按提示输入：
# 账户类型: 1 (管理员)
# 用户名: superadmin
# 新密码: NewAdmin123!@#
```

### 示例4：批量创建运营商

```bash
# 1. 创建 CSV 文件
cat > operators.csv << EOF
username,password,full_name,email,phone,initial_balance
shop_001,Pass123!,一号店,shop001@example.com,13800000001,5000
shop_002,Pass123!,二号店,shop002@example.com,13800000002,3000
shop_003,Pass123!,三号店,shop003@example.com,13800000003,4000
EOF

# 2. 运行批量导入
./manage_accounts.sh

# 选择 8，输入 CSV 路径：operators.csv
```

### 示例5：导出账户备份

```bash
./manage_accounts.sh

# 选择 9（导出账户信息）
# 选择 3（导出所有账户）

# 会生成两个文件：
# - admins_20250128_143022.csv
# - operators_20250128_143022.csv
```

## 🔄 定期维护任务

建议建立以下定期维护计划：

### 每周任务
- [ ] 检查账户列表，确认无异常账户
- [ ] 查看近期登录日志

### 每月任务
- [ ] 导出账户信息备份
- [ ] 审计账户权限
- [ ] 禁用长期未使用的账户

### 每季度任务
- [ ] 强制所有管理员更换密码
- [ ] 审查超级管理员数量
- [ ] 清理测试账户

## 📞 技术支持

如遇到问题，请：
1. 查看 [账户管理详细手册](./账户管理-生产环境.md)
2. 检查容器和数据库状态
3. 查看日志文件排查问题
4. 联系技术支持团队
