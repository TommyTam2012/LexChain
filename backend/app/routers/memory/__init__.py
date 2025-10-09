from fastapi import APIRouter
from .anchor import router as anchor_router
from .search import router as search_router

# Expose a package-level router so main.py can do: app.include_router(memory.router)
router = APIRouter(prefix="/memory", tags=["Memory"])
router.include_router(anchor_router)
router.include_router(search_router)
