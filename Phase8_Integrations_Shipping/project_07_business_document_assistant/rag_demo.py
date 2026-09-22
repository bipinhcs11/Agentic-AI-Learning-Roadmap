"""Build fictional retrieval evidence and grounded sample artifacts, entirely offline."""
import json
from app import Application
from domain import BASE, TEMPLATES, copilot_brief, generate, page_html, word_bytes
from retrieval import RAG_NOTES


def main():
    app = Application(BASE / 'runtime' / 'rag-demo')
    output = BASE / 'outputs'
    output.mkdir(exist_ok=True)
    data = {'title': 'Cobra room readiness improvements', 'notes': RAG_NOTES, 'domain': 'workplace'}
    try:
        result = app.retrieve('offline-demo', data)
        (output / 'rag-retrieval.json').write_text(json.dumps(result, indent=2))
        for kind in TEMPLATES:
            request = app.prepare('offline-demo', dict(data, kind=kind, retrieval_id=result['id'],
                context_confirmed=True, source_ids=[s['id'] for s in result['sources']]))
            doc = dict(generate(request), revision=1, status='ready')
            prefix = output / f'rag-{kind}'
            prefix.with_suffix('.docx').write_bytes(word_bytes(doc))
            prefix.with_suffix('.json').write_text(json.dumps(doc, indent=2))
            css = (BASE / 'static/page.css').read_text()
            prefix.with_suffix('.html').write_text(page_html(doc).replace('<link rel="stylesheet" href="/static/page.css">', f'<style>{css}</style>'))
            (output / f'rag-{kind}-copilot-brief.txt').write_text(copilot_brief(request))
            (output / f'rag-{kind}-sample-response.json').write_text(json.dumps({'sections': doc['sections']}, indent=2))
        print(f"Indexed {result['page_count']} fictional pages / {result['chunk_count']} sections.")
        for term in result['terms']:
            print(f"{term['term']} = {term['selected']['definition']} [{term['selected']['citation']}]")
        print('Retrieved: ' + ', '.join(s['citation'] for s in result['sources']))
        print(f'Created 16 RAG demo artifacts in {output}. No AI call or external publication.')
    finally:
        app.close()


if __name__ == '__main__':
    main()
