from fastapi import APIRouter, Query
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
import os

router = APIRouter(prefix="/qa", tags=["QA"])

@router.get("/ask")
def ask(query: str = Query(...)):
    index_path = os.getenv("LEXCHAIN_INDEX_PATH", "./data/indexes/faiss_v1")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    # ✅ Safe load
    if not os.path.exists(os.path.join(index_path, "index.faiss")):
        return {"query": query, "answer": "No FAISS index found. Please build it first."}

    vectorstore = FAISS.load_local(
        index_path, embeddings, allow_dangerous_deserialization=True
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)

    result = qa_chain.invoke({"query": query})
    return {"query": query, "answer": result["result"]}
