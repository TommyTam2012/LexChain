# ==========================================================
# LexChain FastAPI Main
# ==========================================================
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

# Routers
from app.routers.cases import router as cases_router
# If you have these modules already, keep them:
# from app.routers import ingest, qa

app = FastAPI(title="LexChain API", version="0.0.1")

# CORS (adjust as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health & root
@app.get("/")
def root():
    return RedirectResponse(url="/docs")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/version")
def version():
    return {"name": "LexChain API", "version": "0.0.1"}

# Mount routers
app.include_router(cases_router)
# If present in your project, keep these lines:
# app.include_router(ingest.router)
# app.include_router(qa.router)
