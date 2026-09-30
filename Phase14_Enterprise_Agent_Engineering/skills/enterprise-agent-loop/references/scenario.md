# Scenario G — Contract, telemetry, and runbook orchestration

A fictional diagnostic task needs three sources. Determine dependencies first, then consider parallel read collection. Join results by task/source/version; preserve conflict and unavailability.

In Phase 14, AgentLoop uses a deterministic planner, typed read tools, at most eight total attempts, one transient-read retry, a cooperative deadline, and evidence-based completion. Batch launch is a separate reviewer-controlled transition.

Acceptance: a repeated planner and false completion stop; retries consume budget; inaccessible sources cannot be bypassed through a handoff; a reviewer model cannot approve an action. Test at the actual tool-execution boundary, including SDK-hidden calls if used.

Output: plan/state machine, shared budget propagation, action validation, failure behavior, and real test results. Do not claim distributed tracing from a run ID alone.

Engineering practices: harness, context, loop, tools, orchestration, guardrails, human review, observability.
