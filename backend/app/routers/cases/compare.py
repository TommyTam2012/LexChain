from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .shared import _get_retriever, _get_chat_model, _find_doc_by_id

router = APIRouter()

class CompareRequest(BaseModel):
    case_a: str
    case_b: str

@router.post("/compare")
def compare_cases(request: CompareRequest):
    retriever = _get_retriever()
    llm = _get_chat_model()

    def _get_case_text(cid: str) -> str:
        doc = _find_doc_by_id(retriever, cid) or retriever.get_relevant_documents(cid)[0]
        if not doc:
            raise HTTPException(status_code=404, detail=f"Case not found: {cid}")
        return doc.page_content

    text_a = _get_case_text(request.case_a)
    text_b = _get_case_text(request.case_b)

    prompt = f"""
    Compare the following two cases and summarize similarities and differences
    in their legal reasoning and holdings.

    CASE A ({request.case_a}):
    {text_a[:2000]}

    CASE B ({request.case_b}):
    {text_b[:2000]}

    Provide a concise comparison.
    """
    answer = llm.predict(prompt)
    return {"case_a": request.case_a, "case_b": request.case_b, "comparison": answer}
