from fastapi import APIRouter, Query
from .shared import _get_retriever, _extract_id_title

router = APIRouter()

@router.get("/semantic")
def semantic_search(query: str = Query(..., description="Search phrase or topic")):
    retriever = _get_retriever()
    docs = retriever.get_relevant_documents(query)
    if not docs:
        return {"query": query, "results": []}
    results = []
    for doc in docs:
        cid, title = _extract_id_title(doc)
        results.append({"id": cid, "title": title, "snippet": doc.page_content[:300]})
    return {"query": query, "results": results}
