"""
ResearchPilot AI — Application Configuration

Loads environment variables and provides centralized settings.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

# --- Gemini Model ---
GEMINI_MODEL: str = "gemini-2.0-flash"

# --- Embedding Model ---
EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

# --- ChromaDB ---
CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
CHROMA_COLLECTION_NAME: str = "research_documents"

# --- RAG Settings ---
CHUNK_WORD_COUNT: int = 500
CHUNK_OVERLAP_WORDS: int = 50
RELEVANCE_THRESHOLD: float = 1.2       # ChromaDB L2 distance; lower = more similar
TOP_K_RESULTS: int = 5

# --- Tavily ---
TAVILY_MAX_RESULTS: int = 5

# --- File Upload ---
UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
