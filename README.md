# 🔬 ResearchPilot AI — AI Research Assistant with RAG

> A research assistant that uses semantic search over uploaded PDFs, optionally combines web results, and uses an LLM to generate source-grounded answers.

## Architecture

```
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

## Tech Stack

| Component | Choice |
| :--- | :--- |
| Language | Python 3.11+ |
| Backend | FastAPI |
| Frontend | Streamlit |
| LLM | Gemini API (`google-genai` SDK) |
| Vector DB | ChromaDB |
| Embeddings | Sentence Transformers (`all-MiniLM-L6-v2`) |
| PDF Processing | PyPDF |
| Web Search | Tavily |
| Deployment | Docker |

## Quick Start

### 1. Clone & Configure

```bash
git clone https://github.com/your-username/researchpilot-ai.git
cd researchpilot-ai
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

## Usage

1. **Upload PDFs** — Use the sidebar file uploader and click "Index Documents"
2. **Toggle Web Search** — Check the "Include Web Search" box if you want web results
3. **Ask Questions** — Type your research question in the chat input
4. **View Sources** — Expand the "Sources & Citations" panel to see verified references

## API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Health check |
| `POST` | `/api/upload` | Upload and index PDF files |
| `POST` | `/api/query` | Ask a question with optional web search |

## Deploy Live

### Option 1: Render + Streamlit Community Cloud (Free — Recommended)

Best for a portfolio project. Zero cost.

**Step 1 — Push to GitHub**

```bash
cd researchpilot-ai
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/your-username/researchpilot-ai.git
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

### ⚠️ ChromaDB Persistence Note

On free-tier hosting (Render, Cloud Run), the filesystem resets on every deploy or restart. Your indexed PDFs will be lost. This is fine for a demo — just re-upload PDFs after a restart. For production persistence, attach a Render Disk ($0.25/GB/month) or switch to Chroma Cloud.

## Key Design Decisions

- **Two-layer anti-hallucination**: Similarity-distance threshold check *before* calling the LLM, plus a strict grounding system prompt
- **Verifiable citations**: Source metadata comes from the retrieval pipeline, not from the LLM
- **Local embeddings**: `all-MiniLM-L6-v2` runs on CPU with zero API costs
- **Simple web search toggle**: User controls whether web results are included (no autonomous agent decisions in MVP)

## License

MIT
