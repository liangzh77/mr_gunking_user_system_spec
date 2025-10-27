# 技术调研报告：MR游戏运营管理系统

**项目**: MR游戏授权计费平台
**调研日期**: 2025-10-10
**调研范围**: 后端架构、数据库、安全认证、支付集成、前端技术、可观测性、测试策略
**技术栈**: FastAPI + PostgreSQL + Redis + React/Vue

---

## 目录

1. [FastAPI异步处理最佳实践](#1-fastapi异步处理最佳实践)
2. [PostgreSQL并发控制和事务管理](#2-postgresql并发控制和事务管理)
3. [Redis分布式锁实现](#3-redis分布式锁实现)
4. [API Key + HMAC签名认证](#4-api-key--hmac签名认证)
5. [支付平台集成](#5-支付平台集成)
6. [结构化日志和可观测性](#6-结构化日志和可观测性)
7. [数据库迁移和版本控制](#7-数据库迁移和版本控制)
8. [前端技术选型](#8-前端技术选型)
9. [SDK设计模式](#9-sdk设计模式)
10. [测试策略](#10-测试策略)

---

## 1. FastAPI异步处理最佳实践

### 决策

采用 **SQLAlchemy 2.0 异步引擎 + asyncpg驱动 + 异步依赖注入模式**

### 理由

- **功能满足度**: SQLAlchemy 2.0原生支持async/await，与FastAPI异步机制完美兼容，避免阻塞事件循环
- **性能考量**: asyncpg是PostgreSQL最快的Python驱动（比psycopg2快30-50%），支持连接池和预编译语句
- **社区支持**: SQLAlchemy 2.0在2023年正式发布，社区已稳定，FastAPI官方文档推荐此方案
- **兼容性**: 统一异步技术栈（FastAPI、SQLAlchemy、Redis-py 5.0+均支持async/await），避免混用同步/异步代码

### 备选方案

- **方案A: SQLAlchemy 1.4 + run_in_executor** - 拒绝原因：在线程池中运行同步代码，资源消耗高，无法充分利用异步优势
- **方案B: 纯SQL（asyncpg）+ 手动ORM** - 拒绝原因：放弃ORM便利性，维护成本高，不适合复杂业务逻辑
- **方案C: Tortoise ORM** - 拒绝原因：社区规模小，缺少企业级支持，迁移风险大

### 实施建议

**数据库会话管理（依赖注入）**:
```python
# backend/src/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/db",
    pool_size=20,        # 连接池大小（根据并发量调整）
    max_overflow=10,     # 最大溢出连接
    pool_pre_ping=True,  # 连接健康检查
    echo=False           # 生产环境关闭SQL日志
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False  # 防止提交后访问对象属性报错
)

# 依赖注入函数
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

**异步Redis客户端配置**:
```python
# backend/src/db/redis.py
from redis.asyncio import Redis, ConnectionPool

redis_pool = ConnectionPool.from_url(
    "redis://localhost:6379/0",
    max_connections=50,
    decode_responses=True  # 自动解码字节为字符串
)

async def get_redis() -> Redis:
    return Redis(connection_pool=redis_pool)
```

**中间件设计（认证、日志、限流）**:
```python
# backend/src/api/middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import structlog

logger = structlog.get_logger()

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("X-Trace-ID", str(uuid4()))
        structlog.contextvars.bind_contextvars(trace_id=trace_id)

        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=int(duration * 1000)
        )
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis: Redis):
        super().__init__(app)
        self.redis = redis

    async def dispatch(self, request: Request, call_next):
        operator_id = request.state.operator_id  # 由认证中间件设置
        key = f"rate_limit:{operator_id}"

        # 滑动窗口限流（1分钟10次）
        current = await self.redis.incr(key)
        if current == 1:
            await self.redis.expire(key, 60)

        if current > 10:
            return JSONResponse(
                {"error": "Rate limit exceeded"},
                status_code=429
            )

        return await call_next(request)
```

**服务层异步模式**:
```python
# backend/src/services/billing.py
class BillingService:
    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis

    async def authorize_game(
        self,
        operator_id: int,
        app_id: int,
        player_count: int,
        session_id: str
    ) -> AuthorizationResult:
        # 1. 幂等性检查（Redis缓存）
        cached = await self.redis.get(f"auth:{session_id}")
        if cached:
            return AuthorizationResult.parse_raw(cached)

        # 2. 行级锁 + 事务
        async with self.db.begin():
            operator = await self.db.execute(
                select(Operator)
                .where(Operator.id == operator_id)
                .with_for_update()  # 行级锁
            )
            operator = operator.scalar_one()

            # 3. 业务逻辑...
            if operator.balance < total_cost:
                raise InsufficientBalanceError()

            operator.balance -= total_cost
            # ... 创建使用记录等

        # 4. 缓存结果（15分钟）
        await self.redis.setex(
            f"auth:{session_id}",
            900,
            result.json()
        )
        return result
```

**关键要点**:
- 所有数据库操作使用 `async with` 或 `await`
- 避免在异步函数中调用同步IO（文件读写、requests库等）
- 使用 `asyncio.gather()` 并行执行独立任务（如同时查询多个表）
- 连接池大小设置为 `CPU核心数 × 2 + 磁盘数`（推荐20-50）

---

## 2. PostgreSQL并发控制和事务管理

### 决策

采用 **READ COMMITTED隔离级别 + SELECT FOR UPDATE行级锁 + 乐观锁（version字段）组合方案**

### 理由

- **功能满足度**: 满足高并发扣费场景的数据一致性需求，防止余额重复扣减
- **性能考量**: READ COMMITTED避免SERIALIZABLE的高性能开销（减少事务重试），行级锁仅锁定操作行不阻塞其他运营商
- **死锁风险**: 按固定顺序获取锁（先Operator表后UsageRecord表），降低死锁概率
- **行业实践**: 大部分金融级应用（支付宝、微信支付）采用类似方案

### 备选方案

- **方案A: SERIALIZABLE隔离级别** - 拒绝原因：性能开销大（大量事务重试），吞吐量下降50%，不适合高并发场景
- **方案B: 仅乐观锁（无行级锁）** - 拒绝原因：高并发时冲突率高，用户体验差（频繁重试）
- **方案C: 应用层分布式锁（仅Redis）** - 拒绝原因：无法保证与数据库事务原子性，Redis故障时数据不一致

### 实施建议

**隔离级别配置**:
```python
# backend/src/db/session.py
engine = create_async_engine(
    "postgresql+asyncpg://...",
    isolation_level="READ_COMMITTED"  # 默认即可，无需显式设置
)
```

**行级锁实现（并发扣费）**:
```python
# backend/src/services/billing.py
async def deduct_balance(
    db: AsyncSession,
    operator_id: int,
    amount: Decimal
) -> Operator:
    async with db.begin():  # 自动开启事务
        # SELECT ... FOR UPDATE 悲观锁
        result = await db.execute(
            select(Operator)
            .where(Operator.id == operator_id)
            .with_for_update(nowait=False)  # 等待锁释放（默认）
        )
        operator = result.scalar_one()

        # 验证余额
        if operator.balance < amount:
            raise InsufficientBalanceError(
                f"余额不足: 当前{operator.balance}, 需要{amount}"
            )

        # 扣费
        operator.balance -= amount

        # 创建交易记录（同一事务内）
        transaction = TransactionRecord(
            operator_id=operator_id,
            type="consume",
            amount=amount,
            created_at=datetime.utcnow()
        )
        db.add(transaction)

        # 提交由context manager自动处理
        return operator
```

**乐观锁实现（价格调整场景）**:
```python
# backend/src/models/application.py
class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True)
    price_per_player = Column(Numeric(10, 2), nullable=False)
    version = Column(Integer, default=1, nullable=False)  # 乐观锁版本号

    @validates("price_per_player")
    def validate_price(self, key, value):
        if value <= 0:
            raise ValueError("价格必须大于0")
        return value

# 更新时检查版本号
async def update_app_price(
    db: AsyncSession,
    app_id: int,
    new_price: Decimal,
    expected_version: int
):
    result = await db.execute(
        update(Application)
        .where(
            Application.id == app_id,
            Application.version == expected_version  # 版本号匹配才更新
        )
        .values(
            price_per_player=new_price,
            version=Application.version + 1  # 自增版本号
        )
    )

    if result.rowcount == 0:
        raise OptimisticLockError("数据已被其他用户修改，请刷新后重试")
```

**死锁检测和处理**:
```python
# backend/src/core/exceptions.py
from sqlalchemy.exc import DBAPIError

async def safe_transaction(db: AsyncSession, operation):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with db.begin():
                return await operation(db)
        except DBAPIError as e:
            if "deadlock detected" in str(e).lower():
                if attempt == max_retries - 1:
                    raise DeadlockError("事务死锁，请稍后重试")
                await asyncio.sleep(0.1 * (2 ** attempt))  # 指数退避
            else:
                raise
```

**索引优化（减少锁等待时间）**:
```sql
-- 运营商余额查询索引
CREATE INDEX idx_operator_balance ON operators(id, balance) WHERE is_deleted = false;

-- 应用授权关系查询索引
CREATE INDEX idx_app_auth ON operator_app_authorizations(operator_id, app_id, expires_at);

-- 使用记录时间范围查询索引
CREATE INDEX idx_usage_created ON usage_records(operator_id, created_at DESC);

-- 事务记录查询索引
CREATE INDEX idx_transaction_operator_time ON transaction_records(operator_id, created_at DESC);
```

**关键要点**:
- 事务尽量短（避免长时间持有锁）
- 按固定顺序访问表（先Operator → Application → UsageRecord，避免循环依赖）
- 使用 `NOWAIT` 选项快速失败（适合用户交互场景）
- 定期监控死锁日志（PostgreSQL `log_lock_waits` 参数）

---

## 3. Redis分布式锁实现

### 决策

采用 **单实例Redis + SET NX EX + Lua脚本释放锁 + 看门狗自动续期**

### 理由

- **功能满足度**: 满足防重复扣费、幂等性保证需求，性能优于数据库锁
- **性能考量**: Redis单实例QPS可达10万+，延迟<1ms，远快于数据库
- **复杂度**: Redlock算法需要多个Redis实例，运维成本高，单实例足够应对当前规模（100运营商）
- **一致性**: 配合数据库事务使用（Redis锁用于去重，数据库锁保证一致性）

### 备选方案

- **方案A: Redlock算法（多Redis实例）** - 拒绝原因：过度设计，系统规模不需要跨实例强一致性，运维复杂度高
- **方案B: 数据库唯一约束（UNIQUE INDEX on session_id）** - 拒绝原因：性能不如Redis，无法设置过期时间，需手动清理
- **方案C: Zookeeper分布式锁** - 拒绝原因：引入新组件增加复杂度，CP模型不适合高可用要求

### 实施建议

**基础分布式锁实现**:
```python
# backend/src/utils/redis_lock.py
import asyncio
from redis.asyncio import Redis

class RedisLock:
    def __init__(
        self,
        redis: Redis,
        key: str,
        timeout: int = 30,
        blocking: bool = True,
        blocking_timeout: int = 10
    ):
        self.redis = redis
        self.key = f"lock:{key}"
        self.timeout = timeout  # 锁超时时间（秒）
        self.blocking = blocking
        self.blocking_timeout = blocking_timeout
        self.identifier = str(uuid4())  # 唯一标识符（防止误删其他客户端的锁）
        self._watchdog_task = None

    async def acquire(self) -> bool:
        """获取锁"""
        end_time = time.time() + self.blocking_timeout

        while True:
            # SET key value NX EX timeout（原子操作）
            acquired = await self.redis.set(
                self.key,
                self.identifier,
                nx=True,  # 仅当key不存在时设置
                ex=self.timeout  # 过期时间（防止死锁）
            )

            if acquired:
                # 启动看门狗自动续期
                self._watchdog_task = asyncio.create_task(self._watchdog())
                return True

            if not self.blocking or time.time() > end_time:
                return False

            await asyncio.sleep(0.01)  # 短暂休眠避免CPU空转

    async def release(self):
        """释放锁（Lua脚本保证原子性）"""
        if self._watchdog_task:
            self._watchdog_task.cancel()

        # Lua脚本：仅删除自己持有的锁
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        await self.redis.eval(lua_script, 1, self.key, self.identifier)

    async def _watchdog(self):
        """看门狗：自动续期（每timeout/3秒续期一次）"""
        try:
            while True:
                await asyncio.sleep(self.timeout / 3)

                # 续期Lua脚本（仅续期自己持有的锁）
                lua_script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("expire", KEYS[1], ARGV[2])
                else
                    return 0
                end
                """
                renewed = await self.redis.eval(
                    lua_script,
                    1,
                    self.key,
                    self.identifier,
                    self.timeout
                )
                if not renewed:
                    break  # 锁已被释放或过期
        except asyncio.CancelledError:
            pass

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()
```

**防重复扣费应用**:
```python
# backend/src/services/billing.py
async def authorize_game_idempotent(
    db: AsyncSession,
    redis: Redis,
    session_id: str,
    ...
):
    # 1. 快速检查缓存（避免不必要的锁竞争）
    cached = await redis.get(f"auth:{session_id}")
    if cached:
        return AuthorizationResult.parse_raw(cached)

    # 2. 分布式锁防止并发重复扣费
    async with RedisLock(redis, f"auth_lock:{session_id}", timeout=30):
        # 双重检查（Double-Check）
        cached = await redis.get(f"auth:{session_id}")
        if cached:
            return AuthorizationResult.parse_raw(cached)

        # 3. 执行扣费逻辑（数据库事务）
        result = await _do_authorize(db, ...)

        # 4. 缓存结果（15分钟）
        await redis.setex(
            f"auth:{session_id}",
            900,
            result.json()
        )

        return result
```

**滑动窗口限流实现**:
```python
# backend/src/utils/rate_limiter.py
async def check_rate_limit(
    redis: Redis,
    operator_id: int,
    limit: int = 10,
    window: int = 60
) -> bool:
    """滑动窗口限流（1分钟10次）"""
    key = f"rate_limit:{operator_id}"
    now = time.time()

    # Lua脚本实现滑动窗口
    lua_script = """
    local key = KEYS[1]
    local now = tonumber(ARGV[1])
    local window = tonumber(ARGV[2])
    local limit = tonumber(ARGV[3])

    -- 移除窗口外的记录
    redis.call('zremrangebyscore', key, 0, now - window)

    -- 获取当前窗口内的请求数
    local current = redis.call('zcard', key)

    if current < limit then
        -- 添加当前请求
        redis.call('zadd', key, now, now)
        redis.call('expire', key, window)
        return 1
    else
        return 0
    end
    """

    allowed = await redis.eval(
        lua_script,
        1,
        key,
        now,
        window,
        limit
    )

    return bool(allowed)
```

**关键要点**:
- 锁超时时间必须大于业务处理时间（建议3-5倍）
- 使用唯一标识符（UUID）防止误删其他客户端的锁
- Lua脚本保证操作原子性（Redis单线程执行）
- 看门狗续期防止业务处理时间超过锁超时
- Redis持久化配置（AOF每秒同步）平衡性能和可靠性

---

## 4. API Key + HMAC签名认证

### 决策

采用 **API Key识别 + HMAC-SHA256签名验证 + Timestamp + Nonce防重放攻击**

### 理由

- **功能满足度**: 满足头显Server无状态认证需求，签名验证防止篡改，无需OAuth复杂流程
- **性能考量**: HMAC-SHA256计算速度快（<1ms），无需查询数据库会话
- **安全性**: 密钥不传输网络（仅传输签名），timestamp限制5分钟有效期，nonce防止重放
- **行业标准**: AWS、阿里云等云平台广泛使用此方案

### 备选方案

- **方案A: JWT Token** - 拒绝原因：需要定期刷新token（增加复杂度），头显Server无浏览器环境难以管理
- **方案B: OAuth 2.0** - 拒绝原因：过度设计，头显Server到后端是服务间调用，无需三方授权流程
- **方案C: 仅API Key（无签名）** - 拒绝原因：易被中间人攻击篡改请求，安全性不足

### 实施建议

**签名算法实现（服务端）**:
```python
# backend/src/core/security.py
import hmac
import hashlib
from datetime import datetime, timedelta

class HMACAuth:
    @staticmethod
    def generate_signature(
        api_key: str,
        api_secret: str,
        method: str,
        path: str,
        timestamp: int,
        nonce: str,
        body: str = ""
    ) -> str:
        """生成HMAC-SHA256签名"""
        # 签名字符串格式：METHOD\nPATH\nTIMESTAMP\nNONCE\nBODY
        message = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body}"

        signature = hmac.new(
            api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return signature

    @staticmethod
    async def verify_request(
        db: AsyncSession,
        redis: Redis,
        api_key: str,
        signature: str,
        timestamp: int,
        nonce: str,
        method: str,
        path: str,
        body: str = ""
    ) -> Operator:
        """验证请求签名"""
        # 1. 验证时间戳（5分钟有效期）
        now = int(datetime.utcnow().timestamp())
        if abs(now - timestamp) > 300:
            raise AuthenticationError("请求已过期（时间戳超过5分钟）")

        # 2. 验证Nonce（防止重放攻击）
        nonce_key = f"nonce:{nonce}"
        if await redis.exists(nonce_key):
            raise AuthenticationError("重复请求（Nonce已使用）")

        # 缓存Nonce（5分钟过期）
        await redis.setex(nonce_key, 300, "1")

        # 3. 查询API Secret（缓存优化）
        cache_key = f"api_secret:{api_key}"
        api_secret = await redis.get(cache_key)

        if not api_secret:
            result = await db.execute(
                select(Operator.api_secret, Operator.id)
                .where(Operator.api_key == api_key, Operator.is_deleted == False)
            )
            row = result.one_or_none()
            if not row:
                raise AuthenticationError("无效的API Key")

            api_secret, operator_id = row
            # 缓存1小时
            await redis.setex(cache_key, 3600, api_secret)

        # 4. 计算期望签名
        expected_signature = HMACAuth.generate_signature(
            api_key, api_secret, method, path, timestamp, nonce, body
        )

        # 5. 常量时间比较（防止时序攻击）
        if not hmac.compare_digest(signature, expected_signature):
            raise AuthenticationError("签名验证失败")

        # 6. 返回运营商对象
        operator = await db.get(Operator, operator_id)
        return operator
```

**FastAPI依赖注入认证**:
```python
# backend/src/api/deps.py
from fastapi import Header, Depends, Request

async def get_current_operator(
    request: Request,
    x_api_key: str = Header(..., alias="X-API-Key"),
    x_signature: str = Header(..., alias="X-Signature"),
    x_timestamp: int = Header(..., alias="X-Timestamp"),
    x_nonce: str = Header(..., alias="X-Nonce"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> Operator:
    """认证中间件依赖"""
    body = await request.body()

    operator = await HMACAuth.verify_request(
        db=db,
        redis=redis,
        api_key=x_api_key,
        signature=x_signature,
        timestamp=x_timestamp,
        nonce=x_nonce,
        method=request.method,
        path=request.url.path,
        body=body.decode('utf-8') if body else ""
    )

    return operator

# 使用示例
@router.post("/v1/authorize")
async def authorize_game(
    request: AuthorizeRequest,
    operator: Operator = Depends(get_current_operator),
    db: AsyncSession = Depends(get_db)
):
    # operator已认证，可直接使用
    ...
```

**SDK客户端实现（Python）**:
```python
# sdk/python/mr_auth_sdk/client.py
import hmac
import hashlib
import time
import uuid
import httpx

class MRAuthClient:
    def __init__(self, api_key: str, api_secret: str, base_url: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url

    def _generate_signature(
        self,
        method: str,
        path: str,
        timestamp: int,
        nonce: str,
        body: str = ""
    ) -> str:
        message = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body}"
        return hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    async def authorize_game(
        self,
        app_id: int,
        player_count: int,
        session_id: str
    ) -> dict:
        """请求游戏授权"""
        path = "/v1/authorize"
        method = "POST"
        timestamp = int(time.time())
        nonce = str(uuid.uuid4())

        body_dict = {
            "app_id": app_id,
            "player_count": player_count,
            "session_id": session_id
        }
        body = json.dumps(body_dict)

        # 生成签名
        signature = self._generate_signature(method, path, timestamp, nonce, body)

        # 发送请求
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}{path}",
                headers={
                    "X-API-Key": self.api_key,
                    "X-Signature": signature,
                    "X-Timestamp": str(timestamp),
                    "X-Nonce": nonce,
                    "Content-Type": "application/json"
                },
                content=body
            )
            response.raise_for_status()
            return response.json()
```

**API Key轮换策略**:
```python
# backend/src/services/operator.py
async def rotate_api_key(db: AsyncSession, operator_id: int) -> tuple[str, str]:
    """轮换API Key（生成新Key，旧Key保留24小时）"""
    operator = await db.get(Operator, operator_id)

    # 生成新Key和Secret
    new_api_key = secrets.token_urlsafe(48)  # 64字符
    new_api_secret = secrets.token_urlsafe(48)

    # 旧Key移到历史表（24小时过期）
    old_key_record = DeprecatedAPIKey(
        operator_id=operator_id,
        api_key=operator.api_key,
        api_secret=operator.api_secret,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.add(old_key_record)

    # 更新新Key
    operator.api_key = new_api_key
    operator.api_secret = new_api_secret

    await db.commit()

    return new_api_key, new_api_secret
```

**关键要点**:
- 签名字符串必须包含所有关键参数（防止篡改）
- 使用 `hmac.compare_digest()` 防止时序攻击
- Nonce使用UUID v4（全局唯一）
- API Secret永不传输网络（仅在本地计算签名）
- 支持优雅轮换（新旧Key并存24小时）

---

## 5. 支付平台集成

### 决策

采用 **官方SDK（微信支付v3 + 支付宝SDK）+ 异步回调处理 + 主动查询兜底**

### 理由

- **功能满足度**: 官方SDK封装签名验证、错误处理，降低开发成本，支持最新API（微信v3、支付宝OpenAPI）
- **安全性**: 官方SDK定期更新修复安全漏洞，签名算法符合PCI DSS标准
- **可靠性**: 异步回调 + 5分钟超时主动查询，覆盖网络抖动、回调丢失场景
- **社区支持**: 官方SDK文档完善，问题可直接提交官方工单

### 备选方案

- **方案A: 手动实现签名算法** - 拒绝原因：维护成本高，易出现安全漏洞，官方算法更新需同步修改
- **方案B: 使用消息队列处理回调（Kafka/RabbitMQ）** - 拒绝原因：系统规模不需要消息队列（过度设计），直接处理回调即可
- **方案C: 仅依赖回调（无主动查询）** - 拒绝原因：回调可能丢失（网络故障、防火墙），导致充值成功但余额未更新

### 实施建议

**微信支付集成（Native支付）**:
```python
# backend/src/services/payment.py
from wechatpayv3 import WeChatPay, WeChatPayType

class PaymentService:
    def __init__(self):
        self.wxpay = WeChatPay(
            wechatpay_type=WeChatPayType.NATIVE,
            mchid=settings.WECHAT_MCHID,
            private_key=settings.WECHAT_PRIVATE_KEY,
            cert_serial_no=settings.WECHAT_CERT_SERIAL_NO,
            apiv3_key=settings.WECHAT_APIV3_KEY,
            appid=settings.WECHAT_APPID
        )

    async def create_recharge_order(
        self,
        db: AsyncSession,
        operator_id: int,
        amount: Decimal
    ) -> dict:
        """创建充值订单"""
        # 1. 生成订单号（唯一）
        order_no = f"RC{int(time.time())}{operator_id:06d}"

        # 2. 创建订单记录（状态：待支付）
        recharge_order = RechargeOrder(
            order_no=order_no,
            operator_id=operator_id,
            amount=amount,
            status="pending",
            payment_channel="wechat",
            created_at=datetime.utcnow()
        )
        db.add(recharge_order)
        await db.commit()

        # 3. 调用微信支付API
        code, message = self.wxpay.pay(
            description=f"MR游戏平台充值 - {amount}元",
            out_trade_no=order_no,
            amount={
                "total": int(amount * 100),  # 分
                "currency": "CNY"
            },
            notify_url=f"{settings.API_BASE_URL}/v1/payment/wechat/callback"
        )

        if code != 200:
            raise PaymentError(f"微信支付下单失败: {message}")

        # 返回二维码链接（前端生成二维码）
        return {
            "order_no": order_no,
            "code_url": message["code_url"],
            "expires_at": datetime.utcnow() + timedelta(minutes=30)
        }

    async def handle_wechat_callback(
        self,
        db: AsyncSession,
        request_body: dict,
        signature: str,
        timestamp: str,
        nonce: str
    ):
        """处理微信支付回调"""
        # 1. 验证签名（防止伪造）
        try:
            result = self.wxpay.callback(
                headers={
                    "Wechatpay-Signature": signature,
                    "Wechatpay-Timestamp": timestamp,
                    "Wechatpay-Nonce": nonce,
                    "Wechatpay-Serial": request_body.get("serial")
                },
                body=request_body
            )
        except Exception as e:
            logger.error("微信支付回调签名验证失败", error=str(e))
            raise

        # 2. 查询订单
        order_no = result["out_trade_no"]
        order = await db.execute(
            select(RechargeOrder).where(RechargeOrder.order_no == order_no)
        )
        order = order.scalar_one_or_none()

        if not order:
            logger.error("订单不存在", order_no=order_no)
            return

        if order.status == "completed":
            logger.info("订单已处理", order_no=order_no)
            return  # 幂等性处理

        # 3. 更新订单和余额（事务）
        async with db.begin():
            order.status = "completed"
            order.transaction_id = result["transaction_id"]
            order.completed_at = datetime.utcnow()

            # 增加余额
            operator = await db.get(Operator, order.operator_id)
            operator.balance += order.amount

            # 创建交易记录
            transaction = TransactionRecord(
                operator_id=order.operator_id,
                type="recharge",
                amount=order.amount,
                channel="wechat",
                order_no=order_no,
                created_at=datetime.utcnow()
            )
            db.add(transaction)

        logger.info(
            "充值成功",
            order_no=order_no,
            amount=float(order.amount),
            operator_id=order.operator_id
        )
```

**主动查询兜底（定时任务）**:
```python
# backend/src/tasks/payment_checker.py
import asyncio

async def check_pending_orders():
    """检查5分钟未回调的订单"""
    async with AsyncSessionLocal() as db:
        # 查询5-10分钟前创建且仍为pending的订单
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        result = await db.execute(
            select(RechargeOrder).where(
                RechargeOrder.status == "pending",
                RechargeOrder.created_at < cutoff_time
            )
        )
        pending_orders = result.scalars().all()

        for order in pending_orders:
            try:
                # 主动查询支付平台
                if order.payment_channel == "wechat":
                    code, result = wxpay.query(out_trade_no=order.order_no)

                    if code == 200 and result["trade_state"] == "SUCCESS":
                        # 补偿处理（模拟回调）
                        await handle_wechat_callback(db, result, ...)
                    elif result["trade_state"] == "CLOSED":
                        order.status = "cancelled"
                        await db.commit()
            except Exception as e:
                logger.error(
                    "订单查询失败",
                    order_no=order.order_no,
                    error=str(e)
                )

# 启动定时任务（使用APScheduler）
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
scheduler.add_job(check_pending_orders, 'interval', minutes=2)
scheduler.start()
```

**支付宝集成（类似流程）**:
```python
from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient
from alipay.aop.api.request.AlipayTradePrecreateRequest import AlipayTradePrecreateRequest

class AlipayService:
    def __init__(self):
        alipay_config = AlipayClientConfig()
        alipay_config.app_id = settings.ALIPAY_APP_ID
        alipay_config.app_private_key = settings.ALIPAY_PRIVATE_KEY
        alipay_config.alipay_public_key = settings.ALIPAY_PUBLIC_KEY
        self.client = DefaultAlipayClient(alipay_config=alipay_config)

    async def create_order(self, order_no: str, amount: Decimal) -> str:
        request = AlipayTradePrecreateRequest()
        request.biz_content = {
            "out_trade_no": order_no,
            "total_amount": str(amount),
            "subject": "MR游戏平台充值",
            "notify_url": f"{settings.API_BASE_URL}/v1/payment/alipay/callback"
        }

        response = self.client.execute(request)
        if response.is_success():
            return response.qr_code  # 二维码链接
        else:
            raise PaymentError(f"支付宝下单失败: {response.msg}")
```

**关键要点**:
- 回调接口必须返回200（否则支付平台会重试）
- 使用幂等性处理（订单状态检查）
- 金额单位转换（微信：分，支付宝：元）
- 定时任务2分钟执行一次（检查5分钟前的订单）
- 敏感密钥通过环境变量注入（不提交代码库）

---

## 6. 结构化日志和可观测性

### 决策

采用 **structlog（结构化日志）+ OpenTelemetry（分布式追踪）+ Prometheus（指标）+ Grafana（可视化）**

### 理由

- **功能满足度**: structlog支持JSON格式输出，便于日志聚合系统（ELK/Loki）解析，OpenTelemetry是CNCF标准
- **性能考量**: structlog性能优于标准logging（减少字符串拼接），Prometheus拉模式无需主动推送
- **生态兼容**: OpenTelemetry支持多种后端（Jaeger、Zipkin、SigNoz），Prometheus兼容Kubernetes生态
- **审计要求**: JSON格式日志便于审计查询（按trace_id、operator_id检索）

### 备选方案

- **方案A: 标准logging库 + ELK** - 拒绝原因：logging输出非结构化文本，需额外正则解析，structlog原生JSON输出
- **方案B: Sentry（错误追踪）** - 拒绝原因：Sentry专注异常监控，无法替代完整可观测性方案（日志、追踪、指标）
- **方案C: 自建APM（Application Performance Monitoring）** - 拒绝原因：开发维护成本高，OpenTelemetry已是行业标准

### 实施建议

**structlog配置（JSON格式）**:
```python
# backend/src/core/logging.py
import structlog
from structlog.processors import JSONRenderer, TimeStamper, add_log_level

def configure_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # 合并上下文变量（trace_id等）
            add_log_level,  # 添加日志级别
            TimeStamper(fmt="iso", utc=True),  # ISO 8601时间戳
            structlog.processors.StackInfoRenderer(),  # 堆栈信息
            structlog.processors.format_exc_info,  # 异常格式化
            JSONRenderer()  # JSON输出
        ],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

# 使用示例
logger = structlog.get_logger()

# 绑定上下文变量（整个请求链路可见）
structlog.contextvars.bind_contextvars(
    trace_id="abc123",
    operator_id=42
)

logger.info(
    "game_authorized",
    app_id=10,
    player_count=5,
    cost=50.0,
    session_id="session_123"
)

# 输出（JSON格式）:
# {
#   "event": "game_authorized",
#   "level": "info",
#   "timestamp": "2025-10-10T10:30:45.123456Z",
#   "trace_id": "abc123",
#   "operator_id": 42,
#   "app_id": 10,
#   "player_count": 5,
#   "cost": 50.0,
#   "session_id": "session_123"
# }
```

**OpenTelemetry集成（分布式追踪）**:
```python
# backend/src/core/tracing.py
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

def setup_tracing(app):
    # 1. 配置Tracer Provider
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer_provider()

    # 2. 配置Exporter（发送到Jaeger/SigNoz）
    otlp_exporter = OTLPSpanExporter(
        endpoint="http://localhost:4317",  # OTLP gRPC端点
        insecure=True
    )
    tracer.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # 3. 自动埋点（FastAPI + SQLAlchemy）
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)

    return tracer

# 手动埋点示例
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def authorize_game(...):
    with tracer.start_as_current_span("authorize_game") as span:
        span.set_attribute("operator_id", operator_id)
        span.set_attribute("app_id", app_id)
        span.set_attribute("player_count", player_count)

        # 业务逻辑...
        result = await _do_authorize(...)

        span.set_attribute("total_cost", float(result.total_cost))
        return result
```

**Prometheus指标暴露**:
```python
# backend/src/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY

# 定义指标
authorization_requests = Counter(
    "authorization_requests_total",
    "授权请求总数",
    ["operator_id", "app_id", "status"]  # 标签
)

authorization_duration = Histogram(
    "authorization_duration_seconds",
    "授权请求处理时间",
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0]  # 直方图桶
)

operator_balance = Gauge(
    "operator_balance_yuan",
    "运营商余额",
    ["operator_id"]
)

# 业务代码中使用
async def authorize_game(...):
    with authorization_duration.time():  # 自动记录耗时
        try:
            result = await _do_authorize(...)
            authorization_requests.labels(
                operator_id=operator_id,
                app_id=app_id,
                status="success"
            ).inc()

            # 更新余额指标
            operator_balance.labels(operator_id=operator_id).set(
                float(operator.balance)
            )

            return result
        except Exception as e:
            authorization_requests.labels(
                operator_id=operator_id,
                app_id=app_id,
                status="failed"
            ).inc()
            raise

# FastAPI端点暴露指标
@app.get("/metrics")
async def metrics():
    return Response(
        generate_latest(REGISTRY),
        media_type="text/plain"
    )
```

**审计日志设计（不可变表）**:
```python
# backend/src/models/audit_log.py
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    trace_id = Column(String(36), nullable=False, index=True)
    operator_id = Column(Integer, index=True)
    action = Column(String(50), nullable=False)  # authorize_game, recharge, refund等
    resource_type = Column(String(50))  # operator, application, usage_record等
    resource_id = Column(Integer)
    details = Column(JSON)  # 详细参数
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("idx_audit_action_time", "action", "created_at"),
        Index("idx_audit_operator_time", "operator_id", "created_at"),
    )

# 记录审计日志
async def log_audit(
    db: AsyncSession,
    trace_id: str,
    operator_id: int,
    action: str,
    resource_type: str,
    resource_id: int,
    details: dict,
    ip_address: str
):
    audit = AuditLog(
        trace_id=trace_id,
        operator_id=operator_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        created_at=datetime.utcnow()
    )
    db.add(audit)
    # 不立即commit，由业务事务统一提交
```

**Grafana仪表盘配置（PromQL示例）**:
```promql
# 授权成功率（1分钟内）
sum(rate(authorization_requests_total{status="success"}[1m]))
/
sum(rate(authorization_requests_total[1m])) * 100

# P95响应时间
histogram_quantile(0.95,
  sum(rate(authorization_duration_seconds_bucket[5m])) by (le)
)

# 按运营商消费总金额（今日）
sum by (operator_id) (
  increase(authorization_requests_total{status="success"}[1d])
)
```

**关键要点**:
- trace_id贯穿整个请求链路（从API网关到数据库）
- 审计日志仅插入不更新（append-only），定期归档到冷存储
- Prometheus指标命名遵循规范（`<namespace>_<name>_<unit>`）
- 日志级别：DEBUG（开发环境），INFO（生产环境），ERROR（告警）
- 使用日志采样（高流量时仅记录1%请求）

---

## 7. 数据库迁移和版本控制

### 决策

采用 **Alembic（官方推荐）+ 先增后删零停机迁移策略 + 自动化回滚脚本**

### 理由

- **功能满足度**: Alembic与SQLAlchemy深度集成，支持自动生成迁移脚本（对比模型差异）
- **安全性**: 版本链管理，支持upgrade/downgrade，避免手动SQL错误
- **零停机**: 先增后删策略（添加新列 → 双写 → 删除旧列），服务不中断
- **行业标准**: Django、Rails等主流框架均采用类似迁移机制

### 备选方案

- **方案A: 手动SQL脚本** - 拒绝原因：易出错，无版本管理，回滚困难
- **方案B: SQLAlchemy-migrate** - 拒绝原因：项目已停止维护，Alembic是官方继任者
- **方案C: Flyway/Liquibase（Java生态）** - 拒绝原因：不适合Python项目，与SQLAlchemy集成差

### 实施建议

**Alembic初始化配置**:
```bash
# 初始化Alembic
alembic init alembic

# 配置数据库连接（alembic.ini）
# sqlalchemy.url = postgresql+asyncpg://user:pass@localhost/db
```

```python
# alembic/env.py
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from backend.src.models import Base  # 导入所有模型

config = context.config
target_metadata = Base.metadata

def run_migrations_online():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,  # 检测列类型变化
        compare_server_default=True  # 检测默认值变化
    )

    with context.begin_transaction():
        context.run_migrations()
```

**生成迁移脚本**:
```bash
# 自动生成迁移（对比模型和数据库差异）
alembic revision --autogenerate -m "Add operator balance column"

# 手动创建迁移
alembic revision -m "Create index on usage_records"
```

**零停机迁移示例（重命名列）**:
```python
# alembic/versions/001_rename_price_column.py
"""Rename price to price_per_player

Revision ID: 001
Revises:
Create Date: 2025-10-10

"""
from alembic import op
import sqlalchemy as sa

# Step 1: 添加新列（保留旧列）
def upgrade():
    # 添加新列
    op.add_column('applications',
        sa.Column('price_per_player', sa.Numeric(10, 2), nullable=True)
    )

    # 复制数据（旧列 → 新列）
    op.execute(
        "UPDATE applications SET price_per_player = price WHERE price_per_player IS NULL"
    )

    # 设置新列NOT NULL（数据已复制）
    op.alter_column('applications', 'price_per_player', nullable=False)

    # 注释：第二次迁移再删除旧列（给业务代码时间适配）

def downgrade():
    op.drop_column('applications', 'price_per_player')

# Step 2: 删除旧列（新版本发布后）
# alembic/versions/002_drop_old_price_column.py
def upgrade():
    op.drop_column('applications', 'price')

def downgrade():
    op.add_column('applications',
        sa.Column('price', sa.Numeric(10, 2), nullable=True)
    )
    op.execute("UPDATE applications SET price = price_per_player")
    op.alter_column('applications', 'price', nullable=False)
```

**索引创建（并发模式）**:
```python
# alembic/versions/003_add_index_concurrently.py
def upgrade():
    # PostgreSQL CONCURRENTLY选项（不锁表）
    op.execute(
        "CREATE INDEX CONCURRENTLY idx_usage_operator_time "
        "ON usage_records (operator_id, created_at DESC)"
    )

def downgrade():
    op.drop_index('idx_usage_operator_time', table_name='usage_records')
```

**迁移测试流程**:
```bash
# 1. 在测试数据库执行迁移
alembic upgrade head

# 2. 验证数据完整性
pytest tests/migration/test_001_rename_price.py

# 3. 测试回滚
alembic downgrade -1

# 4. 再次升级验证
alembic upgrade head

# 5. 生产环境部署前备份
pg_dump -Fc mydb > backup_before_migration.dump

# 6. 生产环境执行
alembic upgrade head

# 7. 如果失败立即回滚
alembic downgrade -1
```

**迁移测试用例**:
```python
# tests/migration/test_001_rename_price.py
import pytest
from alembic import command
from alembic.config import Config

@pytest.fixture
def alembic_config():
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    return config

def test_migration_001_upgrade(alembic_config, db_session):
    # 执行迁移
    command.upgrade(alembic_config, "001")

    # 验证新列存在
    result = db_session.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='applications' AND column_name='price_per_player'"
    )
    assert result.scalar() == 'price_per_player'

    # 验证数据正确性
    app = db_session.execute(
        "SELECT price_per_player FROM applications WHERE id=1"
    ).scalar()
    assert app == Decimal('10.00')

def test_migration_001_downgrade(alembic_config, db_session):
    # 执行回滚
    command.downgrade(alembic_config, "-1")

    # 验证新列已删除
    result = db_session.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='applications' AND column_name='price_per_player'"
    )
    assert result.scalar() is None
```

**关键要点**:
- 迁移脚本必须同时编写upgrade和downgrade
- 生产环境迁移前必须在测试环境完整测试
- 大表（>100万行）迁移使用分批处理（避免长时间锁表）
- 索引创建使用CONCURRENTLY（PostgreSQL特性）
- 每次迁移提交前Review SQL语句（检查DROP TABLE等危险操作）

---

## 8. 前端技术选型

### 决策

采用 **Vue 3 + TypeScript + Pinia + Element Plus + ECharts**

### 理由

- **学习曲线**: Vue更易上手（渐进式框架），适合中小团队快速开发
- **TypeScript支持**: Vue 3原生TypeScript重写，类型提示完善
- **状态管理**: Pinia是Vue 3官方推荐（替代Vuex），API更简洁
- **组件库**: Element Plus专为Vue 3设计，组件丰富（表格、表单、图表）
- **图表库**: ECharts功能强大（支持大数据量、多种图表类型），中文文档完善

### 备选方案

- **方案A: React + Redux + Ant Design + Recharts** - 拒绝原因：React学习曲线陡峭（Hooks、Context），Redux样板代码多
- **方案B: Vue 2 + Vuex + Element UI** - 拒绝原因：Vue 2即将停止维护（2023年底），应采用Vue 3
- **方案C: Svelte + Svelte Store + Carbon Components** - 拒绝原因：生态不成熟，招聘困难

### 实施建议

**技术栈组合**:
```json
// frontend/package.json
{
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.0",
    "pinia": "^2.1.0",
    "element-plus": "^2.5.0",
    "echarts": "^5.4.0",
    "axios": "^1.6.0",
    "dayjs": "^1.11.0"  // 日期处理（轻量级，替代moment.js）
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.0.0",
    "typescript": "^5.3.0",
    "vitest": "^1.0.0",  // 测试框架
    "unplugin-auto-import": "^0.17.0",  // 自动导入API
    "unplugin-vue-components": "^0.26.0"  // 自动导入组件
  }
}
```

**项目结构**:
```
frontend/src/
├── assets/          # 静态资源（图片、CSS）
├── components/      # 可复用组件
│   ├── charts/      # 图表组件（LineChart、BarChart等）
│   ├── forms/       # 表单组件（RechargeForm、AuthForm）
│   └── tables/      # 表格组件（UsageTable、TransactionTable）
├── views/           # 页面组件
│   ├── operator/    # 运营商端
│   │   ├── Dashboard.vue
│   │   ├── Recharge.vue
│   │   ├── UsageRecords.vue
│   │   └── Statistics.vue
│   ├── admin/       # 管理员端
│   │   ├── OperatorManagement.vue
│   │   ├── AppAuthorization.vue
│   │   └── PriceConfig.vue
│   └── finance/     # 财务端
│       ├── FinanceDashboard.vue
│       ├── RefundReview.vue
│       └── Reports.vue
├── stores/          # Pinia状态管理
│   ├── user.ts      # 用户状态（当前登录用户）
│   ├── operator.ts  # 运营商数据
│   └── statistics.ts # 统计数据
├── api/             # API调用封装
│   ├── client.ts    # Axios实例配置
│   ├── operator.ts  # 运营商API
│   ├── admin.ts     # 管理员API
│   └── finance.ts   # 财务API
├── router/          # 路由配置
│   └── index.ts
├── utils/           # 工具函数
│   ├── formatter.ts # 格式化（金额、时间）
│   └── validator.ts # 表单验证
└── main.ts
```

**Pinia状态管理示例**:
```typescript
// frontend/src/stores/operator.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getOperatorInfo } from '@/api/operator'

export const useOperatorStore = defineStore('operator', () => {
  // 状态
  const operatorInfo = ref<OperatorInfo | null>(null)
  const balance = ref<number>(0)

  // 计算属性
  const isLowBalance = computed(() => balance.value < 100)

  // 操作
  async function fetchOperatorInfo() {
    const data = await getOperatorInfo()
    operatorInfo.value = data
    balance.value = data.balance
  }

  function updateBalance(amount: number) {
    balance.value += amount
  }

  return {
    operatorInfo,
    balance,
    isLowBalance,
    fetchOperatorInfo,
    updateBalance
  }
})
```

**ECharts图表组件封装**:
```vue
<!-- frontend/src/components/charts/ConsumptionTrendChart.vue -->
<template>
  <div ref="chartRef" style="width: 100%; height: 400px;"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'

interface Props {
  data: Array<{ date: string; amount: number }>
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

const chartRef = ref<HTMLDivElement>()
let chartInstance: echarts.ECharts | null = null

onMounted(() => {
  if (chartRef.value) {
    chartInstance = echarts.init(chartRef.value)
    updateChart()
  }
})

watch(() => props.data, updateChart)
watch(() => props.loading, (loading) => {
  if (chartInstance) {
    loading ? chartInstance.showLoading() : chartInstance.hideLoading()
  }
})

function updateChart() {
  if (!chartInstance) return

  const option: echarts.EChartsOption = {
    title: { text: '消费趋势' },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: props.data.map(d => d.date)
    },
    yAxis: {
      type: 'value',
      name: '金额（元）'
    },
    series: [{
      name: '消费金额',
      type: 'line',
      data: props.data.map(d => d.amount),
      smooth: true,
      areaStyle: {}  // 面积图
    }]
  }

  chartInstance.setOption(option)
}
</script>
```

**Element Plus表格组件使用**:
```vue
<!-- frontend/src/views/operator/UsageRecords.vue -->
<template>
  <el-card>
    <template #header>
      <span>使用记录</span>
    </template>

    <el-table :data="usageRecords" v-loading="loading">
      <el-table-column prop="created_at" label="游戏时间" width="180">
        <template #default="{ row }">
          {{ formatDateTime(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column prop="site_name" label="运营点" />
      <el-table-column prop="app_name" label="应用" />
      <el-table-column prop="player_count" label="玩家数" width="100" />
      <el-table-column prop="price_per_player" label="单价" width="100">
        <template #default="{ row }">
          ¥{{ row.price_per_player.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column prop="total_cost" label="总费用" width="120">
        <template #default="{ row }">
          <el-tag type="danger">¥{{ row.total_cost.toFixed(2) }}</el-tag>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="currentPage"
      :page-size="20"
      :total="total"
      @current-change="fetchRecords"
    />
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getUsageRecords } from '@/api/operator'
import { formatDateTime } from '@/utils/formatter'

const usageRecords = ref([])
const loading = ref(false)
const currentPage = ref(1)
const total = ref(0)

async function fetchRecords() {
  loading.value = true
  try {
    const { data, total: totalCount } = await getUsageRecords({
      page: currentPage.value,
      page_size: 20
    })
    usageRecords.value = data
    total.value = totalCount
  } finally {
    loading.value = false
  }
}

onMounted(fetchRecords)
</script>
```

**关键要点**:
- 使用Vite构建工具（比Webpack快10-100倍）
- TypeScript严格模式（`strict: true`），减少运行时错误
- 组件懒加载（`const Dashboard = () => import('./Dashboard.vue')`）
- ECharts按需引入（减少打包体积）
- 使用unplugin-auto-import自动导入Vue API（无需手动import ref、computed等）

---

## 9. SDK设计模式

### 决策

采用 **统一接口设计 + 自动重试（指数退避）+ 配置文件管理 + 完整错误处理**

### 理由

- **功能满足度**: 支持Python、Node.js、C#三种语言，覆盖主流头显Server开发环境
- **易用性**: 统一API设计（`client.authorize_game()`），降低学习成本
- **可靠性**: 自动重试机制处理网络抖动，指数退避避免雪崩
- **安全性**: API Secret通过配置文件管理（不硬编码），支持环境变量注入

### 备选方案

- **方案A: 仅提供HTTP接口文档** - 拒绝原因：客户需手动实现签名算法，易出错
- **方案B: 仅提供Python SDK** - 拒绝原因：C#是Unity主流语言（MR游戏开发），必须支持
- **方案C: gRPC接口 + gRPC SDK** - 拒绝原因：HTTP更通用，gRPC调试困难

### 实施建议

**Python SDK实现**:
```python
# sdk/python/mr_auth_sdk/client.py
import httpx
import time
import hmac
import hashlib
import json
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential

class MRAuthClient:
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://api.example.com",
        timeout: int = 30
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    def _generate_signature(
        self,
        method: str,
        path: str,
        timestamp: int,
        nonce: str,
        body: str = ""
    ) -> str:
        """生成HMAC-SHA256签名"""
        message = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body}"
        return hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    @retry(
        stop=stop_after_attempt(3),  # 最多重试3次
        wait=wait_exponential(multiplier=1, min=1, max=10)  # 指数退避：1s, 2s, 4s
    )
    async def authorize_game(
        self,
        app_id: int,
        player_count: int,
        session_id: str,
        site_id: Optional[int] = None
    ) -> dict:
        """
        请求游戏授权

        Args:
            app_id: 应用ID
            player_count: 玩家数量
            session_id: 会话ID（幂等性保证）
            site_id: 运营点ID（可选）

        Returns:
            {
                "authorization_token": "uuid",
                "total_cost": 50.0,
                "remaining_balance": 450.0
            }

        Raises:
            InsufficientBalanceError: 余额不足
            UnauthorizedAppError: 应用未授权
            AuthenticationError: 认证失败
        """
        path = "/v1/authorize"
        method = "POST"
        timestamp = int(time.time())
        nonce = str(uuid.uuid4())

        body_dict = {
            "app_id": app_id,
            "player_count": player_count,
            "session_id": session_id
        }
        if site_id:
            body_dict["site_id"] = site_id

        body = json.dumps(body_dict)
        signature = self._generate_signature(method, path, timestamp, nonce, body)

        response = await self.client.post(
            f"{self.base_url}{path}",
            headers={
                "X-API-Key": self.api_key,
                "X-Signature": signature,
                "X-Timestamp": str(timestamp),
                "X-Nonce": nonce,
                "Content-Type": "application/json"
            },
            content=body
        )

        # 错误处理
        if response.status_code == 402:
            raise InsufficientBalanceError(response.json()["detail"])
        elif response.status_code == 403:
            raise UnauthorizedAppError(response.json()["detail"])
        elif response.status_code == 401:
            raise AuthenticationError(response.json()["detail"])

        response.raise_for_status()
        return response.json()

    async def get_balance(self) -> float:
        """查询余额"""
        # 类似实现...
        pass

    async def close(self):
        """关闭HTTP客户端"""
        await self.client.aclose()

# 异常定义
class MRAuthError(Exception):
    """SDK基础异常"""
    pass

class InsufficientBalanceError(MRAuthError):
    """余额不足"""
    pass

class UnauthorizedAppError(MRAuthError):
    """应用未授权"""
    pass

class AuthenticationError(MRAuthError):
    """认证失败"""
    pass
```

**配置文件管理**:
```python
# sdk/python/mr_auth_sdk/config.py
import os
from typing import Optional
import yaml

class Config:
    @staticmethod
    def from_file(path: str = "mr_auth_config.yaml") -> dict:
        """从YAML文件加载配置"""
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    @staticmethod
    def from_env() -> dict:
        """从环境变量加载配置"""
        return {
            "api_key": os.getenv("MR_AUTH_API_KEY"),
            "api_secret": os.getenv("MR_AUTH_API_SECRET"),
            "base_url": os.getenv("MR_AUTH_BASE_URL", "https://api.example.com")
        }

# 使用示例
# 方式1: 配置文件
config = Config.from_file("mr_auth_config.yaml")
client = MRAuthClient(**config)

# 方式2: 环境变量
config = Config.from_env()
client = MRAuthClient(**config)

# mr_auth_config.yaml示例:
# api_key: "your_api_key_here"
# api_secret: "your_api_secret_here"
# base_url: "https://api.example.com"
```

**Node.js SDK实现**:
```typescript
// sdk/nodejs/src/client.ts
import axios, { AxiosInstance } from 'axios'
import crypto from 'crypto'
import axiosRetry from 'axios-retry'

export class MRAuthClient {
  private apiKey: string
  private apiSecret: string
  private client: AxiosInstance

  constructor(
    apiKey: string,
    apiSecret: string,
    baseURL: string = 'https://api.example.com',
    timeout: number = 30000
  ) {
    this.apiKey = apiKey
    this.apiSecret = apiSecret

    this.client = axios.create({ baseURL, timeout })

    // 配置自动重试（指数退避）
    axiosRetry(this.client, {
      retries: 3,
      retryDelay: axiosRetry.exponentialDelay,
      retryCondition: (error) => {
        return axiosRetry.isNetworkOrIdempotentRequestError(error) ||
               error.response?.status === 429  // 限流重试
      }
    })
  }

  private generateSignature(
    method: string,
    path: string,
    timestamp: number,
    nonce: string,
    body: string = ''
  ): string {
    const message = `${method}\n${path}\n${timestamp}\n${nonce}\n${body}`
    return crypto
      .createHmac('sha256', this.apiSecret)
      .update(message)
      .digest('hex')
  }

  async authorizeGame(params: {
    appId: number
    playerCount: number
    sessionId: string
    siteId?: number
  }): Promise<{
    authorizationToken: string
    totalCost: number
    remainingBalance: number
  }> {
    const path = '/v1/authorize'
    const method = 'POST'
    const timestamp = Math.floor(Date.now() / 1000)
    const nonce = crypto.randomUUID()

    const body = JSON.stringify({
      app_id: params.appId,
      player_count: params.playerCount,
      session_id: params.sessionId,
      ...(params.siteId && { site_id: params.siteId })
    })

    const signature = this.generateSignature(method, path, timestamp, nonce, body)

    const response = await this.client.post(path, body, {
      headers: {
        'X-API-Key': this.apiKey,
        'X-Signature': signature,
        'X-Timestamp': timestamp.toString(),
        'X-Nonce': nonce,
        'Content-Type': 'application/json'
      }
    })

    return response.data
  }
}
```

**C# SDK实现（Unity兼容）**:
```csharp
// sdk/csharp/MRAuthSDK/Client.cs
using System;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json;
using Polly;

namespace MRAuthSDK
{
    public class MRAuthClient
    {
        private readonly string _apiKey;
        private readonly string _apiSecret;
        private readonly HttpClient _httpClient;
        private readonly IAsyncPolicy<HttpResponseMessage> _retryPolicy;

        public MRAuthClient(string apiKey, string apiSecret, string baseUrl = "https://api.example.com")
        {
            _apiKey = apiKey;
            _apiSecret = apiSecret;
            _httpClient = new HttpClient { BaseAddress = new Uri(baseUrl) };

            // Polly重试策略（指数退避）
            _retryPolicy = Policy
                .HandleResult<HttpResponseMessage>(r => !r.IsSuccessStatusCode)
                .WaitAndRetryAsync(3, retryAttempt =>
                    TimeSpan.FromSeconds(Math.Pow(2, retryAttempt))
                );
        }

        private string GenerateSignature(string method, string path, long timestamp, string nonce, string body = "")
        {
            var message = $"{method}\n{path}\n{timestamp}\n{nonce}\n{body}";
            using (var hmac = new HMACSHA256(Encoding.UTF8.GetBytes(_apiSecret)))
            {
                var hash = hmac.ComputeHash(Encoding.UTF8.GetBytes(message));
                return BitConverter.ToString(hash).Replace("-", "").ToLower();
            }
        }

        public async Task<AuthorizationResult> AuthorizeGame(
            int appId,
            int playerCount,
            string sessionId,
            int? siteId = null
        )
        {
            var path = "/v1/authorize";
            var method = "POST";
            var timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
            var nonce = Guid.NewGuid().ToString();

            var bodyObject = new
            {
                app_id = appId,
                player_count = playerCount,
                session_id = sessionId,
                site_id = siteId
            };
            var body = JsonConvert.SerializeObject(bodyObject);

            var signature = GenerateSignature(method, path, timestamp, nonce, body);

            var request = new HttpRequestMessage(HttpMethod.Post, path)
            {
                Content = new StringContent(body, Encoding.UTF8, "application/json")
            };
            request.Headers.Add("X-API-Key", _apiKey);
            request.Headers.Add("X-Signature", signature);
            request.Headers.Add("X-Timestamp", timestamp.ToString());
            request.Headers.Add("X-Nonce", nonce);

            var response = await _retryPolicy.ExecuteAsync(() => _httpClient.SendAsync(request));
            response.EnsureSuccessStatusCode();

            var json = await response.Content.ReadAsStringAsync();
            return JsonConvert.DeserializeObject<AuthorizationResult>(json);
        }
    }

    public class AuthorizationResult
    {
        public string AuthorizationToken { get; set; }
        public decimal TotalCost { get; set; }
        public decimal RemainingBalance { get; set; }
    }
}
```

**示例代码和文档**:
```python
# sdk/python/examples/basic_usage.py
"""基础使用示例"""
import asyncio
from mr_auth_sdk import MRAuthClient, Config

async def main():
    # 从配置文件加载
    config = Config.from_file("mr_auth_config.yaml")
    client = MRAuthClient(**config)

    try:
        # 请求游戏授权
        result = await client.authorize_game(
            app_id=10,
            player_count=5,
            session_id="session_12345"
        )

        print(f"授权成功！")
        print(f"授权Token: {result['authorization_token']}")
        print(f"本次费用: {result['total_cost']}元")
        print(f"剩余余额: {result['remaining_balance']}元")

    except InsufficientBalanceError as e:
        print(f"余额不足: {e}")
    except UnauthorizedAppError as e:
        print(f"应用未授权: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

**关键要点**:
- SDK版本号遵循语义化版本（SemVer）：主版本.次版本.修订号
- 提供类型提示（Python typing、TypeScript types、C# generics）
- 错误类型细化（余额不足、认证失败、网络错误等）
- 文档包含完整示例代码和常见问题解答（FAQ）
- 发布到包管理器（PyPI、npm、NuGet）

---

## 10. 测试策略

### 决策

采用 **契约测试（Schemathesis）+ 集成测试（pytest-asyncio）+ 工厂模式（factory_boy）+ Mock支付平台（sandbox）+ 性能测试（Locust）**

### 理由

- **功能满足度**: 契约测试保证API实现符合OpenAPI规范，集成测试覆盖完整业务流程
- **效率**: 工厂模式快速生成测试数据，Mock支付平台避免真实扣费
- **性能验证**: Locust模拟高并发场景，验证系统吞吐量和响应时间
- **CI/CD集成**: pytest生成JUnit格式报告，便于集成Jenkins/GitLab CI

### 备选方案

- **方案A: 仅单元测试** - 拒绝原因：无法验证模块间集成问题（如事务边界、锁冲突）
- **方案B: Postman + Newman（CLI）** - 拒绝原因：无法参数化复杂场景，维护成本高
- **方案C: k6性能测试** - 拒绝原因：JavaScript生态，与Python项目集成差，Locust更易编写Python脚本

### 实施建议

**契约测试（OpenAPI验证）**:
```python
# tests/contract/test_openapi_compliance.py
import pytest
import schemathesis
from backend.src.main import app

# 加载OpenAPI规范
schema = schemathesis.from_asgi("/v1/openapi.json", app=app)

@schema.parametrize()
def test_api_contract(case):
    """自动生成测试用例验证所有API端点"""
    response = case.call_asgi()
    case.validate_response(response)

# 自定义验证
@schema.parametrize(endpoint="/v1/authorize")
def test_authorize_endpoint(case):
    """针对授权端点的额外验证"""
    response = case.call_asgi()

    # 验证响应格式
    case.validate_response(response)

    # 验证业务逻辑
    if response.status_code == 200:
        data = response.json()
        assert "authorization_token" in data
        assert "total_cost" in data
        assert data["total_cost"] > 0
```

**集成测试（完整业务流程）**:
```python
# tests/integration/test_authorization_flow.py
import pytest
from httpx import AsyncClient
from backend.src.main import app
from backend.src.db.session import AsyncSessionLocal

@pytest.fixture
async def test_client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()  # 测试后回滚

@pytest.mark.asyncio
async def test_full_authorization_flow(test_client, db_session):
    """测试完整授权流程：注册 → 充值 → 授权 → 验证余额"""

    # 1. 创建运营商账户
    register_response = await test_client.post("/v1/operators", json={
        "username": "test_operator",
        "name": "测试运营商",
        "phone": "13800138000",
        "email": "test@example.com"
    })
    assert register_response.status_code == 201
    operator_data = register_response.json()
    api_key = operator_data["api_key"]
    api_secret = operator_data["api_secret"]

    # 2. 充值100元（Mock支付回调）
    recharge_response = await test_client.post("/v1/recharge", json={
        "amount": 100.0,
        "channel": "wechat"
    }, headers=_generate_auth_headers(api_key, api_secret, ...))
    assert recharge_response.status_code == 200
    order_no = recharge_response.json()["order_no"]

    # Mock支付成功回调
    await _mock_payment_callback(test_client, order_no, success=True)

    # 3. 请求游戏授权（5人游戏，单价10元）
    auth_response = await test_client.post("/v1/authorize", json={
        "app_id": 1,
        "player_count": 5,
        "session_id": "test_session_123"
    }, headers=_generate_auth_headers(api_key, api_secret, ...))

    assert auth_response.status_code == 200
    auth_data = auth_response.json()
    assert auth_data["total_cost"] == 50.0
    assert auth_data["remaining_balance"] == 50.0  # 100 - 50

    # 4. 重复请求（幂等性测试）
    auth_response2 = await test_client.post("/v1/authorize", json={
        "app_id": 1,
        "player_count": 5,
        "session_id": "test_session_123"  # 相同session_id
    }, headers=_generate_auth_headers(api_key, api_secret, ...))

    assert auth_response2.status_code == 200
    auth_data2 = auth_response2.json()
    assert auth_data2["authorization_token"] == auth_data["authorization_token"]
    assert auth_data2["remaining_balance"] == 50.0  # 未重复扣费

    # 5. 余额不足测试
    auth_response3 = await test_client.post("/v1/authorize", json={
        "app_id": 1,
        "player_count": 8,  # 需要80元，余额不足
        "session_id": "test_session_456"
    }, headers=_generate_auth_headers(api_key, api_secret, ...))

    assert auth_response3.status_code == 402  # Payment Required
    assert "余额不足" in auth_response3.json()["detail"]
```

**工厂模式（测试数据生成）**:
```python
# tests/factories.py
import factory
from factory import Faker, SubFactory
from backend.src.models import Operator, Application, UsageRecord

class OperatorFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Operator
        sqlalchemy_session = None  # 运行时设置

    username = Faker('user_name')
    name = Faker('company')
    phone = Faker('phone_number', locale='zh_CN')
    email = Faker('email')
    api_key = Faker('sha256')
    api_secret = Faker('sha256')
    balance = Faker('pydecimal', left_digits=5, right_digits=2, positive=True)
    customer_category = "normal"
    is_deleted = False

class ApplicationFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Application
        sqlalchemy_session = None

    name = Faker('word')
    price_per_player = Faker('pydecimal', left_digits=2, right_digits=2, positive=True)
    min_players = 2
    max_players = 8

class UsageRecordFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = UsageRecord
        sqlalchemy_session = None

    operator = SubFactory(OperatorFactory)
    application = SubFactory(ApplicationFactory)
    player_count = Faker('pyint', min_value=2, max_value=8)
    price_per_player = Faker('pydecimal', left_digits=2, right_digits=2)
    total_cost = factory.LazyAttribute(lambda o: o.player_count * o.price_per_player)
    session_id = Faker('uuid4')

# 使用示例
@pytest.fixture
def setup_test_data(db_session):
    OperatorFactory._meta.sqlalchemy_session = db_session

    # 批量创建测试数据
    operators = OperatorFactory.create_batch(10)
    apps = ApplicationFactory.create_batch(5)
    records = UsageRecordFactory.create_batch(100)

    db_session.commit()
    return operators, apps, records
```

**Mock支付平台（沙箱环境）**:
```python
# tests/mocks/payment.py
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_wechat_pay():
    """Mock微信支付SDK"""
    with patch('backend.src.services.payment.WeChatPay') as mock:
        # Mock下单成功
        mock.return_value.pay = AsyncMock(return_value=(
            200,
            {"code_url": "weixin://wxpay/bizpayurl?pr=test123"}
        ))

        # Mock查询订单
        mock.return_value.query = AsyncMock(return_value=(
            200,
            {
                "trade_state": "SUCCESS",
                "out_trade_no": "RC1234567890",
                "transaction_id": "WX1234567890"
            }
        ))

        yield mock

@pytest.mark.asyncio
async def test_recharge_with_mock_payment(test_client, mock_wechat_pay):
    """使用Mock支付测试充值流程"""
    response = await test_client.post("/v1/recharge", json={
        "amount": 100.0,
        "channel": "wechat"
    })

    assert response.status_code == 200
    assert "code_url" in response.json()

    # 验证SDK被正确调用
    mock_wechat_pay.return_value.pay.assert_called_once()
```

**性能测试（Locust）**:
```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between
import time
import hmac
import hashlib
import uuid

class MRAuthUser(HttpUser):
    wait_time = between(1, 3)  # 请求间隔1-3秒

    def on_start(self):
        """初始化（登录获取API Key）"""
        self.api_key = "test_api_key"
        self.api_secret = "test_api_secret"

    def _generate_signature(self, method, path, timestamp, nonce, body=""):
        message = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body}"
        return hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    @task(3)  # 权重3（更频繁）
    def authorize_game(self):
        """授权游戏（主要业务场景）"""
        path = "/v1/authorize"
        method = "POST"
        timestamp = int(time.time())
        nonce = str(uuid.uuid4())

        body = '{"app_id": 1, "player_count": 5, "session_id": "' + str(uuid.uuid4()) + '"}'
        signature = self._generate_signature(method, path, timestamp, nonce, body)

        self.client.post(
            path,
            data=body,
            headers={
                "X-API-Key": self.api_key,
                "X-Signature": signature,
                "X-Timestamp": str(timestamp),
                "X-Nonce": nonce,
                "Content-Type": "application/json"
            },
            name="授权游戏"
        )

    @task(1)  # 权重1（较少）
    def get_balance(self):
        """查询余额"""
        path = "/v1/operators/me/balance"
        method = "GET"
        timestamp = int(time.time())
        nonce = str(uuid.uuid4())
        signature = self._generate_signature(method, path, timestamp, nonce)

        self.client.get(
            path,
            headers={
                "X-API-Key": self.api_key,
                "X-Signature": signature,
                "X-Timestamp": str(timestamp),
                "X-Nonce": nonce
            },
            name="查询余额"
        )

# 运行性能测试
# locust -f tests/performance/locustfile.py --host=http://localhost:8000
# 目标：1000并发用户，RPS≥1000，P95<100ms
```

**CI/CD集成（GitHub Actions示例）**:
```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov

      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:test@localhost/test
          REDIS_URL: redis://localhost:6379/0
        run: |
          pytest tests/ \
            --cov=backend/src \
            --cov-report=xml \
            --cov-report=html \
            --junit-xml=test-results.xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

**关键要点**:
- 测试覆盖率目标：单元测试≥80%，核心业务逻辑100%
- 集成测试使用独立测试数据库（避免污染生产数据）
- 性能测试在类生产环境执行（相同配置的服务器）
- 契约测试在每次API变更后执行（防止破坏兼容性）
- 定期执行性能回归测试（每周/每月）

---

## 总结与实施优先级

### 核心技术决策汇总

| 领域 | 技术选型 | 关键优势 |
|------|---------|---------|
| 后端框架 | FastAPI + SQLAlchemy 2.0 Async | 高性能异步处理，原生OpenAPI支持 |
| 数据库 | PostgreSQL 14 + asyncpg | 行级锁、事务隔离、高并发支持 |
| 缓存/锁 | Redis 7 + Lua脚本 | 分布式锁、滑动窗口限流、高性能缓存 |
| 认证 | API Key + HMAC-SHA256 | 无状态认证、防篡改、防重放 |
| 支付 | 官方SDK + 异步回调 + 主动查询 | 安全可靠、自动重试、兜底机制 |
| 可观测性 | structlog + OpenTelemetry + Prometheus | 结构化日志、分布式追踪、完整指标 |
| 数据库迁移 | Alembic + 先增后删策略 | 零停机迁移、版本控制、安全回滚 |
| 前端 | Vue 3 + TypeScript + Element Plus + ECharts | 易学易用、组件丰富、强大图表 |
| SDK | 多语言统一接口 + 自动重试 | 易集成、高可靠、完善文档 |
| 测试 | 契约测试 + 集成测试 + Locust性能测试 | 完整覆盖、自动化CI/CD |

### 实施优先级建议

**Phase 0（当前）**: 完成技术调研 ✅

**Phase 1（第1-2周）**:
1. 搭建基础架构（FastAPI + PostgreSQL + Redis）
2. 实现认证中间件（HMAC签名验证）
3. 生成OpenAPI契约和数据库模型

**Phase 2（第3-4周）**:
1. 实现核心业务逻辑（授权、计费、余额管理）
2. 集成支付平台（微信支付/支付宝）
3. 配置可观测性（日志、追踪、指标）

**Phase 3（第5-6周）**:
1. 开发前端管理界面（运营商端/管理员端）
2. 开发SDK（Python/Node.js/C#）
3. 编写完整测试套件

**Phase 4（第7-8周）**:
1. 性能优化（缓存策略、数据库索引）
2. 压力测试和性能调优
3. 安全审计和渗透测试

**Phase 5（第9-10周）**:
1. 编写完整文档（API文档、SDK文档、运维手册）
2. 生产环境部署（Docker + Kubernetes）
3. 灰度发布和监控告警配置

### 关键风险与缓解措施

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 支付回调丢失 | 充值成功但余额未更新 | 5分钟超时主动查询支付平台 |
| 并发扣费冲突 | 重复扣费或余额不一致 | 行级锁 + Redis分布式锁 + 幂等性设计 |
| API Key泄露 | 恶意授权导致余额耗尽 | 频率限制 + 异常检测 + 快速轮换机制 |
| 数据库迁移失败 | 服务中断 | 测试环境完整验证 + 生产备份 + 自动回滚脚本 |
| 第三方依赖故障 | 支付/认证服务不可用 | 降级方案（人工审核）+ 熔断机制 |

---

**文档版本**: 1.0
**最后更新**: 2025-10-10
**维护者**: 技术团队
**审核状态**: 待审核

所有技术决策基于2024-2025年最新实践，符合项目宪章要求（TDD、零硬编码、API契约优先、可观测性）。建议在Phase 1实施前组织技术评审会议，确认所有选型符合团队能力和项目预算。
