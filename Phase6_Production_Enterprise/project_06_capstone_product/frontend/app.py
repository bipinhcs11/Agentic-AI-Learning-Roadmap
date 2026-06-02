"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           DocuMind — Streamlit Frontend                                      ║
║           Phase 6 / Project 06 Capstone — Agentic AI Learning Roadmap       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Pages / flows:                                                              ║
║    • Login / Register — calls /auth/login or /auth/register                  ║
║    • Main app (post-login):                                                  ║
║        - Sidebar:  document list + upload widget                             ║
║        - Chat panel: question input → answer + expandable citations          ║
║    • Admin tab (role=admin): stats dashboard with bar charts                 ║
║                                                                              ║
║  State management: st.session_state holds token, role, username, and the     ║
║  running conversation history so the chat survives widget interactions.      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

API_URL: str = os.getenv("API_URL", "http://localhost:8000")

# ─────────────────────────────────────────────────────────────────────────────
# Page configuration (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="DocuMind",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────────────────────────────────────
# Session state initialisation
# ─────────────────────────────────────────────────────────────────────────────

def _init_state() -> None:
    defaults = {
        "token": None,
        "role": None,
        "username": None,
        "chat_history": [],      # list of {role: "user"|"assistant", content, citations, quality}
        "auth_error": None,
        "last_upload_sig": None,  # (name, size) of the last file already uploaded — guards the upload loop
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


_init_state()


# ─────────────────────────────────────────────────────────────────────────────
# API helpers
# ─────────────────────────────────────────────────────────────────────────────

def _headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {st.session_state.token}"}


def _api_post(path: str, json: dict | None = None, data: dict | None = None,
              files: dict | None = None, auth: bool = True) -> requests.Response:
    headers = _headers() if auth else {}
    return requests.post(
        f"{API_URL}{path}",
        json=json,
        data=data,
        files=files,
        headers=headers,
        timeout=120,
    )


def _api_get(path: str) -> requests.Response:
    return requests.get(f"{API_URL}{path}", headers=_headers(), timeout=30)


def _api_delete(path: str) -> requests.Response:
    return requests.delete(f"{API_URL}{path}", headers=_headers(), timeout=30)


# ─────────────────────────────────────────────────────────────────────────────
# Auth page
# ─────────────────────────────────────────────────────────────────────────────

def render_auth_page() -> None:
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.markdown("## 📄 DocuMind")
        st.markdown("*Internal Document Intelligence Platform*")
        st.divider()

        tab_login, tab_register = st.tabs(["Login", "Register"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="admin")
                password = st.text_input("Password", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("Sign In", use_container_width=True)

            if submitted:
                # OAuth2PasswordRequestForm requires application/x-www-form-urlencoded
                resp = requests.post(
                    f"{API_URL}/auth/login",
                    data={"username": username, "password": password},
                    timeout=15,
                )
                if resp.status_code == 200:
                    body = resp.json()
                    st.session_state.token = body["access_token"]
                    st.session_state.role = body["role"]
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error(f"Login failed: {resp.json().get('detail', 'Unknown error')}")

        with tab_register:
            with st.form("register_form"):
                new_user = st.text_input("Choose a username")
                new_pass = st.text_input("Choose a password", type="password")
                sub2 = st.form_submit_button("Create Account", use_container_width=True)

            if sub2:
                resp = requests.post(
                    f"{API_URL}/auth/register",
                    json={"username": new_user, "password": new_pass},
                    timeout=15,
                )
                if resp.status_code == 200:
                    body = resp.json()
                    st.session_state.token = body["access_token"]
                    st.session_state.role = body["role"]
                    st.session_state.username = new_user
                    st.rerun()
                else:
                    st.error(f"Registration failed: {resp.json().get('detail', 'Unknown error')}")


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — document management
# ─────────────────────────────────────────────────────────────────────────────

def render_sidebar() -> List[Dict[str, Any]]:
    """Renders sidebar and returns the current document list."""
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        st.caption(f"Role: **{st.session_state.role}**")

        if st.button("Sign Out", use_container_width=True):
            for key in ["token", "role", "username", "chat_history"]:
                st.session_state[key] = None if key != "chat_history" else []
            st.rerun()

        st.divider()
        st.markdown("### 📂 My Documents")

        # Fetch documents
        docs: List[Dict[str, Any]] = []
        try:
            resp = _api_get("/documents")
            if resp.status_code == 200:
                docs = resp.json()
            else:
                st.warning("Could not load documents")
        except requests.RequestException:
            st.error("Backend unreachable")

        if docs:
            for doc in docs:
                col_name, col_del = st.columns([4, 1])
                with col_name:
                    size_kb = doc["size_bytes"] // 1024
                    st.markdown(
                        f"**{doc['filename']}**  \n"
                        f"<span style='font-size:0.75em;color:gray'>"
                        f"{size_kb} KB · {doc['chunk_count']} chunks</span>",
                        unsafe_allow_html=True,
                    )
                with col_del:
                    if st.button("🗑", key=f"del_{doc['id']}", help="Delete"):
                        del_resp = _api_delete(f"/documents/{doc['id']}")
                        if del_resp.status_code == 200:
                            st.rerun()
                        else:
                            st.error("Delete failed")
        else:
            st.info("No documents yet. Upload below.")

        st.divider()
        st.markdown("### ⬆️ Upload Document")
        uploaded = st.file_uploader(
            "PDF, TXT, or MD",
            type=["pdf", "txt", "md"],
            label_visibility="collapsed",
        )
        # st.file_uploader RETAINS its file across reruns, so a naive upload + st.rerun()
        # re-fires every rerun and uploads the same file forever. Guard on a (name, size)
        # signature so each distinct file is sent exactly once.
        if uploaded is not None:
            upload_sig = (uploaded.name, uploaded.size)
            if upload_sig != st.session_state.last_upload_sig:
                st.session_state.last_upload_sig = upload_sig
                with st.spinner(f"Processing {uploaded.name}…"):
                    try:
                        resp = requests.post(
                            f"{API_URL}/documents/upload",
                            headers=_headers(),
                            files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)},
                            timeout=120,
                        )
                        if resp.status_code == 200:
                            st.success(f"Uploaded **{uploaded.name}**")
                            st.rerun()
                        else:
                            detail = resp.json().get("detail", "Upload failed")
                            st.error(detail)
                    except requests.RequestException as exc:
                        st.error(f"Upload error: {exc}")

    return docs


# ─────────────────────────────────────────────────────────────────────────────
# Chat panel
# ─────────────────────────────────────────────────────────────────────────────

def render_chat(docs: List[Dict[str, Any]]) -> None:
    st.markdown("## 💬 Ask your documents")

    if not docs:
        st.info(
            "Upload documents using the sidebar to start asking questions."
        )
        return

    # Render conversation history
    for entry in st.session_state.chat_history:
        if entry["role"] == "user":
            with st.chat_message("user"):
                st.write(entry["content"])
        else:
            with st.chat_message("assistant"):
                st.write(entry["content"])

                # Quality indicator
                score = entry.get("quality_score", 0)
                note = entry.get("quality_note", "")
                if score > 0:
                    color = "green" if score >= 7 else ("orange" if score >= 4 else "red")
                    st.markdown(
                        f"<span style='font-size:0.8em;color:{color}'>"
                        f"Quality score: {score}/10{' — ' + note if note else ''}"
                        f"</span>",
                        unsafe_allow_html=True,
                    )

                # Citations
                citations = entry.get("citations", [])
                if citations:
                    with st.expander(f"📎 {len(citations)} source(s) used"):
                        for i, cit in enumerate(citations, 1):
                            st.markdown(f"**{i}. {cit['filename']}** (similarity: {cit['score']})")
                            st.markdown(
                                f"<div style='background:#f0f2f6;padding:8px;border-radius:4px;"
                                f"font-size:0.85em'>{cit['excerpt']}</div>",
                                unsafe_allow_html=True,
                            )
                            if i < len(citations):
                                st.markdown("---")

    # Question input
    question = st.chat_input("Ask a question about your documents…")
    if question:
        st.session_state.chat_history.append({"role": "user", "content": question})

        with st.spinner("Thinking…"):
            try:
                resp = requests.post(
                    f"{API_URL}/query",
                    json={"question": question},
                    headers=_headers(),
                    timeout=120,
                )
                if resp.status_code == 200:
                    body = resp.json()
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": body["answer"],
                        "citations": body.get("citations", []),
                        "quality_score": body.get("quality_score", 0),
                        "quality_note": body.get("quality_note", ""),
                    })
                else:
                    detail = resp.json().get("detail", "Query failed")
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": f"Error: {detail}",
                        "citations": [],
                        "quality_score": 0,
                        "quality_note": "",
                    })
            except requests.RequestException as exc:
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"Could not reach backend: {exc}",
                    "citations": [],
                    "quality_score": 0,
                    "quality_note": "",
                })

        st.rerun()

    # Clear conversation
    if st.session_state.chat_history:
        if st.button("Clear conversation", use_container_width=False):
            st.session_state.chat_history = []
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Admin dashboard
# ─────────────────────────────────────────────────────────────────────────────

def render_admin_dashboard() -> None:
    st.markdown("## 📊 Admin Dashboard")

    try:
        resp = _api_get("/admin/stats")
        if resp.status_code != 200:
            st.error("Could not load stats")
            return
        stats = resp.json()
    except requests.RequestException:
        st.error("Backend unreachable")
        return

    # KPI cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Users", stats["total_users"])
    col2.metric("Documents Indexed", stats["total_documents"])
    col3.metric("Queries Answered", stats["total_queries"])
    col4.metric("Tokens Used (est.)", f"{stats['total_tokens_used']:,}")

    st.divider()

    # Bar chart — simple example with synthetic breakdown
    # In production these would come from time-series query log aggregation
    avg_q = stats["avg_quality_score"]
    st.markdown(f"**Average answer quality:** {avg_q:.1f} / 10")

    st.bar_chart(
        data={
            "Users": stats["total_users"],
            "Documents": stats["total_documents"],
            "Queries": stats["total_queries"],
        }
    )

    st.divider()
    st.markdown("### 👥 User List")
    try:
        users_resp = _api_get("/admin/users")
        if users_resp.status_code == 200:
            users = users_resp.json()
            for u in users:
                cols = st.columns([3, 1, 2])
                cols[0].write(u["username"])
                cols[1].write(u["role"])
                cols[2].write(str(u.get("created_at", ""))[:10])
    except requests.RequestException:
        st.warning("Could not load user list")


# ─────────────────────────────────────────────────────────────────────────────
# Main app (post-login)
# ─────────────────────────────────────────────────────────────────────────────

def render_main_app() -> None:
    docs = render_sidebar()

    if st.session_state.role == "admin":
        tab_chat, tab_admin = st.tabs(["Chat", "Admin Dashboard"])
        with tab_chat:
            render_chat(docs)
        with tab_admin:
            render_admin_dashboard()
    else:
        render_chat(docs)


# ─────────────────────────────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────────────────────────────

if st.session_state.token is None:
    render_auth_page()
else:
    render_main_app()
