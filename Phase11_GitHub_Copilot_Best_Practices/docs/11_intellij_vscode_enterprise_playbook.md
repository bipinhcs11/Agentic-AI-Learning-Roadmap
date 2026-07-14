# 11 — IntelliJ + VS Code Enterprise Playbook

This chapter is for enterprise developers who know IntelliJ IDEA or VS Code but have
never used Claude Code, Cursor, or another terminal-first coding agent. No knowledge of
those tools is required. GitHub Copilot stays inside the normal engineering loop:
understand the ticket, inspect code, propose a bounded change, review the diff, run the
same tests, and open a pull request.

> **Last support check:** July 12, 2026. Copilot IDE capabilities change frequently.
> Recheck GitHub's official [customization cheat sheet](https://docs.github.com/en/copilot/reference/customization-cheat-sheet)
> and your enterprise policy before declaring a preview feature part of a control.

## Start with the interaction mode, not the model

| Need | Use | Developer remains responsible for |
|---|---|---|
| Explain a call path, test failure, or unfamiliar module | **Ask** | Supplying the relevant files and checking the explanation against code |
| Change a known set of two or three files | **Edit** | Choosing the working set and accepting/rejecting every file diff |
| Implement a small feature whose files must be discovered | **Agent** | Approving tools/commands, watching scope, reviewing all changes, running gates |
| Complete a well-specified backlog item asynchronously | **Coding agent**, only if enabled | Issue quality, draft-PR review, CI, human approval |
| Get a fast first review of a local/PR diff | **Copilot code review** | Treating findings as advice, not approval |

Do not begin with Agent mode merely because it is the newest option. A controller rename
in two known files is an Edit task. Understanding a transaction boundary is an Ask task.
Agent mode earns its wider authority only when file discovery or a test-fix loop is part
of the work.

## What is shared and what differs by IDE

The safest cross-IDE baseline is deliberately small: a repository-wide
`.github/copilot-instructions.md`, bounded prompts written in normal chat when necessary,
human-reviewed diffs, repository build/test/lint commands, and normal pull-request gates.

GitHub's current support matrix describes the following. A check mark is generally
available, **Preview** may require enterprise policy/preview enablement, and unsupported
means the workflow needs a CI or manual fallback.

| Capability | VS Code | JetBrains / IntelliJ IDEA | Enterprise use |
|---|---:|---:|---|
| Repository custom instructions | Supported | Preview/support varies by instruction type | Keep the short repo contract in `.github/copilot-instructions.md`; verify it appears in response References |
| Prompt files | Supported | Preview | Repeated tasks such as test generation or a secure endpoint checklist |
| Custom agents | Supported | Preview | Read-only planner, security reviewer, test specialist |
| Agent skills | Supported | Preview | On-demand workflows with scripts/reference material |
| Hooks | Preview | Not supported | Never make an IntelliJ control depend on a hook; enforce the same rule in pre-commit/CI |
| MCP servers | Supported | Supported | Approved read-only documentation, work-item, or observability access |
| Ask/Edit/Agent chat workflow | Supported | Supported | Day-to-day local development |
| Copilot code review | Supported | Supported | Advisory first-pass review before human approval |

The key architecture decision is therefore: **instructions steer, IDE features assist,
and CI enforces**. If a hook blocks secrets in VS Code, secret scanning must still block
the same content in CI for IntelliJ developers and for non-Copilot commits.

## IntelliJ IDEA: first-day setup for Spring Boot developers

1. Install the organization-approved GitHub Copilot plugin version and authenticate with
   the enterprise-managed GitHub identity—not a personal account.
2. Open Copilot Chat from the Copilot tool window. Confirm which modes your policy
   exposes. A missing Agent option can be an administrator policy, not a broken plugin.
3. Open Chat settings → **Customizations**. Inspect workspace and personal items. Do not
   silently recreate a blocked workspace customization as a personal customization.
4. Ask: `Summarize this service's architecture and list the exact build, test, and lint
   commands. Cite the repository files used.` Expand **References** and confirm that
   `.github/copilot-instructions.md` was applied.
5. Highlight one service method and use inline chat to explain its transaction boundary.
   This teaches selection-scoped context without granting edit authority.
6. Use Edit on a disposable documentation/test-only change. Add only the intended files
   to the working set and practice Accept/Discard per file.
7. Use Agent only on a bounded story with explicit acceptance criteria and commands.
   Inspect each requested terminal command; never approve a broad or destructive command
   because it came from the sanctioned tool.
8. Compare IntelliJ's Git diff with the original task before creating a PR. IDE green
   checks do not replace Maven/Gradle, security scans, or CI.

For the current UI flow, see GitHub's official
[Copilot Chat in JetBrains IDEs](https://docs.github.com/en/copilot/how-tos/chat-with-copilot/chat-in-ide?tool=jetbrains).

## VS Code: first-day setup for Angular and React developers

1. Install the enterprise-approved GitHub Copilot extensions and sign in with the managed
   identity. Open the repository at its real root so `.github/` is discoverable.
2. Run **Chat: Open Customizations**. Review Instructions, Prompts, Agents, Skills,
   Hooks, MCP Servers, and Tools. An unfamiliar tool or server is a finding to resolve.
3. Ask the same architecture/build-command question used above and verify References.
4. Type `/` in chat to inspect team prompt files. Run a review-only prompt before an
   implementation prompt so the difference between advice and file mutation is visible.
5. Select a component and ask for its data-flow and accessibility risks. Then use Edit
   with the component and its test as the explicit working set.
6. Before Agent mode, inspect tool permissions. Terminal and MCP write tools should be
   enabled only when the task requires them.
7. Review Source Control file-by-file, run the repository's lint/type/test commands, and
   request human review through the normal PR process.

See [chapter 10](10_vscode_customizations_panel.md) for the VS Code panel walkthrough.

## The enterprise prompt contract

A useful request answers six questions. This works in either IDE even when prompt files
are unavailable:

```text
Role: Act as a senior engineer in this repository.
Context: Work item ABC-123. Relevant files: <paths>. Follow repository instructions.
Task: Implement one <specific behavior>; do not change unrelated behavior.
Constraints: No new dependency, no sensitive data, preserve API compatibility,
             use the existing <named pattern>.
Validation: Run <exact focused tests> and <lint/type/build command>.
Output: Show changed files, assumptions, test evidence, and remaining risks.
```

Weak: `Build the transfer feature.`

Bounded: `In TransferService and its existing tests, reject a duplicate client request
using the repository's IdempotencyGuard pattern. Preserve the REST contract, add no
dependency, run ./mvnw -q -Dtest=TransferServiceTest test, and stop if a schema change is
required. Report files changed and test output.`

The second prompt gives Copilot a stopping condition. Stopping is a production feature:
an agent that exposes a missing decision is safer than one that invents it.

## Context discipline inside familiar IDEs

- Attach the work item text only after removing customer data, secrets, internal tokens,
  and irrelevant comments. Prefer a fictional or approved test identifier.
- Attach the target file, its test, an existing analogous implementation, and the API
  contract. Four precise artifacts beat an entire monorepo.
- Ask Copilot to cite files and methods when explaining unfamiliar code. Open those
  references before accepting the conclusion.
- Start a new conversation when the objective changes. Long chats carry stale assumptions.
- Never paste production logs raw. Use an approved observability MCP tool or a sanitized
  excerpt with account identifiers, tokens, hostnames, and payloads removed.
- Treat generated configuration, SQL, authorization rules, concurrency code, and money
  calculations as high-risk changes that need a specialist human review.

## Controls that must not depend on developer memory

| Risk | Repository/IDE steering | Deterministic enforcement |
|---|---|---|
| Secret or customer-data leakage | Instructions say what is prohibited; approved MCP returns sanitized data | Secret/DLP scanning, log access controls, CI block |
| Unsupported dependency | Prompt says no dependency; agent explains proposed additions | Lockfile review, SCA, allowlist policy |
| Architecture drift | Stack instructions and a reference implementation | ArchUnit/Nx boundaries/ESLint rules |
| Missing tests | Definition of done and test prompt | Required CI jobs and coverage/quality gates |
| Unauthorized behavior | Security reviewer agent and least-privilege tools | Server-side authorization tests, branch protection, human approval |
| IDE feature mismatch | Support matrix and visible customization inventory | Cross-IDE CI; no control relies only on a preview feature |

## Definition of done for a Copilot-assisted change

- The work-item acceptance criteria map to tests or explicit manual verification.
- The diff contains only in-scope files; generated comments and unused code are removed.
- No dependency, public API, schema, permission, or operational behavior changed silently.
- Focused tests pass locally; required lint/type/build checks pass; outputs are recorded.
- Security, privacy, accessibility, resilience, and observability were reviewed where relevant.
- A human who understands the affected component reviews the PR.
- Copilot authorship never substitutes for the normal change record or approval.

## Rollout checklist for platform and engineering leads

1. Publish a support matrix by IDE and pin the minimum approved plugin/extension version.
2. Start with repository instructions plus three workflows: explain, test, and review.
3. Pilot with one Spring Boot team in IntelliJ and one web team in VS Code; use the same
   fictional benchmark stories from [chapter 12](12_enterprise_use_cases_spring_angular_react.md).
4. Measure lead time, review rework, escaped defects, test completeness, and onboarding
   time—not lines generated or suggestion acceptance alone.
5. Convert recurring output defects into reviewed instruction/test/lint changes.
6. Add agents, skills, MCP, and hooks only after a concrete repeated need is demonstrated.
7. Revalidate preview features and content-exclusion limitations quarterly.

