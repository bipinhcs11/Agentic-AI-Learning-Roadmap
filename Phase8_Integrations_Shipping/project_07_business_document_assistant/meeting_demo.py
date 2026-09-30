"""Reproducible fictional meeting-history + business-context demo."""
import json
from app import Application
from domain import BASE, generate, word_bytes, page_html, copilot_brief

EARLIER = {'project': 'Fictional Cobra pilot', 'meeting_date': '2026-09-01', 'title': 'Cobra discovery',
    'notes': 'FICTIONAL EDUCATIONAL EXAMPLE\nDiscuss Cobra and FHP room readiness.\n[OPEN] PILOT-1 | Assign a pilot owner.\n[OPEN] RULE-1 | Ask the policy owner about 30 days in advance.\n[BLOCKED] ACCESS-1 | Review room accessibility.'}
CURRENT = {'project': 'Fictional Cobra pilot', 'meeting_date': '2026-09-08', 'title': 'Cobra pilot follow-up', 'domain': 'workplace',
    'notes': 'FICTIONAL EDUCATIONAL EXAMPLE\nFollow up on Cobra and FHP readiness.\n[DONE] PILOT-1 | Fictional team reports a pilot owner was assigned.\n[IN_PROGRESS] RULE-1 | Policy owner is reviewing 30 days in advance; no approval yet.\n[OPEN] REMINDER-1 | Explore reminders for an incomplete handover checklist.'}


def main():
    app = Application(BASE / 'runtime' / 'meeting-demo')
    out = BASE / 'outputs'
    out.mkdir(exist_ok=True)
    try:
        app.save_meeting('offline-demo', EARLIER)
        result = app.retrieve('offline-demo', CURRENT)
        request = app.prepare('offline-demo', dict(CURRENT, kind='brd', retrieval_id=result['id'],
            context_confirmed=True, source_ids=[s['id'] for s in result['sources']]))
        doc = dict(generate(request), status='ready', revision=1)
        (out / 'meeting-brd.docx').write_bytes(word_bytes(doc))
        (out / 'meeting-brd.html').write_text(page_html(doc).replace('<link rel="stylesheet" href="/static/page.css">',
            '<style>' + (BASE / 'static/page.css').read_text() + '</style>'))
        (out / 'meeting-brd.json').write_text(json.dumps(doc, indent=2))
        (out / 'meeting-copilot-brief.txt').write_text(copilot_brief(request))
        print('PILOT-1: OPEN → DONE (reported); RULE-1: OPEN → IN_PROGRESS; REMINDER-1: new OPEN.')
        print('ACCESS-1: BLOCKED carried forward. No policy approval inferred.')
        print(f'Created meeting-brd.docx, .html, .json and meeting-copilot-brief.txt in {out}.')
    finally:
        app.close()


if __name__ == '__main__':
    main()
