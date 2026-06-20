# Agent Path

Use this path if your main goal is tool use, planning, memory, multi-agent
coordination, or agent APIs.

## Recommended Order

| Step | Folder | Skill |
|---:|---|---|
| 1 | `Phase3_Agentic_Stack/project_01_tool_calling_agent/` | Tool-calling and ReAct-style behavior |
| 2 | `Phase3_Agentic_Stack/project_02_memory_agent/` | Short-term and long-term memory concepts |
| 3 | `Phase3_Agentic_Stack/project_04_multi_tool_agent/` | Multiple tools behind one agent |
| 4 | `Phase3_Agentic_Stack/project_06_agent_api_server/` | Package an agent as a FastAPI service |
| 5 | `Phase5_Multi_Agent_Systems/` | Add supervisor, crew, bus, and review-loop patterns |
| 6 | `Phase7_Advanced_AI_Patterns/project_05_self_improving_agent/` | Practice reflection and iterative improvement |

## Design Questions

- What tool surface does the model receive?
- What state is passed between steps?
- How are failures handled?
- Which actions require human approval?
- What is logged for debugging?

## Good Portfolio Outcome

Ship an agent API that uses at least two tools, has a visible trace of decisions,
and includes a README with expected output.
