# ==========================================================
# /qa — lightweight semantic QA over FAISS (RAG)
# ==========================================================
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA

router = APIRouter(prefix="/qa", tags=["QA"])

INDEX_PATH = os.getenv("LEXCHAIN_INDEX_PATH", "./data/indexes/faiss_v1")
DISCLAIMER = "Educational demo — not legal advice."

# ---------- Models ----------
class Citation(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None
    score: Optional[float] = None

class AnswerResponse(BaseModel):
    query: str
    answer: str
    citations: List[Citation]
    disclaimer: str

class AskBody(BaseModel):
    query: str

def _load_faiss():
    # Return (vectorstore | None)
    if not os.path.exists(os.path.join(INDEX_PATH, "index.faiss")):
        return None
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    return FAISS.load_local(INDEX_PATH, embeddings, allow_dangerous_deserialization=True)

def _run_retrieval(query: str, k: int = 8):
    vs = _load_faiss()
    if vs is None:
        return None, []
    retriever = vs.as_retriever(search_kwargs={"k": k})
    # Compose a chain that returns source documents
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=True
    )
    result = chain.invoke({"query": query})
    answer = (result.get("result") or "").strip()
    docs = result.get("source_documents") or []
    citations: List[Citation] = []
    for d in docs:
        md = d.metadata or {}
        citations.append(Citation(
            id=md.get("id"),
            title=md.get("title"),
            url=md.get("url"),
            score=getattr(d, "score", None)
        ))
    return answer, citations

@router.get("/ask", response_model=AnswerResponse)
def ask(query: str = Query(..., description="Question for semantic QA")):
    """
    GET convenience endpoint for quick tests (Swagger-friendly).
    """
    vs = _load_faiss()
    if vs is None:
        return AnswerResponse(
            query=query,
            answer="No FAISS index found. Please POST /ingest first.",
            citations=[],
            disclaimer=DISCLAIMER
        )
    answer, citations = _run_retrieval(query)
    return AnswerResponse(
        query=query,
        answer=answer or "No answer.",
        citations=citations,
        disclaimer=DISCLAIMER
    )

@router.post("/answer", response_model=AnswerResponse)
def answer(body: AskBody):
    """
    POST endpoint returning structured answer + citations.
    """
    query = body.query
    vs = _load_faiss()
    if vs is None:
        return AnswerResponse(
            query=query,
            answer="No FAISS index found. Please POST /ingest first.",
            citations=[],
            disclaimer=DISCLAIMER
        )
    answer, citations = _run_retrieval(query)
    return AnswerResponse(
        query=query,
        answer=answer or "No answer.",
        citations=citations,
        disclaimer=DISCLAIMER
    )
