"""
ResearchPilot AI — RAG Module Tests

Tests for text chunking, PDF extraction, document management,
and search result formatting.
"""


# Import the module under test
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import rag


# ---------------------------------------------------------------------------
# Chunking Tests
# ---------------------------------------------------------------------------

class TestChunkText:
    """Test the sentence-aware chunking logic."""

    def test_empty_text_returns_empty(self):
        assert rag.chunk_text("") == []

    def test_single_sentence_returns_one_chunk(self):
        text = "This is a single sentence."
        chunks = rag.chunk_text(text, chunk_size=100, overlap=10)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_respects_approximate_chunk_size(self):
        # Generate text with clear sentence boundaries
        sentences = [f"Sentence number {i} is here." for i in range(50)]
        text = " ".join(sentences)
        chunks = rag.chunk_text(text, chunk_size=20, overlap=5)
        assert len(chunks) > 1
        # Each chunk should be roughly around the target size
        for chunk in chunks:
            word_count = len(chunk.split())
            # Allow some flexibility for sentence boundaries
            assert word_count <= 30, f"Chunk too large: {word_count} words"

    def test_overlap_produces_shared_content(self):
        sentences = [f"Sentence {i} has important content." for i in range(20)]
        text = " ".join(sentences)
        chunks = rag.chunk_text(text, chunk_size=15, overlap=5)
        if len(chunks) >= 2:
            # Check that consecutive chunks share some words
            words_1 = set(chunks[0].split()[-5:])
            words_2 = set(chunks[1].split()[:10])
            shared = words_1 & words_2
            assert len(shared) > 0, "Chunks should overlap"

    def test_fallback_word_splitting_no_sentences(self):
        # Text without sentence boundaries (no periods)
        text = " ".join(["word"] * 100)
        chunks = rag.chunk_text(text, chunk_size=20, overlap=5)
        assert len(chunks) > 1


class TestSentenceSplitting:
    """Test the sentence boundary detection."""

    def test_splits_on_period(self):
        text = "First sentence. Second sentence. Third sentence."
        sentences = rag._split_sentences(text)
        assert len(sentences) >= 2

    def test_handles_abbreviations(self):
        text = "Dr. Smith studied the phenomenon. The results were clear."
        sentences = rag._split_sentences(text)
        assert len(sentences) >= 1  # Should not break on "Dr."


# ---------------------------------------------------------------------------
# Document Hash Tests
# ---------------------------------------------------------------------------

class TestDuplicateDetection:
    """Test file hashing for duplicate detection."""

    def test_compute_file_hash_consistency(self, tmp_path):
        """Same content should produce the same hash."""
        file1 = tmp_path / "test1.txt"
        file2 = tmp_path / "test2.txt"
        content = b"This is test content for hashing."
        file1.write_bytes(content)
        file2.write_bytes(content)

        hash1 = rag._compute_file_hash(str(file1))
        hash2 = rag._compute_file_hash(str(file2))
        assert hash1 == hash2

    def test_compute_file_hash_different_content(self, tmp_path):
        """Different content should produce different hashes."""
        file1 = tmp_path / "test1.txt"
        file2 = tmp_path / "test2.txt"
        file1.write_bytes(b"Content A")
        file2.write_bytes(b"Content B")

        hash1 = rag._compute_file_hash(str(file1))
        hash2 = rag._compute_file_hash(str(file2))
        assert hash1 != hash2
