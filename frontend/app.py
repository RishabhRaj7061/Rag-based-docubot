
import os
import html
from typing import Any

import requests
import streamlit as st

# ----------------------------- Configuration -----------------------------

_DEFAULT_API_URL = "https://rag-based-docubot.onrender.com"


def _get_api_url():
    env_url = os.getenv("DOCUBOT_API_URL")
    if env_url:
        return env_url.rstrip("/")

    try:
        secret_url = st.secrets.get("DOCUBOT_API_URL")
        if secret_url:
            return str(secret_url).rstrip("/")
    except Exception:
        pass

    return _DEFAULT_API_URL


_URL = _get_api_url()
REQUEST_TIMEOUT = 180

st.set_page_config(
    page_title="DocuBot | Document AI",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------- Styling ------------------------------------

st.markdown(
    """
    <style>
      @import url(
        'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap'
      );

      html, body, [class*="css"] {
          font-family: 'DM Sans', sans-serif;
      }

      .stApp {
          background: #0b1020;
          color: #edf2ff;
      }

      [data-testid="stSidebar"] {
          background: #10172a;
          border-right: 1px solid #26314b;
      }

      [data-testid="stSidebar"] > div {
          padding-top: 1.4rem;
      }

      .brand {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 6px;
      }

      .brand-icon {
          width: 44px;
          height: 44px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 14px;
          background: linear-gradient(135deg, #7c5cff, #24c8a5);
          font-size: 24px;
      }

      .brand-title {
          font-family: 'Manrope', sans-serif;
          font-size: 28px;
          font-weight: 800;
          letter-spacing: -1px;
      }

      .muted {
          color: #9aa8c5;
      }

      .hero {
          padding: 28px 30px;
          border: 1px solid #26314b;
          border-radius: 22px;
          background:
              linear-gradient(
                  120deg,
                  rgba(124, 92, 255, .18),
                  rgba(36, 200, 165, .08)
              ),
              #111a2e;
          margin-bottom: 22px;
      }

      .hero h1 {
          font-family: 'Manrope', sans-serif;
          font-size: 32px;
          margin: 0 0 8px 0;
          color: #f6f8ff;
      }

      .hero p {
          color: #aebbd5;
          margin: 0;
          font-size: 15px;
      }

      .section-label {
          color: #9eadd0;
          font-size: 12px;
          font-weight: 700;
          letter-spacing: 1.4px;
          text-transform: uppercase;
          margin: 12px 0 10px;
      }

      .metric {
          background: #121c31;
          border: 1px solid #283653;
          padding: 15px 16px;
          border-radius: 15px;
      }

      .metric-label {
          color: #9eacc8;
          font-size: 12px;
      }

      .metric-value {
          color: #f5f7ff;
          font-size: 22px;
          font-weight: 800;
          margin-top: 4px;
      }

      .doc-card {
          background: #121c31;
          border: 1px solid #283653;
          padding: 13px 14px;
          border-radius: 13px;
          margin: 8px 0;
      }

      .stButton > button {
          border-radius: 11px;
          font-weight: 600;
          min-height: 38px;
      }

      .stTextInput input,
      .stTextArea textarea,
      [data-baseweb="select"] > div {
          background-color: #121c31 !important;
          border-color: #2a3856 !important;
          border-radius: 12px !important;
      }

      [data-testid="stChatMessage"] {
          border: 1px solid #263550;
          border-radius: 16px;
          background: #111a2c;
      }

      .stAlert {
          border-radius: 12px;
      }

      footer, #MainMenu {
          visibility: hidden;
      }

      div[data-testid="stFileUploader"] {
          background: #121c31;
          border: 1px dashed #3c4b6c;
          border-radius: 14px;
          padding: 12px;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------- API helpers --------------------------------


def api_request(method: str, path: str, **kwargs: Any) -> Any:
    """Send an API request and return its JSON response."""
    kwargs.setdefault("timeout", REQUEST_TIMEOUT)

    response = requests.request(
        method,
        f"{_URL}{path}",
        **kwargs,
    )
    response.raise_for_status()

    if not response.content:
        return {}

    return response.json()


def fetch_documents() -> list[dict]:
    """Load document metadata from the backend."""
    data = api_request("GET", "/documents")

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in ("documents", "items", "data"):
            if isinstance(data.get(key), list):
                return data[key]

    return []


def display_name(doc: dict) -> str:
    return str(
        doc.get("filename")
        or doc.get("name")
        or doc.get("document_id")
        or "Untitled document"
    )


def document_id(doc: dict) -> str:
    return str(doc.get("document_id") or doc.get("id") or "")


def ensure_state() -> None:
    st.session_state.setdefault("chat_by_document", {})
    st.session_state.setdefault("selected_document_id", "")
    st.session_state.setdefault("selected_for_deletion", set())
    st.session_state.setdefault("api_status", "checking")
    st.session_state.setdefault("delete_confirmation", False)


def toggle_delete_selection(doc_id: str) -> None:
    """Select or deselect a document using its circular control."""
    selected = set(st.session_state["selected_for_deletion"])

    if doc_id in selected:
        selected.remove(doc_id)
    else:
        selected.add(doc_id)

    st.session_state["selected_for_deletion"] = selected
    st.session_state["delete_confirmation"] = False


def clear_current_history() -> None:
    selected_id = st.session_state.get("selected_document_id", "")

    if selected_id:
        st.session_state["chat_by_document"][selected_id] = []


def delete_selected_documents() -> None:
    """Delete selected documents through the backend API."""
    selected_ids = set(st.session_state["selected_for_deletion"])

    if not selected_ids:
        st.warning("Select at least one document first.")
        return

    deleted_ids = []
    failures = []

    for doc_id in selected_ids:
        try:
            api_request("DELETE", f"/documents/{doc_id}")
            deleted_ids.append(doc_id)
        except Exception as exc:
            failures.append(f"{doc_id[:8]}: {exc}")

    # Clear selection only for successfully deleted documents.
    st.session_state["selected_for_deletion"] = (
        selected_ids - set(deleted_ids)
    )

    # Remove chat history for successfully deleted documents.
    for doc_id in deleted_ids:
        st.session_state["chat_by_document"].pop(doc_id, None)

    if st.session_state.get("selected_document_id") in deleted_ids:
        st.session_state["selected_document_id"] = ""

    st.session_state["delete_confirmation"] = False

    if deleted_ids:
        st.success(f"Deleted {len(deleted_ids)} document(s).")

    for failure in failures:
        st.error(f"Could not delete document: {failure}")

    if deleted_ids:
        st.rerun()


ensure_state()

# ----------------------------- Sidebar ------------------------------------

with st.sidebar:
    st.markdown(
        """
        <div class="brand">
          <div class="brand-icon">📚</div>
          <div>
            <div class="brand-title">DocuBot</div>
            <div class="muted" style="font-size:12px">
              DOCUMENT INTELLIGENCE
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown(
        '<div class="section-label">Workspace</div>',
        unsafe_allow_html=True,
    )

    # Backend status
    try:
        api_request("GET", "/health", timeout=8)
        st.session_state["api_status"] = "online"
        st.success("Backend connected", icon="🟢")
    except Exception:
        st.session_state["api_status"] = "offline"
        st.error("Backend unavailable", icon="🔴")
        st.caption(f"Expected API: {_URL}")

    if st.button("↻ Refresh documents", use_container_width=True):
        st.rerun()

    # Upload documents
    st.markdown(
        '<div class="section-label">Add a document</div>',
        unsafe_allow_html=True,
    )

    uploaded_files = st.file_uploader(
        "Upload PDF or Word files",
        type=["pdf", "doc", "docx"],
        accept_multiple_files=True,
        help="PDF, DOC, and DOCX files are supported.",
        label_visibility="collapsed",
        key="document_uploader",
    )

    if st.button(
        "⬆ Upload selected files",
        use_container_width=True,
        disabled=not uploaded_files,
    ):
        success_count = 0
        failures = []
        progress = st.progress(0)

        for index, uploaded in enumerate(uploaded_files):
            try:
                api_request(
                    "POST",
                    "/documents/upload",
                    files={
                        "file": (
                            uploaded.name,
                            uploaded.getvalue(),
                            uploaded.type or "application/octet-stream",
                        )
                    },
                    timeout=REQUEST_TIMEOUT,
                )
                success_count += 1

            except Exception as exc:
                failures.append(f"{uploaded.name}: {exc}")

            progress.progress((index + 1) / len(uploaded_files))

        if success_count:
            st.success(f"Uploaded and processed {success_count} file(s).")

        for failure in failures:
            st.error(f"Upload failed: {failure}")

        if success_count:
            st.rerun()

    # Load library
    try:
        documents = fetch_documents()
    except Exception as exc:
        documents = []
        st.warning(f"Could not load documents: {exc}")

    # Discard selected IDs that no longer exist in the library.
    available_ids = {
        document_id(doc) for doc in documents if document_id(doc)
    }
    st.session_state["selected_for_deletion"] = (
        set(st.session_state["selected_for_deletion"]) & available_ids
    )

    st.markdown(
        '<div class="section-label">Your library</div>',
        unsafe_allow_html=True,
    )
    st.caption(f"{len(documents)} document(s) available")

    if documents:
        # Each filename gets a circular select/deselect button.
        st.caption("Select the circles beside files you want to delete.")

        for doc in documents:
            doc_id = document_id(doc)

            if not doc_id:
                continue

            filename = display_name(doc)
            is_selected = (
                doc_id in st.session_state["selected_for_deletion"]
            )

            circle_label = "🔵" if is_selected else "⚪"

            circle_col, name_col = st.columns([1, 5])

            with circle_col:
                st.button(
                    circle_label,
                    key=f"delete_select_{doc_id}",
                    help=(
                        "Deselect this document"
                        if is_selected
                        else "Select this document for deletion"
                    ),
                    on_click=toggle_delete_selection,
                    args=(doc_id,),
                    use_container_width=True,
                )

            with name_col:
                # Escape filename before inserting it into HTML.
                safe_filename = html.escape(filename)
                st.markdown(
                    f"<div style='padding-top:9px; "
                    f"overflow-wrap:anywhere;'>{safe_filename}</div>",
                    unsafe_allow_html=True,
                )

        selected_count = len(st.session_state["selected_for_deletion"])

        st.caption(f"{selected_count} document(s) selected")

        if st.button(
            "🗑️ Delete selected documents",
            use_container_width=True,
            disabled=selected_count == 0,
            type="primary",
            key="open_delete_confirmation",
        ):
            st.session_state["delete_confirmation"] = True

        if st.session_state["delete_confirmation"] and selected_count:
            st.warning(
                f"You are about to permanently delete "
                f"{selected_count} selected document(s)."
            )

            confirm_col, cancel_col = st.columns(2)

            with confirm_col:
                st.button(
                    "Confirm delete",
                    key="confirm_delete",
                    type="primary",
                    use_container_width=True,
                    on_click=delete_selected_documents,
                )

            with cancel_col:
                st.button(
                    "Cancel",
                    key="cancel_delete",
                    use_container_width=True,
                    on_click=lambda: st.session_state.update(
                        {"delete_confirmation": False}
                    ),
                )

        # Chat document selector
        options = {
            f"{display_name(doc)} · {document_id(doc)[:8]}": document_id(doc)
            for doc in documents
            if document_id(doc)
        }

        if options:
            labels = list(options.keys())
            current_id = st.session_state.get("selected_document_id", "")

            current_index = next(
                (
                    index
                    for index, label in enumerate(labels)
                    if options[label] == current_id
                ),
                0,
            )

            chosen_label = st.selectbox(
                "Choose a document to chat with",
                labels,
                index=current_index,
                key="document_selector",
                label_visibility="visible",
            )

            chosen_id = options[chosen_label]

            if chosen_id != st.session_state.get("selected_document_id"):
                st.session_state["selected_document_id"] = chosen_id
                st.rerun()

            current_doc = next(
                (
                    doc
                    for doc in documents
                    if document_id(doc) == chosen_id
                ),
                {},
            )

            safe_active_name = html.escape(display_name(current_doc))
            page_count = current_doc.get("page_count", "—")
            chunk_count = current_doc.get("chunk_count", "—")

            st.markdown(
                f"""
                <div class="doc-card">
                  <div style="font-weight:700; overflow-wrap:anywhere">
                    📄 {safe_active_name}
                  </div>
                  <div class="muted" style="font-size:12px; margin-top:5px">
                    {page_count} pages · {chunk_count} chunks
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if st.button(
                "🧹 Clear chat history",
                use_container_width=True,
                key="clear_history",
            ):
                clear_current_history()
                st.toast(
                    "Chat history cleared. Your documents are unchanged.",
                    icon="🧹",
                )
                st.rerun()

    else:
        st.info("Upload a document to begin chatting.")
        st.session_state["selected_document_id"] = ""

    st.markdown("---")
    st.caption("🔒 Your files stay in this project's local data folder.")
    st.caption(f"Backend: {_URL}")

# ----------------------------- Main content -------------------------------

st.markdown(
    """
    <div class="hero">
      <div class="section-label" style="margin-top:0">
        AI DOCUMENT ASSISTANT
      </div>
      <h1>Ask your documents. Get grounded answers.</h1>
      <p>
        Upload a report, resume, or PDF and explore its contents
        with AI-powered search and source context.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        f"""
        <div class="metric">
          <div class="metric-label">DOCUMENTS IN LIBRARY</div>
          <div class="metric-value">{len(documents)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    status_text = (
        "Connected"
        if st.session_state.get("api_status") == "online"
        else "Offline"
    )
    st.markdown(
        f"""
        <div class="metric">
          <div class="metric-label">BACKEND STATUS</div>
          <div class="metric-value">{status_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    active_id = st.session_state.get("selected_document_id", "")
    active_text = "Selected" if active_id else "None selected"

    st.markdown(
        f"""
        <div class="metric">
          <div class="metric-label">ACTIVE DOCUMENT</div>
          <div class="metric-value" style="font-size:17px">
            {active_text}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ----------------------------- Document chat ------------------------------

st.markdown("### 💬 Document chat")

selected_id = st.session_state.get("selected_document_id", "")

if not selected_id:
    st.info(
        "Choose a document from the sidebar or upload one "
        "to start asking questions."
    )
    st.stop()

history = st.session_state["chat_by_document"].setdefault(
    selected_id, []
)

if not history:
    st.markdown(
        """
        <div class="doc-card">
          <div style="font-weight:700; font-size:16px">
            Start with a question
          </div>
          <div class="muted" style="margin-top:6px">
            Try: “Summarize this document”, “What skills are listed?”,
            or “What are the key points?”
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

for message in history:
    avatar = "🧑‍💻" if message["role"] == "user" else "📚"

    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

        sources = message.get("sources", [])
        if sources:
            with st.expander("View retrieved sources"):
                for source in sources:
                    page = source.get(
                        "page",
                        source.get("page_number", "Unknown"),
                    )
                    filename = source.get("filename") or "Document"

                    st.markdown(f"**{filename} · Page {page}**")

                    snippet = source.get("text", "")
                    if snippet:
                        st.write(snippet)

question = st.chat_input(
    "Ask a question about your selected document…"
)

if question:
    history.append({"role": "user", "content": question})

    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(question)

    with st.chat_message("assistant", avatar="📚"):
        with st.spinner(
            "Searching your document and preparing an answer…"
        ):
            try:
                result = api_request(
                    "POST",
                    "/ask",
                    json={
                        "question": question,
                        "document_id": selected_id,
                        "top_k": 5,
                    },
                    timeout=REQUEST_TIMEOUT,
                )

                answer = result.get(
                    "answer",
                    "I couldn't generate an answer.",
                )
                sources = result.get("sources", [])

                st.markdown(answer)

                if sources:
                    with st.expander(
                        "View retrieved sources",
                        expanded=False,
                    ):
                        for source in sources:
                            page = source.get(
                                "page",
                                source.get("page_number", "Unknown"),
                            )
                            filename = source.get("filename") or "Document"

                            st.markdown(
                                f"**{filename} · Page {page}**"
                            )

                            if source.get("text"):
                                st.write(source["text"])

                history.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                    }
                )

            except requests.HTTPError as exc:
                details = ""

                if exc.response is not None:
                    details = exc.response.text[:1500]

                error_message = f"Request failed: {exc}"

                if details:
                    error_message += (
                        f"\n\nBackend response:\n\n{details}"
                    )

                st.error(error_message)
                history.append(
                    {
                        "role": "assistant",
                        "content": error_message,
                    }
                )

            except Exception as exc:
                error_message = f"Could not reach the backend: {exc}"
                st.error(error_message)

                history.append(
                    {
                        "role": "assistant",
                        "content": error_message,
                    }
                )

    st.rerun()
