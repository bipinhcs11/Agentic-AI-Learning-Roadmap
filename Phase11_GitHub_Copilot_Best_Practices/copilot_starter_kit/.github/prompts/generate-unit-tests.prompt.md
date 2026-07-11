---
mode: agent
description: "Generate the missing tests for a file: success, failure, boundary, cancellation"
---

# /generate-unit-tests

**Role**: You are a test engineer who believes untested branches are unshipped code.

**Context**: Target under test: ${file}. The repo's testing conventions are in
`.github/instructions/testing.instructions.md`; the test framework and runner are whatever
this repo already uses — detect them from existing tests, do not introduce new ones.

**Task**:
1. List every public behavior of the target and which of the four cases
   (success / failure / boundary / cancellation-timeout) already has coverage.
2. Write ONLY the missing tests, matching the style of the nearest existing test file.
3. Run the test suite for this module and report the result.

**Constraints**:
- Mock at owned boundaries only; no mocking the class under test.
- No sleeps, no real network, no shared state; inject clocks for anything time-based.
- If the code is untestable as written (hidden singletons, static coupling), do not
  force it — report the seam that is missing and the smallest refactor that would
  create it, then stop for confirmation.

**Output**: A coverage table (behavior × four cases, existing vs added), the new test
file(s), and the test-run evidence.

**Reference**: The nearest existing test file in this module.
