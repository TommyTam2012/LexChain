from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from .shared import (
    _get_retriever, _get_chat_model, _get_meta,
    _find_doc_by_id
)

router = APIRouter()

class GraphRequest(BaseModel):
    ids: Optional[List[str]] = None
    queries: Optional[List[str]] = None
    k_per_query: int = 3
    include_inferred: bool = False

def _node_from_doc(d) -> Dict[str, Any]:
    m = _get_meta(d)
    return {
        "id": m.get("id", "unknown"),
        "label": m.get("title", "Untitled Case"),
        "court": m.get("court"),
        "date": m.get("date"),
    }

@router.post("/graph")
def citation_graph(req: GraphRequest):
    retriever = _get_retriever(k=max(3, req.k_per_query))
    llm = _get_chat_model(temp=0)

    seed_docs = []
    seen_ids = set()

    if req.ids:
        for cid in req.ids:
            d = _find_doc_by_id(retriever, cid)
            if d:
                did = _get_meta(d).get("id")
                if did and did not in seen_ids:
                    seed_docs.append(d); seen_ids.add(did)

    if req.queries:
        for q in req.queries:
            docs = retriever.get_relevant_documents(q)[:req.k_per_query]
            for d in docs:
                did = _get_meta(d).get("id")
                if did and did not in seen_ids:
                    seed_docs.append(d); seen_ids.add(did)

    if not seed_docs:
        raise HTTPException(status_code=404, detail="No seed cases found for graph.")

    nodes = [_node_from_doc(d) for d in seed_docs]
    id_to_doc = { _get_meta(d).get("id"): d for d in seed_docs }

    edges: List[Dict[str, Any]] = []
    for d in seed_docs:
        src_id = _get_meta(d).get("id")
        if not src_id:
            continue
        cites = _get_meta(d).get("citations", []) or []
        for tgt in cites:
            if tgt not in id_to_doc:
                resolved = _find_doc_by_id(retriever, tgt)
                if resolved:
                    nodes.append(_node_from_doc(resolved))
                    id_to_doc[_get_meta(resolved).get("id")] = resolved
            edges.append({"source": src_id, "target": tgt, "type": "cites"})

    if req.include_inferred:
        for d in seed_docs:
            src_id = _get_meta(d).get("id")
            if not src_id:
                continue
            inferred = llm.predict(f"""
            From the following case text, list likely cited case titles as a JSON array of short strings.
            Text:
            {d.page_content[:1600]}
            """).strip()
            guesses = [c.strip().strip('"') for c in (inferred or "").strip("[]").split(",") if c.strip()]
            for guess in guesses[:5]:
                hits = retriever.get_relevant_documents(guess)
                if not hits:
                    continue
                tgt_id = _get_meta(hits[0]).get("id")
                if not tgt_id:
                    continue
                if tgt_id not in id_to_doc:
                    nodes.append(_node_from_doc(hits[0]))
                    id_to_doc[tgt_id] = hits[0]
                edges.append({"source": src_id, "target": tgt_id, "type": "inferred"})

    return {"nodes": nodes, "edges": edges}
