# ==========================================================
# LexChain FastAPI Main (中英双语版本)
# ==========================================================
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

# Routers (package-relative imports from backend.app.*)
from .routers.cases import router as cases_router
from .routers import memory  # mounts /memory/* endpoints

# ----------------------------------------------------------
# 🌐 Bilingual App Metadata / 中英文接口说明
# ----------------------------------------------------------
app = FastAPI(
    title="LexChain 法律链 — AI法律研究助手 (AI Legal Research Assistant)",
    description=(
        "LexChain 是一个由人工智能驱动的法律案例检索与推理系统，"
        "支持语义搜索、案例比较、摘要生成、法律推理与引用图谱可视化。\n\n"
        "LexChain is an AI-powered legal research and reasoning platform. "
        "It enables semantic retrieval, case comparison, summarization, "
        "multi-case synthesis, and citation-graph visualization."
    ),
    version="0.0.1"
)

# ----------------------------------------------------------
# CORS (adjust as needed)
# ----------------------------------------------------------
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

# ----------------------------------------------------------
# Health & Root
# ----------------------------------------------------------
@app.get("/")
def root():
    """Redirect to Swagger UI / 重定向至 Swagger 文档界面"""
    return RedirectResponse(url="/docs")

@app.get("/health")
def health():
    """健康检查 (Health Check)"""
    return {"status": "ok"}

@app.get("/version")
def version():
    """版本信息 (Version Info)"""
    return {"name": "LexChain API / 法律链接口", "version": "0.0.1"}

# ----------------------------------------------------------
# Mount Routers
# ----------------------------------------------------------
app.include_router(cases_router)
app.include_router(memory.router)

# Optional existing modules
# from .routers import ingest, qa
# app.include_router(ingest.router)
# app.include_router(qa.router)
