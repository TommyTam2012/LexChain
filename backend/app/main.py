# ==========================================================
# LexChain FastAPI Main — routers: cases, ingest, qa
# ==========================================================
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import os

# Routers (relative imports because we are in backend/app/)
from .routers import cases
from .routers import ingest
from .routers import qa

APP_NAME = "LexChain API"
APP_VERSION = "0.1.0"

def get_allowed_origins():
    env = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000"
    )
    return [o.strip() for o in env.split(",") if o.strip()]

app = FastAPI(title=APP_NAME, version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(cases.router)
app.include_router(ingest.router)
app.include_router(qa.router)

# Root → docs
@app.get("/")
def root():
    return RedirectResponse(url="/docs")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/version")
def version():
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "env": os.getenv("LEXCHAIN_ENV", "dev")
    }
