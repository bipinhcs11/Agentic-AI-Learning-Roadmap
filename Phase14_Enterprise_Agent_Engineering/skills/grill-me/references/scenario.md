# Enterprise design questions

Example request: “Grill me on our proposal to let an assistant restart failed Spring Batch jobs. Focus on the three decisions most likely to cause duplicate processing.”

Inspect existing job identity, restart configuration, approval flow, and tests. Ask only unresolved design decisions. Useful areas, selected according to the proposal:

- Business goal and definition of success; known workflow versus agentic uncertainty.
- Tenant/resource authority, delegated identity, and who may approve the exact action.
- Stable job/input identity, immutable checksum, committed checkpoints, and replay effects.
- Loop/call/time budgets, repeated actions, partial failure, and cancellation.
- State ownership, crash window between approval and launch, outbox/idempotency strategy.
- Evidence/provenance, eval gates, observable failure signals, and recovery owner.

Do not ask all of these mechanically. For the example, prioritize restart versus rerun identity, ambiguous external writes, and approval freshness. Derive answers already established by code rather than asking the user to repeat facts.

Output: a concise decision record and acceptance cases, such as failure after committed chunk, duplicate approval, changed input, and concurrent launch.

Engineering practices: design review across the ten topics.
