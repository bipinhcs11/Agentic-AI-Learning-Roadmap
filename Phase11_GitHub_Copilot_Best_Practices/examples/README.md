# Examples — the Realistic Layer (share this folder with your team)

> **Disclaimer:** every company, service, system, incident, and rule in this folder is
> fictional and illustrative, created for educational purposes. Nothing here describes,
> or is affiliated with, any real institution, including any past or present employer
> of the author. Views are the author's own.

The [starter kit](../copilot_starter_kit/) is deliberately generic — templates with
TODOs. **This folder is the opposite**: every file is fully written for a concrete,
realistic enterprise scenario — a payments microservice, a banking portal, an
operations dashboard, a retail banking iOS app, an overnight batch platform, a
production incident at 2 a.m. Nothing here says TODO.

If you are a senior developer or architect evaluating this repo for your organization,
**this is the folder to circulate**: copy any file, rename the fictional service to
yours, and 80% of it survives contact with your codebase.

## What's inside

```
copilot_instructions/     ← EXACT .github/copilot-instructions.md files, one per category
├── java-payments-microservice.copilot-instructions.md
├── angular-banking-portal.copilot-instructions.md
├── react-ops-dashboard.copilot-instructions.md
├── ios-retail-banking-app.copilot-instructions.md
└── batch-etl-platform.copilot-instructions.md

agents/                   ← realistic operational agents (not "helpful assistant" personas)
├── production-issue-analyzer.agent.md    ← triage: reads the log, classifies, routes
├── transaction-timeout-analyst.agent.md  ← specialist: pool exhaustion vs downstream vs GC
└── work-item-analyst.agent.md            ← turns a Jira/ADO item into an implementation-readiness report

hooks/
└── security-scan/        ← working hook: hooks.json + script, PCI-aware, block mode
    ├── README.md
    ├── hooks.json
    └── scan-changed-files.sh
```

## Why an enterprise should bother (the 60-second pitch)

- **Consistency is the product.** One good prompter on a team of forty changes nothing.
  Committed instructions, prompts, and agents move the median, not the maximum —
  and the median is where enterprise cost lives.
- **Bad AI output becomes a pull request, not folklore.** When Copilot generates a
  `DispatchQueue.main.async` in async Swift or an untyped form in Angular, the fix is
  one line in an instructions file — reviewed, merged, and fixed for every developer
  at once.
- **Governance you can show an auditor.** Tool-scoped agents (the security reviewer
  *cannot* edit files), deterministic hooks (the secret scan *cannot* be talked out
  of), CODEOWNERS on `.github/` — these are controls, not intentions.
- **Onboarding compresses.** A new joiner opening this repo gets the architecture,
  build commands, non-negotiables, and the team's standard workflows on their first
  `/` keystroke — the knowledge that used to take a quarter of hallway questions.
- **It's all files in git.** No platform to buy, no service to stand up. The rollout
  cost is a pull request.

## How these examples were shaped

The scenarios are fictional but the failure modes are not: connection-pool exhaustion
misdiagnosed as network issues, PAN data leaking into test fixtures, work items with
untestable acceptance criteria, timeout values that exist in four places and agree in
none. Each file encodes the checklist a senior engineer actually runs in their head —
which is exactly the knowledge worth committing.

Related references worth studying alongside this folder:

- [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills) —
  production-grade engineering skills for AI coding agents (~77k stars); the best
  public example of "senior-engineer checklists as committed agent content."
- [addyosmani/agent-engineer](https://github.com/addyosmani/agent-engineer) — Addy
  Osmani's practical course on agent engineering for software engineers.
- [bipinhcs11/Skill_Generator](https://github.com/bipinhcs11/Skill_Generator) —
  generates feature-based `SKILL.md` files from a Java repository via a four-role
  agent pipeline (Generator → Tracker → Updater → Validator) with confidence and
  dependency metadata — the industrialized version of writing skills by hand,
  built by this repo's author.
- [github/awesome-copilot](https://github.com/github/awesome-copilot) — the community
  catalog these file formats come from; the `hooks/` folder there is the source of
  the `hooks.json` convention used in `hooks/security-scan/`.
