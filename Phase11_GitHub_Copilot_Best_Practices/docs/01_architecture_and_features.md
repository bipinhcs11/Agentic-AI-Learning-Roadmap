# 01 — Copilot Architecture & the Features Enterprise Developers Actually Need

Most enterprise developers use ~20% of Copilot: ghost-text completions and the occasional
chat question. The productivity gap between teams is almost entirely in the other 80%.
This chapter is the feature map — what exists, when to reach for it, and what changes
inside a locked-down enterprise.

## The three interaction surfaces

| Surface | What it is | Right-sized task |
|---|---|---|
| **Completions + Next Edit Suggestions (NES)** | Ghost text while typing; NES proposes the *next* related edit across the file after you make one change (rename a param → it offers the call-site updates). | Line-to-function scale. You stay the author. |
| **Chat: Ask / Edit** | Ask = questions, explanations, plans — no file changes. Edit = scoped multi-file edits you review hunk by hunk. | "Explain this", "change these 3 files this way". |
| **Chat: Agent mode** | Copilot plans, edits, runs terminal commands, reads failures, iterates — until build/test pass. Governed by your instructions files and hooks. | A small verifiable feature slice, a test-fix loop, a mechanical migration. |

In IntelliJ IDEA, **Ask**, **Edit**, and **Agent** cover the same decision pattern:
Ask to understand without changing files, Edit when you want to choose the working set
and accept/reject edits, and Agent when Copilot may discover files and iterate with tools.
The labels and exact UI can move between plugin versions, but the risk boundary does not.
See the [IntelliJ + VS Code playbook](11_intellij_vscode_enterprise_playbook.md).

The discipline that makes agent mode safe is the same one in this repo's
[starter kit](../copilot_starter_kit/): committed instructions + small tasks +
build/test/lint as the definition of done.

## Beyond the editor

- **Copilot code review** — request a review from Copilot on a PR like a human reviewer;
  it reads the diff against your repo instructions. Treat it as a fast first pass that
  frees humans for design-level review — never as the approval.
- **Copilot coding agent** — assign a GitHub *issue* to Copilot; it works in an isolated
  cloud environment (Actions), opens a draft PR, responds to review comments. In
  regulated orgs this is gated by policy; know whether yours allows it before demoing it.
- **Copilot CLI / terminal assist** — command suggestion and explanation in the shell.
- **Commit message & PR description generation** — worth standardizing via the
  workspace settings (see the starter kit's `.vscode/settings.json`).
- **JetBrains IDEs** — IntelliJ IDEA developers have completions, inline/chat flows,
  Ask/Edit/Agent workflows, code review, MCP, and a Customizations editor. Several
  repository customization types remain preview features or differ from VS Code;
  consult GitHub's current [customization support matrix](https://docs.github.com/en/copilot/reference/customization-cheat-sheet)
  before making one a mandatory control.
- **Copilot for Xcode** — retained in this roadmap for Swift/Objective-C teams but
  outside the Spring Boot, Angular, and React learning path requested here.

## Feeding it context (the part most developers skip)

Copilot's answer quality tracks the context you attach, in this order of power:

1. **`#file` / drag a file into chat** — precise, cheap, the default move.
2. **`#codebase` / `@workspace`** — semantic search over the repo index; use for
   "where is X handled?" questions, not as a substitute for attaching the file you
   already know matters.
3. **Selection** — highlight code, then ask; the selection is the context.
4. **`#changes`** — the current diff; the input for review prompts.
5. **`#terminalLastCommand` / `#testFailure`** — pipe the actual failure in instead of
   paraphrasing it.
6. **Committed instruction files** — the always-on layer; see
   [chapter 02](02_custom_instructions.md).

Anti-pattern: pasting 500 lines into chat when `#file` would attach it with structure
intact. Second anti-pattern: attaching 20 files "for context" — irrelevant context
actively degrades output (see [chapter 07](07_model_selection_and_context.md)).

## What's different inside a regulated enterprise

- **The model list is curated.** The model picker shows what your org enabled, not
  what the marketing page shows. Chapter 07 covers choosing among what you have.
- **Content exclusion is surface-dependent.** Exclusions can keep configured content
  out of supported Copilot features, but GitHub documents important exceptions:
  Copilot coding agent and IDE Agent mode do not support content exclusion. Never use
  exclusion as the only control protecting secrets or restricted source. Confirm the
  current behavior for the exact IDE surface before enabling Agent mode; see
  [GitHub's content-exclusion documentation](https://docs.github.com/en/copilot/how-tos/configure-content-exclusion/exclude-content-from-copilot).
- **Public-code matching is typically set to block**, so occasionally a completion
  is suppressed; that's the filter working, not Copilot failing.
- **Feedback loops route internally.** "Copilot gave a bad answer" goes to your
  platform team, who fix it by improving the *committed instruction files* — that is
  the whole point of the blueprint: bad answers become PRs against `.github/`.

## The habit that compounds

> Completions make you faster at what you were already typing.
> **Committed customization makes the whole org faster at what it was already deciding.**

Every chapter after this one is about moving knowledge from heads and wikis into the
files Copilot actually reads.
