# ==========================================================
# LexChain – Memory Shared Utilities
# ==========================================================
# Handles FAISS vectorstore loading and OpenAI embeddings
# for the LexChain memory module.
# ==========================================================
import os
from fastapi import HTTPException
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

def _get_memory_path() -> str:
    """Get FAISS memory index path."""
    return os.getenv("LEXCHAIN_MEMORY_PATH", "./data/memory/faiss_memory_v1")

def _faiss_files_exist(p: str) -> bool:
    """Check that memory FAISS index files exist."""
    return os.path.exists(os.path.join(p, "index.faiss")) and os.path.exists(os.path.join(p, "index.pkl"))

def _load_memory_vectorstore(idx_path: str, embed_model: str):
    """Load FAISS memory vectorstore safely."""
    embeddings = OpenAIEmbeddings(model=embed_model)
    return FAISS.load_local(idx_path, embeddings, allow_dangerous_deserialization=True)

def _get_embeddings_model() -> str:
    return os.getenv("LEXCHAIN_EMBED_MODEL", "text-embedding-3-small")
