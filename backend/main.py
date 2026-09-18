"""
ResearchPilot AI — FastAPI Backend

Production-ready REST API with:
  - API versioning (/api/v1/...)
  - Structured logging
  - Global error handling
  - Request/response logging middleware
  - File size validation
  - Streaming responses
  - Chat history support
  - Document management (list/delete)

Endpoints:
  GET   /health                    — Health check
  POST  /api/v1/upload             — Upload and index PDF files
  POST  /api/v1/query              — Ask a question (standard response)
  POST  /api/v1/query/stream       — Ask a question (streaming response)
  GET   /api/v1/documents          — List indexed documents
  DELETE /api/v1/documents/{name}  — Delete a document
"""

import json
import logging
import os
import time

from fastapi import FastAPI, File, UploadFile, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

import config
import rag
import search
import llm

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("researchpilot.api")

# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ResearchPilot AI",
    description=(
        "AI Research Assistant with RAG — TF-IDF search "
        "over PDFs, optional web search, "
        "and grounded LLM answers with verifiable citations."
    ),
    version="2.0.0",
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
# Request/Response Logging Middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every request with method, path, status, and latency."""
    start = time.time()
    response = await call_next(request)
    latency_ms = (time.time() - start) * 1000
    logger.info(
        "%s %s → %d (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        latency_ms,
    )
    return response


# ---------------------------------------------------------------------------
# Global Exception Handler
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return clean JSON errors instead of raw tracebacks."""
    logger.exception("Unhandled error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
        },
    )


# ---------------------------------------------------------------------------
# Startup Validation
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup_validation():
    """Validate critical configuration on startup — fail fast with clear errors."""
    logger.info("=" * 60)
    logger.info("ResearchPilot AI — Starting up...")
    logger.info("=" * 60)

    # Check Gemini API key
    if not config.GEMINI_API_KEY:
        logger.warning(
            "⚠️  GEMINI_API_KEY is not set! The /api/v1/query endpoint will return errors. "
            "Set it in your .env file."
        )
    else:
        logger.info("✅ GEMINI_API_KEY configured.")

    # Check Tavily API key
    if not config.TAVILY_API_KEY:
        logger.info("ℹ️  TAVILY_API_KEY not set — web search will be unavailable.")
    else:
        logger.info("✅ TAVILY_API_KEY configured.")

    logger.info("ResearchPilot AI ready! 🚀")


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str           # "user" or "assistant"
    content: str


class QueryRequest(BaseModel):
    question: str
    use_web_search: bool = False
    chat_history: list[ChatMessage] = []


class SourceItem(BaseModel):
    type: str           # "pdf" or "web"
    filename: str = ""
    page: int = 0
    snippet: str = ""
    title: str = ""
    url: str = ""
    similarity: float = 0.0


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceItem]


class UploadResponse(BaseModel):
    status: str
    indexed_files: list[str]
    total_chunks: int


class DocumentInfo(BaseModel):
    filename: str
    chunk_count: int


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]
    total_documents: int
    total_chunks: int


class DeleteResponse(BaseModel):
    status: str
    filename: str
    chunks_deleted: int


# ---------------------------------------------------------------------------
# API Router (versioned)
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/v1", tags=["Research API v1"])


# ---------------------------------------------------------------------------
# Health Check (root level)
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"],
         summary="Health check",
         response_description="Service status")
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "ResearchPilot AI", "version": "2.0.0"}


# ---------------------------------------------------------------------------
# Upload Endpoint
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=UploadResponse,
              summary="Upload and index PDF files",
              response_description="Indexing results with file names and chunk counts")
async def upload_pdfs(files: list[UploadFile] = File(...)):
    """
    Upload one or more PDF files.

    Extracts text per page with PyPDF, chunks into passages using
    sentence-aware splitting (~500 words with overlap), checks for
    duplicates, and stores chunks in the JSON data store.
    """
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)

    indexed_files: list[str] = []
    total_chunks = 0

    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            logger.warning("Skipping non-PDF file: %s", file.filename)
            continue

        # File size validation
        content = await file.read()
        size_mb = len(content) / (1024 * 1024)
        if size_mb > config.MAX_FILE_SIZE_MB:
            logger.warning(
                "File '%s' too large (%.1f MB > %d MB limit). Skipping.",
                file.filename, size_mb, config.MAX_FILE_SIZE_MB,
            )
            continue

        # Save uploaded file temporarily
        file_path = os.path.join(config.UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as f:
            f.write(content)

        # Index the PDF
        chunk_count = rag.index_pdf(file_path, file.filename)
        indexed_files.append(file.filename)
        total_chunks += chunk_count

    return UploadResponse(
        status="success",
        indexed_files=indexed_files,
        total_chunks=total_chunks,
    )


# ---------------------------------------------------------------------------
# Query Endpoint (Standard)
# ---------------------------------------------------------------------------

@router.post("/query", response_model=QueryResponse,
              summary="Ask a question (standard response)",
              response_description="Grounded answer with verified sources")
def query_documents(request: QueryRequest):
    """
    Ask a question against indexed PDFs, optionally combining web search results.

    Flow:
      1. TF-IDF search over stored chunks
      2. Optionally search the web via Tavily
      3. Check relevance — short-circuit if no relevant context found
      4. Generate a grounded answer with Gemini (with chat history for follow-ups)
      5. Attach source metadata from the retrieval pipeline (NOT from the LLM)
    """
    question = request.question.strip()
    if not question:
        return QueryResponse(answer="Please enter a question.", sources=[])

    # Step 1: Search the document store
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

    # Step 4: Generate grounded answer with Gemini (with chat history)
    chat_history = [msg.model_dump() for msg in request.chat_history] if request.chat_history else None

    answer = llm.generate_answer(
        question=question,
        pdf_chunks=pdf_results,
        web_results=web_results if request.use_web_search else None,
        chat_history=chat_history,
    )

    # Step 5: Build verified source metadata from retrieval pipeline
    sources = _build_sources(pdf_results, web_results)

    return QueryResponse(answer=answer, sources=sources)


# ---------------------------------------------------------------------------
# Query Endpoint (Streaming)
# ---------------------------------------------------------------------------

@router.post("/query/stream",
              summary="Ask a question (streaming response)",
              response_description="Server-Sent Events stream with answer tokens and sources")
def query_documents_stream(request: QueryRequest):
    """
    Streaming version of the query endpoint.

    Uses Server-Sent Events (SSE) to deliver answer tokens in real-time,
    followed by the source metadata as a final JSON event.

    Event types:
      - 'token':   A chunk of the answer text
      - 'sources': JSON array of source metadata
      - 'done':    Signal that the stream is complete
      - 'error':   An error message
    """
    question = request.question.strip()
    if not question:
        return StreamingResponse(
            _sse_error("Please enter a question."),
            media_type="text/event-stream",
        )

    def generate():
        # Step 1: Search document store
        pdf_results = rag.search_documents(question)

        # Step 2: Web search
        web_results: list[dict] = []
        if request.use_web_search:
            web_results = search.search_web(question)

        # Step 3: Relevance check
        has_pdf_context = rag.retrieved_chunks_meet_threshold(pdf_results)
        has_web_context = len(web_results) > 0

        if not has_pdf_context and not has_web_context:
            yield _sse_event("token", "I don't have enough information in the provided sources.")
            yield _sse_event("sources", "[]")
            yield _sse_event("done", "")
            return

        # Step 4: Stream grounded answer
        chat_history = [msg.model_dump() for msg in request.chat_history] if request.chat_history else None

        for token in llm.generate_answer_stream(
            question=question,
            pdf_chunks=pdf_results,
            web_results=web_results if request.use_web_search else None,
            chat_history=chat_history,
        ):
            yield _sse_event("token", token)

        # Step 5: Send source metadata
        sources = _build_sources(pdf_results, web_results)
        sources_json = json.dumps([s.model_dump() for s in sources])
        yield _sse_event("sources", sources_json)
        yield _sse_event("done", "")

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Document Management Endpoints
# ---------------------------------------------------------------------------

@router.get("/documents", response_model=DocumentListResponse,
             summary="List all indexed documents",
             response_description="List of document names and chunk counts")
def list_documents():
    """List all documents currently indexed in the vector store."""
    docs = rag.list_indexed_documents()
    total_chunks = sum(d["chunk_count"] for d in docs)
    return DocumentListResponse(
        documents=[DocumentInfo(**d) for d in docs],
        total_documents=len(docs),
        total_chunks=total_chunks,
    )


@router.delete("/documents/{filename}", response_model=DeleteResponse,
                summary="Delete a document from the index",
                response_description="Deletion result with chunk count")
def delete_document(filename: str):
    """Delete all indexed chunks for a specific document."""
    chunks_deleted = rag.delete_document(filename)
    if chunks_deleted == 0:
        return DeleteResponse(
            status="not_found",
            filename=filename,
            chunks_deleted=0,
        )
    return DeleteResponse(
        status="deleted",
        filename=filename,
        chunks_deleted=chunks_deleted,
    )


# ---------------------------------------------------------------------------
# Legacy Endpoint Compatibility (redirect /api/* → /api/v1/*)
# ---------------------------------------------------------------------------

@app.post("/api/upload", include_in_schema=False)
async def legacy_upload(files: list[UploadFile] = File(...)):
    """Legacy endpoint — redirects to v1."""
    return await upload_pdfs(files)


@app.post("/api/query", include_in_schema=False)
def legacy_query(request: QueryRequest):
    """Legacy endpoint — redirects to v1."""
    return query_documents(request)


# ---------------------------------------------------------------------------
# Register Router
# ---------------------------------------------------------------------------

app.include_router(router)


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _build_sources(pdf_results: list[dict], web_results: list[dict]) -> list[SourceItem]:
    """Build verified source metadata from the retrieval pipeline."""
    sources: list[SourceItem] = []

    for chunk in pdf_results:
        sources.append(SourceItem(
            type="pdf",
            filename=chunk["filename"],
            page=chunk["page"],
            snippet=chunk["snippet"],
            similarity=chunk.get("similarity", 0.0),
        ))

    for result in web_results:
        sources.append(SourceItem(
            type="web",
            title=result["title"],
            url=result["url"],
            snippet=result["snippet"][:200],
        ))

    return sources


def _sse_event(event_type: str, data: str) -> str:
    """Format a Server-Sent Event string."""
    # Escape newlines in data for SSE format
    escaped = data.replace("\n", "\ndata: ")
    return f"event: {event_type}\ndata: {escaped}\n\n"


def _sse_error(message: str):
    """Generator that yields a single SSE error event."""
    yield _sse_event("error", message)
    yield _sse_event("done", "")
