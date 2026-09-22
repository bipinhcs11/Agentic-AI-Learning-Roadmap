# Business Document Assistant POC

A local browser workspace with indexed retrieval over fictional Confluence pages, for product owners to turn meeting notes and retrieved business context into a reviewed BRD, user-story document, or change request, then export Word or preview a Confluence page.

**All fixtures and outputs are fictional and educational. Do not use real financial, HR, payroll, billing, benefits, or customer data.**

## RAG workflow and implementation plan

Read [PLAN.md](PLAN.md) for the concrete build plan, user experience, acceptance criteria,
and production integration stages.

The app now indexes **7 readable/current fictional pages and 11 sections** from
`fixtures/confluence-pages.json`. Two additional fixture pages are excluded because
one is superseded and one is restricted. The local RAG retriever uses **SQLite FTS5
BM25 with explicit glossary expansion**, not embeddings or a semantic model. No new
Python dependency, model download, or external service is needed; Python's SQLite
build must include FTS5 (available in common Python distributions).

The corpus defines fictional **Cobra = Coordinated Booking and Room Allocation** and
**FHP = Facility Handover Plan** in Workplace. In Lab Operations, **FHP = Field Hardware
Protocol**. These are invented demo meanings, not definitions of your organization's terms.

Source cards show the page, section, space, version, excerpt, reason for retrieval, and
a link to a **local fictional Confluence page preview**. Original `fictional.example`
URLs are provenance placeholders and are not real Confluence endpoints.

## The Copilot-only constraint

The organization has GitHub Copilot, but no confirmed backend model endpoint, no enabled MCP, and no GitHub Actions workflow. This POC deliberately supports two honest paths:

| Mode | What actually runs |
|---|---|
| **Use my Copilot** | App prepares a prompt with selected context and a JSON document contract. The user runs it in their approved Copilot Chat, then pastes the response into the app. The app validates and imports it. |
| **Offline sample** | Deterministic text assembly with a narrow sample policy-conflict check. No model call; not AI-generated. Useful for repeatable demos without Copilot or internet. |

The app does **not** automate Copilot through a PAT, scrape its interface, share a user's Copilot identity, or assume a subscription supplies a backend inference API. No Jenkins, MCP server, GitHub Actions, or cloud account is required to run this POC. Copilot-assisted mode still requires manual user interaction with Copilot and access permitted by organization policy.

## Quick start

Python 3.10+ is required. Run from this project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:8765**. Expected console output:

```text
Business Document Assistant: http://127.0.0.1:8765
Offline + Copilot-assisted drafting. Fictional data only. Confluence publication is simulated.
```

The only third-party runtime dependency is `python-docx`. The web server, job executor, persistence, and tests use Python's standard library. There is no frontend build step, external font, CDN, telemetry, or outbound HTTP request from the app. Copilot use takes place separately in the user's approved interface.

### Five-minute demo

1. Click **Load sample** to load Cobra/FHP notes. Workplace is selected automatically.
2. Click **Find business context**. Review the resolved definitions and retrieved excerpts.
3. Optional ambiguity demo: select **All domains**, search, and see two FHP meanings. Choose **Facility Handover Plan**, then search again. Drafting is blocked until ambiguity is resolved.
4. Confirm **I confirm these definitions and sources apply to this request**.
5. Choose **Offline sample**, then **Generate offline sample**. Show the source-backed definitions and `[S101]`–`[S108]` references alongside meeting proposals `[N1]`.
6. Highlight the proposed **30-day** booking window versus the existing **14-day** rule. The tool does not approve a policy change.
7. Edit, save, and **Download Word**. The source appendix records page sections, versions, and the index hash.
8. Acknowledge review, approve the revision, and **Publish to demo space**. Open the local preview; nothing is sent to Confluence.
9. Edit and save again. Approval is invalidated and the published snapshot stays unchanged.

Changing notes, title, or business domain invalidates the context review and requires
retrieval again. Definition evidence cannot be deselected. Unknown uppercase acronyms
require acknowledgment and remain unresolved questions. If no context matches, drafting
is blocked. Unknown ordinary words are not reliably detected by the acronym heuristic.

For actual Copilot drafting, choose **Use my Copilot** at step 5. Copy/download the brief, run it in the approved Copilot interface, and paste the returned JSON into **Copilot response**. Click **Import draft**. Copilot's output quality varies; the import validates structure and known citation IDs, not semantic truth.

See [the full presenter script](docs/DEMO_GUIDE.md), [architecture and integration design](docs/ARCHITECTURE.md), and [rollout plan](docs/ROLLOUT.md).

## Generate RAG demo files without the UI

```bash
python rag_demo.py
```

Expected output:

```text
Indexed 7 fictional pages / 11 sections.
Cobra = Coordinated Booking and Room Allocation [S101]
FHP = Facility Handover Plan [S103]
Retrieved: S101, S103, S106, S104, S108, S105, S107, S102
Created 16 RAG demo artifacts in .../outputs. No AI call or external publication.
```

`outputs/rag-retrieval.json` contains the actual ranked retrieval result and term decisions.
For each template, `rag-<kind>.docx`, `.html`, `.json`, `-copilot-brief.txt`, and
`-sample-response.json` contain the grounded draft and handoff artifacts. Sample responses
are deterministic fixtures, not actual Copilot output.

## Original three-page sample files

```bash
python demo.py
```

Expected: `Created 18 fictional demo artifacts in .../outputs`.

For each of `brd`, `stories`, and `change`, this creates:

- `.docx`: a real editable Word document with headings and source/provenance appendix.
- `.html`: standalone simulated Confluence preview.
- `.json`: structured draft with input hash and source snapshots.
- `-copilot-brief.txt`: the prompt to run manually in Copilot.
- `-sample-response.json`: deterministic fixture for demonstrating import; **not actual Copilot output**.
- `-confluence-payload.json`: illustrative Cloud v2 storage-format payload; **not sent**.

Browser downloads go to your browser's download location. `demo.py` writes to `outputs/`. Both outputs and `runtime/` are gitignored.

## Verification

```bash
python -m unittest discover -s tests -v
```

Checks cover acronym/domain resolution, unknown terms, no matches, index refresh, restricted/superseded exclusion, stale or foreign retrieval, source confirmation, and all templates, input validation, source selection, citation validation, Copilot import, HTML escaping, real DOCX structure, browser-session isolation, stale revisions, approval invalidation, immutable publication snapshots, idempotent publication, HTTP lifecycle, CSRF/origin/Host checks, and restart handling. HTTP tests bind ephemeral loopback ports.

For layout QA, render the generated DOCX with LibreOffice and inspect every page. Automated DOCX tests validate content and package structure; they do not prove visual layout.

## Files

| File | Responsibility |
|---|---|
| `app.py` | Loopback HTTP routes, session cookies, CSRF, bounded generation queue |
| `retrieval.py` | Section index, BM25 search, glossary lookup, source previews |
| `rag_demo.py` | Reproducible RAG evidence and draft artifacts |
| `PLAN.md` | Implementation plan and acceptance criteria |
| `domain.py` | Template validation, deterministic drafting, Copilot brief, Word/HTML renderers |
| `store.py` | SQLite document state, revisions, approval and publication transitions |
| `templates.json` | Versioned document headings |
| `fixtures/` | Fictional meeting notes and versioned business context |
| `static/` | Browser UI with editable sections and review actions |
| `demo.py` | Reproducible sample artifacts |
| `tests/` | Offline unit and local HTTP integration checks |
| `docs/` | Demo walkthrough, production architecture, rollout decisions |

## POC boundaries

- **Local only:** server binds to `127.0.0.1`, rejects other Host values, and is not a production application server. Do not expose it through a public tunnel or change the binding to share it.
- **No enterprise identity:** the displayed product owner is a demo label. An opaque browser cookie isolates local sessions; this is not SSO, RBAC, or a security boundary against other processes on the same machine.
- **No live Confluence:** context is retrieved from a bundled, sectioned JSON corpus indexed locally. Publishing stores a local HTML-renderable snapshot and a demo parent label. There is no PAT handling or network publishing code.
- **No automatic AI:** Copilot-assisted mode is a manual handoff. Offline mode preserves note lines and fills a template, not a substitute for model reasoning.
- **Limited checks:** retrieval is lexical and may miss paraphrases; the eight-result cap is not evidence of completeness. Fixture audience filters are not real Confluence ACL enforcement. Citation checks cannot establish whether the cited source supports a claim. The only automatic conflict detector matches the sample advance-booking rule. Review all generated content.
- **Input limits:** at most 24,000 characters and 120 non-empty lines of notes; 48,000 characters per draft section.
- **Simple persistence:** SQLite keeps current drafts, input/source snapshots, events, and published snapshots. Full historical draft bodies are not retained. This is not a tamper-proof audit log.
- **Index lifecycle:** the corpus is indexed at startup. Restart after changing fixtures; old retrieval runs cannot create drafts against a different index version. Existing draft snapshots remain unchanged. No live synchronization is implemented.
- **Queue limits:** two generation workers and at most eight active/queued offline jobs. Work interrupted by a server restart is marked failed rather than silently rerun.
- **No DOCX/PDF input parser:** upload `.txt` or `.md`, or paste notes. Word is an output format.
- **Plain-text section bodies:** no rich text editor, tables, tracked changes, arbitrary custom Word templates, or document round-trip import yet.

## Troubleshooting

- **Port in use:** `python app.py --port 8766` and use the printed URL.
- **Missing docx module:** activate the project venv and install its requirements; do not install the root roadmap requirements.
- **No context results:** choose a relevant domain or use the supplied Cobra notes. Lexical search does not understand arbitrary paraphrases.
- **Ambiguous FHP:** choose a meaning and click Find business context again, or narrow the domain.
- **FTS5 unavailable:** use a Python distribution compiled with SQLite FTS5; the app intentionally does not fall back to an unindexed hardcoded result.
- **Import rejected:** ensure JSON contains only `sections`, with every exact heading in order. Section 2 must cite `[N1]`; section 3 must cite every selected source. Remove invented source IDs.
- **Stale revision:** another tab saved this document. Select the draft again in Recent Documents before making the next change.
- **Disabled export:** save your draft edits first.
- **No publication button:** review and approve the current saved revision.
- **Missing history:** use the same browser session and hostname. Sessions survive a server restart while the browser retains its cookie. Session ownership is local; clearing cookies loses access to that session's documents.
- **Reset a disposable demo:** stop the server and remove this project's `runtime/` directory, then restart. This deletes local demo documents; export anything you want to keep first.

## Meeting history and progress

Expand **Track meetings for a project** to save notes under a project and meeting date. A later meeting under the same name can retrieve earlier notes when you click **Find business context**. The app displays a timeline, literal changes since the previous meeting, explicit item transitions, and unresolved items carried forward. Notes and timeline stay local to this browser session; project names are case-insensitive.

Use `[OPEN] ITEM-1 | Description` in notes and reuse `ITEM-1` in a later meeting with `IN_PROGRESS`, `BLOCKED`, `DONE`, or `DECIDED`. These are reported states, not verified completion or policy approval. Unmentioned items are never assumed complete. Arbitrary free text is compared literally, without semantic status inference.

**Load two-meeting demo** saves a fictional September 1 meeting and loads September 8 notes. Retrieve context to see a reported completed owner assignment, policy review in progress, a new reminder proposal, and an accessibility blocker carried forward. Save each real demo meeting explicitly; generating a document alone does not save it to the timeline. Same-day and future meetings are excluded from comparisons. Previous drafts are not automatically backfilled.

Generate standalone artifacts with:

```bash
python meeting_demo.py
```

Expected output: PILOT-1 OPEN → DONE (reported); RULE-1 OPEN → IN_PROGRESS; REMINDER-1 new OPEN; ACCESS-1 BLOCKED carried forward. Files: `outputs/meeting-brd.docx`, `.html`, `.json`, and `meeting-copilot-brief.txt`. Earlier meeting citations and snapshots survive Copilot response import, document edits, and export. See `PLAN.md` for shared-project rollout requirements.

## Architecture diagrams and future integrations

See [architecture and roadmap](docs/ARCHITECTURE.md), the [demo architecture diagram](docs/diagrams/architecture-overview.svg), and [editable Mermaid source](docs/diagrams/enterprise-architecture.mmd). The design uses Zoom transcript uploads and manual notes as the preferred input paths; dedicated transcript processing and live connectors are future work. OneNote is deferred. Current and proposed capabilities are explicitly labeled.
