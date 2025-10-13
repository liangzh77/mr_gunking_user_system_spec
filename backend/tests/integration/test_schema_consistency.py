"""
集成测试：验证数据库Schema与SQLAlchemy模型一致性 (T010a)

测试目标：
- 使用SQLAlchemy反射读取数据库Schema
- 对比模型定义的表名/字段/类型/索引/约束
- 不匹配时测试失败并输出差异报告

设计理念：
将SQLAlchemy模型作为单一真实来源(Single Source of Truth)，
验证数据库迁移脚本是否正确地反映了模型定义。
"""
import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import Base


# ========== 辅助函数 ==========

async def get_inspector(test_db: AsyncSession):
    """获取数据库Inspector的异步辅助函数"""
    engine = test_db.bind

    def _get_inspector(conn):
        return inspect(conn)

    async with engine.connect() as conn:
        return await conn.run_sync(_get_inspector)


# ========== 测试函数 ==========

@pytest.mark.asyncio
async def test_all_models_have_corresponding_tables(test_db: AsyncSession):
    """测试所有SQLAlchemy模型都有对应的数据库表"""
    # 获取所有模型定义的表名
    model_table_names = set()
    for mapper in Base.registry.mappers:
        table_name = mapper.class_.__tablename__
        model_table_names.add(table_name)

    # 获取数据库中的表名
    def get_table_names(conn):
        inspector = inspect(conn)
        return set(inspector.get_table_names())

    engine = test_db.bind
    async with engine.connect() as conn:
        db_table_names = await conn.run_sync(get_table_names)

    # 检查缺失的表
    missing_tables = model_table_names - db_table_names

    assert not missing_tables, (
        f"以下模型定义的表在数据库中不存在:\n"
        f"{', '.join(sorted(missing_tables))}\n"
        f"数据库现有表: {', '.join(sorted(db_table_names))}"
    )


@pytest.mark.asyncio
async def test_no_extra_tables_in_database(test_db: AsyncSession):
    """测试数据库中没有多余的表（除了alembic_version）"""
    # 获取所有模型定义的表名
    model_table_names = set()
    for mapper in Base.registry.mappers:
        table_name = mapper.class_.__tablename__
        model_table_names.add(table_name)

    # 获取数据库中的表名
    def get_table_names(conn):
        inspector = inspect(conn)
        return set(inspector.get_table_names())

    engine = test_db.bind
    async with engine.connect() as conn:
        db_table_names = await conn.run_sync(get_table_names)

    # 排除合法的元数据表
    db_table_names.discard('alembic_version')

    # 检查多余的表
    extra_tables = db_table_names - model_table_names

    assert not extra_tables, (
        f"数据库中存在未定义在模型中的表:\n"
        f"{', '.join(sorted(extra_tables))}"
    )


@pytest.mark.asyncio
async def test_table_column_consistency(test_db: AsyncSession):
    """测试每个表的字段与模型定义一致"""
    issues = []

    for mapper in Base.registry.mappers:
        model_class = mapper.class_
        table_name = model_class.__tablename__

        # 获取模型定义的列
        model_columns = {column.name for column in mapper.columns}

        # 获取数据库实际列
        def get_columns(conn):
            inspector = inspect(conn)
            if table_name not in inspector.get_table_names():
                return None
            return {col['name'] for col in inspector.get_columns(table_name)}

        engine = test_db.bind
        async with engine.connect() as conn:
            db_columns = await conn.run_sync(get_columns)

        if db_columns is None:
            issues.append(f"表 '{table_name}' 在数据库中不存在")
            continue

        # 检查模型中定义但数据库中缺失的列
        missing_columns = model_columns - db_columns
        if missing_columns:
            issues.append(
                f"表 '{table_name}': 模型中定义但数据库缺失的列: {', '.join(sorted(missing_columns))}"
            )

        # 检查数据库中存在但模型未定义的列
        extra_columns = db_columns - model_columns
        if extra_columns:
            issues.append(
                f"表 '{table_name}': 数据库中存在但模型未定义的列: {', '.join(sorted(extra_columns))}"
            )

    assert not issues, (
        f"发现以下Schema一致性问题:\n" + "\n".join(issues)
    )


@pytest.mark.asyncio
async def test_primary_key_consistency(test_db: AsyncSession):
    """测试主键约束与模型定义一致"""
    issues = []

    for mapper in Base.registry.mappers:
        model_class = mapper.class_
        table_name = model_class.__tablename__

        # 获取模型定义的主键列
        model_pk_columns = {col.name for col in mapper.primary_key}

        # 获取数据库实际主键
        def get_pk_constraint(conn):
            inspector = inspect(conn)
            if table_name not in inspector.get_table_names():
                return None
            pk_constraint = inspector.get_pk_constraint(table_name)
            return set(pk_constraint.get('constrained_columns', []))

        engine = test_db.bind
        async with engine.connect() as conn:
            db_pk_columns = await conn.run_sync(get_pk_constraint)

        if db_pk_columns is None:
            continue  # 表不存在的问题已在其他测试中检测

        if model_pk_columns != db_pk_columns:
            issues.append(
                f"表 '{table_name}': 主键不一致\n"
                f"  模型定义: {sorted(model_pk_columns)}\n"
                f"  数据库实际: {sorted(db_pk_columns)}"
            )

    assert not issues, (
        f"发现以下主键一致性问题:\n" + "\n".join(issues)
    )


@pytest.mark.asyncio
async def test_foreign_key_consistency(test_db: AsyncSession):
    """测试外键约束与模型定义一致"""
    issues = []

    for mapper in Base.registry.mappers:
        model_class = mapper.class_
        table_name = model_class.__tablename__

        # 获取模型定义的外键
        model_fks = {}
        for column in mapper.columns:
            if column.foreign_keys:
                for fk in column.foreign_keys:
                    model_fks[column.name] = {
                        'referred_table': fk.column.table.name,
                        'referred_column': fk.column.name
                    }

        # 获取数据库实际外键
        def get_foreign_keys(conn):
            inspector = inspect(conn)
            if table_name not in inspector.get_table_names():
                return None

            db_fks = {}
            for fk in inspector.get_foreign_keys(table_name):
                constrained_cols = fk['constrained_columns']
                referred_cols = fk['referred_columns']
                referred_table = fk['referred_table']

                for const_col, ref_col in zip(constrained_cols, referred_cols):
                    db_fks[const_col] = {
                        'referred_table': referred_table,
                        'referred_column': ref_col
                    }
            return db_fks

        engine = test_db.bind
        async with engine.connect() as conn:
            db_fks = await conn.run_sync(get_foreign_keys)

        if db_fks is None:
            continue

        # 检查外键一致性
        model_fk_columns = set(model_fks.keys())
        db_fk_columns = set(db_fks.keys())

        # 模型定义但数据库缺失的外键
        missing_fks = model_fk_columns - db_fk_columns
        if missing_fks:
            issues.append(
                f"表 '{table_name}': 模型中定义但数据库缺失的外键列: {', '.join(sorted(missing_fks))}"
            )

        # 数据库存在但模型未定义的外键
        extra_fks = db_fk_columns - model_fk_columns
        if extra_fks:
            issues.append(
                f"表 '{table_name}': 数据库中存在但模型未定义的外键列: {', '.join(sorted(extra_fks))}"
            )

        # 检查外键引用是否一致
        for fk_col in model_fk_columns & db_fk_columns:
            model_fk = model_fks[fk_col]
            db_fk = db_fks[fk_col]

            if model_fk['referred_table'] != db_fk['referred_table']:
                issues.append(
                    f"表 '{table_name}', 列 '{fk_col}': 外键引用表不一致\n"
                    f"  模型定义: {model_fk['referred_table']}\n"
                    f"  数据库实际: {db_fk['referred_table']}"
                )

    assert not issues, (
        f"发现以下外键一致性问题:\n" + "\n".join(issues)
    )


@pytest.mark.asyncio
async def test_nullable_consistency(test_db: AsyncSession):
    """测试字段可空性与模型定义一致"""
    issues = []

    for mapper in Base.registry.mappers:
        model_class = mapper.class_
        table_name = model_class.__tablename__

        # 获取模型定义的列可空性
        model_nullable = {}
        for column in mapper.columns:
            model_nullable[column.name] = column.nullable

        # 获取数据库列可空性
        def get_columns_nullable(conn):
            inspector = inspect(conn)
            if table_name not in inspector.get_table_names():
                return None

            db_nullable = {}
            for db_col in inspector.get_columns(table_name):
                db_nullable[db_col['name']] = db_col['nullable']
            return db_nullable

        engine = test_db.bind
        async with engine.connect() as conn:
            db_nullable = await conn.run_sync(get_columns_nullable)

        if db_nullable is None:
            continue

        # 比较可空性
        for col_name in model_nullable:
            if col_name in db_nullable:
                model_col_nullable = model_nullable[col_name]
                db_col_nullable = db_nullable[col_name]

                if model_col_nullable != db_col_nullable:
                    issues.append(
                        f"表 '{table_name}', 列 '{col_name}': 可空性不一致\n"
                        f"  模型定义: {'NULL' if model_col_nullable else 'NOT NULL'}\n"
                        f"  数据库实际: {'NULL' if db_col_nullable else 'NOT NULL'}"
                    )

    assert not issues, (
        f"发现以下字段可空性一致性问题:\n" + "\n".join(issues)
    )


@pytest.mark.asyncio
async def test_index_existence(test_db: AsyncSession):
    """测试关键索引是否存在（基础验证）"""
    # 定义期望的关键索引（基于实际迁移脚本生成的索引名称）
    expected_indexes = [
        # operator_accounts表的关键索引
        ('operator_accounts', 'uq_operator_username'),
        ('operator_accounts', 'uq_operator_api_key'),
        ('operator_accounts', 'idx_operator_email'),

        # operation_sites表的关键索引
        ('operation_sites', 'idx_site_operator'),

        # applications表的关键索引
        ('applications', 'uq_app_code'),

        # usage_records表的关键索引
        ('usage_records', 'uq_session_id'),
        ('usage_records', 'idx_usage_operator'),

        # transaction_records表的关键索引
        ('transaction_records', 'idx_trans_operator'),
    ]

    issues = []

    def get_index_names(conn, table_name):
        inspector = inspect(conn)
        if table_name not in inspector.get_table_names():
            return None

        indexes = inspector.get_indexes(table_name)
        unique_constraints = inspector.get_unique_constraints(table_name)

        index_names = {idx['name'] for idx in indexes if idx.get('name')}
        constraint_names = {uc['name'] for uc in unique_constraints if uc.get('name')}

        return index_names | constraint_names

    engine = test_db.bind

    for table_name, index_name in expected_indexes:
        async with engine.connect() as conn:
            all_index_names = await conn.run_sync(lambda c: get_index_names(c, table_name))

        if all_index_names is None:
            issues.append(f"表 '{table_name}' 不存在，无法检查索引 '{index_name}'")
            continue

        if index_name not in all_index_names:
            issues.append(
                f"表 '{table_name}': 缺少索引/唯一约束 '{index_name}'\n"
                f"  现有索引: {', '.join(sorted(all_index_names)) or '(无)'}"
            )

    assert not issues, (
        f"发现以下关键索引缺失问题:\n" + "\n".join(issues)
    )


@pytest.mark.asyncio
async def test_essential_tables_exist(test_db: AsyncSession):
    """测试核心业务表是否存在"""
    # 定义Phase 2-3必需的核心表
    essential_tables = [
        'operator_accounts',      # 运营商账户
        'operation_sites',        # 运营点
        'applications',           # 应用
        'operator_app_authorizations',  # 应用授权关系
        'usage_records',          # 使用记录
        'transaction_records',    # 交易记录
        'admin_accounts',         # 管理员账户
    ]

    def get_table_names(conn):
        inspector = inspect(conn)
        return set(inspector.get_table_names())

    engine = test_db.bind
    async with engine.connect() as conn:
        db_table_names = await conn.run_sync(get_table_names)

    missing_tables = [table for table in essential_tables if table not in db_table_names]

    assert not missing_tables, (
        f"缺少以下核心业务表:\n"
        f"{', '.join(missing_tables)}\n"
        f"这些表是MVP功能(Phase 2-3)所必需的"
    )
