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

Two references that show where the skills layer is heading:

- **[addyosmani/agent-skills](https://github.com/addyosmani/agent-skills)** (~77k
  stars) — production-grade engineering skills for AI coding agents; study it for
  how senior-engineer checklists become skill content.
- **[bipinhcs11/Skill_Generator](https://github.com/bipinhcs11/Skill_Generator)** —
  hand-writing skills doesn't scale to a 500-repo enterprise; this generator walks a
  Java repository and produces feature-based `SKILL.md` files through a four-role
  agent pipeline (Generator → Tracker → Updater → Validator), each skill carrying
  `confidence` and `review_required` frontmatter plus `depends_on`/`depended_on_by`
  metadata so PR-impact detection can propagate updates. That is the industrial
  pattern: skills as *generated, reviewed, dependency-tracked artifacts* — with
  deterministic code confined to structural validation and semantic judgment left
  to the agent.

## Hooks

Hooks run **your commands** at fixed points in an agent session — and can block the
action. They are deterministic: grep does not get persuaded.

The concrete format (as used across the hooks in
[github/awesome-copilot](https://github.com/github/awesome-copilot/tree/main/hooks)):
a folder under `.github/hooks/<name>/` containing a `hooks.json` plus the script it
wires. Events include `sessionStart`, `sessionEnd`, `preToolUse`, and `postToolUse`;
the script receives the tool invocation as JSON on stdin (`toolName`, `toolInput`)
and **a non-zero exit blocks the action**:

```jsonc
// .github/hooks/security-scan/hooks.json
{
  "version": 1,
  "hooks": {
    "postToolUse": [
      { "type": "command",
        "bash": ".github/hooks/security-scan/scan-changed-files.sh",
        "cwd": ".",
        "env": { "SCAN_MODE": "block", "SCAN_SCOPE": "diff" },
        "timeoutSec": 30 }
    ]
  }
}
```

A complete, tested implementation lives in this phase:
[`examples/hooks/security-scan/`](../examples/hooks/security-scan/) — a PCI-aware
scan (secrets, card numbers outside the approved test range, internal hostnames,
curl-pipe-shell) that runs after every edit and again at session end, logs redacted
JSONL findings for SIEM pickup, and blocks in `SCAN_MODE=block`.

The canonical enterprise trio:

| Hook point | Enforcement |
|---|---|
| `preToolUse` | Block edits to `.github/workflows/`, `CODEOWNERS`, migration files; command allowlist — build/test/lint run, `curl \| sh`, package publishes, `git push --force` are refused mechanically (see awesome-copilot's `tool-guardian`) |
| `postToolUse` | Secret/PCI scan + lint the touched files immediately, so violations die in-session, not in CI 20 minutes later (see `examples/hooks/security-scan/`) |
| `sessionEnd` | Final scan of everything the session changed — the backstop (see awesome-copilot's `secrets-scanner`) |

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
