# Troubleshooting

This repo intentionally spans many project types. Start with the smallest local
check, then move outward.

## Ollama Is Not Responding

Symptoms:

```text
Connection refused
Error connecting to http://localhost:11434
```

Fix:

```bash
ollama serve
ollama list
```

If the model is missing:

```bash
ollama pull gemma3:4b
ollama pull nomic-embed-text
```

## Python Imports Fail

Make sure the repo virtual environment is active:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Some project folders have their own `requirements.txt`. Install those from the
project folder when the README says to.

## Docker Cannot Reach Ollama

On Docker Desktop for Mac, containers usually reach the host through:

```text
http://host.docker.internal:11434
```

Check the project README for the expected `OLLAMA_URL`.

## Tests Try To Call A Live Server

Several files named `test_*.py` are integration demo scripts from the learning
projects. They are meant to be run directly after starting a local service. The
CI workflow runs the offline Phase 9 capstone tests instead.

## Out Of Memory Or Very Slow Responses

- Use `gemma3:4b` or `qwen2.5:3b` first.
- Close other model servers or heavy apps.
- Avoid pulling large models until the small path works.
- Prefer the NumPy-based examples before adding vector databases or frameworks.

## Cloud Credentials Missing

Cloud examples are optional and scoped to the production phases. If a project
mentions AWS, Stripe, Slack, or GitHub credentials, create a local `.env` and do
not commit real secrets.
