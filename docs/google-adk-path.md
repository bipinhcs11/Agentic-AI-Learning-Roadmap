# Google ADK Path

Use this path if you want to learn Google Agent Development Kit patterns,
Agent-to-Agent handoffs, and local cross-language agent services.

## Recommended Order

| Step | Folder | Skill |
|---:|---|---|
| 1 | `Phase3_Agentic_Stack/project_01_tool_calling_agent/` | Learn tool-calling basics before adding a framework |
| 2 | `Phase5_Multi_Agent_Systems/` | Practice handoffs, supervision, and agent boundaries |
| 3 | `Phase10_Google_ADK_Series/` | Run a Python ADK coordinator with Go and Java A2A services |

## Phase 10 Focus

- Keep the live demo local-first and deterministic where possible.
- Use ADK for orchestration and A2A remote-agent handoffs.
- Keep Go and Java services as auditable policy/scoring agents, not LLM agents.
- Use fictional contract examples only.

## Offline Checks

```bash
cd Phase10_Google_ADK_Series/python-extraction-agent
uv sync
uv run pytest tests/unit -q

cd ../java-risk-scoring-agent
mvn test
```

Run Go tests with `go test ./...` from `Phase10_Google_ADK_Series/go-compliance-agent`
when Go is installed.
