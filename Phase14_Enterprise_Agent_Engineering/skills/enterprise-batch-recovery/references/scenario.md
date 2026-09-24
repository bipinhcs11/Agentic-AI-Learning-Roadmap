# Scenario E — Failure after a committed chunk

Fictional import: chunk one committed, chunk two failed after a dependency timeout. Determine which writes were committed and whether the external dependency processed any ambiguous calls. Reuse identifying input parameters only when the input checksum and restart eligibility are unchanged.

Expected recommendation: correct the failure, verify replay safety, and review the exact restart action. Do not add a timestamp to force a new instance as an unexplained workaround.

Acceptance for a runnable extension: inject a post-commit failure, restart, verify no duplicate business output, reject stale/changed-input approval, and prevent concurrent restart. If evidence is unavailable, say recovery is not yet established.

Phase 14 does not provide a restart endpoint; use it to design the extension, not to claim an existing capability.

Engineering practices: loop, memory, orchestration, guardrails, human review, observability.
