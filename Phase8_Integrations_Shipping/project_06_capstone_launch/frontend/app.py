"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║  Phase 8 — Project 06: Capstone | frontend/app.py — Streamlit UI               ║
║                       AskMyDocs Pro — Complete Frontend                         ║
║                                                                                 ║
║  PURPOSE: A polished, production-ready Streamlit UI for AskMyDocs Pro.          ║
║  Features:                                                                      ║
║  - Login page with tenant branding                                              ║
║  - Dashboard with usage meter and document library                              ║
║  - Document upload (drag & drop)                                                ║
║  - Real-time streaming chat via WebSocket                                       ║
║  - Usage statistics with visual charts                                          ║
║  - Admin view: all tenants + platform usage                                     ║
║                                                                                 ║
║  WHY STREAMLIT? It turns Python into a web app with minimal boilerplate.        ║
║  Perfect for internal tools, demos, and MVPs. For a customer-facing product,    ║
║  you'd use React/Next.js — but Streamlit gets you 80% there in 20% of the time. ║
║                                                                                 ║
║  RUN: streamlit run frontend/app.py                                             ║
║  Requires: pip install streamlit requests websocket-client                      ║
╚══════════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import json
import os
import queue
import threading
import time
from datetime import datetime
from typing import Optional

import requests
import streamlit as st

# ─── Configuration ────────────────────────────────────────────────────────────
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
WS_BASE = API_BASE.replace("http://", "ws://").replace("https://", "wss://")
SUPER_ADMIN_TOKEN = os.getenv("SUPER_ADMIN_TOKEN", "superadmin-dev-token-CHANGE-IN-PRODUCTION")


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE MANAGEMENT
# Streamlit reruns the entire script on every interaction.
# st.session_state persists data between reruns within a user session.
# WHY initialize here? Avoids KeyError on first access before state is set.
# ═══════════════════════════════════════════════════════════════════════════════

def init_session_state() -> None:
    """Initialize all session state variables with defaults."""
    defaults = {
        "token": None,
        "tenant_id": None,
        "tenant_name": None,
        "role": None,
        "email": None,
        "page": "login",           # Current page: login | dashboard | chat | upload | usage | admin
        "chat_messages": [],       # List of {role, content, sources}
        "documents": [],           # Cached document list
        "selected_document_id": None,
        "streaming_active": False,
        "stream_buffer": "",
    }
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


# ═══════════════════════════════════════════════════════════════════════════════
# API CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

def api_get(path: str, params: Optional[dict] = None) -> Optional[dict]:
    """Make an authenticated GET request to the backend API."""
    try:
        headers = {}
        if st.session_state.token:
            headers["Authorization"] = f"Bearer {st.session_state.token}"
        resp = requests.get(f"{API_BASE}{path}", headers=headers, params=params, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        else:
            st.error(f"API Error {resp.status_code}: {resp.text[:200]}")
            return None
    except requests.exceptions.ConnectionError:
        st.error(f"Cannot connect to backend at {API_BASE}. Is the server running?")
        return None


def api_post(path: str, data: dict, headers_extra: Optional[dict] = None, files=None) -> Optional[dict]:
    """Make an authenticated POST request to the backend API."""
    try:
        headers = {}
        if st.session_state.token:
            headers["Authorization"] = f"Bearer {st.session_state.token}"
        if headers_extra:
            headers.update(headers_extra)

        if files:
            resp = requests.post(f"{API_BASE}{path}", headers=headers, files=files, timeout=60)
        else:
            resp = requests.post(f"{API_BASE}{path}", headers=headers, json=data, timeout=30)

        if resp.status_code in (200, 201):
            return resp.json()
        else:
            st.error(f"API Error {resp.status_code}: {resp.text[:300]}")
            return None
    except requests.exceptions.ConnectionError:
        st.error(f"Cannot connect to backend at {API_BASE}. Is the server running?")
        return None


def api_delete(path: str) -> bool:
    """Make an authenticated DELETE request."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        resp = requests.delete(f"{API_BASE}{path}", headers=headers, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET STREAMING
# ═══════════════════════════════════════════════════════════════════════════════

def stream_chat_response(question: str, document_id: Optional[int]) -> tuple[str, list]:
    """Stream a chat response via WebSocket.

    WHY stream? Streaming gives the user immediate feedback — tokens appear
    as they're generated, creating a ChatGPT-like experience.

    This function blocks until the stream is complete and returns
    the full response + sources. For a production Streamlit app, you'd
    use st.write_stream() with a generator for true real-time rendering.

    LIMITATION: Streamlit's threading model makes true async WebSocket
    streaming complex. This implementation collects the full response
    via WebSocket but simulates streaming in the UI with a typing effect.
    """
    try:
        import websocket as ws_client
    except ImportError:
        # Fallback to HTTP if websocket-client not installed
        return http_chat_fallback(question, document_id)

    token = st.session_state.token
    ws_url = f"{WS_BASE}/ws/chat?token={token}"

    collected_tokens = []
    sources = []
    done_event = threading.Event()
    error_msg = [None]

    def on_message(ws, message):
        data = json.loads(message)
        if data["type"] == "token":
            collected_tokens.append(data["content"])
        elif data["type"] == "done":
            sources.extend(data.get("sources", []))
            done_event.set()
            ws.close()
        elif data["type"] == "error":
            error_msg[0] = data.get("message", "Unknown error")
            done_event.set()
            ws.close()

    def on_error(ws, error):
        error_msg[0] = str(error)
        done_event.set()

    def on_open(ws):
        payload = {"message": question}
        if document_id:
            payload["document_id"] = document_id
        ws.send(json.dumps(payload))

    ws = ws_client.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
    )

    thread = threading.Thread(target=ws.run_forever)
    thread.daemon = True
    thread.start()

    # Wait up to 60 seconds for the response
    done_event.wait(timeout=60)

    if error_msg[0]:
        return f"Error: {error_msg[0]}", []

    return "".join(collected_tokens), sources


def http_chat_fallback(question: str, document_id: Optional[int]) -> tuple[str, list]:
    """Fallback to HTTP /chat if WebSocket isn't available."""
    payload = {"message": question, "top_k": 3}
    if document_id:
        payload["document_id"] = document_id

    result = api_post("/chat", payload)
    if result:
        return result.get("answer", ""), result.get("sources", [])
    return "Failed to get response", []


# ═══════════════════════════════════════════════════════════════════════════════
# PAGES
# ═══════════════════════════════════════════════════════════════════════════════

def render_login_page() -> None:
    """Login page with demo credentials hint."""
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("# AskMyDocs Pro")
        st.markdown("*AI-powered document Q&A for your team*")
        st.divider()

        with st.form("login_form"):
            email = st.text_input("Email", placeholder="admin@acme.example")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

        if submitted:
            resp = api_post("/auth/login", {"email": email, "password": password})
            if resp:
                st.session_state.token = resp["access_token"]
                st.session_state.tenant_id = resp["tenant_id"]
                st.session_state.tenant_name = resp["tenant_name"]
                st.session_state.role = resp.get("role", "user")
                st.session_state.email = email
                st.session_state.page = "dashboard"
                st.rerun()

        st.divider()
        st.markdown("**Demo accounts:**")
        st.markdown("""
        | Email | Password | Plan |
        |-------|----------|------|
        | admin@acme.example | acme-pass-123 | Pro |
        | admin@startup.example | startup-pass-123 | Free |
        | admin@bigcorp.example | bigcorp-pass-123 | Enterprise |
        """)


def render_sidebar() -> None:
    """Sidebar navigation and user info."""
    with st.sidebar:
        # Tenant branding
        st.markdown(f"### {st.session_state.tenant_name}")
        st.caption(f"Logged in as: {st.session_state.email}")
        st.caption(f"Role: {st.session_state.role}")

        # Usage meter
        tenant_data = api_get("/tenants/me")
        if tenant_data:
            used = tenant_data.get("used_this_month", 0)
            quota = tenant_data.get("monthly_quota", 50)
            plan = tenant_data.get("plan", "free")

            st.divider()
            st.markdown("**Usage this month**")
            if quota == "unlimited":
                st.markdown(f"🟢 {used} requests used (unlimited)")
            else:
                percent = min(1.0, used / max(1, quota))
                # Color based on usage level
                if percent >= 0.9:
                    bar_color = "red"
                elif percent >= 0.7:
                    bar_color = "orange"
                else:
                    bar_color = "green"
                st.progress(percent, text=f"{used}/{quota} requests")
                if percent >= 0.9:
                    st.warning("Quota nearly exhausted! Consider upgrading.")

            st.caption(f"Plan: **{plan.upper()}**")

        st.divider()

        # Navigation
        st.markdown("**Navigation**")
        if st.button("Dashboard", use_container_width=True):
            st.session_state.page = "dashboard"
            st.rerun()
        if st.button("Chat", use_container_width=True):
            st.session_state.page = "chat"
            st.rerun()
        if st.button("Upload Documents", use_container_width=True):
            st.session_state.page = "upload"
            st.rerun()
        if st.button("Usage Stats", use_container_width=True):
            st.session_state.page = "usage"
            st.rerun()

        # Admin button — only for admins
        if st.session_state.role == "admin":
            st.divider()
            if st.button("Admin Dashboard", use_container_width=True, type="secondary"):
                st.session_state.page = "admin"
                st.rerun()

        st.divider()
        if st.button("Sign Out", use_container_width=True):
            # Clear all session state on logout
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            init_session_state()
            st.rerun()


def render_dashboard() -> None:
    """Main dashboard: overview stats and quick actions."""
    tenant_data = api_get("/tenants/me")
    if not tenant_data:
        return

    st.title(f"Welcome to {st.session_state.tenant_name}")
    st.caption(f"AskMyDocs Pro — {datetime.now().strftime('%A, %B %d %Y')}")

    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Documents",
            tenant_data.get("document_count", 0),
            help="Total indexed documents",
        )
    with col2:
        used = tenant_data.get("used_this_month", 0)
        st.metric("Requests This Month", used, help="AI queries this month")
    with col3:
        remaining = tenant_data.get("remaining", "unlimited")
        st.metric("Remaining Quota", remaining, help="Queries remaining this month")
    with col4:
        st.metric("Plan", tenant_data.get("plan", "free").upper())

    st.divider()

    # Documents section
    col_a, col_b = st.columns([2, 1])

    with col_a:
        st.subheader("Document Library")
        docs_data = api_get("/documents")
        if docs_data:
            st.session_state.documents = docs_data
            if docs_data:
                for doc in docs_data[:5]:  # Show most recent 5
                    status_icon = "✅" if doc["status"] == "ready" else "⏳" if doc["status"] == "processing" else "❌"
                    st.markdown(f"{status_icon} **{doc['filename']}** — {doc['chunk_count']} chunks")
                if len(docs_data) > 5:
                    st.caption(f"...and {len(docs_data) - 5} more documents")
            else:
                st.info("No documents yet. Upload your first document to get started!")
                if st.button("Upload Document →"):
                    st.session_state.page = "upload"
                    st.rerun()
        else:
            st.info("No documents yet.")

    with col_b:
        st.subheader("Quick Actions")
        if st.button("Ask a Question", use_container_width=True, type="primary"):
            st.session_state.page = "chat"
            st.rerun()
        if st.button("Upload Document", use_container_width=True):
            st.session_state.page = "upload"
            st.rerun()
        if st.button("View Usage", use_container_width=True):
            st.session_state.page = "usage"
            st.rerun()


def render_chat_page() -> None:
    """Chat interface with document selection and streaming responses."""
    st.title("Ask Your Documents")

    # Document selector
    docs_data = api_get("/documents")
    ready_docs = [d for d in (docs_data or []) if d["status"] == "ready"]

    if not ready_docs:
        st.warning("No documents indexed yet. Please upload documents first.")
        if st.button("Go to Upload"):
            st.session_state.page = "upload"
            st.rerun()
        return

    # Sidebar for document selection (inline, since sidebar is used for nav)
    col_main, col_sidebar = st.columns([3, 1])

    with col_sidebar:
        st.markdown("**Search in:**")
        doc_options = ["All Documents"] + [f"{d['filename']}" for d in ready_docs]
        selected_doc_name = st.selectbox("Document scope", doc_options, label_visibility="collapsed")

        selected_doc_id = None
        if selected_doc_name != "All Documents":
            for doc in ready_docs:
                if doc["filename"] == selected_doc_name:
                    selected_doc_id = doc["id"]
                    break

        if st.button("Clear Chat"):
            st.session_state.chat_messages = []
            st.rerun()

        st.divider()
        st.caption("**How to use:**")
        st.caption("1. Select a document or search all")
        st.caption("2. Ask a question in natural language")
        st.caption("3. View AI answer with sources")

    with col_main:
        # Display chat history
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("sources"):
                    with st.expander(f"Sources ({len(msg['sources'])})"):
                        for src in msg["sources"]:
                            st.caption(f"📄 **{src.get('filename', 'Unknown')}** (relevance: {src.get('relevance_score', 0):.2f})")
                            if "chunk_excerpt" in src:
                                st.caption(f"> {src['chunk_excerpt'][:150]}...")

        # Chat input
        if question := st.chat_input("Ask a question about your documents..."):
            # Add user message to history
            st.session_state.chat_messages.append({
                "role": "user",
                "content": question,
                "sources": [],
            })

            with st.chat_message("user"):
                st.markdown(question)

            # Get and stream response
            with st.chat_message("assistant"):
                with st.spinner("Searching documents and generating answer..."):
                    answer, sources = stream_chat_response(question, selected_doc_id)

                st.markdown(answer)
                if sources:
                    with st.expander(f"Sources ({len(sources)})"):
                        for src in sources:
                            st.caption(f"📄 **{src.get('filename', 'Unknown')}** (score: {src.get('relevance_score', 0):.2f})")

            # Add assistant message to history
            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": answer,
                "sources": sources,
            })


def render_upload_page() -> None:
    """Document upload page with drag-and-drop support."""
    st.title("Upload Documents")
    st.caption("Upload PDF or TXT files to make them searchable with AI")

    # Upload form
    with st.form("upload_form", clear_on_submit=True):
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["pdf", "txt"],
            help="Supported formats: PDF, plain text (.txt). Max size: ~10MB",
        )
        submitted = st.form_submit_button("Upload & Index", type="primary", use_container_width=True)

    if submitted and uploaded_file:
        with st.spinner(f"Uploading and indexing '{uploaded_file.name}'..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            headers = {}
            if st.session_state.token:
                headers["Authorization"] = f"Bearer {st.session_state.token}"
            try:
                resp = requests.post(
                    f"{API_BASE}/documents",
                    headers=headers,
                    files=files,
                    timeout=120,
                )
                if resp.status_code == 201:
                    doc = resp.json()
                    st.success(
                        f"✅ '{doc['filename']}' uploaded successfully! "
                        f"{doc['chunk_count']} chunks indexed."
                    )
                else:
                    st.error(f"Upload failed: {resp.text[:200]}")
            except requests.exceptions.ConnectionError:
                st.error(f"Cannot connect to backend at {API_BASE}")

    st.divider()
    st.subheader("Your Documents")

    docs_data = api_get("/documents")
    if docs_data:
        for doc in docs_data:
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            status_icon = {"ready": "✅", "processing": "⏳", "failed": "❌"}.get(doc["status"], "❓")

            with col1:
                st.markdown(f"{status_icon} **{doc['filename']}**")
            with col2:
                st.caption(f"{doc['chunk_count']} chunks")
            with col3:
                st.caption(doc["created_at"][:10])
            with col4:
                if st.button("Delete", key=f"del_{doc['id']}"):
                    if api_delete(f"/documents/{doc['id']}"):
                        st.success(f"Deleted '{doc['filename']}'")
                        st.rerun()
    else:
        st.info("No documents uploaded yet.")


def render_usage_page() -> None:
    """Usage statistics page with daily breakdown chart."""
    st.title("Usage Statistics")

    usage_data = api_get("/usage")
    if not usage_data:
        return

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Requests This Month", usage_data["used"])
    with col2:
        st.metric("Quota", usage_data["quota"])
    with col3:
        st.metric("Remaining", usage_data.get("remaining", "unlimited"))

    st.metric("Estimated Cost (USD)", f"${usage_data.get('total_cost_usd', 0):.4f}")

    st.divider()

    # Daily usage chart using Streamlit's native bar chart
    by_day = usage_data.get("by_day", {})
    if by_day:
        st.subheader("Daily Usage")
        # Convert to format Streamlit chart expects
        days = sorted(by_day.keys())
        counts = [by_day[d] for d in days]

        chart_data = {day: count for day, count in zip(days, counts)}
        st.bar_chart(chart_data)
    else:
        st.info("No usage data for this month yet.")

    # Usage by endpoint
    by_endpoint = usage_data.get("by_endpoint", {})
    if by_endpoint:
        st.subheader("Usage by Endpoint")
        for endpoint, count in sorted(by_endpoint.items(), key=lambda x: x[1], reverse=True):
            st.markdown(f"- **{endpoint}**: {count} requests")


def render_admin_page() -> None:
    """Admin view: all tenants + platform-wide usage (admin role required)."""
    if st.session_state.role != "admin":
        st.error("Admin access required")
        return

    st.title("Admin Dashboard")
    st.caption("Platform-wide view (admin only)")

    # Get all tenants using super-admin token
    # Note: in a real app, admin users would have a separate admin API
    # For demo, we use the super-admin token directly
    try:
        resp = requests.get(
            f"{API_BASE}/admin/tenants",
            headers={"Authorization": f"Bearer {SUPER_ADMIN_TOKEN}"},
            timeout=10,
        )
        if resp.status_code == 200:
            tenants = resp.json()
        else:
            st.error(f"Could not load tenants: {resp.status_code}")
            return
    except Exception as e:
        st.error(f"Connection error: {e}")
        return

    st.subheader(f"All Tenants ({len(tenants)})")

    for t in tenants:
        with st.expander(f"**{t['name']}** — {t['plan'].upper()} plan"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Requests This Month", t.get("used_this_month", 0))
            with col2:
                st.metric("Monthly Quota", t["monthly_quota"] if t["monthly_quota"] != -1 else "∞")
            with col3:
                st.metric("Created", t["created_at"][:10])
            st.caption(f"Slug: {t['slug']} | ID: {t['id']}")

    # Platform metrics
    st.divider()
    st.subheader("Platform Metrics")
    try:
        resp = requests.get(
            f"{API_BASE}/metrics",
            headers={"Authorization": f"Bearer {SUPER_ADMIN_TOKEN}"},
            timeout=10,
        )
        if resp.status_code == 200:
            metrics = resp.json()
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Tenants", metrics.get("tenants_total", 0))
            with col2:
                st.metric("Total Users", metrics.get("users_total", 0))
            with col3:
                st.metric("Total Documents", metrics.get("documents_total", 0))
            with col4:
                st.metric("Requests This Month", metrics.get("requests_this_month", 0))
    except Exception:
        st.info("Platform metrics unavailable")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Main Streamlit application entry point."""
    st.set_page_config(
        page_title="AskMyDocs Pro",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session_state()

    # Check backend connectivity
    try:
        health = requests.get(f"{API_BASE}/health", timeout=3).json()
        if health.get("status") != "healthy":
            st.warning(f"Backend health: {health}")
    except Exception:
        st.error(
            f"Cannot connect to backend at {API_BASE}. "
            "Please start the server with: `uvicorn main:app --port 8000`"
        )
        return

    # Route to the correct page
    if not st.session_state.token:
        render_login_page()
        return

    # Authenticated pages
    render_sidebar()

    page = st.session_state.page
    if page == "dashboard":
        render_dashboard()
    elif page == "chat":
        render_chat_page()
    elif page == "upload":
        render_upload_page()
    elif page == "usage":
        render_usage_page()
    elif page == "admin":
        render_admin_page()
    else:
        render_dashboard()


if __name__ == "__main__":
    main()
