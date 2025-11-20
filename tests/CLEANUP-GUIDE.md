# E2E测试数据清理指南

## 📋 清理方法汇总

### ✅ **方法1: 自动清理 (推荐)**

**Playwright测试会在所有测试结束后自动清理测试数据**

```bash
cd tests
npm run test:localhost
# 测试结束后会自动清理所有E2E测试数据
```

**工作原理:**
- `playwright.config.ts`配置了`globalTeardown: './e2e/global-teardown.ts'`
- 所有测试运行完成后,Playwright会自动调用`global-teardown.ts`
- 该脚本会删除所有E2E测试创建的数据

---

### 🔧 **方法2: 手动清理命令 (快速)**

**使用npm script快速清理:**

```bash
cd tests
npm run cleanup
```

这会立即清理所有E2E测试数据,无需运行测试。

---

### 💻 **方法3: 直接运行清理脚本**

```bash
cd tests
npx tsx e2e/scripts/cleanup-test-data.ts
```

---

### 🗄️ **方法4: 直接使用SQL (高级)**

如果您有数据库访问权限,可以直接运行SQL:

```sql
-- 删除E2E测试运营商
DELETE FROM operator_accounts
WHERE username LIKE 'e2e_%'
  OR full_name LIKE '%E2E测试%'
  OR full_name LIKE 'E2E测试运营商%';

-- 删除E2E测试的发票记录
DELETE FROM invoice_records
WHERE invoice_title LIKE '%E2E%' OR invoice_title LIKE '%自动化测试%';

-- 删除E2E测试的退款记录
DELETE FROM refund_records
WHERE refund_reason LIKE '%E2E%' OR refund_reason LIKE '%自动化测试%';

-- 删除E2E测试的应用授权申请
DELETE FROM application_authorization_requests
WHERE request_reason LIKE '%E2E%' OR request_reason LIKE '%自动化测试%';

-- 删除E2E测试的银行转账申请
DELETE FROM bank_transfer_applications
WHERE remark LIKE '%E2E%' OR remark LIKE '%自动化测试%';

-- 删除E2E测试的充值订单
DELETE FROM recharge_orders
WHERE order_id LIKE 'e2e_%';

-- 删除E2E测试的交易记录
DELETE FROM transaction_records
WHERE description LIKE '%E2E测试%' OR description LIKE '%E2E%';

-- 删除E2E测试站点
DELETE FROM operation_sites
WHERE name LIKE '%E2E测试%' OR name LIKE '%E2E%';

-- 删除E2E测试应用
DELETE FROM applications
WHERE app_name LIKE '%E2E测试%' OR app_code LIKE 'e2e_%';
```

---

## 🎯 清理范围

清理脚本会删除以下测试数据:

### 运营商账户
- ✅ 用户名以`e2e_`开头的账户
- ✅ 全名包含"E2E测试"的账户
- ✅ 全名以"E2E测试运营商"开头的账户

### 相关数据
- ✅ 发票记录 (`invoice_records`)
- ✅ 退款记录 (`refund_records`)
- ✅ 应用授权申请 (`application_authorization_requests`)
- ✅ 银行转账申请 (`bank_transfer_applications`)
- ✅ 充值订单 (`recharge_orders`)
- ✅ 交易记录 (`transaction_records`)
- ✅ 运营站点 (`operation_sites`)
- ✅ 应用 (`applications`)

---

## ⚙️ 配置说明

### 自动清理配置

**文件**: `tests/playwright.config.ts`
```typescript
export default defineConfig({
  // ...
  globalTeardown: './e2e/global-teardown.ts', // ← 自动清理配置
  // ...
});
```

### 清理脚本文件

- **全局清理**: `tests/e2e/global-teardown.ts`
- **手动清理**: `tests/e2e/scripts/cleanup-test-data.ts`
- **清理逻辑**: `tests/e2e/utils/db-helper.ts` (cleanupTestData方法)

---

## 🔍 验证清理结果

清理后,您可以通过以下方式验证:

1. **查看清理日志**:
   ```
   🧹 Cleaning up test data...
   ✅ Test data cleaned up successfully
   ```

2. **手动检查数据库**:
   ```sql
   SELECT * FROM operator_accounts WHERE username LIKE 'e2e_%';
   -- 应该返回0行
   ```

3. **查看运营商列表** (通过管理后台):
   - 不应该有`e2e_`开头的账户
   - 不应该有"E2E测试运营商"的账户

---

## ⚠️ 注意事项

1. **本地环境清理**: 默认自动清理
2. **生产环境**: 由于使用`@readonly`标签,不会创建测试数据,无需清理
3. **失败的测试**: 即使测试失败,清理脚本仍会执行
4. **手动中断**: 如果测试被手动中断(Ctrl+C),可能需要手动运行清理命令

---

## 🆘 故障排除

### 问题1: 清理脚本报错
**解决方法**: 检查数据库连接配置(`.env`文件)

### 问题2: 测试数据未被清理
**解决方法**: 手动运行清理命令
```bash
cd tests
npm run cleanup
```

### 问题3: 数据库表不存在
**解决方法**: 确保数据库迁移已执行
```bash
cd backend
alembic upgrade head
```

---

## 📞 需要帮助?

如果遇到清理问题,请检查:
1. 数据库连接是否正常
2. `.env`文件配置是否正确
3. 数据库迁移是否完整

参考文档: `tests/README.md`
