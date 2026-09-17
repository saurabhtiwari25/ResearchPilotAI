# ResearchPilot AI — AI Research Assistant with RAG

> **Elevator Pitch**: *"I built a research assistant that uses semantic search over uploaded PDFs, optionally combines web results, and uses an LLM to generate source-grounded answers."*

---

## 🎯 Goal

A simple, focused AI research assistant where a user:
1. **Enters a research question**
2. **Uploads PDFs**
3. **AI searches the uploaded documents** (via semantic vector search)
4. **AI can optionally search the web** (via a simple toggle)
5. **Generates an answer** strictly grounded in the retrieved context
6. **Shows sources/citations** (document name, page number, or web link)

*That's it.*

---

## 🏗️ Architecture & Data Flow

```plaintext
                    ┌───────────────┐
                    │   Streamlit   │
                    └───────┬───────┘
                            │
                            ↓
                         FastAPI
                            │
             ┌──────────────┴──────────────┐
             ↓                             ↓
       PDF Vector Search             Tavily Search
         (ChromaDB)                    (optional)
             │                             │
             └──────────────┬──────────────┘
                            ↓
                    Retrieved Context
                   (+ Relevance Check)
                            ↓
                       Grounded LLM
                       (Gemini API)
                            ↓
                    Answer + Sources
                            ↓
                        Streamlit
```

### Web Search Logic (Simple Toggle)

```text
[x] Include Web Search
```
- **If Checked**: Question ➔ PDF Vector Search + Tavily Web Search ➔ Combine Context ➔ Gemini ➔ Answer + Sources
- **If Unchecked**: Question ➔ PDF Vector Search ➔ Gemini ➔ Answer + Sources

---

## 🛠️ Stack (Locked for MVP)

| Component | Choice |
| :--- | :--- |
| **Language** | Python 3.11+ |
| **Backend** | FastAPI |
| **Frontend** | Streamlit |
| **LLM** | Gemini API (using Google's current `google-genai` SDK) |
| **Vector DB** | ChromaDB |
| **Embeddings** | Sentence Transformers (`all-MiniLM-L6-v2`) |
| **PDF Processing** | PyPDF |
| **Web Search** | Tavily (`tavily-python`) |
| **Persistence** | ChromaDB (local disk storage) |
| **Deployment** | Docker |
| **Version Control** | Git / GitHub |

> **Scope Note**: No LangGraph, PostgreSQL, reranking, authentication, Redis, multi-agent architecture, or complex orchestration in this MVP. Keep it lean, reliable, and explainable.

---

## 🛡️ Grounded RAG Rules & Guardrails

### 1. Pre-Generation Relevance Threshold
Do not rely solely on the LLM prompt to catch out-of-scope questions. The retrieval pipeline applies a similarity-distance check first:

```python
# Relevance check before calling the LLM
if not retrieved_chunks_meet_threshold(retrieved_docs) and not use_web_search:
    return {
        "answer": "I don't have enough information in the provided sources.",
        "sources": []
    }
```

### 2. Strict Grounding Prompt
To reduce hallucinations and enforce grounded responses, the LLM prompt strictly instructs:

```text
Answer only using the retrieved context.

If the context does not contain enough information to answer,
say "I don't have enough information in the provided sources."

Never invent citations or sources.
Cite only sources that are actually present in the retrieved context.
```

---

## 📚 Verifiable Citations Pipeline

The LLM is **not** responsible for inventing or mapping citation metadata. Instead:

```plaintext
Retriever (ChromaDB / Tavily)
   ↓
Retrieved chunks + verified metadata (filename, page, URL)
   ↓
Gemini → Generates Answer
   ↓
Backend attaches source metadata to response
   ↓
Streamlit displays structured citations
```

### Example API Response
```json
{
  "answer": "Multi-head attention allows the model to jointly attend to information from different representation subspaces at different positions.",
  "sources": [
    {
      "type": "pdf",
      "filename": "attention_is_all_you_need.pdf",
      "page": 4,
      "snippet": "Multi-head attention allows the model to jointly attend..."
    }
  ]
}
```

---

## 📂 Project Directory Structure

```plaintext
researchpilot-ai/
│
├── .env.example              # GEMINI_API_KEY, TAVILY_API_KEY
├── .gitignore
├── docker-compose.yml        # Backend + Streamlit orchestration
├── README.md
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt      # fastapi, uvicorn, chromadb, sentence-transformers, pypdf, tavily-python, google-genai
│   ├── main.py               # FastAPI entrypoint & REST routes
│   ├── config.py             # App configuration & environment variables
│   ├── rag.py                # PDF extraction (PyPDF), chunking, ChromaDB vector store
│   ├── search.py             # Tavily web search integration
│   └── llm.py                # Gemini answer generation with grounded prompt
│
└── streamlit_app/
    ├── Dockerfile
    ├── requirements.txt      # streamlit, requests
    └── app.py                # Single-page UI (upload PDFs, toggle web search, chat & sources)
```

---

## 🔌 API Endpoints (FastAPI Backend)

### 1. `POST /api/upload`
- Uploads one or more PDF files via `multipart/form-data`.
- Extracts text per page with PyPDF, chunks into passages (~500 words with 50-word overlap), and stores embeddings in ChromaDB.
- **Response**:
  ```json
  {
    "status": "success",
    "indexed_files": ["attention_is_all_you_need.pdf"],
    "total_chunks": 36
  }
  ```

### 2. `POST /api/query`
- **Request Body**:
  ```json
  {
    "question": "What is the primary advantage of multi-head attention?",
    "use_web_search": false
  }
  ```
- **Response**:
  ```json
  {
    "answer": "Multi-head attention allows the model to jointly attend to information from different representation subspaces...",
    "sources": [
      {
        "type": "pdf",
        "filename": "attention_is_all_you_need.pdf",
        "page": 4,
        "snippet": "Multi-head attention allows the model to jointly attend..."
      }
    ]
  }
  ```

---

## 🚀 Step-by-Step Implementation Roadmap

### Step 1: Environment & Setup
- [ ] Create Python virtual environment and `.env` template (`GEMINI_API_KEY`, `TAVILY_API_KEY`).
- [ ] Set up `backend/requirements.txt` (`fastapi`, `uvicorn`, `chromadb`, `sentence-transformers`, `pypdf`, `tavily-python`, `google-genai`).
- [ ] Set up `streamlit_app/requirements.txt` (`streamlit`, `requests`).
- [ ] Initialize Git repository.

### Step 2: Document Ingestion & Embeddings (`backend/rag.py`)
- [ ] Extract text and page numbers using `pypdf.PdfReader`.
- [ ] Implement text chunker (~500 words with 50-word overlap) retaining metadata (`filename`, `page`).
- [ ] Embed chunks locally using `SentenceTransformer("all-MiniLM-L6-v2")`.
- [ ] Store chunks and metadata in a persistent local ChromaDB collection.
- [ ] Implement query function with similarity-distance threshold filtering.

### Step 3: Web Search Integration (`backend/search.py`)
- [ ] Integrate Tavily API client (`tavily-python`).
- [ ] Create search helper returning top 3-5 clean snippets with titles and URLs.

### Step 4: Grounded LLM Answering (`backend/llm.py`)
- [ ] Configure Gemini API using Google's current `google-genai` SDK.
- [ ] Implement strict grounding prompt and context injection.
- [ ] If retrieved chunks do not meet the relevance threshold and web search is off, short-circuit immediately without making an unnecessary LLM call.

### Step 5: FastAPI REST API (`backend/main.py`)
- [ ] Implement `POST /api/upload` (accepts `multipart/form-data` PDF files).
- [ ] Implement `POST /api/query` (accepts question + `use_web_search` boolean).
- [ ] Add `GET /health` endpoint.

### Step 6: Streamlit UI (`streamlit_app/app.py`)
- [ ] **Sidebar**: PDF file uploader + "Index Documents" action button.
- [ ] **Search Options**: Checkbox `[x] Include Web Search`.
- [ ] **Chat Area**: `st.chat_input` for queries, `st.chat_message` for answers.
- [ ] **Citations Panel**: `st.expander("📚 Sources & Citations")` rendering verified source metadata (file, page, snippet, or URL).

### Step 7: Dockerization
- [ ] Create `backend/Dockerfile` and `streamlit_app/Dockerfile`.
- [ ] Create `docker-compose.yml` to spin up both services with `docker compose up --build`.

---

## 💡 Interview Talking Points

- **Architectural Clarity**: Kept the system clean and explainable: a FastAPI backend coordinating local semantic retrieval (ChromaDB) and optional web search (Tavily) with a Streamlit interface.
- **Why `all-MiniLM-L6-v2` locally?** Fast, runs entirely on CPU, zero API costs, and avoids external latency or rate limits during document ingestion.
- **Why Tavily over general scrapers?** Pre-parsed, clean markdown/text content designed specifically for RAG context injection without raw HTML bloat.
- **Two-Layer Anti-Hallucination Guardrails**:
  1. *Programmatic check*: A similarity-distance threshold check on retrieved chunks before the LLM is even invoked.
  2. *Strict grounding prompt*: Instructions requiring the model to say *"I don't have enough information in the provided sources"* rather than guessing.
- **Verifiable Citations by Design**: Citations are derived directly from chunk metadata collected during retrieval—the LLM is not trusted to hallucinate or invent its own reference links.
