"""Admin business operations service.

This service handles admin operations like reviewing application authorization requests.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID as PyUUID

from sqlalchemy import select, and_, desc, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ..core import BadRequestException, NotFoundException
from ..models.app_request import ApplicationRequest
from ..models.authorization import OperatorAppAuthorization
from ..models.application import Application
from ..models.operator import OperatorAccount
from ..schemas.operator import ApplicationRequestItem, ApplicationRequestListResponse


class AdminService:
    """Admin business operations service."""

    def __init__(self, db: AsyncSession):
        """Initialize service with database session.

        Args:
            db: Async database session
        """
        self.db = db

    async def get_application_requests(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> ApplicationRequestListResponse:
        """Get application authorization requests list.

        Args:
            status: Filter by status (pending/approved/rejected), None for all
            page: Page number (starts from 1)
            page_size: Items per page

        Returns:
            ApplicationRequestListResponse: Paginated list of requests
        """
        # Build query with eager loading to avoid N+1 queries
        query = select(ApplicationRequest).options(selectinload(ApplicationRequest.application))

        # Add status filter if provided
        if status:
            query = query.where(ApplicationRequest.status == status)

        # Order by created_at desc (newest first)
        query = query.order_by(desc(ApplicationRequest.created_at))

        # Get total count using func.count() instead of loading all records
        count_query = select(func.count(ApplicationRequest.id))
        if status:
            count_query = count_query.where(ApplicationRequest.status == status)

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query with application relationship loaded
        result = await self.db.execute(query)
        requests = result.scalars().all()

        # Convert to response items
        items = []
        for req in requests:
            # Application relation already loaded via selectinload

            items.append(ApplicationRequestItem(
                request_id=str(req.id),
                app_id=str(req.application_id),
                app_code=req.application.app_code if req.application else "unknown",
                app_name=req.application.app_name if req.application else "Unknown",
                reason=req.request_reason,
                status=req.status,
                reject_reason=req.reject_reason,
                reviewed_by=str(req.reviewed_by) if req.reviewed_by else None,
                reviewed_at=req.reviewed_at,
                created_at=req.created_at
            ))

        return ApplicationRequestListResponse(
            page=page,
            page_size=page_size,
            total=total,
            items=items
        )

    async def review_application_request(
        self,
        request_id: str,
        admin_id: PyUUID,
        action: str,
        reject_reason: Optional[str] = None
    ) -> ApplicationRequestItem:
        """Review (approve/reject) an application authorization request.

        Args:
            request_id: Application request ID
            admin_id: Admin ID performing the review
            action: "approve" or "reject"
            reject_reason: Reason for rejection (required if action is reject)

        Returns:
            ApplicationRequestItem: Updated request item

        Raises:
            NotFoundException: If request not found
            BadRequestException: If request already reviewed or validation fails
        """
        # Validate action
        if action not in ["approve", "reject"]:
            raise BadRequestException("Invalid action. Must be 'approve' or 'reject'")

        # If rejecting, require reject_reason
        if action == "reject" and not reject_reason:
            raise BadRequestException("Reject reason is required when action is 'reject'")

        # Find the request
        try:
            request_uuid = PyUUID(request_id)
        except ValueError:
            raise BadRequestException("Invalid request ID format")

        result = await self.db.execute(
            select(ApplicationRequest).where(ApplicationRequest.id == request_uuid)
        )
        request = result.scalar_one_or_none()

        if not request:
            raise NotFoundException("Application request not found")

        # Check if already reviewed
        if request.status != "pending":
            raise BadRequestException(f"Request already {request.status}")

        # Update request status
        request.status = "approved" if action == "approve" else "rejected"
        request.reviewed_by = admin_id
        request.reviewed_at = datetime.now(timezone.utc)

        if action == "reject":
            request.reject_reason = reject_reason

        # If approved, create authorization
        if action == "approve":
            # Check if authorization already exists
            auth_result = await self.db.execute(
                select(OperatorAppAuthorization).where(
                    and_(
                        OperatorAppAuthorization.operator_id == request.operator_id,
                        OperatorAppAuthorization.application_id == request.application_id,
                        OperatorAppAuthorization.is_active == True
                    )
                )
            )
            existing_auth = auth_result.scalar_one_or_none()

            if not existing_auth:
                # Create new authorization
                authorization = OperatorAppAuthorization(
                    operator_id=request.operator_id,
                    application_id=request.application_id,
                    authorized_by=admin_id,
                    application_request_id=request.id,
                    is_active=True,
                    authorized_at=datetime.now(timezone.utc),
                    expires_at=None  # Permanent authorization
                )
                self.db.add(authorization)

        # Commit changes
        await self.db.commit()
        await self.db.refresh(request)

        # Load application relation if not loaded
        if not request.application:
            await self.db.refresh(request, ['application'])

        # Return updated request
        return ApplicationRequestItem(
            request_id=str(request.id),
            app_id=str(request.application_id),
            app_code=request.application.app_code if request.application else "unknown",
            app_name=request.application.app_name if request.application else "Unknown",
            reason=request.request_reason,
            status=request.status,
            reject_reason=request.reject_reason,
            reviewed_by=str(request.reviewed_by) if request.reviewed_by else None,
            reviewed_at=request.reviewed_at,
            created_at=request.created_at
        )

    async def get_operators(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> dict:
        """Get operators list for admin.

        Args:
            search: Search by username, full_name, email, or phone
            status: Filter by status (active/inactive/locked)
            page: Page number (starts from 1)
            page_size: Items per page

        Returns:
            dict: Paginated list of operators
        """
        # Build query
        query = select(OperatorAccount).where(OperatorAccount.deleted_at.is_(None))

        # Add search filter if provided
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                (OperatorAccount.username.ilike(search_pattern)) |
                (OperatorAccount.full_name.ilike(search_pattern)) |
                (OperatorAccount.email.ilike(search_pattern)) |
                (OperatorAccount.phone.ilike(search_pattern))
            )

        # Add status filter if provided
        if status:
            if status == "active":
                query = query.where(
                    and_(
                        OperatorAccount.is_active == True,
                        OperatorAccount.is_locked == False
                    )
                )
            elif status == "inactive":
                query = query.where(OperatorAccount.is_active == False)
            elif status == "locked":
                query = query.where(OperatorAccount.is_locked == True)

        # Order by created_at desc (newest first)
        query = query.order_by(desc(OperatorAccount.created_at))

        # Get total count
        count_query = select(OperatorAccount).where(OperatorAccount.deleted_at.is_(None))
        if search:
            search_pattern = f"%{search}%"
            count_query = count_query.where(
                (OperatorAccount.username.ilike(search_pattern)) |
                (OperatorAccount.full_name.ilike(search_pattern)) |
                (OperatorAccount.email.ilike(search_pattern)) |
                (OperatorAccount.phone.ilike(search_pattern))
            )
        if status:
            if status == "active":
                count_query = count_query.where(
                    and_(
                        OperatorAccount.is_active == True,
                        OperatorAccount.is_locked == False
                    )
                )
            elif status == "inactive":
                count_query = count_query.where(OperatorAccount.is_active == False)
            elif status == "locked":
                count_query = count_query.where(OperatorAccount.is_locked == True)

        count_result = await self.db.execute(count_query)
        total = len(count_result.scalars().all())

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        result = await self.db.execute(query)
        operators = result.scalars().all()

        # Convert to response items
        items = [
            {
                "id": str(op.id),
                "username": op.username,
                "full_name": op.full_name,
                "email": op.email,
                "phone": op.phone,
                "balance": float(op.balance),
                "customer_tier": op.customer_tier,
                "is_active": op.is_active,
                "is_locked": op.is_locked,
                "locked_reason": op.locked_reason,
                "locked_at": op.locked_at,
                "last_login_at": op.last_login_at,
                "last_login_ip": op.last_login_ip,
                "created_at": op.created_at,
                "updated_at": op.updated_at,
            }
            for op in operators
        ]

        return {
            "page": page,
            "page_size": page_size,
            "total": total,
            "items": items
        }

    async def get_applications(
        self,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> dict:
        """Get applications list for admin.

        Args:
            search: Search by app_code or app_name
            page: Page number (starts from 1)
            page_size: Items per page

        Returns:
            dict: Paginated list of applications
        """
        # Build query
        query = select(Application)

        # Add search filter if provided
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                (Application.app_code.ilike(search_pattern)) |
                (Application.app_name.ilike(search_pattern))
            )

        # Order by created_at desc (newest first)
        query = query.order_by(desc(Application.created_at))

        # Get total count
        count_query = select(Application)
        if search:
            search_pattern = f"%{search}%"
            count_query = count_query.where(
                (Application.app_code.ilike(search_pattern)) |
                (Application.app_name.ilike(search_pattern))
            )

        count_result = await self.db.execute(count_query)
        total = len(count_result.scalars().all())

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        result = await self.db.execute(query)
        applications = result.scalars().all()

        # Convert to response items
        items = [
            {
                "id": str(app.id),
                "app_code": app.app_code,
                "app_name": app.app_name,
                "description": app.description,
                "price_per_request": float(app.price_per_player),
                "is_active": app.is_active,
                "created_at": app.created_at,
                "updated_at": app.updated_at,
            }
            for app in applications
        ]

        return {
            "page": page,
            "page_size": page_size,
            "total": total,
            "items": items
        }

    # ==================== Application Management (T132) ====================

    async def create_application(
        self,
        admin_id: PyUUID,
        app_code: str,
        app_name: str,
        description: Optional[str],
        price_per_player: float,
        min_players: int,
        max_players: int
    ) -> dict:
        """Create a new application.

        Args:
            admin_id: Admin ID creating the application
            app_code: Unique application code
            app_name: Application name
            description: Application description
            price_per_player: Price per player
            min_players: Minimum players
            max_players: Maximum players

        Returns:
            dict: Created application data

        Raises:
            BadRequestException: If validation fails
        """
        from decimal import Decimal

        # Check if app_code already exists
        existing = await self.db.execute(
            select(Application).where(Application.app_code == app_code)
        )
        if existing.scalar_one_or_none():
            raise BadRequestException(f"Application code '{app_code}' already exists")

        # Validate player range
        if min_players < 1:
            raise BadRequestException("Minimum players must be at least 1")
        if max_players < min_players:
            raise BadRequestException("Maximum players must be >= minimum players")
        if max_players > 100:
            raise BadRequestException("Maximum players cannot exceed 100")

        # Validate price
        if price_per_player <= 0:
            raise BadRequestException("Price per player must be positive")

        # Create application
        app = Application(
            app_code=app_code,
            app_name=app_name,
            description=description,
            price_per_player=Decimal(str(price_per_player)),
            min_players=min_players,
            max_players=max_players,
            is_active=True,
            created_by=admin_id
        )
        self.db.add(app)
        await self.db.commit()
        await self.db.refresh(app)

        return {
            "id": str(app.id),
            "app_code": app.app_code,
            "app_name": app.app_name,
            "description": app.description,
            "price_per_player": float(app.price_per_player),
            "min_players": app.min_players,
            "max_players": app.max_players,
            "is_active": app.is_active,
            "created_at": app.created_at,
            "updated_at": app.updated_at,
        }

    async def update_application_price(
        self,
        app_id: str,
        new_price: float
    ) -> dict:
        """Update application price.

        Args:
            app_id: Application ID
            new_price: New price per player

        Returns:
            dict: Updated application data

        Raises:
            NotFoundException: If application not found
            BadRequestException: If validation fails
        """
        from decimal import Decimal

        # Validate price
        if new_price <= 0:
            raise BadRequestException("Price must be positive")

        # Find application
        try:
            app_uuid = PyUUID(app_id)
        except ValueError:
            raise BadRequestException("Invalid application ID format")

        result = await self.db.execute(
            select(Application).where(Application.id == app_uuid)
        )
        app = result.scalar_one_or_none()

        if not app:
            raise NotFoundException("Application not found")

        # Update price
        app.price_per_player = Decimal(str(new_price))
        app.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(app)

        return {
            "id": str(app.id),
            "app_code": app.app_code,
            "app_name": app.app_name,
            "price_per_player": float(app.price_per_player),
            "updated_at": app.updated_at,
        }

    async def update_player_range(
        self,
        app_id: str,
        min_players: int,
        max_players: int
    ) -> dict:
        """Update application player range.

        Args:
            app_id: Application ID
            min_players: New minimum players
            max_players: New maximum players

        Returns:
            dict: Updated application data

        Raises:
            NotFoundException: If application not found
            BadRequestException: If validation fails
        """
        # Validate player range
        if min_players < 1:
            raise BadRequestException("Minimum players must be at least 1")
        if max_players < min_players:
            raise BadRequestException("Maximum players must be >= minimum players")
        if max_players > 100:
            raise BadRequestException("Maximum players cannot exceed 100")

        # Find application
        try:
            app_uuid = PyUUID(app_id)
        except ValueError:
            raise BadRequestException("Invalid application ID format")

        result = await self.db.execute(
            select(Application).where(Application.id == app_uuid)
        )
        app = result.scalar_one_or_none()

        if not app:
            raise NotFoundException("Application not found")

        # Update player range
        app.min_players = min_players
        app.max_players = max_players
        app.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(app)

        return {
            "id": str(app.id),
            "app_code": app.app_code,
            "app_name": app.app_name,
            "min_players": app.min_players,
            "max_players": app.max_players,
            "updated_at": app.updated_at,
        }

    # ==================== Authorization Management (T133) ====================

    async def authorize_application(
        self,
        operator_id: str,
        application_id: str,
        admin_id: PyUUID,
        expires_at: Optional[datetime] = None
    ) -> dict:
        """Authorize an application for an operator.

        Args:
            operator_id: Operator ID
            application_id: Application ID
            admin_id: Admin ID performing the authorization
            expires_at: Optional expiration datetime

        Returns:
            dict: Authorization data

        Raises:
            NotFoundException: If operator or application not found
            BadRequestException: If authorization already exists
        """
        # Convert IDs to UUID
        try:
            op_uuid = PyUUID(operator_id)
            app_uuid = PyUUID(application_id)
        except ValueError:
            raise BadRequestException("Invalid ID format")

        # Check operator exists
        op_result = await self.db.execute(
            select(OperatorAccount).where(OperatorAccount.id == op_uuid)
        )
        operator = op_result.scalar_one_or_none()
        if not operator:
            raise NotFoundException("Operator not found")

        # Check application exists
        app_result = await self.db.execute(
            select(Application).where(Application.id == app_uuid)
        )
        application = app_result.scalar_one_or_none()
        if not application:
            raise NotFoundException("Application not found")

        # Check if authorization already exists
        auth_result = await self.db.execute(
            select(OperatorAppAuthorization).where(
                and_(
                    OperatorAppAuthorization.operator_id == op_uuid,
                    OperatorAppAuthorization.application_id == app_uuid,
                    OperatorAppAuthorization.is_active == True
                )
            )
        )
        existing_auth = auth_result.scalar_one_or_none()

        if existing_auth:
            raise BadRequestException("Authorization already exists for this operator-application pair")

        # Create authorization
        authorization = OperatorAppAuthorization(
            operator_id=op_uuid,
            application_id=app_uuid,
            authorized_by=admin_id,
            is_active=True,
            authorized_at=datetime.now(timezone.utc),
            expires_at=expires_at
        )
        self.db.add(authorization)
        await self.db.commit()
        await self.db.refresh(authorization)

        return {
            "id": str(authorization.id),
            "operator_id": str(authorization.operator_id),
            "application_id": str(authorization.application_id),
            "authorized_at": authorization.authorized_at,
            "expires_at": authorization.expires_at,
            "is_active": authorization.is_active,
        }

    async def revoke_authorization(
        self,
        operator_id: str,
        application_id: str
    ) -> dict:
        """Revoke an application authorization for an operator.

        Args:
            operator_id: Operator ID
            application_id: Application ID

        Returns:
            dict: Revoked authorization data

        Raises:
            NotFoundException: If authorization not found
            BadRequestException: If validation fails
        """
        # Convert IDs to UUID
        try:
            op_uuid = PyUUID(operator_id)
            app_uuid = PyUUID(application_id)
        except ValueError:
            raise BadRequestException("Invalid ID format")

        # Find active authorization
        result = await self.db.execute(
            select(OperatorAppAuthorization).where(
                and_(
                    OperatorAppAuthorization.operator_id == op_uuid,
                    OperatorAppAuthorization.application_id == app_uuid,
                    OperatorAppAuthorization.is_active == True
                )
            )
        )
        authorization = result.scalar_one_or_none()

        if not authorization:
            raise NotFoundException("Active authorization not found")

        # Revoke authorization
        authorization.is_active = False
        authorization.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(authorization)

        return {
            "id": str(authorization.id),
            "operator_id": str(authorization.operator_id),
            "application_id": str(authorization.application_id),
            "is_active": authorization.is_active,
            "updated_at": authorization.updated_at,
        }

    # ==================== 运营点管理 ====================

    async def get_sites(
        self,
        search: Optional[str] = None,
        operator_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> dict:
        """获取运营点列表

        Args:
            search: 搜索关键词（运营点名称或地址）
            operator_id: 运营商ID筛选
            page: 页码
            page_size: 每页条数

        Returns:
            dict: 分页的运营点列表
        """
        from ..models.site import OperationSite
        from ..schemas.site import SiteListResponse, SiteItem

        # Build query with eager loading
        query = select(OperationSite).options(
            selectinload(OperationSite.operator)
        ).where(OperationSite.deleted_at.is_(None))

        # Add search filter if provided
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                (OperationSite.name.ilike(search_pattern)) |
                (OperationSite.address.ilike(search_pattern))
            )

        # Add operator filter if provided
        if operator_id:
            try:
                op_uuid = PyUUID(operator_id)
                query = query.where(OperationSite.operator_id == op_uuid)
            except ValueError:
                raise BadRequestException("Invalid operator ID format")

        # Order by created_at desc (newest first)
        query = query.order_by(desc(OperationSite.created_at))

        # Get total count
        count_query = select(func.count(OperationSite.id)).where(
            OperationSite.deleted_at.is_(None)
        )
        if search:
            search_pattern = f"%{search}%"
            count_query = count_query.where(
                (OperationSite.name.ilike(search_pattern)) |
                (OperationSite.address.ilike(search_pattern))
            )
        if operator_id:
            try:
                op_uuid = PyUUID(operator_id)
                count_query = count_query.where(OperationSite.operator_id == op_uuid)
            except ValueError:
                raise BadRequestException("Invalid operator ID format")

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        result = await self.db.execute(query)
        sites = result.scalars().all()

        # Convert to response items
        items = []
        for site in sites:
            items.append(SiteItem(
                site_id=site.id,
                name=site.name,
                address=site.address,
                description=site.description,
                operator_id=site.operator_id,
                operator_name=site.operator.full_name if site.operator else "Unknown",
                contact_person=site.contact_person,
                contact_phone=site.contact_phone,
                server_identifier=site.server_identifier,
                is_active=site.is_active,
                created_at=site.created_at,
                updated_at=site.updated_at,
            ))

        return SiteListResponse(
            page=page,
            page_size=page_size,
            total=total,
            items=items
        )

    async def create_site(
        self,
        admin_id: PyUUID,
        name: str,
        address: str,
        description: Optional[str],
        operator_id: PyUUID,
        contact_person: Optional[str] = None,
        contact_phone: Optional[str] = None,
        server_identifier: Optional[str] = None
    ) -> dict:
        """创建运营点

        Args:
            admin_id: 管理员ID
            name: 运营点名称
            address: 运营点地址
            description: 运营点描述
            operator_id: 运营商ID
            contact_person: 现场负责人
            contact_phone: 现场联系电话
            server_identifier: 头显Server设备标识符

        Returns:
            dict: 创建的运营点数据

        Raises:
            NotFoundException: 如果运营商不存在
            BadRequestException: 如果验证失败
        """
        from ..models.site import OperationSite

        # Check if operator exists
        op_result = await self.db.execute(
            select(OperatorAccount).where(OperatorAccount.id == operator_id)
        )
        operator = op_result.scalar_one_or_none()
        if not operator:
            raise NotFoundException("Operator not found")

        # Create site
        site = OperationSite(
            name=name,
            address=address,
            description=description,
            operator_id=operator_id,
            contact_person=contact_person,
            contact_phone=contact_phone,
            server_identifier=server_identifier,
            is_active=True
        )
        self.db.add(site)
        await self.db.commit()
        await self.db.refresh(site)

        # Load operator relation
        await self.db.refresh(site, ['operator'])

        return {
            "site_id": site.id,
            "name": site.name,
            "address": site.address,
            "description": site.description,
            "operator_id": site.operator_id,
            "operator_name": site.operator.full_name if site.operator else "Unknown",
            "contact_person": site.contact_person,
            "contact_phone": site.contact_phone,
            "server_identifier": site.server_identifier,
            "is_active": site.is_active,
            "created_at": site.created_at,
            "updated_at": site.updated_at,
        }

    async def update_site(
        self,
        site_id: str,
        admin_id: PyUUID,
        **update_data
    ) -> dict:
        """更新运营点

        Args:
            site_id: 运营点ID
            admin_id: 管理员ID
            **update_data: 更新数据

        Returns:
            dict: 更新后的运营点数据

        Raises:
            NotFoundException: 如果运营点不存在
            BadRequestException: 如果验证失败
        """
        from ..models.site import OperationSite

        # Find site
        try:
            site_uuid = PyUUID(site_id)
        except ValueError:
            raise BadRequestException("Invalid site ID format")

        result = await self.db.execute(
            select(OperationSite).options(
                selectinload(OperationSite.operator)
            ).where(
                and_(
                    OperationSite.id == site_uuid,
                    OperationSite.deleted_at.is_(None)
                )
            )
        )
        site = result.scalar_one_or_none()

        if not site:
            raise NotFoundException("Site not found")

        # Update fields
        for field, value in update_data.items():
            if value is not None and hasattr(site, field):
                setattr(site, field, value)

        site.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(site)

        return {
            "site_id": site.id,
            "name": site.name,
            "address": site.address,
            "description": site.description,
            "operator_id": site.operator_id,
            "operator_name": site.operator.full_name if site.operator else "Unknown",
            "contact_person": site.contact_person,
            "contact_phone": site.contact_phone,
            "server_identifier": site.server_identifier,
            "is_active": site.is_active,
            "created_at": site.created_at,
            "updated_at": site.updated_at,
        }

    async def delete_site(
        self,
        site_id: str,
        admin_id: PyUUID
    ) -> None:
        """删除运营点（软删除）

        Args:
            site_id: 运营点ID
            admin_id: 管理员ID

        Raises:
            NotFoundException: 如果运营点不存在
            BadRequestException: 如果验证失败
        """
        from ..models.site import OperationSite

        # Find site
        try:
            site_uuid = PyUUID(site_id)
        except ValueError:
            raise BadRequestException("Invalid site ID format")

        result = await self.db.execute(
            select(OperationSite).where(
                and_(
                    OperationSite.id == site_uuid,
                    OperationSite.deleted_at.is_(None)
                )
            )
        )
        site = result.scalar_one_or_none()

        if not site:
            raise NotFoundException("Site not found")

        # Soft delete
        site.deleted_at = datetime.now(timezone.utc)
        site.updated_at = datetime.now(timezone.utc)

        await self.db.commit()

    async def create_operator(
        self,
        admin_id: PyUUID,
        username: str,
        password: str,
        full_name: str,
        email: str,
        phone: str,
        customer_tier: str = "standard"
    ) -> dict:
        """Create a new operator account.

        Args:
            admin_id: Admin ID creating the operator
            username: Operator username (must be unique)
            password: Operator password
            full_name: Operator full name
            email: Operator email
            phone: Operator phone
            customer_tier: Customer tier (vip/standard/trial)

        Returns:
            dict: Created operator data

        Raises:
            BadRequestException: If validation fails
        """
        from ..core.utils.password import hash_password
        import secrets
        import string

        def _generate_api_key() -> str:
            """Generate a secure random API key."""
            alphabet = string.ascii_letters + string.digits
            return ''.join(secrets.choice(alphabet) for _ in range(64))

        # Validate customer tier
        if customer_tier not in ["vip", "standard", "trial"]:
            raise BadRequestException("Invalid customer tier. Must be 'vip', 'standard', or 'trial'")

        # Check for existing username
        existing_result = await self.db.execute(
            select(OperatorAccount).where(
                and_(
                    OperatorAccount.username == username,
                    OperatorAccount.deleted_at.is_(None)
                )
            )
        )
        if existing_result.scalar_one_or_none():
            raise BadRequestException(f"Username '{username}' already exists")

        # Check for existing email
        existing_email_result = await self.db.execute(
            select(OperatorAccount).where(
                and_(
                    OperatorAccount.email == email,
                    OperatorAccount.deleted_at.is_(None)
                )
            )
        )
        if existing_email_result.scalar_one_or_none():
            raise BadRequestException(f"Email '{email}' already exists")

        # Generate password hash and API key
        password_hash = hash_password(password)
        api_key = _generate_api_key()
        api_key_hash = hash_password(api_key)  # Use hash_password for API key hash

        # Create operator account
        operator = OperatorAccount(
            username=username,
            password_hash=password_hash,
            full_name=full_name,
            email=email,
            phone=phone,
            customer_tier=customer_tier,
            api_key=api_key,
            api_key_hash=api_key_hash,
            balance=0.00,
            is_active=True,
            is_locked=False
        )

        self.db.add(operator)
        await self.db.commit()
        await self.db.refresh(operator)

        # Return operator data (excluding password hash and API key hash)
        return {
            "id": str(operator.id),
            "username": operator.username,
            "full_name": operator.full_name,
            "email": operator.email,
            "phone": operator.phone,
            "customer_tier": operator.customer_tier,
            "balance": float(operator.balance),
            "is_active": operator.is_active,
            "is_locked": operator.is_locked,
            "locked_reason": operator.locked_reason,
            "locked_at": operator.locked_at,
            "last_login_at": operator.last_login_at,
            "last_login_ip": operator.last_login_ip,
            "api_key": operator.api_key,  # Return the actual API key for display
            "created_at": operator.created_at,
            "updated_at": operator.updated_at
        }
