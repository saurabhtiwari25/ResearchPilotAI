"""
ResearchPilot AI — LLM Module

Uses the Google Gemini API (google-genai SDK) to generate grounded answers
from retrieved context. The LLM is NOT responsible for inventing citations —
source metadata is attached by the backend from the retrieval pipeline.
"""

from google import genai

import config

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
            parts.append(
                f"\n[Source {i}] File: {chunk['filename']} | Page: {chunk['page']}\n"
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


def generate_answer(
    question: str,
    pdf_chunks: list[dict],
    web_results: list[dict] | None = None,
) -> str:
    """
    Generate a grounded answer using Gemini.

    Args:
        question:    The user's research question.
        pdf_chunks:  Retrieved chunks from ChromaDB (list of dicts with text, filename, page).
        web_results: Optional web search results (list of dicts with title, url, snippet).

    Returns:
        The LLM-generated answer string.
    """
    if not config.GEMINI_API_KEY:
        return "Error: GEMINI_API_KEY is not configured. Please set it in your .env file."

    context = _build_context_block(pdf_chunks, web_results or [])

    user_prompt = f"""Retrieved Context:
{context}

User Question:
{question}

Please answer the question based on the retrieved context above."""

    try:
        client = genai.Client(api_key=config.GEMINI_API_KEY)

        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=user_prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.3,
                max_output_tokens=2048,
            ),
        )

        return response.text or "The model returned an empty response."

    except Exception as e:
        return f"Error generating answer: {e}"
