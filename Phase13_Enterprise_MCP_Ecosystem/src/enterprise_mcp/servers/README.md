# Scenario MCP servers

Each folder is an independently deployable MCP server with one narrowly scoped,
read-only tool. It owns its API credential, scope, upstream paths, input
validation, and response limits.

| Folder | Tool | Approved upstream operations |
|---|---|---|
| `work_item_analysis` | `work_item_analyze` | work item, participant, enrollment, rate, and six-month life-event reads |
| `config_check` | `config_check` | participant configuration read |
| `sonar_analysis` | `sonar_get_issues` | bounded issue read; no source snippets or PR mutation |
| `coding_standards` | `standards_get_rule` | versioned standard read |
| `skills_catalog` | `skills_list_approved` | approved skill metadata read; no branch creation |

The gateway is the only intended caller. Each server rejects requests without a
short-lived, scenario-bound gateway assertion. A server never accepts an
arbitrary URL, arbitrary SQL, a write operation, or the developer's inbound
token.

Adding a scenario requires its own folder, config entry, registry manifest,
credential path, API scope, tests, and gateway policy entry. Do not add a
generic REST proxy or generic SQL tool.
