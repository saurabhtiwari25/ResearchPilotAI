"""
ResearchPilot AI — Streamlit Frontend

Single-page interactive UI:
  - Sidebar: PDF uploader + Index Documents button
  - Main: Chat interface with web search toggle
  - Citations panel with verified source metadata
"""

import os
import streamlit as st
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# Page Setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="ResearchPilot AI",
    page_icon="🔬",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Custom CSS for a cleaner look
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .source-card {
        border: 1px solid #444;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
        background-color: #1e1e2e;
    }
    .source-card h4 {
        margin: 0 0 4px 0;
        font-size: 14px;
    }
    .source-card p {
        margin: 0;
        font-size: 13px;
        color: #aaa;
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


# ---------------------------------------------------------------------------
# Sidebar — PDF Upload & Document Management
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("🔬 ResearchPilot AI")
    st.caption("AI Research Assistant with RAG")

    st.divider()

    # PDF Upload Section
    st.subheader("📄 Upload PDFs")
    uploaded_files = st.file_uploader(
        "Drag and drop PDF files here",
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files:
        if st.button("📥 Index Documents", use_container_width=True, type="primary"):
            with st.spinner("Extracting, chunking, and embedding..."):
                try:
                    files_payload = []
                    for f in uploaded_files:
                        files_payload.append(
                            ("files", (f.name, f.getvalue(), "application/pdf"))
                        )

                    response = requests.post(
                        f"{API_BASE_URL}/api/upload",
                        files=files_payload,
                        timeout=120,
                    )

                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.indexed_files.extend(data["indexed_files"])
                        st.success(
                            f"✅ Indexed **{len(data['indexed_files'])}** file(s) "
                            f"→ **{data['total_chunks']}** chunks"
                        )
                    else:
                        st.error(f"Upload failed: {response.text}")

                except requests.exceptions.ConnectionError:
                    st.error("❌ Cannot connect to the backend. Is the FastAPI server running?")
                except Exception as e:
                    st.error(f"Error: {e}")

    # Show indexed files
    if st.session_state.indexed_files:
        st.divider()
        st.subheader("📚 Indexed Documents")
        for fname in set(st.session_state.indexed_files):
            st.markdown(f"- `{fname}`")

    st.divider()

    # Web search toggle
    use_web_search = st.checkbox(
        "🌐 Include Web Search (Tavily)",
        value=False,
        help="When enabled, your question will also be searched on the web and results combined with PDF context.",
    )

    st.divider()

    # Clear chat
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# ---------------------------------------------------------------------------
# Main Area — Chat Interface
# ---------------------------------------------------------------------------

st.title("🔬 ResearchPilot AI")
st.caption("Ask questions about your uploaded research documents")

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # Show sources if available
        if msg.get("sources"):
            with st.expander("📚 Sources & Citations", expanded=False):
                for source in msg["sources"]:
                    if source["type"] == "pdf":
                        st.markdown(
                            f"**📄 {source['filename']}** — Page {source['page']}\n\n"
                            f">{source['snippet']}"
                        )
                    elif source["type"] == "web":
                        st.markdown(
                            f"**🌐 [{source['title']}]({source['url']})**\n\n"
                            f">{source['snippet']}"
                        )
                    st.divider()


# Chat input
if prompt := st.chat_input("Ask a research question..."):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call the backend
    with st.chat_message("assistant"):
        with st.status("🔍 Researching...", expanded=True) as status:
            st.write("Searching document knowledge base...")
            if use_web_search:
                st.write("Searching the web via Tavily...")

            try:
                response = requests.post(
                    f"{API_BASE_URL}/api/query",
                    json={
                        "question": prompt,
                        "use_web_search": use_web_search,
                    },
                    timeout=60,
                )

                if response.status_code == 200:
                    data = response.json()
                    answer = data["answer"]
                    sources = data["sources"]

                    status.update(label="✅ Done!", state="complete", expanded=False)

                    # Display the answer
                    st.markdown(answer)

                    # Display sources
                    if sources:
                        with st.expander("📚 Sources & Citations", expanded=True):
                            for source in sources:
                                if source["type"] == "pdf":
                                    st.markdown(
                                        f"**📄 {source['filename']}** — Page {source['page']}\n\n"
                                        f">{source['snippet']}"
                                    )
                                elif source["type"] == "web":
                                    st.markdown(
                                        f"**🌐 [{source.get('title', 'Web Result')}]({source.get('url', '#')})**\n\n"
                                        f">{source['snippet']}"
                                    )
                                st.divider()

                    # Save to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                    })

                else:
                    error_msg = f"Backend error: {response.text}"
                    status.update(label="❌ Error", state="error", expanded=False)
                    st.error(error_msg)

            except requests.exceptions.ConnectionError:
                status.update(label="❌ Connection Error", state="error", expanded=False)
                st.error("Cannot connect to the backend. Is the FastAPI server running on port 8000?")
            except Exception as e:
                status.update(label="❌ Error", state="error", expanded=False)
                st.error(f"Error: {e}")
