# Project 04 — Observability Dashboard
**Phase 6 · Production & Enterprise**

---

## What Observability Means for AI Systems

A running model is not enough. You need to know: Is it slow? Is it failing? How many tokens is it burning? Are users hitting errors? **Observability** is the practice of instrumenting your system so you can answer these questions in real time — without redeploying or guessing.

For AI platforms specifically, the stakes are high: LLM calls are slow (2–60s), expensive (token cost), and non-deterministic. A spike in P95 latency, a surge in errors, or a sudden drop in throughput can go unnoticed for minutes without proper monitoring. This project wires up a production-grade observability stack around the FastAPI AI platform.

---

## Architecture

```
Browser (you)
    |
    |  http://localhost:3000
    v
+-------------------+
|      Grafana      |  Reads time-series data, renders dashboards
+-------------------+
    |
    |  PromQL queries
    v
+-------------------+
|    Prometheus     |  Stores metrics, scrapes /metrics every 15s
+-------------------+
    |
    |  GET /metrics  (pull model — Prometheus comes to the API)
    v
+-------------------+
|   FastAPI API     |  Emits Prometheus metrics on every request
+-------------------+
    |
    |  POST /api/chat
    v
+-------------------+
|     Ollama        |  Runs the LLM locally (gemma3:4b)
+-------------------+
```

Key insight: **Prometheus pulls** metrics from the API on a schedule. The API does not push. This means the API stays simple — it just exposes a `/metrics` endpoint and Prometheus handles the rest.

---

## How to Run

**Prerequisites:** Docker Desktop running, Ollama running locally with `gemma3:4b` pulled.

```bash
# From this directory
docker compose up --build
```

Wait about 20–30 seconds for all services to start. Then open:

| Service    | URL                          | Notes                          |
|------------|------------------------------|--------------------------------|
| API docs   | http://localhost:8000/docs   | Swagger UI — try /chat here    |
| Raw metrics| http://localhost:8000/metrics| Prometheus text format         |
| Prometheus | http://localhost:9090        | Query metrics directly         |
| Grafana    | http://localhost:3000        | Dashboards — login below       |

Grafana credentials: **admin / admin123**

To stop:
```bash
docker compose down
```

To stop and remove stored metric data:
```bash
docker compose down -v
```

---

## Finding the Dashboard in Grafana

1. Open http://localhost:3000 in your browser.
2. Log in with **admin** / **admin123**.
3. In the left sidebar, click the **four-square grid icon** (Dashboards).
4. Click **Browse**.
5. Open the **AI Platform** folder.
6. Click **AI Platform Overview**.

The dashboard auto-refreshes every 15 seconds. Set the time range to **Last 30 minutes** (top-right) to see recent data.

---

## Metrics Reference

| Metric Name | What It Measures | Why It Matters |
|---|---|---|
| `ai_requests_total` | Count of LLM calls, labeled by model and status (success/error) | Tracks throughput and error rate |
| `ai_request_duration_seconds` | Histogram of how long each LLM call took | Reveals latency distribution; P95 catches slow outliers |
| `ai_tokens_estimated_total` | Word-count proxy for token output per model | Tracks throughput and cost proxy |
| `ai_errors_total` | Error count by type: timeout, ollama_unavailable, internal, stream_error | Pinpoints failure mode |
| `ai_active_requests` | Gauge of in-flight requests right now | Detects concurrency pile-ups |
| `ai_ollama_up` | 1 if Ollama API responds, 0 if not | Binary health signal for dependency |
| `http_requests_total` | Auto-instrumented count of all HTTP requests by endpoint and status code | Standard web metrics |
| `http_request_duration_seconds` | Auto-instrumented latency for all endpoints | Latency for non-LLM endpoints |

### Dashboard Panels Explained

| Panel | PromQL | Meaning |
|---|---|---|
| Request Rate | `rate(ai_requests_total[1m])` | Requests per second, 1-min rolling window |
| Error Rate % | errors / total * 100 | Turns red at 5% — actionable threshold |
| P95 Latency | `histogram_quantile(0.95, ...)` | The slowest 5% of requests — worst user experience |
| Active Requests | `ai_active_requests` | Live gauge, 0–10 scale |
| Ollama Status | `ai_ollama_up` | Green=UP, Red=DOWN |
| Duration Heatmap | Bucketed histogram | Shows where most requests land in latency space |
| Requests Over Time | Rate by status | Lets you see error spikes vs normal traffic |
| Tokens Over Time | `rate(ai_tokens_estimated_total[1m])` | Token throughput per model |

---

## Running the Load Test

The load test sends 30 requests with varied prompts, cycling through 10 different questions.

```bash
# Make sure the stack is running first
pip install requests   # if not already installed
python load_test.py
```

**Watch metrics change live:**

1. Open Grafana → AI Platform Overview dashboard.
2. Set time range to **Last 5 minutes**.
3. Run `python load_test.py` in a terminal.
4. Watch the Request Rate, Active Requests, and Tokens panels spike in real time.

The load test prints progress every 5 requests and a final summary with min/avg/P95/max latency and the error breakdown.

---

## How Prometheus Scraping Works

Prometheus uses a **pull model**, which is the opposite of most monitoring systems:

1. Your API exposes a `/metrics` endpoint that returns text in [Prometheus exposition format](https://prometheus.io/docs/instrumenting/exposition_formats/).
2. Prometheus reads `prometheus.yml` to know which targets to scrape (in this case, `api:8000`).
3. Every `scrape_interval` seconds (15s here), Prometheus sends `GET http://api:8000/metrics`.
4. It parses the response, stores the time-series data in its local TSDB (time-series database).
5. Grafana connects to Prometheus as a datasource and runs **PromQL** queries to fetch and visualize that data.

The pull model has advantages: targets don't need to know where Prometheus lives, and Prometheus can detect when a target goes down (missing scrapes = gap in data = alert).

---

## File Structure

```
project_04_observability/
├── api/
│   ├── main.py              # FastAPI app with Prometheus metrics
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Multi-stage build
├── prometheus/
│   └── prometheus.yml       # Scrape targets configuration
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/
│   │   │   └── prometheus.yml   # Auto-wires Prometheus datasource
│   │   └── dashboards/
│   │       └── dashboard.yml    # Tells Grafana where dashboard files live
│   └── dashboards/
│       └── ai_platform.json     # Pre-built dashboard (8 panels)
├── docker-compose.yml       # Orchestrates api + prometheus + grafana
├── load_test.py             # 30-request load generator
└── README.md                # This file
```

---

## Key Concepts Practiced

- **Prometheus metrics types**: Counter, Histogram, Gauge — when to use each
- **Labels**: Slicing metrics by model, status, error_type for richer queries
- **PromQL**: `rate()`, `histogram_quantile()`, `sum() by (label)`
- **Grafana provisioning**: Auto-loading datasources and dashboards via config files (no manual clicking)
- **Pull-based monitoring**: Prometheus scrapes the API, not the reverse
- **Docker networking**: Container-to-container DNS (`api`, `prometheus` as hostnames)
- **Production patterns**: Health checks, `unless-stopped` restart policy, named volumes for data persistence
