# Phase 7 — Project 2: Real-time Streaming AI (FastAPI + WebSocket)

## What WebSockets Are vs HTTP

```
HTTP (Request-Response)
───────────────────────
Client          Server
  │──── GET /chat ────►│
  │                    │  [waits for full response]
  │◄─── 200 OK ────────│
  │   (all at once)    │
  │                    │
  │ (connection closes)│

  ↑ You wait in silence until the ENTIRE response is ready. With slow LLMs,
    this can be 10–30 seconds of nothing. Users see a loading spinner.


WebSocket (Persistent Bidirectional Channel)
────────────────────────────────────────────
Client          Server
  │──── Upgrade to WS ─►│
  │◄─── 101 Switching ──│  (connection stays open)
  │                     │
  │──── "user message" ─►│
  │◄── "I" ─────────────│  token 1 arrives instantly
  │◄── " think" ─────────│  token 2
  │◄── " the" ───────────│  token 3
  │◄── " answer" ────────│  ...
  │◄── " is" ────────────│
  │◄── " 42." ───────────│  last token
  │◄── {done} ───────────│  stream finished signal
  │                     │
  │ (connection stays open for next message)

  ↑ Text appears as it's generated. Users feel the AI is "thinking" live.
    Same total time, but perceived as MUCH faster. No spinner needed.
```

## Why Streaming Matters for AI UX

**Without streaming:** User sends message → 8 seconds of nothing → full response appears.

**With streaming:** User sends message → first word appears in ~0.3s → words keep flowing.

Research consistently shows perceived response time matters more than actual response time. Streaming typically feels 3-5x faster even with identical model speed because:
1. Users start reading while the model is still generating
2. The "first token" appears almost immediately
3. There is always visible progress — no uncertainty about whether it's working

This is why ChatGPT, Claude.ai, and every production LLM interface uses streaming.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         server.py                               │
│                                                                 │
│  GET /  ──────────────────────────────────────► HTML (inline)  │
│                                                                 │
│  GET /health ──────────────────────────────────► JSON status   │
│                                                                 │
│  POST /chat ──► collect all tokens ──────────► JSON response   │
│                                                                 │
│  WS /ws/chat                                                    │
│    client connects                                              │
│    server sends: {type:"welcome"}                               │
│    client sends: {message:"..."}                                │
│    server:                                                      │
│      httpx async stream ──► Ollama /api/generate               │
│                                 │                              │
│                      for each token:                           │
│                         send {type:"token", text:"..."}        │
│                      send {type:"done", total_tokens:N}        │
│                                                                 │
│  Connection tracking: ConnectionTracker counts active WS clients│
└─────────────────────────────────────────────────────────────────┘
```

## Files

| File | Purpose |
|---|---|
| `server.py` | FastAPI app with WebSocket endpoint + embedded HTML UI |
| `streaming_client.py` | Python terminal client for testing without a browser |
| `requirements.txt` | Python dependencies |

## Requirements

```bash
pip install -r requirements.txt
```

You also need [Ollama](https://ollama.com) running:
```bash
ollama pull gemma3:4b
ollama serve        # starts on http://localhost:11434
```

## How to Run

### Start the server
```bash
cd "Phase7_Advanced_AI_Patterns/project_02_realtime_streaming"
uvicorn server:app --reload --port 8000
```

### Open the browser UI
Go to http://localhost:8000 — you'll see the streaming chat interface.

### Test with the Python client (no browser needed)
```bash
python streaming_client.py
```
This connects to the WebSocket and streams 3 demo prompts to your terminal. You'll see tokens arriving one at a time with a tokens/sec stat at the end.

### Test the REST endpoint (non-streaming)
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 2+2?"}'
```

### Health check
```bash
curl http://localhost:8000/health
```

## Configuration

You can set these in a `.env` file or as environment variables:

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `gemma3:4b` | Model to use for generation |
| `PORT` | `8000` | Server port |
| `HOST` | `0.0.0.0` | Server host |

## WebSocket Message Protocol

The server and client communicate using JSON messages:

**Server → Client:**
```json
{"type": "welcome",  "text": "Connected to GraphStream AI…"}
{"type": "token",    "text": "Hello"}
{"type": "token",    "text": " world"}
{"type": "done",     "total_tokens": 42}
{"type": "error",    "text": "Ollama returned 503"}
```

**Client → Server:**
```json
{"message": "What is the capital of France?"}
```

## Key Concepts Demonstrated

| Concept | Where |
|---|---|
| **WebSocket upgrade** | Browser opens `ws://` URL; server accepts via `@app.websocket()` |
| **Async generators** | `stream_ollama_tokens()` yields tokens without blocking the event loop |
| **httpx streaming** | `client.stream()` + `aiter_lines()` reads Ollama response line by line |
| **Bidirectional WS** | Server pushes tokens; client sends new messages on same connection |
| **Self-contained HTML** | Entire frontend embedded as a Python string in `server.py` |
| **Graceful disconnect** | `WebSocketDisconnect` caught; connection removed from tracker |
