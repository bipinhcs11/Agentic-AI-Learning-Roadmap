# ═══════════════════════════════════════════════════════════════
# Project 05 — Custom Agent Framework (Mini LangChain)
# Phase 4 · Agentic AI Learning Roadmap
# ═══════════════════════════════════════════════════════════════
#
# WHAT THIS DOES:
#   Builds a mini agent framework from scratch.
#   After this, you'll understand how LangChain works internally!
#
# KEY CONCEPTS:
#   - Tool registry (decorator pattern)
#   - ReAct loop (Reason → Act → Observe)
#   - Agent memory
#   - Task planning
#
# HOW TO RUN:
#   1. ollama serve
#   2. source ~/Documents/my-ai-project/ai-env/bin/activate
#   3. python custom_agent_framework.py
# ═══════════════════════════════════════════════════════════════

import json
import re
import os
import math
from datetime import datetime
from dataclasses import dataclass, field
from typing import Callable, Any, Optional
from openai import OpenAI


# ═══════════════════════════════════════════════════════════════
# COMPONENT 1: TOOL REGISTRY
# This is how LangChain's @tool decorator works!
# ═══════════════════════════════════════════════════════════════

class ToolRegistry:
    """Stores all available tools and their descriptions."""

    def __init__(self):
        self._tools: dict[str, dict] = {}

    def register(self, name: str, func: Callable, description: str, parameters: dict = None):
        """Register a tool."""
        self._tools[name] = {
            "name": name,
            "func": func,
            "description": description,
            "parameters": parameters or {},
        }

    def tool(self, description: str, parameters: dict = None):
        """Decorator to register a function as a tool."""
        def decorator(func: Callable):
            self.register(func.__name__, func, description, parameters)
            return func
        return decorator

    def get_tool(self, name: str) -> Optional[dict]:
        return self._tools.get(name)

    def list_tools(self) -> str:
        """Format tool list for the LLM prompt."""
        lines = ["AVAILABLE TOOLS:"]
        for name, info in self._tools.items():
            params = ", ".join(
                f"{k}: {v}" for k, v in info.get("parameters", {}).items()
            )
            lines.append(f"  {name}({params}) — {info['description']}")
        return "\n".join(lines)

    def call(self, name: str, **kwargs) -> str:
        """Execute a tool by name."""
        tool = self._tools.get(name)
        if not tool:
            return f"Error: No tool named '{name}'"
        try:
            result = tool["func"](**kwargs)
            return str(result)
        except Exception as e:
            return f"Tool error: {e}"

    @property
    def names(self) -> list:
        return list(self._tools.keys())


# ═══════════════════════════════════════════════════════════════
# COMPONENT 2: AGENT MEMORY
# Stores observations, actions, and conversation history
# ═══════════════════════════════════════════════════════════════

@dataclass
class Observation:
    step: int
    thought: str
    action: str
    action_input: dict
    result: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class AgentMemory:
    """Stores the agent's working memory for one task."""

    def __init__(self, max_history: int = 10):
        self.observations: list[Observation] = []
        self.conversation: list[dict] = []
        self.max_history = max_history

    def add_observation(self, step: int, thought: str, action: str, action_input: dict, result: str):
        obs = Observation(step, thought, action, action_input, result)
        self.observations.append(obs)

    def add_message(self, role: str, content: str):
        self.conversation.append({"role": role, "content": content})
        if len(self.conversation) > self.max_history * 2:
            self.conversation = self.conversation[-(self.max_history * 2):]

    def get_scratchpad(self) -> str:
        """Format observations as a scratchpad for the LLM."""
        if not self.observations:
            return "(No steps taken yet)"
        lines = []
        for obs in self.observations[-5:]:  # last 5 steps
            lines.append(f"Step {obs.step}:")
            lines.append(f"  Thought: {obs.thought}")
            lines.append(f"  Action: {obs.action}({json.dumps(obs.action_input)})")
            lines.append(f"  Result: {obs.result}")
        return "\n".join(lines)

    def reset(self):
        self.observations = []


# ═══════════════════════════════════════════════════════════════
# COMPONENT 3: PLANNER
# Breaks big tasks into smaller steps
# ═══════════════════════════════════════════════════════════════

class Planner:
    """Plans multi-step tasks before execution."""

    def __init__(self, llm_client, model: str):
        self.llm = llm_client
        self.model = model

    def create_plan(self, task: str, available_tools: str) -> list[str]:
        """Break a complex task into numbered steps."""
        prompt = f"""Break this task into 2-4 clear steps.
Be specific. Use the available tools where appropriate.

Task: {task}

{available_tools}

Return ONLY a numbered list, one step per line. No extra text.
Example:
1. Use calculator to compute X
2. Save the result with save_note
3. Answer the user"""

        resp = self.llm.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        text = resp.choices[0].message.content
        steps = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                step = re.sub(r'^[\d\.\-\s]+', '', line).strip()
                if step:
                    steps.append(step)
        return steps if steps else [task]


# ═══════════════════════════════════════════════════════════════
# COMPONENT 4: REACT AGENT
# The core agent loop: Think → Act → Observe → Repeat
# ═══════════════════════════════════════════════════════════════

REACT_PROMPT = """You are an AI agent solving a task step by step.

{tool_list}

INSTRUCTIONS:
- Think about what to do next
- If you need a tool, output EXACTLY this JSON:
  {{"thought": "why I'm using this tool", "action": "tool_name", "action_input": {{"param": "value"}}}}
- If you have the final answer, output EXACTLY this:
  {{"thought": "I have everything I need", "action": "FINAL_ANSWER", "action_input": {{"answer": "your answer here"}}}}

CURRENT TASK: {task}

SCRATCHPAD (steps taken so far):
{scratchpad}

What should I do next? (respond with JSON only)"""


class ReActAgent:
    """
    The main agent — implements the ReAct loop.
    Reason → Act → Observe → Repeat until done.
    """

    def __init__(self, llm_client, model: str, tools: ToolRegistry, max_steps: int = 8):
        self.llm = llm_client
        self.model = model
        self.tools = tools
        self.max_steps = max_steps
        self.memory = AgentMemory()
        self.planner = Planner(llm_client, model)

    def _parse_action(self, response: str) -> Optional[dict]:
        """Extract JSON action from model response."""
        # Try to find JSON block
        match = re.search(r'\{.*?\}', response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return None

    def run(self, task: str, verbose: bool = True) -> str:
        """Run the agent on a task."""
        self.memory.reset()

        if verbose:
            print(f"\n{'='*55}")
            print(f"🤖 Agent starting task: {task}")
            print('='*55)

        for step in range(1, self.max_steps + 1):
            if verbose:
                print(f"\n📍 Step {step}/{self.max_steps}")

            # Build prompt
            prompt = REACT_PROMPT.format(
                tool_list=self.tools.list_tools(),
                task=task,
                scratchpad=self.memory.get_scratchpad()
            )

            # Ask the LLM
            resp = self.llm.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            response_text = resp.choices[0].message.content

            if verbose:
                print(f"  Model: {response_text[:200]}...")

            # Parse the action
            action_data = self._parse_action(response_text)

            if not action_data:
                # Model didn't follow format — treat as final answer
                self.memory.add_observation(step, "couldn't parse", "FINAL_ANSWER", {}, response_text)
                return response_text

            thought = action_data.get("thought", "")
            action = action_data.get("action", "")
            action_input = action_data.get("action_input", {})

            if verbose:
                print(f"  💭 Thought: {thought}")
                print(f"  🔧 Action: {action}({action_input})")

            # FINAL ANSWER
            if action == "FINAL_ANSWER":
                answer = action_input.get("answer", str(action_input))
                if verbose:
                    print(f"\n✅ Final Answer: {answer}")
                self.memory.add_observation(step, thought, action, action_input, answer)
                return answer

            # TOOL CALL
            if action in self.tools.names:
                result = self.tools.call(action, **action_input)
                if verbose:
                    print(f"  📊 Result: {result}")
                self.memory.add_observation(step, thought, action, action_input, result)
            else:
                result = f"Unknown action: {action}. Available: {', '.join(self.tools.names + ['FINAL_ANSWER'])}"
                if verbose:
                    print(f"  ❌ {result}")
                self.memory.add_observation(step, thought, action, action_input, result)

        # Max steps reached
        return "I wasn't able to complete this task within the step limit. Please try a simpler request."


# ═══════════════════════════════════════════════════════════════
# TOOL SETUP — Register tools using our custom framework
# ═══════════════════════════════════════════════════════════════

registry = ToolRegistry()

@registry.tool("Calculate a math expression", {"expression": "string like '2 * 3'"})
def calculator(expression: str) -> str:
    try:
        allowed = set("0123456789+-*/.() ")
        if not all(c in allowed for c in expression):
            return "Error: invalid chars"
        return str(eval(expression))
    except Exception as e:
        return f"Error: {e}"


@registry.tool("Get the current date and time", {})
def get_time() -> str:
    return datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")


@registry.tool("Save a note to file", {"text": "the note to save"})
def save_note(text: str) -> str:
    notes_file = os.path.join(os.path.dirname(__file__), "agent_notes.txt")
    with open(notes_file, "a") as f:
        f.write(f"[{datetime.now().strftime('%H:%M')}] {text}\n")
    return f"Saved: {text}"


@registry.tool("Read all saved notes", {})
def read_notes() -> str:
    notes_file = os.path.join(os.path.dirname(__file__), "agent_notes.txt")
    if not os.path.exists(notes_file):
        return "No notes saved yet."
    with open(notes_file) as f:
        return f.read().strip() or "Notes file is empty."


@registry.tool("Convert Celsius to Fahrenheit", {"celsius": "temperature in Celsius"})
def celsius_to_fahrenheit(celsius: float) -> str:
    f = float(celsius) * 9/5 + 32
    return f"{celsius}°C = {f:.1f}°F"


@registry.tool("Count words in text", {"text": "the text to count"})
def count_words(text: str) -> str:
    return f"{len(text.split())} words"


# ═══════════════════════════════════════════════════════════════
# MAIN — Run the agent
# ═══════════════════════════════════════════════════════════════

def main():
    llm = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    agent = ReActAgent(llm, "gemma3:4b", registry, max_steps=6)

    print("=" * 55)
    print("🧩 Custom Agent Framework — Phase 4, Project 5")
    print("=" * 55)
    print("Tools:", ", ".join(registry.names))
    print("\nThis is YOUR mini LangChain!")
    print("Watch the ReAct loop: Think → Act → Observe → Repeat")
    print("\nTry multi-step tasks:")
    print("  • What is 15% of 3200, and save it as a note")
    print("  • What is 100 Celsius in Fahrenheit?")
    print("  • What time is it? Save it as a note.")
    print("  • Read my notes and summarize them")
    print("\nType 'quit' to exit")
    print("=" * 55)

    while True:
        try:
            task = input("\n🎯 Task: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Goodbye!")
            break

        if not task:
            continue
        if task.lower() in ["quit", "exit", "q"]:
            print("👋 Goodbye!")
            break

        try:
            answer = agent.run(task, verbose=True)
            print(f"\n🏁 RESULT: {answer}")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Make sure 'ollama serve' is running.")


if __name__ == "__main__":
    main()
