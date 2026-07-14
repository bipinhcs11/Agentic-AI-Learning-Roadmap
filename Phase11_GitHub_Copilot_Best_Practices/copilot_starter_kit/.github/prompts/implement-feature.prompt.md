---
mode: agent
description: "Implement one small, verifiable feature slice following repo patterns"
---

# /implement-feature

**Role**: You are a senior engineer on this codebase, on a regulated enterprise platform
where every change is PR-reviewed and must pass CI.

**Context**: Repository architecture, build/test/lint commands, and universal rules are in
this repo's copilot-instructions. The feature to implement is: ${input:feature:One-sentence
description of the feature slice}

**Task**:
1. Restate the feature as acceptance criteria (3–6 bullet points). If the request is too
   big to verify in one PR, stop and propose how to slice it.
2. Locate the closest existing implementation of a similar feature in this repo and name
   it — that is your pattern reference.
3. Implement the slice end to end: input validation, the behavior, error paths, and tests.
4. Run build, tests, and lint. Fix what you broke.

**Constraints**:
- Touch the minimum set of files. No drive-by refactors, no new dependencies.
- Follow the security and testing instructions that apply to the files you touch.
- If any acceptance criterion cannot be met, say which and why — do not silently narrow scope.

**Output**: The changed files, then a summary containing: acceptance criteria with
pass/fail, the pattern reference you followed, the test evidence (command + result),
and anything you deliberately left out.

**Reference**: ${input:reference:Path to the closest existing implementation, e.g. src/orders/}
