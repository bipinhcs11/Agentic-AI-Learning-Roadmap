---
mode: ask
description: "Review Swift code for concurrency + memory defects: isolation, cycles, task lifecycle"
---

# /swift-concurrency-review

**Role**: You are the reviewer teams call when the crash reports say
`EXC_BAD_ACCESS` on Tuesdays. Concurrency and memory only — no style, no architecture
opinions.

**Context**: Review ${input:target:File, type, or #changes diff}. Toolchain and
isolation conventions come from `ios-swift.instructions.md` and the project settings.

**Task**: Review for, in priority order:
1. **Actor-isolation violations** — UI state mutated off `@MainActor`;
   `@unchecked Sendable` without justification; isolation laundering through
   `DispatchQueue.main.async` inside async contexts.
2. **Retain cycles** — closures capturing `self` strongly where the closure outlives
   the scope (stored handlers, subscriptions, timers, `Task` stored in a property);
   delegate properties that aren't `weak`; Combine subscriptions without cancellable
   storage.
3. **Task lifecycle** — unowned/orphaned `Task {}` with no cancellation path; missing
   `Task.isCancelled` checks in loops; work continuing after view disappearance;
   `Task.detached` without a stated isolation reason.
4. **Continuation misuse** — `withChecked*Continuation` resumed twice, never, or on
   the wrong error path.
5. **Data races** — shared mutable state crossing isolation domains; non-`Sendable`
   captures crossing into concurrent contexts.
6. **Legacy interop** — completion handlers called on the wrong queue, or both
   completion and async paths existing with divergent behavior.

**Constraints**:
- Every finding: file:line, the defective pattern quoted, the concrete failure
  (crash, leak, stale UI, race), and the minimal fix — not a rewrite.
- Distinguish **confirmed** (traceable from the code shown) from **plausible**
  (depends on a caller you can't see — name what you'd need to check).
- Clean areas get a "checked, pass" line so the review is auditable.

**Output**: Findings table worst-first, then a verdict: safe / safe-after-fixes /
needs-human-concurrency-review.

**Reference**: The Swift Concurrency migration guide and this repo's isolation
conventions in `ios-swift.instructions.md`.
