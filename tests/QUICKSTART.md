# 快速开始指南

## 5分钟快速上手

### 1. 安装依赖 (首次使用)

```bash
cd tests
npm install
npx playwright install
```

### 2. 运行测试

**本地环境测试** (推荐先用这个):
```bash
npm run test:localhost:ui
```

这会打开 Playwright 的可视化界面,你可以:
- 看到所有测试用例
- 点击运行单个或多个测试
- 实时查看测试执行过程
- 调试失败的测试

**命令行运行所有测试**:
```bash
npm run test:localhost
```

**生产环境只读测试**:
```bash
# 先配置生产环境密码
# 编辑 .env 文件,填入:
# PROD_ADMIN_PASSWORD=实际密码
# PROD_FINANCE_PASSWORD=实际密码
# PROD_OPERATOR_PASSWORD=实际密码

npm run test:production
```

### 3. 查看测试结果

测试完成后会自动生成报告,运行:
```bash
npm run test:report
```

## 常用命令速查

| 命令 | 说明 |
|------|------|
| `npm run test:localhost:ui` | 本地环境 UI 模式(推荐) |
| `npm run test:localhost` | 本地环境命令行模式 |
| `npm run test:production` | 生产环境只读测试 |
| `npm run test:localhost:debug` | 调试模式(步进执行) |
| `npm run test:report` | 查看测试报告 |
| `npx playwright test admin.spec.ts` | 只测试管理员功能 |
| `npx playwright test finance.spec.ts` | 只测试财务功能 |
| `npx playwright test operator.spec.ts` | 只测试运营商功能 |

## 测试内容概览

### 管理员测试 (11个测试用例)
- 仪表盘、运营商管理、站点管理
- 应用管理、审批、授权
- 交易记录、搜索、筛选

### 财务测试 (14个测试用例)
- 仪表盘、充值记录、交易记录
- 退款管理、发票管理、银行流水
- 财务报表、审计日志
- **确认充值、执行扣费、审批退款**

### 运营商测试 (19个测试用例)
- 仪表盘、个人资料、充值
- 交易记录、**财务扣费显示验证**
- 站点、应用、使用记录、统计
- 退款、发票、消息
- **各种筛选和创建操作**

## 注意事项

1. **本地测试前确保服务运行**:
   ```bash
   docker-compose up -d
   ```

2. **生产环境只运行只读测试**:
   - 不会修改任何数据
   - 仅验证页面能正常访问和显示

3. **测试数据自动清理**:
   - 本地测试创建的数据会自动清理
   - 所有测试数据都以 `e2e_` 前缀命名

## 故障排查

**测试失败怎么办?**

1. 使用 UI 模式查看失败原因:
   ```bash
   npm run test:localhost:ui
   ```

2. 使用调试模式步进执行:
   ```bash
   npm run test:localhost:debug
   ```

3. 查看服务日志:
   ```bash
   docker-compose logs -f backend
   docker-compose logs -f frontend
   ```

**元素找不到?**

页面可能已更新,使用代码生成器重新录制:
```bash
npm run test:codegen:localhost
```

## 下一步

详细文档请参考 [README.md](./README.md)
