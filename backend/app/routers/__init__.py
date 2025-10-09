from fastapi import APIRouter

from .anchor import router as anchor_router

router = APIRouter(prefix="/memory", tags=["Memory"])

# Mount sub-routers
router.include_router(anchor_router)
