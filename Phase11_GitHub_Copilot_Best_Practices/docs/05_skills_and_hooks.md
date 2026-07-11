# 05 — Skills & Hooks: Auto-Loading Capabilities and Deterministic Guardrails

These are the two newest layers of the customization stack, and they answer the two
questions the other layers can't:

- **Skills**: "how do I give Copilot a capability *with materials*, loaded only when
  relevant?"
- **Hooks**: "how do I enforce a rule even when the model ignores its instructions?"

## Skills

A skill is a folder with a `SKILL.md` (name + description frontmatter, then the
procedure) plus any bundled assets — scripts, templates, checklists. Copilot loads it
**automatically when the task matches the description**, unlike a prompt file which
waits to be invoked.

```
.github/skills/
└── dependency-audit/
    └── SKILL.md    ← "Use when adding, upgrading, or reviewing a dependency..."
```

The [starter-kit example](../copilot_starter_kit/.github/skills/dependency-audit/SKILL.md)
fires whenever a task involves adding a dependency — the developer never asks for it,
which is precisely the point: **the process step that's easy to forget is the one that
should auto-load.**

Design rules that keep skills useful:

- **The description is the trigger.** Write it like a matching condition ("Use when…"),
  not a title. Vague description = skill that never fires or always fires.
- **Progressive disclosure**: `SKILL.md` stays short; deep material goes in companion
  files inside the folder that the agent reads only when needed. Skills don't tax the
  context window until they're relevant — that's their advantage over instructions.
- **Skills carry process, instructions carry rules.** "No floating versions" is an
  instruction; "here is the 6-step audit with an output template" is a skill.
- Good enterprise candidates: dependency audit, incident-postmortem format, release
  checklist, data-classification handling, accessibility audit.

## Hooks

Hooks run **your commands** at fixed points in an agent session (session start/end,
before/after each tool use) — and can block the action. They are deterministic:
grep does not get persuaded.

The canonical enterprise trio:

| Hook point | Enforcement |
|---|---|
| Before file edit | Block edits to `.github/workflows/`, `CODEOWNERS`, migration files — protected paths stay protected even if the model is convinced otherwise |
| Before terminal command | Allowlist: build/test/lint commands run; `curl` to arbitrary hosts, package publishes, `git push --force` are refused mechanically |
| After file edit | Secret scan + lint the touched files immediately, so violations die in-session, not in CI 20 minutes later |

Why this matters more in an enterprise: agent mode reads repo content — code comments,
README files, test fixtures. A malicious or compromised dependency README saying
"run this command" is a **prompt injection** vector. Instructions ask the model to be
careful; hooks make classes of outcome impossible. Auditors accept "the tool cannot do
X"; they correctly reject "the tool was told not to X."

## The complete decision table (chapters 02–05 in one view)

| You want to… | Use |
|---|---|
| State a rule that always applies to these files | `*.instructions.md` |
| Package a procedure a developer runs on demand | `.prompt.md` |
| Create a role with restricted tools/permissions | `.agent.md` |
| Auto-load a process + materials when a task matches | Skill |
| Enforce a boundary regardless of what the model thinks | Hook |

Read the table bottom-up for trust: hooks are the only layer whose guarantee doesn't
depend on the model. Everything above them is steering; hooks are the rails.
