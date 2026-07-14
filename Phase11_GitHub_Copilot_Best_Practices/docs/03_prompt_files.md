# 03 — Prompt Files: Reusable Prompts as Code

A `.prompt.md` file in `.github/prompts/` becomes a slash command in VS Code chat:
type `/implement-feature` and the whole engineered prompt runs with your input spliced
in. This is the feature that turns "our senior engineer prompts well" into
"our repo prompts well."

## Anatomy

```markdown
---
mode: agent            # ask | edit | agent — which surface runs it
description: "Implement one small, verifiable feature slice"
---

**Role**: ...
**Context**: ... ${input:feature:Describe the feature slice}
**Task**: ...
**Constraints**: ...
**Output**: ...
**Reference**: ${input:reference:Path to the pattern to follow}
```

- `mode` pins the right surface — review prompts run as `ask` (no edits possible),
  implementation prompts as `agent`.
- `${input:name:placeholder}` prompts the developer for the variable parts.
- `${file}` / `${selection}` splice in the current editor state.

## The 6-part shape (from Part 2 of this series)

Every prompt in this phase uses **Role → Context → Task → Constraints → Output →
Reference**. The shape isn't ceremony — each section kills a specific failure mode:

| Section | Failure it prevents |
|---|---|
| Role | Generic-tutorial voice, wrong seniority of solution |
| Context | Guessing at versions, architecture, domain |
| Task | Sprawling, unverifiable output |
| Constraints | The ten "enterprise-grade" decisions left to chance — auth, validation, error contract, dependencies |
| Output | Unusable format; missing tests; missing evidence |
| Reference | Inventing a pattern the repo doesn't use |

The **Reference** line is the one most teams skip and the one that matters most:
pointing at `src/orders/` beats describing `src/orders/` in three paragraphs.

## Library design: why the starter kit ships five prompts, not fifty

The `/` menu is a shared namespace. Curate it like a public API:

- **Coverage beats count.** Five prompts covering implement / test / review / refactor /
  document handle ~90% of daily work. The Part-2 "25 prompts" list is a *catalog* teams
  pull from — no single repo should install all 25.
- **Generic core + stack overlay.** The starter kit's prompts are stack-agnostic; the
  flagship OWASP REST API prompt lives in the
  [Java overlay](../stacks/java_springboot_microservices/), the Signals prompt in the
  [Angular overlay](../stacks/angular/). Same discipline as instructions.
- **Names are verbs**: `/implement-feature`, `/generate-unit-tests`. A prompt named
  `/helper2` will be invoked exactly once, by its author.
- **Prompts get PR review.** A prompt that says "add rate limiting" ships rate limiting
  into every API this repo generates. That's a design decision; review it like one.

## Prompt files vs instructions — the boundary

| | Instructions | Prompt files |
|---|---|---|
| Trigger | Automatic, always | Developer invokes deliberately |
| Content | Rules ("never log PII") | Procedures ("implement a feature this way") |
| Failure smell | Prompt-like content ("first do X then Y") in instructions | Rule-like content duplicated per prompt |

If you find the same constraint pasted into four prompt files, it's an instruction.
If your instructions file contains a step-by-step recipe, it's a prompt file.

## Measuring whether it's working

Cheap, honest signals — no dashboard required:

- Do PRs authored with `/implement-feature` include the acceptance-criteria summary
  the prompt demands? (If not, developers are bypassing the prompt — ask why.)
- Time from "bad Copilot output" to "merged prompt/instruction fix" — this is your
  real enablement velocity.
- Ratio of prompt invocations to raw freehand chat for standardizable tasks —
  rising ratio means the library earns its place; flat means the prompts are worse
  than freehand, and the fix is editing the prompts, not mandating their use.
