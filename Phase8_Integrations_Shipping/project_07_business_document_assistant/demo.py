"""Create reproducible fictional demo deliverables without running a server or AI."""
import json
from pathlib import Path
from domain import (BASE, SAMPLE_NOTES, SOURCES, TEMPLATES, copilot_brief, generate,
                    page_html, storage_html, validate_request, word_bytes)


def main():
    output = BASE / 'outputs'
    output.mkdir(exist_ok=True)
    for kind in TEMPLATES:
        request = validate_request({'title': 'Meeting room booking improvements',
            'kind': kind, 'notes': SAMPLE_NOTES, 'source_ids': [s['id'] for s in SOURCES]})
        doc = dict(generate(request), revision=1, status='ready')
        (output / f'{kind}.docx').write_bytes(word_bytes(doc))
        # Standalone preview shares the same renderer, with CSS embedded for file viewing.
        css = (BASE / 'static/page.css').read_text()
        (output / f'{kind}.html').write_text(page_html(doc).replace('<link rel="stylesheet" href="/static/page.css">', f'<style>{css}</style>'))
        (output / f'{kind}.json').write_text(json.dumps(doc, indent=2))
        (output / f'{kind}-copilot-brief.txt').write_text(copilot_brief(request))
        (output / f'{kind}-sample-response.json').write_text(json.dumps({'sections': doc['sections']}, indent=2))
        # Payload preview only: never sent to Confluence.
        (output / f'{kind}-confluence-payload.json').write_text(json.dumps({
            'spaceId': 'DEMO_SPACE_ID', 'parentId': 'DEMO_PARENT_ID', 'status': 'current',
            'title': doc['title'], 'body': {'representation': 'storage', 'value': storage_html(doc)}}, indent=2))
    print(f'Created 18 fictional demo artifacts in {output}')
    print('Sample responses are deterministic fixtures, not actual Copilot output. Nothing was published.')


if __name__ == '__main__':
    main()
