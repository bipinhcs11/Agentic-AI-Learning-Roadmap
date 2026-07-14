# 13 — Enterprise Resources and Adoption Guide

This is a curated implementation guide, not a link dump. It maps current official
GitHub and VS Code material to the person who needs it, the decision it supports, and
the evidence an enterprise should produce after reading it.

> **Last reviewed:** July 12, 2026. GitHub Copilot features, policy names, preview
> status, telemetry coverage, and billing change frequently. Recheck the linked source
> before turning any statement into policy. Prefer generally available controls for
> mandatory requirements and give every preview feature a fallback.

## If the team reads only eight resources

| Priority | Official resource | Why it matters | Action after reading |
|---:|---|---|---|
| 1 | [Customization cheat sheet](https://docs.github.com/en/copilot/reference/customization-cheat-sheet) | Compares instructions, prompt files, agents, skills, hooks, MCP, and IDE support | Publish an IntelliJ/VS Code support matrix and identify every preview dependency |
| 2 | [GitHub Copilot enterprise and organization policies](https://docs.github.com/en/copilot/concepts/policies) | Explains where policy applies and how enterprise/organization settings interact | Record the approved value, owner, rationale, and review date for every Copilot policy |
| 3 | [Responsible use of Copilot agents](https://docs.github.com/en/copilot/responsible-use/agents) | States intended uses, limitations, safety mitigations, and human validation duties | Add agent limitations and required human review to training and the acceptable-use policy |
| 4 | [Content exclusion behavior](https://docs.github.com/en/copilot/how-tos/configure-content-exclusion/exclude-content-from-copilot) | Documents supported surfaces and important Agent mode/coding-agent limitations | Identify repositories that cannot safely use Agent mode based on exclusion alone |
| 5 | [Copilot code review](https://docs.github.com/en/copilot/concepts/agents/code-review) | Covers review availability, limitations, instructions, skills, and MCP behavior | Keep Copilot advisory; require human approval and define how findings are validated |
| 6 | [Configure enterprise/organization MCP access](https://docs.github.com/en/copilot/how-tos/administer-copilot/manage-mcp-usage/configure-mcp-server-access) | Describes an MCP registry and allowlist policy for supported clients | Create an internal registry; default to read-only tools and named owners |
| 7 | [Monitor agentic activity](https://docs.github.com/en/copilot/how-tos/administer-copilot/manage-for-enterprise/manage-agents/monitor-agentic-activity) | Shows recent agent sessions and audit-log monitoring | Assign an operations owner and define alerts/review cadence for agent actions |
| 8 | [Copilot usage metrics reference](https://docs.github.com/en/copilot/reference/copilot-usage-metrics/copilot-usage-metrics) | Defines dashboard/API adoption and code-generation fields | Pair usage data with delivery, quality, security, and developer-experience outcomes |

## Developer track — IntelliJ and VS Code

These resources belong in onboarding, not in an administrator-only wiki.

### Use Copilot in the IDE

- [Copilot Chat in JetBrains IDEs](https://docs.github.com/en/copilot/how-tos/chat-with-copilot/chat-in-ide?tool=jetbrains)
  covers Ask, Plan, Edit/Agent workflows, references, models, and the effect of enterprise
  policy. Use it with the Spring Boot exercises in [chapter 12](12_enterprise_use_cases_spring_angular_react.md).
- [Copilot customization in VS Code](https://code.visualstudio.com/docs/agent-customization/overview)
  explains instructions, prompt files, custom agents, skills, MCP, hooks, plugins, and
  the Customizations editor. Use it with the Angular and React exercises.
- [Repository custom instructions](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions-in-your-ide)
  is the source of truth for installation locations and how instructions are applied.
- [Customizing Copilot code review](https://docs.github.com/en/copilot/tutorials/customize-code-review)
  shows how concise, testable instructions improve review output.

### Onboarding lab with expected evidence

1. Ask Copilot to explain one call path and cite repository files.
2. Confirm `.github/copilot-instructions.md` appears under response References.
3. Make a test-only change in Edit mode and accept/reject individual files.
4. Run a bounded Agent task in a fictional training repository.
5. Review the diff, focused tests, full repository checks, and terminal-command history.
6. Request a Copilot review, validate one correct finding, and reject one unsupported
   suggestion with a written reason.

Completion evidence is the reviewed training PR and test output—not a screenshot showing
that the extension is installed.

## Repository maintainer track — customization as code

| Need | Official resource | Repository artifact |
|---|---|---|
| Whole-repository rules | [Configure custom instructions](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions-in-your-ide) | `.github/copilot-instructions.md` with architecture and exact commands |
| Repeated single task | [Customization cheat sheet](https://docs.github.com/en/copilot/reference/customization-cheat-sheet) | `.github/prompts/*.prompt.md` where supported; plain prompt fallback elsewhere |
| Specialist role | [About custom agents](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-custom-agents) | Read-only planner/reviewer or narrowly tooled implementation agent |
| Reusable workflow with assets | [Agent Skills in VS Code](https://code.visualstudio.com/docs/agent-customization/agent-skills) | `.github/skills/<name>/SKILL.md` plus reviewed scripts/references |
| Deterministic lifecycle action | [Agent hooks in VS Code](https://code.visualstudio.com/docs/agent-customization/hooks) | `.github/hooks/*.json`, with CI fallback because hooks are preview/not cross-IDE |

Repository owners should maintain a small conformance test set: ten fictional tasks with
expected behaviors and prohibited behaviors. Re-run it when instructions, agents, models,
IDE plugins, or major framework versions change. This is more informative than asking
whether a prompt “looks good.”

## Platform and security track — controls before scale

### Policy inventory

Use [Copilot policies](https://docs.github.com/en/copilot/concepts/policies) to create a
control register containing:

- policy name and enterprise/organization scope;
- approved value and business rationale;
- surfaces covered: GitHub.com, VS Code, JetBrains, CLI, cloud agent;
- general-availability or preview status;
- control owner, approver, last test date, and next review date;
- fallback when an IDE or feature does not implement the setting.

Do not assume a setting shown in one IDE applies everywhere. Test with enterprise-managed
identities on the exact approved extension/plugin versions.

### Network and workstation readiness

- [Copilot network settings](https://docs.github.com/en/copilot/how-tos/configure-personal-settings/configure-network-settings)
  covers corporate proxies and custom certificates for supported IDEs. GitHub warns
  against ignoring certificate errors; enterprise documentation should do the same.
- [Copilot network allowlist reference](https://docs.github.com/en/copilot/reference/copilot-allowlist-reference)
  lists current endpoints and their purposes. Network teams should derive firewall rules
  from this maintained source rather than copying a stale list into this repository.

Required evidence: supported proxy design, TLS/certificate decision, approved endpoints,
test results from IntelliJ and VS Code, and a troubleshooting route that does not ask
developers to disable certificate verification.

### Content and data boundaries

Read [content exclusion](https://docs.github.com/en/copilot/how-tos/configure-content-exclusion/exclude-content-from-copilot)
together with [responsible use for agents](https://docs.github.com/en/copilot/responsible-use/agents).
Document:

- repositories and paths excluded on supported surfaces;
- Agent mode/coding-agent exceptions and the compensating control;
- prohibited prompt data: secrets, real customer data, production payloads, credentials;
- approved sanitization process for logs and work items;
- repositories where agentic features are disabled;
- incident process for suspected sensitive-data exposure.

Content exclusion is defense in depth. It is not a substitute for repository access
control, secret management, DLP, sanitized training data, or human judgment.

## MCP track — useful enterprise context without uncontrolled reach

MCP is valuable when Copilot needs current information from approved systems—work items,
service ownership, API catalogs, runbooks, or sanitized observability data. It also creates
a new tool and data boundary.

Start with:

- [Configure MCP access and an allowlist](https://docs.github.com/en/copilot/how-tos/administer-copilot/manage-mcp-usage/configure-mcp-server-access)
  for enterprise/organization discovery policy;
- [MCP with Copilot cloud agent](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/mcp-and-cloud-agent)
  for cloud-agent limitations, default servers, repository configuration, and tool use;
- [MCP and Copilot code review](https://docs.github.com/en/copilot/concepts/agents/code-review)
  because repository MCP settings can also affect review behavior.

### Minimum MCP registration record

| Field | Required enterprise answer |
|---|---|
| Business purpose | Which developer workflow needs this server? |
| Owner | Who patches, monitors, and decommissions it? |
| Data classification | What input/output may cross the boundary? |
| Tools | Exact tool inventory; read/write; destructive potential |
| Identity | User or service identity, scopes, token lifetime, rotation |
| Authorization | Does the server enforce the initiating user's permissions? |
| Network | Destinations, egress restrictions, proxy path |
| Logging | Tool calls, result metadata, redaction, retention, SIEM route |
| Failure behavior | Timeout, partial result, revoked access, prompt-injection response |
| Review | Security approval, version pin, reassessment date |

Adopt read-only servers first. A work-item reader is a safer first pilot than a tool that
updates incidents, merges pull requests, or changes production configuration.

## Code review and coding-agent track

- [About Copilot code review](https://docs.github.com/en/copilot/concepts/agents/code-review)
  explicitly says feedback must be validated and supplemented with human review.
- [Use Copilot code review on GitHub](https://docs.github.com/en/copilot/how-tos/copilot-on-github/use-copilot-agents/copilot-code-review)
  explains base-branch instructions, review-focused skills, MCP context, and session logs.
- [Responsible use of Copilot agents](https://docs.github.com/en/copilot/responsible-use/agents)
  should be required reading before cloud-agent access is granted.
- [Enterprise agent management](https://docs.github.com/en/copilot/concepts/agents/enterprise-management)
  covers feature policy and administrative visibility.

Enterprise operating rules:

1. Coding agents open draft PRs; they do not bypass protected branches.
2. Issue acceptance criteria are executable or manually verifiable and contain no real
   sensitive data.
3. The agent receives only the permissions and MCP tools required for the task.
4. CI applies the same SAST, SCA, secret, license, test, and deployment gates to all authors.
5. Copilot review is advisory; an accountable human provides required approval.
6. Reviewers inspect agent session/tool evidence when MCP or autonomous execution matters.

## Audit and monitoring track

- [Review Copilot audit logs](https://docs.github.com/en/enterprise-cloud@latest/copilot/how-tos/administer-copilot/manage-for-enterprise/review-audit-logs)
  distinguishes policy/license and GitHub agent events from local IDE prompt history. Do
  not promise prompt-level IDE auditability that the platform does not provide.
- [Monitor agentic activity](https://docs.github.com/en/copilot/how-tos/administer-copilot/manage-for-enterprise/manage-agents/monitor-agentic-activity)
  covers active/recent sessions and agent activity through enterprise audit logs.
- [Agentic audit-log event reference](https://docs.github.com/en/copilot/reference/agentic-audit-log-events)
  defines fields such as agent session ID, initiating user, and agent action.

Suggested detections:

- unexpected agent sessions in restricted organizations or repositories;
- policy, MCP, model, or seat changes outside the approved change window;
- new or materially changed MCP tool inventories;
- agent-created PRs with unusual scope, sensitive paths, or repeated CI failures;
- abnormal write-tool use or activity initiated by dormant/unexpected identities.

Define retention and SIEM streaming from current product capabilities and legal policy.
Avoid collecting prompt/code content “just in case”; logging itself creates a sensitive
data store that needs purpose limitation, access control, redaction, and retention.

## Measurement track — prove outcomes, not generated volume

Use three layers together:

1. [User activity data](https://docs.github.com/en/enterprise-cloud@latest/copilot/how-tos/administer-copilot/manage-for-organization/review-activity/review-user-activity-data)
   for seat assignment and recent engagement.
2. [Usage metrics data](https://docs.github.com/en/copilot/reference/copilot-usage-metrics/copilot-usage-metrics)
   for dashboard/API definitions and adoption patterns.
3. Engineering-system measures from source control, CI, incident, security, and developer
   surveys for actual outcomes.

| Question | Useful measure | Misleading substitute |
|---|---|---|
| Are seats reaching intended users? | Activated/active users by approved cohort and IDE | Seats purchased |
| Is onboarding improving? | Time to first reviewed PR; new-joiner task completion | Suggestions accepted |
| Is delivery improving? | PR lead time by comparable work type and team | Lines generated |
| Is quality stable? | Rework, escaped defects, rollback/change-failure rate | Number of Copilot reviews |
| Is security stable? | Valid findings, secret events, vulnerable dependencies, policy exceptions | “No incidents reported” |
| Are agents appropriate? | Successful bounded tasks, human rework, CI pass rate, tool exceptions | Agent sessions started |
| Is the platform cost-effective? | Outcome change per active cohort and use case | Average requests per user |

Lines-of-code and acceptance metrics are directional telemetry, not productivity scores.
Never use individual Copilot metrics for employee performance ranking. Compare cohorts and
work types carefully, account for IDE/plugin telemetry coverage, and publish limitations.

## Role-based reading paths

### Spring Boot developer or lead using IntelliJ

1. [JetBrains IDE guide](https://docs.github.com/en/copilot/how-tos/chat-with-copilot/chat-in-ide?tool=jetbrains)
2. [Customization support matrix](https://docs.github.com/en/copilot/reference/customization-cheat-sheet)
3. [Custom instructions](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions-in-your-ide)
4. [Code review](https://docs.github.com/en/copilot/concepts/agents/code-review)
5. This roadmap's [Spring Boot use case](12_enterprise_use_cases_spring_angular_react.md#use-case-1--spring-boot-idempotent-scheduled-transfer-creation-in-intellij)

### Angular or React developer using VS Code

1. [VS Code customization overview](https://code.visualstudio.com/docs/agent-customization/overview)
2. [Custom instructions](https://code.visualstudio.com/docs/agent-customization/custom-instructions)
3. [Custom agents](https://code.visualstudio.com/docs/agent-customization/custom-agents)
4. [Agent Skills](https://code.visualstudio.com/docs/agent-customization/agent-skills)
5. This roadmap's [Angular and React use cases](12_enterprise_use_cases_spring_angular_react.md)

### Enterprise platform or security owner

1. [Policies](https://docs.github.com/en/copilot/concepts/policies)
2. [Responsible use of agents](https://docs.github.com/en/copilot/responsible-use/agents)
3. [Content exclusion](https://docs.github.com/en/copilot/how-tos/configure-content-exclusion/exclude-content-from-copilot)
4. [MCP access control](https://docs.github.com/en/copilot/how-tos/administer-copilot/manage-mcp-usage/configure-mcp-server-access)
5. [Agentic monitoring](https://docs.github.com/en/copilot/how-tos/administer-copilot/manage-for-enterprise/manage-agents/monitor-agentic-activity)

### Engineering leader or adoption owner

1. [Plan a Copilot rollout](https://docs.github.com/en/copilot/rolling-out-github-copilot-at-scale/planning-your-rollout)
2. [User activity data](https://docs.github.com/en/enterprise-cloud@latest/copilot/how-tos/administer-copilot/manage-for-organization/review-activity/review-user-activity-data)
3. [Usage metrics](https://docs.github.com/en/copilot/reference/copilot-usage-metrics/copilot-usage-metrics)
4. [Responsible use of agents](https://docs.github.com/en/copilot/responsible-use/agents)

## A practical 30/60/90-day adoption backlog

### Days 0–30 — establish the safe baseline

- Select one IntelliJ Spring Boot team and one VS Code web team.
- Confirm managed identities, policies, proxy/certificate path, and approved IDE versions.
- Add short repository instructions, exact commands, CODEOWNERS, and CI gates.
- Train Ask → Edit → bounded Agent workflows using fictional chapter 12 scenarios.
- Record baseline lead time, defects/rework, onboarding time, security findings, and survey data.
- Keep MCP write tools, broad agents, and preview-only mandatory controls out of scope.

### Days 31–60 — standardize repeated workflows

- Convert recurring tasks into three reviewed assets: test generation, implementation
  planning, and read-only security/code review.
- Establish the MCP registration record and pilot one approved read-only server.
- Enable advisory Copilot code review for the cohort; retain required human approvals.
- Connect policy/agent audit events to the normal monitoring process.
- Review telemetry coverage by IDE/plugin version before interpreting usage differences.

### Days 61–90 — expand using evidence

- Compare the pilot with its baseline using delivery, quality, security, and experience.
- Fix repeated Copilot failures through instructions, tests, lint rules, or training.
- Decide which workflows merit broader rollout and which should remain human-led.
- Publish a versioned paved-road template plus stack overlays for Spring Boot, Angular,
  and React.
- Set quarterly reviews for policies, preview features, MCP inventory, model changes,
  network endpoints, audit coverage, and customization conformance tests.

The enterprise goal is not “maximum Copilot usage.” It is a repeatable system in which
developers receive useful help inside familiar IDEs, sensitive boundaries remain explicit,
changes are independently verified, and adoption expands only when outcomes justify it.

