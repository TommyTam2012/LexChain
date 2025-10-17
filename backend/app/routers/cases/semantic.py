# ==========================================================
# 案件语义搜索接口 (Case Semantic Search Endpoint)
# ==========================================================
from fastapi import APIRouter, Query
from .shared import _get_retriever, _extract_id_title

router = APIRouter()

@router.get(
    "/semantic",
    tags=["cases"],
    summary="案件语义搜索 | Case Semantic Search",
    description=(
        "使用语义向量检索（Semantic Retrieval）从案例库中查找最相关的案件与段落。\n\n"
        "Use semantic vector retrieval to find the most relevant cases and passages "
        "from the case database."
    ),
)
def semantic_search(
    query: str = Query(
        ...,
        description="查询关键词或主题（可输入中文或英文） | Search phrase or topic (in Chinese or English)"
    )
):
    """
    案件语义搜索接口 / Case Semantic Search Endpoint

    📘 功能 (Function):
    使用嵌入模型进行语义检索，根据输入的关键词或主题，从案例数据库中返回最相似的案件段落。

    ⚙️ 返回值 (Return):
    - query: 查询字符串
    - results: 匹配结果列表，每个元素包含：
        - id: 案件编号
        - title: 案件标题
        - snippet: 案件内容前300字

    English Summary:
    Performs semantic retrieval from the case database using vector embeddings.
    Returns the most relevant case IDs, titles, and snippets (first 300 chars).
    """
    retriever = _get_retriever()
    docs = retriever.get_relevant_documents(query)
    if not docs:
        return {"query": query, "results": []}

    results = []
    for doc in docs:
        cid, title = _extract_id_title(doc)
        results.append({
            "id": cid,
            "title": title,
            "snippet": doc.page_content[:300]
        })
    return {"query": query, "results": results}
