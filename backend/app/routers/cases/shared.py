
# ==========================================================
# LexChain – Shared utilities for /cases module
# ==========================================================
from typing import Tuple, Dict, Any
import os

from fastapi import HTTPException
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

def _get_index_path() -> str:
    return os.getenv("LEXCHAIN_INDEX_PATH", "./data/indexes/faiss_v1")

def _faiss_files_exist(p: str) -> bool:
    return os.path.exists(os.path.join(p, "index.faiss")) and os.path.exists(os.path.join(p, "index.pkl"))

def _load_vectorstore(idx_path: str, embed_model: str):
    embeddings = OpenAIEmbeddings(model=embed_model)
    return FAISS.load_local(idx_path, embeddings, allow_dangerous_deserialization=True)

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

def _extract_id_title(doc) -> Tuple[str, str]:
    meta = getattr(doc, "metadata", {}) or {}
    return meta.get("id", "unknown"), meta.get("title", "Untitled Case")

def _get_meta(doc) -> Dict[str, Any]:
    return getattr(doc, "metadata", {}) or {}

def _find_doc_by_id(retriever, case_id: str, fallback_k: int = 5):
    # Try vector lookup by id and variations
    candidates = retriever.get_relevant_documents(case_id)
    for d in candidates:
        if _get_meta(d).get("id") == case_id:
            return d
    more = retriever.get_relevant_documents(case_id.replace("_", " ")[:64])
    for d in more:
        if _get_meta(d).get("id") == case_id:
            return d
    if candidates:
        return candidates[0]
    broad = retriever.get_relevant_documents("case law " + case_id)[:fallback_k]
    return broad[0] if broad else None
