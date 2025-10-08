from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from .shared import _get_retriever, _get_chat_model, _extract_id_title

router = APIRouter()

class SynthesizeRequest(BaseModel):
    queries: List[str]

@router.post("/synthesize")
def synthesize_cases(request: SynthesizeRequest):
    retriever = _get_retriever(k=2)
    llm = _get_chat_model(temp=0)

    all_texts: List[str] = []
    summaries: List[str] = []

    for query in request.queries:
        docs = retriever.get_relevant_documents(query)
        if not docs:
            continue
        doc = docs[0]
        cid, title = _extract_id_title(doc)
        summaries.append(f"{title} ({cid})")
        all_texts.append(f"Case: {title}\n\n{doc.page_content[:1500]}")

    if not all_texts:
        raise HTTPException(status_code=404, detail="No cases found for synthesis.")

    joined_text = "\n\n---\n\n".join(all_texts)
    prompt = f"""
    You are LexChain, an AI legal analyst.
    Given several related cases, produce a structured synthesis describing:

    {{
      "common_issue": "shared legal question among the cases",
      "alignments": "which cases reach similar holdings",
      "conflicts": "which cases diverge or conflict",
      "precedent_trend": "overall trend (strengthening / diverging)",
      "summary": "concise narrative of the combined reasoning"
    }}

    Analyze the following case materials:
    {joined_text}
    """

    result = llm.predict(prompt)
    return {
        "queries": request.queries,
        "cases_considered": summaries,
        "synthesis": result.strip()
    }
