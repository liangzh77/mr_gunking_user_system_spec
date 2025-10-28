#!/usr/bin/env python3
"""
批量更新 tasks.md 中已完成的任务标记
"""

# Phase 8 (US6) 已完成的任务列表
completed_tasks = {
    # 数据模型
    "T160": "创建FinanceAccount模型",
    "T161": "创建FinanceOperationLog模型",

    # Pydantic Schemas
    "T162": "创建财务登录Schema",
    "T163": "创建财务仪表盘Schema",
    "T164": "创建退款审核Schema",
    "T165": "创建发票审核Schema",
    "T166": "创建财务报表Schema",
    "T167": "创建审计日志Schema",

    # 业务服务
    "T168": "实现FinanceService",
    "T169": "实现FinanceDashboardService",
    "T170": "实现FinanceRefundService",
    "T171": "实现FinanceInvoiceService",
    "T172": "实现FinanceReportService",

    # API接口
    "T174": "实现财务人员登录API",
    "T175": "实现财务仪表盘API",
    "T176": "实现今日收入概览API",
    "T177": "实现本月趋势API",
    "T178": "实现大客户分析API",
    "T179": "实现客户财务详情API",
    "T180": "实现退款申请列表API",
    "T181": "实现退款详情API",
    "T182": "实现审核通过退款API",
    "T183": "实现拒绝退款API",
    "T184": "实现发票申请列表API",
    "T185": "实现审核发票API",
    "T186": "实现生成财务报表API",
    "T187": "实现导出报表API",
    "T188": "实现查询审计日志API",
    "T189": "注册财务路由",
}

tasks_file = "specs/001-mr-v2/tasks.md"

def update_tasks():
    with open(tasks_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 更新每个任务的标记
    for task_id in completed_tasks:
        # 将 - [ ] T### 替换为 - [X] T###
        content = content.replace(f"- [ ] {task_id} ", f"- [X] {task_id} ")

    with open(tasks_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ 已更新 {len(completed_tasks)} 个任务标记")
    print("\n已标记完成的任务:")
    for task_id, desc in completed_tasks.items():
        print(f"  - {task_id}: {desc}")

if __name__ == "__main__":
    update_tasks()
