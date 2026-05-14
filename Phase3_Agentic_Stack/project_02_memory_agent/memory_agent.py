# ═══════════════════════════════════════════════════════════════
# Project 02 — Memory Agent
# Phase 3 · Agentic AI Learning Roadmap
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   An agent with TWO kinds of memory:
#   1. Short-term: remembers the current conversation
#   2. Long-term: saves facts to a file, remembered next session
#
# HOW TO RUN:
#   1. ollama serve  (in a separate terminal)
#   2. source ~/Documents/my-ai-project/ai-env/bin/activate
#   3. python memory_agent.py
#   Try: tell it your name, quit, restart, ask "what's my name?"
# ═══════════════════════════════════════════════════════════════

import json
import os
import re
from datetime import datetime
from openai import OpenAI

# ── Connect to Ollama ─────────────────────────────────────────
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
MODEL = "gemma3:4b"

# ── Where to save long-term memory ───────────────────────────
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")

# ═══════════════════════════════════════════════════════════════
# LONG-TERM MEMORY — Saved to disk, persists between sessions
# ═══════════════════════════════════════════════════════════════

def load_memory() -> dict:
    """Load saved memories from file."""
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    # Default empty memory structure
    return {
        "user_profile": {},
        "facts": [],
        "preferences": [],
        "conversation_count": 0,
        "first_seen": datetime.now().isoformat(),
        "last_seen": None,
    }


def save_memory(memory: dict):
    """Save memories to file."""
    memory["last_seen"] = datetime.now().isoformat()
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)
    print(f"  💾 Memory saved to {MEMORY_FILE}")


def format_memory_for_prompt(memory: dict) -> str:
    """Convert memory dict into a string the AI can read."""
    lines = ["=== WHAT I REMEMBER ABOUT YOU ==="]

    if memory["user_profile"]:
        lines.append("User profile:")
        for key, value in memory["user_profile"].items():
            lines.append(f"  - {key}: {value}")

    if memory["facts"]:
        lines.append("\nImportant facts:")
        for fact in memory["facts"][-10:]:  # last 10 facts
            lines.append(f"  - {fact}")

    if memory["preferences"]:
        lines.append("\nPreferences:")
        for pref in memory["preferences"][-5:]:
            lines.append(f"  - {pref}")

    count = memory.get("conversation_count", 0)
    if count > 0:
        lines.append(f"\nWe have talked {count} time(s) before.")

    if not memory["user_profile"] and not memory["facts"]:
        lines.append("(No memories yet — this is our first conversation!)")

    return "\n".join(lines)


def extract_memories(user_message: str, agent_response: str, memory: dict):
    """
    Look for memorable facts in the conversation and save them.
    Simple rule-based extraction (no extra AI call needed).
    """
    text = user_message.lower()

    # Extract name
    name_patterns = [
        r"my name is (\w+)",
        r"i am (\w+)",
        r"i'm (\w+)",
        r"call me (\w+)",
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text)
        if match:
            name = match.group(1).capitalize()
            memory["user_profile"]["name"] = name
            print(f"  🧠 Remembered: your name is {name}")
            break

    # Extract job/role
    job_patterns = [
        r"i (?:am|work as|work in) (?:a |an )?(.+?)(?:\.|,|$)",
        r"my (?:job|role|profession) is (.+?)(?:\.|,|$)",
    ]
    for pattern in job_patterns:
        match = re.search(pattern, text)
        if match:
            job = match.group(1).strip()
            if len(job) < 50:  # sanity check
                memory["user_profile"]["job"] = job
                print(f"  🧠 Remembered: your job is {job}")
            break

    # Extract preferences (like/love/prefer/hate)
    pref_patterns = [
        r"i (?:like|love|prefer|enjoy) (.+?)(?:\.|,|$)",
        r"i (?:don't like|hate|dislike) (.+?)(?:\.|,|$)",
        r"my favorite (?:\w+ )?is (.+?)(?:\.|,|$)",
    ]
    for pattern in pref_patterns:
        match = re.search(pattern, text)
        if match:
            pref = match.group(0).strip()
            if len(pref) < 100 and pref not in memory["preferences"]:
                memory["preferences"].append(pref)
                print(f"  🧠 Remembered preference: {pref}")

    # Save any sentence with "I" as a potential fact (simple heuristic)
    if any(phrase in text for phrase in ["i live", "i have", "i own", "i use", "i studied", "i learned"]):
        fact = user_message.strip()
        if len(fact) < 200 and fact not in memory["facts"]:
            memory["facts"].append(fact)
            print(f"  🧠 Saved fact: {fact[:60]}...")


# ═══════════════════════════════════════════════════════════════
# MAIN AGENT — Combines short-term + long-term memory
# ═══════════════════════════════════════════════════════════════

def agent_respond(user_message: str, short_term_history: list, long_term_memory: dict) -> str:
    """Generate a response using both memory types."""

    memory_context = format_memory_for_prompt(long_term_memory)

    system_prompt = f"""You are a helpful personal AI assistant with memory.

{memory_context}

Instructions:
- Use what you remember about the user to personalize your responses
- Be warm and personal — use their name if you know it
- If you learn something new and important, acknowledge it
- Keep responses concise and helpful
"""

    messages = [{"role": "system", "content": system_prompt}]
    messages += short_term_history
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.7,
    )
    return response.choices[0].message.content


def main():
    print("=" * 60)
    print("🧠 Memory Agent — Phase 3, Project 2")
    print("=" * 60)

    # Load long-term memory
    memory = load_memory()
    memory["conversation_count"] = memory.get("conversation_count", 0) + 1

    # Welcome message
    if memory["user_profile"].get("name"):
        name = memory["user_profile"]["name"]
        count = memory["conversation_count"]
        print(f"\n👋 Welcome back, {name}! (Session #{count})")
    else:
        print("\n👋 Hello! I'm your memory-powered assistant.")
        print("   Tell me your name and I'll remember it next time!")

    print(f"\nMemory file: {MEMORY_FILE}")
    print("\nTry: 'My name is [name]', 'I work as a [job]', 'I like [thing]'")
    print("Then quit and restart — I'll remember you!")
    print("\nCommands: 'quit' to exit | 'show memory' to see what I know")
    print("=" * 60)

    short_term_history = []

    while True:
        user_input = input("\nYou: ").strip()
        if not user_input:
            continue

        if user_input.lower() in ["quit", "exit", "q"]:
            save_memory(memory)
            print("\n👋 Goodbye! I'll remember our conversation.")
            break

        if user_input.lower() == "show memory":
            print("\n" + format_memory_for_prompt(memory))
            continue

        if user_input.lower() == "clear memory":
            memory = {"user_profile": {}, "facts": [], "preferences": [],
                      "conversation_count": 0, "first_seen": datetime.now().isoformat(), "last_seen": None}
            print("🗑️  Memory cleared!")
            continue

        try:
            print("🤔 Thinking...", end="", flush=True)
            response = agent_respond(user_input, short_term_history, memory)
            print(" done")
            print(f"\n🤖 Agent: {response}")

            # Extract and save new memories
            extract_memories(user_input, response, memory)

            # Update short-term history
            short_term_history.append({"role": "user", "content": user_input})
            short_term_history.append({"role": "assistant", "content": response})

            # Keep last 8 exchanges in short-term memory
            if len(short_term_history) > 16:
                short_term_history = short_term_history[-16:]

        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Make sure 'ollama serve' is running in another terminal.")


if __name__ == "__main__":
    main()
