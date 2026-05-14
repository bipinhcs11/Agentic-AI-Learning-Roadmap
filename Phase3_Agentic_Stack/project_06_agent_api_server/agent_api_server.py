# ═══════════════════════════════════════════════════════════════
# Project 06 — Agent API Server
# Phase 3 · Agentic AI Learning Roadmap
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   Wraps an AI agent in a FastAPI server with REST endpoints.
#   After running, visit http://localhost:8000/docs to test it!
#
# HOW TO RUN:
#   1. ollama serve
#   2. source ~/Documents/my-ai-project/ai-env/bin/activate
#   3. python agent_api_server.py
#   4. Open browser: http://localhost:8000/docs
# ═══════════════════════════════════════════════════════════════

import json
import re
import uuid
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from openai import OpenAI
import uvicorn

# ── Setup ──────────────────────────────────────────────────────
ollama = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
MODEL = "gemma3:4b"

app = FastAPI(
    title="🤖 AI Agent API",
    description="A locally-hosted AI agent with tools, powered by Ollama + gemma3:4b",
    version="1.0.0",
)

# ── In-memory conversation storage ───────────────────────────
# Key: session_id → list of messages
sessions: dict = {}


# ═══════════════════════════════════════════════════════════════
# REQUEST / RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None  # if None, creates a new session

    class Config:
        json_schema_extra = {
            "example": {
                "message": "What is 25% of 480?",
                "session_id": None
            }
        }


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    tool_used: Optional[str] = None
    timestamp: str


class HistoryResponse(BaseModel):
    session_id: str
    messages: list
    message_count: int


# ═══════════════════════════════════════════════════════════════
# AGENT LOGIC (with tools)
# ═══════════════════════════════════════════════════════════════

def calculator(expression: str) -> str:
    try:
        allowed = set("0123456789+-*/.() ")
        if not all(c in allowed for c in expression):
            return "Error: invalid characters"
        return str(eval(expression))
    except Exception as e:
        return f"Error: {e}"


def get_time() -> str:
    return datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")


TOOLS = {"calculator": calculator, "get_time": get_time}

SYSTEM_PROMPT = """You are a helpful AI assistant with two tools:
- calculator(expression): for math (e.g., {"tool": "calculator", "args": {"expression": "2+2"}})
- get_time(): for current date/time (e.g., {"tool": "get_time", "args": {}})

To use a tool, reply with ONLY the JSON call.
Otherwise, answer normally.
Keep responses helpful and concise."""


def parse_tool_call(text: str):
    match = re.search(r'\{[^{}]*"tool"[^{}]*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass
    return None


def run_tool(tool_call: dict) -> tuple[str, str]:
    """Execute tool, return (result, tool_name)."""
    name = tool_call.get("tool", "")
    args = tool_call.get("args", {})
    if name not in TOOLS:
        return f"Unknown tool: {name}", name
    try:
        result = str(TOOLS[name](**args) if args else TOOLS[name]())
        return result, name
    except Exception as e:
        return f"Tool error: {e}", name


def agent_respond(user_message: str, history: list) -> tuple[str, Optional[str]]:
    """Run agent and return (response_text, tool_used_or_None)."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += history
    messages.append({"role": "user", "content": user_message})

    # First pass: see if model wants a tool
    resp = ollama.chat.completions.create(model=MODEL, messages=messages, temperature=0.1)
    first = resp.choices[0].message.content

    tool_call = parse_tool_call(first)
    if tool_call:
        tool_result, tool_name = run_tool(tool_call)
        # Second pass: generate final answer
        messages += [
            {"role": "assistant", "content": first},
            {"role": "user", "content": f"Tool result: {tool_result}. Now give a complete answer."}
        ]
        final = ollama.chat.completions.create(model=MODEL, messages=messages, temperature=0.3)
        return final.choices[0].message.content, tool_name

    return first, None


# ═══════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/health")
def health_check():
    """Check if the server is running."""
    return {
        "status": "ok",
        "model": MODEL,
        "ollama_url": "http://localhost:11434",
        "active_sessions": len(sessions),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Send a message to the AI agent and get a reply.

    - **message**: Your question or message
    - **session_id**: Optional. Pass the same ID to continue a conversation.
    """
    # Get or create session
    session_id = request.session_id or str(uuid.uuid4())[:8]
    if session_id not in sessions:
        sessions[session_id] = []

    history = sessions[session_id]

    try:
        reply, tool_used = agent_respond(request.message, history)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Agent error: {e}. Make sure 'ollama serve' is running."
        )

    # Save to history
    history.append({"role": "user", "content": request.message})
    history.append({"role": "assistant", "content": reply})

    # Keep history bounded
    if len(history) > 20:
        sessions[session_id] = history[-20:]

    return ChatResponse(
        reply=reply,
        session_id=session_id,
        tool_used=tool_used,
        timestamp=datetime.now().isoformat()
    )


@app.get("/history/{session_id}", response_model=HistoryResponse)
def get_history(session_id: str):
    """Get the conversation history for a session."""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    history = sessions[session_id]
    return HistoryResponse(
        session_id=session_id,
        messages=history,
        message_count=len(history)
    )


@app.delete("/history/{session_id}")
def clear_history(session_id: str):
    """Clear the conversation history for a session."""
    if session_id in sessions:
        del sessions[session_id]
        return {"message": f"Session '{session_id}' cleared"}
    raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")


@app.get("/sessions")
def list_sessions():
    """List all active sessions."""
    return {
        "sessions": [
            {"session_id": sid, "message_count": len(msgs)}
            for sid, msgs in sessions.items()
        ],
        "total": len(sessions)
    }


@app.get("/")
def root():
    """API root — redirect hint."""
    return {
        "message": "🤖 AI Agent API is running!",
        "docs": "http://localhost:8000/docs",
        "health": "http://localhost:8000/health",
        "chat_example": {
            "method": "POST",
            "url": "http://localhost:8000/chat",
            "body": {"message": "Hello! What can you do?"}
        }
    }


# ═══════════════════════════════════════════════════════════════
# START SERVER
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Agent API Server — Phase 3, Project 6")
    print("=" * 60)
    print(f"Model:  {MODEL} (local via Ollama)")
    print(f"Server: http://localhost:8000")
    print(f"Docs:   http://localhost:8000/docs  ← open this in browser!")
    print(f"Health: http://localhost:8000/health")
    print()
    print("Test with curl:")
    print('  curl -X POST "http://localhost:8000/chat" \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"message": "What is 42 * 7?"}\'')
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
