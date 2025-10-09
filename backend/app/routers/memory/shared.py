import os
from datetime import datetime
from typing import Optional

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS


MEM_ENV_PATH = "LEXCHAIN_MEMORY_PATH"
MEM_DEFAULT_PATH = "./data/memory/faiss_memory_v1"
EMB_ENV_MODEL = "LEXCHAIN_EMBED_MODEL"
EMB_DEFAULT_MODEL = "text-embedding-3-small"


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
    Loads an existing FAISS store from `path` or creates a new, empty one.
    """
    path = path or get_memory_path()
    os.makedirs(path, exist_ok=True)

    embeddings = get_embeddings()
    if _faiss_files_exist(path):
        # allow_dangerous_deserialization: safe here because we read our own files
        return FAISS.load_local(path, embeddings, allow_dangerous_deserialization=True)
    else:
        # Create an empty store by adding a trivial placeholder, then immediately delete it.
        vs = FAISS.from_texts(texts=["__init_anchor__"], embedding=embeddings, metadatas=[{"_created": datetime.utcnow().isoformat()}])
        # Remove placeholder entry from the index’s docstore
        vs.docstore._dict.pop(list(vs.docstore._dict.keys())[0], None)
        return vs


def save_vectorstore(vs: FAISS, path: Optional[str] = None) -> str:
    path = path or get_memory_path()
    os.makedirs(path, exist_ok=True)
    vs.save_local(path)
    return path
