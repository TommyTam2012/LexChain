from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.docstore.document import Document
import os, json

INDEX_PATH = "./data/indexes/faiss_v1"
os.makedirs(INDEX_PATH, exist_ok=True)

# Load normalized cases (use title+summary for richer recall)
docs = []
with open("./data/normalized/cases_normalized.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        row = json.loads(line)
        text = f"{row.get('title','')}\n{row.get('summary','')}"
        docs.append(Document(page_content=text, metadata={"id": row.get("id","")}))

emb = OpenAIEmbeddings(model="text-embedding-3-small")
db = FAISS.from_documents(docs, emb)
db.save_local(INDEX_PATH)
print("✅ FAISS saved to", INDEX_PATH)
