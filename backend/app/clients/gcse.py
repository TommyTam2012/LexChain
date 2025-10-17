import os, httpx
from typing import Dict, Any

KEY = os.getenv("CSE_KEY", "")
CX  = os.getenv("CSE_CX", "")
BASE = "https://www.googleapis.com/customsearch/v1"

async def gcse_search(q: str, num: int = 5) -> Dict[str, Any]:
    if not KEY or not CX:
        return {"ok": False, "error": "CSE_KEY or CSE_CX not set"}
    params = {"key": KEY, "cx": CX, "q": q, "num": num}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(BASE, params=params)
        data = r.json()
        return {"ok": r.status_code < 400, "status": r.status_code, "data": data, "url": str(r.request.url)}
