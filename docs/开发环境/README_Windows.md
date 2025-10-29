# Windows开发环境账户管理工具

## 简介

本工具用于在Windows开发环境中管理MR游戏运营系统的账户，包括管理员、运营商和财务人员账户。

## 使用方法

### 前置条件

1. **Docker Desktop** 已启动
2. **服务容器**已运行：`docker-compose up -d`
3. **PowerShell** 或 Windows Terminal （推荐）

### 快速开始

```powershell
# 进入开发环境目录
cd docs\开发环境

# 列出所有账户
.\manage_accounts.bat list

# 显示帮助
.\manage_accounts.bat help
```

### 执行方式

**方式1：PowerShell（推荐）**
```powershell
.\manage_accounts.bat list
```

**方式2：命令提示符(cmd.exe)**
```cmd
manage_accounts.bat list
```

## 技术架构

### 文件结构

```
docs/开发环境/
├── manage_accounts.bat        # Windows批处理入口
├── manage_accounts.ps1        # PowerShell入口（备用）
├── scripts/
│   └── list_accounts.py       # Python脚本：列出所有账户
└── README_Windows.md          # 本文件
```

### 设计理念

- **职责分离**：批处理只负责调用，业务逻辑在Python中
- **无需转义**：Python脚本独立，避免批处理转义问题
- **易于扩展**：添加新功能只需创建新的Python脚本文件

### 工作原理

```
manage_accounts.bat
    ↓ (检查Docker容器)
    ↓ (读取Python脚本)
    ↓ (通过docker exec执行)
    ↓
scripts/list_accounts.py
    ↓ (连接数据库)
    ↓ (查询账户)
    ↓ (格式化输出)
```

## 可用命令

| 命令 | 说明 | 状态 |
|------|------|------|
| `manage_accounts.bat list` | 列出所有账户 | ✅ 已实现 |
| `manage_accounts.bat help` | 显示帮助信息 | ✅ 已实现 |
| `manage_accounts.bat` | 交互式菜单 | 🚧 开发中 |

## 输出示例

```
========================================================================================================================
【管理员账户】
========================================================================================================================
      用户名             姓名                      邮箱                     角色           状态            创建时间
------------------------------------------------------------------------------------------------------------------------
  test_admin         测试管理员              admin@test.com              admin        ✅ 激活   2025-10-29 00:30:11

共 1 个管理员账户

========================================================================================================================
【运营商账户】
========================================================================================================================
      用户名             名称                      邮箱                     余额           状态      站点数
------------------------------------------------------------------------------------------------------------------------
   operator1         一号游戏厅          operator1@example.com         ¥5000.00       ✅ 激活      0
   operator2         二号游戏厅          operator2@example.com         ¥3000.00       ✅ 激活      0

共 6 个运营商账户
```

## 故障排查

### 错误：Backend container is not running

**原因：**Docker容器未启动

**解决方法：**
```powershell
# 启动服务
docker-compose up -d

# 检查容器状态
docker ps | findstr mr_game_ops_backend
```

### 错误：中文显示乱码

**原因：**控制台编码问题

**解决方法1（推荐）：**使用PowerShell或Windows Terminal

**解决方法2：**在cmd.exe中设置UTF-8编码
```cmd
chcp 65001
manage_accounts.bat list
```

### 错误：无输出或脚本无响应

**原因：**可能从cmd.exe执行导致输出被抑制

**解决方法：**使用PowerShell执行
```powershell
powershell.exe -ExecutionPolicy Bypass -File ".\manage_accounts.bat" list
```

### 错误：脚本文件不存在

**原因：**工作目录不正确

**解决方法：**
```powershell
# 检查当前目录
pwd

# 切换到正确目录
cd C:\liangz77\python_projects\github_projects\mr_gunking_user_system_spec\docs\开发环境
```

## 与生产环境的区别

| 项目 | 开发环境(Windows) | 生产环境(Linux) |
|------|-------------------|----------------|
| 脚本语言 | Windows批处理(.bat) | Linux Bash(.sh) |
| 容器名 | mr_game_ops_backend | mr_game_ops_backend_prod |
| 执行方式 | PowerShell/cmd.exe | bash |
| 脚本位置 | docs/开发环境/ | docs/生产环境/ |

## 开发计划

### 已实现功能

- [x] `list_accounts.py` - 列出所有账户
- [x] 容器状态检查
- [x] UTF-8编码支持
- [x] 命令行参数解析

### 待实现功能

创建以下Python脚本以支持完整功能：

```
scripts/
├── list_accounts.py          # ✅ 已实现
├── create_admin.py           # 🚧 待实现 - 创建管理员账户
├── create_operator.py        # 🚧 待实现 - 创建运营商账户
├── create_finance.py         # 🚧 待实现 - 创建财务账户
├── delete_account.py         # 🚧 待实现 - 删除账户
├── reset_password.py         # 🚧 待实现 - 重置密码
├── toggle_active.py          # 🚧 待实现 - 启用/禁用账户
├── change_admin_role.py      # 🚧 待实现 - 修改管理员角色
└── batch_create_operators.py # 🚧 待实现 - 批量创建运营商
```

## 开发提示

### 添加新功能

1. **创建Python脚本**：在 `scripts/` 目录下创建新的.py文件
2. **测试脚本**：直接测试Python脚本
   ```powershell
   Get-Content scripts\new_script.py | docker exec -i mr_game_ops_backend python3
   ```
3. **更新批处理文件**：在 `manage_accounts.bat` 中添加新命令
4. **测试完整流程**：`.\manage_accounts.bat new-command`

### Python脚本模板

```python
#!/usr/bin/env python3
"""功能描述"""
import asyncio
import sys
sys.path.insert(0, '/app')

from src.db.session import init_db, get_db_context
from src.models import AdminAccount

async def main():
    init_db()
    async with get_db_context() as session:
        # 你的代码逻辑
        pass

if __name__ == "__main__":
    asyncio.run(main())
```

### 调试Python代码

```powershell
# 方式1：直接在容器中执行
docker exec -it mr_game_ops_backend python3
>>> from src.models import *
>>> # 测试代码

# 方式2：查看脚本输出
Get-Content scripts\list_accounts.py | docker exec -i mr_game_ops_backend python3 2>&1 | more
```

## 参考资料

- **生产环境脚本**：`docs/生产环境/manage_accounts.sh`
- **示例CSV文件**：`docs/开发环境/operators_example.csv`
- **项目README**：根目录 `README.md`

## 技术细节

### 批处理转义规则

在批处理文件中：
- REM注释：使用英文避免编码问题
- echo输出：可以使用中文（会显示给用户）
- Python代码：独立文件，无需转义

### UTF-8编码设置

批处理文件第5行：
```batch
chcp 65001 >nul
```
设置控制台为UTF-8编码，确保中文正确显示。

### Docker命令解析

```batch
type "%SCRIPT_DIR%\list_accounts.py" | docker exec -i %BACKEND_CONTAINER% python3
```

- `type`: Windows命令，读取文件内容
- `|`: 管道，传递给docker命令
- `docker exec -i`: 在容器中执行命令，`-i`保持标准输入
- `python3`: 容器中的Python解释器

## 常见问题

**Q: 为什么选择批处理+独立Python脚本的方案？**

A: 因为Windows批处理中转义Python代码极其复杂（所有括号都需要转义），容易出错。独立Python文件无需转义，更易维护。

**Q: 能否直接运行Python脚本？**

A: 不行。Python脚本需要在Docker容器中运行才能访问数据库。必须通过批处理文件调用。

**Q: PowerShell脚本（.ps1）为什么不用？**

A: PowerShell也有编码问题。批处理文件(.bat)更通用，兼容性更好。

**Q: 如何查看详细的SQL日志？**

A: 将stderr重定向查看：
```powershell
.\manage_accounts.bat list 2>&1 | more
```

## 许可

本项目为内部开发工具，仅供团队使用。
