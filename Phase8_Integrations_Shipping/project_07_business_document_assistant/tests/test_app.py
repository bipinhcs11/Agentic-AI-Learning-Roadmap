import io
import json
import sys
import tempfile
import threading
import time
import unittest
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener
from http.server import ThreadingHTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import Application, make_handler
from domain import (SAMPLE_NOTES, SOURCES, TEMPLATES, copilot_brief, generate,
                    offline_sections, page_html, validate_request, word_bytes)
from store import Conflict, Store


def request_data(**updates):
    return dict(title='Meeting room booking improvements', notes=SAMPLE_NOTES,
                kind='brd', source_ids=[s['id'] for s in SOURCES], **updates)


class DomainTests(unittest.TestCase):
    def setUp(self):
        self.request = validate_request(request_data())

    def test_all_templates_and_source_citations(self):
        for kind in TEMPLATES:
            doc = generate(dict(self.request, kind=kind))
            self.assertEqual([s['heading'] for s in doc['sections']], TEMPLATES[kind]['headings'])
            self.assertIn('[N1]', doc['sections'][1]['body'])
            for source in SOURCES:
                self.assertIn(f"[{source['citation']}]", doc['sections'][2]['body'])

    def test_conflict_is_flagged_and_not_resolved_as_fact(self):
        doc = generate(self.request)
        self.assertIn('14', doc['warnings'][0])
        self.assertIn('30', doc['warnings'][0])
        self.assertIn('must decide', doc['warnings'][0])

    def test_unselected_policy_not_used(self):
        data = request_data(); data['source_ids'] = ['accessibility-standard']
        doc = generate(validate_request(data))
        self.assertFalse(doc['warnings'])
        self.assertNotIn('[S1]', doc['sections'][2]['body'])

    def test_invalid_inputs(self):
        for field, value in [('title', ''), ('title', []), ('kind', 'unknown'),
                             ('kind', []), ('notes', 'line\n' * 121), ('notes', 'x' * 24001), ('notes', 'bad\x00'),
                             ('source_ids', []), ('source_ids', ['unknown']),
                             ('source_ids', ['booking-policy', 'booking-policy'])]:
            data = request_data(); data[field] = value
            with self.subTest(field=field, value=str(value)[:30]), self.assertRaises(ValueError):
                validate_request(data)

    def test_copilot_brief_contains_selected_evidence_and_schema(self):
        brief = copilot_brief(self.request)
        self.assertIn('Return ONLY a JSON object', brief)
        self.assertIn('14 days', brief)
        self.assertIn('30 days', brief)
        self.assertIn('Open questions and conflicts', brief)

    def test_copilot_import_rejects_missing_sections_or_bad_citations(self):
        sections = offline_sections(self.request)
        with self.assertRaises(ValueError):
            generate(self.request, sections[:-1])
        sections[1]['body'] += ' Invented rule [S99]'
        with self.assertRaises(ValueError):
            generate(self.request, sections)

    def test_copilot_import_requires_note_and_source_citations(self):
        for index in (1, 2):
            sections = offline_sections(self.request)
            sections[index]['body'] = 'Unreferenced content'
            with self.assertRaises(ValueError):
                generate(self.request, sections)

    def test_html_escapes_content(self):
        doc = generate(self.request)
        doc['sections'][0]['body'] = '<script>alert(1)</script>'
        doc['title'] = '<img src=x onerror=alert(1)>'
        rendered = page_html(doc)
        self.assertNotIn('<script>', rendered)
        self.assertNotIn('<img', rendered)
        self.assertIn('&lt;script&gt;', rendered)

    def test_word_export_contains_edited_text_and_provenance(self):
        from docx import Document
        doc = generate(self.request)
        doc['sections'][0]['body'] = 'A reviewed purpose.'
        paragraphs = '\n'.join(p.text for p in Document(io.BytesIO(word_bytes(doc))).paragraphs)
        for text in ('A reviewed purpose.', '[S1]', 'version 3', 'Input SHA256:', 'Fictional educational example'):
            self.assertIn(text, paragraphs)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / 'test.db')
        self.request = validate_request(request_data())
        self.doc = self.store.create('alice', self.request)
        self.key = self.doc['id']
        self.store.mutate('alice', self.key, 'generated', generate(self.request))

    def tearDown(self):
        self.temp.cleanup()

    def test_cross_session_access_denied(self):
        with self.assertRaises(KeyError):
            self.store.get('bob', self.key)
        with self.assertRaises(KeyError):
            self.store.mutate('bob', self.key, 'approve', {'revision': 1, 'reviewed': True})
        self.assertEqual(self.store.listing('bob'), [])

    def test_approval_required_for_publication(self):
        with self.assertRaises(Conflict):
            self.store.mutate('alice', self.key, 'publish', {'revision': 1, 'parent': 'product-discovery'})
        with self.assertRaises(ValueError):
            self.store.mutate('alice', self.key, 'approve', {'revision': 1, 'reviewed': False})

    def test_edit_invalidates_approval_and_preserves_published_snapshot(self):
        self.store.mutate('alice', self.key, 'approve', {'revision': 1, 'reviewed': True})
        doc = self.store.mutate('alice', self.key, 'publish', {'revision': 1, 'parent': 'product-discovery'})
        original = doc['sections'][0]['body']
        doc['sections'][0]['body'] = 'Edited purpose'
        changed = self.store.mutate('alice', self.key, 'save', {'revision': 1, 'sections': doc['sections']})
        self.assertEqual(changed['revision'], 2)
        self.assertIsNone(changed['approved_revision'])
        self.assertEqual(changed['publications'][0]['snapshot']['sections'][0]['body'], original)
        with self.assertRaises(Conflict):
            self.store.mutate('alice', self.key, 'publish', {'revision': 2, 'parent': 'product-discovery'})

    def test_duplicate_publish_is_idempotent(self):
        self.store.mutate('alice', self.key, 'approve', {'revision': 1, 'reviewed': True})
        for _ in range(2):
            doc = self.store.mutate('alice', self.key, 'publish', {'revision': 1, 'parent': 'product-discovery'})
        self.assertEqual(len(doc['publications']), 1)
        self.assertEqual(sum(e['action'] == 'publish' for e in doc['events']), 1)

    def test_stale_revision_rejected(self):
        with self.assertRaises(Conflict):
            self.store.mutate('alice', self.key, 'approve', {'revision': 0, 'reviewed': True})

    def test_copilot_import_workflow(self):
        pending = self.store.create('alice', self.request)
        self.store.mutate('alice', pending['id'], 'awaiting_copilot', self.request)
        data = {'result': {'sections': offline_sections(self.request)}}
        imported = self.store.mutate('alice', pending['id'], 'import', data)
        self.assertEqual(imported['provider'], 'copilot-assisted')
        self.assertNotIn('brief', imported)
        with self.assertRaises(Conflict):
            self.store.mutate('alice', pending['id'], 'import', data)

    def test_null_copilot_sections_cannot_fall_back_to_offline(self):
        pending = self.store.create('alice', self.request)
        self.store.mutate('alice', pending['id'], 'awaiting_copilot', self.request)
        with self.assertRaises(ValueError):
            self.store.mutate('alice', pending['id'], 'import', {'result': {'sections': None}})
        self.assertEqual(self.store.get('alice', pending['id'])['status'], 'awaiting_copilot')

    def test_recovery_marks_interrupted_jobs_failed(self):
        pending = self.store.create('alice', self.request)
        recovered = Store(self.store.path)
        self.assertEqual(recovered.get('alice', pending['id'])['status'], 'failed')
        self.assertEqual(recovered.get('alice', self.key)['status'], 'ready')


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.app = Application(cls.temp.name)
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(cls.app))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.app.close(); cls.temp.cleanup()

    def setUp(self):
        self.client = build_opener(HTTPCookieProcessor(CookieJar()))
        with self.client.open(self.base + '/api/config') as response:
            self.csrf = json.load(response)['csrf']

    def call(self, path, data=None, headers=None):
        if path == '/api/documents' and isinstance(data, dict) and data.get('notes') and 'retrieval_id' not in data:
            data = dict(data)
            with self.call('/api/retrieve', {'title': data['title'], 'notes': data['notes'], 'domain': 'workplace'}, headers) as response:
                context = json.load(response)
            data.update(retrieval_id=context['id'], domain='workplace', context_confirmed=True,
                        source_ids=[s['id'] for s in context['sources']])
        request = Request(self.base + path, data=json.dumps(data).encode() if data is not None else None,
                          headers={'Content-Type': 'application/json', 'X-CSRF-Token': self.csrf, **(headers or {})})
        return self.client.open(request)

    def test_offline_lifecycle_and_export(self):
        with self.call('/api/documents', request_data()) as response:
            self.assertEqual(response.status, 202); doc = json.load(response)
        path = '/api/documents/' + doc['id']
        for _ in range(30):
            with self.call(path) as response: doc = json.load(response)
            if doc['status'] == 'ready': break
            time.sleep(.05)
        self.assertEqual(doc['status'], 'ready')
        with self.call(path + '/word') as response:
            self.assertTrue(response.read().startswith(b'PK'))
            self.assertIn('.docx', response.headers['Content-Disposition'])
        with self.call(path + '/approve', {'revision': 1, 'reviewed': True}) as response:
            self.assertEqual(json.load(response)['status'], 'approved')
        with self.call(path + '/publish', {'revision': 1, 'parent': 'product-discovery'}) as response:
            self.assertEqual(json.load(response)['status'], 'published')
        with self.call(path + '/page') as response:
            self.assertIn(b'NOTHING WAS PUBLISHED EXTERNALLY', response.read())

    def test_csrf_and_origin_rejected(self):
        for headers in ({'X-CSRF-Token': 'bad'}, {'Origin': 'https://evil.example'}):
            with self.assertRaises(HTTPError) as error:
                self.call('/api/documents', request_data(), headers)
            self.assertEqual(error.exception.code, 403)

    def test_invalid_host_rejected(self):
        with self.assertRaises(HTTPError) as error:
            self.call('/api/config', headers={'Host': 'evil.example'})
        self.assertEqual(error.exception.code, 403)

    def test_session_cookie_survives_app_restart(self):
        owner, csrf, _ = self.app.session('')
        with tempfile.TemporaryDirectory() as temp:
            app = Application(temp)
            owner, csrf, _ = app.session('')
            app.close()
            reopened = Application(temp)
            try:
                self.assertEqual(reopened.session('bda_session=' + owner), (owner, csrf, False))
            finally:
                reopened.close()

    def test_http_copilot_import_and_session_isolation(self):
        data = request_data(); data['mode'] = 'copilot'
        with self.call('/api/documents', data) as response: doc = json.load(response)
        path = '/api/documents/' + doc['id']
        self.assertEqual(doc['status'], 'awaiting_copilot')
        with self.call(path + '/brief') as response: self.assertIn(b'EVIDENCE', response.read())
        other = build_opener(HTTPCookieProcessor(CookieJar()))
        with self.assertRaises(HTTPError) as error: other.open(self.base + path)
        self.assertEqual(error.exception.code, 404)
        with self.call(path + '/import', {'result': {'sections': offline_sections(doc)}}) as response:
            self.assertEqual(json.load(response)['provider'], 'copilot-assisted')

    def test_validation_errors_return_400(self):
        for data in ([], {'title': 'Missing notes'}):
            with self.assertRaises(HTTPError) as error: self.call('/api/documents', data)
            self.assertEqual(error.exception.code, 400)

    def test_retrieval_route_and_source_preview(self):
        from retrieval import RAG_NOTES
        with self.call('/api/retrieve', {'title': 'Cobra readiness', 'notes': RAG_NOTES, 'domain': 'workplace'}) as response:
            result = json.load(response)
        self.assertEqual(len(result['terms']), 2)
        with self.call('/api/sources/fhp-workplace') as response:
            self.assertIn(b'Facility Handover Plan', response.read())
        with self.assertRaises(HTTPError) as error:
            self.call('/api/sources/restricted-cobra')
        self.assertEqual(error.exception.code, 404)
        with self.assertRaises(HTTPError) as error:
            self.call('/api/documents', {'title': 'Cobra readiness', 'notes': RAG_NOTES + ' Changed.',
                'domain': 'workplace', 'kind': 'brd', 'retrieval_id': result['id'],
                'source_ids': [s['id'] for s in result['sources']], 'context_confirmed': True})
        self.assertEqual(error.exception.code, 409)

    def test_version_routes_and_readable_ui(self):
        with self.call('/api/baselines', {'title': 'Existing architecture', 'content': 'Cobra room readiness.', 'kind': 'architecture'}) as response:
            original = json.load(response)
        data = request_data(); data.update(kind='architecture', workflow='revise', base_document_id=original['id'], base_revision=1)
        with self.call('/api/documents', data) as response: version = json.load(response)
        path = '/api/documents/' + version['id']
        for _ in range(30):
            with self.call(path) as response: version = json.load(response)
            if version['status'] == 'ready': break
            time.sleep(.05)
        self.assertEqual(version['status'], 'ready')
        self.assertEqual(version['document_version'], '1.1')
        self.assertEqual([e['action'] for e in version['events']], ['queued', 'generating', 'generated'])
        with self.call(path + '/versions') as response:
            self.assertEqual([d['document_version'] for d in json.load(response)], ['1.0', '1.1'])
        with self.call(path + '/edits') as response:
            self.assertEqual(len(json.load(response)), 1)
        other = build_opener(HTTPCookieProcessor(CookieJar()))
        for suffix in ('versions', 'edits'):
            with self.assertRaises(HTTPError) as error: other.open(self.base + path + '/' + suffix)
            self.assertEqual(error.exception.code, 404)
        with self.call('/') as response:
            markup = response.read().decode()
            self.assertNotIn('Copilot response (JSON)', markup)
            self.assertNotIn('Copy brief', markup)
            self.assertIn('Create a new version', markup)

    def test_static_asset_and_traversal(self):
        with self.call('/static/app.js') as response:
            self.assertIn('script-src', response.headers['Content-Security-Policy'])
        with self.assertRaises(HTTPError) as error: self.call('/static/../app.py')
        self.assertEqual(error.exception.code, 404)


if __name__ == '__main__':
    unittest.main()
