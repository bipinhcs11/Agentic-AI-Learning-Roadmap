# ═══════════════════════════════════════════════════════════════
# Phase 6 — Streamlit Chat UI (Dockerized)
# Talks to the API container — not directly to Ollama
# ═══════════════════════════════════════════════════════════════
#
# KEY DIFFERENCE from Phase 4:
#   Phase 4: UI → Ollama directly (http://localhost:11434)
#   Phase 6: UI → API container → Ollama
#
#   This is the production pattern. The UI doesn't know or care
#   about Ollama — it only knows about the API. You can swap
#   the model backend without touching the UI.
# ═══════════════════════════════════════════════════════════════

import json
import os
import time

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://api:8000")   # "api" = container name in docker-compose

st.set_page_config(
    page_title="AI Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# Sidebar — model selector and stats
# ─────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ Settings")

    # Fetch available models from API
    try:
        resp = requests.get(f"{API_URL}/models", timeout=5)
        model_data = resp.json()
        available_models = model_data.get("models", ["gemma3:4b"])
        default_model = model_data.get("default", "gemma3:4b")
    except Exception:
        available_models = ["gemma3:4b"]
        default_model = "gemma3:4b"

    selected_model = st.selectbox("Model", available_models,
                                   index=available_models.index(default_model) if default_model in available_models else 0)

    system_prompt = st.text_area(
        "System Prompt",
        value="You are a helpful AI assistant.",
        height=100,
    )

    st.divider()

    # API health status
    try:
        health = requests.get(f"{API_URL}/health", timeout=3).json()
        status = health.get("status", "unknown")
        ollama = health.get("ollama", "unknown")
        color = "🟢" if status == "healthy" else "🟡"
        st.markdown(f"**API:** {color} {status}")
        st.markdown(f"**Ollama:** {'🟢' if ollama == 'connected' else '🔴'} {ollama}")
        st.caption(f"Env: {health.get('environment', 'unknown')}")
    except Exception:
        st.markdown("**API:** 🔴 unreachable")

    st.divider()

    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()


# ─────────────────────────────────────────────────────────────
# Main chat area
# ─────────────────────────────────────────────────────────────

st.title("🤖 AI Platform")
st.caption(f"Powered by {selected_model} — running locally via Ollama")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Ask anything..."):
    # Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get response from API
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""
        start = time.time()

        try:
            # Use streaming endpoint
            with requests.post(
                f"{API_URL}/chat/stream",
                json={
                    "message": prompt,
                    "model": selected_model,
                    "stream": True,
                    "system_prompt": system_prompt,
                },
                stream=True,
                timeout=120,
            ) as resp:
                for line in resp.iter_lines():
                    if line:
                        line_str = line.decode("utf-8")
                        if line_str.startswith("data: "):
                            data_str = line_str[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                token = data.get("token", "")
                                full_response += token
                                placeholder.markdown(full_response + "▌")
                            except json.JSONDecodeError:
                                continue

            duration = time.time() - start
            placeholder.markdown(full_response)
            st.caption(f"⏱ {duration:.1f}s · {len(full_response.split())} words")

        except Exception as e:
            full_response = f"Error connecting to API: {e}\n\nMake sure the API container is running."
            placeholder.error(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})
