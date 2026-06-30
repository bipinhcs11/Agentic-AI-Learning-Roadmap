# Tutorial: Run Phase 10 Google ADK Contract Compliance

This tutorial walks through the executable Phase 10 demo: a Python Google ADK
orchestrator calls a Go compliance agent and a Java risk scoring agent through
A2A JSON-RPC `SendMessage`.

The live cockpit path is deterministic and does not require a Gemini API key.

## 1. Start The Services

Use Docker Compose when you want the fastest local startup:

```bash
cd Phase10_Google_ADK_Series
docker compose up --build
```

Then open:

```text
http://127.0.0.1:8000/live-compliance/
```

Manual startup uses three terminals.

Terminal 1, start Go:

```bash
cd Phase10_Google_ADK_Series/go-compliance-agent
go run cmd/server/main.go
```

Go exposes:

```text
http://localhost:8888/.well-known/agent.json
http://localhost:8888/
```

Terminal 2, start Java:

```bash
cd Phase10_Google_ADK_Series/java-risk-scoring-agent
mvn package
java -jar target/risk-scoring-agent-1.0.0.jar
```

Java exposes:

```text
http://localhost:9999/.well-known/agent.json
http://localhost:9999/
```

Terminal 3, start Python:

```bash
cd Phase10_Google_ADK_Series/python-extraction-agent
uv sync
uv run uvicorn app.fast_api_app:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/live-compliance/
```

## 2. Run The Happy Path

1. Select `standard-vendor-agreement.pdf`.
2. Keep A2A Simulator Mode on `Healthy`.
3. Click **Run Pipeline Audit**.
4. Confirm the Agent Exchange panel shows:
   - source: `python-extraction-agent`
   - Go target: `Security Compliance Validator`
   - method: `SendMessage`
   - JSON-RPC payload
   - passed Go verdict
5. Confirm the Java risk score panel shows the Financial Risk Scoring Engine
   result.
6. Open the generated compliance certificate artifact.

Expected result: the contract passes because value, term, insurance, liability,
renewal, and exit terms are inside the active policy thresholds. Java adds a
quantitative risk grade for the same extracted contract fields.

## 3. Run The Review Paths

Test the bundled failure cases:

| Contract | Expected result |
|---|---|
| `high-risk-liability-contract.pdf` | Review because unlimited liability is prohibited |
| `non-compliant-contract.pdf` | Review with multiple policy violations and a high Java risk score |

For `non-compliant-contract.pdf`, the UI should show review required with these
violation categories:

- value above `$500k`
- unlimited liability
- auto-renewal longer than 3 years
- insurance below `$1M`
- term longer than 5 years
- missing usable exit clause

## 4. Simulate A2A Failure

Use A2A Simulator Mode to test remote-agent failure behavior:

- `Healthy`: normal Go and Java service path.
- `Delayed`: waits before the Go call, bounded by the backend.
- `Crashed (503)`: simulates Go service failure and routes to manual review.

Expected crashed result: Python fails closed to `MANUAL_REVIEW` and the
certificate explains that manual legal review is required. Java risk scoring is
best-effort and does not override the Go fail-close path.

## 5. What The Browser Sends

The UI posts contract text and policy settings to:

```text
POST /api/compliance/upload
```

Important form fields:

| Field | Purpose |
|---|---|
| `file` | Text contract fixture, including `.pdf`-named text samples |
| `custom_policies` | Active policy values sent to Go |
| `simulated_latency` | Bounded delay for simulator testing |
| `simulated_server_state` | `normal` or `crashed` |

The browser does not call Go or Java directly. Python owns those A2A handoffs.

## 6. What Python Sends

Python builds A2A data payloads in
`python-extraction-agent/app/fast_api_app.py`.

Go compliance receives:

```text
schema_version: contract-compliance.a2a.v1
contract: extracted contract fields
policy: active policy thresholds
```

Java risk scoring receives:

```text
schema_version: contract-risk-scoring.a2a.v1
contract: extracted contract fields
```

Both calls go through ADK `RemoteA2aAgent`.

## 7. Test The Demo

Run Python tests:

```bash
cd Phase10_Google_ADK_Series/python-extraction-agent
uv run pytest tests/unit -q
```

Run Go tests:

```bash
cd Phase10_Google_ADK_Series/go-compliance-agent
go test ./...
```

Run Java tests:

```bash
cd Phase10_Google_ADK_Series/java-risk-scoring-agent
mvn test
```

Smoke-test agent cards:

```bash
curl http://127.0.0.1:8888/.well-known/agent.json
curl http://127.0.0.1:9999/.well-known/agent.json
```

## 8. Key Code To Read

| File | Why it matters |
|---|---|
| `python-extraction-agent/app/fast_api_app.py` | API routes, request validation, ADK handoffs, simulator handling |
| `python-extraction-agent/app/agent.py` | Full reference ADK `SequentialAgent` shape |
| `python-extraction-agent/app/tools.py` | Deterministic contract extraction |
| `go-compliance-agent/internal/handler/task_handler.go` | Go A2A JSON-RPC handler |
| `go-compliance-agent/internal/compliance/checker.go` | Go deterministic policy verdict |
| `java-risk-scoring-agent/src/main/java/com/compliance/riskscoring/handler/JsonRpcHandler.java` | Java A2A JSON-RPC handler |
| `java-risk-scoring-agent/src/main/java/com/compliance/riskscoring/scoring/RiskCalculator.java` | Java risk scoring rules |
