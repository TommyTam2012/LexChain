from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .shared import load_or_create_vectorstore, save_vectorstore, get_memory_path


router = APIRouter()


class AnchorPayload(BaseModel):
    topic: str = Field(..., description="Canonical topic key for this memory anchor")
    summary: str = Field(..., description="Short synthesis you want to remember")
    source_case: Optional[str] = Field(None, description="Case ID or citation this anchor is derived from")


@router.get("/health")
def health():
    return {"status": "ok", "path": get_memory_path()}


@router.post("/anchor")
def create_anchor(payload: AnchorPayload):
    """
    Create/append a memory anchor into the FAISS memory index.
    - Embeds the payload into the memory store
    - Persists to LEXCHAIN_MEMORY_PATH (default: ./data/memory/faiss_memory_v1)
    """
    text = f"[{payload.topic}] {payload.summary}"
    metadata = {
        "topic": payload.topic,
        "source_case": payload.source_case or "",
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "type": "memory_anchor",
    }

    try:
        vs = load_or_create_vectorstore()
        vs.add_texts(texts=[text], metadatas=[metadata])
        saved_path = save_vectorstore(vs)
        return {
            "ok": True,
            "message": "Anchor stored",
            "memory_path": saved_path,
            "anchor": metadata,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store anchor: {e}")
