---
name: enterprise-batch-recovery
description: Analyze failed Spring Batch executions and prepare or carry out an explicitly authorized restart with input/version and replay checks.
---

# Recover a failed batch execution

Read [scenario instructions](references/scenario.md). Start with read-only evidence: job and execution IDs, identifying parameters, status, committed step/chunk progress, input checksum/version, failure category, and downstream side effects. Sanitize record contents.

Distinguish transient infrastructure failure, data rejection, configuration error, and code defect. Check whether the cause is corrected, the job is restartable, and input identity is unchanged. A new random/timestamp parameter may create a new JobInstance; do not present that as a restart.

Before an authorized restart, verify current state, scoped permission, approved parameters, approval freshness if required, and concurrency ownership. Reject running/completed instances and changed input when restart semantics do not permit them. Reconcile ambiguous non-idempotent writes by business key before retrying.

Deliver a recovery proposal with exact target/parameters, replay effects, prerequisites, verification, and stop conditions. A diagnosis request does not authorize restart. If execution is authorized and prerequisites are established, proceed within scope without asking for redundant approval; otherwise finish the read-only assessment and identify the missing prerequisite.

Confirm recovery from job/business-state evidence, not merely an accepted launch response.
