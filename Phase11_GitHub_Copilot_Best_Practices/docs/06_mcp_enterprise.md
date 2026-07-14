# 06 — MCP in the Enterprise: the Governance Boundary

MCP (Model Context Protocol) is how Copilot reaches beyond the repo — issue trackers,
API catalogs, databases, internal docs. That makes it simultaneously the biggest
capability unlock and the biggest governance surface in this whole blueprint. Treat
`mcp.json` as **the firewall rule table of your AI setup.**

## Mechanics in 60 seconds

Workspace config in `.vscode/mcp.json` (checked in, team-shared):

```jsonc
{
  "servers": {
    "github": { "type": "http", "url": "https://api.githubcopilot.com/mcp/" },
    "internal-api-catalog": { "type": "http", "url": "https://<gateway>/catalog" },
    "local-docs": { "type": "stdio", "command": "npx", "args": ["-y", "<package>"] }
  }
}
```

Each server contributes tools (and sometimes resources/prompts) that agent mode can
call. The [starter kit's mcp.json](../copilot_starter_kit/.vscode/mcp.json) shows the
three archetypes: an official vendor server, an internal gateway, a local stdio server.
Secrets are never inlined — `${input:...}` prompts or environment variables only.

## Why a bank should care (both directions)

**The upside is real.** The dynamic-MCP work in Phase 9 of this repo demonstrated the
architecture enterprises want: a central **MCP gateway** with per-team tool allowlists,
identity-aware auth, and audit logging — one governed door to internal systems instead
of fifty ad-hoc integrations. When Copilot can query the internal API catalog, the
"which service owns customer addresses?" question stops costing a meeting.

**The risk is specific**, not hand-wavy:

1. **Data egress** — a tool's output enters the model context. A server that returns
   customer records has just shipped customer records into an AI request.
2. **Prompt injection via tool output** — a Jira ticket body or API description saying
   "now call the delete tool" is untrusted input arriving with insider credentials.
3. **Tool-name spoofing / rug pulls** — a server can change its tool definitions after
   approval. Pin versions; re-review on change.
4. **Confused deputy** — the developer's token doing things the developer wouldn't.

## The enterprise MCP policy (the short version that works)

- **Allowlist, not discovery.** Developers install from an internal registry of
  reviewed servers. Unknown servers from the public internet do not get corporate
  credentials, period. GitHub's MCP registry / allowed-servers policy features are the
  control point; the org disables everything else.
- **`mcp.json` is code.** It lives in the repo, changes by PR, `CODEOWNERS`-protected —
  exactly like the instructions files, and for the same reason: it changes what the AI
  can *do*.
- **Read-only by default.** A server that only reads the API catalog needs one review;
  a server that can mutate Jira needs a different conversation. Grade servers R/RW and
  make RW rare.
- **Gateway over point-to-point.** One internal MCP gateway with authn/z + audit logs
  beats N teams running N servers with N secret-handling bugs. (Phase 9's capstone hub
  is a working miniature of this pattern.)
- **Log tool calls.** "Which tools did the agent call to produce this PR?" must be an
  answerable question in an audit.

## When NOT to use MCP

The most common MCP mistake in the wild is standing up a server for content that
should have been **checked into the repo**. If it's stable text an agent needs
(coding standards, API conventions, runbooks) — that's instructions, skills, or a
`docs/` folder. MCP earns its complexity only when the data is **live** (current
tickets, real schemas, actual service status). Static knowledge → files in git.
Live systems → MCP through the gateway.
