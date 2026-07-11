---
description: "How Copilot should behave when reviewing code in this repo"
applyTo: "**"
---

# Code review instructions

When reviewing a diff (Copilot code review on a PR, or `/security-pr-review` in chat):

- Rank findings by severity and lead with the worst. A real injection risk buried
  under twelve naming nitpicks is a failed review.
- Cite the rule, not taste: reference the specific OWASP category, the repo instruction,
  or the existing pattern being violated. "Looks fine to me" and "consider maybe
  possibly" are both banned phrases.
- For each finding give: **where** (file:line), **what** (the defect), **why it matters**
  (the failure scenario), and **the fix** (concrete, minimal).
- Check what the diff does NOT contain: missing tests for new branches, missing
  authorization on new endpoints, missing error handling on new I/O.
- Flag scope creep — changes unrelated to the stated purpose of the PR.
- Do not request changes for style the linter already enforces; the linter is the
  authority on formatting.
- If the diff is too large to review meaningfully (> ~400 changed lines), say so and
  suggest a split before anything else.
