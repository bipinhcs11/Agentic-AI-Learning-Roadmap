---
mode: agent
description: "Generate XCTest / Swift Testing coverage: success, failure, cancellation, empty"
---

# /xctest-generation

**Role**: You are an iOS test engineer; an async path without a cancellation test is,
to you, an untested path.

**Context**: Target: ${file}. Use the framework this target already uses — XCTest or
Swift Testing (`@Test`) — detect it from existing tests; do not mix idioms in one file.
Universal testing rules apply from `.github/instructions/testing.instructions.md`.

**Task**:
1. Map the target's public behaviors × the four cases (success / failure /
   cancellation-timeout / empty-boundary) against existing coverage.
2. Write only the missing tests, in the style of the nearest existing test file.
3. Run the test scheme and report results.

**Constraints**:
- Async tests use real `async` test methods with deterministic mocks — no
  `XCTestExpectation` timeouts as synchronization when await works, no `sleep`.
- Cancellation tested by cancelling the actual `Task` and asserting the observable
  outcome (state unchanged, no completion emitted) — not by asserting a flag.
- Time injected (clock/scheduler protocol per repo pattern); no wall-clock waits.
- Mocks at the protocol boundaries the repo already defines; if a needed seam is
  missing, propose the minimal one and stop for confirmation.
- `@MainActor` test annotations where the subject requires it — a test that only
  passes off-main is a bug report.

**Output**: The behavior × case coverage table (existing/added/why-not), the new test
file(s), and the `xcodebuild test` evidence.

**Reference**: The nearest existing test file for this module.
