# 🔬 ResearchPilot AI — AI Research Assistant with RAG

> A production-ready research assistant that uses TF-IDF search over uploaded PDFs, optional web results, and Gemini to generate source-grounded answers with streaming responses.

[![CI](https://github.com/saurabhtiwari25/ResearchPilotAI/actions/workflows/ci.yml/badge.svg)](https://github.com/saurabhtiwari25/ResearchPilotAI/actions)

## ✨ Key Features

- **TF-IDF RAG Pipeline** — Keyword-based search using TF-IDF vectorization and cosine similarity for fast, transparent retrieval
- **Sentence-Aware Chunking** — Splits documents at sentence boundaries instead of arbitrary word counts for more coherent passages
- **Streaming Responses** — Real-time token delivery via Server-Sent Events (SSE) for dramatically faster perceived response times
- **Multi-Turn Conversations** — Chat history is sent with each query so follow-up questions work naturally
- **Anti-Hallucination** — Similarity threshold check *before* calling the LLM, plus a strict grounding system prompt
- **Verifiable Citations** — Source metadata comes from the retrieval pipeline, not from the LLM
- **Document Management** — List, upload, and delete indexed documents via the API and UI
- **Premium UI** — Glassmorphism design, gradient accents, animated chat bubbles, styled source cards with relevance bars
- **Session Analytics** — Track query count, average response time, and session duration
- **Conversation Export** — Download chat history as Markdown
- **Production-Ready** — Structured logging, request/response middleware, global error handling, API versioning, file size validation, GitHub Actions CI

## Architecture

```
                    ┌───────────────┐
                    │   Streamlit   │ ← Premium UI with streaming + analytics
                    └───────┬───────┘
                            │
                            ↓
                         FastAPI       ← API v1, middleware, error handling
                            │
             ┌──────────────┴──────────────┐
             ↓                             ↓
       TF-IDF Search                  Tavily Search
    (Cosine Similarity)                (optional)
             │                             │
             └──────────────┬──────────────┘
                            ↓
                    Retrieved Context
                   (+ Relevance Check)
                            ↓
                       Grounded LLM
                       (Gemini API)
                     + Chat History
                            ↓
                    Answer + Sources
                            ↓
                    Streaming SSE →
                        Streamlit
```

## Tech Stack

| Component | Choice |
| :--- | :--- |
| Language | Python 3.11+ |
| Backend | FastAPI |
| Frontend | Streamlit |
| LLM | Gemini API (`google-genai` SDK) |
| Text Vectorization | scikit-learn TF-IDF |
| Search | Brute-force cosine similarity |
| Data Storage | JSON file (no external DB) |
| PDF Processing | PyPDF |
| Web Search | Tavily |
| Testing | Pytest + Ruff |
| CI/CD | GitHub Actions |
| Deployment | Docker |

> 📖 **Deep Dive:** For an in-depth breakdown of every algorithm, model, retrieval technique, and library used, see [**TECHNOLOGIES_USED.md**](file:///c:/Users/saura/OneDrive/Desktop/ai%20pro/TECHNOLOGIES_USED.md).

## Quick Start

### 1. Clone & Configure

```bash
git clone https://github.com/saurabhtiwari25/ResearchPilotAI.git
cd ResearchPilotAI
cp .env.example .env
# Edit .env and add your API keys
```

### 2. Run with Docker

```bash
docker compose up --build
```

- **Streamlit UI**: http://localhost:8501
- **FastAPI Docs**: http://localhost:8000/docs

### 3. Run Locally (without Docker)

#### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

#### Frontend

```bash
cd streamlit_app
pip install -r requirements.txt
streamlit run app.py
```

### 4. Run Tests

```bash
cd backend
pip install pytest ruff
python -m pytest tests/ -v
ruff check .
```

## Usage

1. **Upload PDFs** — Use the sidebar file uploader and click "Index Documents"
2. **Toggle Web Search** — Check the "Include Web Search" box if you want web results
3. **Enable Streaming** — Check "Stream Responses" for real-time token delivery
4. **Ask Questions** — Type your research question in the chat input
5. **Follow Up** — Ask follow-up questions — the chat history provides context
6. **View Sources** — Expand the "Sources & Citations" panel to see verified references with relevance scores
7. **Manage Documents** — Delete individual documents from the sidebar
8. **Export** — Download your conversation as Markdown

## API Endpoints

### v1 (Current)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/upload` | Upload and index PDF files |
| `POST` | `/api/v1/query` | Ask a question (standard response) |
| `POST` | `/api/v1/query/stream` | Ask a question (streaming SSE) |
| `GET` | `/api/v1/documents` | List indexed documents |
| `DELETE` | `/api/v1/documents/{name}` | Delete a document |

### Legacy (Backwards Compatible)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/upload` | Redirects to v1 |
| `POST` | `/api/query` | Redirects to v1 |

## Deploy Live

### Option 1: Render + Streamlit Community Cloud (Free — Recommended)

Best for a portfolio project. Zero cost.

**Step 1 — Push to GitHub**

```bash
cd ResearchPilotAI
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/saurabhtiwari25/ResearchPilotAI.git
git push -u origin main
```

**Step 2 — Deploy Backend on Render**

1. Go to [render.com](https://render.com) → **New Web Service**
2. Connect your GitHub repo
3. Configure:
   - **Name**: `researchpilot-backend`
   - **Root Directory**: `backend`
   - **Runtime**: Docker
   - **Instance Type**: Free
4. Add environment variables:
   - `GEMINI_API_KEY` → your key
   - `TAVILY_API_KEY` → your key
5. Click **Deploy**
6. Copy your backend URL (e.g. `https://researchpilot-backend.onrender.com`)

**Step 3 — Deploy Frontend on Streamlit Community Cloud**

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **New app** → connect your GitHub repo
3. Set:
   - **Main file path**: `streamlit_app/app.py`
4. Go to **Advanced settings** → **Secrets** and add:
   ```toml
   API_BASE_URL = "https://researchpilot-backend.onrender.com"
   ```
5. Click **Deploy**

Your app is now live at `https://your-app.streamlit.app` 🎉

> **Note**: Render free tier sleeps after 15 minutes of inactivity. The first request after sleep takes ~30 seconds. This is fine for a portfolio demo.

---

### Option 2: Railway (Easiest Docker Compose)

~$5/month after free trial. Deploys both services from your `docker-compose.yml`.

1. Go to [railway.app](https://railway.app) → **New Project from GitHub**
2. Railway auto-detects your `docker-compose.yml`
3. Add environment variables in the dashboard (`GEMINI_API_KEY`, `TAVILY_API_KEY`)
4. Railway assigns public URLs to both services
5. Set `API_BASE_URL` on the frontend service to the backend's Railway URL

---

### Option 3: Google Cloud Run (Production-Grade)

Free tier covers ~2M requests/month. Good fit since you're already using Gemini.

```bash
# Install gcloud CLI: https://cloud.google.com/sdk/docs/install

# Deploy backend
cd backend
gcloud run deploy researchpilot-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your-key,TAVILY_API_KEY=your-key

# Copy the backend URL from output, then deploy frontend
cd ../streamlit_app
gcloud run deploy researchpilot-frontend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars API_BASE_URL=https://researchpilot-backend-xxx-uc.a.run.app
```

---

### ⚠️ Data Persistence Note

On free-tier hosting (Render, Cloud Run), the filesystem resets on every deploy or restart. Your indexed PDFs and the `chunks.json` data file will be lost. This is fine for a demo — just re-upload PDFs after a restart. For production persistence, attach a Render Disk ($0.25/GB/month) or mount a persistent volume.

## Key Design Decisions

- **TF-IDF search**: Simple, transparent keyword-based search using term frequency statistics — no GPU or ML models needed for retrieval
- **Cosine similarity matching**: Brute-force comparison against every chunk ensures no relevant matches are missed
- **Sentence-aware chunking**: Documents are split at sentence boundaries so chunks don't cut mid-thought, producing more coherent passages for the LLM
- **Anti-hallucination**: Similarity threshold check *before* calling the LLM, plus a strict grounding system prompt
- **Verifiable citations**: Source metadata comes from the retrieval pipeline, not from the LLM
- **Zero-cost retrieval**: scikit-learn TF-IDF runs on CPU with zero API costs and minimal dependencies
- **Streaming SSE**: Answer tokens are delivered in real-time via Server-Sent Events, giving a dramatically better UX
- **API versioning**: All endpoints under `/api/v1/` with legacy compatibility at `/api/`

## License

MIT
