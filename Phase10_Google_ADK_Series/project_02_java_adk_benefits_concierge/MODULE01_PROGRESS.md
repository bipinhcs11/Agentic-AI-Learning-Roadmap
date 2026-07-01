# Module 01 Progress

Branch: `codex/phase10-module1-rung01a`

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

## Verification

```bash
cd Phase10_Google_ADK_Series/project_02_java_adk_benefits_concierge
mvn test
```

Result: 12 tests passed.

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

## Not Started Yet

- Rung 01C React renderer.
- Rung 01D AG-UI streaming.

Reason: the merged plan says to climb rungs only after the previous rung runs
and the next path is verified. Rung 01B now verifies the Java A2UI payload shape
and Dev UI server registration. A live model rendering check still requires
local Gemini or Vertex credentials, but the next code rung can consume the same
validated payload through a minimal React renderer.
