from typing import Optional, List, Dict, Any, Tuple
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .shared import load_or_create_vectorstore, get_memory_path, is_placeholder

router = APIRouter()

class SearchItem(BaseModel):
    text: Optional[str] = Field(None, description="Stored text content (omitted if include_text=false)")
    score: Optional[float] = Field(None, description="Similarity score or distance (vector-store dependent)")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SearchResponse(BaseModel):
    ok: bool
    query: str
    k: int
    memory_path: str
    results_count: int
    results: List[SearchItem] = Field(default_factory=list)

def _normalize_with_scores(vs, query: str, k: int) -> List[Tuple[Any, Optional[float]]]:
    if hasattr(vs, "similarity_search_with_relevance_scores"):
        return [(doc, float(score)) for doc, score in vs.similarity_search_with_relevance_scores(query, k=k)]
    if hasattr(vs, "similarity_search_with_score"):
        return [(doc, float(score)) for doc, score in vs.similarity_search_with_score(query, k=k)]
    docs = vs.similarity_search(query, k=k)
    return [(doc, None) for doc in docs]

@router.get("/search", response_model=SearchResponse)
def search_memory(
    q: str = Query(..., description="Free-text query to search memory anchors"),
    k: int = Query(5, ge=1, le=50, description="Number of results to return"),
    topic: Optional[str] = Query(None, description="Filter by exact metadata topic"),
    include_text: bool = Query(True, description="Include stored text content in the response"),
):
    try:
        vs = load_or_create_vectorstore()
        pairs = _normalize_with_scores(vs, q, k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load/search memory: {e}")

    results: List[SearchItem] = []
    for doc, score in pairs:
        meta = getattr(doc, "metadata", {}) or {}
        # Skip internal bootstrap doc
        if is_placeholder(meta):
            continue
        if topic and meta.get("topic") != topic:
            continue

        results.append(SearchItem(
            text=doc.page_content if include_text else None,
            score=score,
            metadata=meta,
        ))

    return SearchResponse(
        ok=True,
        query=q,
        k=k,
        memory_path=get_memory_path(),
        results_count=len(results),
        results=results,
    )
