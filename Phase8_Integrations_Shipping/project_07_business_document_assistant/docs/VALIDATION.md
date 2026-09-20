# POC validation record

Validated locally on 2026-09-19 (America/Chicago) using the bundled Python 3.12 runtime.

## Automated checks

- `python -m unittest discover -s tests -v`: **24 tests passed**.
- JavaScript syntax check: `node --check static/app.js` passed.
- Python compilation check passed.
- Git whitespace check passed.

Tests cover template structure, selected-source citations, the fictional policy conflict, input validation, HTML escaping, Word content, manual-response import including malformed/null responses, ownership isolation, persistent session cookies, stale revisions, approval enforcement and invalidation, publication snapshots/idempotency, HTTP endpoints, CSRF/origin/Host checks, and interrupted-job recovery.

## Manual verification

- Opened the actual browser app and loaded fictional sample input.
- Generated an offline BRD with the expected policy disagreement and citations.
- Approved a revision, confirmed a demo destination, and created a local publication snapshot.
- Prepared a Copilot brief and imported a deterministic test response through the UI. **No actual Copilot model call was made during verification.**
- Generated all 18 sample artifacts using `demo.py`.
- Rendered BRD, user stories, and change request DOCX exports and inspected all final pages. Each sample has two pages. Fixed a default title border and unwanted page break during this review.

## Not verified or implemented

No live Confluence, organization SSO, real AI inference, production deployment, enterprise authorization, or load test was performed. The activity log is not a compliance audit system. The sample conflict checker is not a semantic evaluator. A shared rollout requires the work described in `ROLLOUT.md`.
