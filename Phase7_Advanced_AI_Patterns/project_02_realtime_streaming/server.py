"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║           PHASE 7 — PROJECT 2: REAL-TIME STREAMING AI (FastAPI + WebSocket)     ║
║                                                                                  ║
║  What this file does:                                                            ║
║    Implements a streaming AI chat server using FastAPI and WebSockets.           ║
║    When a user sends a message, Ollama generates a response token-by-token.      ║
║    Each token is pushed through the WebSocket connection as soon as it arrives   ║
║    — the user sees text appear progressively, just like ChatGPT.                 ║
║                                                                                  ║
║  Why WebSockets instead of plain HTTP?                                           ║
║    HTTP is request-response: you send a request, you wait, you get a response.   ║
║    With streaming you want to *push* data continuously as it becomes available.  ║
║    WebSocket creates a persistent two-way channel — the server can push tokens   ║
║    without the client asking for each one individually.                          ║
║                                                                                  ║
║  Endpoints:                                                                      ║
║    GET  /              → Serves the embedded HTML chat interface                 ║
║    GET  /health        → Health check (returns server + Ollama status)           ║
║    POST /chat          → Non-streaming chat for REST clients                     ║
║    WS   /ws/chat       → WebSocket streaming chat (main endpoint)                ║
║                                                                                  ║
║  How to run:                                                                     ║
║    uvicorn server:app --reload --port 8000                                       ║
║    Then open http://localhost:8000                                                ║
║                                                                                  ║
║  Dependencies: pip install fastapi "uvicorn[standard]" httpx python-dotenv       ║
║  Author : Bipin Pradhan                                                          ║
║  Phase  : 7 — Advanced AI Patterns                                               ║
╚══════════════════════════════════════════════════════════════════════════════════╝
"""

# ─────────────────────────────────────────────────────────────────────────────────
# IMPORTS
# ─────────────────────────────────────────────────────────────────────────────────
import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx                         # async HTTP client for Ollama streaming
from dotenv import load_dotenv       # load .env file (optional, for OLLAMA_URL override)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

# ─────────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# We use environment variables so the server can be reconfigured without code edits.
# OLLAMA_URL can be overridden in a .env file or shell environment.
# ─────────────────────────────────────────────────────────────────────────────────
load_dotenv()

OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gemma3:4b")
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8000"))


# ─────────────────────────────────────────────────────────────────────────────────
# CONNECTION TRACKER
# We track connected WebSocket clients for monitoring/logging purposes.
# This is a simple in-memory counter — in production you'd use Redis or a database.
# ─────────────────────────────────────────────────────────────────────────────────
class ConnectionTracker:
    """Tracks active WebSocket connections."""

    def __init__(self) -> None:
        self.count: int = 0
        self._connections: set[WebSocket] = set()

    def add(self, ws: WebSocket) -> None:
        self._connections.add(ws)
        self.count = len(self._connections)
        print(f"[Tracker] Client connected. Active connections: {self.count}")

    def remove(self, ws: WebSocket) -> None:
        self._connections.discard(ws)
        self.count = len(self._connections)
        print(f"[Tracker] Client disconnected. Active connections: {self.count}")


tracker = ConnectionTracker()


# ─────────────────────────────────────────────────────────────────────────────────
# EMBEDDED HTML INTERFACE
# The entire frontend is a single HTML string embedded in this Python file.
# This makes the server fully self-contained — no separate static file serving.
# The HTML uses vanilla JS with WebSocket API (built into every modern browser).
# ─────────────────────────────────────────────────────────────────────────────────

HTML_INTERFACE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>GraphStream AI Chat</title>
  <style>
    /* ── Reset & Base ────────────────────────────────────────────── */
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0f0f13;
      color: #e0e0e0;
      height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 1rem;
    }

    /* ── Layout ──────────────────────────────────────────────────── */
    .chat-container {
      width: 100%;
      max-width: 760px;
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    /* ── Header ──────────────────────────────────────────────────── */
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.75rem 0;
      border-bottom: 1px solid #2a2a3a;
    }
    header h1 { font-size: 1.2rem; font-weight: 600; color: #a78bfa; }
    header .subtitle { font-size: 0.75rem; color: #666; margin-top: 2px; }

    /* ── Connection status indicator ─────────────────────────────── */
    .status {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.8rem;
      color: #888;
    }
    .status-dot {
      width: 8px; height: 8px;
      border-radius: 50%;
      background: #ef4444;      /* red = disconnected */
      transition: background 0.3s;
    }
    .status-dot.connected { background: #22c55e; }  /* green = connected */

    /* ── Message area ────────────────────────────────────────────── */
    #messages {
      flex: 1;
      overflow-y: auto;
      padding: 1rem 0;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      min-height: 0;           /* allows flexbox child to scroll */
    }

    /* ── Individual message bubbles ──────────────────────────────── */
    .msg {
      max-width: 85%;
      padding: 0.65rem 1rem;
      border-radius: 1rem;
      line-height: 1.55;
      font-size: 0.92rem;
      word-break: break-word;
      white-space: pre-wrap;   /* preserve line breaks from the model */
    }
    .msg.user {
      align-self: flex-end;
      background: #4f46e5;
      color: #fff;
      border-bottom-right-radius: 0.25rem;
    }
    .msg.assistant {
      align-self: flex-start;
      background: #1e1e2e;
      border: 1px solid #2a2a3a;
      border-bottom-left-radius: 0.25rem;
    }
    .msg.system {
      align-self: center;
      background: transparent;
      color: #666;
      font-size: 0.78rem;
      font-style: italic;
      border: none;
      padding: 0.25rem 0;
    }

    /* Blinking cursor shown while the model is streaming */
    .cursor::after {
      content: "▌";
      animation: blink 0.7s step-end infinite;
      color: #a78bfa;
    }
    @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

    /* ── Token stats bar ─────────────────────────────────────────── */
    #stats {
      font-size: 0.72rem;
      color: #555;
      text-align: right;
      height: 1rem;
    }

    /* ── Input row ────────────────────────────────────────────────── */
    .input-row {
      display: flex;
      gap: 0.5rem;
      padding-bottom: 0.5rem;
    }
    #input {
      flex: 1;
      background: #1e1e2e;
      border: 1px solid #2a2a3a;
      border-radius: 0.6rem;
      padding: 0.65rem 1rem;
      color: #e0e0e0;
      font-size: 0.92rem;
      outline: none;
      resize: none;
      transition: border-color 0.2s;
    }
    #input:focus { border-color: #4f46e5; }
    #input:disabled { opacity: 0.5; }

    #send-btn {
      background: #4f46e5;
      border: none;
      border-radius: 0.6rem;
      color: #fff;
      padding: 0 1.25rem;
      font-size: 0.92rem;
      cursor: pointer;
      transition: background 0.2s, opacity 0.2s;
    }
    #send-btn:hover { background: #6366f1; }
    #send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
  </style>
</head>
<body>
  <div class="chat-container">
    <header>
      <div>
        <h1>GraphStream AI Chat</h1>
        <div class="subtitle">Phase 7 · Real-time WebSocket Streaming · Ollama</div>
      </div>
      <div class="status">
        <div class="status-dot" id="dot"></div>
        <span id="status-text">Connecting…</span>
      </div>
    </header>

    <div id="messages"></div>
    <div id="stats"></div>

    <div class="input-row">
      <textarea id="input" rows="2" placeholder="Type a message… (Enter to send, Shift+Enter for newline)" disabled></textarea>
      <button id="send-btn" disabled>Send</button>
    </div>
  </div>

  <script>
    // ── DOM references ───────────────────────────────────────────────────────────
    const messagesEl = document.getElementById('messages');
    const inputEl    = document.getElementById('input');
    const sendBtn    = document.getElementById('send-btn');
    const dot        = document.getElementById('dot');
    const statusText = document.getElementById('status-text');
    const statsEl    = document.getElementById('stats');

    // ── State ────────────────────────────────────────────────────────────────────
    let ws = null;           // WebSocket instance
    let streaming = false;   // true while model is generating
    let currentBubble = null;// the <div> currently receiving streamed tokens
    let tokenCount = 0;      // tokens received in current response
    let startTime = 0;       // when streaming started (for tokens/sec calc)

    // ── Helper: add a message bubble to the chat ─────────────────────────────────
    function addMessage(role, text) {
      const div = document.createElement('div');
      div.classList.add('msg', role);
      div.textContent = text;
      messagesEl.appendChild(div);
      messagesEl.scrollTop = messagesEl.scrollHeight;
      return div;
    }

    // ── WebSocket connection ──────────────────────────────────────────────────────
    // We use the same host/port as the page was served from, so this works
    // whether running locally or behind a proxy.
    function connect() {
      const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
      const url = `${protocol}//${location.host}/ws/chat`;
      ws = new WebSocket(url);

      ws.onopen = () => {
        dot.classList.add('connected');
        statusText.textContent = 'Connected';
        inputEl.disabled = false;
        sendBtn.disabled = false;
        inputEl.focus();
      };

      ws.onclose = () => {
        dot.classList.remove('connected');
        statusText.textContent = 'Disconnected — reconnecting…';
        inputEl.disabled = true;
        sendBtn.disabled = true;
        // Auto-reconnect after 3 seconds
        setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        statusText.textContent = 'Connection error';
      };

      // ── Incoming message handler ───────────────────────────────────────────────
      // The server sends JSON objects with a "type" field:
      //   {type: "welcome",  text: "..."}       — greeting on connect
      //   {type: "token",    text: "..."}        — one streaming token
      //   {type: "done",     total_tokens: N}    — stream complete
      //   {type: "error",    text: "..."}        — something went wrong
      ws.onmessage = (event) => {
        let msg;
        try { msg = JSON.parse(event.data); }
        catch { addMessage('system', event.data); return; }

        if (msg.type === 'welcome') {
          addMessage('system', msg.text);

        } else if (msg.type === 'token') {
          // First token of a new response — create the bubble
          if (!currentBubble) {
            currentBubble = addMessage('assistant', '');
            currentBubble.classList.add('cursor');
            startTime = Date.now();
            tokenCount = 0;
          }
          // Append the token to the current bubble
          currentBubble.textContent += msg.text;
          tokenCount++;
          messagesEl.scrollTop = messagesEl.scrollHeight;

          // Live stats update
          const elapsed = (Date.now() - startTime) / 1000;
          const tps = elapsed > 0 ? (tokenCount / elapsed).toFixed(1) : '—';
          statsEl.textContent = `${tokenCount} tokens · ${tps} tok/s`;

        } else if (msg.type === 'done') {
          // Streaming finished — remove blinking cursor, re-enable input
          if (currentBubble) {
            currentBubble.classList.remove('cursor');
            currentBubble = null;
          }
          streaming = false;
          setInputEnabled(true);
          const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
          const tps = elapsed > 0 ? (msg.total_tokens / elapsed).toFixed(1) : '—';
          statsEl.textContent = `Done · ${msg.total_tokens} tokens · ${tps} tok/s · ${elapsed}s`;

        } else if (msg.type === 'error') {
          if (currentBubble) currentBubble.classList.remove('cursor');
          currentBubble = null;
          streaming = false;
          setInputEnabled(true);
          addMessage('system', `Error: ${msg.text}`);
        }
      };
    }

    // ── Enable/disable input ──────────────────────────────────────────────────────
    function setInputEnabled(enabled) {
      inputEl.disabled = !enabled;
      sendBtn.disabled = !enabled;
      if (enabled) inputEl.focus();
    }

    // ── Send message ──────────────────────────────────────────────────────────────
    function sendMessage() {
      const text = inputEl.value.trim();
      if (!text || streaming || !ws || ws.readyState !== WebSocket.OPEN) return;

      addMessage('user', text);
      inputEl.value = '';
      statsEl.textContent = 'Generating…';
      streaming = true;
      setInputEnabled(false);

      // Send as JSON so the server can parse reliably
      ws.send(JSON.stringify({ message: text }));
    }

    // ── Input event listeners ─────────────────────────────────────────────────────
    sendBtn.addEventListener('click', sendMessage);
    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    // ── Boot ──────────────────────────────────────────────────────────────────────
    connect();
  </script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────────
# FASTAPI APPLICATION
# The lifespan context manager runs startup/shutdown logic.
# We use it to verify Ollama is reachable before accepting traffic.
# ─────────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Lifespan handler: runs on startup (before yield) and shutdown (after yield).
    We check Ollama connectivity at startup so we fail fast with a clear message.
    """
    print(f"[Server] Starting GraphStream AI server …")
    print(f"[Server] Ollama URL : {OLLAMA_URL}")
    print(f"[Server] Model      : {OLLAMA_MODEL}")

    # Quick connectivity check — non-fatal (Ollama might start later)
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                print(f"[Server] Ollama reachable. Available models: {models}")
            else:
                print(f"[Server] Ollama responded with status {resp.status_code}")
    except Exception as exc:
        print(f"[Server] WARNING: Could not reach Ollama at {OLLAMA_URL}: {exc}")
        print(f"[Server] Server will start anyway. Ensure Ollama is running.")

    yield   # <── server runs here

    print("[Server] Shutting down.")


app = FastAPI(
    title="GraphStream AI Chat",
    description="Real-time streaming AI chat via WebSocket + Ollama",
    version="1.0.0",
    lifespan=lifespan,
)


# ─────────────────────────────────────────────────────────────────────────────────
# OLLAMA STREAMING HELPER
# This is the heart of the streaming implementation.
# Ollama's /api/generate endpoint accepts a "stream": true parameter.
# With streaming enabled, the response is a series of newline-delimited JSON
# objects, each containing one token in the "response" field.
# We yield each token as it arrives using Python async generators.
# ─────────────────────────────────────────────────────────────────────────────────

async def stream_ollama_tokens(prompt: str) -> AsyncIterator[str]:
    """
    Async generator that yields one token string at a time from Ollama.

    Implementation details:
    - httpx.AsyncClient with stream=True keeps the HTTP connection open
    - aiter_lines() reads the response line by line as they arrive
    - Each line is a JSON object; we extract the "response" field
    - When "done" is true in the JSON, we stop iteration
    """
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,          # CRITICAL: enables token-by-token streaming
        "options": {
            "temperature": 0.7,  # moderate creativity
            "num_predict": 512,  # max tokens to generate
        }
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{OLLAMA_URL}/api/generate",
            json=payload,
        ) as response:
            if response.status_code != 200:
                error_body = await response.aread()
                raise RuntimeError(
                    f"Ollama returned {response.status_code}: {error_body.decode()[:200]}"
                )

            # aiter_lines() is an async iterator — each "next" awaits the next
            # newline from the HTTP response body
            async for line in response.aiter_lines():
                line = line.strip()
                if not line:
                    continue   # skip blank lines

                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue   # skip malformed lines

                token = data.get("response", "")
                if token:
                    yield token

                # Ollama sets done=True on the final chunk
                if data.get("done", False):
                    break


# ─────────────────────────────────────────────────────────────────────────────────
# PYDANTIC MODELS (for POST /chat request/response typing)
# ─────────────────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Request body for the non-streaming POST /chat endpoint."""
    message: str
    system_prompt: str = "You are a helpful AI assistant."


class ChatResponse(BaseModel):
    """Response body for the non-streaming POST /chat endpoint."""
    response: str
    model: str
    tokens_generated: int


# ─────────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_ui() -> HTMLResponse:
    """
    Serve the embedded HTML interface.
    Returning HTMLResponse with the string directly — no file I/O needed.
    """
    return HTMLResponse(content=HTML_INTERFACE)


@app.get("/health")
async def health_check() -> JSONResponse:
    """
    Health check endpoint. Checks both server status and Ollama reachability.
    Useful for monitoring and load balancer health probes.
    """
    ollama_ok = False
    ollama_models: list[str] = []

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            if resp.status_code == 200:
                ollama_ok = True
                ollama_models = [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        pass

    return JSONResponse({
        "status": "ok",
        "server": "running",
        "ollama_reachable": ollama_ok,
        "ollama_url": OLLAMA_URL,
        "model": OLLAMA_MODEL,
        "available_models": ollama_models,
        "active_connections": tracker.count,
    })


@app.post("/chat", response_model=ChatResponse)
async def chat_rest(request: ChatRequest) -> ChatResponse:
    """
    Standard non-streaming POST endpoint.
    Collects the full Ollama response then returns it in one HTTP response.
    Useful for REST clients that don't support WebSockets.
    """
    prompt = f"{request.system_prompt}\n\nUser: {request.message}\nAssistant:"
    tokens: list[str] = []

    try:
        async for token in stream_ollama_tokens(prompt):
            tokens.append(token)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Ollama error: {exc}")

    full_response = "".join(tokens)
    return ChatResponse(
        response=full_response,
        model=OLLAMA_MODEL,
        tokens_generated=len(tokens),
    )


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    """
    WebSocket endpoint — the main streaming chat interface.

    Protocol (all messages are JSON):
      Server → Client:
        {type: "welcome",  text: "..."}        — on connection open
        {type: "token",    text: "..."}         — one streaming token
        {type: "done",     total_tokens: N}     — stream finished
        {type: "error",    text: "..."}         — on error

      Client → Server:
        {message: "user text"}                  — send a chat message
        (or plain string, for backwards compatibility)

    Why async? WebSocket I/O is inherently async — we don't block waiting for
    tokens, we await them. This lets FastAPI handle thousands of connections
    concurrently without threading overhead.
    """
    await websocket.accept()
    tracker.add(websocket)

    # Send welcome message so the client knows the connection is live
    await websocket.send_json({
        "type": "welcome",
        "text": f"Connected to GraphStream AI · Model: {OLLAMA_MODEL} · Type a message to begin."
    })

    try:
        while True:
            # Wait for a message from the client (blocks until message arrives)
            raw = await websocket.receive_text()

            # Parse the incoming message — support both JSON and plain string
            try:
                data = json.loads(raw)
                user_message = data.get("message", raw)
            except json.JSONDecodeError:
                user_message = raw

            user_message = user_message.strip()
            if not user_message:
                continue

            print(f"[WS] Received: '{user_message[:80]}'")

            # Build a conversational prompt
            prompt = (
                "You are a helpful, concise AI assistant. "
                "Answer the user's question clearly.\n\n"
                f"User: {user_message}\nAssistant:"
            )

            # ── Stream tokens back to the client ──────────────────────────────────
            # Each token arrives from Ollama as soon as it's generated.
            # We immediately push it to the WebSocket — no buffering.
            token_count = 0
            try:
                async for token in stream_ollama_tokens(prompt):
                    await websocket.send_json({"type": "token", "text": token})
                    token_count += 1

                # Signal that the full response has been sent
                await websocket.send_json({
                    "type": "done",
                    "total_tokens": token_count,
                })
                print(f"[WS] Done. Streamed {token_count} tokens.")

            except asyncio.CancelledError:
                # Client disconnected mid-stream
                print("[WS] Stream cancelled (client disconnected mid-stream)")
                break
            except Exception as exc:
                print(f"[WS] Stream error: {exc}")
                await websocket.send_json({
                    "type": "error",
                    "text": str(exc),
                })

    except WebSocketDisconnect:
        print("[WS] Client disconnected normally")
    except Exception as exc:
        print(f"[WS] Unexpected error: {exc}")
    finally:
        tracker.remove(websocket)


# ─────────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# Running directly (python server.py) uses uvicorn programmatically.
# Preferred invocation: uvicorn server:app --reload
# ─────────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print(f"Starting server on {HOST}:{PORT}")
    print(f"Open http://localhost:{PORT} in your browser")
    uvicorn.run("server:app", host=HOST, port=PORT, reload=True)
