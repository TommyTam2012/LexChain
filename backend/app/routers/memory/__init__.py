from fastapi import APIRouter
from .anchor import router as anchor_router

# Expose a package-level router so main.py can do: app.include_router(memory.router)
router = APIRouter(prefix="/memory", tags=["Memory"])
router.include_router(anchor_router)
