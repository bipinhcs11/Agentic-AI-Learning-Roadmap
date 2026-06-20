# AGENTS.md

## Project Purpose

This repository is a local-first Agentic AI learning roadmap with hands-on
projects covering RAG, agents, multi-agent systems, MCP, production deployment,
and integrations.

## Contribution Rules

- Keep examples local-first unless the phase explicitly uses cloud services.
- Prefer small, focused changes that preserve the existing phase structure.
- Avoid adding heavyweight dependencies to the root `requirements.txt`.
- Do not use real financial, HR, payroll, billing, benefits, or customer data.
- Add or update README instructions whenever code behavior changes.
- Include expected output for runnable examples when practical.
- Keep mock enterprise examples clearly labeled as fictional and educational.

## Testing

Run the focused offline checks when changing shared code or Phase 9 capstone code:

```bash
python -m pytest -q Phase9_Dynamic_Agentic_RAG_MCP/capstone_enterprise_assistant_hub/tests
```

Some projects require Ollama, Docker, Redis, or cloud credentials. Document those
requirements clearly in the relevant project README and pull request.
