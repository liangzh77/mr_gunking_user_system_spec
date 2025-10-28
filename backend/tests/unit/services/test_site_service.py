"""单元测试：SiteService (T100)

测试OperatorService中运营点管理相关的方法:
1. create_site - 创建运营点
2. get_sites - 获取运营点列表
3. update_site - 更新运营点信息
4. delete_site - 删除运营点(软删除)

测试策略:
- 使用真实数据库会话(test_db fixture)
- 验证业务规则和数据完整性
- 测试权限控制和异常处理
- 验证软删除逻辑
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import HTTPException
from uuid import uuid4, UUID

from src.services.operator import OperatorService
from src.models.operator import OperatorAccount
from src.models.admin import AdminAccount
from src.models.site import OperationSite
from sqlalchemy import select


@pytest.fixture
async def admin_account(test_db):
    """创建管理员账户用于测试"""
    admin = AdminAccount(
        username="admin_site_test",
        password_hash="hashed_pw",
        full_name="Test Admin",
        email="admin@test.com",
        phone="13800138000",
        role="admin",
        is_active=True
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)
    return admin


@pytest.fixture
async def operator_with_sites(test_db, admin_account):
    """创建包含运营点的运营商测试数据"""
    from src.core.utils.password import hash_password

    # 创建运营商
    operator = OperatorAccount(
        username="site_test_operator",
        full_name="Site Test Operator",
        email="operator@test.com",
        phone="13900000001",
        password_hash=hash_password("password123"),
        api_key="site_test_api_key_" + "a" * 48,
        api_key_hash=hash_password("site_test_api_key_" + "a" * 48),
        balance=Decimal("1000.00"),
        customer_tier="trial",
        is_active=True,
        is_locked=False
    )
    test_db.add(operator)
    await test_db.commit()
    await test_db.refresh(operator)

    # 创建2个运营点
    site1 = OperationSite(
        operator_id=operator.id,
        name="北京朝阳门店",
        address="北京市朝阳区建国路88号"
    )
    site2 = OperationSite(
        operator_id=operator.id,
        name="上海静安店",
        address="上海市静安区南京西路123号"
    )
    test_db.add_all([site1, site2])
    await test_db.commit()
    await test_db.refresh(site1)
    await test_db.refresh(site2)

    # 创建另一个运营商(用于测试权限隔离)
    other_operator = OperatorAccount(
        username="other_operator",
        full_name="Other Operator",
        email="other@test.com",
        phone="13900000002",
        password_hash=hash_password("password123"),
        api_key="other_api_key_" + "b" * 48,
        api_key_hash=hash_password("other_api_key_" + "b" * 48),
        balance=Decimal("500.00"),
        customer_tier="trial",
        is_active=True,
        is_locked=False
    )
    test_db.add(other_operator)
    await test_db.commit()
    await test_db.refresh(other_operator)

    # 为other_operator创建一个运营点
    other_site = OperationSite(
        operator_id=other_operator.id,
        name="广州天河店",
        address="广州市天河区体育西路10号"
    )
    test_db.add(other_site)
    await test_db.commit()
    await test_db.refresh(other_site)

    return {
        "admin": admin_account,
        "operator": operator,
        "site1": site1,
        "site2": site2,
        "other_operator": other_operator,
        "other_site": other_site
    }


class TestCreateSite:
    """测试create_site方法"""

    @pytest.mark.asyncio
    async def test_create_site_success(self, test_db, operator_with_sites):
        """测试成功创建运营点"""
        service = OperatorService(test_db)
        operator = operator_with_sites["operator"]

        site = await service.create_site(
            operator_id=operator.id,
            name="深圳福田店",
            address="深圳市福田区中心四路1号",
            description="福田CBD核心商圈"
        )

        # 验证返回数据
        assert site.operator_id == operator.id
        assert site.name == "深圳福田店"
        assert site.address == "深圳市福田区中心四路1号"
        assert site.deleted_at is None
        assert site.created_at is not None

        # 验证数据库记录
        stmt = select(OperationSite).where(
            OperationSite.id == site.id
        )
        db_result = await test_db.execute(stmt)
        db_site = db_result.scalar_one()
        assert db_site.name == "深圳福田店"

    @pytest.mark.asyncio
    async def test_create_site_without_description(self, test_db, operator_with_sites):
        """测试创建不带描述的运营点"""
        service = OperatorService(test_db)
        operator = operator_with_sites["operator"]

        site = await service.create_site(
            operator_id=operator.id,
            name="成都武侯店",
            address="成都市武侯区人民南路二段18号"
        )

        assert site.name == "成都武侯店"
        assert site.address == "成都市武侯区人民南路二段18号"

    @pytest.mark.asyncio
    async def test_create_site_non_existent_operator_raises_404(self, test_db):
        """测试为不存在的运营商创建运营点抛出HTTP 404"""
        service = OperatorService(test_db)

        non_existent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.create_site(
                operator_id=non_existent_id,
                name="测试门店",
                address="测试地址"
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error_code"] == "OPERATOR_NOT_FOUND"


class TestGetSites:
    """测试get_sites方法"""

    @pytest.mark.asyncio
    async def test_get_sites_returns_all_active_sites(self, test_db, operator_with_sites):
        """测试查询所有未删除的运营点"""
        service = OperatorService(test_db)
        operator = operator_with_sites["operator"]

        sites = await service.get_sites(operator.id)

        # 验证返回2个运营点
        assert len(sites) == 2
        site_names = {site.name for site in sites}
        assert "北京朝阳门店" in site_names
        assert "上海静安店" in site_names

    @pytest.mark.asyncio
    async def test_get_sites_excludes_deleted(self, test_db, operator_with_sites):
        """测试默认不返回已删除的运营点"""
        service = OperatorService(test_db)
        operator = operator_with_sites["operator"]
        site1 = operator_with_sites["site1"]

        # 软删除site1
        site1.deleted_at = datetime.now(timezone.utc)
        await test_db.commit()

        sites = await service.get_sites(operator.id, include_deleted=False)

        # 验证只返回1个运营点(site2)
        assert len(sites) == 1
        assert sites[0].name == "上海静安店"

    @pytest.mark.asyncio
    async def test_get_sites_includes_deleted_when_requested(self, test_db, operator_with_sites):
        """测试include_deleted=true时返回已删除的运营点"""
        service = OperatorService(test_db)
        operator = operator_with_sites["operator"]
        site1 = operator_with_sites["site1"]

        # 软删除site1
        site1.deleted_at = datetime.now(timezone.utc)
        await test_db.commit()

        sites = await service.get_sites(operator.id, include_deleted=True)

        # 验证返回2个运营点(包括已删除的)
        assert len(sites) == 2
        deleted_sites = [site for site in sites if site.deleted_at is not None]
        assert len(deleted_sites) == 1
        assert deleted_sites[0].name == "北京朝阳门店"

    @pytest.mark.asyncio
    async def test_get_sites_empty_list(self, test_db, operator_with_sites):
        """测试运营商没有运营点时返回空列表"""
        service = OperatorService(test_db)

        # 创建新的运营商(没有运营点)
        from src.core.utils.password import hash_password
        new_operator = OperatorAccount(
            username="new_operator_no_sites",
            full_name="No Sites Operator",
            email="nosites@test.com",
            phone="13900000099",
            password_hash=hash_password("password123"),
            api_key="new_api_key_" + "c" * 48,
            api_key_hash=hash_password("new_api_key_" + "c" * 48),
            balance=Decimal("0.00"),
            customer_tier="trial",
            is_active=True,
            is_locked=False
        )
        test_db.add(new_operator)
        await test_db.commit()
        await test_db.refresh(new_operator)

        sites = await service.get_sites(new_operator.id)

        assert sites == []

    @pytest.mark.asyncio
    async def test_get_sites_data_isolation(self, test_db, operator_with_sites):
        """测试数据隔离 - 只能看到自己的运营点"""
        service = OperatorService(test_db)
        operator = operator_with_sites["operator"]
        other_operator = operator_with_sites["other_operator"]

        # 查询operator的运营点
        operator_sites = await service.get_sites(operator.id)
        assert len(operator_sites) == 2

        # 查询other_operator的运营点
        other_sites = await service.get_sites(other_operator.id)
        assert len(other_sites) == 1
        assert other_sites[0].name == "广州天河店"

        # 验证互不干扰
        operator_site_ids = {site.id for site in operator_sites}
        other_site_ids = {site.id for site in other_sites}
        assert operator_site_ids.isdisjoint(other_site_ids)

    @pytest.mark.asyncio
    async def test_get_sites_non_existent_operator_raises_404(self, test_db):
        """测试查询不存在的运营商抛出HTTP 404"""
        service = OperatorService(test_db)

        non_existent_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.get_sites(non_existent_id)

        assert exc_info.value.status_code == 404


class TestUpdateSite:
    """测试update_site方法"""

    @pytest.mark.asyncio
    async def test_update_site_all_fields(self, test_db, operator_with_sites):
        """测试更新运营点的所有字段"""
        service = OperatorService(test_db)
        operator = operator_with_sites["operator"]
        site1 = operator_with_sites["site1"]

        updated_site = await service.update_site(
            operator_id=operator.id,
            site_id=site1.id,
            name="北京朝阳门店(旗舰店)",
            address="北京市朝阳区建国路99号",
            description="朝阳区旗舰店，面积300平米"
        )

        # 验证更新结果
        assert updated_site.id == site1.id
        assert updated_site.name == "北京朝阳门店(旗舰店)"
        assert updated_site.address == "北京市朝阳区建国路99号"

        # 验证数据库记录
        await test_db.refresh(site1)
        assert site1.name == "北京朝阳门店(旗舰店)"
        assert site1.address == "北京市朝阳区建国路99号"

    @pytest.mark.asyncio
    async def test_update_site_partial_fields(self, test_db, operator_with_sites):
        """测试部分字段更新"""
        service = OperatorService(test_db)
        operator = operator_with_sites["operator"]
        site2 = operator_with_sites["site2"]

        original_address = site2.address

        updated_site = await service.update_site(
            operator_id=operator.id,
            site_id=site2.id,
            name="上海静安店(VIP)"
            # 不更新address
        )

        # 验证只有name被更新
        assert updated_site.name == "上海静安店(VIP)"
        assert updated_site.address == original_address

    @pytest.mark.asyncio
    async def test_update_site_non_existent_raises_404(self, test_db, operator_with_sites):
        """测试更新不存在的运营点抛出HTTP 404"""
        service = OperatorService(test_db)
        operator = operator_with_sites["operator"]

        non_existent_site_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.update_site(
                operator_id=operator.id,
                site_id=non_existent_site_id,
                name="不存在的门店"
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error_code"] == "SITE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_update_site_permission_denied(self, test_db, operator_with_sites):
        """测试更新其他运营商的运营点抛出HTTP 404"""
        service = OperatorService(test_db)
        operator = operator_with_sites["operator"]
        other_site = operator_with_sites["other_site"]

        # 尝试更新other_operator的运营点
        with pytest.raises(HTTPException) as exc_info:
            await service.update_site(
                operator_id=operator.id,
                site_id=other_site.id,
                name="尝试更新其他运营商的门店"
            )

        assert exc_info.value.status_code == 404
        assert "无权限访问" in exc_info.value.detail["message"]

    @pytest.mark.asyncio
    async def test_update_deleted_site_raises_404(self, test_db, operator_with_sites):
        """测试更新已删除的运营点抛出HTTP 404"""
        service = OperatorService(test_db)
        operator = operator_with_sites["operator"]
        site1 = operator_with_sites["site1"]

        # 软删除site1
        site1.deleted_at = datetime.now(timezone.utc)
        await test_db.commit()

        # 尝试更新已删除的运营点
        with pytest.raises(HTTPException) as exc_info:
            await service.update_site(
                operator_id=operator.id,
                site_id=site1.id,
                name="尝试更新已删除的门店"
            )

        assert exc_info.value.status_code == 404


class TestDeleteSite:
    """测试delete_site方法"""

    @pytest.mark.asyncio
    async def test_delete_site_success(self, test_db, operator_with_sites):
        """测试成功删除运营点(软删除)"""
        service = OperatorService(test_db)
        operator = operator_with_sites["operator"]
        site1 = operator_with_sites["site1"]

        await service.delete_site(
            operator_id=operator.id,
            site_id=site1.id
        )

        # 验证软删除
        await test_db.refresh(site1)
        assert site1.deleted_at is not None

        # 验证普通查询不返回已删除的运营点
        sites = await service.get_sites(operator.id, include_deleted=False)
        assert len(sites) == 1
        assert sites[0].name == "上海静安店"

    @pytest.mark.asyncio
    async def test_delete_already_deleted_site_raises_404(self, test_db, operator_with_sites):
        """测试删除已删除的运营点抛出HTTP 404"""
        service = OperatorService(test_db)
        operator = operator_with_sites["operator"]
        site1 = operator_with_sites["site1"]

        # 第一次删除
        await service.delete_site(operator.id, site1.id)

        # 第二次删除
        with pytest.raises(HTTPException) as exc_info:
            await service.delete_site(operator.id, site1.id)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error_code"] == "SITE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_delete_non_existent_site_raises_404(self, test_db, operator_with_sites):
        """测试删除不存在的运营点抛出HTTP 404"""
        service = OperatorService(test_db)
        operator = operator_with_sites["operator"]

        non_existent_site_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.delete_site(operator.id, non_existent_site_id)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_site_permission_denied(self, test_db, operator_with_sites):
        """测试删除其他运营商的运营点抛出HTTP 404"""
        service = OperatorService(test_db)
        operator = operator_with_sites["operator"]
        other_site = operator_with_sites["other_site"]

        # 尝试删除other_operator的运营点
        with pytest.raises(HTTPException) as exc_info:
            await service.delete_site(operator.id, other_site.id)

        assert exc_info.value.status_code == 404

        # 验证other_site未被删除
        stmt = select(OperationSite).where(
            OperationSite.id == other_site.id
        )
        result = await test_db.execute(stmt)
        site = result.scalar_one()
        assert site.deleted_at is None

    @pytest.mark.asyncio
    async def test_delete_site_non_existent_operator_raises_404(self, test_db, operator_with_sites):
        """测试不存在的运营商删除运营点抛出HTTP 404"""
        service = OperatorService(test_db)
        site1 = operator_with_sites["site1"]

        non_existent_operator_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await service.delete_site(non_existent_operator_id, site1.id)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error_code"] == "OPERATOR_NOT_FOUND"
