"""
ResearchPilot AI — LLM Module Tests

Tests for context block formatting, multi-turn content building,
and system prompt structure.
"""


import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import llm


# ---------------------------------------------------------------------------
# Context Block Tests
# ---------------------------------------------------------------------------

class TestBuildContextBlock:
    """Test the context block formatting for LLM prompts."""

    def test_empty_context(self):
        result = llm._build_context_block([], [])
        assert result == "(No context available)"

    def test_pdf_chunks_only(self):
        chunks = [
            {"filename": "paper.pdf", "page": 1, "text": "Introduction text here."},
            {"filename": "paper.pdf", "page": 3, "text": "Results text here."},
        ]
        result = llm._build_context_block(chunks, [])
        assert "=== PDF Document Sources ===" in result
        assert "paper.pdf" in result
        assert "Page: 1" in result
        assert "Page: 3" in result
        assert "Introduction text here." in result

    def test_web_results_only(self):
        web = [
            {"title": "Example", "url": "https://example.com", "snippet": "Web content."},
        ]
        result = llm._build_context_block([], web)
        assert "=== Web Search Results ===" in result
        assert "Example" in result
        assert "https://example.com" in result

    def test_combined_context(self):
        chunks = [{"filename": "a.pdf", "page": 1, "text": "PDF content."}]
        web = [{"title": "Web", "url": "https://web.com", "snippet": "Web content."}]
        result = llm._build_context_block(chunks, web)
        assert "PDF Document Sources" in result
        assert "Web Search Results" in result

    def test_rerank_score_included(self):
        chunks = [
            {"filename": "a.pdf", "page": 1, "text": "Content.", "similarity": 0.9512},
        ]
        result = llm._build_context_block(chunks, [])
        assert "Relevance: 0.9512" in result


# ---------------------------------------------------------------------------
# Content Building Tests
# ---------------------------------------------------------------------------

class TestBuildContents:
    """Test multi-turn content construction for Gemini."""

    def test_single_turn(self):
        contents = llm._build_contents("What is X?", "Context about X.")
        assert len(contents) == 1
        assert contents[0]["role"] == "user"
        assert "What is X?" in contents[0]["parts"][0]["text"]

    def test_with_chat_history(self):
        history = [
            {"role": "user", "content": "What is A?"},
            {"role": "assistant", "content": "A is..."},
        ]
        contents = llm._build_contents("What about B?", "Context.", history)
        assert len(contents) == 3  # 2 history + 1 current
        assert contents[0]["role"] == "user"
        assert contents[1]["role"] == "model"  # assistant → model for Gemini
        assert contents[2]["role"] == "user"

    def test_no_history(self):
        contents = llm._build_contents("Question?", "Context.", None)
        assert len(contents) == 1


# ---------------------------------------------------------------------------
# System Prompt Tests
# ---------------------------------------------------------------------------

class TestSystemPrompt:
    """Verify critical constraints are in the system prompt."""

    def test_grounding_instruction(self):
        assert "ONLY the retrieved context" in llm.SYSTEM_PROMPT

    def test_anti_hallucination(self):
        assert "Never invent citations" in llm.SYSTEM_PROMPT

    def test_markdown_instruction(self):
        assert "markdown" in llm.SYSTEM_PROMPT.lower()
