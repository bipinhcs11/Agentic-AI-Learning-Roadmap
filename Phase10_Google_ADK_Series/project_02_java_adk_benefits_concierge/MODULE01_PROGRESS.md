# Module 01 Progress

Branch: `codex/phase10-module1-rung01c`

## Completed

- Phase A: lightweight skill design in `MODULE01_SKILL_DESIGN.md`.
- Rung 01A: Java ADK text agent using `LlmAgent`.
- Rung 01A deterministic tools:
  - benefits knowledge lookup,
  - 401(k)/HSA projection math,
  - non-executable election drafting,
  - request guardrail screening.
- Rung 01A eval fixtures in `src/test/resources/evals/rung01a_eval_cases.json`.
- Rung 01B verification scaffold:
  - trusted A2UI-shaped `Card`, `Table`, and `Text` payloads,
  - server-side validation,
  - rejection of untrusted components and executable props,
  - A2UI `DataPart`-style wrapper with `metadata.mimeType = application/json+a2ui`,
  - ADK Dev UI launcher,
  - offline A2UI fixture exporter.
- Rung 01C React renderer:
  - Vite/React app scoped to `react-a2ui-renderer/`,
  - checked-in offline A2UI projection fixture,
  - client-side trusted component catalog validation,
  - local rendering for `Card`, `Table`, and `Text`.
- Rung 01D AG-UI streaming:
  - local Java SSE server at `BenefitsAgUiStreamServerApp`,
  - AG-UI-shaped lifecycle, text, tool-call, state, and finish events,
  - streamed `STATE_SNAPSHOT` carrying the trusted A2UI payload,
  - React `Start stream` path that renders the live state update.

## Verification

```bash
cd Phase10_Google_ADK_Series/project_02_java_adk_benefits_concierge
mvn test
```

Result: 15 tests passed.

```bash
mvn -q exec:java
```

Result: Java ADK agent object is created successfully.

```bash
mvn -q exec:java -Dexec.mainClass=com.benefits.adk.ExportA2uiFixtureApp
```

Result: A2UI `DataPart`-style fixture is exported with
`metadata.mimeType = application/json+a2ui`.

```bash
mvn -q exec:java -Dexec.mainClass=com.benefits.adk.BenefitsConciergeDevUiApp
curl -sS -I http://localhost:8080
curl -sS http://localhost:8080/list-apps
```

Result: ADK Dev UI starts on port 8080, `/` redirects to `/dev-ui`, and
`/list-apps` returns `["java_adk_benefits_concierge"]`.

```bash
cd react-a2ui-renderer
npm install
npm run build
npm run dev -- --port 5174
```

Result: Vite builds successfully, the renderer loads at
`http://127.0.0.1:5174/`, the trusted projection card renders five rows, and
browser console errors are clean.

```bash
mvn -q exec:java -Dexec.mainClass=com.benefits.adk.BenefitsAgUiStreamServerApp
curl -sS -N http://127.0.0.1:8091/ag-ui/runs/benefits-projection
```

Result: the Java server emits AG-UI-shaped SSE frames including `RUN_STARTED`,
`TEXT_MESSAGE_CONTENT`, `TOOL_CALL_START`, `STATE_SNAPSHOT`, and `RUN_FINISHED`.

Browser result: `Start stream` reaches `finished`, renders the trusted five-row
A2UI projection card, has no validation alerts, and reports no console errors
on desktop or a 390px mobile viewport.

## Not Started Yet

- Module 02 UCP transaction lane.
- Module 03 A2A specialist agents.

Reason: the merged plan says to climb rungs only after the previous rung runs
and the next path is verified. Rung 01D now streams live browser state over a
local AG-UI-shaped SSE bridge while preserving the same Java-validated A2UI
payload shape. A live model check still requires local Gemini or Vertex
credentials, but the streaming browser demo can run offline from deterministic
Java tools.
