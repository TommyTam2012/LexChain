import os
from datetime import datetime
from typing import Optional

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

MEM_ENV_PATH = "LEXCHAIN_MEMORY_PATH"
MEM_DEFAULT_PATH = "./data/memory/faiss_memory_v1"
EMB_ENV_MODEL = "LEXCHAIN_EMBED_MODEL"
EMB_DEFAULT_MODEL = "text-embedding-3-small"

# Constant marker to identify the bootstrap doc we keep in the index
_PLACEHOLDER_TEXT = "__lexchain_memory_bootstrap__"
_PLACEHOLDER_META = {"_placeholder": True, "_created": "bootstrap"}

def get_memory_path() -> str:
    return os.getenv(MEM_ENV_PATH, MEM_DEFAULT_PATH)

def get_embed_model_name() -> str:
    return os.getenv(EMB_ENV_MODEL, EMB_DEFAULT_MODEL)

def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=get_embed_model_name())

def _faiss_files_exist(path: str) -> bool:
    return (
        os.path.exists(os.path.join(path, "index.faiss"))
        and os.path.exists(os.path.join(path, "index.pkl"))
    )

def load_or_create_vectorstore(path: Optional[str] = None) -> FAISS:
    """
    Loads an existing FAISS store from `path` or creates a new one with a harmless placeholder.
    We KEEP the placeholder in the store to avoid index/docstore mismatches.
    """
    path = path or get_memory_path()
    os.makedirs(path, exist_ok=True)

    embeddings = get_embeddings()
    if _faiss_files_exist(path):
        return FAISS.load_local(path, embeddings, allow_dangerous_deserialization=True)
    else:
        vs = FAISS.from_texts(
            texts=[_PLACEHOLDER_TEXT],
            embedding=embeddings,
            metadatas=[_PLACEHOLDER_META],
        )
        vs.save_local(path)
        return vs

def save_vectorstore(vs: FAISS, path: Optional[str] = None) -> str:
    path = path or get_memory_path()
    os.makedirs(path, exist_ok=True)
    vs.save_local(path)
    return path

def is_placeholder(meta: dict) -> bool:
    return bool(meta.get("_placeholder"))
