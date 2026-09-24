# Phase 14 instructions

This phase is a local, fictional Spring teaching lab. Preserve the distinction
between deterministic runtime controls, model integration designs, and reusable
coding-assistant skills. Adding a SKILL.md does not load it into the Java planner.

For a matching task, read the relevant skill and its scenario reference from
`skills/`. Use only the matching workflow; do not load every skill for every edit.

| Task | Skill |
|---|---|
| Develop a REST endpoint | `skills/enterprise-spring-rest/SKILL.md` |
| Review a contract or expose an API tool | `skills/enterprise-openapi-review/SKILL.md` |
| Investigate an API incident | `skills/enterprise-api-diagnose/SKILL.md` |
| Build/change a batch job or launch flow | `skills/enterprise-batch-delivery/SKILL.md` |
| Diagnose/recover a failed batch execution | `skills/enterprise-batch-recovery/SKILL.md` |
| Design scoped retrieval/context/memory | `skills/enterprise-rag-context/SKILL.md` |
| Change agent loops or orchestration | `skills/enterprise-agent-loop/SKILL.md` |
| Build evaluation/release evidence | `skills/enterprise-agent-evaluation/SKILL.md` |
| User requests a design interview | `skills/grill-me/SKILL.md` |

Root contribution rules still apply. Read versions from pom.xml; run `mvn test`
in this folder for Java/runtime changes. For skill-only edits, validate skill
frontmatter/references and review workflow behavior; no Java rebuild is needed
unless executable behavior changed. Update README usage when behavior changes.

The `third_party/matt-pocock` files are pinned source references. Do not activate
or rewrite them as general project instructions. The operational `skills/grill-me`
is explicitly adapted; maintain attribution and license when changing it.
