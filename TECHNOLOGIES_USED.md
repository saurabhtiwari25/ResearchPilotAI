# 🛠️ Technologies & Techniques Used — ResearchPilot AI

A comprehensive guide to all programming languages, frameworks, libraries, foundation models, algorithms, and architectural techniques powering **ResearchPilot AI**.

---

## 📑 Table of Contents

1. [Architecture Overview](#-architecture-overview)
2. [Foundation Models & LLM Technology](#-foundation-models--llm-technology)
3. [Text Vectorization & Search](#-text-vectorization--search)
4. [Document Processing & Chunking Techniques](#-document-processing--chunking-techniques)
5. [Web Search & External Context Enrichment](#-web-search--external-context-enrichment)
6. [Backend Web Framework & API Architecture](#-backend-web-framework--api-architecture)
7. [Frontend Application & UI/UX](#-frontend-application--uiux)
8. [DevOps, Containerization & CI/CD](#-devops-containerization--cicd)
9. [Testing & Code Quality](#-testing--code-quality)
10. [Summary Table of Technologies & Versions](#-summary-table-of-technologies--versions)

---

## 🏛️ Architecture Overview

ResearchPilot AI is built as a modular **Retrieval-Augmented Generation (RAG)** system:

```
[Uploaded PDFs] 
       │
       ▼
 [Sentence-Aware Chunking] ──> [SHA-256 Deduplication]
       │
       ▼
 [TF-IDF Vectorization]
 (scikit-learn TfidfVectorizer)
       │
       ▼
 [JSON Chunk Store]
 (Persisted to disk)
       │
       ▼
 [Brute-Force Cosine Similarity Search]
  + Similarity Threshold Filter
       │
  [+ Optional Tavily Web Search]
       │
       ▼
 [Google Gemini 2.5 Flash] (Streaming SSE)
       │
       ▼
 [Streamlit Glassmorphism UI]
```

---

## 🧠 Foundation Models & LLM Technology

### 1. Google Gemini 2.5 Flash
* **Provider:** Google DeepMind / Google AI Studio
* **SDK:** `google-genai` (v1.*) — modern unified official SDK
* **Role:** Primary reasoning engine for answering research queries based strictly on retrieved source documents.
* **Techniques Used:**
  * **Strict Grounding System Prompt:** Constrains the LLM to only answer using provided context chunks. If the retrieved context is insufficient, it explicitly responds that information is missing, preventing hallucinations.
  * **Source Attributions:** The LLM is directed to cite filename and page numbers directly in its markdown response.
  * **Real-time Token Streaming:** Implemented using Gemini's `generate_content_stream` API, yielding chunks as they are generated to minimize Time-to-First-Token (TTFT).
  * **Multi-Turn Context Maintenance:** Converts conversation history into Gemini `types.Content` turns (`user` and `model` roles) so users can ask contextual follow-up questions.

---

## 🔢 Text Vectorization & Search

### 1. TF-IDF Vectorization (`scikit-learn` TfidfVectorizer)
* **Library:** `scikit-learn` (v1.*)
* **Role:** Converts text chunks and queries into sparse numerical vectors based on word frequency statistics.
* **Technique:**
  * **Term Frequency–Inverse Document Frequency (TF-IDF):** Weighs words by how frequently they appear in a document relative to how common they are across all documents. Common words (e.g., "the", "is") get low weight; distinctive keywords get high weight.
  * **Sublinear TF:** Applies logarithmic scaling (`1 + log(tf)`) to prevent long documents from dominating scores.
  * **English Stop Words Removal:** Filters out common English words that carry no retrieval value.
  * **Feature Limit:** Caps vocabulary at 10,000 features to balance precision and memory.

### 2. Brute-Force Cosine Similarity Search
* **Library:** `scikit-learn` (`cosine_similarity`)
* **Role:** Compares the query TF-IDF vector against every stored chunk vector to find the most relevant matches.
* **Technique:**
  * Computes the cosine of the angle between the query vector and each document vector. A score of `1.0` means identical term distributions; `0.0` means completely unrelated.
  * All chunks are compared in a single batch operation — simple, transparent, and easy to debug.

### 3. Similarity Threshold Filtering
* Chunks whose cosine similarity score falls below `SIMILARITY_THRESHOLD` (default `0.1`) are discarded before being passed to the LLM, preventing low-quality context from degrading answer quality.

### 4. JSON Chunk Store
* Chunks and their metadata are persisted as a simple JSON file on disk (`data/chunks.json`).
* The TF-IDF index is rebuilt in-memory from this file on startup and after any indexing or deletion operation.
* No external database dependencies — everything runs locally with zero infrastructure.

---

## 📄 Document Processing & Chunking Techniques

### 1. PDF Text Extraction
* **Library:** `pypdf` (v5.*)
* **Technique:** Per-page text stream parsing with fallback handling for unreadable or encrypted pages. Preserves physical page numbers for citations.

### 2. Sentence-Aware Sliding Window Chunking
* **Technique:**
  * Regex lookbehind for sentence terminations: `(?<=[.!?])\s+`.
  * Target chunk size: **500 words**.
  * Chunk overlap: **50 words**.
  * **Sentence preservation:** Chunks always split at sentence boundaries rather than arbitrary character or word boundaries, preventing severed semantic context.

### 3. Content Hashing & Deduplication
* **Algorithm:** SHA-256 cryptographic hashing.
* **Technique:** The entire byte stream of each uploaded document is hashed. If the same file is uploaded again, it is detected and re-indexed cleanly, preventing redundant chunks.

### 4. Document Lifecycle & Granular Deletion
* Supports deleting individual files from the chunk store by filtering on `filename`, cleanly purging all associated chunks and rebuilding the TF-IDF index.

---

## 🌐 Web Search & External Context Enrichment

### 1. Tavily Search API (`tavily-python` v0.5.*)
* **Role:** AI-native search engine designed specifically for LLM and RAG context injection.
* **Technique:**
  * Extracts concise, cleaned web snippets without advertising or boilerplate HTML.
  * Returns title, URL, and content snippet.
  * Formatted into a dedicated `=== Web Search Results ===` block in the LLM prompt when web search is toggled on.

---

## 🚀 Backend Web Framework & API Architecture

### 1. FastAPI (`fastapi` v0.115.*)
* Modern, high-performance asynchronous Python web framework built on Starlette and Pydantic.
* **Techniques & Features:**
  * **API Versioning:** Structured prefix `/api/v1` for future backward compatibility.
  * **Server-Sent Events (SSE):** Streaming endpoint `/api/v1/query/stream` using Starlette `StreamingResponse` with `text/event-stream` media type.
  * **Data Validation:** Pydantic v2 schemas (`QueryRequest`, `QueryResponse`, `DocumentInfo`, `HealthResponse`).
  * **File Upload Guardrails:** In-flight file size checks limiting uploads to 50MB with instant HTTP 413 Payload Too Large responses.
  * **Global Exception Handlers:** Centralized error trapping returning unified JSON error envelopes: `{"error": "...", "detail": "...", "status_code": ...}`.
  * **Structured Logging:** Standard library `logging` configured with ISO-8601 timestamps, module namespaces, and hierarchical loggers (`researchpilot.main`, `researchpilot.rag`, etc.).
  * **Startup Sanity Checks:** Verifies API keys and logs configuration state before accepting requests.

### 2. Uvicorn (`uvicorn[standard]` v0.34.*)
* Lightning-fast ASGI server implementation using `uvloop` (fast event loop) and `httptools` (HTTP parser).

---

## 🎨 Frontend Application & UI/UX

### 1. Streamlit (`streamlit` v1.*)
* Rapid web application framework powering the user interface.

### 2. UI/UX & CSS Techniques
* **Custom Glassmorphism Design System:**
  * Backdrop filter blur (`backdrop-filter: blur(12px)`).
  * Semi-transparent gradients with modern dark-mode palette (`#0F172A`, `#1E293B`, `#6366F1`, `#8B5CF6`).
  * Custom Google Font integration (`Inter`, 400/500/600/700 weights).
* **Token-by-Token Streaming Display:**
  * Consumes backend SSE streams using `requests(stream=True)`.
  * Updates Streamlit's `st.write_stream` / `st.empty` container dynamically in real-time.
* **Interactive State Management:**
  * `st.session_state` preserves multi-turn message history, document list, and UI state across rerenders.
* **Source Inspection Accordion:**
  * Collapsible source badges showing exact filename, page number, similarity score, and chunk preview.
* **Export Utilities:**
  * One-click conversation export to **JSON** and **Markdown** format.
* **Document Management Sidebar:**
  * Visual file cards with chunk statistics, status badges, and single-click file deletion.

---

## 🐳 DevOps, Containerization & CI/CD

### 1. Docker & Docker Compose
* **Multi-Container Architecture:**
  * `backend`: Runs FastAPI with scikit-learn and TF-IDF search.
  * `streamlit_app`: Runs Streamlit UI connected to backend over an internal Docker bridge network.
* **Named Volumes:** `data` and `uploads` volumes for data persistence across container rebuilds.
* **Health Checks:** Container dependency management using Docker health checks on `/api/v1/health`.

### 2. GitHub Actions CI (`.github/workflows/ci.yml`)
* Automated workflow triggered on push and pull requests to `main`.
* **Testing Matrix:** Tests against Python `3.11` and `3.12`.
* **Linting & Code Quality:** Uses `ruff` for linting and formatting verification.
* **Test Suite:** Automated execution of `pytest` with verbose reporting.
* **Docker Build Validation:** Verifies that both backend and frontend Dockerfiles build successfully.

---

## 🧪 Testing & Code Quality

### 1. Pytest (`pytest`, `pytest-mock`, `httpx`)
* Comprehensive test suite in `backend/tests/`:
  * `test_rag.py`: Unit tests for sentence-aware chunking, TF-IDF search, and content hashing.
  * `test_api.py`: Integration tests using FastAPI `TestClient` (`httpx`) covering health check, document upload, query, and streaming endpoints.

---

## 📊 Summary Table of Technologies & Versions

| Layer / Component | Technology / Library | Version | Purpose |
|:------------------|:---------------------|:--------|:--------|
| **LLM Inference** | Google Gemini 2.5 Flash | via API | Grounded question answering & reasoning |
| **LLM SDK** | `google-genai` | `1.*` | Official Google GenAI Python SDK |
| **Text Vectorization** | `scikit-learn` (TfidfVectorizer) | `1.*` | TF-IDF word frequency vectors |
| **Search** | `scikit-learn` (cosine_similarity) | `1.*` | Brute-force cosine similarity matching |
| **Data Storage** | JSON file (`chunks.json`) | Built-in | Lightweight chunk persistence (no external DB) |
| **PDF Extraction** | `pypdf` | `5.*` | PDF text extraction and page tracking |
| **Web Search** | `tavily-python` | `0.5.*` | AI-optimized live web research snippets |
| **Web Framework** | `fastapi` | `0.115.*` | Async REST API & SSE streaming server |
| **ASGI Server** | `uvicorn[standard]` | `0.34.*` | High-concurrency ASGI server |
| **Multipart Parser** | `python-multipart` | `0.0.*` | File upload handling with size validation |
| **Config / Env** | `python-dotenv` | `1.*` | Environment variable management |
| **Frontend UI** | `streamlit` | `1.*` | Interactive research dashboard & chat UI |
| **HTTP Client** | `requests` | `2.*` | Frontend-to-backend communication & SSE stream |
| **Containerization**| Docker & Docker Compose | Compose v2 | Multi-service orchestration and persistence |
| **CI/CD** | GitHub Actions | YAML | Multi-version Python testing, linting & Docker builds |
| **Testing** | `pytest`, `pytest-mock`, `httpx` | `8.*` | Automated unit and integration test suite |
