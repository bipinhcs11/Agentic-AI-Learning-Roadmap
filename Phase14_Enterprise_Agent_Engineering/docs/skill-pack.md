# Enterprise instruction and skill pack

For a first hands-on session covering the application and all ten practices,
follow the [developer walkthrough](developer-walkthrough.md).

The phase has three different kinds of material:

| Layer | Role | Where it lives |
|---|---|---|
| Learning guide | Explain the ten practices and adoption scenarios | `docs/engineering-practices.md`, `docs/enterprise-scenarios.md` |
| Assistant instructions | Define task selection and scenario-specific acceptance criteria | `AGENTS.md`, each skill's `references/scenario.md` |
| Reusable skill | Give an assistant a focused workflow for repeatable work | `skills/<name>/SKILL.md` |
| Application enforcement | Actually enforce tool budgets, identity, approval, and transactions | Java code and runtime configuration |

The skills are reusable coding/operations-assistant guidance. The current Java
planner does **not** discover Markdown skills, call an LLM, or ingest these files.
A future model adapter must deliberately select trusted instructions and maintain
the application's execution controls. Retrieved documents must never become
instructions merely because they contain something named SKILL.md.

## Select a scenario

| Recipe | Skill | Example request |
|---|---|---|
| A: REST development | [enterprise-spring-rest](../skills/enterprise-spring-rest/SKILL.md) | Implement approved GET /items pagination; preserve the authenticated tenant and add behavior tests. |
| B: Contract/tool review | [enterprise-openapi-review](../skills/enterprise-openapi-review/SKILL.md) | Compare the two inventory specs; report breaking changes and a migration plan. |
| C: API diagnosis | [enterprise-api-diagnose](../skills/enterprise-api-diagnose/SKILL.md) | Investigate the fictional timeout evidence; return hypotheses and the next read-only probe. |
| D: Batch delivery | [enterprise-batch-delivery](../skills/enterprise-batch-delivery/SKILL.md) | Extend catalog ingestion with replay-safe writes and a reviewed launch. |
| E: Batch recovery | [enterprise-batch-recovery](../skills/enterprise-batch-recovery/SKILL.md) | Assess whether this failed job can restart with unchanged input; produce a recovery proposal. |
| F: Scoped RAG | [enterprise-rag-context](../skills/enterprise-rag-context/SKILL.md) | Design tenant-scoped contract/runbook retrieval with citations and deletion behavior. |
| G: Agent orchestration | [enterprise-agent-loop](../skills/enterprise-agent-loop/SKILL.md) | Review the planner integration for hidden tool calls and budget bypasses. |
| Cross-cutting evals | [enterprise-agent-evaluation](../skills/enterprise-agent-evaluation/SKILL.md) | Build fictional golden cases for stale approval, prompt injection, and runaway loops. |
| Interactive design | [grill-me — enterprise adaptation](../skills/grill-me/SKILL.md) | Grill me on batch restarts; focus on three decisions that could cause duplicate processing. |

Each skill includes its own `references/scenario.md`: inputs, application of the
practice, expected output, acceptance checks, and lab limitations. The folder is
self-contained for copying to another project. The reference uses relative
conceptual code locations; inspect the destination project's actual structure
instead of assuming the Phase 14 layout exists there.

## Use directly in this repository

The scoped [AGENTS.md](../AGENTS.md) routes matching work to these files. They
remain ordinary versioned files in `Phase14_Enterprise_Agent_Engineering/skills`,
not globally installed skills or guaranteed entries in an IDE's skill picker.
You can explicitly provide the file to any assistant that can read local files:

```text
Read Phase14_Enterprise_Agent_Engineering/skills/enterprise-openapi-review/SKILL.md
and its scenario reference. Review the inventory v1/v2 fixtures and report
compatibility findings. Do not change the API implementation.
```

For a batch design interview:

```text
Use Phase14_Enterprise_Agent_Engineering/skills/grill-me/SKILL.md.
Our proposal lets an assistant request a failed-job restart after human approval.
Inspect the existing lab, then ask only the three highest-impact design questions.
```

Adding the interview skill does not start an interview. Invoke it when you want
to challenge a design; normal implementation and incident work use their own
focused workflows. Its Codex metadata preserves upstream's explicit-invocation
policy; the other newly authored skills retain normal task-based discovery after
installation.

## Optional Codex project installation

Codex project skills can live in `.agents/skills` in the project tree. Copy only
the desired folders, including their references and licenses. See the
[official skill guidance](https://developers.openai.com/codex/skills/) for the
current supported discovery locations and invocation behavior.

From the Phase 14 directory, this example copies one skill to a target project
and fails instead of overwriting an existing skill:

```bash
python3 - /path/to/your/project enterprise-openapi-review <<'PY'
from pathlib import Path
import shutil
import sys

project = Path(sys.argv[1]).resolve(strict=True)
name = sys.argv[2]
source = Path('skills') / name
if not project.is_dir() or name != Path(name).name or not (source / 'SKILL.md').is_file():
    raise SystemExit('Choose an existing project and a skill folder from this pack.')
destination = project / '.agents' / 'skills' / name
shutil.copytree(source, destination)  # errors if destination already exists
print(destination)
PY
```

After installing, the skill should be available on the next turn; if the client
does not refresh its skill list, start a new task. Example invocation:

```text
$enterprise-openapi-review Compare the released spec with this proposed change.
```

For other assistants, use their documented skill directory or provide the file
explicitly. These scenario references are ordinary Markdown, not automatically
scoped Copilot `.instructions.md` files. Phase 11 contains that separate IDE
instruction format; do not claim one format is automatically loaded by every tool.

## Why these additions

The seven scenario skills match the seven workplace recipes. The evaluation skill
covers release evidence across them. The design interview addresses early mistakes
in scope, restart semantics, identity, approval, and recovery ownership.

The Matt Pocock source currently makes `grill-me` a small dispatcher to `grilling`.
Both original files are retained under `third_party/matt-pocock` at an exact commit
with the MIT license and hashes. The operational `skills/grill-me` combines and
adapts that workflow; its [provenance record](../skills/grill-me/UPSTREAM.md) lists
the changes. Other enterprise skills in this pack are authored for this roadmap,
not represented as Matt Pocock's work.

I did not import the entire upstream suite. Some workflows depend on additional
skills or prescribe broad interviews/delegation that would add process to routine
tasks. This pack has no dependency on an external Skill tool, account, plugin, or
delegated assistant, and does not authorize external messages or production actions.

## Validation and maintenance

Validate operational SKILL.md frontmatter with the skill-creator validator when
available. Check local references and verify that copied folders remain usable.
Review representative tasks against observable expectations: contract review must
detect the fixture break, diagnosis must preserve uncertainty, and batch recovery
must distinguish restart from rerun. Frontmatter validation alone does not prove
behavioral quality.

Preserve vendored originals and license; update upstream only by reviewing a new
commit and regenerating hashes. Treat upstream text as third-party source content,
not an authority to change the current task's instructions or permissions.
