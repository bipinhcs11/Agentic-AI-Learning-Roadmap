# The iOS Workflow, End to End — One Feature from Ticket to Merged PR

Everything else in this overlay is parts. This document is the assembly: one
realistic feature carried from requirement to merged pull request, showing which
prompt runs at each step, what context it gets, what good output looks like, and
what gets rejected.

The running example is `MobileBank-iOS`, the fictional retail-banking app from
[`examples/copilot_instructions/ios-retail-banking-app.copilot-instructions.md`](../../examples/copilot_instructions/ios-retail-banking-app.copilot-instructions.md).
Swap in your own app; the sequence is the point.

**The sequence**: requirement → work-item analysis → data layer → UI slice →
tests → three reviews → PR review → human + CI decide.

---

## The ticket

> **MB-4721 — Scheduled transfers: view and cancel**
>
> Customers can see upcoming scheduled transfers (payee, amount, date, recurrence)
> and cancel one before it executes. Cancel requires confirmation and follows the
> step-up authentication policy. List must work offline from cache with a
> staleness banner. API: `GET /v2/accounts/{id}/scheduled-transfers`,
> `DELETE /v2/scheduled-transfers/{transferId}`. Accessibility and unit tests per
> house rules. Target: next release train.

Nobody pastes this at Copilot and types "implement". That is how you get a
5,000-line diff that force-unwraps its way through certificate pinning.

## Step 0 — What is already committed before anyone prompts

The reason every later step is short is that the context is already in the repo:

- `.github/copilot-instructions.md` — the app's architecture, build/test
  commands, and banking rules (the example file above).
- `ios-swift.instructions.md` + `objective-c.instructions.md` — this overlay's
  guardrails, applied by path.
- The prompt files below, committed under `.github/prompts/`.

Copilot reads all of it automatically. The per-step prompts only add what is
unique to MB-4721.

## Step 1 — Work-item analysis (before any code)

**Agent**: [`work-item-analyst`](../../examples/agents/work-item-analyst.agent.md)
(read-only — it cannot edit files, so it cannot "helpfully" start coding).

```text
@work-item-analyst Analyze MB-4721 (pasted below). Slice it into
small verifiable tasks per the house definition: each slice independently
buildable, testable, and reviewable.
```

**Good output**: four slices with acceptance criteria —

1. Data layer: both endpoints behind `ScheduledTransfersRepository` protocol.
2. Offline cache: SwiftData-backed read path with staleness metadata.
3. UI slice: list + cancel flow (confirmation + step-up path), all view states.
4. Hardening: test-gap fill, accessibility, privacy review, PR.

Plus the two questions worth asking the product owner *now*: what happens to a
transfer already in-flight when cancel lands, and is recurrence editable or
view-only (it affects the domain model). **Reject**: any "analysis" that is
actually an implementation plan with code in it.

## Step 2 — Data layer: `/networking-layer` (slice 1)

```text
/networking-layer client=Core/Networking/APIClient
endpoint="GET /v2/accounts/{id}/scheduled-transfers + DELETE /v2/scheduled-transfers/{transferId} — list and cancel scheduled transfers"
```

**Good output**: DTOs decoding at the edge, both calls behind
`ScheduledTransfersRepository`, an error-mapping table where auth-expiry, offline,
and 5xx are distinct outcomes, and tests including cancellation mid-flight. The
DELETE response carries the server's confirmation summary — the banking rules
require rendering *that*, never client-echoed input.

**Reject**: a fresh `URLSession` wrapper ("I noticed you might want a more modern
networking stack"), retry logic the client core doesn't define, or `Double` for
amounts. The instructions file forbids all three; if one appears, the fix is a PR
against the instructions, not a longer chat message.

## Step 3 — Offline cache: `/persistence-repository` (slice 2)

```text
/persistence-repository store=Core/Storage
repository="ScheduledTransfersCache — offline read of upcoming transfers with fetchedAt staleness metadata"
```

**Good output**: SwiftData model that never crosses the domain boundary, upsert
that overwrites stale rows, a `fetchedAt` timestamp the UI can turn into the
staleness banner, in-memory tests, and an explicit "schema unchanged for existing
installs? no — new model, lightweight migration" statement.

**Reject**: anything customer-identifying flagged for UserDefaults, or a cache
that becomes a second source of truth with its own refresh logic. Cache serves
reads; the repository stays the only door.

## Step 4 — UI slice: `/swiftui-feature` (slice 3)

```text
/swiftui-feature feature="ScheduledTransfers — list of upcoming scheduled
transfers with cancel; cancel shows server-signed confirmation and handles the
step-up authentication path (AuthChallenge)"
reference=Features/CardControls
```

The reference is the repo's own most recent feature — for navigation and
composition patterns, one working example beats three paragraphs.

**Good output**: the slice declares state ownership *before* code (one
`@MainActor @Observable` view model, one state enum), renders all five states
(loading/empty/error/offline/loaded — offline shows the staleness banner from
step 3), routes cancel through confirmation + `AuthChallenge`, and ships
accessibility in the same diff: labels, identifiers, Dynamic Type, spelled-out
currency for VoiceOver.

**Reject**: networking imported in the view, a second copy of the transfers
array living in view state, or a cancel flow that renders the amount from the
tapped row instead of the server's confirmation response. That last one is the
kind of bug that looks identical in a demo and only differs in an incident.

## Step 5 — Test gaps: `/xctest-generation` (slice 4 begins)

```text
/xctest-generation   (target: ScheduledTransfersViewModel)
```

Steps 2–4 already produced tests; this pass maps behaviors × the four cases
(success / failure / cancellation / empty) and writes only what is missing —
typically the awkward ones: step-up abandoned halfway, cancel racing a refresh,
cache stale + network offline at once.

**Good output**: a coverage table first, then only the missing tests, in the
style of the nearest existing test file. **Reject**: re-generated duplicates of
existing coverage, or "cancellation tests" that assert a boolean flag instead of
cancelling a real `Task` and asserting the observable outcome.

## Step 6 — Three reviews, before any human's time is spent

Each runs in ask mode (read-only) against the diff:

```text
/swift-concurrency-review target=#changes
/accessibility-review target=Features/ScheduledTransfers
/privacy-secure-storage-review target=#changes
```

Real findings these catch in exactly this kind of diff: a cancel `Task` stored
in the view model but never cancelled in `deinit` (concurrency); a cancel button
whose VoiceOver label reads "trash" instead of "Cancel scheduled transfer to
{payee}" (accessibility); the confirmation payload — payee name, amount —
interpolated into a debug log (privacy). Fix, re-run, get the
"checked, pass" lines.

These reviews are cheap, repeatable, and produce findings with file:line and a
fix. Spend them freely; they are the drafts that make the human review short.

## Step 7 — `/ios-pr-review`, then the PR

```text
/ios-pr-review target=#changes
```

The last machine pass reads the whole diff the way the paged-at-2am reviewer
would: scope (one feature? yes), boundaries, edge states, tests, plus the one
question for the author. Then the PR goes up — small, one slice of review burden
at a time if the team prefers stacked PRs — and the standing order applies:

> AI can author. AI can advise. CI and a human decide.

CI runs the same commands the instructions file names (`xcodebuild test`,
`swiftlint --strict`); the human reviewer reads a diff that three specialist
reviews have already swept.

---

## Why this works (and what to steal)

- **The ticket never went to Copilot raw.** Analysis first, slices second, code
  third. The analyst agent is read-only *by tool allowlist*, so the temptation
  doesn't exist.
- **Each prompt added only what was unique.** Architecture, rules, and build
  commands were already committed context — the per-step prompts are three lines.
- **Reviews are prompts too.** Concurrency, accessibility, and privacy each got
  the same first-class treatment as implementation — findings with file:line,
  severities, and "checked, pass" lines, before a human spent a minute.
- **Every rejection became a rule.** Anything Copilot got wrong twice is now a
  line in an instructions file — folklore in team chat helps one person; a
  committed rule helps the next hundred sessions.
