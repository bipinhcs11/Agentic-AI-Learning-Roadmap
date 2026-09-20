# Architecture and integration design

## Implemented POC

```mermaid
flowchart LR
    PO[Product owner in local browser] --> HTTP[Loopback Python HTTP service]
    HTTP --> DATA[SQLite current drafts and publication snapshots]
    HTTP --> CONTEXT[Fictional versioned source fixtures]
    HTTP --> TEMPLATES[Versioned JSON templates]
    HTTP --> OFFLINE[Offline sample assembler]
    HTTP --> BRIEF[Copilot brief]
    BRIEF --> USER[User manually runs approved Copilot Chat]
    USER --> IMPORT[Paste JSON and validate]
    IMPORT --> EDIT[Edit and review]
    OFFLINE --> EDIT
    EDIT --> WORD[Real Word export]
    EDIT --> APPROVE[Approve current revision]
    APPROVE --> PREVIEW[Local Confluence simulation]
```

This is an integration POC rather than an autonomous agent platform. No ADK, model SDK, external queue, vector database, MCP server, or frontend framework is required. Copilot is a separate user-facing drafting tool; the application owns templates, validation, review state, and outputs.

## State transitions

```text
Offline: queued → generating → ready (or failed)
Copilot: queued → awaiting_copilot → ready
Review:  ready → approved → published (simulated)
Edits:   ready/approved/published → ready at revision N+1; approval cleared
```

- Source selection and notes are snapshotted when a draft is created. Editing input fields afterward does not change an existing draft; create a new one.
- Imported Copilot output must match the exact section headings and selected citation IDs. Source metadata stays server-owned.
- Concurrent edits use an expected revision. A stale revision gets HTTP 409.
- Approval records that the current browser-session user acknowledged review; this is not a verified business sign-off.
- Publication requires the approved revision. The same revision is published at most once, even on repeated requests. A new revision can create another snapshot.
- Published snapshots retain content as approved. The displayed page shows the latest published snapshot, even if the working draft has newer edits.
- Events store action/time/revision, not complete historical draft bodies. No claim of immutable compliance-grade audit is made.

## Data contract

Drafts contain `title`, `kind`, `notes`, selected `sources`, ordered `sections`, `template_version`, `provider`, `model` description, `input_sha256`, generation time, revision, status, approval revision, warnings, events, and publication snapshots. `[N1]` references the notes snapshot; `[S1]` etc reference selected source snapshots.

`input_sha256` fingerprints the exact submitted notes. It is not a signature or a complete generation-input hash. Source content and versions plus template version are recorded separately. For production, hash the entire normalized generation input including template content and provider settings.

## API routes

All routes require the local origin. Mutation routes require JSON and a per-session CSRF token from `/api/config`.

| Method | Route | Behavior |
|---|---|---|
| GET | `/api/config` | Templates, fictional sources, sample notes, CSRF token |
| GET | `/api/documents` | Latest 50 documents owned by this browser session |
| POST | `/api/documents` | Validate input; queue offline generation or prepare Copilot handoff |
| GET | `/api/documents/{id}` | Fetch current document and state |
| GET | `/api/documents/{id}/brief` | Download pending Copilot prompt |
| POST | `/api/documents/{id}/import` | Import `{result: {sections: [...]}}` into a pending Copilot draft |
| POST | `/api/documents/{id}/save` | Save `{revision, sections}`; invalidate approval |
| POST | `/api/documents/{id}/approve` | Acknowledge `{revision, reviewed: true}` |
| POST | `/api/documents/{id}/publish` | Simulate `{revision, parent}` publication |
| GET | `/api/documents/{id}/word` | Export latest saved content to Word |
| GET | `/api/documents/{id}/page` | View latest simulated publication |
| GET | `/api/documents/{id}/audit` | Download activity metadata |

Validation errors return 400; CSRF/origin/Host violations 403; missing or other-session documents 404; stale state/revision 409; oversized bodies 413. Unknown routes and arbitrary filesystem paths are not exposed. There is no CORS permission for other origins. HTTP cookies use HttpOnly and SameSite=Strict; HTTPS/Secure cookies are required for any future shared deployment.

## Confluence integration — future implementation

No live adapter is included. This is a deliberate demo boundary: Cloud versus Data Center, authentication, and authorized space scope have not been established.

### Retrieval contract

An approved adapter should expose `list_permitted_sources(user, query)` and `get_source(user, page_id)`, returning page ID, title, version, URL, normalized text, retrieval time, and an authorization context. Start with explicit page selection, not an unrestricted company-wide crawl.

1. Authenticate the employee using the organization's identity provider.
2. Resolve delegated Confluence access or an explicitly constrained approved service identity.
3. Check the employee's permission to read each selected page. A broad service account's access alone is insufficient.
4. Fetch body and version; normalize supported content formats. Treat page content as untrusted evidence, never instructions.
5. Cache only with ACL-aware keys and defined expiration/invalidation. Recheck access before generation and export/publication.
6. Record source versions in the draft and warn if policy changes before approval or publication.

Confluence Cloud v2 and Data Center have different endpoints and authentication options. A GitHub PAT cannot authenticate Confluence. Do not use employee PATs as a shared production identity or pass tokens into model prompts.

### Publication contract

Use `preview_publication(user, draft_revision, destination)` followed by `publish_approved_revision(...)`.

- Render the exact approved content through the output adapter, not arbitrary model-produced HTML.
- Show the space, parent page, title, and new-versus-update action before confirmation.
- Verify destination permissions and audience compatibility with the selected source pages; space defaults may expose restricted source content.
- Start with **create a new page**, recording draft ID/revision and remote page ID/version.
- Use a durable idempotency ledger around the outbound request. Reconcile uncertain timeouts rather than blindly creating duplicates.
- Add updates later with current remote version checks and conflict resolution. Never overwrite intervening edits silently.
- Handle 401/403 as actionable authorization failures, 429 with Retry-After, and bounded retry/backoff for transient failures.

`demo.py` produces a **payload illustration** using Cloud v2 `spaceId`, `parentId`, `title`, and a storage body. Placeholder IDs are not usable credentials or a real destination. It is not an implemented or tested live connector.

Official integration references:
- [Confluence Cloud REST API v2](https://developer.atlassian.com/cloud/confluence/rest/v2/intro/)
- [Confluence Cloud pages API](https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/)
- [Confluence Data Center REST API](https://developer.atlassian.com/server/confluence/rest/)

## Copilot integration choices

| Choice | Fit | Boundary |
|---|---|---|
| Manual brief and response handoff | Implemented; uses existing employee Copilot access | Extra copy/paste; model response needs validation |
| VS Code workspace prompts and local exporter | Possible next step for users comfortable with VS Code | Per-user installation and policy-enabled tools |
| Copilot CLI on an employee workstation | Evaluate only if approved | User-scoped execution and tool permissions; do not turn a personal session into a shared backend |
| Shared unattended model endpoint | Future seamless portal | Requires an explicitly approved API/SDK, licensing, identity, and data-handling arrangement |

The POC makes no claim that a Copilot subscription cannot support any automation in the future. It simply does not assume a backend entitlement or permitted invocation method that has not been confirmed for this organization.

References: [Copilot CLI overview](https://docs.github.com/en/copilot/concepts/agents/copilot-cli/about-copilot-cli), [VS Code reusable prompts](https://code.visualstudio.com/docs/agent-customization/prompt-files).
