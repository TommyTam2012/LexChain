from fastapi import APIRouter, Query
from typing import Optional
from ..clients.hklii import hklii_search

router = APIRouter(prefix="/hklii", tags=["HKLII"])

@router.get("/search")
async def hklii_proxy(
    q: str = Query(..., description="HKLII query string"),
    page: Optional[int] = Query(1, ge=1),
    page_size: Optional[int] = Query(5, ge=1, le=100),
):
    # Basic params; adjust names here to match HKLII’s expected fields
    params = {"q": q, "page": page, "page_size": page_size}
    return await hklii_search(params)
