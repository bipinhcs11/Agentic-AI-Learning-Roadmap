# 04 — Custom Agents: Packaged Roles with Scoped Tools

A custom agent (`.github/agents/*.agent.md`, surfaced in VS Code's mode/agent picker —
the evolution of "chat modes") is a persistent persona: its own instructions, its own
**tool allowlist**, optionally its own model. Where a prompt file is a *procedure you
invoke*, an agent is a *role you switch into* for a whole conversation.

## Why enterprises care: the tool allowlist

The frontmatter is a permission boundary, not decoration:

```markdown
---
description: "Read-only security reviewer — finds and ranks, never edits"
tools: ["search", "usages", "problems", "changes"]
---
```

The [starter kit's security reviewer](../copilot_starter_kit/.github/agents/security-reviewer.agent.md)
*cannot* edit files — not "is instructed not to", **cannot**: `editFiles` and
`runCommands` are absent from its tool list. This is the difference between asking a
model to behave and removing the capability. In a regulated org, that distinction is
the difference between "AI reviewed the code" being an audit statement or a hope.

The three starter-kit agents demonstrate the pattern:

| Agent | Tools granted | Hard boundary |
|---|---|---|
| `security-reviewer` | search, usages, problems, changes | Read-only; ranks findings, never edits |
| `test-engineer` | + editFiles, runCommands, testFailure | Edits **test files only**; never production code |
| `legacy-navigator` | search, usages, problems | Read-only; explains and maps blast radius |

For agents with real operational teeth — the kind an SRE or lead actually reaches
for during an incident or at sprint refinement — see
[`examples/agents/`](../examples/agents/): a **production-issue analyzer** that
reads the attached log, classifies the failure signature, and routes to a
specialist; a **transaction-timeout analyst** that distinguishes pool exhaustion
from downstream latency from missing timeouts from GC from lock contention (and
tells you which modes it ruled out and why); and a **work-item analyst** that turns
a Jira/ADO item into an implementation-readiness report with testability grades,
blast radius, and slicing. Those files are the difference between an agent as a
persona and an agent as a *procedure with judgment*.

## Designing an agent worth having

1. **Start from a recurring conversation, not an org chart.** If your team keeps having
   the "is this safe to change?" conversation, that's `legacy-navigator`. Nobody needs
   a "Java Agent".
2. **Write the refusals first.** The "What you refuse" section is what makes an agent
   trustworthy — an agent that does anything is just chat with a costume.
3. **Give it a verdict format.** The security reviewer's severity/file:line/OWASP/
   scenario/fix table is what makes its output *comparable across runs* — which is what
   makes it usable in process.
4. **Scope tools to the minimum.** Every tool you grant is something a prompt injection
   in reviewed code could try to use (see [chapter 05](05_skills_and_hooks.md) for the
   deterministic backstop).

## Agents vs prompt files vs instructions — one decision rule

- Rule that always applies → **instruction**
- Procedure invoked on demand, ends with the answer → **prompt file**
- Role with different *permissions* than default, holding a whole conversation →
  **agent**

Most things people first build as agents should have been prompt files. Build the
agent when the tool boundary or the persistent persona is doing real work.

## Distribution at enterprise scale

Same as everything in this blueprint: agents are files, so they ship with repos —
`git pull` is the update mechanism. The community pattern to copy is
[github/awesome-copilot](https://github.com/github/awesome-copilot): a searchable
catalog of agents/instructions/prompts, with **collections/plugins** bundling related
items per workflow. A platform team's internal fork of that catalog — curated,
security-reviewed, versioned — is the mature end-state; individual developers
hand-rolling personas in every repo is the immature one.
