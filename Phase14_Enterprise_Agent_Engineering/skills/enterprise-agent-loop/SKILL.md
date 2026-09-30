---
name: enterprise-agent-loop
description: Implement or review bounded agent loops and cross-service orchestration, preserving policy, budgets, evidence, and human-action boundaries.
---

# Bounded loop and orchestration

Read [scenario instructions](references/scenario.md). Inspect the planner/tool interfaces, completion criteria, global call/time/token budgets, persistence, and action policy.

Make every tool execution pass through one authoritative validation/budget boundary. Account for retries and child work in the same task budget. Do not place SDK automatic tool loops inside an outer planner without equivalent execution hooks. Completion requires observable goal evidence, not a model's claim.

Define exits for success, review/clarification, deadline, budget, repeated/no-progress action, and tool failure. Use canonical action/arguments/state version for repetition checks. Distinguish cooperative deadlines from actual I/O cancellation. Treat an ambiguous write outcome as reconciliation work, not a routine retry.

Sequence dependent operations. Parallelize only independent permitted reads with a shared budget, bounded workers, cancellation, and explicit partial-failure aggregation. Use specialist agents only when the requested design benefits measurably; a multi-agent design does not authorize spawning development assistants or live operational workers.

Keep approved mutation outside model-granted authority. Correlate run/tool/job IDs, use low-cardinality metrics, and avoid logging payloads/private reasoning.

Deliver a state diagram, focused implementation/design, stop-condition evidence, and documented limitations.
