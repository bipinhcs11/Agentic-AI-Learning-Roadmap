# 02 — Custom Instructions: the Always-On Layer

Custom instructions are the highest-leverage Copilot feature in an enterprise, because
they are the only layer that works **without the developer doing anything**. A prompt
file helps the developer who invokes it; instructions help the intern who doesn't know
they exist.

## The three files and when each applies

| File | Scope | When it's injected |
|---|---|---|
| `.github/copilot-instructions.md` | Whole repo | Every chat/agent request in this workspace |
| `.github/instructions/*.instructions.md` | Paths matched by `applyTo` frontmatter | Requests touching matching files |
| `AGENTS.md` (repo root) | Whole repo, tool-agnostic | Read by Copilot agent mode/coding agent — and by other AI agents, so it's the portability layer |

Path-scoped example (from the [starter kit](../copilot_starter_kit/.github/instructions/testing.instructions.md)):

```markdown
---
description: "Rules for generating and modifying tests, any framework"
applyTo: "**/{test,tests,__tests__,spec}/**,**/*{Test,Tests,.test,.spec}.*"
---
```

This is how you keep the always-on file short: repo-wide truths in
`copilot-instructions.md`, everything conditional pushed down into scoped files.

## What belongs in `copilot-instructions.md`

Exactly four things — the starter kit template enforces this shape:

1. **What the project is** — 3–5 lines, because Copilot cannot infer intent from file names.
2. **Architecture in five lines** — only the rules that survive code review
   ("domain/ has no framework imports"), not an essay.
3. **Build / test / lint commands** — verbatim. This is what lets agent mode
   self-verify instead of declaring victory on unbuilt code.
4. **Universal rules** — the 5–10 non-negotiables: no secrets, no new dependencies
   silently, tests required, no drive-by refactors.

## What does NOT belong (the expensive mistakes)

- **Formatting rules the linter enforces.** The linter is deterministic and free;
  instructions are probabilistic and cost context on every request.
- **Anything secret or internal** — hostnames, ticket URLs with auth, team rosters.
  Instructions travel with every request and every fork.
- **Novels.** Past ~60 lines, each marginal line dilutes the others. If your
  instructions file scrolls, it's a docs page wearing an instructions costume.
- **Stale commands.** An instructions file that says `./gradlew build` after the repo
  moved to Maven makes every agent session start with a lie. Treat drift here like a
  broken build.

## The enterprise pattern: instructions as governed artifacts

What separates a Fortune-100 rollout from a hobbyist setup is not the file content —
it's the lifecycle:

- **Ownership**: `.github/copilot-instructions.md` and `.github/instructions/` are in
  `CODEOWNERS`, owned by the platform/enablement team plus a senior engineer per repo.
- **Review**: instruction changes are behavior changes for every developer in the repo.
  They get PR review, not direct pushes.
- **Templates with overlays**: the org publishes a generic base (like this starter kit);
  each stack adds scoped `*.instructions.md` overlays (like [`../stacks/`](../stacks/)).
  Base changes propagate org-wide; stack teams own only their delta.
- **Feedback loop**: recurring bad Copilot output → issue → PR against the instructions →
  merged → fixed for everyone. This converts prompt folklore into infrastructure.

## Verifying instructions are actually loaded

In VS Code chat, expand the request's context/references list — the instruction files
in effect are listed there. When output ignores a rule, check (in order): is the file
listed at all → does the `applyTo` glob match the file being edited → is the rule
contradicted by a longer, more specific instruction elsewhere → is the file so long
the rule is buried.

## Relationship to CLAUDE.md and other agent files

`AGENTS.md` is emerging as the cross-tool standard; Copilot reads it alongside its own
files. The pragmatic enterprise policy: **one source of truth** — keep the tool-agnostic
contract in `AGENTS.md`, keep Copilot-specific detail in `.github/copilot-instructions.md`,
and state in both that the other exists. Duplicated content drifts; drifted instructions
are worse than none.
