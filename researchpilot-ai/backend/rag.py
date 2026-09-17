"""
ResearchPilot AI — RAG Module

Handles PDF text extraction, word-based chunking, embedding generation,
ChromaDB storage, and similarity search with relevance threshold filtering.
"""

import os
import uuid
from typing import Optional

import chromadb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

import config

# ---------------------------------------------------------------------------
# Singleton-style module-level resources (initialized on first use)
# ---------------------------------------------------------------------------

_embedding_model: Optional[SentenceTransformer] = None
_chroma_client: Optional[chromadb.ClientAPI] = None
_collection: Optional[chromadb.Collection] = None


def _get_embedding_model() -> SentenceTransformer:
    """Lazy-load the SentenceTransformer embedding model."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
    return _embedding_model


def _get_collection() -> chromadb.Collection:
    """Lazy-load the ChromaDB persistent client and collection."""
    global _chroma_client, _collection
    if _collection is None:
        os.makedirs(config.CHROMA_PERSIST_DIR, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)
        _collection = _chroma_client.get_or_create_collection(
            name=config.CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "l2"},
        )
    return _collection


# ---------------------------------------------------------------------------
# PDF Extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(pdf_path: str) -> list[dict]:
    """
    Extract text from each page of a PDF file.

    Returns a list of dicts:
        [{"page": 1, "text": "..."}, {"page": 2, "text": "..."}, ...]
    """
    reader = PdfReader(pdf_path)
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            pages.append({"page": i, "text": text})
    return pages


# ---------------------------------------------------------------------------
# Word-Based Chunking
# ---------------------------------------------------------------------------

def chunk_text(
    text: str,
    chunk_size: int = config.CHUNK_WORD_COUNT,
    overlap: int = config.CHUNK_OVERLAP_WORDS,
) -> list[str]:
    """
    Split text into chunks of approximately `chunk_size` words
    with `overlap` words of overlap between consecutive chunks.
    """
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


# ---------------------------------------------------------------------------
# Indexing Pipeline
# ---------------------------------------------------------------------------

def index_pdf(pdf_path: str, filename: str) -> int:
    """
    Full indexing pipeline for a single PDF:
      1. Extract text per page
      2. Chunk each page's text
      3. Embed chunks
      4. Store in ChromaDB with metadata

    Returns the total number of chunks indexed.
    """
    pages = extract_text_from_pdf(pdf_path)
    model = _get_embedding_model()
    collection = _get_collection()

    all_chunks: list[str] = []
    all_metadatas: list[dict] = []
    all_ids: list[str] = []

    for page_data in pages:
        page_num = page_data["page"]
        chunks = chunk_text(page_data["text"])

        for chunk in chunks:
            all_chunks.append(chunk)
            all_metadatas.append({
                "filename": filename,
                "page": page_num,
                "snippet": chunk[:200],     # first 200 chars as a readable snippet
            })
            all_ids.append(str(uuid.uuid4()))

    if not all_chunks:
        return 0

    # Generate embeddings in a single batch
    embeddings = model.encode(all_chunks).tolist()

    # Upsert into ChromaDB
    collection.add(
        ids=all_ids,
        documents=all_chunks,
        embeddings=embeddings,
        metadatas=all_metadatas,
    )

    return len(all_chunks)


# ---------------------------------------------------------------------------
# Similarity Search with Relevance Threshold
# ---------------------------------------------------------------------------

def search_documents(query: str, top_k: int = config.TOP_K_RESULTS) -> list[dict]:
    """
    Search ChromaDB for chunks similar to the query.

    Returns a list of result dicts, each containing:
        {
            "text": "...",
            "filename": "...",
            "page": 4,
            "snippet": "...",
            "distance": 0.42,
        }

    Only chunks with distance <= RELEVANCE_THRESHOLD are included.
    """
    collection = _get_collection()

    # Check if the collection is empty
    if collection.count() == 0:
        return []

    model = _get_embedding_model()
    query_embedding = model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    hits: list[dict] = []
    if results and results["documents"]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # Apply relevance threshold (L2 distance: lower = more similar)
            if dist <= config.RELEVANCE_THRESHOLD:
                hits.append({
                    "text": doc,
                    "filename": meta.get("filename", ""),
                    "page": meta.get("page", 0),
                    "snippet": meta.get("snippet", ""),
                    "distance": round(dist, 4),
                })

    return hits


def retrieved_chunks_meet_threshold(results: list[dict]) -> bool:
    """
    Return True if at least one retrieved chunk meets the relevance threshold.
    This is a simple check: if the search function already filters by threshold,
    any non-empty result list means we have relevant chunks.
    """
    return len(results) > 0
