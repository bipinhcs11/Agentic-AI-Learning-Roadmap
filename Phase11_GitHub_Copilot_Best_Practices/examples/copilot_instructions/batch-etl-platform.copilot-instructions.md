<!-- EXAMPLE: save as .github/copilot-instructions.md in an overnight batch/ETL repo.
     Fictional platform ("nightly-settlement-batch") — rename, keep the shape.
     Included because half of enterprise banking code is batch, and almost no
     Copilot guidance exists for it. -->

# Repository instructions for GitHub Copilot

## What this project is

`nightly-settlement-batch` runs the end-of-day settlement window: ingest cleared
transactions from the card networks, reconcile against the ledger, produce
settlement files for the Fed/ACH cutoffs, and emit the GL postings. Spring Batch 5
on Java 21, orchestrated by Control-M. **The batch window is 23:00–04:30 ET and the
cutoffs do not move** — a job that becomes 20% slower is a production incident even
though every test passes.

## Architecture in five lines

- One Gradle module per job under `jobs/` (`ingest-network-files`, `reconcile`,
  `settlement-files`, `gl-postings`); shared chunk components in `batch-commons`.
- Spring Batch chunk model everywhere: reader → processor → writer; chunk size and
  commit interval come from `application.yaml` per job — never hardcoded.
- **Every job must be restartable**: state lives in the JobRepository, readers are
  restart-safe (keyset pagination, never OFFSET), writers are idempotent
  (upsert by natural key). "Rerun from scratch" is not a recovery strategy at 3 a.m.
- File exchange via `FileGateway` (SFTP + PGP + control-file handshake) — a data
  file without its `.ctl` checksum twin does not exist, in either direction.
- Reconciliation breaks go to `recon_break` with a reason code — jobs continue past
  individual breaks (skip policy) and fail the run only on threshold breach
  (`recon.break-threshold`).

## How to build, test, validate

- Build + unit: `./gradlew check`
- Job-level integration test (Testcontainers Postgres + localstack SFTP):
  `./gradlew :jobs:reconcile:integrationTest`
- Run one job locally against fixtures:
  `./gradlew :jobs:reconcile:bootRun --args='--spring.batch.job.name=reconcileJob --run.date=2026-07-10'`
- Performance guard: `./gradlew :jobs:reconcile:perfTest` compares rows/sec against
  the baseline in `perf-baseline.json` — required when touching any reader/processor/
  writer; a >10% regression fails.

## Batch rules (non-negotiable)

- **Determinism**: same input files + same `run.date` ⇒ byte-identical outputs.
  No `LocalDate.now()` inside job logic — business dates come from `RunContext`.
  Iteration order over map-like structures must be explicit (sorted), or the
  settlement file diff will light up for no reason.
- **Restartability proof**: every new/changed step needs the kill-and-restart test
  (`BatchRestartTestSupport`) — kill mid-chunk, restart, assert no duplicates and
  no gaps. This test is not optional and not mockable.
- **Skip/retry policy**: poison records skip with a `recon_break` row + structured
  log (record key, reason, file, line) — never silent `continue`; retries only on
  transient infra exceptions (`TransientDataAccessException`, SFTP I/O), with
  backoff, never on business rejects.
- **Memory discipline**: streaming everywhere — readers page, processors hold one
  record, writers batch. Loading a file into a `List` fails review at any size;
  tonight's file is 100× the fixture.
- **Financial totals**: every output file carries computed control totals
  (count + hash + sum in minor units); `TotalsVerifier` runs as the last step of
  every job — a totals mismatch fails the job BEFORE file transmission.
- **Observability**: per-step metrics (rows read/written/skipped, duration) via
  the built-in listeners in `batch-commons` — new steps register them; the ops
  dashboard and the 2 a.m. operator depend on it.

## What NOT to do

- No parallelism changes (`taskExecutor`, partitioning, chunk size) as a drive-by —
  they change DB lock behavior in the window; propose with perfTest evidence and a
  rollback note.
- No new direct DB reads of another team's schema — cross-domain data arrives by
  file or replicated read model, per the integration contract.
- No timezone arithmetic outside `BusinessCalendar` (it owns ET cutoffs, bank
  holidays, and DST — especially DST; two incidents say you won't get it right inline).
- Do not "clean up" `Legacy/CobolBridge` formats — field positions are a contract
  with a mainframe; byte offsets are load-bearing.
