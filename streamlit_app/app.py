"""
ResearchPilot AI — Streamlit Frontend

Premium single-page interactive UI with:
  - Dark glassmorphism design with gradient accents
  - Animated chat interface with streaming responses
  - Rich onboarding welcome experience
  - Styled source citation cards with relevance scores
  - Document management (upload, list, delete)
  - Chat history for follow-up questions
  - Conversation export to Markdown
  - Session analytics sidebar
"""

import json
import os
import time
from datetime import datetime

import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# Inline SVG Icons (no external font dependency)
# ---------------------------------------------------------------------------

SVG_DESCRIPTION = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor" style="vertical-align:middle;margin-right:4px;"><path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11zm-3-7H9v-2h6v2zm0 4H9v-2h6v2zm-2-8H9V7h4v2z"/></svg>'
SVG_LANGUAGE = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor" style="vertical-align:middle;margin-right:4px;"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zm6.93 6h-2.95c-.32-1.25-.78-2.45-1.38-3.56 1.84.63 3.37 1.91 4.33 3.56zM12 4.04c.83 1.2 1.48 2.53 1.91 3.96h-3.82c.43-1.43 1.08-2.76 1.91-3.96zM4.26 14C4.1 13.36 4 12.69 4 12s.1-1.36.26-2h3.38c-.08.66-.14 1.32-.14 2s.06 1.34.14 2H4.26zm.82 2h2.95c.32 1.25.78 2.45 1.38 3.56-1.84-.63-3.37-1.9-4.33-3.56zm2.95-8H5.08c.96-1.66 2.49-2.93 4.33-3.56C8.81 5.55 8.35 6.75 8.03 8zM12 19.96c-.83-1.2-1.48-2.53-1.91-3.96h3.82c-.43 1.43-1.08 2.76-1.91 3.96zM14.34 14H9.66c-.09-.66-.16-1.32-.16-2s.07-1.35.16-2h4.68c.09.65.16 1.32.16 2s-.07 1.34-.16 2zm.25 5.56c.6-1.11 1.06-2.31 1.38-3.56h2.95c-.96 1.65-2.49 2.93-4.33 3.56zM16.36 14c.08-.66.14-1.32.14-2s-.06-1.34-.14-2h3.38c.16.64.26 1.31.26 2s-.1 1.36-.26 2h-3.38z"/></svg>'
SVG_LIBRARY = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor" style="vertical-align:middle;margin-right:4px;"><path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9H9V9h10v2zm-4 4H9v-2h6v2zm4-8H9V5h10v2z"/></svg>'
SVG_CHAT = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="vertical-align:middle;margin-right:4px;"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>'
SVG_TIMER = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="vertical-align:middle;margin-right:4px;"><path d="M15 1H9v2h6V1zm-4 13h2V8h-2v6zm8.03-6.61 1.42-1.42c-.43-.51-.9-.99-1.41-1.41l-1.42 1.42C16.07 4.74 14.12 4 12 4c-4.97 0-9 4.03-9 9s4.03 9 9 9 9-4.03 9-9c0-2.12-.74-4.07-1.97-5.61zM12 20c-3.87 0-7-3.13-7-7s3.13-7 7-7 7 3.13 7 7-3.13 7-7 7z"/></svg>'
SVG_SCHEDULE = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" style="vertical-align:middle;margin-right:4px;"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67V7z"/></svg>'

# Large icons for feature cards
SVG_DESCRIPTION_LG = '<svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="#3b82f6"><path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11zm-3-7H9v-2h6v2zm0 4H9v-2h6v2zm-2-8H9V7h4v2z"/></svg>'
SVG_LANGUAGE_LG = '<svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="#8b5cf6"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zm6.93 6h-2.95c-.32-1.25-.78-2.45-1.38-3.56 1.84.63 3.37 1.91 4.33 3.56zM12 4.04c.83 1.2 1.48 2.53 1.91 3.96h-3.82c.43-1.43 1.08-2.76 1.91-3.96zM4.26 14C4.1 13.36 4 12.69 4 12s.1-1.36.26-2h3.38c-.08.66-.14 1.32-.14 2s.06 1.34.14 2H4.26zm.82 2h2.95c.32 1.25.78 2.45 1.38 3.56-1.84-.63-3.37-1.9-4.33-3.56zm2.95-8H5.08c.96-1.66 2.49-2.93 4.33-3.56C8.81 5.55 8.35 6.75 8.03 8zM12 19.96c-.83-1.2-1.48-2.53-1.91-3.96h3.82c-.43 1.43-1.08 2.76-1.91 3.96zM14.34 14H9.66c-.09-.66-.16-1.32-.16-2s.07-1.35.16-2h4.68c.09.65.16 1.32.16 2s-.07 1.34-.16 2zm.25 5.56c.6-1.11 1.06-2.31 1.38-3.56h2.95c-.96 1.65-2.49 2.93-4.33 3.56zM16.36 14c.08-.66.14-1.32.14-2s-.06-1.34-.14-2h3.38c.16.64.26 1.31.26 2s-.1 1.36-.26 2h-3.38z"/></svg>'
SVG_LIBRARY_LG = '<svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="#ec4899"><path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9H9V9h10v2zm-4 4H9v-2h6v2zm4-8H9V5h10v2z"/></svg>'

# ---------------------------------------------------------------------------
# Page Setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="ResearchPilot AI — AI Research Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Premium CSS Styling
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    /* --- Import Google Font --- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* --- Global (scoped to avoid breaking Streamlit icons) --- */
    .stMarkdown, .stChatMessage, .stTextInput, .stButton,
    .stCaption, .stExpander, h1, h2, h3, h4, h5, h6, p, span, div {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        max-width: 1400px;
        margin: 0 auto;
    }

    /* --- Sidebar Glassmorphism --- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(15,15,35,0.97) 0%, rgba(20,20,50,0.97) 100%) !important;
        backdrop-filter: blur(20px);
        border-right: 1px solid rgba(255,255,255,0.06);
    }

    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown li {
        color: #c0c0d0 !important;
    }

    /* --- Chat Message Styling --- */
    .stChatMessage {
        border-radius: 16px !important;
        padding: 16px 20px !important;
        margin-bottom: 12px !important;
        border: 1px solid rgba(255,255,255,0.04) !important;
        animation: fadeSlideIn 0.35s ease-out;
    }

    @keyframes fadeSlideIn {
        from {
            opacity: 0;
            transform: translateY(12px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    /* --- Source Citation Cards --- */
    .source-card {
        border-radius: 12px;
        padding: 16px 18px;
        margin-bottom: 10px;
        transition: all 0.25s ease;
        position: relative;
        overflow: hidden;
    }

    .source-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        border-radius: 4px 0 0 4px;
    }

    .source-card-pdf {
        background: linear-gradient(135deg, rgba(59,130,246,0.08) 0%, rgba(59,130,246,0.03) 100%);
        border: 1px solid rgba(59,130,246,0.15);
    }

    .source-card-pdf::before {
        background: linear-gradient(180deg, #3b82f6, #2563eb);
    }

    .source-card-web {
        background: linear-gradient(135deg, rgba(16,185,129,0.08) 0%, rgba(16,185,129,0.03) 100%);
        border: 1px solid rgba(16,185,129,0.15);
    }

    .source-card-web::before {
        background: linear-gradient(180deg, #10b981, #059669);
    }

    .source-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.3);
    }

    .source-card h4 {
        margin: 0 0 6px 0;
        font-size: 14px;
        font-weight: 600;
        color: #e0e0f0;
    }

    .source-card p {
        margin: 0;
        font-size: 13px;
        color: #999;
        line-height: 1.5;
    }

    .source-card .relevance-bar {
        height: 3px;
        border-radius: 3px;
        margin-top: 8px;
        background: rgba(255,255,255,0.05);
        overflow: hidden;
    }

    .source-card .relevance-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.5s ease;
    }

    .source-card-pdf .relevance-fill {
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
    }

    .source-card-web .relevance-fill {
        background: linear-gradient(90deg, #10b981, #06b6d4);
    }

    /* --- Welcome Card --- */
    .welcome-card {
        background: linear-gradient(135deg, rgba(59,130,246,0.06) 0%, rgba(139,92,246,0.06) 50%, rgba(236,72,153,0.06) 100%);
        border: 1px solid rgba(139,92,246,0.12);
        border-radius: 20px;
        padding: 40px;
        text-align: center;
        margin: 30px 0;
        animation: fadeIn 0.6s ease-out;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: scale(0.97); }
        to { opacity: 1; transform: scale(1); }
    }

    .welcome-card h2 {
        font-size: 28px;
        font-weight: 700;
        background: linear-gradient(135deg, #3b82f6, #8b5cf6, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 8px;
    }

    .welcome-card p {
        color: #888;
        font-size: 15px;
        max-width: 600px;
        margin: 0 auto 20px;
    }

    .feature-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
        margin: 24px 0;
    }

    .feature-item {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 20px 16px;
        transition: all 0.2s ease;
    }

    .feature-item:hover {
        border-color: rgba(139,92,246,0.3);
        background: rgba(139,92,246,0.05);
    }

    .feature-item .icon {
        font-size: 28px;
        margin-bottom: 8px;
    }

    .feature-item h4 {
        margin: 0 0 4px;
        font-size: 14px;
        font-weight: 600;
        color: #d0d0e0;
    }

    .feature-item p {
        margin: 0;
        font-size: 12px;
        color: #777;
    }

    /* --- Sample Question Buttons --- */
    .sample-q {
        background: rgba(139,92,246,0.08);
        border: 1px solid rgba(139,92,246,0.18);
        border-radius: 10px;
        padding: 10px 16px;
        margin: 4px;
        color: #b4a0e0;
        font-size: 13px;
        cursor: pointer;
        transition: all 0.2s ease;
        display: inline-block;
    }

    .sample-q:hover {
        background: rgba(139,92,246,0.15);
        border-color: rgba(139,92,246,0.3);
        color: #d0c0f0;
    }

    /* --- Stats Badge --- */
    .stat-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(59,130,246,0.08);
        border: 1px solid rgba(59,130,246,0.15);
        border-radius: 8px;
        padding: 6px 12px;
        font-size: 12px;
        color: #7cb3f0;
        margin: 2px;
    }

    /* --- Typing Indicator --- */
    .typing-indicator {
        display: flex;
        gap: 4px;
        padding: 8px 0;
    }

    .typing-indicator span {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #8b5cf6;
        animation: typingBounce 1.4s infinite ease-in-out;
    }

    .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
    .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

    @keyframes typingBounce {
        0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
        40% { transform: scale(1); opacity: 1; }
    }

    /* --- Divider styling --- */
    hr {
        border: none;
        border-top: 1px solid rgba(255,255,255,0.06);
        margin: 16px 0;
    }

    /* --- Header gradient text --- */
    .gradient-title {
        font-size: 24px;
        font-weight: 700;
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "indexed_files" not in st.session_state:
    st.session_state.indexed_files = []

if "query_count" not in st.session_state:
    st.session_state.query_count = 0

if "total_response_time" not in st.session_state:
    st.session_state.total_response_time = 0.0

if "session_start" not in st.session_state:
    st.session_state.session_start = time.time()


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def render_source_card(source: dict):
    """Render a styled source citation card."""
    if source["type"] == "pdf":
        # Calculate relevance percentage for visual bar
        similarity = source.get("similarity", 0.0)
        relevance_pct = min(max(int(similarity * 100), 10), 100) if similarity else 50

        st.markdown(f"""
        <div class="source-card source-card-pdf">
            <h4>{SVG_DESCRIPTION} {source['filename']} — Page {source['page']}</h4>
            <p>{source['snippet'][:180]}{'...' if len(source.get('snippet', '')) > 180 else ''}</p>
            <div class="relevance-bar">
                <div class="relevance-fill" style="width: {relevance_pct}%"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    elif source["type"] == "web":
        title = source.get("title", "Web Result")
        url = source.get("url", "#")
        st.markdown(f"""
        <div class="source-card source-card-web">
            <h4>{SVG_LANGUAGE} <a href="{url}" target="_blank" style="color: #10b981; text-decoration: none;">{title}</a></h4>
            <p>{source['snippet'][:180]}{'...' if len(source.get('snippet', '')) > 180 else ''}</p>
            <div class="relevance-bar">
                <div class="relevance-fill" style="width: 70%"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def export_conversation_markdown() -> str:
    """Export the current conversation as Markdown."""
    lines = [
        "# ResearchPilot AI — Conversation Export",
        f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Queries**: {st.session_state.query_count}",
        "",
        "---",
        "",
    ]

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            lines.append(f"## User\n\n{msg['content']}\n")
        else:
            lines.append(f"## ResearchPilot AI\n\n{msg['content']}\n")

            if msg.get("sources"):
                lines.append("### Sources\n")
                for src in msg["sources"]:
                    if src["type"] == "pdf":
                        lines.append(f"- **{src['filename']}** — Page {src['page']}")
                    elif src["type"] == "web":
                        lines.append(f"- [{src.get('title', 'Web')}]({src.get('url', '#')})")
                lines.append("")

        lines.append("---\n")

    return "\n".join(lines)


def process_sse_stream(response):
    """Parse SSE stream and yield (event_type, data) tuples."""
    buffer = ""
    for chunk in response.iter_content(decode_unicode=True):
        buffer += chunk
        while "\n\n" in buffer:
            event_block, buffer = buffer.split("\n\n", 1)
            event_type = ""
            data_lines = []
            for line in event_block.split("\n"):
                if line.startswith("event: "):
                    event_type = line[7:]
                elif line.startswith("data: "):
                    data_lines.append(line[6:])
                elif line.startswith("data:"):
                    data_lines.append(line[5:])
            data = "\n".join(data_lines)
            if event_type:
                yield event_type, data


# ---------------------------------------------------------------------------
# Sidebar — Premium Design
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown('<p class="gradient-title">ResearchPilot AI</p>', unsafe_allow_html=True)
    st.caption("Next-Gen AI Research Assistant")

    st.divider()

    # --- PDF Upload Section ---
    st.subheader("Upload PDFs")
    uploaded_files = st.file_uploader(
        "Upload PDF Documents",
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files:
        if st.button("Index Documents", use_container_width=True, type="primary"):
            with st.spinner("Extracting, chunking, and embedding..."):
                try:
                    files_payload = []
                    for f in uploaded_files:
                        files_payload.append(
                            ("files", (f.name, f.getvalue(), "application/pdf"))
                        )

                    response = requests.post(
                        f"{API_BASE_URL}/api/v1/upload",
                        files=files_payload,
                        timeout=120,
                    )

                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.indexed_files.extend(data["indexed_files"])
                        st.success(
                            f"Indexed **{len(data['indexed_files'])}** file(s) "
                            f"→ **{data['total_chunks']}** chunks"
                        )
                    else:
                        st.error(f"Upload failed: {response.text}")

                except requests.exceptions.ConnectionError:
                    st.error("Cannot connect to the backend. Is the FastAPI server running?")
                except Exception as e:
                    st.error(f"Error: {e}")

    # --- Indexed Documents (with delete) ---
    st.divider()
    st.subheader("Indexed Documents")

    try:
        doc_response = requests.get(f"{API_BASE_URL}/api/v1/documents", timeout=10)
        if doc_response.status_code == 200:
            doc_data = doc_response.json()
            if doc_data["documents"]:
                for doc in doc_data["documents"]:
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"{SVG_DESCRIPTION} `{doc['filename']}`  \n<small style='color:#666'>{doc['chunk_count']} chunks</small>", unsafe_allow_html=True)
                    with col2:
                        if st.button("Del", key=f"del_{doc['filename']}", help=f"Delete {doc['filename']}"):
                            del_resp = requests.delete(
                                f"{API_BASE_URL}/api/v1/documents/{doc['filename']}",
                                timeout=30,
                            )
                            if del_resp.status_code == 200:
                                st.success(f"Deleted {doc['filename']}")
                                st.rerun()
            else:
                st.caption("No documents indexed yet.")
        else:
            st.caption("Unable to fetch document list.")
    except requests.exceptions.ConnectionError:
        st.caption("Backend not connected.")
    except Exception:
        st.caption("No documents indexed yet.")

    st.divider()

    # --- Search Options ---
    st.subheader("Search Options")

    use_web_search = st.checkbox(
        "Include Web Search (Tavily)",
        value=False,
        help="When enabled, your question will also be searched on the web and results combined with PDF context.",
    )

    use_streaming = st.checkbox(
        "Stream Responses",
        value=True,
        help="See answer tokens appear in real-time as they're generated.",
    )

    st.divider()

    # --- Session Analytics ---
    st.subheader("Session Stats")
    elapsed = time.time() - st.session_state.session_start
    elapsed_min = int(elapsed // 60)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="stat-badge">{SVG_CHAT} {st.session_state.query_count} queries</div>
        """, unsafe_allow_html=True)
    with col2:
        avg_time = (
            st.session_state.total_response_time / st.session_state.query_count
            if st.session_state.query_count > 0 else 0
        )
        st.markdown(f"""
        <div class="stat-badge">{SVG_TIMER} {avg_time:.1f}s avg</div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="stat-badge">{SVG_SCHEDULE} {elapsed_min}m session</div>
    """, unsafe_allow_html=True)

    st.divider()

    # --- Actions ---
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.query_count = 0
            st.session_state.total_response_time = 0.0
            st.rerun()
    with col2:
        if st.session_state.messages:
            export_md = export_conversation_markdown()
            st.download_button(
                "Export",
                data=export_md,
                file_name=f"researchpilot_export_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                mime="text/markdown",
                use_container_width=True,
            )


# ---------------------------------------------------------------------------
# Main Area — Chat Interface
# ---------------------------------------------------------------------------

st.markdown('<p class="gradient-title">ResearchPilot AI</p>', unsafe_allow_html=True)
st.caption("Ask questions about your uploaded research documents • Powered by RAG + Gemini")

# --- Welcome Card (shown when no messages and no documents) ---
if not st.session_state.messages:
    st.markdown(f"""
<div class="welcome-card">
<h2>Welcome to ResearchPilot AI</h2>
<p>Upload your research PDFs and ask questions. I'll find answers grounded in your documents with verifiable citations.</p>
<div class="feature-grid">
<div class="feature-item">
<div class="icon">{SVG_DESCRIPTION_LG}</div>
<h4>Smart PDF Search</h4>
<p>Search your documents for relevant context and key answers</p>
</div>
<div class="feature-item">
<div class="icon">{SVG_LANGUAGE_LG}</div>
<h4>Web Augmentation</h4>
<p>Optionally combine web results for broader context</p>
</div>
<div class="feature-item">
<div class="icon">{SVG_LIBRARY_LG}</div>
<h4>Verified Citations</h4>
<p>Every claim traced back to source documents with page numbers</p>
</div>
</div>
</div>
""", unsafe_allow_html=True)

    # Sample questions
    st.markdown("**Try asking:**")
    sample_cols = st.columns(3)
    sample_questions = [
        "Summarize the key findings of this paper",
        "What methodology was used in the study?",
        "Compare the results across different experiments",
    ]
    for i, sq in enumerate(sample_questions):
        with sample_cols[i]:
            if st.button(f"{sq}", key=f"sample_{i}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": sq})
                st.rerun()


# --- Display chat history ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # Show sources if available
        if msg.get("sources"):
            with st.expander("Sources & Citations", expanded=False):
                for source in msg["sources"]:
                    render_source_card(source)


# --- Chat Input ---
if prompt := st.chat_input("Ask a research question..."):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call the backend
    with st.chat_message("assistant"):
        query_start = time.time()

        # Build chat history for the API (last 10 messages)
        chat_history = []
        for msg in st.session_state.messages[:-1]:  # Exclude the current message
            chat_history.append({
                "role": msg["role"],
                "content": msg["content"],
            })
        chat_history = chat_history[-10:]  # Keep only last 10 turns

        if use_streaming:
            # --- STREAMING MODE ---
            try:
                # Show typing indicator
                typing_placeholder = st.empty()
                typing_placeholder.markdown("""
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
                """, unsafe_allow_html=True)

                response = requests.post(
                    f"{API_BASE_URL}/api/v1/query/stream",
                    json={
                        "question": prompt,
                        "use_web_search": use_web_search,
                        "chat_history": chat_history,
                    },
                    stream=True,
                    timeout=120,
                )

                typing_placeholder.empty()

                if response.status_code == 200:
                    answer_tokens = []
                    sources = []
                    answer_placeholder = st.empty()

                    for event_type, data in process_sse_stream(response):
                        if event_type == "token":
                            answer_tokens.append(data)
                            answer_placeholder.markdown("".join(answer_tokens))
                        elif event_type == "sources":
                            try:
                                sources = json.loads(data)
                            except json.JSONDecodeError:
                                sources = []
                        elif event_type == "error":
                            st.error(data)
                        elif event_type == "done":
                            break

                    full_answer = "".join(answer_tokens)

                    # Display sources
                    if sources:
                        with st.expander("Sources & Citations", expanded=True):
                            for source in sources:
                                render_source_card(source)

                    # Track analytics
                    query_time = time.time() - query_start
                    st.session_state.query_count += 1
                    st.session_state.total_response_time += query_time

                    # Save to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": full_answer,
                        "sources": sources,
                    })

                else:
                    st.error(f"Backend error: {response.text}")

            except requests.exceptions.ConnectionError:
                st.error("Cannot connect to the backend. Is the FastAPI server running on port 8000?")
            except Exception as e:
                st.error(f"Error: {e}")

        else:
            # --- STANDARD MODE ---
            with st.status("Researching...", expanded=True) as status:
                st.write("Searching document knowledge base...")
                if use_web_search:
                    st.write("Searching the web via Tavily...")

                try:
                    response = requests.post(
                        f"{API_BASE_URL}/api/v1/query",
                        json={
                            "question": prompt,
                            "use_web_search": use_web_search,
                            "chat_history": chat_history,
                        },
                        timeout=60,
                    )

                    if response.status_code == 200:
                        data = response.json()
                        answer = data["answer"]
                        sources = data["sources"]

                        status.update(label="Done!", state="complete", expanded=False)

                        # Display the answer
                        st.markdown(answer)

                        # Display sources
                        if sources:
                            with st.expander("Sources & Citations", expanded=True):
                                for source in sources:
                                    render_source_card(source)

                        # Track analytics
                        query_time = time.time() - query_start
                        st.session_state.query_count += 1
                        st.session_state.total_response_time += query_time

                        # Save to chat history
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": answer,
                            "sources": sources,
                        })

                    else:
                        error_msg = f"Backend error: {response.text}"
                        status.update(label="Error", state="error", expanded=False)
                        st.error(error_msg)

                except requests.exceptions.ConnectionError:
                    status.update(label="Connection Error", state="error", expanded=False)
                    st.error("Cannot connect to the backend. Is the FastAPI server running on port 8000?")
                except Exception as e:
                    status.update(label="Error", state="error", expanded=False)
                    st.error(f"Error: {e}")
