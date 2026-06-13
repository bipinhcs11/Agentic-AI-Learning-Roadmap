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

## Before Opening A Pull Request

1. Keep the existing folder structure unless there is a clear reason to change it.
2. Prefer small, focused changes over broad rewrites.
3. Keep examples local-first with Ollama unless a phase explicitly covers cloud.
4. Do not add PyTorch, sentence-transformers, or heavyweight ML dependencies to the
   shared install path.
5. Avoid real financial, payroll, HR, HSA, 401(k), billing, or customer data.

## Local Checks

Use the project virtual environment when possible:

```bash
source ~/Documents/my-ai-project/ai-env/bin/activate
python -m pytest -q
```

Some projects require local services such as Ollama, Redis, or Docker. If a check
needs a service or credentials, mention that clearly in the pull request.

## Community Notes

Questions, roadmap suggestions, and learning progress updates are better suited
for GitHub Discussions. Bugs and broken instructions are better as Issues.
