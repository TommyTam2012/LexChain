# ==========================================================
# LexChain – Phase 3.6: Citation Mapping & Graph Visualization
# ==========================================================
# Captain's Log:
# Purpose: Map how cases cite (and are cited by) each other;
#          return graph-ready JSON for visualization.
# Behavior: Uses FAISS metadata ("citations": [...]) when present;
#           optionally infers candidate links with GPT.
# ==========================================================

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Tuple
import os

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

# ----------------------------------------------------------
# Router Initialization
# ----------------------------------------------------------
router = APIRouter(prefix="/cases", tags=["Cases"])

# ----------------------------------------------------------
# FAISS Helpers
# ----------------------------------------------------------
def _get_index_path() -> str:
    return os.getenv("LEXCHAIN_INDEX_PATH", "./data/indexes/faiss_v1")

def _faiss_files_exist(p: str) -> bool:
    return os.path.exists(os.path.join(p, "index.faiss")) and os.path.exists(os.path.join(p, "index.pkl"))

def _load_vectorstore(idx_path: str, embed_model: str):
    embeddings = OpenAIEmbeddings(model=embed_model)
    return FAISS.load_local(idx_path, embeddings, allow_dangerous_deserialization=True)

def _extract_id_title(doc) -> Tuple[str, str]:
    meta = getattr(doc, "metadata", {}) or {}
    return meta.get("id", "unknown"), meta.get("title", "Untitled Case")

def _get_meta(doc) -> Dict[str, Any]:
    return getattr(doc, "metadata", {}) or {}

# ----------------------------------------------------------
# Models
# ----------------------------------------------------------
class CompareRequest(BaseModel):
    case_a: str
    case_b: str

class SynthesizeRequest(BaseModel):
    queries: List[str]

class CitationsRequest(BaseModel):
    """Lookup citations for a case by ID or by query/topic."""
    id: Optional[str] = None
    query: Optional[str] = None
    k_scan: int = 20                 # how many candidate docs to scan for cited_by
    infer: bool = False              # try GPT-based inference when metadata missing

class GraphRequest(BaseModel):
    """Build a citation graph for given case IDs or queries."""
    ids: Optional[List[str]] = None
    queries: Optional[List[str]] = None
    k_per_query: int = 3
    include_inferred: bool = False   # allow GPT to infer links when metadata lacks them

# ----------------------------------------------------------
# Utilities
# ----------------------------------------------------------
def _get_retriever(k: int = 3):
    idx_path = _get_index_path()
    if not _faiss_files_exist(idx_path):
        raise HTTPException(status_code=404, detail="FAISS index not found. Please build it first.")
    embed_model = os.getenv("LEXCHAIN_EMBED_MODEL", "text-embedding-3-small")
    vectorstore = _load_vectorstore(idx_path, embed_model)
    return vectorstore.as_retriever(search_kwargs={"k": k})

def _get_chat_model(temp: float = 0):
    model_name = os.getenv("LEXCHAIN_CHAT_MODEL", "gpt-4o-mini")
    return ChatOpenAI(model=model_name, temperature=temp)

def _find_doc_by_id(retriever, case_id: str, fallback_k: int = 5):
    """
    Best-effort: search by ID first (exact match unlikely in vector space),
    so we also try the ID and pieces of it, then fall back to top-k and
    pick the doc whose metadata id matches when possible.
    """
    candidates = retriever.get_relevant_documents(case_id)
    for d in candidates:
        if _get_meta(d).get("id") == case_id:
            return d
    # Fallback scan: ask for some generic docs and try to match by id in metadata
    more = retriever.get_relevant_documents(case_id.replace("_", " ")[:64])
    for d in more:
        if _get_meta(d).get("id") == case_id:
            return d
    if candidates:
        return candidates[0]
    # final fallback: broad query "case" to get something
    broad = retriever.get_relevant_documents("case law " + case_id)[:fallback_k]
    return broad[0] if broad else None

# ==========================================================
# /cases/semantic – Semantic Search (3.1)
# ==========================================================
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

# ==========================================================
# /cases/compare – Compare Two Cases (3.2)
# ==========================================================
@router.post("/compare")
def compare_cases(request: CompareRequest):
    retriever = _get_retriever()
    llm = _get_chat_model()

    def _get_case_text(cid: str) -> str:
        doc = _find_doc_by_id(retriever, cid) or retriever.get_relevant_documents(cid)[0]
        if not doc:
            raise HTTPException(status_code=404, detail=f"Case not found: {cid}")
        return doc.page_content

    text_a = _get_case_text(request.case_a)
    text_b = _get_case_text(request.case_b)

    prompt = f"""
    Compare the following two cases and summarize similarities and differences
    in their legal reasoning and holdings.

    CASE A ({request.case_a}):
    {text_a[:2000]}

    CASE B ({request.case_b}):
    {text_b[:2000]}

    Provide a concise comparison.
    """
    answer = llm.predict(prompt)
    return {"case_a": request.case_a, "case_b": request.case_b, "comparison": answer}

# ==========================================================
# /cases/summarize – GPT Summary (3.3)
# ==========================================================
@router.get("/summarize")
def summarize_case(query: str = Query(..., description="Case name or topic")):
    retriever = _get_retriever(k=1)
    llm = _get_chat_model()
    docs = retriever.get_relevant_documents(query)
    if not docs:
        raise HTTPException(status_code=404, detail="No case found to summarize.")
    case_text = docs[0].page_content[:3000]
    cid, title = _extract_id_title(docs[0])

    prompt = f"Summarize the key issue and holding of the case titled '{title}'.\n\n{case_text}"
    summary = llm.predict(prompt)
    return {"id": cid, "title": title, "summary": summary}

# ==========================================================
# /cases/analyze – Structured Reasoning (3.4)
# ==========================================================
@router.get("/analyze")
def analyze_case(query: str = Query(..., description="Search term or legal issue")):
    retriever = _get_retriever(k=2)
    llm = _get_chat_model()

    docs = retriever.get_relevant_documents(query)
    if not docs:
        raise HTTPException(status_code=404, detail="No related cases found for analysis.")

    top_doc = docs[0]
    cid, title = _extract_id_title(top_doc)
    content = top_doc.page_content[:4000]

    prompt = f"""
    You are a legal analysis assistant.
    Analyze the following case passage and extract:

    {{
      "issue": "Legal question addressed",
      "holding": "Court's resolution",
      "precedent_strength": "High / Medium / Low"
    }}

    Case: {title}
    Text:
    {content}
    """
    analysis = llm.predict(prompt)
    return {"id": cid, "title": title, "analysis": analysis.strip()}

# ==========================================================
# /cases/synthesize – Multi-Case Reasoning (3.5)
# ==========================================================
@router.post("/synthesize")
def synthesize_cases(request: SynthesizeRequest):
    """
    Combine reasoning from multiple related cases to identify
    common issues, alignments, conflicts, and overall precedent trend.
    """
    retriever = _get_retriever(k=2)
    llm = _get_chat_model(temp=0)

    all_texts: List[str] = []
    summaries: List[str] = []

    for query in request.queries:
        docs = retriever.get_relevant_documents(query)
        if not docs:
            continue
        doc = docs[0]
        cid, title = _extract_id_title(doc)
        summaries.append(f"{title} ({cid})")
        all_texts.append(f"Case: {title}\n\n{doc.page_content[:1500]}")

    if not all_texts:
        raise HTTPException(status_code=404, detail="No cases found for synthesis.")

    joined_text = "\n\n---\n\n".join(all_texts)
    prompt = f"""
    You are LexChain, an AI legal analyst.
    Given several related cases, produce a structured synthesis describing:

    {{
      "common_issue": "shared legal question among the cases",
      "alignments": "which cases reach similar holdings",
      "conflicts": "which cases diverge or conflict",
      "precedent_trend": "overall trend (strengthening / diverging)",
      "summary": "concise narrative of the combined reasoning"
    }}

    Analyze the following case materials:
    {joined_text}
    """

    result = llm.predict(prompt)
    return {
        "queries": request.queries,
        "cases_considered": summaries,
        "synthesis": result.strip()
    }

# ==========================================================
# /cases/citations – Citation Lookup (3.6)
# ==========================================================
@router.post("/citations")
def citations_lookup(req: CitationsRequest):
    """
    Return outbound citations and best-effort 'cited_by' set.
    Uses metadata['citations'] if present; optionally infers with GPT.
    """
    retriever = _get_retriever(k=3)
    llm = _get_chat_model(temp=0)

    # Resolve target document
    target_doc = None
    target_id = None
    target_title = None

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

    # Optional GPT inference for missing citations
    if req.infer and not outbound:
        inferred = llm.predict(f"""
        From the following case text, list likely cited case titles as a JSON array of short strings.
        Text:
        {target_doc.page_content[:1800]}
        """).strip()
        outbound = [c.strip() for c in (inferred or "").strip("[]").split(",") if c.strip()]
        # Note: these may be titles; frontend can use semantic search to resolve to IDs

    # Best-effort cited_by: scan k candidates and check metadata.citations includes our target_id
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

    return {
        "id": target_id,
        "title": target_title,
        "citations": outbound,     # may be IDs or titles depending on your ingest metadata
        "cited_by": cited_by
    }

# ==========================================================
# /cases/graph – Citation Graph (3.6)
# ==========================================================
@router.post("/graph")
def citation_graph(req: GraphRequest):
    """
    Build a citation graph for given case IDs or queries.
    Returns nodes (id,label,court) and edges (source->target).
    """
    retriever = _get_retriever(k=max(3, req.k_per_query))
    llm = _get_chat_model(temp=0)

    # Collect seed documents from ids and/or queries
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

    # Build node list
    def node_from_doc(d) -> Dict[str, Any]:
        m = _get_meta(d)
        return {
            "id": m.get("id", "unknown"),
            "label": m.get("title", "Untitled Case"),
            "court": m.get("court"),
            "date": m.get("date"),
        }

    nodes = [node_from_doc(d) for d in seed_docs]
    id_to_doc = { _get_meta(d).get("id"): d for d in seed_docs }

    # Build edges from explicit metadata citations
    edges: List[Dict[str, Any]] = []
    for d in seed_docs:
        src_id = _get_meta(d).get("id")
        if not src_id:
            continue
        cites = _get_meta(d).get("citations", []) or []
        for tgt in cites:
            # If target not in graph yet, try to resolve it to a doc (optional)
            if tgt not in id_to_doc:
                resolved = _find_doc_by_id(retriever, tgt)
                if resolved:
                    nodes.append(node_from_doc(resolved))
                    id_to_doc[_get_meta(resolved).get("id")] = resolved
            edges.append({"source": src_id, "target": tgt, "type": "cites"})

    # Optional: infer additional links if metadata is sparse
    if req.include_inferred:
        # Use GPT to guess referenced case titles/IDs from text; map them via semantic search
        for d in seed_docs:
            src_id = _get_meta(d).get("id")
            if not src_id:
                continue
            inferred = llm.predict(f"""
            From the following case text, list likely cited case titles as a JSON array of short strings.
            Text:
            {d.page_content[:1600]}
            """).strip()

            # Parse crude JSON array
            raw_items = [c.strip().strip('"') for c in (inferred or "").strip("[]").split(",") if c.strip()]
            for guess in raw_items[:5]:
                # Resolve guess to an id by semantic search
                hits = retriever.get_relevant_documents(guess)
                if not hits:
                    continue
                tgt_id = _get_meta(hits[0]).get("id")
                if not tgt_id:
                    continue
                if tgt_id not in id_to_doc:
                    nodes.append(node_from_doc(hits[0]))
                    id_to_doc[tgt_id] = hits[0]
                edges.append({"source": src_id, "target": tgt_id, "type": "inferred"})

    return {
        "nodes": nodes,
        "edges": edges
    }

# ==========================================================
# Captain's Test Commands
# ==========================================================
# Run locally:
# uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
#
# Swagger Tests:
# /cases/semantic?query=arbitration
# /cases/compare { "case_a": "us-2011-scotus-concepcion", "case_b": "us-2014-scotus-riley" }
# /cases/summarize?query=cellphone privacy
# /cases/analyze?query=class action waiver
# /cases/synthesize { "queries": ["arbitration class action", "employment arbitration"] }
# /cases/citations { "id": "us-2011-scotus-concepcion", "k_scan": 20, "infer": true }
# /cases/graph { "ids": ["us-2011-scotus-concepcion"], "queries": ["arbitration"], "k_per_query": 2, "include_inferred": false }
# ==========================================================
