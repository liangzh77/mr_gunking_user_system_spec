# OpenAPI 文档定制指南

本文档说明如何定制和增强 FastAPI 自动生成的 OpenAPI 文档。

## OpenAPI 访问

### 开发环境

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI JSON**: http://localhost:8000/api/openapi.json

### 生产环境

出于安全考虑，生产环境默认禁用 API 文档。如需启用：

1. 修改 `backend/deployment/nginx.conf`：

```nginx
# 注释掉以下行以启用文档
# location /api/docs {
#     deny all;
#     return 403;
# }
```

2. 设置环境变量：
```bash
export ENABLE_DOCS=true  # 仅推荐在内网或受保护环境
```

---

## 当前配置

### FastAPI 应用配置

```python
app = FastAPI(
    title="MR游戏运营管理系统",
    version="0.1.0",
    description="MR游戏运营管理系统 - 后端API",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)
```

---

## 端点文档最佳实践

### 1. 使用 Summary 和 Description

```python
@router.post(
    "/login",
    response_model=AdminLoginResponse,
    summary="管理员登录",  # 简短标题
    description="使用用户名和密码认证管理员，返回 JWT Token",  # 详细说明
)
```

### 2. 响应模型和状态码

```python
@router.get(
    "/balance",
    response_model=BalanceResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "API Key 无效"},
        429: {"description": "请求过多"},
    }
)
```

### 3. 参数说明

```python
async def get_invoices(
    status: Annotated[Optional[str], Query(
        description="发票状态: pending | approved | rejected"
    )] = None,
    page: Annotated[int, Query(
        description="页码（从1开始）",
        ge=1
    )] = 1,
):
    ...
```

### 4. 请求体示例

```python
class InvoiceRequest(BaseModel):
    amount_cents: int = Field(..., description="金额（分）", example=100000)
    invoice_type: str = Field(..., description="发票类型", example="vat_special")

    class Config:
        json_schema_extra = {
            "example": {
                "amount_cents": 100000,
                "invoice_type": "vat_special",
                "tax_id": "91110000XXXXXXXXX"
            }
        }
```

---

## Tags 分组

当前 API 按功能分组：

| Tag | 说明 | 示例端点 |
|-----|------|---------|
| Admin Authentication | 管理员认证 | /v1/admin/login |
| Admin Operations | 管理员操作 | /v1/admin/operators |
| Operator | 运营商 API | /v1/operator/balance |
| Finance | 财务管理 | /v1/finance/dashboard |
| Webhooks | Webhook 回调 | /v1/webhooks/payment |
| Health | 健康检查 | /health |

---

## 安全方案定义

### JWT Bearer 认证

```python
from fastapi.security import HTTPBearer

security = HTTPBearer()

app = FastAPI(
    # ...
    components={
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    }
)
```

### API Key 认证

```python
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
```

---

## 导出 OpenAPI Spec

### 导出为 JSON

```bash
# 启动应用
uvicorn src.main:app --host 0.0.0.0 --port 8000

# 下载 OpenAPI JSON
curl http://localhost:8000/api/openapi.json > openapi.json
```

### 导出为 YAML

```bash
pip install pyyaml

python -c "
import json
import yaml
from urllib.request import urlopen

spec = json.loads(urlopen('http://localhost:8000/api/openapi.json').read())
with open('openapi.yaml', 'w') as f:
    yaml.dump(spec, f, default_flow_style=False, allow_unicode=True)
"
```

---

## 生成客户端 SDK

### 使用 OpenAPI Generator

```bash
# 安装
npm install -g @openapitools/openapi-generator-cli

# 生成 Python 客户端
openapi-generator-cli generate \
  -i http://localhost:8000/api/openapi.json \
  -g python \
  -o ./sdk/python \
  --additional-properties=packageName=mr_game_sdk

# 生成 TypeScript 客户端
openapi-generator-cli generate \
  -i http://localhost:8000/api/openapi.json \
  -g typescript-axios \
  -o ./sdk/typescript
```

### 生成 Postman Collection

```bash
# 安装
npm install -g openapi-to-postmanv2

# 转换
openapi2postmanv2 \
  -s openapi.json \
  -o postman_collection.json \
  -p
```

---

## 示例代码

### 增强的端点文档

```python
@router.post(
    "/invoice/apply",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="申请发票",
    description="""
    运营商申请开具发票。

    **要求**:
    - 金额不能超过可开票额度
    - 必须提供完整的公司信息
    - 增值税专用发票需要银行信息

    **流程**:
    1. 提交申请
    2. 财务审核（3-5个工作日）
    3. 开具并邮寄发票
    """,
    responses={
        201: {
            "description": "发票申请成功",
            "content": {
                "application/json": {
                    "example": {
                        "invoice_id": "inv_123456",
                        "status": "pending",
                        "amount": "1000.00"
                    }
                }
            }
        },
        400: {"description": "金额超出可开票额度"},
        401: {"description": "API Key 无效"},
    },
    tags=["Finance"]
)
async def apply_invoice(
    request: InvoiceApplyRequest,
    api_key: str = Depends(api_key_header),
    db: AsyncSession = Depends(get_db),
):
    ...
```

---

## 自定义 OpenAPI Schema

### 修改默认配置

在 `src/main.py` 中：

```python
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="MR游戏运营管理系统 API",
        version="1.0.0",
        description="""
        # MR游戏运营管理系统后端 API

        ## 功能概述
        - 运营商账户管理
        - 财务结算系统
        - API Key 授权
        - 数据统计分析

        ## 认证方式
        - **管理员**: JWT Bearer Token
        - **运营商**: X-API-Key Header
        """,
        routes=app.routes,
    )

    # 添加认证方案
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
        }
    }

    # 添加服务器信息
    openapi_schema["servers"] = [
        {
            "url": "https://api.mr-game.com",
            "description": "生产环境"
        },
        {
            "url": "http://localhost:8000",
            "description": "开发环境"
        }
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

---

## 文档部署

### ReDoc 静态部署

```bash
# 安装 redoc-cli
npm install -g redoc-cli

# 生成静态 HTML
redoc-cli bundle openapi.json \
  -o docs/api.html \
  --title "MR游戏运营管理系统 API 文档"

# 部署到静态服务器
cp docs/api.html /var/www/docs/
```

### Swagger UI 静态部署

```bash
# 下载 Swagger UI
wget https://github.com/swagger-api/swagger-ui/archive/refs/tags/v5.0.0.tar.gz
tar -xzf v5.0.0.tar.gz

# 配置
cp openapi.json swagger-ui-5.0.0/dist/
cd swagger-ui-5.0.0/dist/
sed -i 's|https://petstore.swagger.io/v2/swagger.json|./openapi.json|' swagger-initializer.js

# 部署
cp -r swagger-ui-5.0.0/dist/* /var/www/swagger/
```

---

## Markdown 文档生成

### 使用 widdershins

```bash
# 安装
npm install -g widdershins

# 生成 Markdown
widdershins openapi.json \
  -o docs/API_REFERENCE.md \
  --language_tabs 'python:Python' 'javascript:JavaScript' \
  --summary
```

---

## 版本管理

### API 版本化策略

当前使用 URL 路径版本化：

- `/v1/admin/login` - API v1
- `/v2/admin/login` - API v2（未来）

### 文档版本

每次发布时保存 OpenAPI spec：

```bash
mkdir -p docs/openapi/
curl http://localhost:8000/api/openapi.json > docs/openapi/v1.0.0.json
git add docs/openapi/v1.0.0.json
git commit -m "docs: Add OpenAPI spec for v1.0.0"
```

---

## 测试文档

### 验证 OpenAPI Spec

```bash
# 使用 swagger-cli
npm install -g @apidevtools/swagger-cli

swagger-cli validate openapi.json
```

### 自动化文档测试

```python
# tests/test_openapi.py
def test_openapi_schema_valid():
    """测试 OpenAPI schema 有效性"""
    response = client.get("/api/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    assert "openapi" in schema
    assert schema["openapi"].startswith("3.")
    assert "paths" in schema
```

---

## 常见问题

### Q: 如何隐藏某个端点？

```python
@router.get("/internal", include_in_schema=False)
async def internal_endpoint():
    ...
```

### Q: 如何添加认证示例？

```python
@router.get(
    "/secure",
    dependencies=[Depends(security)],  # 自动添加到文档
)
```

### Q: 如何自定义错误响应？

```python
responses={
    404: {
        "description": "资源未找到",
        "model": ErrorResponse,
    }
}
```

---

## 参考资源

- [FastAPI OpenAPI 文档](https://fastapi.tiangolo.com/tutorial/metadata/)
- [OpenAPI 3.0 规范](https://swagger.io/specification/)
- [ReDoc 文档](https://github.com/Redocly/redoc)
- [Swagger UI](https://swagger.io/tools/swagger-ui/)
