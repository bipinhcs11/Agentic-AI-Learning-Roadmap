# Scenario D — Refresh two technical documents

Phase 14's BATCH flow reads evidence, returns WAITING_APPROVAL, and lets an authenticated reviewer approve one fixed catalogRefresh action. Spring Batch writes two fixture documents in one chunk with tenant/document-key upserts.

Acceptance: pending/rejected proposals do not write; repeated successful approval returns the same execution ID; a second approved proposal still leaves two catalog rows; other tenants see no rows.

The local ListItemReader replays fixtures and does not persist a cursor. H2 and approvals disappear on restart. Do not claim durable exactly-once execution. Production extension: immutable manifest, persistent JobRepository, checkpointed reader, action-bound approval, and outbox/worker ownership.

Output: executable job plus documented retry/replay semantics, launch/status contract, and focused tests.

Engineering practices: harness, loop boundary, tools, memory, orchestration, guardrails, human review, observability.
