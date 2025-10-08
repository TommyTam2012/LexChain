from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from .shared import _get_retriever, _get_chat_model, _extract_id_title, _get_meta, _find_doc_by_id

router = APIRouter()

class CitationsRequest(BaseModel):
    id: Optional[str] = None
    query: Optional[str] = None
    k_scan: int = 20
    infer: bool = False

@router.post("/citations")
def citations_lookup(req: CitationsRequest):
    retriever = _get_retriever(k=3)
    llm = _get_chat_model(temp=0)

    # Resolve target doc
    target_doc = None
    if req.id:
        target_doc = _find_doc_by_id(retriever, req.id)
    if (not target_doc) and req.query:
        docs = retriever.get_relevant_documents(req.query)
        target_doc = docs[0] if docs else None

    if not target_doc:
        raise HTTPException(status_code=404, detail="Target case not found for citation lookup.")

    target_id, target_title = _extract_id_title(target_doc)
    target_meta = _get_meta(target_doc)
    outbound = list(target_meta.get("citations", []) or [])

    # Optional GPT inference
    if req.infer and not outbound:
        inferred = llm.predict(f"""
        From the following case text, list likely cited case titles as a JSON array of short strings.
        Text:
        {target_doc.page_content[:1800]}
        """).strip()
        outbound = [c.strip().strip('"') for c in (inferred or "").strip("[]").split(",") if c.strip()]

    # Best-effort cited_by
    cited_by: List[str] = []
    scan_basis = target_title or target_id
    candidates = retriever.get_relevant_documents(scan_basis)[:req.k_scan]
    for d in candidates:
        mid = _get_meta(d).get("id")
        if not mid or mid == target_id:
            continue
        cites = _get_meta(d).get("citations", []) or []
        if target_id in cites:
            cited_by.append(mid)

    return {"id": target_id, "title": target_title, "citations": outbound, "cited_by": cited_by}
