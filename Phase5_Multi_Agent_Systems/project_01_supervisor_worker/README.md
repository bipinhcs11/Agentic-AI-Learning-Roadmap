# Project 01 — Supervisor-Worker Multi-Agent System
**Phase 5 · Multi-Agent Systems**

## What You Build
A 4-agent pipeline coordinated by LangGraph:

```
User Request
    ↓
[SUPERVISOR] — reads state, decides who's next
    ↓
[RESEARCHER] — gathers detailed information
    ↓
[SUPERVISOR] — routes to next worker
    ↓
[SUMMARIZER] — condenses research into key points
    ↓
[SUPERVISOR] — routes to next worker
    ↓
[FORMATTER]  — creates polished briefing document
    ↓
[SUPERVISOR] — sees all work done → FINISH
    ↓
Final Briefing Output
```

## Key Concepts Learned
| Concept | What It Is |
|---|---|
| `StateGraph` | LangGraph's directed graph of agents |
| `TypedDict` State | Shared "whiteboard" all agents read/write |
| `add_messages` reducer | Appends to message history (never overwrites) |
| Conditional Edges | Supervisor's routing decisions in graph form |
| Worker → Supervisor loop | How agents hand off work |

## How to Run
```bash
# Terminal 1 — keep Ollama running
ollama serve

# Terminal 2 — run the project
source ~/Documents/my-ai-project/ai-env/bin/activate
cd Phase5_Multi_Agent_Systems/project_01_supervisor_worker
python supervisor_worker.py
```

## Tech Stack
- **LangGraph 1.1.x** — graph orchestration
- **LangChain Core** — message types
- **langchain-openai** — ChatOpenAI client
- **Ollama (local)** — runs gemma3:4b

## What's Different From Phase 4?
In Phase 4 you built a **single agent with tools** (ReAct loop).  
In Phase 5 you build **multiple agents coordinating** (supervisor pattern).

The key shift: instead of one agent deciding what to do next, you have a **dedicated supervisor** whose only job is routing. Workers are laser-focused specialists.
