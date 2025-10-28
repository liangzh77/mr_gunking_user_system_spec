"""
Integration Test: Application Authorization Request Flow (T086)

Test complete application authorization request workflow:
1. Apply for application authorization
2. Query authorization request list
3. Verify request status and data integrity
4. Test edge cases (duplicate requests, non-existent apps, etc.)
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


async def create_application(db, app_code: str, app_name: str, is_active: bool = True) -> str:
    """Create application, return application_id"""
    from src.models.application import Application
    from decimal import Decimal

    app = Application(
        app_code=app_code,
        app_name=app_name,
        description=f"{app_name}的描述",
        price_per_player=Decimal("10.00"),
        min_players=2,
        max_players=8,
        is_active=is_active
    )

    db.add(app)
    await db.commit()
    await db.refresh(app)

    return str(app.id)


# ========== Integration Tests ==========

@pytest.mark.asyncio
async def test_application_request_full_flow(test_db):
    """Test complete application authorization request flow"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "app_request_user_1")

        # Create application first
        app_id = await create_application(test_db, "space_adventure", "太空探险")

        # ========== Step 1: Apply for application authorization ==========
        request_response = await client.post(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "app_id": f"app_{app_id}",
                "reason": "门店客户强烈要求，预计月消费额5000元以上"
            }
        )

        assert request_response.status_code == 201
        request_data = request_response.json()["data"]
        request_id = request_data["request_id"]

        # ========== Step 2: Query authorization request list ==========
        list_response = await client.get(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert list_response.status_code == 200
        requests_data = list_response.json()["data"]
        assert "items" in requests_data
        assert len(requests_data["items"]) == 1
        assert requests_data["items"][0]["request_id"] == request_id
        assert requests_data["items"][0]["status"] == "pending"
        assert requests_data["items"][0]["app_code"] == "space_adventure"

        # ========== Step 3: Verify request status remains pending ==========
        # Query again to ensure data consistency
        list_response2 = await client.get(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"}
        )

        requests_data2 = list_response2.json()["data"]["items"]
        assert len(requests_data2) == 1
        assert requests_data2[0]["status"] == "pending"


@pytest.mark.asyncio
async def test_create_multiple_requests_and_query(test_db):
    """Test create multiple authorization requests and query"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "app_request_user_2")

        # Create 3 different applications first
        app_codes = [
            ("space_adventure", "太空探险"),
            ("underwater_world", "海底世界"),
            ("racing_master", "赛车大师")
        ]
        created_ids = []

        for app_code, app_name in app_codes:
            # Create application
            app_id = await create_application(test_db, app_code, app_name)

            # Apply for authorization
            response = await client.post(
                "/v1/operators/me/applications/requests",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "app_id": f"app_{app_id}",
                    "reason": f"门店需要{app_name}游戏，预计月消费3000元以上"
                }
            )
            assert response.status_code == 201
            created_ids.append(response.json()["data"]["request_id"])

        # Query all requests
        list_response = await client.get(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"}
        )

        requests_data = list_response.json()["data"]["items"]
        assert len(requests_data) == 3

        # Verify all request IDs are present
        returned_ids = {req["request_id"] for req in requests_data}
        for created_id in created_ids:
            assert created_id in returned_ids


@pytest.mark.asyncio
async def test_duplicate_request_prevention(test_db):
    """Test duplicate authorization request prevention"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "app_request_user_3")

        # Create application
        app_id = await create_application(test_db, "space_adventure", "太空探险")

        # First request
        response1 = await client.post(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "app_id": f"app_{app_id}",
                "reason": "第一次申请太空探险游戏"
            }
        )

        assert response1.status_code == 201

        # Second request for same app should fail
        response2 = await client.post(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "app_id": f"app_{app_id}",
                "reason": "第二次申请同一个游戏"
            }
        )

        # Should return 400 or 409 (Conflict)
        assert response2.status_code in [400, 409]


@pytest.mark.asyncio
async def test_request_nonexistent_application(test_db):
    """Test request authorization for non-existent application"""
    from uuid import uuid4

    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "app_request_user_4")

        # Use a non-existent UUID
        fake_uuid = str(uuid4())

        response = await client.post(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "app_id": f"app_{fake_uuid}",
                "reason": "测试申请不存在的应用，理由至少10个字符"
            }
        )

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_request_inactive_application(test_db):
    """Test request authorization for inactive application"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "app_request_user_5")

        # Create an inactive application
        app_id = await create_application(test_db, "mystery_dungeon", "神秘地牢", is_active=False)

        response = await client.post(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "app_id": f"app_{app_id}",
                "reason": "申请已下架的应用，测试业务逻辑"
            }
        )

        # Should return 400 or 404 depending on business logic
        assert response.status_code in [400, 404]


@pytest.mark.asyncio
async def test_request_list_sorted_by_time(test_db):
    """Test authorization request list is sorted by creation time (newest first)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        token = await create_and_login_operator(client, "app_request_user_6")

        # Create 3 applications and request them in sequence
        app_codes = [
            ("space_adventure", "太空探险"),
            ("underwater_world", "海底世界"),
            ("racing_master", "赛车大师")
        ]

        for app_code, app_name in app_codes:
            app_id = await create_application(test_db, app_code, app_name)
            await client.post(
                "/v1/operators/me/applications/requests",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "app_id": f"app_{app_id}",
                    "reason": f"申请{app_name}游戏，客户需求强烈"
                }
            )

        # Query list
        list_response = await client.get(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token}"}
        )

        requests = list_response.json()["data"]["items"]
        assert len(requests) == 3

        # Verify sorted by created_at descending (newest first)
        # Check that timestamps are in descending order
        from datetime import datetime
        timestamps = [datetime.fromisoformat(req["created_at"].replace('Z', '+00:00')) for req in requests]

        for i in range(len(timestamps) - 1):
            # Each timestamp should be >= the next one (descending order)
            assert timestamps[i] >= timestamps[i + 1], \
                f"Timestamps not in descending order: {timestamps[i]} should be >= {timestamps[i + 1]}"


@pytest.mark.asyncio
async def test_data_isolation_between_operators(test_db):
    """Test data isolation: operators can only see their own requests"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create two operators
        token1 = await create_and_login_operator(client, "app_request_user_7a")
        token2 = await create_and_login_operator(client, "app_request_user_7b")

        # Create applications
        app_id1 = await create_application(test_db, "space_adventure", "太空探险")
        app_id2 = await create_application(test_db, "underwater_world", "海底世界")

        # Operator 1 creates a request
        await client.post(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token1}"},
            json={
                "app_id": f"app_{app_id1}",
                "reason": "运营商1申请太空探险游戏"
            }
        )

        # Operator 2 creates a different request
        await client.post(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token2}"},
            json={
                "app_id": f"app_{app_id2}",
                "reason": "运营商2申请海底世界游戏"
            }
        )

        # Operator 1 queries their requests
        response1 = await client.get(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token1}"}
        )

        # Operator 2 queries their requests
        response2 = await client.get(
            "/v1/operators/me/applications/requests",
            headers={"Authorization": f"Bearer {token2}"}
        )

        # Each should only see their own request
        requests1 = response1.json()["data"]["items"]
        requests2 = response2.json()["data"]["items"]

        assert len(requests1) == 1
        assert len(requests2) == 1
        assert requests1[0]["app_code"] == "space_adventure"
        assert requests2[0]["app_code"] == "underwater_world"
