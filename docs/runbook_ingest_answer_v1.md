\# LexChain Runbook — Ingest \& Answer (v1)



\## Pre-flight

\- \[ ] Backend running at http://127.0.0.1:8000/health → OK

\- \[ ] Frontend running at http://localhost:3000 → loads



\## Raw data (seed)

\- \[ ] data/raw/contract\_raw.jsonl → ≥1 line

\- \[ ] data/raw/privacy\_raw.jsonl → ≥1 line

\- \[ ] data/raw/appeal\_raw.jsonl → ≥1 line



\## Normalize (target)

\- Output: data/normalized/cases\_normalized.jsonl

\- Keep fields: id, title, court, jurisdiction, date, docket, parties\[], url, citations\[], summary, plain\_text

\- Dedup: same docket OR same (title + date) → keep richer text



\## Chunking (decision)

\- Size ≈ 1200 tokens, overlap ≈ 150

\- chunk\_id = {case\_id}#{start\_idx}-{end\_idx}

\- Attach meta: { id, title, court, date, url, citations }



\## Embeddings \& Index (plan)

\- Embeddings: OpenAI text-embedding-3-small (1536-d)

\- Index: FAISS (cosine via L2 norm) at data/indexes/faiss\_v1/

\- Build on Render (avoid Windows FAISS issues)



\## Endpoints (contract)

\- GET /cases/search?q=… → list CaseSummary

\- GET /cases/{id} → CaseFull (optionally include\_text)

\- POST /ingest → load normalized JSONL, (re)build index, return counts

\- POST /answer → {question, filters} → {answer, citations\[]}



\## QA seeds (quick checks)

\- data/samples/qa.jsonl has 3 lines:

&nbsp; - contractual damages → us-2011-scotus-concepcion

&nbsp; - warrantless search → us-2014-scotus-riley

&nbsp; - affirmed in part → us-2023-9th-epic-apple



\## Troubleshooting

\- “Failed to fetch” → frontend can’t reach API; confirm .env points to http://localhost:8000 and restart `npm run dev`.

\- HTTP 500 → check Uvicorn logs (Terminal 1).

\- CORS → allow http://localhost:3000 and http://127.0.0.1:3000.



