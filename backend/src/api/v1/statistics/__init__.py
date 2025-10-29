"""Statistics API module

Aggregates all statistics-related API routers for admin users.
"""

from fastapi import APIRouter

from .dashboard import router as dashboard_router
from .applications import router as applications_router
from .sites import router as sites_router
from .players import router as players_router
from .cross_analysis import router as cross_analysis_router
from .export import router as export_router

# Create main statistics router
router = APIRouter(prefix="/statistics", tags=["Statistics"])

# Include all sub-routers
router.include_router(dashboard_router)
router.include_router(applications_router)
router.include_router(sites_router)
router.include_router(players_router)
router.include_router(cross_analysis_router)
router.include_router(export_router)

__all__ = ["router"]
