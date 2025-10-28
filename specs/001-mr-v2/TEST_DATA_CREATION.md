# 测试数据创建记录

**日期**: 2025-10-28
**目的**: 为E2E测试创建退款和发票审核测试数据 (T332, T334)

## 创建的测试数据

### 1. 退款申请记录 (Refund Request)

```sql
INSERT INTO refund_records (
  id,
  operator_id,
  requested_amount,
  refund_reason,
  status,
  created_at,
  updated_at
) VALUES (
  gen_random_uuid(),
  '40c3f8d9-bc57-49f3-a0d2-576bd575eed8',  -- testoperator001
  500.00,
  '测试退款申请 - E2E测试数据',
  'pending',
  CURRENT_TIMESTAMP,
  CURRENT_TIMESTAMP
);
```

**数据详情**:
- 运营商: testoperator001 (测试运营商公司)
- 退款金额: ¥500.00
- 退款理由: "测试退款申请 - E2E测试数据"
- 状态: pending (待审核)
- 记录ID: cdd4fc7a-0a69-489a-b95e-c3e44fbcaf81

### 2. 发票申请记录 (Invoice Request)

```sql
INSERT INTO invoice_records (
  id,
  operator_id,
  invoice_type,
  invoice_amount,
  invoice_title,
  tax_id,
  bank_name,
  bank_account,
  company_address,
  company_phone,
  status,
  requested_at,
  created_at,
  updated_at
) VALUES (
  gen_random_uuid(),
  '40c3f8d9-bc57-49f3-a0d2-576bd575eed8',  -- testoperator001
  'vat_normal',
  1000.00,
  '测试公司有限公司',
  '91110000XXXXXXXXXX',
  '中国银行北京分行',
  '1234567890123456',
  '北京市朝阳区测试街道123号',
  '010-12345678',
  'pending',
  CURRENT_TIMESTAMP,
  CURRENT_TIMESTAMP,
  CURRENT_TIMESTAMP
);
```

**数据详情**:
- 运营商: testoperator001 (测试运营商公司)
- 发票类型: vat_normal (增值税普通发票)
- 发票金额: ¥1000.00
- 发票抬头: 测试公司有限公司
- 税号: 91110000XXXXXXXXXX
- 开户银行: 中国银行北京分行
- 银行账号: 1234567890123456
- 公司地址: 北京市朝阳区测试街道123号
- 公司电话: 010-12345678
- 状态: pending (待审核)
- 记录ID: 4435ffd1-c6f5-4b72-ac1b-16de92c0d5ae

## 验证查询

```sql
-- 验证测试数据是否创建成功
SELECT 'Refund' as type, COUNT(*) as count FROM refund_records WHERE status = 'pending'
UNION ALL
SELECT 'Invoice' as type, COUNT(*) as count FROM invoice_records WHERE status = 'pending';
```

## 用途

这些测试数据用于以下E2E测试:
- **T332**: 财务端 - 退款审核操作测试
- **T334**: 财务端 - 发票审核操作测试

## 如何重新创建

如果需要在新环境中重新创建这些测试数据，运行以下命令:

```bash
# 创建退款申请
docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops -c "
INSERT INTO refund_records (id, operator_id, requested_amount, refund_reason, status, created_at, updated_at)
VALUES (gen_random_uuid(), (SELECT id FROM operator_accounts WHERE username = 'testoperator001' LIMIT 1), 500.00, '测试退款申请 - E2E测试数据', 'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;
"

# 创建发票申请
docker exec mr_game_ops_db psql -U mr_admin -d mr_game_ops -c "
INSERT INTO invoice_records (id, operator_id, invoice_type, invoice_amount, invoice_title, tax_id, bank_name, bank_account, company_address, company_phone, status, requested_at, created_at, updated_at)
VALUES (gen_random_uuid(), (SELECT id FROM operator_accounts WHERE username = 'testoperator001' LIMIT 1), 'vat_normal', 1000.00, '测试公司有限公司', '91110000XXXXXXXXXX', '中国银行北京分行', '1234567890123456', '北京市朝阳区测试街道123号', '010-12345678', 'pending', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT DO NOTHING;
"
```

## 清理测试数据

如果需要清理这些测试数据:

```sql
-- 删除测试退款记录
DELETE FROM refund_records
WHERE refund_reason LIKE '%E2E测试数据%';

-- 删除测试发票记录
DELETE FROM invoice_records
WHERE invoice_title = '测试公司有限公司'
  AND tax_id = '91110000XXXXXXXXXX';
```

## 相关文档

- E2E测试报告: [E2E_TEST_REPORT.md](./E2E_TEST_REPORT.md)
- MVP发布计划: [MVP_RELEASE_PLAN.md](./MVP_RELEASE_PLAN.md)
- 任务清单: [tasks.md](./tasks.md)
