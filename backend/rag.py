"""
ResearchPilot AI — RAG Module

Handles PDF text extraction, sentence-aware chunking, TF-IDF vectorization,
brute-force cosine similarity search, relevance threshold filtering,
and duplicate document detection.

Storage: Chunks are persisted in a local JSON file.
Search:  TF-IDF vectors + cosine similarity (no neural network needed).
"""

import hashlib
import json
import logging
import os
import re
import uuid
from collections import Counter
from typing import Optional

from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import config

logger = logging.getLogger("researchpilot.rag")

# ---------------------------------------------------------------------------
# In-memory document store + TF-IDF index
# ---------------------------------------------------------------------------

_chunks: list[dict] = []           # [{id, text, filename, page, snippet, file_hash}]
_tfidf_vectorizer: Optional[TfidfVectorizer] = None
_tfidf_matrix = None               # scipy sparse matrix (docs × features)
_index_dirty: bool = True          # Flag to rebuild TF-IDF after changes

STORE_PATH = os.path.join(config.DATA_DIR, "chunks.json")


def _save_store():
    """Persist chunks to disk as a JSON file."""
    os.makedirs(os.path.dirname(STORE_PATH), exist_ok=True)
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(_chunks, f, ensure_ascii=False)
    logger.info("Saved %d chunks to disk.", len(_chunks))


def _load_store():
    """Load chunks from the JSON file on disk."""
    global _chunks
    if os.path.exists(STORE_PATH):
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            _chunks = json.load(f)
        logger.info("Loaded %d chunks from disk.", len(_chunks))
    else:
        _chunks = []


def _rebuild_tfidf():
    """Rebuild the TF-IDF matrix from the current chunk store."""
    global _tfidf_vectorizer, _tfidf_matrix, _index_dirty

    if not _chunks:
        _tfidf_vectorizer = None
        _tfidf_matrix = None
        _index_dirty = False
        return

    _tfidf_vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=10000,
        sublinear_tf=True,      # Apply log normalization to term frequencies
    )
    texts = [chunk["text"] for chunk in _chunks]
    _tfidf_matrix = _tfidf_vectorizer.fit_transform(texts)
    _index_dirty = False

    logger.info(
        "TF-IDF index rebuilt: %d documents, %d features.",
        _tfidf_matrix.shape[0],
        _tfidf_matrix.shape[1],
    )


def _ensure_index():
    """Rebuild the TF-IDF index if it's stale."""
    if _index_dirty:
        _rebuild_tfidf()


# ---------------------------------------------------------------------------
# Module Initialization — load persisted chunks on import
# ---------------------------------------------------------------------------

_load_store()
_rebuild_tfidf()


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
# Sentence-Aware Chunking
# ---------------------------------------------------------------------------

_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences using regex boundary detection."""
    sentences = _SENTENCE_SPLIT_RE.split(text)
    return [s.strip() for s in sentences if s.strip()]


def chunk_text(
    text: str,
    chunk_size: int = config.CHUNK_WORD_COUNT,
    overlap: int = config.CHUNK_OVERLAP_WORDS,
) -> list[str]:
    """
    Split text into chunks of approximately `chunk_size` words,
    breaking at sentence boundaries where possible, with `overlap`
    words of overlap between consecutive chunks.

    This is a significant improvement over naive word-count splitting —
    chunks won't cut mid-sentence, producing more coherent passages.
    """
    sentences = _split_sentences(text)

    # Fallback to word-based splitting if there are no clear sentence boundaries
    # or if the entire text is just one massive sentence that exceeds chunk_size.
    if not sentences or (len(sentences) == 1 and len(sentences[0].split()) > chunk_size):
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

    chunks: list[str] = []
    current_chunk_sentences: list[str] = []
    current_word_count = 0

    for sentence in sentences:
        sentence_words = len(sentence.split())

        if current_word_count + sentence_words > chunk_size and current_chunk_sentences:
            # Emit the current chunk
            chunks.append(" ".join(current_chunk_sentences))

            # Calculate overlap: keep trailing sentences that fit in `overlap` words
            overlap_sentences: list[str] = []
            overlap_words = 0
            for s in reversed(current_chunk_sentences):
                s_words = len(s.split())
                if overlap_words + s_words > overlap:
                    break
                overlap_sentences.insert(0, s)
                overlap_words += s_words

            current_chunk_sentences = overlap_sentences
            current_word_count = overlap_words

        current_chunk_sentences.append(sentence)
        current_word_count += sentence_words

    # Emit the last chunk
    if current_chunk_sentences:
        chunks.append(" ".join(current_chunk_sentences))

    return chunks


# ---------------------------------------------------------------------------
# Document Hashing (Duplicate Detection)
# ---------------------------------------------------------------------------

def _compute_file_hash(pdf_path: str) -> str:
    """Compute SHA-256 hash of a PDF file for duplicate detection."""
    sha = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            sha.update(block)
    return sha.hexdigest()


def is_document_indexed(filename: str) -> bool:
    """Check if a document with this filename is already in the store."""
    return any(chunk["filename"] == filename for chunk in _chunks)


# ---------------------------------------------------------------------------
# Indexing Pipeline
# ---------------------------------------------------------------------------

def index_pdf(pdf_path: str, filename: str) -> int:
    """
    Full indexing pipeline for a single PDF:
      1. Check for duplicates
      2. Extract text per page
      3. Chunk each page's text (sentence-aware)
      4. Store chunks with metadata in the JSON store

    Returns the total number of chunks indexed.
    """
    global _index_dirty

    # Duplicate detection
    if is_document_indexed(filename):
        logger.warning("Document '%s' is already indexed. Re-indexing...", filename)
        delete_document(filename)

    pages = extract_text_from_pdf(pdf_path)
    file_hash = _compute_file_hash(pdf_path)

    new_chunks: list[dict] = []

    for page_data in pages:
        page_num = page_data["page"]
        chunks = chunk_text(page_data["text"])

        for chunk in chunks:
            new_chunks.append({
                "id": str(uuid.uuid4()),
                "text": chunk,
                "filename": filename,
                "page": page_num,
                "snippet": chunk[:200],
                "file_hash": file_hash,
            })

    if not new_chunks:
        logger.warning("No text extracted from '%s'.", filename)
        return 0

    # Add to in-memory store
    _chunks.extend(new_chunks)

    # Persist to disk
    _save_store()

    # Mark TF-IDF index as stale
    _index_dirty = True

    logger.info("Indexed '%s': %d chunks stored.", filename, len(new_chunks))
    return len(new_chunks)


# ---------------------------------------------------------------------------
# Document Management
# ---------------------------------------------------------------------------

def list_indexed_documents() -> list[dict]:
    """
    List all uniquely indexed document filenames with their chunk counts.

    Returns:
        [{"filename": "paper.pdf", "chunk_count": 42}, ...]
    """
    if not _chunks:
        return []

    doc_counts: Counter = Counter()
    for chunk in _chunks:
        doc_counts[chunk.get("filename", "unknown")] += 1

    return [
        {"filename": fname, "chunk_count": count}
        for fname, count in sorted(doc_counts.items())
    ]


def delete_document(filename: str) -> int:
    """
    Delete all chunks belonging to a document by filename.

    Returns the number of chunks deleted.
    """
    global _chunks, _index_dirty

    original_count = len(_chunks)
    _chunks = [c for c in _chunks if c["filename"] != filename]
    deleted = original_count - len(_chunks)

    if deleted == 0:
        logger.info("No chunks found for '%s'.", filename)
        return 0

    # Persist changes and mark index as stale
    _save_store()
    _index_dirty = True

    logger.info("Deleted %d chunks for '%s'.", deleted, filename)
    return deleted


# ---------------------------------------------------------------------------
# TF-IDF + Brute-Force Cosine Similarity Search
# ---------------------------------------------------------------------------

def search_documents(query: str, top_k: int = config.TOP_K_RESULTS) -> list[dict]:
    """
    Search for relevant chunks using TF-IDF vectorization and
    brute-force cosine similarity.

    Transforms the query into a TF-IDF vector using the same vocabulary
    fitted on all stored chunks, then computes cosine similarity against
    every chunk. Returns the top-K most similar chunks that exceed the
    minimum similarity threshold.

    Returns a list of result dicts, each containing:
        {
            "text": "...",
            "filename": "...",
            "page": 4,
            "snippet": "...",
            "similarity": 0.72,
        }
    """
    if not _chunks:
        return []

    # Ensure TF-IDF index is up to date
    _ensure_index()

    if _tfidf_vectorizer is None or _tfidf_matrix is None:
        return []

    # Vectorize the query using the same fitted vocabulary
    query_vector = _tfidf_vectorizer.transform([query])

    # Brute-force cosine similarity against every chunk
    similarities = cosine_similarity(query_vector, _tfidf_matrix).flatten()

    # Pair chunks with their similarity scores and filter by threshold
    scored_chunks: list[dict] = []
    for i, score in enumerate(similarities):
        if score >= config.SIMILARITY_THRESHOLD:
            chunk = _chunks[i]
            scored_chunks.append({
                "text": chunk["text"],
                "filename": chunk["filename"],
                "page": chunk["page"],
                "snippet": chunk["snippet"],
                "similarity": round(float(score), 4),
            })

    # Sort by similarity (descending) and take top-K
    scored_chunks.sort(key=lambda x: x["similarity"], reverse=True)

    logger.info(
        "TF-IDF search returned %d results (threshold: %.2f).",
        len(scored_chunks[:top_k]),
        config.SIMILARITY_THRESHOLD,
    )

    return scored_chunks[:top_k]


def retrieved_chunks_meet_threshold(results: list[dict]) -> bool:
    """
    Return True if at least one retrieved chunk meets the relevance threshold.
    This is a simple check: if the search function already filters by threshold,
    any non-empty result list means we have relevant chunks.
    """
    return len(results) > 0
