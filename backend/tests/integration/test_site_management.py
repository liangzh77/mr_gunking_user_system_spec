"""
Integration Test: Site Management Flow (T085)

Test complete CRUD operations for operation sites:
1. Create site
2. Query site list
3. Update site
4. Delete site (soft delete)
5. Verify deleted site handling
"""
import pytest
from httpx import AsyncClient

from src.main import app


# ========== Helper Functions ==========

async def create_and_login_operator(client: AsyncClient, username: str) -> str:
    """Create operator and login, return JWT Token"""
    # Register
    await client.post(
        "/v1/auth/operators/register",
        json={
            "username": username,
            "password": "TestPass123",
            "name": "Test Company",
            "phone": "13800138000",
            "email": f"{username}@example.com"
        }
    )

    # Login
    response = await client.post(
        "/v1/auth/operators/login",
        json={
            "username": username,
            "password": "TestPass123"
        }
    )

    return response.json()["data"]["access_token"]


# ========== Integration Tests ==========

@pytest.mark.asyncio
async def test_site_management_full_flow(test_db):
    """Test complete site management flow: create -> query -> update -> delete"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "site_flow_user_1")

        # ========== Step 1: Create site ==========
        create_response = await client.post(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Beijing Chaoyang Store",
                "address": "No.88 Jianguo Road, Chaoyang District, Beijing",
                "description": "Chaoyang flagship store"
            }
        )

        assert create_response.status_code == 201
        created_site = create_response.json()["data"]
        site_id = created_site["site_id"]
        assert created_site["name"] == "Beijing Chaoyang Store"
        assert created_site["address"] == "No.88 Jianguo Road, Chaoyang District, Beijing"
        assert created_site["is_deleted"] is False

        # ========== Step 2: Query site list, verify creation ==========
        list_response = await client.get(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert list_response.status_code == 200
        sites_data = list_response.json()["data"]
        assert "sites" in sites_data
        assert len(sites_data["sites"]) == 1
        assert sites_data["sites"][0]["site_id"] == site_id

        # ========== Step 3: Update site ==========
        update_response = await client.put(
            f"/v1/operators/me/sites/{site_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Beijing Chaoyang Store Upgraded",
                "address": "No.88 Jianguo Road, Chaoyang District, Beijing",
                "description": "Flagship store with new equipment"
            }
        )

        assert update_response.status_code == 200
        updated_site = update_response.json()["data"]
        assert updated_site["site_id"] == site_id
        assert updated_site["name"] == "Beijing Chaoyang Store Upgraded"
        assert updated_site["description"] == "Flagship store with new equipment"

        # ========== Step 4: Verify update in list ==========
        list_response2 = await client.get(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"}
        )

        sites_data2 = list_response2.json()["data"]["sites"]
        assert len(sites_data2) == 1
        assert sites_data2[0]["name"] == "Beijing Chaoyang Store Upgraded"
        assert sites_data2[0]["description"] == "Flagship store with new equipment"

        # ========== Step 5: Delete site (soft delete) ==========
        delete_response = await client.delete(
            f"/v1/operators/me/sites/{site_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert delete_response.status_code == 200
        assert delete_response.json()["success"] is True

        # ========== Step 6: Query list, verify deleted site not shown ==========
        list_response3 = await client.get(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"}
        )

        sites_data3 = list_response3.json()["data"]["sites"]
        assert len(sites_data3) == 0

        # ========== Step 7: With include_deleted param, verify deleted site shown ==========
        list_with_deleted = await client.get(
            "/v1/operators/me/sites?include_deleted=true",
            headers={"Authorization": f"Bearer {token}"}
        )

        sites_with_deleted = list_with_deleted.json()["data"]["sites"]
        assert len(sites_with_deleted) == 1
        assert sites_with_deleted[0]["site_id"] == site_id
        assert sites_with_deleted[0]["is_deleted"] is True


@pytest.mark.asyncio
async def test_create_and_update_site(test_db):
    """Test create and immediately update site"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "site_flow_user_2")

        # Create site
        create_response = await client.post(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Shanghai Store",
                "address": "No.100 West Nanjing Road, Jing'an District, Shanghai"
            }
        )

        site_id = create_response.json()["data"]["site_id"]

        # Update site
        update_response = await client.put(
            f"/v1/operators/me/sites/{site_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Shanghai Jing'an Flagship Store",
                "address": "No.100 West Nanjing Road, Jing'an District, Shanghai"
            }
        )

        assert update_response.status_code == 200
        updated_site = update_response.json()["data"]
        assert updated_site["name"] == "Shanghai Jing'an Flagship Store"


@pytest.mark.asyncio
async def test_create_multiple_sites_and_list(test_db):
    """Test create multiple sites and list"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "site_flow_user_3")

        # Create 3 sites
        sites_to_create = [
            {"name": "Beijing Store", "address": "No.88 Jianguo Road, Chaoyang District, Beijing"},
            {"name": "Shanghai Store", "address": "No.100 West Nanjing Road, Jing'an District, Shanghai"},
            {"name": "Guangzhou Store", "address": "No.10 Tiyu West Road, Tianhe District, Guangzhou"}
        ]

        created_ids = []
        for site_data in sites_to_create:
            response = await client.post(
                "/v1/operators/me/sites",
                headers={"Authorization": f"Bearer {token}"},
                json=site_data
            )
            assert response.status_code == 201
            created_ids.append(response.json()["data"]["site_id"])

        # Query list and verify all 3 sites
        list_response = await client.get(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"}
        )

        sites_data = list_response.json()["data"]["sites"]
        assert len(sites_data) == 3

        # Verify all IDs are in list
        returned_ids = {site["site_id"] for site in sites_data}
        for created_id in created_ids:
            assert created_id in returned_ids


@pytest.mark.asyncio
async def test_delete_nonexistent_site(test_db):
    """Test delete non-existent site"""
    from uuid import uuid4

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "site_flow_user_4")

        # Use a valid UUID format but non-existent site
        fake_uuid = str(uuid4())

        # Try to delete non-existent site
        response = await client.delete(
            f"/v1/operators/me/sites/site_{fake_uuid}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_nonexistent_site(test_db):
    """Test update non-existent site"""
    from uuid import uuid4

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "site_flow_user_5")

        # Use a valid UUID format but non-existent site
        fake_uuid = str(uuid4())

        # Try to update non-existent site
        response = await client.put(
            f"/v1/operators/me/sites/site_{fake_uuid}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Test Store",
                "address": "Test Address"
            }
        )

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_already_deleted_site(test_db):
    """Test delete already deleted site"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "site_flow_user_6")

        # Create site
        create_response = await client.post(
            "/v1/operators/me/sites",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Test Store",
                "address": "Test Address 123"
            }
        )

        site_id = create_response.json()["data"]["site_id"]

        # First delete
        delete_response1 = await client.delete(
            f"/v1/operators/me/sites/{site_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert delete_response1.status_code == 200

        # Second delete should return 404 or 409
        delete_response2 = await client.delete(
            f"/v1/operators/me/sites/{site_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert delete_response2.status_code in [404, 409]
