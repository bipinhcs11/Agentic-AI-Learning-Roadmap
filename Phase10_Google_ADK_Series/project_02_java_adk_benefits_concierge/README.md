# Project 02 - Java ADK Benefits Concierge

Module 01, Rung 01A from `PHASE10_PLAN_MERGED_for_review.md`.

This is a Java-first Google ADK text agent for a fictional 401(k)/HSA benefits
concierge. It reuses the familiar Phase 9 benefits domain, but the lesson is ADK
orchestration: a Java `LlmAgent` selects retrieval, projection, draft, and
guardrail tools.

All examples are fictional and educational. Do not use real financial, HR,
payroll, billing, benefits, customer, or account data.

## What Rung 01A Includes

- Java ADK root agent with Vertex Gemini model configuration.
- Deterministic 401(k)/HSA projection tool.
- Local benefits knowledge retriever that stands in for managed Agent Search
  during offline development.
- Guardrails for real data, transactions, and individualized legal/tax/
  investment advice.
- Non-executable election draft tool.
- Rung 01B verification scaffold for trusted A2UI-shaped projection payloads.
- Offline JUnit coverage and eval fixtures.

## What Is Deferred

- Built-in ADK web UI rendering of A2UI payloads: Rung 01B manual verification.
- React rendering: Rung 01C.
- AG-UI streaming: Rung 01D.
- UCP transaction lane: Module 02.
- A2A specialist agents: Module 03.

## Run Offline Checks

```bash
cd Phase10_Google_ADK_Series/project_02_java_adk_benefits_concierge
mvn test
```

Expected output:

```text
BUILD SUCCESS
Tests run: 13, Failures: 0, Errors: 0, Skipped: 0
```

## Create the Agent Object

```bash
cd Phase10_Google_ADK_Series/project_02_java_adk_benefits_concierge
mvn -q exec:java
```

Expected output:

```text
Created Java ADK agent: java_adk_benefits_concierge
Model: gemini-2.0-flash
Rung 01A is text-only. Run it in ADK Dev UI with Gemini credentials configured.
```

## Run ADK Dev UI

```bash
cd Phase10_Google_ADK_Series/project_02_java_adk_benefits_concierge
mvn -q exec:java -Dexec.mainClass=com.benefits.adk.BenefitsConciergeDevUiApp
```

Open:

```text
http://localhost:8080
```

Prompt to verify the Rung 01B path:

```text
Build an A2UI-style projection card for salary 100000, 401k 6%, HSA 4400,
self-only coverage, and 24% marginal tax rate.
```

Expected behavior:

- the agent calls `buildProjectionA2uiCard`,
- the tool response has `metadata.mimeType` set to `application/json+a2ui`,
- the payload validates against the trusted `Card`/`Table`/`Text` catalog,
- no real payroll/account action is claimed.

You need local Gemini or Vertex credentials for a live model response.
Verified offline: the Dev UI server starts on port 8080 and `/list-apps`
returns `["java_adk_benefits_concierge"]`.

## Export A2UI Fixture Offline

This command does not call Gemini:

```bash
mvn -q exec:java -Dexec.mainClass=com.benefits.adk.ExportA2uiFixtureApp
```

Expected shape:

```json
{
  "data": {
    "schemaVersion": "a2ui.phase10.rung01b.v1",
    "root": {
      "type": "Card"
    }
  },
  "metadata": {
    "mimeType": "application/json+a2ui"
  }
}
```

## Gemini / Vertex Runtime Notes

The Java ADK agent uses `com.google.adk:google-adk` and `google-adk-dev`
version `1.5.0`. Configure Gemini or Vertex credentials according to your local
ADK setup before using the Dev UI or live model calls.

The model is intentionally centralized in
`src/main/java/com/benefits/adk/BenefitsConciergeAgent.java`.

## Eval Cases

Java ADK upstream evaluation support is currently marked as coming soon. Until
that lands, the rung keeps eval fixtures in:

```text
src/test/resources/evals/rung01a_eval_cases.json
```

Use those cases in the ADK Dev UI as smoke checks. The judge criteria verify:

- grounded fictional 401(k)/HSA answers,
- deterministic math tool usage,
- citation of local retrieval source ids,
- refusal of real payroll/account transactions,
- no legal, tax, investment, or fiduciary advice.

## Rung 01B A2UI Verification Scaffold

The project includes a Java-side trusted A2UI-shaped payload builder:

```text
src/main/java/com/benefits/adk/ui/
```

It only allows `Card`, `Table`, and `Text` components and blocks executable or
external props. The exposed tool returns an A2UI `DataPart`-style shape with
`metadata.mimeType = application/json+a2ui`, matching the renderer discovery
pattern from the ADK A2UI docs. This proves the payload shape and server-side
validation model before Rung 01C adds a React renderer.

## Managed Retrieval Path

Rung 01A ships with `LocalBenefitsKnowledgeRetriever` so the module runs
offline. The interface boundary is `BenefitsKnowledgeRetriever`; swap that
implementation for Agent Search once the Google Cloud project, datastore, and
fictional KB ingestion are configured.

Do not add custom chunking/embedding code here. Managed retrieval remains
infrastructure for Phase 10 rather than the lesson.
