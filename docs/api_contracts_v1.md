# API Contracts v1

This document defines data types and endpoint request/response shapes for the LexChain demo.  
All JSON below is illustrative schema/sample, not live data.

## Types

### CaseSummary
```json
{ "id": "string", "title": "string", "court": "string", "date": "YYYY-MM-DD", "url": "string" }
```

### CaseFull
```json
{
  "id": "string",
  "title": "string",
  "court": "string",
  "date": "YYYY-MM-DD",
  "url": "string",
  "jurisdiction": "string",
  "docket": "string",
  "parties": ["string"],
  "citations": ["string"],
  "summary": "string",
  "plain_text": "string|null"
}
```

### Citation
```json
{
  "id": "string",
  "title": "string",
  "court": "string",
  "date": "YYYY-MM-DD",
  "url": "string",
  "excerpt": "string",
  "chunk_id": "string",
  "score": 0.0
}
```

## Endpoints

### GET /cases/search

**Query params**
- `q` (string, required)  
- `jurisdiction` (string, optional)  
- `court` (string, optional)  
- `from` (YYYY-MM-DD, optional)  
- `to` (YYYY-MM-DD, optional)  
- `page` (int, default 1)  
- `size` (int, default 10, max 50)

**200 Response**
```json
{
  "query": "contract",
  "count": 1,
  "items": [
    {
      "id": "us-1999-001",
      "title": "Smith v. Jones",
      "court": "U.S. Supreme Court",
      "date": "1999-06-12",
      "url": "https://..."
    }
  ],
  "page": 1,
  "size": 10
}
```

---

### GET /cases/{id}

**Query params**
- `include_text` (bool, default false)

**200 Response**
```json
{
  "case": {
    "id": "us-2014-scotus-riley",
    "title": "Riley v. California",
    "court": "Supreme Court of the United States",
    "date": "2014-06-25",
    "url": "https://...",
    "jurisdiction": "US-SCOTUS",
    "docket": "13-132",
    "parties": ["David Leon Riley", "California"],
    "citations": ["573 U.S. 373 (2014)"],
    "summary": "Police generally may not, without a warrant, search digital info on a cellphone.",
    "plain_text": null
  }
}
```

---

### POST /ingest (admin-only)

Loads normalized JSONL or inline records, then (re)builds the vector index.

**Request (jsonl_path)**
```json
{ "mode": "jsonl_path", "path": "data/normalized/cases_normalized.jsonl", "rebuild_index": true }
```

**Request (inline)**
```json
{ "mode": "inline", "records": [ { "id": "string", "title": "string" } ], "rebuild_index": false }
```

**200 Response**
```json
{
  "ingested": 275,
  "deduped": 12,
  "chunks": 1830,
  "index": {
    "id": "faiss_v1",
    "dims": 1536,
    "size": 1830,
    "path": "data/indexes/faiss_v1",
    "updated_at": "2025-10-04T09:00:00Z"
  },
  "warnings": []
}
```

---

### POST /answer

Retrieval-augmented answer with citations.

**Request**
```json
{
  "question": "What did the Supreme Court hold about cell phone searches incident to arrest?",
  "top_k": 8,
  "min_citations": 2,
  "filters": { "jurisdiction": ["US-SCOTUS"], "from": "2010-01-01", "to": "2025-12-31" },
  "max_tokens": 250
}
```

**200 Response**
```json
{
  "answer": "Educational demo — not legal advice. In Riley v. California (2014), the Court held that police generally need a warrant to search the digital contents of a cellphone seized incident to arrest.",
  "citations": [
    {
      "id": "us-2014-scotus-riley",
      "title": "Riley v. California",
      "court": "SCOTUS",
      "date": "2014-06-25",
      "url": "https://...",
      "excerpt": "Police generally may not, without a warrant...",
      "chunk_id": "us-2014-scotus-riley#12-14",
      "score": 0.82
    },
    {
      "id": "us-2011-scotus-concepcion",
      "title": "AT&T Mobility LLC v. Concepcion",
      "court": "SCOTUS",
      "date": "2011-04-27",
      "url": "https://...",
      "excerpt": "...",
      "chunk_id": "us-2011-scotus-concepcion#3-5",
      "score": 0.61
    }
  ],
  "retrieval": { "top_k": 8, "index_id": "faiss_v1", "filters_applied": { "jurisdiction": ["US-SCOTUS"] } },
  "usage": { "prompt_tokens": 0, "completion_tokens": 0 }
}
```

---

## Error shape (all endpoints)
```json
{ "error": { "code": "BAD_REQUEST", "message": "q is required" } }
```

## Notes
- Field names are stable; values above are examples.  
- Answers must include source citations.  
- **Educational demo — not legal advice.**
