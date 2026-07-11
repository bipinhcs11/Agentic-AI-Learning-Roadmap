# 10 — The VS Code Agent Customizations Panel, Section by Section

VS Code ships a UI for everything this blueprint describes: the **Agent
Customizations** editor (reachable from the Chat view / Agents window; there's a
matching "Agent Customizations for Copilot CLI" view). Its left nav is the
definitive map of the customization surface:

> **Overview · Agents · Skills · Instructions · Hooks · MCP Servers · Plugins · Tools**

This chapter follows that panel top-to-bottom — for each section: what it shows,
the file that backs it, what this repo ships for it, and what you should *see*
in the panel when it's working. Treat the panel as the runtime view and the
`.github/` folder as the source code of the same thing.

## Overview

**What it shows:** everything currently loaded for this workspace, in one place.

**Use it as your verification surface.** The most common enterprise support ticket
("Copilot ignores our rules") is diagnosed here in ten seconds: if the file isn't
listed, it isn't loaded — wrong path, wrong extension, or you're in a subfolder of
a monorepo (enable `chat.useCustomizationsInParentRepositories` for parent-repo
discovery).

⚠️ **Why your panel says "No agents yet" for this repo:** the starter kit lives at
`Phase11_GitHub_Copilot_Best_Practices/copilot_starter_kit/.github/` — a *template
to copy*, not this repo's live root config. Copy it to a real repo's root (or a
scratch repo) and the panel populates: 3 agents, 1 skill, 3 instruction files, and
the prompts appear under `/`. That copy-then-look loop is also the best 10-minute
demo when you pitch this setup to a team.

## Agents

**Backing files:** `.github/agents/*.agent.md` (workspace) — personal agents can
also live in your user profile; workspace wins for team consistency.

**This repo ships:** three generic agents in the
[starter kit](../copilot_starter_kit/.github/agents/security-reviewer.agent.md)
(security-reviewer, test-engineer, legacy-navigator) and three operational ones in
[`examples/agents/`](../examples/agents/production-issue-analyzer.agent.md)
(production-issue-analyzer, transaction-timeout-analyst, work-item-analyst).

**In the panel:** each agent appears with its description; **New Agent (Workspace)**
scaffolds the file for you — fine for drafting, but in an enterprise the agent file
still merges via PR like any other code. Full guidance: [chapter 04](04_custom_agents.md).

## Skills

**Backing files:** `.github/skills/<name>/SKILL.md` plus bundled assets in the folder.

**This repo ships:** [`dependency-audit`](../copilot_starter_kit/.github/skills/dependency-audit/SKILL.md).
For generating skills at codebase scale instead of hand-writing them, see
[Skill_Generator](https://github.com/bipinhcs11/Skill_Generator) and
[addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) —
covered in [chapter 05](05_skills_and_hooks.md).

**In the panel:** skills list with their trigger descriptions. If a skill never
fires, the description is the first thing to fix — it's the matching condition.

## Instructions

**Backing files:** `.github/copilot-instructions.md` (always-on),
`.github/instructions/*.instructions.md` (path-scoped via `applyTo`), `AGENTS.md`
(tool-agnostic root contract).

**This repo ships:** the starter kit trio (security / testing / code-review) plus
five *filled-in* real-world examples in
[`examples/copilot_instructions/`](../examples/copilot_instructions/) —
payments microservice, banking portal, ops dashboard, iOS app, batch platform.

**In the panel:** every instructions file in effect, with its scope. If a rule is
being ignored, check here first — then check the `applyTo` glob, then file length.
Full guidance: [chapter 02](02_custom_instructions.md).

## Hooks

**Backing files:** `.github/hooks/<name>/hooks.json` + the script it wires
(events: `sessionStart`, `sessionEnd`, `preToolUse`, `postToolUse`; non-zero exit
blocks the action).

**This repo ships:** the tested, PCI-aware
[`security-scan`](../examples/hooks/security-scan/) hook.

**In the panel:** registered hooks per event. This is also where an auditor can be
*shown* that the guardrail exists and what it's wired to — a screenshot of this
section belongs in your control evidence. Full guidance: [chapter 05](05_skills_and_hooks.md).

## MCP Servers

**Backing files:** `.vscode/mcp.json` (workspace) — org policy controls what's
allowed to appear here at all.

**This repo ships:** a placeholder-only
[`mcp.json`](../copilot_starter_kit/.vscode/mcp.json) showing the three archetypes
(vendor HTTP server, internal gateway, local stdio).

**In the panel:** each server with connection state and the tools it contributes.
Your screenshot showing `MCP Servers: 1` is the point of the section — you can
enumerate exactly what external reach this workspace has. If the count surprises
you, that's a finding. Full guidance: [chapter 06](06_mcp_enterprise.md).

## Plugins

**What they are:** installable bundles of agents + skills for a workflow —
`copilot plugin install <name>@awesome-copilot` pulls from a marketplace like
[github/awesome-copilot](https://github.com/github/awesome-copilot)'s catalog.

**Enterprise stance:** plugins are the *distribution* mechanism, and distribution
is a governance decision. The mature pattern is an **internal plugin
catalog** — your platform team forks/curates the community catalog, security
reviews each bundle, and developers install from that registry only (same
allowlist logic as MCP servers). This repo's starter kit + one stack overlay is
exactly the content you'd package as your org's first internal plugin.

**In the panel:** installed plugins and what they brought in. Anything listed here
that nobody can name the reviewer for is your shadow-AI surface inside the
sanctioned tool.

## Tools

**What it shows:** the flat registry of everything agents can *do* — built-in
tools (edit files, run commands, search, fetch) plus every tool contributed by
connected MCP servers. Your screenshot's `Tools: 8` is this inventory.

**Why enterprises should read this section weekly:**

- The `tools:` allowlist in every `.agent.md` frontmatter refers to names from
  **this registry** — this panel is where you look up what's grantable, and what
  a tool actually is before you grant it.
- Tools can be enabled/disabled here per workspace. The enterprise default:
  everything an agent doesn't need is off, and the risky ones (arbitrary fetch,
  command execution) are guarded by hooks even when on
  ([chapter 05](05_skills_and_hooks.md)) — disable is policy, hooks are enforcement.
- After adding an MCP server, come here and read what it *actually* contributed —
  tool-count drift after a server "update" is the rug-pull signal
  ([chapter 06](06_mcp_enterprise.md)).

## The one-line summary

The panel is the same blueprint in runtime form: **Agents, Skills, Instructions,
Hooks, MCP Servers, Plugins, Tools — seven sections, seven file conventions, one
`.github/` folder under code review.** If you can't find something in the panel,
it isn't governing anything; if you can't find its file in git, it isn't governed.
