<!-- EXAMPLE: save as .github/copilot-instructions.md in a Java payments microservice.
     Fictional service ("payment-execution-service") — rename, keep the shape. -->

# Repository instructions for GitHub Copilot

## What this project is

`payment-execution-service` executes outbound payments (ACH, wire, RTP) for retail
banking. Upstream: `payment-orchestrator` (REST, sync). Downstream: the core banking
ledger (`ledger-api`, REST), the fraud decision engine (Kafka request/reply), and the
bank's ISO 20022 gateway (MQ). A payment that executes twice is a regulatory incident;
a payment that silently disappears is worse. Correctness beats latency everywhere.

## Architecture in five lines

- Hexagonal: `domain/` has zero Spring/Jackson/JPA imports — pure Java, unit-testable.
- All I/O goes through ports in `domain/port/`, implemented by adapters in
  `adapter/` (`rest/`, `kafka/`, `mq/`, `persistence/`).
- Every state change of a `Payment` goes through `PaymentStateMachine` — never set
  status fields directly. Valid transitions are the enum's whole point.
- The transactional outbox (`outbox_event` table) is the ONLY way events leave this
  service. Never publish to Kafka inside a request thread.
- Money is `javax.money.MonetaryAmount` (JSR-354). `double`/`float` for money fails
  the build via ArchUnit — don't write it.

## How to build, test, validate

- Build: `./mvnw -q -T 1C verify` (includes ArchUnit architecture tests)
- Unit tests only (fast loop): `./mvnw -q test -Punit`
- Integration tests: `./mvnw -q verify -Pintegration` (Testcontainers: Postgres 16,
  Kafka; Docker must be running)
- Lint/format: `./mvnw -q spotless:check` (fix with `spotless:apply`)
- A task is complete only when `verify` passes — ArchUnit failures are failures.

## Payment-domain rules (non-negotiable)

- **Idempotency**: every mutating endpoint requires an `Idempotency-Key` header;
  execution goes through `IdempotencyGuard` (Postgres unique constraint, not a cache).
  New mutation without idempotency handling = do not generate it, flag it.
- **State machine**: new statuses/transitions are added in `PaymentStateMachine` +
  a migration backfill plan + tests for every legal AND illegal transition.
- **Amounts and currency**: construct via `Money.of(...)`; comparisons via
  `isEqualTo`/`isGreaterThan` — never `equals()` across currencies; rounding only via
  `CurrencyRounding` (bankers' rounding, per-currency scale from ISO 4217).
- **Timeouts**: every outbound call sets connect + read timeouts from
  `application.yaml` under `clients.<name>.*` — never inline durations. Ledger calls
  retry only if the ledger operation is idempotent (`GET`, `PUT` with request id);
  fraud-check replies past `fraud.reply-timeout` route to `ManualReviewQueue`, never
  auto-approve.
- **Audit**: every state change emits `PaymentAuditEvent` via the outbox with actor,
  correlation id, before/after status — amounts yes, account numbers masked
  (`****1234`), never full PAN/IBAN in any log or event.

## Compliance (PCI / SOX context)

- No PAN, IBAN, or real customer data anywhere — including tests: use
  `TestPayments.fake*()` builders (Luhn-valid test PANs from the approved test range).
- Schema changes: Flyway only, `V<n>__<desc>.sql`, backward-compatible for one
  release (expand/contract) — this service blue/green deploys.
- New dependencies need the approved-library check; anything touching crypto, TLS,
  or serialization additionally needs a security-team PR reviewer.

## What NOT to do

- No `@Async`/`CompletableFuture` fire-and-forget for anything that must survive a
  pod restart — that's what the outbox is for.
- No new REST endpoints on this service for orchestration concerns — that logic
  belongs in `payment-orchestrator`; this service executes.
- No mocking `PaymentStateMachine` or `IdempotencyGuard` in tests — use them real;
  they ARE the behavior under test.
- Do not invent config keys — every `@ConfigurationProperties` field must exist in
  `application.yaml` and `config/README.md` in the same PR.
