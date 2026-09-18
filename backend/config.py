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

# --- Data Storage ---
DATA_DIR: str = os.getenv("DATA_DIR", "./data")

# --- RAG Settings ---
CHUNK_WORD_COUNT: int = 500
CHUNK_OVERLAP_WORDS: int = 50
SIMILARITY_THRESHOLD: float = 0.1      # Cosine similarity; higher = more similar (0.0–1.0)
TOP_K_RESULTS: int = 5

# --- Tavily ---
TAVILY_MAX_RESULTS: int = 5

# --- File Upload ---
UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
MAX_FILE_SIZE_MB: int = 50             # Maximum PDF file size in MB

# --- Logging ---
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
