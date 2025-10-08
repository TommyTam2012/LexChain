from fastapi import APIRouter
from . import semantic, compare, summarize, analyze, synthesize, citations, graph

router = APIRouter(prefix="/cases", tags=["Cases"])

# Mount sub-routers (each defines endpoints under /cases/*)
router.include_router(semantic.router)
router.include_router(compare.router)
router.include_router(summarize.router)
router.include_router(analyze.router)
router.include_router(synthesize.router)
router.include_router(citations.router)
router.include_router(graph.router)
