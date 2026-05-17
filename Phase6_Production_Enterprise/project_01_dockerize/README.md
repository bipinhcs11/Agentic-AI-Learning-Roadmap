# Project 01 — Dockerize Everything
**Phase 6 · Production & Enterprise**

## What You Build
Three containers wired together with Docker Compose:

```
Your Browser
     ↓
 nginx :80          ← single entry point
  ├── /api/* → api container :8000   (FastAPI)
  └── /*     → ui  container :8501   (Streamlit)
                          ↓
               host.docker.internal:11434  (Ollama on your Mac)
```

## File Structure
```
project_01_dockerize/
├── docker-compose.yml      ← wires all 3 services together
├── .env.example            ← copy to .env for config
├── .dockerignore
├── api/
│   ├── Dockerfile          ← multi-stage build, non-root user
│   ├── main.py             ← FastAPI app
│   └── requirements.txt
├── ui/
│   ├── Dockerfile
│   ├── app.py              ← Streamlit chat UI
│   └── requirements.txt
└── nginx/
    └── nginx.conf          ← reverse proxy config
```

## How to Run

```bash
# 1. Start Ollama on your Mac (must be running BEFORE docker compose)
ollama serve

# 2. Build and start all containers
cd Phase6_Production_Enterprise/project_01_dockerize
docker compose up --build

# 3. Open your browser
open http://localhost          # Chat UI (via nginx)
open http://localhost:8000/docs  # FastAPI Swagger docs
```

## Key Docker Concepts Learned

| Concept | Where Used |
|---|---|
| Multi-stage build | api/Dockerfile — keeps image small |
| Non-root user | Both Dockerfiles — security best practice |
| HEALTHCHECK | API waits for Ollama before accepting traffic |
| `depends_on: condition: service_healthy` | UI waits for API to be ready |
| Container networking | Services talk by name: `http://api:8000` |
| `host.docker.internal` | How containers reach Ollama on your Mac |
| Reverse proxy | Nginx routes /api/* and /* to right container |

## Useful Commands

```bash
docker compose up --build      # build images and start
docker compose up -d           # start in background
docker compose down            # stop all containers
docker compose logs -f api     # stream API logs
docker compose logs -f ui      # stream UI logs
docker ps                      # see running containers
docker images                  # see built images
docker compose restart api     # restart one service
```

## What's Different from Phase 4?
- Phase 4: `python inference_server.py` — one process, local only
- Phase 6: Three containers, reproducible on any machine, `docker compose up` = done
