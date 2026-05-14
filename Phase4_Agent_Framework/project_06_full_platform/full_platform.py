# ═══════════════════════════════════════════════════════════════
# Project 06 — Full Platform (Capstone)
# Phase 4 · Agentic AI Learning Roadmap
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   The capstone project — combines everything:
#   - Multi-tool agent (Phase 3)
#   - Persistent memory (Phase 3)
#   - FastAPI server (Phase 3/4)
#   - Custom framework (Phase 4)
#
# This is a demo of your complete skill set!
#
# HOW TO RUN:
#   1. ollama serve
#   2. source ~/Documents/my-ai-project/ai-env/bin/activate
#   3. python full_platform.py
# ═══════════════════════════════════════════════════════════════

import json
import os
import re
import math
import time
import uuid
import threading
from datetime import datetime
from typing import Optional

import requests
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

# ─────────────────────────────────────────────────────────────
OLLAMA_URL  = "http://localhost:11434"
MODEL       = "gemma3:4b"
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "platform_memory.json")
LOG_FILE    = os.path.join(os.path.dirname(__file__), "platform_log.jsonl")
API_PORT    = 8003
# ─────────────────────────────────────────────────────────────

llm = OpenAI(base_url=f"{OLLAMA_URL}/v1", api_key="ollama")

# ═══════════════════════════════════════════════════════════════
# MEMORY SYSTEM
# ═══════════════════════════════════════════════════════════════

def load_memory() -> dict:
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE) as f:
            return json.load(f)
    return {"users": {}, "global_notes": [], "session_count": 0}


def save_memory(mem: dict):
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, indent=2)


platform_memory = load_memory()
platform_memory["session_count"] = platform_memory.get("session_count", 0) + 1
save_memory(platform_memory)


# ═══════════════════════════════════════════════════════════════
# TOOL REGISTRY
# ═══════════════════════════════════════════════════════════════

TOOLS = {}

def tool(description: str):
    def decorator(func):
        TOOLS[func.__name__] = {"func": func, "description": description}
        return func
    return decorator


@tool("Calculate math expression")
def calculator(expression: str) -> str:
    try:
        allowed = set("0123456789+-*/.() ")
        if all(c in allowed for c in expression):
            return str(eval(expression))
        return "Invalid expression"
    except Exception as e:
        return f"Error: {e}"


@tool("Get current date and time")
def get_time() -> str:
    return datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")


@tool("Save a note to the platform")
def save_note(text: str) -> str:
    platform_memory["global_notes"].append({
        "text": text,
        "timestamp": datetime.now().isoformat()
    })
    save_memory(platform_memory)
    return f"Note saved: {text}"


@tool("Read all saved notes")
def read_notes() -> str:
    notes = platform_memory.get("global_notes", [])
    if not notes:
        return "No notes saved."
    return "\n".join(f"[{n['timestamp'][:10]}] {n['text']}" for n in notes[-10:])


@tool("Search web page content")
def web_search(url: str) -> str:
    try:
        from bs4 import BeautifulSoup
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav"]):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ").split())
        return text[:2000]
    except Exception as e:
        return f"Error: {e}"


@tool("Convert Celsius to Fahrenheit")
def convert_temp(celsius: float) -> str:
    f = float(celsius) * 9/5 + 32
    return f"{celsius}°C = {f:.1f}°F"


def get_tool_list() -> str:
    lines = ["TOOLS (use JSON to call):"]
    for name, info in TOOLS.items():
        lines.append(f"  {name} — {info['description']}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# AGENT LOOP
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """{tool_list}

You are a helpful AI assistant with memory and tools.

MEMORY CONTEXT:
Session #{session_count}
Notes: {note_count} saved

To use a tool, reply with JSON: {{"tool": "name", "args": {{"param": "value"}}}}
For final answer: {{"final_answer": "your response"}}
"""


def run_agent(user_message: str, history: list, session_id: str) -> str:
    """Run the agent with tools and memory."""
    note_count = len(platform_memory.get("global_notes", []))
    system = SYSTEM_PROMPT.format(
        tool_list=get_tool_list(),
        session_count=platform_memory["session_count"],
        note_count=note_count
    )

    messages = [{"role": "system", "content": system}]
    messages += history[-10:]  # last 5 exchanges
    messages.append({"role": "user", "content": user_message})

    for step in range(5):  # max 5 steps
        resp = llm.chat.completions.create(
            model=MODEL, messages=messages, temperature=0.2
        )
        text = resp.choices[0].message.content

        # Parse response
        match = re.search(r'\{[^{}]+\}', text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())

                # Final answer
                if "final_answer" in data:
                    return data["final_answer"]

                # Tool call
                if "tool" in data:
                    tool_name = data["tool"]
                    args = data.get("args", {})
                    if tool_name in TOOLS:
                        result = str(TOOLS[tool_name]["func"](**args) if args else TOOLS[tool_name]["func"]())
                        messages.append({"role": "assistant", "content": text})
                        messages.append({"role": "user", "content": f"Tool '{tool_name}' returned: {result}. Continue."})
                        continue

            except (json.JSONDecodeError, TypeError):
                pass

        # No JSON — treat as direct answer
        return text

    return "I couldn't complete that in the allowed steps. Please try again."


# ═══════════════════════════════════════════════════════════════
# FASTAPI SERVER
# ═══════════════════════════════════════════════════════════════

app = FastAPI(title="🏆 Full AI Platform", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

sessions: dict = {}  # session_id → message history


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


@app.post("/chat")
def chat(req: ChatRequest):
    sid = req.session_id or str(uuid.uuid4())[:8]
    if sid not in sessions:
        sessions[sid] = []

    start = time.time()
    reply = run_agent(req.message, sessions[sid], sid)
    elapsed = round(time.time() - start, 2)

    sessions[sid] += [
        {"role": "user", "content": req.message},
        {"role": "assistant", "content": reply}
    ]
    if len(sessions[sid]) > 20:
        sessions[sid] = sessions[sid][-20:]

    # Log
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps({
            "ts": datetime.now().isoformat(),
            "session": sid,
            "user": req.message[:100],
            "reply": reply[:200],
            "elapsed_s": elapsed
        }) + "\n")

    return {"reply": reply, "session_id": sid, "elapsed_s": elapsed}


@app.get("/memory")
def get_memory():
    return {
        "session_count": platform_memory.get("session_count", 0),
        "note_count": len(platform_memory.get("global_notes", [])),
        "notes": platform_memory.get("global_notes", [])[-5:],
    }


@app.get("/health")
def health():
    try:
        r = requests.get(f"{OLLAMA_URL}/api/version", timeout=2)
        ollama = "ok"
    except Exception:
        ollama = "not running"
    return {"server": "ok", "ollama": ollama, "model": MODEL, "sessions": len(sessions)}


@app.get("/")
def root():
    return {
        "name": "Full AI Platform — Phase 4 Capstone",
        "docs": f"http://localhost:{API_PORT}/docs",
        "chat": f"POST http://localhost:{API_PORT}/chat",
        "memory": f"GET http://localhost:{API_PORT}/memory",
    }


# ═══════════════════════════════════════════════════════════════
# CLI MODE (run without web server)
# ═══════════════════════════════════════════════════════════════

def run_cli():
    """Run in terminal mode."""
    print("=" * 60)
    print("🏆 Full AI Platform — Phase 4, Project 6 (CAPSTONE)")
    print("=" * 60)
    print(f"Model: {MODEL} | Memory: {MEMORY_FILE}")
    print(f"Session #{platform_memory['session_count']}")
    print(f"Notes stored: {len(platform_memory.get('global_notes', []))}")
    print("\nAll tools active: calculator, timer, notes, web, temp")
    print("Type 'server' to start API server | 'quit' to exit")
    print("=" * 60)

    history = []
    session_id = str(uuid.uuid4())[:8]

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Goodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ["quit", "exit", "q"]:
            print("👋 Goodbye!")
            break
        if user_input.lower() == "server":
            print(f"\n🚀 Starting API server on port {API_PORT}...")
            print(f"   Docs: http://localhost:{API_PORT}/docs")
            uvicorn.run(app, host="0.0.0.0", port=API_PORT, log_level="warning")
            break

        print("🤔 ...", end="", flush=True)
        try:
            start = time.time()
            response = run_agent(user_input, history, session_id)
            elapsed = time.time() - start
            print(f"\r🤖 Agent ({elapsed:.1f}s): {response}")
            history += [
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": response}
            ]
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Make sure 'ollama serve' is running.")


if __name__ == "__main__":
    import sys
    if "--server" in sys.argv:
        print(f"🚀 Starting Full Platform API on port {API_PORT}")
        print(f"   Docs: http://localhost:{API_PORT}/docs")
        uvicorn.run(app, host="0.0.0.0", port=API_PORT, log_level="info")
    else:
        run_cli()
