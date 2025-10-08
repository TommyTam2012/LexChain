from fastapi import APIRouter, HTTPException, Query
from .shared import _get_retriever, _get_chat_model, _extract_id_title

router = APIRouter()

@router.get("/summarize")
def summarize_case(query: str = Query(..., description="Case name or topic")):
    retriever = _get_retriever(k=1)
    llm = _get_chat_model()
    docs = retriever.get_relevant_documents(query)
    if not docs:
        raise HTTPException(status_code=404, detail="No case found to summarize.")
    case_text = docs[0].page_content[:3000]
    cid, title = _extract_id_title(docs[0])

    prompt = f"Summarize the key issue and holding of the case titled '{title}'.\n\n{case_text}"
    summary = llm.predict(prompt)
    return {"id": cid, "title": title, "summary": summary}
