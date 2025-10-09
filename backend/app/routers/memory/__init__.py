# ==========================================================
# LexChain – Memory Module Init (Phase 3.8)
# ==========================================================
# Captain's Log:
# Purpose: Anchor LexChain's memory system by connecting
#          /memory/anchor and /memory/search subrouters.
# ==========================================================

from fastapi import APIRouter

router = APIRouter(prefix="/memory", tags=["Memory 知识记忆模块"])

# Subrouters will be added in next steps:
# from . import anchor, search
# router.include_router(anchor.router)
# router.include_router(search.router)
