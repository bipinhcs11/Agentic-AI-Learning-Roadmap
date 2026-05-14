# ═══════════════════════════════════════════════════════════════
# Project 04 — Multi-Tool Agent
# Phase 3 · Agentic AI Learning Roadmap
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   An agent with many tools. Shows how a real production agent
#   works — pick the right tool, call it, use the result.
#
# HOW TO RUN:
#   1. ollama serve
#   2. source ~/Documents/my-ai-project/ai-env/bin/activate
#   3. python multi_tool_agent.py
# ═══════════════════════════════════════════════════════════════

import json
import os
import re
from datetime import datetime
from openai import OpenAI

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
MODEL = "gemma3:4b"
NOTES_FILE = os.path.join(os.path.dirname(__file__), "notes.txt")

# ═══════════════════════════════════════════════════════════════
# TOOL DEFINITIONS
# ═══════════════════════════════════════════════════════════════

def calculator(expression: str) -> str:
    """Evaluate a safe math expression."""
    try:
        allowed = set("0123456789+-*/.() ")
        if not all(c in allowed for c in expression):
            return "Error: Use only numbers and +−×÷() operators"
        result = eval(expression)
        return f"{result}"
    except Exception as e:
        return f"Math error: {e}"


def save_note(text: str) -> str:
    """Save a note to the notes file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"[{timestamp}] {text}\n"
    with open(NOTES_FILE, "a") as f:
        f.write(entry)
    return f"Note saved: '{text}'"


def read_notes() -> str:
    """Read all saved notes."""
    if not os.path.exists(NOTES_FILE):
        return "No notes saved yet."
    with open(NOTES_FILE, "r") as f:
        content = f.read().strip()
    if not content:
        return "Notes file is empty."
    lines = content.split("\n")
    return f"Your notes ({len(lines)} total):\n" + content


def list_files(directory: str = ".") -> str:
    """List files in a directory."""
    try:
        path = os.path.expanduser(directory)
        if not os.path.exists(path):
            return f"Directory not found: {directory}"
        items = os.listdir(path)
        files = [f for f in items if os.path.isfile(os.path.join(path, f))]
        dirs = [f for f in items if os.path.isdir(os.path.join(path, f))]
        result = f"Directory: {path}\n"
        if dirs:
            result += f"Folders ({len(dirs)}): {', '.join(sorted(dirs)[:10])}\n"
        if files:
            result += f"Files ({len(files)}): {', '.join(sorted(files)[:15])}"
        return result
    except Exception as e:
        return f"Error: {e}"


def word_count(text: str) -> str:
    """Count words, characters, and sentences."""
    words = len(text.split())
    chars = len(text)
    sentences = max(1, text.count('.') + text.count('!') + text.count('?'))
    return f"Words: {words} | Characters: {chars} | Sentences: {sentences}"


def web_fetch(url: str) -> str:
    """Fetch a web page and return clean text."""
    if not HAS_REQUESTS:
        return "Error: requests library not installed. Run: pip install requests beautifulsoup4"
    if not url.startswith("http"):
        url = "https://" + url
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=8)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        clean = "\n".join(lines)[:3000]
        title = soup.find("title")
        title_text = title.get_text().strip() if title else url
        return f"Title: {title_text}\n\n{clean}"
    except Exception as e:
        return f"Error fetching {url}: {e}"


def get_current_time() -> str:
    """Return current date and time."""
    return datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")


def clear_notes() -> str:
    """Clear all notes."""
    if os.path.exists(NOTES_FILE):
        os.remove(NOTES_FILE)
    return "All notes cleared."


# ── Tool Registry ─────────────────────────────────────────────
TOOLS = {
    "calculator":     calculator,
    "save_note":      save_note,
    "read_notes":     read_notes,
    "list_files":     list_files,
    "word_count":     word_count,
    "web_fetch":      web_fetch,
    "get_current_time": get_current_time,
    "clear_notes":    clear_notes,
}

# ── System Prompt: tells the model how to use tools ──────────
SYSTEM_PROMPT = """You are a powerful AI assistant with access to tools.

AVAILABLE TOOLS:
- calculator(expression)     → math: e.g., calculator("15 * 8.5")
- save_note(text)            → save text as a note
- read_notes()               → read all saved notes
- clear_notes()              → delete all notes
- list_files(directory)      → list files, e.g., list_files("~/Downloads")
- word_count(text)           → count words in text
- web_fetch(url)             → fetch a web page
- get_current_time()         → current date and time

WHEN TO USE TOOLS:
- Math question → use calculator
- "Save/remember this" → use save_note
- "What notes do I have" → use read_notes
- "What files are in..." → use list_files
- "Count words in..." → use word_count
- "Fetch/scrape/summarize [URL]" → use web_fetch
- "What time/date is it" → use get_current_time

TO CALL A TOOL, respond with EXACTLY this JSON (nothing else in that line):
{"tool": "calculator", "args": {"expression": "2+2"}}

If no tool is needed, answer normally.
After a tool result, give a helpful, complete answer.
"""


# ═══════════════════════════════════════════════════════════════
# AGENT LOOP — With multi-step tool chaining
# ═══════════════════════════════════════════════════════════════

def parse_tool_call(text: str):
    """Extract JSON tool call from model response."""
    match = re.search(r'\{[^{}]*"tool"\s*:[^{}]*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def run_tool(tool_call: dict) -> str:
    """Execute a tool."""
    name = tool_call.get("tool", "")
    args = tool_call.get("args", {})
    if name not in TOOLS:
        return f"Unknown tool: {name}"
    try:
        return str(TOOLS[name](**args) if args else TOOLS[name]())
    except TypeError as e:
        return f"Tool argument error: {e}"
    except Exception as e:
        return f"Tool error: {e}"


def agent_chat(user_message: str, history: list) -> str:
    """Run one turn of the agent — may use a tool."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += history
    messages.append({"role": "user", "content": user_message})

    # Step 1: Get model's initial response
    resp = client.chat.completions.create(model=MODEL, messages=messages, temperature=0.1)
    model_output = resp.choices[0].message.content

    # Step 2: Check for tool call
    tool_call = parse_tool_call(model_output)
    if tool_call:
        tool_name = tool_call.get("tool", "unknown")
        print(f"🔧 Using tool: {tool_name}", end="", flush=True)
        result = run_tool(tool_call)
        print(f" → {result[:80]}{'...' if len(result) > 80 else ''}")

        # Step 3: Feed result back for final answer
        messages += [
            {"role": "assistant", "content": model_output},
            {"role": "user", "content": f"Tool '{tool_name}' returned: {result}\n\nNow give a clear, complete answer."}
        ]
        final = client.chat.completions.create(model=MODEL, messages=messages, temperature=0.4)
        return final.choices[0].message.content

    return model_output


def main():
    print("=" * 60)
    print("🛠️  Multi-Tool Agent — Phase 3, Project 4")
    print("=" * 60)
    print(f"Model: {MODEL} | Tools: {len(TOOLS)} available")
    print(f"Notes saved to: {NOTES_FILE}")
    print("\nTry:")
    print("  • What is 17% of 2500?")
    print("  • Save a note: buy groceries tomorrow")
    print("  • What notes do I have?")
    print("  • List files in my Downloads folder")
    print("  • What time is it?")
    print("  • Fetch https://en.wikipedia.org/wiki/Machine_learning")
    print("\nType 'quit' to exit | 'tools' to list all tools")
    print("=" * 60)

    history = []

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
        if user_input.lower() == "tools":
            print("\nAvailable tools:")
            for name, func in TOOLS.items():
                print(f"  • {name}: {func.__doc__}")
            continue

        print("🤔 ...", end="", flush=True)
        try:
            response = agent_chat(user_input, history)
            print(f"\r🤖 Agent: {response}")
            history += [
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": response}
            ]
            if len(history) > 20:
                history = history[-20:]
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Make sure 'ollama serve' is running.")


if __name__ == "__main__":
    main()
