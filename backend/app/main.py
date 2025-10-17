# ==========================================================
# LexChain FastAPI Main (中英双语版本)
# ==========================================================
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.openapi.docs import get_swagger_ui_html

# Routers (package-relative imports from backend.app.*)
from .routers.cases import router as cases_router
from .routers import memory
from .routers.hklii import router as hklii_router  # ✅ HKLII adapter router
from .routers.hklii_gcse import router as hklii_gcse_router  # ✅ NEW: HKLII GCSE extension router

# ----------------------------------------------------------
# 🌐 Bilingual Tag Metadata / 中英文标签说明
# ----------------------------------------------------------
TAGS_METADATA = [
    {
        "name": "cases",
        "description": "📚 案件功能 | Case utilities：语义搜索、比较、摘要、分析、综合、引注、关系图谱。",
    },
    {
        "name": "memory",
        "description": "🧠 记忆锚点 | Memory anchors：添加/查询开发中的记忆向量。",
    },
    {
        "name": "hklii",
        "description": "🔎 HKLII 适配器 | HKLII adapter：与 HKLII 搜索/数据对接。",
    },
    {
        "name": "hklii_gcse",
        "description": "📖 HKLII GCSE 扩展接口 | HKLII GCSE extension interface。",
    },
]

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
    version="0.0.1",
    openapi_tags=TAGS_METADATA,
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
@app.get("/", summary="重定向至 Swagger 文档 | Redirect to Swagger Docs")
def root():
    """重定向至 Swagger 文档界面 / Redirect to Swagger UI"""
    return RedirectResponse(url="/docs")


@app.get("/health", summary="健康检查 | Health Check")
def health():
    """健康检查 (Health Check)：用于检测服务是否正常运行"""
    return {"status": "ok"}


@app.get("/version", summary="版本信息 | Version Info")
def version():
    """版本信息 (Version Info)：显示当前 API 名称与版本"""
    return {"name": "LexChain API / 法律链接口", "version": "0.0.1"}

# ----------------------------------------------------------
# Mount Routers
# ----------------------------------------------------------
app.include_router(cases_router)
app.include_router(memory.router)
app.include_router(hklii_router)        # ✅ HKLII Search Proxy
app.include_router(hklii_gcse_router)   # ✅ HKLII GCSE Integration

# ----------------------------------------------------------
# Swagger 中文界面增强脚本 / Chinese UI Patch
# ----------------------------------------------------------
ZH_PATCH_SCRIPT = r"""
<script>
(function(){
  const dict = {
    "Schemas":"模式","Models":"模型","Try it out":"试一试","Execute":"执行",
    "Clear":"清除","Parameters":"参数","Request body":"请求体","Responses":"响应",
    "Description":"描述","Example Value":"示例值","Schema":"模式","Authorize":"授权",
    "Server":"服务器","Hide":"隐藏","Show":"显示","Cancel":"取消",
    "No content":"无内容","Request samples":"请求示例","Response samples":"响应示例"
  };
  function translateNode(node){
    if(node.nodeType===Node.TEXT_NODE){
      const t=node.nodeValue.trim();
      if(dict[t]) node.nodeValue=node.nodeValue.replace(t, dict[t]);
    } else if(node.nodeType===Node.ELEMENT_NODE && node.childNodes){
      node.childNodes.forEach(translateNode);
    }
  }
  const mo=new MutationObserver(()=>translateNode(document.body));
  mo.observe(document.body,{childList:true,subtree:true,characterData:true});
  window.addEventListener('load', ()=>translateNode(document.body));
})();
</script>
"""

@app.get("/docs", include_in_schema=False, summary="Swagger 文档页面 | Swagger Docs Page")
def custom_docs():
    """Swagger 文档页面 (含中文界面增强) / Swagger Docs page with Chinese UI patch"""
    ui = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="LexChain API 文档 / Docs",
        swagger_js_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css",
        swagger_favicon_url="https://unpkg.com/swagger-ui-dist@5/favicon-32x32.png",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": 1,
            "docExpansion": "list",
            "displayRequestDuration": True,
        },
    )
    html = ui.body.decode("utf-8").replace("</body>", f"{ZH_PATCH_SCRIPT}</body>")
    return HTMLResponse(content=html)

# ----------------------------------------------------------
# Captain’s Note
# ----------------------------------------------------------
# ✅ Ready for Step 4.0 — HKLII GCSE integration smoke test
# Swagger: http://127.0.0.1:8000/docs
# Test endpoint: /hklii_gcse/search?q=arbitration&page=1&page_size=5
# ----------------------------------------------------------
