---
name: enterprise-batch-delivery
description: Build or change Spring Batch ingestion jobs and reviewed launch workflows with stable job identity, transactional writes, and replay safety.
---

# Deliver a batch workflow

Read [scenario instructions](references/scenario.md). Inspect the pinned Batch version, input format/version, JobRepository, transaction manager, reader/writer, scheduler, and side effects.

Keep agent planning outside chunk transactions. Define identifying job parameters from business input identity. Distinguish a new input/rerun from a restart. Use a restartable reader or explicitly justify replay; make writers idempotent by tenant/business key where replay is possible. Define skip/retry/quarantine policy from actual failure classes, not blanket exception handling.

When launch needs review, bind approval to immutable action, parameters, tenant, input version, and expiry. Recheck authorization and freshness at execution. Long jobs need durable asynchronous launch/status and crash recovery, not an HTTP thread held indefinitely.

Test transaction rollback, duplicate launch, replay, tenant isolation, and material failure boundaries for the implementation being changed. Use fictional input. Explain what the local datastore cannot prove about the production database.

Deliver the focused code/config change, run instructions, expected outcomes, and evidence. Do not run against production or alter scheduler settings unless the user authorized those actions.
