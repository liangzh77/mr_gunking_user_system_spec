# 开发环境账户管理

本目录包含本地开发环境的账户管理脚本和文档。

## 📁 文件说明

| 文件名 | 说明 |
|--------|------|
| `README.md` | 本文件 - 开发环境使用指南 |
| `manage_accounts.sh` | 账户管理脚本（Linux/Mac） |
| `manage_accounts.bat` | 账户管理脚本（Windows） |
| `operators_example.csv` | 批量导入运营商的示例文件 |
| `scripts/` | Python脚本目录（Windows版本使用） |

## 🔄 与生产环境的区别

| 项目 | 开发环境 | 生产环境 |
|------|---------|---------|
| 容器名称 | `mr_game_ops_backend` | `mr_game_ops_backend_prod` |
| Docker Compose 文件 | `docker-compose.yml` | `docker-compose.prod.yml` |
| 数据库 | 本地测试数据 | 生产真实数据 |
| 端口 | 前端 5173，后端 8000 | 前端 80，后端 8000 |
| 使用场景 | 开发、测试、调试 | 生产部署 |

## 🚀 快速开始

### 1. 确保开发环境已启动

```bash
# 在项目根目录
docker-compose up -d

# 检查容器状态
docker-compose ps
```

### 2. 选择对应平台的脚本

#### Linux/Mac 用户

```bash
cd docs/开发环境
chmod +x manage_accounts.sh
./manage_accounts.sh
```

#### Windows 用户

```cmd
cd docs\开发环境
.\manage_accounts.bat
```

或在PowerShell中：
```powershell
cd docs\开发环境
.\manage_accounts.bat
```

### 3. 运行脚本

**交互式菜单模式：**
```bash
# Linux/Mac
./manage_accounts.sh

# Windows
./manage_accounts.bat
```

会显示如下菜单：
```
=========================================
   MR游戏运营管理系统 - 账户管理
   (开发环境)
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

## 💡 使用示例

### 示例1：查看所有管理员账户

```bash
./manage_accounts.sh list-admins
```

输出示例：
```
====================================================================================================
用户名           姓名            邮箱                       角色          状态      创建时间
====================================================================================================
superadmin     超级管理员       admin@example.com          super_admin  ✅ 激活   2025-01-28 10:30:15
testadmin      测试管理员       test@example.com           admin        ✅ 激活   2025-01-28 10:31:22
====================================================================================================

共 2 个管理员账户
```

### 示例2：创建测试运营商

```bash
./manage_accounts.sh create-operator

# 按提示输入：
# 用户名: dev_test_01
# 密码: TestPass123!
# 运营商名称: 开发测试运营商
# 邮箱: dev01@test.com
# 电话: 13800138000
# 初始余额: 5000
```

### 示例3：批量创建测试运营商

```bash
# 使用提供的示例文件
./manage_accounts.sh

# 选择 8（批量创建运营商）
# 输入文件路径: operators_example.csv
```

### 示例4：重置开发账户密码

```bash
./manage_accounts.sh reset-password

# 按提示输入：
# 账户类型: 2 (运营商)
# 用户名: dev_test_01
# 新密码: NewPass123!
```

## 🧪 测试场景

### 场景1：初始化开发数据

```bash
# 1. 创建测试管理员
./manage_accounts.sh create-admin
# 用户名: dev_admin
# 密码: DevAdmin123!
# 姓名: 开发管理员
# 邮箱: dev@example.com
# 电话: 13900000000
# 角色: 2 (admin)

# 2. 批量创建测试运营商
./manage_accounts.sh
# 选择 8, 使用 operators_example.csv
```

### 场景2：测试权限管理

```bash
# 1. 创建普通管理员
./manage_accounts.sh create-admin
# 用户名: test_admin
# 角色: 2 (admin)

# 2. 提升为超级管理员
./manage_accounts.sh
# 选择 7 (修改管理员角色)
# 用户名: test_admin
# 新角色: 1 (super_admin)
```

### 场景3：测试账户状态切换

```bash
# 1. 禁用测试账户
./manage_accounts.sh
# 选择 6 (启用/禁用账户)
# 账户类型: 2 (运营商)
# 用户名: operator1
# 操作: 2 (禁用)

# 2. 重新启用
# 操作: 1 (启用)
```

## 📊 CSV 批量导入格式

### 运营商导入文件格式

文件名：`operators.csv` 或任意名称

```csv
username,password,full_name,email,phone,initial_balance
dev_op1,Pass123!,开发运营商1,dev1@example.com,13800000001,5000
dev_op2,Pass123!,开发运营商2,dev2@example.com,13800000002,3000
dev_op3,Pass123!,开发运营商3,dev3@example.com,13800000003,4000
```

**字段说明：**
- `username`: 登录用户名（唯一）
- `password`: 登录密码
- `full_name`: 运营商名称
- `email`: 邮箱地址
- `phone`: 联系电话
- `initial_balance`: 初始余额（单位：元）

## 🛠️ 故障排除

### 问题1：脚本报错"后端容器未运行"

**原因：** 开发环境未启动或容器异常

**解决方法：**
```bash
# 检查容器状态
docker-compose ps

# 如果未运行，启动服务
docker-compose up -d

# 查看后端日志
docker-compose logs backend
```

### 问题2：权限不足

**解决方法：**
```bash
# 赋予执行权限
chmod +x manage_accounts.sh

# 或使用 bash 执行
bash manage_accounts.sh
```

### 问题3：Python 导入错误

**原因：** 容器中的代码可能不是最新版本

**解决方法：**
```bash
# 重新构建后端容器
docker-compose build backend

# 重启服务
docker-compose restart backend
```

### 问题4：数据库连接失败

**解决方法：**
```bash
# 检查数据库容器
docker-compose ps postgres

# 查看数据库日志
docker-compose logs postgres

# 重启数据库（会丢失未持久化的数据）
docker-compose restart postgres
```

## 🔐 开发环境安全提示

1. **开发环境专用**
   - 本脚本仅用于本地开发和测试
   - 不要在生产环境使用此脚本
   - 开发环境数据库可随时清空重建

2. **测试数据管理**
   - 定期清理测试账户
   - 使用明显的测试标识（如 `dev_`, `test_` 前缀）
   - 不要使用真实的邮箱和电话

3. **密码管理**
   - 开发环境可使用简单密码
   - 建议统一测试密码方便开发
   - 示例：`DevPass123!`, `TestPass123!`

4. **数据备份**
   - 重要测试数据可导出备份
   - 使用菜单选项 9 导出账户信息
   - 重新构建容器前先导出

## 🔄 常用开发工作流

### 工作流1：每日开发启动

```bash
# 1. 启动开发环境
docker-compose up -d

# 2. 查看当前账户
cd docs/开发环境
./manage_accounts.sh list-admins
./manage_accounts.sh list-operators

# 3. 开始开发...
```

### 工作流2：功能测试

```bash
# 1. 创建测试账户
./manage_accounts.sh create-operator
# 创建若干测试运营商

# 2. 通过前端或API测试功能

# 3. 测试完成后查看账户状态
./manage_accounts.sh list-operators

# 4. 清理测试数据（如需要）
# 手动禁用或删除测试账户
```

### 工作流3：数据库重置

```bash
# 1. 停止所有服务
docker-compose down -v

# 2. 重新启动（会创建新数据库）
docker-compose up -d

# 3. 等待服务就绪
sleep 10

# 4. 重新创建初始数据
cd docs/开发环境
./manage_accounts.sh
# 选择 8, 批量导入 operators_example.csv
```

## 📚 相关文档

- [生产环境账户管理](../生产环境/README.md) - 生产环境使用指南
- [账户管理详细手册](../生产环境/账户管理-生产环境.md) - 详细操作说明
- [项目文档](../../README.md) - 项目总体说明

## 💬 开发提示

### 调试脚本

如果需要调试脚本中的 Python 代码，可以直接进入容器：

```bash
# 进入后端容器
docker exec -it mr_game_ops_backend bash

# 进入 Python 交互环境
cd /app
python3

# 测试代码
>>> from src.models import AdminAccount
>>> from src.db.session import init_db, get_db_context
>>> # ... 测试你的代码
```

### 修改脚本

脚本是纯文本 Shell 脚本，可以直接编辑：

```bash
# 使用你喜欢的编辑器
vim manage_accounts.sh
# 或
code manage_accounts.sh
```

修改后立即生效，无需重新构建容器。

### 添加新功能

如需添加新的账户管理功能：

1. 在脚本中添加新函数
2. 在 `show_menu()` 中添加菜单项
3. 在 `main()` 函数的 case 语句中添加调用
4. 测试新功能
5. 更新本 README 文档

## 🪟 Windows版本特别说明

### 技术架构
Windows版本(`manage_accounts.bat`)与Linux版本功能完全一致，但采用不同的技术实现：

**参数传递方式：**
- **Linux版本**: 使用Bash heredoc (`<< EOFPYTHON`)
- **Windows版本**: 使用环境变量 + 独立Python脚本

**脚本结构：**
```
manage_accounts.bat (主程序)
  → 收集用户输入
  → type scripts\*.py | docker exec -i -e VAR=value backend python3
  → Python脚本从os.environ读取参数
  → 执行数据库操作
```

**Python脚本列表：**
- `list_accounts.py` - 查看所有账户
- `create_admin_env.py` - 创建管理员
- `create_operator_env.py` - 创建运营商（自动生成API密钥）
- `create_finance_env.py` - 创建财务账户
- `delete_account_env.py` - 删除账户
- `reset_password_env.py` - 重置密码
- `toggle_active_env.py` - 启用/禁用账户
- `change_admin_role_env.py` - 修改管理员角色
- `batch_create_operators.py` - 批量创建运营商

### 中文显示问题
如果出现中文乱码：
1. 推荐在PowerShell中运行（支持UTF-8最佳）
2. 或在CMD中手动设置编码：`chcp 65001`

### 文件路径注意事项
- 批量创建时，CSV文件路径支持相对路径和绝对路径
- 如果路径包含空格，会自动处理（无需额外引号）

## 🎯 下一步

- 熟悉各个功能的使用
- 根据开发需要创建测试数据
- 如有问题或建议，可以修改脚本或提交 Issue
- 测试通过后，可参考生产环境部署指南进行部署

---

**Windows用户提示**: 详细的Windows使用说明请参阅 [README_Windows.md](./README_Windows.md)
