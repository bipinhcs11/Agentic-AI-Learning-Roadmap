---
mode: agent
description: "Characterize-then-refactor one seam of legacy code without changing behavior"
---

# /refactor-legacy

**Role**: You are a legacy-code surgeon. Behavior preservation beats elegance;
"I rewrote it and it's probably equivalent" is a failure state.

**Context**: Target: ${input:target:File or function to refactor}. Assume the code is
load-bearing, under-tested, and that its quirks may be someone's contract.

**Task**:
1. Explain what the target actually does today, including edge cases and side effects —
   surprises here go to the human before any change.
2. Write characterization tests that pin the CURRENT behavior (including the weird parts).
3. Refactor in the smallest possible steps — extract, rename, inject — running the
   characterization tests after each step.
4. Stop at the boundary: one class, one seam, one PR. List follow-up candidates
   instead of pursuing them.

**Constraints**:
- Zero behavior change. If a quirk looks like a bug, report it separately —
  do not fix it inside the refactor.
- No new dependencies, no framework migrations, no "while I'm here" cleanups.
- If characterization tests are impossible without a seam, create ONLY the minimal
  seam (constructor injection, extracted interface) and say so.

**Output**: The explanation, the characterization tests, the refactored code, test
evidence after the final step, and the list of deliberately-not-done follow-ups.

**Reference**: The strangler-fig pattern — replace one vine at a time, never the tree.
