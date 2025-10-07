# ==========================================================
# LexChain – Phase 3.4: Intelligent Legal Reasoning
# ==========================================================
# Captain's Log:
# Purpose: Provide endpoints for legal case retrieval, comparison,
# summarization, and analytical reasoning using FAISS + GPT.
# Behavior: Maintains backward compatibility with previous phases.
# ==========================================================

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA

# ----------------------------------------------------------
# Router Initialization
# ----------------------------------------------------------
router = APIRouter(prefix="/cases", tags=["Cases"])

# ----------------------------------------------------------
# FAISS Helper Functions
# ----------------------------------------------------------
def _get_index_path() -> str:
    """Return FAISS index path from env var or default."""
    return os.getenv("LEXCHAIN_INDEX_PATH", "./data/indexes/faiss_v1")

def _faiss_files_exist(p: str) -> bool:
    """Check that FAISS index + pickle exist."""
    return os.path.exists(os.path.join(p, "index.faiss")) and os.path.exists(os.path.join(p, "index.pkl"))

def _load_vectorstore(idx_path: str, embed_model: str):
    """Load FAISS vectorstore safely."""
    embeddings = OpenAIEmbeddings(model=embed_model)
    vs = FAISS.load_local(idx_path, embeddings, allow_dangerous_deserialization=True)
    return vs

def _extract_id_title(doc) -> tuple[str, str]:
    """Extract ID and Title from FAISS doc metadata."""
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
#  /cases/semantic – Semantic Search
# ==========================================================
@router.get("/semantic")
def semantic_search(query: str = Query(..., description="Search phrase or topic")):
    """Retrieve similar cases via semantic FAISS search."""
    retriever = _get_retriever()
    docs = retriever.get_relevant_documents(query)
    if not docs:
        return {"query": query, "results": []}

    results = []
    for doc in docs:
        cid, title = _extract_id_title(doc)
        results.append({
            "id": cid,
            "title": title,
            "snippet": doc.page_content[:300]
        })
    return {"query": query, "results": results}

# ==========================================================
#  /cases/compare – Compare Two Cases
# ==========================================================
@router.post("/compare")
def compare_cases(request: CompareRequest):
    """Compare reasoning or holdings of two cases using GPT."""
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
    Compare the following two cases and summarize differences and similarities
    in their legal reasoning and holdings.

    CASE A ({request.case_a}):
    {text_a[:2000]}

    CASE B ({request.case_b}):
    {text_b[:2000]}

    Provide a concise comparison.
    """

    answer = llm.predict(prompt)
    return {
        "case_a": request.case_a,
        "case_b": request.case_b,
        "comparison": answer
    }

# ==========================================================
#  /cases/summarize – GPT Summary
# ==========================================================
@router.get("/summarize")
def summarize_case(query: str = Query(..., description="Case name or topic")):
    """Summarize the most relevant case."""
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
#  /cases/analyze – Phase 3.4 Intelligent Reasoning
# ==========================================================
@router.get("/analyze")
def analyze_case(query: str = Query(..., description="Search term or legal issue")):
    """
    Analyze case content to extract structured legal reasoning.
    Returns: Issue, Holding, and Precedent Strength.
    """
    # Captain's Log:
    # Purpose: Leverage FAISS + GPT to reason over top documents.
    # Behavior: Synthesizes structured insights (issue, holding, precedent strength).
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
    Analyze the following case passage and extract the following fields in JSON:

    {{
      "issue": "What legal question the court addressed",
      "holding": "How the court resolved it",
      "precedent_strength": "High / Medium / Low based on its authority"
    }}

    Case: {title}
    Text:
    {content}
    """

    analysis = llm.predict(prompt)
    return {
        "id": cid,
        "title": title,
        "analysis": analysis.strip()
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
# ==========================================================
