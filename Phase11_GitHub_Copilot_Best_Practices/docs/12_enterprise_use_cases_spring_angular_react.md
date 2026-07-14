# 12 — Enterprise Use Cases: Spring Boot, Angular & React

These are realistic, end-to-end training exercises for developers in large regulated
enterprises. All organizations, services, work items, data, identifiers, and rules are
**fictional and educational**. They do not describe any real company or institution,
including any past or present employer of the author. Never replace the sample data
with real customer, employee, financial, or production data.

Each scenario shows where Copilot helps and where the human must decide. That boundary is
more useful than a catalog of clever prompts.

## Use case 1 — Spring Boot: idempotent scheduled-transfer creation in IntelliJ

### Fictional work item

`TRN-142`: Mobile clients sometimes retry `POST /scheduled-transfers` after a timeout.
The service must return the original result for the same client request and must never
create a second schedule. No public API or database change is allowed in this slice; the
repository already contains `IdempotencyGuard`, used by `POST /payees`.

### Acceptance criteria

- A request with a new `Idempotency-Key` creates one schedule and returns `201`.
- Repeating the same key and same payload returns the original result without a second row.
- Reusing the key with a different payload returns the repository's existing conflict
  `ProblemDetail` response.
- Missing/invalid keys follow the current validation contract.
- Authorization, audit event, and transaction boundary remain unchanged.
- Focused unit and integration tests pass; no new dependency or migration appears.

### Copilot workflow

1. **Ask, no edits:** attach the scheduled-transfer controller/service/tests and the
   existing payee implementation. Ask Copilot to trace both call paths, name the reusable
   pattern, and list open questions. Verify every cited method in IntelliJ.
2. **Plan:** ask for the smallest file set and a test matrix. Reject a plan that changes
   the schema, moves transaction boundaries, or invents a second idempotency mechanism.
3. **Edit or Agent:** use Edit if the target files are known. Use Agent only if discovering
   configuration or test fixtures is necessary.
4. **Verify:** run the exact focused commands first, then the repository verification
   command. Inspect the database assertion proving one row, not only the HTTP status.
5. **Review:** compare against the payee reference and ask Copilot code review for a first
   pass. A Spring/domain owner provides required human approval.

### Bounded implementation prompt

```text
Role: Senior Spring Boot maintainer for this repository.
Context: Fictional work item TRN-142. Use the existing POST /payees idempotency flow as
the reference. Relevant files are ScheduledTransferController, ScheduledTransferService,
their tests, and IdempotencyGuard.
Task: Apply the existing idempotency pattern to POST /scheduled-transfers.
Constraints: Preserve the API and schema. Do not add a dependency. Do not move the
@Transactional boundary. Do not log request payloads or identifiers. Stop and explain if
the current IdempotencyGuard cannot represent payload mismatch.
Validation: Add tests for new key, same key/same payload, same key/different payload, and
missing key. Run ./mvnw -q -Dtest=ScheduledTransfer* test, then ./mvnw -q verify.
Output: Changed files, assumptions, command results, and remaining concurrency risks.
```

### What Copilot should produce

- A small controller/service/test diff that follows the existing payee pattern.
- Test evidence for behavior and persistence count.
- An explicit stop/report if the existing abstraction cannot meet an acceptance criterion.

### Human-only decisions and review traps

- Whether the idempotency key is scoped per authenticated principal and endpoint.
- Whether the response may be replayed after authorization/entitlement changes.
- Concurrency correctness: two simultaneous first requests must not both execute.
- Transaction isolation, unique-constraint behavior, audit semantics, and retention policy.
- Never accept an in-memory map/cache just because it makes the unit test pass.

## Use case 2 — Angular: accessible beneficiary form in VS Code

### Fictional work item

`WEB-308`: Add a beneficiary nickname field to an existing add-beneficiary flow. The
nickname is optional, 1–40 characters after trimming, must render safely, and must be
announced correctly by screen readers. The backend OpenAPI client already exposes
`nickname?: string`; no API generation is needed.

### Acceptance criteria

- The existing strictly typed Reactive Form gains an optional nickname control.
- Whitespace-only input is normalized to `undefined`; length validation is visible and
  associated with the field through the design-system form component.
- Keyboard flow and focus-on-error continue to work; no hardcoded English is added.
- The submitted DTO contains no nickname for blank input and the trimmed value otherwise.
- Component, accessibility, and mapper tests cover valid, blank, too-long, and API-error cases.

### Copilot workflow

1. Ask Copilot to identify the form model, request mapper, design-system field example,
   i18n keys, tests, and generated API type. Do not ask it to scan the entire monorepo.
2. Use `/typed-reactive-form` from the Angular overlay as a checklist, not permission to
   replace the existing form.
3. Use Edit with the component, template, mapper, translation file, and tests as the
   working set. Review each file before accepting.
4. Run the affected Nx unit/lint targets plus the focused Playwright keyboard/a11y flow.
5. Inspect the rendered error association and payload in the browser; snapshots alone are
   not sufficient accessibility evidence.

### Bounded implementation prompt

```text
In the fictional add-beneficiary feature, add the optional nickname field described in
WEB-308. Follow the existing account-label field and the repository's typed-form and
design-system patterns. Keep this to the form, template, request mapper, approved i18n
files, and their tests. Do not edit the generated API client, introduce a dependency, use
any, or add raw aria-live markup. Normalize trimmed blank input to undefined. Test valid,
blank, >40 characters, focus/error association, and API failure. Run the focused Nx test
and lint targets and report exact results.
```

### Human-only decisions and review traps

- Product/legal approval of what users may place in the field; free text can become a
  sensitive-data channel.
- Unicode length/normalization semantics and backend consistency.
- Translation quality and whether the design-system component meets WCAG 2.2 AA.
- Do not accept direct DOM manipulation, an untyped form, duplicated server state, or an
  accessibility claim based only on generated ARIA attributes.

## Use case 3 — React: operations queue filter with URL-safe state in VS Code

### Fictional work item

`OPS-517`: Add a “stalled longer than” filter to a payment-operations queue. Operators
need 5/15/30-minute presets that survive refresh and can be shared with another authorized
operator. The URL must contain only non-sensitive filter state; no account, customer, or
payment identifiers may be added.

### Acceptance criteria

- Filter state is validated when read from the URL and defaults safely on invalid input.
- The query key includes the normalized threshold; changing it cancels/invalidates the
  correct request according to the repository's TanStack Query pattern.
- The UI uses the existing design-system select, has a programmatic label, and supports
  keyboard interaction.
- Loading, empty, error, and populated states continue to render.
- Tests cover all presets, invalid URL input, back/forward navigation, request parameters,
  and no-results/error states.

### Copilot workflow

1. In Ask mode, attach the queue page, query-key factory, an existing URL-synchronized
   filter, MSW handler, and tests. Ask for state ownership and data-flow before code.
2. Use the React instructions overlay to prevent `useEffect`-driven fetching and ad-hoc
   server-state duplication.
3. Use Edit for a known file set. If Agent mode discovers a utility, require it to stop
   before creating a new shared abstraction or dependency.
4. Run focused Vitest/Testing Library tests, ESLint, TypeScript, and the relevant browser
   test. Manually check browser back/forward behavior.

### Bounded implementation prompt

```text
Implement fictional work item OPS-517 using the existing URL-filter hook and query-key
factory as references. Add only 5, 15, and 30 minute presets. Keep server state in TanStack
Query; do not fetch in useEffect or copy results into Zustand/local state. The URL may hold
only the threshold enum—never payment, account, or customer identifiers. Use the existing
design-system Select. Add MSW-backed tests for presets, invalid URL, navigation, request
parameters, empty state, and error state. Add no dependency and stop before inventing a
new cross-feature abstraction. Run test, lint, and typecheck and report results.
```

### Human-only decisions and review traps

- Whether a shareable URL is permitted at all for the operations application.
- Backend query cost, index support, polling behavior, and rate limits.
- Time semantics: server UTC cutoff versus browser-local calculations and clock skew.
- Do not accept raw query-string concatenation, arbitrary numbers, hidden PII, a new
  interval, or a hook that creates two sources of truth.

## Use case 4 — Cross-stack contract change: Spring Boot + Angular + React

This is the scenario enterprise teams meet most often: one backend contract affects two
frontends owned by different teams and developed in different IDEs.

### Fictional work item

`CASE-771`: The case API adds a backward-compatible `reviewBy` timestamp. Spring Boot
computes and returns it; the Angular customer portal renders a localized message; the React
operations tool renders the exact UTC value with an operator-timezone display. Old clients
must continue to work during a two-release rollout.

### Decompose before generating

| Slice | Owner/IDE | Artifact and verification |
|---|---|---|
| Contract decision | API + frontend leads | OpenAPI change, nullability, timezone, compatibility ADR |
| Backend | Spring Boot / IntelliJ | DTO/domain mapping, contract test, service tests, OpenAPI diff |
| Customer UI | Angular / VS Code | Generated client update through approved command, mapper/view/a11y tests |
| Operations UI | React / VS Code | Schema/type update, timezone display, MSW and component tests |
| Delivery | All teams | Consumer compatibility, staged rollout, observability, rollback plan |

Do not give one Agent session write access to all three repositories and say “implement
CASE-771.” First settle the contract with humans. Then create one bounded task per repo,
each with its own instructions, reference implementation, commands, and reviewer.

### Questions Copilot can help answer

- Where is a similar optional timestamp mapped and rendered?
- Which generated clients and contract tests are affected?
- Which tests prove UTC serialization and locale/timezone display?
- Which dashboards or logs reveal missing/invalid `reviewBy` values after rollout?

### Decisions Copilot must not invent

- The business formula, holiday calendar, or regulatory deadline behind `reviewBy`.
- Whether the field is nullable, absent, or defaulted for old records.
- Which system owns the clock and timezone.
- Release order, compatibility window, rollback, or customer-facing wording.

### Cross-stack completion evidence

- Reviewed OpenAPI diff and compatibility decision.
- Backend unit/contract/integration results.
- Angular type/lint/unit/a11y results and approved client-generation diff.
- React type/lint/unit/browser results with UTC and operator-zone assertions.
- No real case/customer data in fixtures, prompts, screenshots, or logs.
- Human approvals from API, frontend, security/privacy, and product owners as applicable.

## A reusable review prompt for all four scenarios

```text
Review this diff against the work-item acceptance criteria and repository instructions.
Do not modify files. Report only evidence-backed findings in this format:
severity | file:line | violated criterion/rule | concrete failure scenario | smallest fix.
Check scope, security/privacy, authorization, data handling, concurrency, error states,
accessibility, observability, backward compatibility, and meaningful tests. Distinguish
confirmed defects from questions. End with commands that still need to be run and risks
that require a human domain decision.
```

## What “good Copilot adoption” looks like in these use cases

- Copilot shortens discovery, scaffolding, test enumeration, and mechanical editing.
- Developers attach fewer, better context files and receive smaller diffs.
- The agent stops when a contract, security, or domain decision is missing.
- Existing architecture and design-system patterns are reused instead of reinvented.
- Tests prove business behavior, not merely line coverage.
- IDE differences disappear at the enforcement boundary because all paths meet in CI and
  required human review.

