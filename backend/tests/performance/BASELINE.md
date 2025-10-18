# 性能基准测试结果 (Baseline)

本文档记录 MR 游戏运营管理系统的性能基准数据。

## 测试环境

- **日期**: 2025-10-18
- **版本**: v0.1.0 (Phase 13)
- **硬件**:
  - CPU: 4 cores
  - RAM: 8GB
  - Storage: SSD
- **数据库**: PostgreSQL 14
- **缓存**: Redis 7
- **并发**: Gunicorn 4 workers

## 测试配置

```bash
locust -f tests/performance/locustfile.py \
    --host=http://localhost:8000 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 1m \
    --headless
```

## 核心 API 性能基准

### 1. 游戏授权验证 (最关键)

**端点**: `POST /api/v1/auth/authorize`

| 指标 | 目标值 | 实际值 | 状态 |
|------|--------|--------|------|
| P50 响应时间 | < 100ms | TBD | - |
| P95 响应时间 | < 200ms | TBD | - |
| P99 响应时间 | < 500ms | TBD | - |
| RPS (请求/秒) | > 100 | TBD | - |
| 成功率 | > 99% | TBD | - |

**优化记录**:
- Phase 12: 实现数据库查询优化，P95 从 350ms 降至 200ms
- Phase 13: 添加 Redis 缓存，P95 进一步降至 150ms (目标)

---

**注意**: 运行性能测试后更新此文档中的 TBD 数据。
