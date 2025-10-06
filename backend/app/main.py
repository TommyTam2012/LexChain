# ==========================================================
# LexChain FastAPI Main – HKLII-style dynamic loader
# ==========================================================
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import json, os

# ==========================================================
# Routers (LangChain QA)
# ==========================================================
from app.routers import qa

# ==========================================================
# App Setup
# ==========================================================
app = FastAPI(title="LexChain API", version="0.0.1")

# Register Routers
app.include_router(qa.router)

# ==========================================================
# Middleware (CORS)
# ==========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://lexchain-w9rl.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================================
# Static Files (optional)
# ==========================================================
BASE_DIR = Path(__file__).parent.resolve()
STATIC_DIR = BASE_DIR / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ==========================================================
# Core Routes
# ==========================================================
@app.get("/")
def root():
    """Redirect to /docs for Swagger."""
    return RedirectResponse(url="/docs")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/version")
def version():
    env = os.getenv("LEXCHAIN_ENV", "dev")
    return {"name": "LexChain API", "version": "0.0.1", "env": env}

# ==========================================================
# HKLII-style Case Loader
# ==========================================================
from fastapi import HTTPException

DATA_PATH = Path(__file__).parent.parent / "data" / "normalized" / "cases_normalized.jsonl"

def load_cases():
    cases = []
    if not DATA_PATH.exists():
        raise HTTPException(status_code=500, detail=f"{DATA_PATH} not found")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                cases.append({
                    "id": row.get("id", ""),
                    "title": row.get("title", ""),
                    "court": row.get("court", ""),
                    "date": row.get("date", ""),
                    "summary": row.get("summary", ""),
                    "citations": row.get("citations", []),
                })
            except Exception:
                continue
    return cases

SAMPLE_CASES = load_cases()

# ==========================================================
# Search Endpoint (keyword / token match)
# ==========================================================
class Case(BaseModel):
    id: str
    title: str
    court: Optional[str] = ""
    date: Optional[str] = ""
    summary: Optional[str] = ""
    citations: List[str] = []


class SearchResult(BaseModel):
    query: str
    count: int
    items: List[Case]


@app.get("/cases/search", response_model=SearchResult)
def search_cases(
    q: str = Query(..., min_length=1, max_length=100, description="Search text"),
):
    """Searches loaded HKLII-style cases (case-insensitive, token match)."""
    tokens = [t for t in q.lower().split() if t]
    results = []
    for c in SAMPLE_CASES:
        haystack = f"{c.get('title','')} {c.get('summary','')} {c.get('court','')}".lower()
        if any(t in haystack for t in tokens):
            results.append(Case(**c))
    return SearchResult(query=q, count=len(results), items=results)

# ==========================================================
# Run (Local Dev Only)
# ==========================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
