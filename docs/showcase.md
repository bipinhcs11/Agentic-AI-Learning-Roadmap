# Showcase

Use these demos when you want to share progress or verify the most complete
systems in the roadmap.

## Demo 1: First RAG From Scratch

```bash
ollama serve
ollama pull gemma3:4b
ollama pull nomic-embed-text
python Phase2_RAG_Systems/project_01_first_rag/rag_from_scratch.py
```

What to capture:

- Terminal showing chunking and embeddings
- First query, top match, and grounded answer
- One custom interactive question

## Demo 2: DocuMind Capstone

```bash
cd Phase6_Production_Enterprise/project_06_capstone_product
docker compose up --build
python demo/seed_data.py
```

Open `http://localhost` and log in with `admin / admin123`.

What to capture:

- Login screen
- Uploaded documents
- Chat answer with citations
- Admin dashboard

## Demo 3: Enterprise Assistant Hub

```bash
cd Phase9_Dynamic_Agentic_RAG_MCP/capstone_enterprise_assistant_hub
pip install -r requirements.txt
ollama serve
ollama pull qwen2.5:3b
ollama pull nomic-embed-text

AI_PROVIDER=ollama python hub.py --tenant acme \
  "I contribute 6%. Am I getting the full match, and what is the 2026 employee primary contribution limit?"
```

What to capture:

- Route decision
- Tools used
- Documents cited
- Provider/model metadata

## Demo 4: Google ADK Contract Compliance Team

```bash
cd Phase10_Google_ADK_Series
docker compose up --build
```

Open `http://127.0.0.1:8000/live-compliance/`.

What to capture:

- The live cockpit selecting a fictional contract
- Python ADK handoff to the Go compliance agent
- Java professional risk scoring response
- Generated legal parameter sheet and compliance certificate

## Demo 5: Enterprise AI Access Gateway

```bash
cd Phase12_Enterprise_AI_Identity_Security/module_10_enterprise_ai_access_gateway
cp .env.example .env
docker compose up --build
./demo/seed_agents.sh
```

What to capture:

- Keycloak login and the fictional user's delegable scopes
- Separate Finance and Email agent registrations
- OPA allow decision for a tenant-matched task
- successful scoped MCP tool call
- cross-tenant, wrong-tool, and revoked-task denials
- correlated trace in Jaeger or Langfuse

All displayed identities and records must remain fictional.

## Asset Backlog

When real recordings are available, add them under `assets/` and link them from
the root README:

```text
assets/
  roadmap-overview.svg
  documind-demo.gif
  phase9-mcp-demo.gif
  phase10-google-adk-demo.gif
  phase12-enterprise-ai-iam-demo.gif
  architecture-documind.png
  architecture-mcp-hub.png
```

Do not add placeholder screenshots. The showcase should reflect a working local
run.
