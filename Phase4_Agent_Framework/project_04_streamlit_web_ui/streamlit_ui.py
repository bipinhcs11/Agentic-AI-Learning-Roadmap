# ═══════════════════════════════════════════════════════════════
# Project 04 — Streamlit Web UI (Chat Interface)
# Phase 4 · Agentic AI Learning Roadmap
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   A full chat web app for your local Ollama models.
#   Looks and feels like ChatGPT but runs 100% locally!
#
# INSTALL STREAMLIT FIRST:
#   pip install streamlit --break-system-packages
#
# HOW TO RUN:
#   1. ollama serve  (in another terminal)
#   2. source ~/Documents/my-ai-project/ai-env/bin/activate
#   3. streamlit run streamlit_ui.py
#   Browser opens at http://localhost:8501
# ═══════════════════════════════════════════════════════════════

import time
import requests

try:
    import streamlit as st
except ImportError:
    print("Streamlit not installed!")
    print("Run: pip install streamlit --break-system-packages")
    exit(1)

# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="Local AI Chat",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

OLLAMA_URL = "http://localhost:11434"


# ═══════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def get_available_models() -> list:
    """Fetch models from Ollama."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        models = resp.json().get("models", [])
        return [m.get("name") for m in models]
    except Exception:
        return ["gemma3:4b"]  # fallback


def stream_response(messages: list, model: str, temperature: float) -> str:
    """Stream response from Ollama and display in Streamlit."""
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": True,
                "options": {"temperature": temperature}
            },
            stream=True,
            timeout=120
        )

        full_response = ""
        placeholder = st.empty()

        for line in resp.iter_lines():
            if line:
                import json
                data = json.loads(line)
                token = data.get("message", {}).get("content", "")
                if token:
                    full_response += token
                    placeholder.markdown(full_response + "▌")
                if data.get("done"):
                    break

        placeholder.markdown(full_response)
        return full_response

    except requests.ConnectionError:
        error_msg = "❌ Cannot connect to Ollama. Make sure `ollama serve` is running!"
        st.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"❌ Error: {e}"
        st.error(error_msg)
        return error_msg


# ═══════════════════════════════════════════════════════════════
# SESSION STATE INITIALIZATION
# ═══════════════════════════════════════════════════════════════

if "messages" not in st.session_state:
    st.session_state.messages = []
if "total_tokens" not in st.session_state:
    st.session_state.total_tokens = 0
if "response_times" not in st.session_state:
    st.session_state.response_times = []


# ═══════════════════════════════════════════════════════════════
# SIDEBAR — Settings
# ═══════════════════════════════════════════════════════════════

with st.sidebar:
    st.title("⚙️ Settings")

    # Ollama status
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/version", timeout=2)
        st.success(f"✅ Ollama running (v{resp.json().get('version', '?')})")
    except Exception:
        st.error("❌ Ollama not running!\nRun: `ollama serve`")

    st.divider()

    # Model selection
    models = get_available_models()
    selected_model = st.selectbox(
        "🤖 Model",
        models,
        index=0,
        help="gemma3:4b is recommended (fast, low RAM)"
    )

    # Temperature
    temperature = st.slider(
        "🌡️ Temperature",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="Lower = more focused, Higher = more creative"
    )

    # System prompt
    system_prompt = st.text_area(
        "📋 System Prompt (optional)",
        value="You are a helpful AI assistant.",
        height=80,
        help="Instructions for how the AI should behave"
    )

    st.divider()

    # Stats
    st.subheader("📊 Session Stats")
    msg_count = len([m for m in st.session_state.messages if m["role"] == "user"])
    st.metric("Conversations", msg_count)
    if st.session_state.response_times:
        avg_time = sum(st.session_state.response_times) / len(st.session_state.response_times)
        st.metric("Avg Response Time", f"{avg_time:.1f}s")

    st.divider()

    # Clear button
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.response_times = []
        st.rerun()

    st.divider()
    st.caption("Phase 4 · Agentic AI Learning Roadmap")
    st.caption("Model: " + selected_model)


# ═══════════════════════════════════════════════════════════════
# MAIN CHAT AREA
# ═══════════════════════════════════════════════════════════════

st.title("🤖 Local AI Chat")
st.caption(f"Powered by Ollama + {selected_model} · Running 100% locally on your Mac")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Message the AI..."):

    # Show user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Add to history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Build messages for API (include system prompt)
    api_messages = []
    if system_prompt:
        api_messages.append({"role": "system", "content": system_prompt})
    api_messages.extend(st.session_state.messages)

    # Get AI response with streaming
    with st.chat_message("assistant"):
        start_time = time.time()
        response = stream_response(api_messages, selected_model, temperature)
        elapsed = time.time() - start_time
        st.session_state.response_times.append(elapsed)
        st.caption(f"⏱️ {elapsed:.1f}s · {selected_model}")

    # Save response
    st.session_state.messages.append({"role": "assistant", "content": response})

# Empty state
if not st.session_state.messages:
    st.info("👆 Type a message above to start chatting with your local AI!")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Try asking:**")
        st.markdown("- Explain machine learning")
        st.markdown("- Write a Python function")
    with col2:
        st.markdown("**Or:**")
        st.markdown("- Summarize a topic")
        st.markdown("- Help me debug code")
    with col3:
        st.markdown("**Or:**")
        st.markdown("- What is LangChain?")
        st.markdown("- Explain RAG to me")
