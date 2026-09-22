# POC validation record

Validated locally on 2026-09-21 (America/Chicago) using the bundled Python 3.12 runtime.

## Automated checks

- `python -m unittest discover -s tests -v`: **46 tests passed**.
- JavaScript syntax check: `node --check static/app.js` passed.
- Python compilation check passed.
- Git whitespace check passed.

Tests cover template structure, selected-source citations, the fictional policy conflict, input validation, HTML escaping, Word content, manual-response import including malformed/null responses, ownership isolation, persistent session cookies, stale revisions, approval enforcement and invalidation, publication snapshots/idempotency, HTTP endpoints, CSRF/origin/Host checks, and interrupted-job recovery.

RAG checks additionally cover glossary expansion, ambiguous FHP definitions, domain filtering, unknown-term acknowledgement, empty matches, restricted and superseded fixture exclusion, source previews, session-owned retrieval snapshots, stale inputs/index versions, required definition evidence, source tampering, index rebuilds, and retrieval provenance after Copilot-response import.

## Manual verification

- Opened the actual browser app and retrieved context for fictional Cobra meeting notes.
- Confirmed that All domains flags FHP as ambiguous, then selected the Workplace definition and verified that lab evidence was excluded.
- Reviewed retrieved excerpts, glossary definitions, source titles, versions, and preview links.
- Generated an offline BRD with the expected 30-day proposal versus 14-day source-policy disagreement and citations.
- Approved a revision, confirmed a demo destination, and created a local publication snapshot.
- The earlier baseline UI verification prepared a Copilot brief and imported a deterministic test response; the new automated checks verify preservation of RAG provenance on import. **No actual Copilot model call was made during verification.**
- Generated 16 RAG artifacts using `rag_demo.py`, including retrieval evidence, three document flavors, and manual Copilot handoff files. The original `demo.py` remains available for the baseline examples.
- Rendered the RAG BRD, user stories, and change request DOCX exports and visually inspected all nine final pages. Each sample has three pages, including source and retrieval provenance.

## Not verified or implemented

No live Confluence, organization SSO, real AI inference, production deployment, enterprise authorization, or load test was performed. Retrieval uses SQLite FTS5/BM25 and a curated fictional glossary; semantic embeddings are not implemented. Fixture audience filtering is not enterprise access control. The activity log is not a compliance audit system. The sample conflict checker is not a semantic evaluator. A shared rollout requires the work described in `ROLLOUT.md` and `../PLAN.md`.

## Meeting continuity verification

- Seven additional tests cover reported transitions, unresolved carry-forward, reopened items, chronological selection, project/session/date isolation, idempotent saves, invalid tracking data, stale history, citation validation, immutable snapshots, Copilot import, and Word content.
- Browser walkthrough loaded the two-meeting fixture, retrieved the timeline and Confluence evidence, and generated a draft with M1/N1/S citations.
- Ran `python meeting_demo.py`; rendered the resulting Word document and checked its three-page layout. Compacted provenance to remove a nearly empty overflow page.
- Progress inference from arbitrary prose and real Copilot calls remain unverified/unimplemented. The demo uses explicit author-reported item states and literal text comparison.
