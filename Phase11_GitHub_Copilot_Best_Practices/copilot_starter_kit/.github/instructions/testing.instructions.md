---
description: "Rules for generating and modifying tests, any framework"
applyTo: "**/{test,tests,__tests__,spec}/**,**/*{Test,Tests,.test,.spec}.*"
---

# Testing instructions (all test files)

- Every behavior gets four cases: **success, failure, empty/boundary, and cancellation
  or timeout** where the operation is async.
- Test names state behavior, not implementation:
  `rejects expired token` — not `test_validate_2`.
- Arrange–Act–Assert with one logical assertion per test. If a test needs ten asserts,
  it is several tests.
- Mock at the boundary you own (repository, client interface) — never mock the class
  under test or private internals.
- No sleeps, no wall-clock time, no real network, no shared mutable state between tests.
  Inject clocks and use fakes; tests must pass in parallel and in any order.
- Test data says what matters: build minimal fixtures inline or with builders; a fixture
  with 40 irrelevant fields hides the one that matters.
- When asked to "fix a failing test", first state whether the test or the code is wrong.
  Never adjust an assertion to match buggy behavior without saying so.
- Coverage is a floor, not a goal: do not generate assertion-free tests or tests that
  restate the implementation line by line.
