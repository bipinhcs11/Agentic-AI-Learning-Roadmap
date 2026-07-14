---
description: "Swift + SwiftUI conventions — concurrency, state ownership, view hygiene"
applyTo: "**/*.swift"
---

# Swift / SwiftUI instructions

## Toolchain & targets

- Target the minimum iOS version, Xcode version, and Swift version pinned in this
  repo's project settings — read them; never assume newer language features.
- SwiftUI for new screens; preserve UIKit for existing flows. Do not migrate UIKit
  surfaces as a side effect of another task.
- Validation: run SwiftLint and the repo's `xcodebuild test` scheme before declaring
  any task complete.

## Concurrency (the rules Copilot most often gets wrong)

- Structured concurrency (`async/await`, `TaskGroup`) over completion handlers in new
  code; wrap legacy completion APIs with `withCheckedThrowingContinuation` at the
  boundary rather than spreading callbacks.
- UI-facing mutable state is `@MainActor`-isolated. Never hop to the main thread with
  `DispatchQueue.main.async` inside async code — isolation is declared, not sprinkled.
- No `Task.detached` unless an isolation requirement genuinely demands it, stated in
  a comment.
- Every `Task` created in a view or view model has an owner and gets cancelled —
  `.task {}` for view-lifecycle work; stored tasks cancelled in `deinit`/`onDisappear`.
  Cancellation behavior is explicit: check `Task.isCancelled` in loops.
- Preserve `Sendable` conformances and actor isolation — never silence a concurrency
  warning with `@unchecked Sendable` without a justifying comment.

## State & architecture

- Follow this repo's architecture boundaries (View → ViewModel → UseCase/Repository).
  Views never call networking or persistence directly.
- One source of truth per piece of state; choose property wrappers deliberately
  (`@State` local, `@StateObject`/`@Observable` owned, `@Binding` borrowed,
  `@Environment` injected) — if you can't say who owns the state, stop and ask.
- No force unwraps, force casts, or force `try` outside tests. No hidden singletons —
  dependencies are injected (initializer injection preferred).
- Business logic stays out of `body`: complex transforms live in the view model,
  computed properties stay cheap — `body` may be recomputed at any time, so no side
  effects and no object creation of heavyweight dependencies inside it.
- Networking is abstracted behind protocols; persistence (SwiftData/Core Data) behind
  repository types. DTOs decode at the edge; domain types flow inward.

## Every screen ships with

- Loading, empty, error, and offline states — designed, not defaulted.
- Accessibility: labels and identifiers on interactive elements, Dynamic Type support,
  dark-mode-safe colors, VoiceOver-sensible ordering.
- Tests: unit tests for the view model covering success, failure, cancellation, and
  empty states (see the testing instructions); navigation and state transitions tested.

## Privacy & security

- Never log tokens, PII, or Keychain values. Secrets live in the Keychain, not
  UserDefaults, not plists, not code.
- New third-party dependencies go through the dependency-audit skill and SPM only —
  exact versions, no branch pins.
