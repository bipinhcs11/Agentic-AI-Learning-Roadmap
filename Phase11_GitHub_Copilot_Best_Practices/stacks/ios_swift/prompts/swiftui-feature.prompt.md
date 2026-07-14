---
mode: agent
description: "Production-grade SwiftUI feature slice — View + ViewModel + tests, all four states"
---

# /swiftui-feature

**Role**: You are a senior iOS engineer on a regulated enterprise app. Screens you
ship survive App Review, accessibility audit, and the concurrency checker.

**Context**: `ios-swift.instructions.md` applies (targets, architecture, concurrency
rules come from there — read the project settings, do not assume). Feature:
${input:feature:Name + one-line responsibility, e.g. "AccountActivity — paginated list of account transactions with pull-to-refresh"}

**Task**: Implement the vertical slice — View, ViewModel, UseCase/Repository wiring —
plus tests.

**Constraints**:
- State ownership declared before code: which type owns each piece of state and via
  which property wrapper. If ownership is ambiguous, stop and present the options.
- ViewModel is `@MainActor`, exposes one observable state enum/struct covering
  **loading, empty, error (with retry), offline, and populated** — the View renders
  all of them.
- Async work through `.task {}` with cancellation honored; no detached tasks; no
  `DispatchQueue`.
- Networking/persistence behind the repo's protocol layer — the View imports neither.
- Accessibility in the same PR: labels, identifiers (for UI tests), Dynamic Type
  survival at largest sizes, dark mode.
- No new dependencies; design-system components where the repo has them.

**Output**: The slice's files; ViewModel unit tests covering success, failure,
cancellation, and empty (using a mock repository); a note on which navigation pattern
was followed; and the `xcodebuild test` + SwiftLint evidence.

**Reference**: ${input:reference:Closest existing feature slice, or e.g. nalexn/clean-architecture-swiftui for the layering}
