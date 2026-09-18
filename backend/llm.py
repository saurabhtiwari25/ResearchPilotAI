"""
ResearchPilot AI — LLM Module

Uses the Google Gemini API (google-genai SDK) to generate grounded answers
from retrieved context. Supports:
  - Multi-turn chat history for follow-up questions
  - Streaming responses for real-time token delivery
  - Strict grounding — the LLM is NOT responsible for inventing citations;
    source metadata is attached by the backend from the retrieval pipeline.
"""

import logging
from collections.abc import Generator

from google import genai

import config

logger = logging.getLogger("researchpilot.llm")

# ---------------------------------------------------------------------------
# Grounding System Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are ResearchPilot AI, a helpful research assistant.

Your job is to answer the user's question using ONLY the retrieved context provided below.

Rules:
- Answer only using the retrieved context.
- If the context does not contain enough information to answer, say "I don't have enough information in the provided sources."
- Never invent citations or sources.
- Cite only sources that are actually present in the retrieved context.
- When referencing information, mention the source filename and page number if available (e.g., "According to paper.pdf, page 3...").
- Be clear, concise, and well-structured in your response.
- Use markdown formatting for readability."""


def _build_context_block(pdf_chunks: list[dict], web_results: list[dict]) -> str:
    """
    Format retrieved chunks and web results into a single context block
    for injection into the LLM prompt.
    """
    parts: list[str] = []

    if pdf_chunks:
        parts.append("=== PDF Document Sources ===")
        for i, chunk in enumerate(pdf_chunks, start=1):
            relevance_info = ""
            if "similarity" in chunk:
                relevance_info = f" | Relevance: {chunk['similarity']:.4f}"
            parts.append(
                f"\n[Source {i}] File: {chunk['filename']} | Page: {chunk['page']}{relevance_info}\n"
                f"{chunk['text']}"
            )

    if web_results:
        parts.append("\n=== Web Search Results ===")
        for i, result in enumerate(web_results, start=1):
            parts.append(
                f"\n[Web Source {i}] Title: {result['title']} | URL: {result['url']}\n"
                f"{result['snippet']}"
            )

    if not parts:
        return "(No context available)"

    return "\n".join(parts)


def _build_contents(
    question: str,
    context: str,
    chat_history: list[dict] | None = None,
) -> list[dict]:
    """
    Build the multi-turn contents list for Gemini.

    If chat_history is provided, prior turns are included so the LLM
    can understand follow-up questions in context.

    chat_history format:
        [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]
    """
    contents: list[dict] = []

    # Include previous conversation turns (if any)
    if chat_history:
        for turn in chat_history:
            # Gemini expects 'user' and 'model' roles
            role = "model" if turn.get("role") == "assistant" else "user"
            contents.append({
                "role": role,
                "parts": [{"text": turn["content"]}],
            })

    # Current question with context
    user_prompt = f"""Retrieved Context:
{context}

User Question:
{question}

Please answer the question based on the retrieved context above."""

    contents.append({
        "role": "user",
        "parts": [{"text": user_prompt}],
    })

    return contents


def generate_answer(
    question: str,
    pdf_chunks: list[dict],
    web_results: list[dict] | None = None,
    chat_history: list[dict] | None = None,
) -> str:
    """
    Generate a grounded answer using Gemini.

    Args:
        question:     The user's research question.
        pdf_chunks:   Retrieved chunks from the RAG pipeline.
        web_results:  Optional web search results.
        chat_history: Optional list of prior conversation turns.

    Returns:
        The LLM-generated answer string.
    """
    if not config.GEMINI_API_KEY:
        return "Error: GEMINI_API_KEY is not configured. Please set it in your .env file."

    context = _build_context_block(pdf_chunks, web_results or [])
    contents = _build_contents(question, context, chat_history)

    try:
        client = genai.Client(api_key=config.GEMINI_API_KEY)

        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=contents,
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.3,
                max_output_tokens=2048,
            ),
        )

        logger.info("Generated answer for question: '%s...'", question[:60])
        return response.text or "The model returned an empty response."

    except Exception as e:
        logger.exception("Error generating answer: %s", e)
        return f"Error generating answer: {e}"


def generate_answer_stream(
    question: str,
    pdf_chunks: list[dict],
    web_results: list[dict] | None = None,
    chat_history: list[dict] | None = None,
) -> Generator[str, None, None]:
    """
    Generate a grounded answer using Gemini with streaming.

    Yields text chunks as they arrive from the model. This provides
    a dramatically better UX — the user sees tokens appearing in real-time.

    Args:
        question:     The user's research question.
        pdf_chunks:   Retrieved chunks from the RAG pipeline.
        web_results:  Optional web search results.
        chat_history: Optional list of prior conversation turns.

    Yields:
        Text chunks as they're generated by the model.
    """
    if not config.GEMINI_API_KEY:
        yield "Error: GEMINI_API_KEY is not configured. Please set it in your .env file."
        return

    context = _build_context_block(pdf_chunks, web_results or [])
    contents = _build_contents(question, context, chat_history)

    try:
        client = genai.Client(api_key=config.GEMINI_API_KEY)

        response_stream = client.models.generate_content_stream(
            model=config.GEMINI_MODEL,
            contents=contents,
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.3,
                max_output_tokens=2048,
            ),
        )

        for chunk in response_stream:
            if chunk.text:
                yield chunk.text

        logger.info("Streamed answer for question: '%s...'", question[:60])

    except Exception as e:
        logger.exception("Error streaming answer: %s", e)
        yield f"Error generating answer: {e}"
