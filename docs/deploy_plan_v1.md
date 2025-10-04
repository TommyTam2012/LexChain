\# Deploy Plan v1 (Render + Vercel)



\## Backend — Render (lexchain-api)

\- Runtime: Python 3.x

\- Start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT --app-dir ./backend

\- Health check path: /health

\- Disk: persistent /data (for FAISS index)

\- Env vars:

&nbsp; - OPENAI\_API\_KEY= (later)

&nbsp; - CORS\_ALLOWED\_ORIGINS=https://<your-vercel-domain>,http://localhost:3000

&nbsp; - LEXCHAIN\_INDEX\_PATH=/data/indexes/faiss\_v1

&nbsp; - LEXCHAIN\_ENV=prod

\- Notes: Render sets $PORT automatically; keep CORS tight to Vercel domain.



\## Frontend — Vercel (lexchain-frontend)

\- Framework: Next.js (App Router)

\- Build: default (npm install \&\& next build)

\- Env var:

&nbsp; - NEXT\_PUBLIC\_API\_BASE=https://<your-render-service>.onrender.com

\- Preview branches: point NEXT\_PUBLIC\_API\_BASE to the same Render API (or a staging API).



\## Post-deploy smoke test

1\) Backend: https://<render>/health → {"status":"ok"}

2\) Frontend: https://<vercel>/ → click \*\*Check Health\*\* and \*\*Get Version\*\*

3\) Search box: "contract", "privacy", "appeal" should return lists.

4\) Banner note: “Educational demo — Not legal advice.”



\## Rollback \& Notes

\- Keep README “two terminals” instructions for local dev.

\- Index path lives under /data; redeploy doesn’t erase persistent disk.

\- If CORS errors appear, verify CORS\_ALLOWED\_ORIGINS matches Vercel URL exactly.



