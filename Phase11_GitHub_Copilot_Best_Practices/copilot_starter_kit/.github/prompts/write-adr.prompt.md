---
mode: ask
description: "Write an Architecture Decision Record for a decision just made in this repo"
---

# /write-adr

**Role**: You are the engineer documenting a decision for the person who will curse it
in three years — give them the context to curse accurately.

**Context**: Decision to record: ${input:decision:One sentence — what was decided}.
Use the conversation so far and the current diff as evidence of what was considered.

**Task**: Produce one ADR in the repo's existing ADR format (look in `docs/adr/` or
`doc/architecture/`; if none exists, use the standard: Status / Context / Decision /
Consequences).

**Constraints**:
- Context states the forces honestly, including the constraint that actually drove
  the decision (deadline, policy, team skill) — not a retrofitted technical story.
- List the alternatives that were genuinely considered and the one-line reason each
  lost. Two alternatives minimum; "do nothing" counts.
- Consequences include the negative ones. An ADR with only upsides is marketing.
- One page maximum.

**Output**: The ADR file, numbered to follow the existing sequence, ready to commit.

**Reference**: Existing ADRs in this repo; match their tone and depth.
