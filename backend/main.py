"""
ResearchPilot AI — FastAPI Backend

REST API entrypoint with two core endpoints:
  POST /api/upload  — Upload and index PDF files
  POST /api/query   — Ask a question with optional web search
  GET  /health      — Health check
"""

import os
import shutil

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
import rag
import search
import llm

# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ResearchPilot AI",
    description="AI Research Assistant with RAG — Semantic search over PDFs with optional web search and grounded LLM answers.",
    version="1.0.0",
)

# CORS — allow Streamlit frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    question: str
    use_web_search: bool = False


class SourceItem(BaseModel):
    type: str           # "pdf" or "web"
    filename: str = ""
    page: int = 0
    snippet: str = ""
    title: str = ""
    url: str = ""


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceItem]


class UploadResponse(BaseModel):
    status: str
    indexed_files: list[str]
    total_chunks: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "ResearchPilot AI"}


@app.post("/api/upload", response_model=UploadResponse)
async def upload_pdfs(files: list[UploadFile] = File(...)):
    """
    Upload one or more PDF files.

    Extracts text per page with PyPDF, chunks into passages
    (~500 words with 50-word overlap), and stores embeddings in ChromaDB.
    """
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)

    indexed_files: list[str] = []
    total_chunks = 0

    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            continue

        # Save uploaded file temporarily
        file_path = os.path.join(config.UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Index the PDF
        chunk_count = rag.index_pdf(file_path, file.filename)
        indexed_files.append(file.filename)
        total_chunks += chunk_count

    return UploadResponse(
        status="success",
        indexed_files=indexed_files,
        total_chunks=total_chunks,
    )


@app.post("/api/query", response_model=QueryResponse)
def query_documents(request: QueryRequest):
    """
    Ask a question against indexed PDFs, optionally combining web search results.

    Flow:
      1. Search ChromaDB for relevant PDF chunks
      2. Optionally search the web via Tavily
      3. Check relevance threshold — short-circuit if no relevant context found
      4. Generate a grounded answer with Gemini
      5. Attach source metadata from the retrieval pipeline (NOT from the LLM)
    """
    question = request.question.strip()
    if not question:
        return QueryResponse(answer="Please enter a question.", sources=[])

    # Step 1: Search the vector store
    pdf_results = rag.search_documents(question)

    # Step 2: Optionally search the web
    web_results: list[dict] = []
    if request.use_web_search:
        web_results = search.search_web(question)

    # Step 3: Relevance check — short-circuit if no useful context
    has_pdf_context = rag.retrieved_chunks_meet_threshold(pdf_results)
    has_web_context = len(web_results) > 0

    if not has_pdf_context and not has_web_context:
        return QueryResponse(
            answer="I don't have enough information in the provided sources.",
            sources=[],
        )

    # Step 4: Generate grounded answer with Gemini
    answer = llm.generate_answer(
        question=question,
        pdf_chunks=pdf_results,
        web_results=web_results if request.use_web_search else None,
    )

    # Step 5: Build verified source metadata from retrieval pipeline
    sources: list[SourceItem] = []

    for chunk in pdf_results:
        sources.append(SourceItem(
            type="pdf",
            filename=chunk["filename"],
            page=chunk["page"],
            snippet=chunk["snippet"],
        ))

    for result in web_results:
        sources.append(SourceItem(
            type="web",
            title=result["title"],
            url=result["url"],
            snippet=result["snippet"][:200],
        ))

    return QueryResponse(answer=answer, sources=sources)
