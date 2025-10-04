
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="LexChain API", version="0.0.1")

# CORS (open for now; tighten later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "LexChain backend online. Visit /docs for Swagger."}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/version")
def version():
    return {"name": "LexChain API", "version": "0.0.1"}
# ======== LexChain demo: /cases/search (stub) ========
from typing import List, Optional
from fastapi import Query
from pydantic import BaseModel

# Sample stub data (replace with real CourtListener data later)
SAMPLE_CASES = [
    {
        "id": "us-1999-001",
        "title": "Smith v. Jones",
        "court": "U.S. Supreme Court",
        "date": "1999-06-12",
        "summary": "Dispute over contractual obligations and damages.",
        "citations": ["us-1975-010", "us-1982-233"],
    },
    {
        "id": "us-2014-042",
        "title": "Doe v. State of California",
        "court": "California Court of Appeal",
        "date": "2014-03-27",
        "summary": "Privacy rights case involving warrantless search.",
        "citations": ["ca-2008-112"],
    },
    {
        "id": "us-2007-118",
        "title": "Acme Corp. v. Omega LLC",
        "court": "9th Circuit",
        "date": "2007-11-02",
        "summary": "Antitrust and unfair competition; appeal affirmed in part.",
        "citations": [],
    },
]

class Case(BaseModel):
    id: str
    title: str
    court: str
    date: str
    summary: Optional[str] = None
    citations: List[str] = []

class SearchResult(BaseModel):
    query: str
    count: int
    items: List[Case]

@app.get("/cases/search", response_model=SearchResult)
def search_cases(q: str = Query(..., min_length=1, max_length=100, description="Search text")):
    ql = q.lower()
    items = []
    for c in SAMPLE_CASES:
        haystack = f"{c['title']} {c.get('summary','')} {c['court']}".lower()
        if ql in haystack:
            items.append(Case(**c))
    return SearchResult(query=q, count=len(items), items=items)
# =====================================================

