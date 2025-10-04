

\# LexChain Data Plan v1

Source: U.S. case law via CourtListener.

Topics: contract, privacy, appeal. Size: ~250–300 opinions (2010–2025).

Fields: id, title, court, jurisdiction, date, docket, parties, citations, url, summary, plain\_text.

Flow: raw JSONL → normalize → dedupe → (later) chunk + embed on Render → FAISS index.

API surface (planned): /cases/search, /cases/{id}, /ingest, /answer (answers with citations).



