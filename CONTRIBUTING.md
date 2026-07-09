# Contributing

Thanks for taking a look at the Agentic AI Learning Roadmap. This repo is first
a hands-on learning project, and second a community resource. Contributions are
welcome when they make the path clearer, easier to run, or more useful for other
builders.

## Good Contributions

- Fix broken setup steps, commands, imports, or dependency notes.
- Improve README clarity without changing the phase structure.
- Add focused tests for existing projects.
- Add comments where a beginner would otherwise get lost.
- Suggest project ideas through GitHub Discussions before adding large modules.

## Good First Contributions

- Test one project on Linux or Windows and report setup differences.
- Add expected output to a project README.
- Add troubleshooting notes for common Ollama, Docker, or Python errors.
- Improve beginner-facing comments in Phase 1, Phase 2, or Phase 3 projects.
- Add missing tests for utility functions that do not require live services.
- Create a Mermaid architecture diagram for one phase or capstone.
- Verify a project README command from a fresh virtual environment.

## Before Opening A Pull Request

1. Keep the existing folder structure unless there is a clear reason to change it.
2. Prefer small, focused changes over broad rewrites.
3. Keep examples local-first with Ollama unless a phase explicitly covers cloud.
4. Do not add PyTorch, sentence-transformers, or heavyweight ML dependencies to the
   shared install path.
5. Avoid real professional, record system, HR, savings account, primary contribution, billing, or customer data.

## Local Checks

Use the project virtual environment when possible:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m pytest -q Phase9_Dynamic_Agentic_RAG_MCP/capstone_enterprise_assistant_hub/tests
```

Some project scripts are integration demos, not pytest suites. They may require
local services such as Ollama, Redis, Docker, a running FastAPI server, or cloud
credentials. If a check needs a service or credentials, mention that clearly in
the pull request.

## Pull Request Checklist

- The change is limited to one project, doc area, or setup concern.
- New or changed commands have been run locally when possible.
- README instructions and expected output are updated for behavior changes.
- Mock data remains fictional and safe for a public repository.
- Any skipped checks or external service requirements are called out in the PR.

## Community Notes

Questions, roadmap suggestions, and learning progress updates are better suited
for GitHub Discussions. Bugs and broken instructions are better as Issues.
