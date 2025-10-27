# MR游戏运营管理系统 - 非Docker部署账户管理手册

## 📋 目录

- [快速开始](#快速开始)
- [管理员账户管理](#管理员账户管理)
- [财务账户管理](#财务账户管理)
- [运营商账户管理](#运营商账户管理)
- [查看所有用户](#查看所有用户)
- [安全最佳实践](#安全最佳实践)
- [常见问题](#常见问题)
- [故障排查](#故障排查)

---

## 🚀 快速开始

### 前置条件

- 服务器已部署并运行（非Docker部署）
- 能够通过 SSH 访问服务器
- 后端服务正在运行（默认端口8001）
- 前端服务正在运行（默认端口80）
- Python 3.12 虚拟环境已配置

### 基本命令格式

所有账户管理脚本都在后端目录中执行：

```bash
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate  # 或 source venv_py312/Scripts/activate (Windows)
python scripts/<脚本名>.py [参数]
```

### 默认账户信息

首次部署后系统会自动创建以下默认账户：

| 账户类型 | 用户名 | 密码 | 角色 | 备注 |
|----------|--------|------|------|------|
| 管理员 | superadmin | admin123456 | super_admin | 超级管理员 |
| 财务 | finance_wang | finance123456 | specialist | 财务专员 |
| 运营商 | operator_vip | operator123456 | operator | VIP游戏公司 |

**⚠️ 重要**: 首次部署后必须立即修改所有默认密码！

---

## 👨‍💼 管理员账户管理

### 1. 修改管理员密码

**脚本**: `change_password.py`

#### 基本用法

```bash
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate
python scripts/change_password.py <用户名> <新密码>
```

#### 实际示例

```bash
# 修改 superadmin 的密码为 Admin@Secure2024!
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate
python scripts/change_password.py superadmin Admin@Secure2024!
```

**输出示例**：
```
密码修改成功！
用户名: superadmin
新密码: Admin@Secure2024!
```

#### 密码要求建议

- ✅ 至少 12 个字符
- ✅ 包含大写字母 (A-Z)
- ✅ 包含小写字母 (a-z)
- ✅ 包含数字 (0-9)
- ✅ 包含特殊字符 (!@#$%^&*)
- ❌ 不要使用常见单词、生日、公司名称

**强密码示例**：
- `Admin@2024!Secure`
- `MyP@ssw0rd2024#`
- `Secure!Game2024$`

---

## 💰 财务账户管理

### 1. 创建财务用户

**脚本**: `manage_finance_user.py`

#### 基本用法

```bash
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate
python scripts/manage_finance_user.py create <用户名> <密码> <姓名> [邮箱] [手机]
```

#### 实际示例

**示例 1：完整参数**
```bash
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate
python scripts/manage_finance_user.py create finance001 Finance@2024! 张财务 zhang@company.com 13800138001
```

**示例 2：最少参数（邮箱和手机使用默认值）**
```bash
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate
python scripts/manage_finance_user.py create finance001 Finance@2024! 张财务
```

**示例 3：创建多个财务用户**
```bash
# 财务主管
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate
python scripts/manage_finance_user.py create finance_manager FinMgr@2024! 李主管 li@company.com 13800138002

# 财务专员
python scripts/manage_finance_user.py create finance_staff1 FinStaff@2024! 王专员 wang@company.com 13800138003

# 财务审计
python scripts/manage_finance_user.py create finance_audit Audit@2024! 赵审计 zhao@company.com 13800138004
```

**输出示例**：
```
财务用户创建成功！
用户名: finance001
密码: Finance@2024!
姓名: 张财务
角色: finance（财务）
权限: finance:read, finance:recharge, finance:refund, invoice:read, invoice:create, statistics:read
```

#### 财务角色权限说明

| 权限 | 说明 |
|------|------|
| `finance:read` | 查看财务信息、账户余额 |
| `finance:recharge` | 为用户充值 |
| `finance:refund` | 处理退款申请 |
| `invoice:read` | 查看发票记录 |
| `invoice:create` | 创建和开具发票 |
| `statistics:read` | 查看财务统计报表 |

**财务用户不能**：
- ❌ 创建/删除其他管理员
- ❌ 修改系统配置
- ❌ 访问技术日志
- ❌ 管理操作员账号（非财务范围）

---

### 2. 修改财务用户密码

#### 基本用法

```bash
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate
python scripts/manage_finance_user.py password <用户名> <新密码>
```

#### 实际示例

```bash
# 修改 finance001 的密码
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate
python scripts/manage_finance_user.py password finance001 NewFinPass2024!

# 修改财务主管的密码
python scripts/manage_finance_user.py password finance_manager NewMgrPass2024!
```

**输出示例**：
```
密码修改成功！
用户名: finance001
新密码: NewFinPass2024!
```

---

## 🎮 运营商账户管理

### 1. 创建运营商账户

**脚本**: `manage_operator_user.py`

#### 基本用法

```bash
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate
python scripts/manage_operator_user.py create <用户名> <密码> <公司名称> <联系人> [邮箱] [手机] [初始余额] [客户等级]
```

#### 实际示例

**示例 1：创建VIP运营商**
```bash
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate
python scripts/manage_operator_user.py create gamevip VIP@2024! "VIP游戏公司" 张总 zhang@vipgame.com 13900139000 10000.00 vip
```

**示例 2：创建普通运营商**
```bash
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate
python scripts/manage_operator_user.py create game001 Game@2024! "普通游戏公司" 李经理 li@game001.com 13900139001 5000.00 normal
```

**示例 3：创建测试运营商**
```bash
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate
python scripts/manage_operator_user.py create test_game Test@2024! "测试游戏公司" 测试员 test@test.com 13900139999 1000.00 trial
```

**输出示例**：
```
运营商账户创建成功！
用户名: gamevip
密码: VIP@2024!
公司名称: VIP游戏公司
联系人: 张总
邮箱: zhang@vipgame.com
手机: 13900139000
初始余额: 10000.00
客户等级: vip
API密钥: vip_abc123def456...
```

#### 客户等级说明

| 等级 | 说明 | 特权 |
|------|------|------|
| `vip` | VIP客户 | 最高额度、最优费率、专属客服 |
| `premium` | 高级客户 | 较高额度、较优费率 |
| `normal` | 普通客户 | 标准额度、标准费率 |
| `trial` | 试用客户 | 有限额度、基础功能 |

---

### 2. 修改运营商密码

#### 基本用法

```bash
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate
python scripts/manage_operator_user.py password <用户名> <新密码>
```

#### 实际示例

```bash
# 修改运营商密码
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate
python scripts/manage_operator_user.py password gamevip NewVIPPass2024!
```

---

### 3. 运营商余额管理

#### 充值操作

```bash
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate
python scripts/manage_operator_user.py recharge <用户名> <充值金额> [备注]
```

**示例**：
```bash
# 为 gamevip 充值 5000 元
python scripts/manage_operator_user.py recharge gamevip 5000.00 "月度充值"

# 为 game001 充值 2000 元
python scripts/manage_operator_user.py recharge game001 2000.00 "活动充值"
```

---

## 👥 查看所有用户

### 1. 查看所有管理员和财务用户

**脚本**: `manage_finance_user.py`

```bash
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate
python scripts/manage_finance_user.py list
```

**输出示例**：
```
当前用户列表：
----------------------------------------------------------------------------------------------------
用户名           姓名            角色            邮箱                      状态     创建时间
----------------------------------------------------------------------------------------------------
superadmin       系统管理员       super_admin     admin@mrgameops.com       激活     2025-10-27 16:30:34
finance_wang     王财务          specialist      wang@mrgameops.com        激活     2025-10-27 16:30:34
finance_manager  李主管          finance         li@company.com            激活     2025-10-27 17:15:20
finance001      张财务          finance         zhang@company.com         激活     2025-10-27 17:30:45
----------------------------------------------------------------------------------------------------
总计: 4 个用户
```

### 2. 查看所有运营商用户

**脚本**: `manage_operator_user.py`

```bash
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate
python scripts/manage_operator_user.py list
```

**输出示例**：
```
运营商账户列表：
----------------------------------------------------------------------------------------------------------------------------------------
用户名       公司名称         联系人     邮箱                    手机         余额      等级      状态     创建时间
----------------------------------------------------------------------------------------------------------------------------------------
operator_vip  VIP游戏公司     赵总       zhao@vipgame.com        13900139000  5000.00  vip       激活     2025-10-27 16:30:34
gamevip       VIP游戏公司     张总       zhang@vipgame.com       13900139000  10000.00 vip       激活     2025-10-27 17:45:10
game001       普通游戏公司    李经理     li@game001.com          13900139001  5000.00  normal    激活     2025-10-27 18:00:22
----------------------------------------------------------------------------------------------------------------------------------------
总计: 3 个运营商
```

---

## 🔒 安全最佳实践

### 1. 密码管理

#### ✅ 推荐做法

- 首次部署后**立即**修改所有默认密码
- 使用强密码（12+ 字符，大小写+数字+符号）
- 定期更换密码（建议每 3-6 个月）
- 不同账户使用不同密码
- 使用密码管理器保存密码

#### ❌ 避免做法

- 不要使用 `admin123`、`password`、`123456` 等弱密码
- 不要使用生日、姓名拼音等可预测密码
- 不要在多个系统使用相同密码
- 不要将密码写在记事本或邮件中
- 不要与他人共享账号

### 2. 账户管理

#### ✅ 推荐做法

```bash
# 1. 首次部署后立即修改默认密码
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate
python scripts/change_password.py superadmin Admin@Secure2024!
python scripts/manage_finance_user.py password finance_wang NewFinance@2024!
python scripts/manage_operator_user.py password operator_vip NewOperator@2024!

# 2. 为每个员工创建独立账号
python scripts/manage_finance_user.py create finance_zhang FinZhang@2024! 张三
python scripts/manage_finance_user.py create finance_li FinLi@2024! 李四

# 3. 定期检查用户列表
python scripts/manage_finance_user.py list
python scripts/manage_operator_user.py list

# 4. 员工离职后立即修改或禁用其账号
python scripts/manage_finance_user.py password finance_zhang DisabledAccount@999!
```

#### ❌ 避免做法

- 不要多人共用一个账号
- 不要长期使用默认密码
- 不要忘记清理离职员工账号
- 不要在公共场所登录

### 3. 登录安全

- 仅在安全网络环境下登录
- 使用完毕后及时退出登录
- 不要在公共电脑上保存密码
- 定期检查登录日志

### 4. 服务器访问安全

```bash
# 1. 仅允许特定IP访问服务器（在防火墙配置）
sudo ufw allow from 192.168.1.0/24 to any port 22
sudo ufw allow from 203.0.113.5 to any port 8001

# 2. 使用SSH密钥而不是密码登录服务器

# 3. 定期更新系统
sudo apt update && sudo apt upgrade

# 4. 检查服务状态
sudo systemctl status mr-game-ops-backend
```

---

## 📝 完整操作流程示例

### 场景 1：新系统部署后的初始化

```bash
# 步骤 1：登录服务器
ssh your-user@your-server

# 步骤 2：修改默认管理员密码
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate
python scripts/change_password.py superadmin Admin@Secure2024!

# 步骤 3：修改默认财务密码
python scripts/manage_finance_user.py password finance_wang NewFinance@2024!

# 步骤 4：修改默认运营商密码
python scripts/manage_operator_user.py password operator_vip NewOperator@2024!

# 步骤 5：创建新的财务主管账号
python scripts/manage_finance_user.py create finance_manager FinMgr@2024! 财务主管 manager@company.com 13800138000

# 步骤 6：创建新的运营商账号
python scripts/manage_operator_user.py create new_game NewGame@2024! "新游戏公司" 王总 wang@newgame.com 13900138888 8000.00 premium

# 步骤 7：验证所有账号已创建
python scripts/manage_finance_user.py list
python scripts/manage_operator_user.py list
```

### 场景 2：新员工入职

```bash
# 创建新财务员工账号
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate
python scripts/manage_finance_user.py create finance_newuser FinNew@2024! 新员工姓名 new@company.com 13800138888

# 验证账号创建成功
python scripts/manage_finance_user.py list

# 将用户名和初始密码告知新员工，要求首次登录后修改密码
```

### 场景 3：员工离职

```bash
# 方法 1：修改密码以禁用账号（推荐）
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate
python scripts/manage_finance_user.py password finance_olduser DisabledAccount@999!

# 方法 2：如果是运营商，也可以清零余额
python scripts/manage_operator_user.py password operator_olduser DisabledAccount@999!
python scripts/manage_operator_user.py recharge operator_olduser 0 "离职清零"

# 验证用户列表
python scripts/manage_finance_user.py list
python scripts/manage_operator_user.py list
```

### 场景 4：定期密码更换

```bash
# 每季度更换一次管理员密码
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate
python scripts/change_password.py superadmin NewAdminPass_Q1_2024!

# 要求所有财务人员更换密码
python scripts/manage_finance_user.py password finance001 NewPass_Q1_2024!
python scripts/manage_finance_user.py password finance002 NewPass_Q1_2024!

# 方法 2：员工自行在系统中修改（登录后从个人中心修改）
```

### 场景 5：运营商余额管理

```bash
# 月度充值流程
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate

# 1. 查看当前余额
python scripts/manage_operator_user.py list

# 2. 为VIP客户充值
python scripts/manage_operator_user.py recharge gamevip 10000.00 "VIP客户月度充值"

# 3. 为普通客户充值
python scripts/manage_operator_user.py recharge game001 5000.00 "普通客户月度充值"

# 4. 验证充值结果
python scripts/manage_operator_user.py list
```

### 场景 6：忘记密码

```bash
# 管理员重置用户密码
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate
python scripts/manage_finance_user.py password <忘记密码的用户名> TemporaryPass@2024!

# 告知用户临时密码，要求立即登录并修改
```

---

## ❓ 常见问题

### Q1: 如何确认脚本文件存在？

```bash
# 查看后端 scripts 目录
cd /opt/mr_gunking_user_system_spec/backend
ls -la scripts/

# 应该看到以下文件：
# create_admin_simple.py
# create_admin.py
# change_password.py
# manage_finance_user.py
# manage_operator_user.py
# README.md
```

### Q2: 如果脚本不存在怎么办？

```bash
# 方法 1：从 Git 仓库拉取最新代码
cd /opt/mr_gunking_user_system_spec
git pull origin 001-mr

# 方法 2：检查文件权限
chmod +x scripts/*.py
```

### Q3: 创建用户时提示"用户已存在"怎么办？

```bash
# 方法 1：换一个用户名
python scripts/manage_finance_user.py create finance002 Pass@2024! 张财务

# 方法 2：如果确实要使用该用户名，先修改现有用户密码
python scripts/manage_finance_user.py password finance001 NewPass@2024!
```

### Q4: 如何批量创建多个账号？

```bash
# 创建一个 shell 脚本
cat > create_finance_users.sh << 'EOF'
#!/bin/bash
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate

python scripts/manage_finance_user.py create finance001 Fin001@2024! 张三
python scripts/manage_finance_user.py create finance002 Fin002@2024! 李四
python scripts/manage_finance_user.py create finance003 Fin003@2024! 王五
EOF

# 执行脚本
chmod +x create_finance_users.sh
./create_finance_users.sh
```

### Q5: 如何验证密码修改成功？

```bash
# 方法 1：尝试在浏览器登录
# 访问 http://mrgun.chu-jiao.com/
# 使用新密码登录

# 方法 2：查看用户列表（确认用户存在）
python scripts/manage_finance_user.py list
```

### Q6: 如何查看某个用户的详细信息？

```bash
# 目前只能查看所有用户列表
python scripts/manage_finance_user.py list

# 或者使用 grep 过滤
python scripts/manage_finance_user.py list | grep finance001
```

### Q7: 密码可以包含中文吗？

**不推荐**使用中文密码，因为：
- 可能导致编码问题
- 在某些终端环境下输入困难
- 建议使用英文、数字和符号组合

### Q8: 服务停止了怎么办？

```bash
# 检查服务状态
sudo systemctl status mr-game-ops-backend

# 重启服务
sudo systemctl restart mr-game-ops-backend

# 或者使用重启脚本
cd /opt/mr_gunking_user_system_spec
sudo ./reset_and_start_services.sh
```

### Q9: 如何备份用户数据？

```bash
# 备份数据库
sudo -u postgres pg_dump mr_game_ops > backup_$(date +%Y%m%d_%H%M%S).sql

# 或者备份特定表
sudo -u postgres pg_dump mr_game_ops -t admin_accounts -t finance_accounts -t operator_accounts > accounts_backup.sql
```

---

## 🔧 故障排查

### 错误 1: `ModuleNotFoundError: No module named 'src'`

**原因**: 脚本路径配置问题

**解决方案**:
```bash
# 1. 确保在后端目录中执行
cd /opt/mr_gunking_user_system_spec/backend

# 2. 确保虚拟环境已激活
source venv/bin/activate

# 3. 确保使用正确的 Python 版本
python --version  # 应该显示 Python 3.12.x

# 4. 重试
python scripts/manage_finance_user.py list
```

### 错误 2: `can't open file 'scripts/xxx.py': No such file or directory`

**原因**: 脚本文件不存在

**解决方案**:
```bash
# 1. 检查文件是否存在
ls -la scripts/

# 2. 拉取最新代码
cd /opt/mr_gunking_user_system_spec
git pull origin 001-mr

# 3. 验证文件存在
ls -la backend/scripts/
```

### 错误 3: 数据库连接失败

**原因**: 数据库未启动或连接配置错误

**解决方案**:
```bash
# 1. 检查数据库服务状态
sudo systemctl status postgresql

# 2. 启动数据库服务
sudo systemctl start postgresql

# 3. 测试数据库连接
sudo -u postgres psql -d mr_game_ops -c "SELECT 1;"

# 4. 检查环境变量配置
cat .env.production | grep DATABASE_URL
```

### 错误 4: 密码验证失败（登录时）

**可能原因**:
1. 密码输入错误（检查大小写、空格）
2. 使用了旧密码
3. 账号被禁用

**解决方案**:
```bash
# 重置密码
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate
python scripts/change_password.py <用户名> NewPassword@2024!
```

### 错误 5: 端口被占用

**解决方案**:
```bash
# 1. 检查端口占用情况
netstat -tlnp | grep 8001
netstat -tlnp | grep 80

# 2. 使用重启脚本清理端口
cd /opt/mr_gunking_user_system_spec
sudo ./reset_and_start_services.sh
```

### 错误 6: 权限不足

**解决方案**:
```bash
# 1. 使用 sudo 执行
sudo ./reset_and_start_services.sh

# 2. 检查文件权限
chmod +x scripts/*.py

# 3. 检查目录权限
sudo chown -R $USER:$USER /opt/mr_gunking_user_system_spec
```

---

## 📞 技术支持

如遇到本文档未涵盖的问题，请：

1. 检查系统日志：
   ```bash
   # 后端日志
   tail -f /opt/mr_gunking_user_system_spec/backend/logs/backend.log

   # 系统服务日志
   sudo journalctl -u mr-game-ops-backend -f
   ```

2. 检查服务状态：
   ```bash
   sudo systemctl status mr-game-ops-backend
   sudo systemctl status mr-game-ops-frontend
   ```

3. 查看详细文档：
   ```bash
   cat /opt/mr_gunking_user_system_spec/backend/scripts/README.md
   ```

4. 检查网络连接：
   ```bash
   # 检查端口是否开放
   curl -I http://localhost:8001/health
   curl -I http://localhost:80
   ```

---

## 📚 附录

### 快速命令参考

```bash
# === 环境准备 ===
cd /opt/mr_gunking_user_system_spec/backend
source venv/bin/activate

# === 管理员操作 ===
# 修改密码
python scripts/change_password.py <用户名> <新密码>

# === 财务用户操作 ===
# 创建财务用户
python scripts/manage_finance_user.py create <用户名> <密码> <姓名>

# 修改财务用户密码
python scripts/manage_finance_user.py password <用户名> <新密码>

# 查看所有用户
python scripts/manage_finance_user.py list

# === 运营商操作 ===
# 创建运营商
python scripts/manage_operator_user.py create <用户名> <密码> <公司名称> <联系人>

# 修改运营商密码
python scripts/manage_operator_user.py password <用户名> <新密码>

# 运营商充值
python scripts/manage_operator_user.py recharge <用户名> <金额>

# 查看所有运营商
python scripts/manage_operator_user.py list

# === 系统维护 ===
# 查看服务状态
sudo systemctl status mr-game-ops-backend
sudo systemctl status mr-game-ops-frontend

# 查看日志
tail -f /opt/mr_gunking_user_system_spec/backend/logs/backend.log
tail -f /opt/mr_gunking_user_system_spec/frontend/logs/frontend.log

# 重启服务
sudo ./reset_and_start_services.sh

# === 数据库操作 ===
# 备份数据库
sudo -u postgres pg_dump mr_game_ops > backup_$(date +%Y%m%d_%H%M%S).sql

# 连接数据库
sudo -u postgres psql -d mr_game_ops
```

### 默认端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 | 80 | HTTP访问，用户界面 |
| 后端 | 8001 | API服务，管理系统功能 |
| 数据库 | 5432 | PostgreSQL数据库 |

### 重要文件路径

| 文件 | 路径 |
|------|------|
| 部署脚本 | `/opt/mr_gunking_user_system_spec/reset_and_start_services.sh` |
| 管理脚本 | `/opt/mr_gunking_user_system_spec/backend/scripts/` |
| 后端日志 | `/opt/mr_gunking_user_system_spec/backend/logs/backend.log` |
| 前端日志 | `/opt/mr_gunking_user_system_spec/frontend/logs/frontend.log` |
| 环境配置 | `/opt/mr_gunking_user_system_spec/backend/.env.production` |

---

**文档版本**: v2.0
**最后更新**: 2025-10-27
**适用系统版本**: MR游戏运营管理系统 v1.0（非Docker部署）
**部署方式**: 直接部署（非容器化）