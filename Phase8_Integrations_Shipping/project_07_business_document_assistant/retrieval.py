"""Local lexical RAG: section index, BM25, and explicit fictional glossary lookup.

No embedding model, external API, or live Confluence permissions are used.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
CORPUS = BASE / 'fixtures/confluence-pages.json'
RAG_NOTES = (BASE / 'fixtures/cobra-meeting-notes.txt').read_text()
DOMAINS = {'all': 'All domains', 'workplace': 'Workplace', 'lab': 'Lab Operations'}
STOP = set('a an the and or to in of for on with is are be by at it its as from that this those these should must can will we our their they proposed team improve new update please using use support need needs what who how when before after show display open question fictional educational example meeting discovery brd api ui json html'.split())


def tokens(text):
    return [t for t in re.findall(r'[a-z0-9]+', text.lower()) if len(t) > 1 and t not in STOP]


def fingerprint(title, notes, domain):
    return hashlib.sha256(json.dumps([title, notes, domain], ensure_ascii=False).encode()).hexdigest()


def domain_value(value):
    if not isinstance(value, str) or value not in DOMAINS:
        raise ValueError('Choose a supported business domain.')
    return value


class KnowledgeIndex:
    def __init__(self, path, corpus=CORPUS):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        pages = json.loads(Path(corpus).read_text())
        # Apply fixture access/status scope BEFORE glossary building, search, and previews.
        self.pages = {p['id']: p for p in pages if p['audience'] == 'demo' and p['status'] == 'current'}
        canonical = json.dumps(list(self.pages.values()), sort_keys=True)
        self.index_version = hashlib.sha256(canonical.encode()).hexdigest()
        self.chunks = {}
        self.glossary = {}
        for page in self.pages.values():
            for section in page['sections']:
                key = page['id'] + ':' + section['id']
                chunk = {k: page[k] for k in ('title', 'space', 'domain', 'version')}
                chunk.update(id=key, page_id=page['id'], heading=section['heading'], text=section['text'],
                             citation=section['citation'], url=f"https://fictional.example/wiki/spaces/{page['space']}/pages/{page['id']}#{section['id']}")
                self.chunks[key] = chunk
                for term in section.get('terms', []):
                    candidate = dict(term, source_id=key, citation=section['citation'], domain=page['domain'],
                                     page_title=page['title'], version=page['version'])
                    self.glossary.setdefault(term['term'].lower(), []).append(candidate)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS index_meta (version TEXT NOT NULL)')
            db.execute('CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(id UNINDEXED, title, heading, body, aliases, domain UNINDEXED)')
            row = db.execute('SELECT version FROM index_meta').fetchone()
            if not row or row[0] != self.index_version:
                db.execute('DELETE FROM chunks')
                for key, chunk in self.chunks.items():
                    aliases = [a for candidates in self.glossary.values() for term in candidates
                               if term['source_id'] == key for a in [term['term'], term['definition'], *term['aliases']]]
                    db.execute('INSERT INTO chunks VALUES (?,?,?,?,?,?)',
                               (key, chunk['title'], chunk['heading'], chunk['text'], ' '.join(aliases), chunk['domain']))
                db.execute('DELETE FROM index_meta')
                db.execute('INSERT INTO index_meta VALUES (?)', (self.index_version,))

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def term_lookup(self, text, domain, choices):
        found, consumed = [], set()
        for term, candidates in self.glossary.items():
            aliases = {term} | {a.lower() for c in candidates for a in c['aliases']}
            if not any(re.search(r'(?<!\w)' + re.escape(a) + r'(?!\w)', text, re.I) for a in aliases):
                continue
            consumed.add(term)
            scoped = [c for c in candidates if domain == 'all' or c['domain'] == domain]
            selected = choices.get(term)
            if selected is not None and selected not in [c['source_id'] for c in scoped]:
                raise ValueError('The chosen definition is not available in this domain.')
            resolved = next((c for c in scoped if c['source_id'] == selected), None)
            if resolved is None and len(scoped) == 1:
                resolved = scoped[0]
            found.append({'term': candidates[0]['term'], 'status': 'resolved' if resolved else ('ambiguous' if scoped else 'unknown'),
                          'candidates': scoped, 'selected': resolved})
        # Uppercase acronym heuristic only; ordinary unknown product names may need explicit review.
        for acronym in sorted(set(re.findall(r'\b[A-Z][A-Z0-9]{1,7}\b', text))):
            if acronym.lower() not in consumed and acronym.lower() not in STOP:
                found.append({'term': acronym, 'status': 'unknown', 'candidates': [], 'selected': None})
        if set(choices) - consumed:
            raise ValueError('Definition choices must refer to terms present in these notes.')
        return found

    def search(self, title, notes, domain='all', choices=None):
        domain_value(domain)
        choices = {} if choices is None else choices
        if not isinstance(choices, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in choices.items()):
            raise ValueError('Definition choices must map a term to a source ID.')
        # Tracking labels/IDs are metadata, not unknown business acronyms.
        query = title + '\n' + re.sub(r'^\s*\[(?:OPEN|IN_PROGRESS|DONE|BLOCKED|DECIDED)\]\s+[A-Za-z0-9_-]{1,40}\s*\|\s*', '', notes, flags=re.M)
        terms = self.term_lookup(query, domain, choices)
        resolved = [t['selected'] for t in terms if t['selected']]
        expanded = query + ' ' + ' '.join(t['definition'] for t in resolved)
        words = list(dict.fromkeys(tokens(expanded)))[:80]
        ranked = []
        if words:
            expression = ' OR '.join('"' + word + '"' for word in words)
            with self.connect() as db:
                rows = db.execute('SELECT id, bm25(chunks, 0, 3, 2, 1, 4, 0) AS score FROM chunks WHERE chunks MATCH ? AND (? = \'all\' OR domain = ?) ORDER BY score, id LIMIT 30',
                                  (expression, domain, domain)).fetchall()
            for key, score in rows:
                chunk = self.chunks[key]
                matched = sorted(set(words) & set(tokens(chunk['title'] + ' ' + chunk['heading'] + ' ' + chunk['text'])))
                ranked.append(dict(chunk, score=round(-score, 6), reason='Keyword match: ' + ', '.join(matched[:8])))
        # Do not retrieve alternate-definition chunks after explicit disambiguation.
        excluded = {c['source_id'] for t in terms if t['selected'] for c in t['candidates']
                    if c['source_id'] != t['selected']['source_id']}
        resolved_domains = {t['domain'] for t in resolved}
        if domain == 'all' and resolved_domains and not any(t['status'] == 'ambiguous' for t in terms):
            ranked = [c for c in ranked if c['domain'] in resolved_domains]
        pinned = [dict(self.chunks[t['source_id']], score=None,
                       reason=f"Definition evidence for {t['term']}") for t in resolved]
        seen = {c['id'] for c in pinned}
        evidence = pinned + [c for c in ranked if c['id'] not in seen and c['id'] not in excluded]
        evidence = evidence[:8]
        for rank, chunk in enumerate(evidence, 1):
            chunk['rank'] = rank
        return {'title': title, 'notes': notes, 'domain': domain, 'choices': choices,
                'input_fingerprint': fingerprint(title, notes, domain), 'terms': terms,
                'sources': evidence, 'index_version': self.index_version,
                'method': 'SQLite FTS5 BM25 + glossary expansion (lexical, no embeddings)',
                'page_count': len(self.pages), 'chunk_count': len(self.chunks),
                'unresolved': [f"{t['term']}: {'multiple definitions; choose a meaning' if t['status'] == 'ambiguous' else 'no definition found in the selected domain'}"
                               for t in terms if t['status'] != 'resolved']}

    def page_html(self, page_id):
        if page_id not in self.pages:
            raise KeyError('Source page is unavailable.')
        page = self.pages[page_id]
        esc = html.escape
        body = f"<p class='badge'>FICTIONAL CONFLUENCE SOURCE · LOCAL INDEX PREVIEW</p><h1>{esc(page['title'])}</h1>"
        body += f"<p>Space {esc(page['space'])} · {esc(DOMAINS[page['domain']])} · Version {page['version']}</p>"
        for section in page['sections']:
            body += f"<section id='{esc(section['id'])}'><h2>{esc(section['heading'])}</h2><p>[{esc(section['citation'])}] {esc(section['text'])}</p></section>"
        return '<!doctype html><html lang="en"><meta charset="utf-8"><title>Fictional source preview</title><link rel="stylesheet" href="/static/page.css"><main>' + body + '</main></html>'
