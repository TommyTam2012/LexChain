# ==========================================================
# LexChain — HKLII Vectorization Ingest Tool
# ==========================================================
# Purpose: Convert cached HKLII case JSON files into
# searchable FAISS embeddings for LexChain.
# ==========================================================

import os, json, glob
from pathlib import Path
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ---------- Config ----------
DATA_DIR = Path("../data/hklii_cache").resolve()
INDEX_PATH = Path(os.getenv("LEXCHAIN_INDEX_PATH", "./data/indexes/faiss_v1")).resolve()
MODEL_NAME = os.getenv("LEXCHAIN_EMBED_MODEL", "text-embedding-3-large")

# ---------- Step 1: Verify Inputs ----------
if not DATA_DIR.exists():
    raise FileNotFoundError(f"HKLII cache folder not found: {DATA_DIR}")

INDEX_PATH.mkdir(parents=True, exist_ok=True)
print(f"[i] Using data from: {DATA_DIR}")
print(f"[i] Saving index to: {INDEX_PATH}")
print(f"[i] Embedding model: {MODEL_NAME}")

# ---------- Step 2: Prepare Splitter ----------
splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=150)

# ---------- Step 3: Gather Cases ----------
case_files = sorted(DATA_DIR.glob("case_*.json"))
if not case_files:
    raise FileNotFoundError("No case_*.json files found in hklii_cache folder.")
print(f"[i] Found {len(case_files)} case files.")

texts, metas = [], []

for fp in case_files:
    try:
        with open(fp, "r", encoding="utf-8") as f:
            j = json.load(f)
        content = j.get("content") or ""
        if len(content) < 500:
            continue  # skip short ones
        chunks = splitter.split_text(content)
        for c in chunks:
            texts.append(c)
            metas.append({
                "source": j.get("url"),
                "title": j.get("title"),
                "court": j.get("court"),
                "year": j.get("year"),
                "path": fp.name
            })
    except Exception as e:
        print(f"[x] Failed to read {fp.name}: {e}")

print(f"[i] Total text chunks prepared: {len(texts)}")

# ---------- Step 4: Build & Save FAISS ----------
if not texts:
    raise RuntimeError("No valid text chunks to index.")

embeddings = OpenAIEmbeddings(model=MODEL_NAME)
vs = FAISS.from_texts(texts, embeddings, metadatas=metas)
vs.save_local(str(INDEX_PATH))

print(f"[✓] Vector index successfully built and saved → {INDEX_PATH}")
print(f"[✓] Total chunks indexed: {len(texts)}")
print(f"[✓] All systems green. LexChain memory ready.")

