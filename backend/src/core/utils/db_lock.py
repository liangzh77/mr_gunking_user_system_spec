"""
数据库并发控制工具

功能：
- 提供行级锁（SELECT FOR UPDATE）工具函数
- 支持并发余额扣费场景的原子性控制
- 防止丢失更新和重复扣费
"""
from typing import TypeVar, Optional, Type
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeMeta
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar('T', bound=DeclarativeMeta)


async def select_for_update(
    db: AsyncSession,
    model: Type[T],
    row_id: any,
    nowait: bool = False,
    skip_locked: bool = False
) -> Optional[T]:
    """
    使用行级锁查询单条记录（SELECT FOR UPDATE）

    用途：
    - 并发扣费场景：锁定运营商账户行，防止余额并发修改
    - 保证事务隔离：其他事务需等待当前事务提交或回滚

    Args:
        db: 数据库会话（必须在事务中）
        model: SQLAlchemy模型类
        row_id: 主键ID
        nowait: 立即返回（如果已被锁定则抛出异常）
        skip_locked: 跳过已锁定的行（返回None）

    Returns:
        锁定的模型实例，不存在时返回None

    Raises:
        OperationalError: nowait=True且行已被锁定时

    Example:
        async with db.begin():  # 必须在事务中
            operator = await select_for_update(
                db, OperatorAccount, operator_id
            )
            if operator.balance < cost:
                raise InsufficientBalanceError()
            operator.balance -= cost
            await db.flush()
            # 事务提交时自动释放锁
    """
    stmt = select(model).where(model.id == row_id)

    # 添加FOR UPDATE子句
    if nowait:
        stmt = stmt.with_for_update(nowait=True)
    elif skip_locked:
        stmt = stmt.with_for_update(skip_locked=True)
    else:
        stmt = stmt.with_for_update()

    result = await db.execute(stmt)
    instance = result.scalar_one_or_none()

    if instance:
        logger.debug(
            "row_locked",
            model=model.__name__,
            row_id=str(row_id),
            nowait=nowait,
            skip_locked=skip_locked
        )

    return instance


async def select_multiple_for_update(
    db: AsyncSession,
    model: Type[T],
    row_ids: list,
    nowait: bool = False
) -> list[T]:
    """
    批量锁定多行记录（按ID顺序锁定避免死锁）

    重要：必须按固定顺序获取锁，避免死锁
    示例：两个事务同时锁定账户A和B，必须都按照A→B的顺序

    Args:
        db: 数据库会话
        model: SQLAlchemy模型类
        row_ids: 主键ID列表（自动排序）
        nowait: 立即返回（如果任一行已被锁定则抛出异常）

    Returns:
        锁定的模型实例列表

    Example:
        # 转账场景：锁定两个账户
        async with db.begin():
            from_acc, to_acc = await select_multiple_for_update(
                db,
                OperatorAccount,
                [from_id, to_id]  # 自动按ID排序避免死锁
            )
            from_acc.balance -= amount
            to_acc.balance += amount
    """
    # 排序ID避免死锁
    sorted_ids = sorted(row_ids)

    stmt = (
        select(model)
        .where(model.id.in_(sorted_ids))
        .order_by(model.id)  # 确保顺序一致
    )

    if nowait:
        stmt = stmt.with_for_update(nowait=True)
    else:
        stmt = stmt.with_for_update()

    result = await db.execute(stmt)
    instances = result.scalars().all()

    logger.debug(
        "multiple_rows_locked",
        model=model.__name__,
        row_count=len(instances),
        expected_count=len(row_ids)
    )

    return instances


class OptimisticLockError(Exception):
    """乐观锁版本冲突异常"""
    pass


async def optimistic_update(
    db: AsyncSession,
    model: Type[T],
    row_id: any,
    expected_version: int,
    updates: dict
) -> T:
    """
    乐观锁更新（使用version字段）

    适用场景：
    - 低冲突场景（如用户信息编辑）
    - 不适合高并发扣费（应使用悲观锁）

    Args:
        db: 数据库会话
        model: SQLAlchemy模型类
        row_id: 主键ID
        expected_version: 期望的版本号
        updates: 更新字段字典

    Returns:
        更新后的模型实例

    Raises:
        OptimisticLockError: 版本号不匹配（已被其他事务修改）

    Example:
        try:
            operator = await optimistic_update(
                db,
                OperatorAccount,
                operator_id,
                expected_version=5,
                updates={"full_name": "新名称"}
            )
        except OptimisticLockError:
            # 提示用户刷新页面重新编辑
            raise HTTPException(409, "Data has been modified by another user")
    """
    # 查询当前版本
    stmt = select(model).where(
        model.id == row_id,
        model.version == expected_version  # 假设模型有version字段
    )
    result = await db.execute(stmt)
    instance = result.scalar_one_or_none()

    if not instance:
        logger.warning(
            "optimistic_lock_conflict",
            model=model.__name__,
            row_id=str(row_id),
            expected_version=expected_version
        )
        raise OptimisticLockError(
            f"Version conflict: expected {expected_version}, "
            f"but row has been modified"
        )

    # 更新字段并递增版本号
    for key, value in updates.items():
        setattr(instance, key, value)
    instance.version += 1

    await db.flush()

    logger.info(
        "optimistic_update_success",
        model=model.__name__,
        row_id=str(row_id),
        old_version=expected_version,
        new_version=instance.version
    )

    return instance


async def acquire_advisory_lock(
    db: AsyncSession,
    lock_id: int,
    timeout_seconds: int = 0
) -> bool:
    """
    获取PostgreSQL咨询锁（Advisory Lock）

    用途：
    - 跨表的业务级锁（如"确保同一会话ID只处理一次"）
    - 分布式锁的数据库实现（单实例部署推荐）

    Args:
        db: 数据库会话
        lock_id: 锁ID（整数，建议使用业务ID的哈希值）
        timeout_seconds: 超时时间（0表示不等待）

    Returns:
        成功获取锁返回True，否则False

    Example:
        # 防止重复扣费：使用session_id作为锁
        lock_id = hash(session_id) % (2**31)  # 转换为整数
        if await acquire_advisory_lock(db, lock_id):
            # 处理授权逻辑
            pass
        else:
            raise HTTPException(409, "Request is being processed")
    """
    if timeout_seconds > 0:
        # 尝试获取锁（阻塞直到超时）
        result = await db.execute(
            "SELECT pg_try_advisory_lock(:lock_id)",
            {"lock_id": lock_id}
        )
    else:
        # 立即返回（非阻塞）
        result = await db.execute(
            "SELECT pg_try_advisory_lock(:lock_id)",
            {"lock_id": lock_id}
        )

    acquired = result.scalar()

    if acquired:
        logger.debug("advisory_lock_acquired", lock_id=lock_id)
    else:
        logger.debug("advisory_lock_failed", lock_id=lock_id)

    return acquired


async def release_advisory_lock(db: AsyncSession, lock_id: int):
    """
    释放PostgreSQL咨询锁

    Args:
        db: 数据库会话
        lock_id: 锁ID
    """
    await db.execute(
        "SELECT pg_advisory_unlock(:lock_id)",
        {"lock_id": lock_id}
    )
    logger.debug("advisory_lock_released", lock_id=lock_id)
