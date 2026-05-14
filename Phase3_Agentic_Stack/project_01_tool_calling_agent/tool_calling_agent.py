# ═══════════════════════════════════════════════════════════════
# Project 01 — Tool-Calling Agent
# Phase 3 · Agentic AI Learning Roadmap
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   Builds an AI agent that can use tools (calculator, clock, etc.)
#   The agent decides which tool to use based on your question.
#
# HOW TO RUN:
#   1. ollama serve  (in a separate terminal)
#   2. source ~/Documents/my-ai-project/ai-env/bin/activate
#   3. python tool_calling_agent.py
# ═══════════════════════════════════════════════════════════════

import json
import math
import re
from datetime import datetime
from openai import OpenAI

# ── Connect to Ollama ────────────────────────────────────────────
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"  # Ollama doesn't need a real key
)

MODEL = "gemma3:4b"  # RAM-safe for Mac Mini M4

# ═══════════════════════════════════════════════════════════════
# STEP 1: Define Your Tools
# Each tool is a Python function + a description the AI reads
# ═══════════════════════════════════════════════════════════════

def calculator(expression: str) -> str:
    """Safely evaluate a math expression."""
    try:
        # Allow only safe math operations
        allowed = set("0123456789+-*/()., ")
        if not all(c in allowed for c in expression):
            return "Error: Only basic math allowed (+, -, *, /, parentheses)"
        result = eval(expression)  # safe here — restricted chars above
        return str(result)
    except Exception as e:
        return f"Error: {e}"


def get_current_time() -> str:
    """Return the current date and time."""
    now = datetime.now()
    return now.strftime("%A, %B %d, %Y at %I:%M:%S %p")


def word_counter(text: str) -> str:
    """Count the number of words in the given text."""
    words = text.split()
    chars = len(text)
    sentences = text.count('.') + text.count('!') + text.count('?')
    return f"{len(words)} words, {chars} characters, ~{max(1, sentences)} sentences"


def temperature_converter(value: float, from_unit: str, to_unit: str) -> str:
    """Convert temperature between Celsius, Fahrenheit, and Kelvin."""
    from_unit = from_unit.upper()[0]  # C, F, or K
    to_unit = to_unit.upper()[0]

    # Convert to Celsius first
    if from_unit == "F":
        celsius = (value - 32) * 5 / 9
    elif from_unit == "K":
        celsius = value - 273.15
    else:
        celsius = value

    # Convert Celsius to target
    if to_unit == "F":
        result = celsius * 9 / 5 + 32
        unit_name = "°F"
    elif to_unit == "K":
        result = celsius + 273.15
        unit_name = "K"
    else:
        result = celsius
        unit_name = "°C"

    return f"{value}{from_unit} = {result:.2f}{unit_name}"


# ── Tool registry: maps name → function ─────────────────────────
TOOLS = {
    "calculator": calculator,
    "get_current_time": get_current_time,
    "word_counter": word_counter,
    "temperature_converter": temperature_converter,
}

# ── Tool descriptions (what the AI reads to choose tools) ───────
TOOL_DESCRIPTIONS = """You have access to these tools. Use them when needed.

TOOLS:
1. calculator(expression) — evaluate math: e.g., calculator("2 * (3 + 4)")
2. get_current_time() — get the current date and time
3. word_counter(text) — count words in text: e.g., word_counter("Hello world foo")
4. temperature_converter(value, from_unit, to_unit) — convert temps: e.g., temperature_converter(100, "C", "F")

To use a tool, respond EXACTLY like this (JSON format):
{"tool": "calculator", "args": {"expression": "2+2"}}

If you don't need a tool, just answer normally.
Only call ONE tool per response.
"""

# ═══════════════════════════════════════════════════════════════
# STEP 2: The Agent Loop (ReAct: Reason → Act → Observe)
# ═══════════════════════════════════════════════════════════════

def parse_tool_call(response_text: str):
    """Try to extract a tool call from the model's response."""
    # Look for JSON-like tool call in the response
    match = re.search(r'\{[^{}]*"tool"[^{}]*\}', response_text, re.DOTALL)
    if match:
        try:
            tool_call = json.loads(match.group())
            return tool_call
        except json.JSONDecodeError:
            pass
    return None


def run_tool(tool_call: dict) -> str:
    """Execute the tool the model requested."""
    tool_name = tool_call.get("tool")
    args = tool_call.get("args", {})

    if tool_name not in TOOLS:
        return f"Error: Tool '{tool_name}' not found"

    func = TOOLS[tool_name]
    try:
        if args:
            result = func(**args)
        else:
            result = func()
        return str(result)
    except Exception as e:
        return f"Tool error: {e}"


def agent_respond(user_message: str, conversation_history: list) -> str:
    """
    Main agent loop:
    1. Ask the model what to do
    2. If it wants to use a tool → run it → ask model to summarize
    3. If no tool needed → return the answer
    """

    # Add system prompt with tool descriptions
    messages = [
        {"role": "system", "content": TOOL_DESCRIPTIONS}
    ] + conversation_history + [
        {"role": "user", "content": user_message}
    ]

    print("\n🤔 Thinking...", end="", flush=True)

    # Step 1: Ask the model
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.1,  # low temp for more reliable tool calls
    )
    first_response = response.choices[0].message.content
    print(" done")

    # Step 2: Check if model wants to use a tool
    tool_call = parse_tool_call(first_response)

    if tool_call:
        tool_name = tool_call.get("tool", "unknown")
        print(f"🔧 Using tool: {tool_name}")

        # Run the tool
        tool_result = run_tool(tool_call)
        print(f"✅ Tool result: {tool_result}")

        # Step 3: Ask model to give a final answer using the tool result
        messages_with_result = messages + [
            {"role": "assistant", "content": first_response},
            {"role": "user", "content": f"Tool result: {tool_result}\n\nNow give the user a clear, friendly answer using this result."}
        ]

        final_response = client.chat.completions.create(
            model=MODEL,
            messages=messages_with_result,
            temperature=0.3,
        )
        return final_response.choices[0].message.content
    else:
        # No tool needed — return direct answer
        return first_response


# ═══════════════════════════════════════════════════════════════
# STEP 3: Run the Chat Loop
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("🤖 Tool-Calling Agent — Phase 3, Project 1")
    print("=" * 60)
    print(f"Model: {MODEL} (local via Ollama)")
    print("\nAvailable tools: calculator, get_current_time,")
    print("                 word_counter, temperature_converter")
    print("\nTry asking:")
    print("  • What is 1234 * 5678?")
    print("  • What time is it?")
    print("  • How many words are in 'The quick brown fox jumps over the lazy dog'?")
    print("  • Convert 100 Celsius to Fahrenheit")
    print("\nType 'quit' to exit")
    print("=" * 60)

    conversation_history = []

    while True:
        user_input = input("\nYou: ").strip()

        if not user_input:
            continue
        if user_input.lower() in ["quit", "exit", "q"]:
            print("\n👋 Goodbye!")
            break

        try:
            response = agent_respond(user_input, conversation_history)
            print(f"\n🤖 Agent: {response}")

            # Save to conversation history
            conversation_history.append({"role": "user", "content": user_input})
            conversation_history.append({"role": "assistant", "content": response})

            # Keep history manageable (last 6 exchanges)
            if len(conversation_history) > 12:
                conversation_history = conversation_history[-12:]

        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Make sure 'ollama serve' is running in another terminal.")


if __name__ == "__main__":
    main()
