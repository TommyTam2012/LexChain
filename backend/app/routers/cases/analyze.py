from fastapi import APIRouter, HTTPException, Query
from .shared import _get_retriever, _get_chat_model, _extract_id_title

router = APIRouter()

@router.get("/analyze")
def analyze_case(query: str = Query(..., description="Search term or legal issue")):
    retriever = _get_retriever(k=2)
    llm = _get_chat_model()

    docs = retriever.get_relevant_documents(query)
    if not docs:
        raise HTTPException(status_code=404, detail="No related cases found for analysis.")

    top_doc = docs[0]
    cid, title = _extract_id_title(top_doc)
    content = top_doc.page_content[:4000]

    prompt = f"""
    You are a legal analysis assistant.
    Analyze the following case passage and extract:

    {{
      "issue": "Legal question addressed",
      "holding": "Court's resolution",
      "precedent_strength": "High / Medium / Low"
    }}

    Case: {title}
    Text:
    {content}
    """
    analysis = llm.predict(prompt)
    return {"id": cid, "title": title, "analysis": analysis.strip()}
