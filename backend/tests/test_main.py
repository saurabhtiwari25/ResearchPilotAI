"""
ResearchPilot AI — API Integration Tests

Tests for FastAPI endpoints using TestClient.
"""

from fastapi.testclient import TestClient
from unittest.mock import patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    """Test the health check endpoint."""

    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_body(self):
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "ResearchPilot AI"
        assert "version" in data


# ---------------------------------------------------------------------------
# Upload Endpoint
# ---------------------------------------------------------------------------

class TestUploadEndpoint:
    """Test the PDF upload endpoint."""

    def test_upload_rejects_non_pdf(self):
        """Non-PDF files should be silently skipped."""
        response = client.post(
            "/api/v1/upload",
            files=[("files", ("test.txt", b"plain text", "text/plain"))],
        )
        assert response.status_code == 200
        data = response.json()
        assert data["indexed_files"] == []
        assert data["total_chunks"] == 0

    @patch("rag.index_pdf")
    def test_upload_pdf_success(self, mock_index):
        """Valid PDF upload should index and return chunk count."""
        mock_index.return_value = 10

        # Create a minimal PDF-like content (won't actually be parsed in mock)
        pdf_content = b"%PDF-1.4 fake pdf content"
        response = client.post(
            "/api/v1/upload",
            files=[("files", ("test.pdf", pdf_content, "application/pdf"))],
        )
        assert response.status_code == 200
        data = response.json()
        assert "test.pdf" in data["indexed_files"]
        assert data["total_chunks"] == 10


# ---------------------------------------------------------------------------
# Query Endpoint
# ---------------------------------------------------------------------------

class TestQueryEndpoint:
    """Test the query endpoint."""

    def test_empty_question_returns_message(self):
        response = client.post(
            "/api/v1/query",
            json={"question": "   ", "use_web_search": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert "enter a question" in data["answer"].lower()

    @patch("llm.generate_answer")
    @patch("rag.search_documents")
    def test_query_with_results(self, mock_search, mock_llm):
        """Query with matching documents should return answer + sources."""
        mock_search.return_value = [
            {"text": "Content", "filename": "doc.pdf", "page": 1,
             "snippet": "Content...", "similarity": 0.85},
        ]
        mock_llm.return_value = "The answer based on the document."

        response = client.post(
            "/api/v1/query",
            json={"question": "What is this about?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["sources"]) > 0

    @patch("rag.search_documents")
    def test_query_no_context_returns_fallback(self, mock_search):
        """Query with no matching documents should return fallback message."""
        mock_search.return_value = []

        response = client.post(
            "/api/v1/query",
            json={"question": "Something completely unrelated"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "don't have enough" in data["answer"].lower()


# ---------------------------------------------------------------------------
# Document Management Endpoints
# ---------------------------------------------------------------------------

class TestDocumentManagement:
    """Test document list and delete endpoints."""

    @patch("rag.list_indexed_documents")
    def test_list_documents(self, mock_list):
        mock_list.return_value = [
            {"filename": "paper.pdf", "chunk_count": 25},
        ]
        response = client.get("/api/v1/documents")
        assert response.status_code == 200
        data = response.json()
        assert data["total_documents"] == 1
        assert data["documents"][0]["filename"] == "paper.pdf"

    @patch("rag.delete_document")
    def test_delete_document(self, mock_delete):
        mock_delete.return_value = 25
        response = client.delete("/api/v1/documents/paper.pdf")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        assert data["chunks_deleted"] == 25

    @patch("rag.delete_document")
    def test_delete_nonexistent_document(self, mock_delete):
        mock_delete.return_value = 0
        response = client.delete("/api/v1/documents/nonexistent.pdf")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_found"


# ---------------------------------------------------------------------------
# Legacy Endpoint Compatibility
# ---------------------------------------------------------------------------

class TestLegacyEndpoints:
    """Verify legacy /api/ endpoints still work."""

    def test_legacy_query_empty(self):
        response = client.post(
            "/api/query",
            json={"question": "", "use_web_search": False},
        )
        assert response.status_code == 200
