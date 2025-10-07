# ==========================================================
# /ingest — build FAISS index from normalized JSONL
# ==========================================================
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
import os, json

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

router = APIRouter(prefix="/ingest", tags=["Ingest"])

DATA_ROOT = os.getenv("LEXCHAIN_DATA_PATH", "./data")
NORMALIZED_FILE = os.path.join(DATA_ROOT, "normalized", "cases_normalized.jsonl")
INDEX_PATH = os.getenv("LEXCHAIN_INDEX_PATH", "./data/indexes/faiss_v1")

class IngestResult(BaseModel):
    ok: bool
    count: int
    index_path: str
    note: str

def _load_records() -> List[Dict[str, Any]]:
    if not os.path.exists(NORMALIZED_FILE):
        return []
    out: List[Dict[str, Any]] = []
    with open(NORMALIZED_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out

@router.post("", response_model=IngestResult)
def build_index():
    """
    Build/update FAISS index at LEXCHAIN_INDEX_PATH.
    Uses OpenAI text-embedding-3-small for title+summary fields.
    """
    records = _load_records()
    if not records:
        raise HTTPException(status_code=400, detail="No normalized records found to ingest.")

    # Prepare texts + metadatas
    texts = []
    metadatas = []
    for r in records:
        text = f"{r.get('title','')}\n\n{r.get('summary','')}".strip()
        if not text:
            # Skip empty rows
            continue
        texts.append(text)
        metadatas.append({
            "id": r.get("id"),
            "title": r.get("title"),
            "url": r.get("url"),
            "court": r.get("court"),
            "date": r.get("date"),
        })

    if not texts:
        raise HTTPException(status_code=400, detail="No valid texts to index.")

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = FAISS.from_texts(texts=texts, embedding=embeddings, metadatas=metadatas)

    os.makedirs(INDEX_PATH, exist_ok=True)
    vectorstore.save_local(INDEX_PATH)

    return IngestResult(
        ok=True,
        count=len(texts),
        index_path=INDEX_PATH,
        note="FAISS updated successfully."
    )
