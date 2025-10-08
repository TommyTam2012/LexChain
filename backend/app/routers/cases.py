# ==========================================================
# LexChain – Phase 3.5: Multi-Case Synthesis / Chain of Precedents
# ==========================================================
# Captain's Log:
# Purpose: Extend LexChain to analyze multiple cases jointly.
# Behavior: Synthesizes shared issues, alignments, and conflicts
#            using FAISS retrieval + GPT reasoning.
# ==========================================================

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any
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

def _extract_id_title(doc) -> tuple[str, str]:
    meta = getattr(doc, "metadata", {}) or {}
    return meta.get("id", "unknown"), meta.get("title", "Untitled Case")

# ----------------------------------------------------------
# Models
# ----------------------------------------------------------
class CaseRequest(BaseModel):
    query: str

class CompareRequest(BaseModel):
    case_a: str
    case_b: str

class SynthesizeRequest(BaseModel):
    queries: List[str]

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

# ==========================================================
# /cases/semantic – Semantic Search
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
# /cases/compare – Compare Two Cases
# ==========================================================
@router.post("/compare")
def compare_cases(request: CompareRequest):
    retriever = _get_retriever()
    llm = _get_chat_model()

    def _get_case_text(cid: str) -> str:
        docs = retriever.get_relevant_documents(cid)
        if not docs:
            raise HTTPException(status_code=404, detail=f"Case not found: {cid}")
        return docs[0].page_content

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
# /cases/summarize – GPT Summary
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
# /cases/synthesize – Phase 3.5 Multi-Case Reasoning
# ==========================================================
@router.post("/synthesize")
def synthesize_cases(request: SynthesizeRequest):
    """
    Combine reasoning from multiple related cases to identify
    common issues, alignments, conflicts, and overall precedent trend.
    """
    # Captain's Log:
    # Purpose: Provide higher-order reasoning across multiple precedents.
    retriever = _get_retriever(k=2)
    llm = _get_chat_model(temp=0)

    all_texts = []
    summaries = []

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
# ==========================================================
