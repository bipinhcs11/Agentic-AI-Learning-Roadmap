# Copilot Starter Kit — generic, stack-agnostic

Copy this folder's `.github/` and `.vscode/` into the root of any repository and you have
the full Copilot customization stack: always-on instructions, path-scoped rules, reusable
prompts, custom agents, one example skill, and an MCP config with safe placeholders.

Nothing in here assumes a language or framework. Stack specifics live in
[`../stacks/`](../stacks/) as overlays — a Spring Boot team adds the Java files, an iOS
team adds the Swift files, and this kit stays identical underneath.

## What's inside

```
.github/
├── copilot-instructions.md            ← always-on repo rules (fill in the TODOs)
├── instructions/
│   ├── security.instructions.md       ← applies to all source files
│   ├── testing.instructions.md        ← applies to test files
│   └── code-review.instructions.md    ← applies during review flows
├── prompts/                           ← type "/" in chat to invoke these
│   ├── implement-feature.prompt.md
│   ├── generate-unit-tests.prompt.md
│   ├── security-pr-review.prompt.md
│   ├── refactor-legacy.prompt.md
│   └── write-adr.prompt.md
├── agents/                            ← custom agents (chat modes)
│   ├── security-reviewer.agent.md
│   ├── test-engineer.agent.md
│   └── legacy-navigator.agent.md
└── skills/
    └── dependency-audit/SKILL.md      ← example bundled skill
.vscode/
├── mcp.json                           ← approved MCP servers (placeholders only)
└── settings.json                      ← Copilot-relevant workspace settings
AGENTS.md                              ← root agent contract (works across AI tools)
```

## Adoption checklist for a platform team

1. **Fill in the TODOs** in `copilot-instructions.md` — build command, test command,
   architecture summary. Copilot is only as good as these five lines.
2. **Protect the folder.** Add `.github/copilot-instructions.md`, `.github/prompts/` and
   `.github/agents/` to `CODEOWNERS`. Prompt changes are behavior changes — review them.
3. **Start with three prompts, not thirty.** Adoption dies when the `/` menu is noise.
4. **Keep instructions short.** Instructions are injected into every request; every line
   costs context window on every single chat. If it isn't a rule you'd flag in code
   review, it doesn't belong in the always-on file.
5. **Never put secrets or internal hostnames** in any of these files. They travel with
   every Copilot request and with every fork of the repo.

## The 6-part prompt shape

Every prompt file in this kit follows the same structure (introduced in Part 2 of the
series), which is what makes them reviewable and consistent:

| Section | Purpose |
|---|---|
| **Role** | Who Copilot is for this task ("senior backend engineer on a regulated platform") |
| **Context** | What it must know: architecture, versions, constraints that always apply |
| **Task** | The specific, *small*, verifiable unit of work |
| **Constraints** | The non-negotiables: security, style, what NOT to do |
| **Output** | Exact shape of the answer: files, format, tests included or not |
| **Reference** | A file, folder, or repo that shows what "good" looks like here |

The single highest-leverage habit: **always point at a reference implementation.**
"Follow the pattern in `src/orders/`" outperforms three paragraphs of description.
