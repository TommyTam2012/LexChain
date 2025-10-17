from fastapi import APIRouter, Query
from ..clients.gcse import gcse_search

router = APIRouter(prefix="/hklii_gcse", tags=["HKLII (GCSE)"])

@router.get("/search")
async def hklii_gcse(q: str = Query(...), k: int = 5):
    return await gcse_search(q, num=k)
