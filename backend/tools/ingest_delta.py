# ==========================================================
# LexChain — Delta Ingest Tool
# ==========================================================
# Purpose:
#   Detect new or updated HKLII case JSONs since last ingest
#   and merge them into the existing FAISS index.
# ==========================================================

import os, json, glob, hashlib
from pathlib import Path
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ---------- Config ----------
DATA_DIR = Path("../data/hklii_cache").resolve()
INDEX_PATH = Path(os.getenv("LEXCHAIN_INDEX_PATH", "./data/indexes/faiss_v1")).resolve()
MODEL_NAME = os.getenv("LEXCHAIN_EMBED_MODEL", "text-embedding-3-large")
META_FILE = INDEX_PATH / "metadata.json"

# ---------- Helpers ----------
def hash_text(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()

def load_metadata():
    if META_FILE.exists():
        with open(META_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_metadata(meta):
    META_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

# ---------- Step 1: Setup ----------
print(f"[i] Using data from: {DATA_DIR}")
print(f"[i] Index path: {INDEX_PATH}")
print(f"[i] Model: {MODEL_NAME}")

old_meta = load_metadata()
new_meta = {}
splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=150)
embeddings = OpenAIEmbeddings(model=MODEL_NAME)

# ---------- Step 2: Detect new or changed files ----------
case_files = sorted(DATA_DIR.glob("case_*.json"))
new_files = []

for fp in case_files:
    with open(fp, "r", encoding="utf-8") as f:
        j = json.load(f)
    content = j.get("content") or ""
    if len(content) < 500:
        continue

    content_hash = hash_text(content)
    new_meta[fp.name] = content_hash

    # Compare hashes to detect new or updated cases
    if old_meta.get(fp.name) != content_hash:
        new_files.append(fp)

print(f"[i] Found {len(new_files)} new or changed case files.")

if not new_files:
    print("[✓] No new cases to ingest. FAISS index is current.")
    exit(0)

# ---------- Step 3: Load existing FAISS index ----------
if INDEX_PATH.exists():
    vs = FAISS.load_local(str(INDEX_PATH), embeddings, allow_dangerous_deserialization=True)
    print("[i] Loaded existing FAISS index.")
else:
    vs = None
    print("[i] No existing index found. Creating a new one.")

# ---------- Step 4: Build new chunks ----------
texts, metas = [], []
for fp in new_files:
    with open(fp, "r", encoding="utf-8") as f:
        j = json.load(f)
    chunks = splitter.split_text(j["content"])
    for c in chunks:
        texts.append(c)
        metas.append({
            "source": j.get("url"),
            "title": j.get("title"),
            "court": j.get("court"),
            "year": j.get("year"),
            "path": fp.name
        })

print(f"[i] Prepared {len(texts)} text chunks for ingestion.")

# ---------- Step 5: Add to FAISS ----------
if vs:
    vs.add_texts(texts, metadatas=metas)
else:
    vs = FAISS.from_texts(texts, embeddings, metadatas=metas)

vs.save_local(str(INDEX_PATH))
save_metadata(new_meta)

print(f"[✓] Delta ingest complete. Index updated → {INDEX_PATH}")
print(f"[✓] Metadata saved → {META_FILE}")
