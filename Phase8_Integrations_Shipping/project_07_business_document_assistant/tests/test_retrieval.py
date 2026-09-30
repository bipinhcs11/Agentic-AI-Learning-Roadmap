import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import Application
from domain import generate, word_bytes, copilot_brief
from retrieval import CORPUS, KnowledgeIndex, RAG_NOTES
from store import Conflict


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = Application(self.temp.name)
        self.data = {'title': 'Cobra room readiness improvements', 'notes': RAG_NOTES, 'domain': 'workplace'}

    def tearDown(self):
        self.app.close()
        self.temp.cleanup()

    def prepared(self, result=None, **updates):
        result = result or self.app.retrieve('alice', self.data)
        return self.app.prepare('alice', dict(self.data, kind='brd', retrieval_id=result['id'],
            source_ids=[s['id'] for s in result['sources']], context_confirmed=True, **updates))

    def test_workplace_definitions_are_retrieved_with_policy_evidence(self):
        result = self.app.retrieve('alice', self.data)
        meanings = {t['term']: t['selected']['definition'] for t in result['terms']}
        self.assertEqual(meanings['Cobra'], 'Coordinated Booking and Room Allocation')
        self.assertEqual(meanings['FHP'], 'Facility Handover Plan')
        ids = {s['id'] for s in result['sources']}
        self.assertIn('cobra-booking:window', ids)
        self.assertIn('fhp-workplace:release', ids)
        self.assertNotIn('cafeteria:menu', ids)
        self.assertTrue(all(s['reason'] and s['heading'] and s['url'] for s in result['sources']))

    def test_ambiguous_fhp_blocks_drafting_until_choice(self):
        data = dict(self.data, domain='all')
        result = self.app.retrieve('alice', data)
        fhp = next(t for t in result['terms'] if t['term'] == 'FHP')
        self.assertEqual(fhp['status'], 'ambiguous')
        self.assertEqual(len(fhp['candidates']), 2)
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            self.app.prepare('alice', dict(data, kind='brd', retrieval_id=result['id'],
                source_ids=[s['id'] for s in result['sources']], context_confirmed=True))
        resolved = self.app.retrieve('alice', dict(data, choices={'fhp': 'fhp-workplace:definition'}))
        self.assertFalse(resolved['unresolved'])
        self.assertFalse(any(s['domain'] == 'lab' for s in resolved['sources']))

    def test_lab_domain_selects_other_meaning(self):
        result = self.app.retrieve('alice', {'title': 'Instrument checkout', 'notes': 'Apply FHP calibration rules.', 'domain': 'lab'})
        self.assertEqual(result['terms'][0]['selected']['definition'], 'Field Hardware Protocol')
        self.assertTrue(all(s['domain'] == 'lab' for s in result['sources']))

    def test_lowercase_term_and_alias_lookup(self):
        result = self.app.index.search('handover', 'cobra and facility handover', 'workplace')
        self.assertEqual({t['term'] for t in result['terms']}, {'Cobra', 'FHP'})

    def test_unknown_acronym_requires_acknowledgment_and_survives_export(self):
        self.data['notes'] += '\nWhat does QZX mean for Cobra?'
        result = self.app.retrieve('alice', self.data)
        self.assertIn('QZX', result['unresolved'][0])
        with self.assertRaisesRegex(ValueError, 'Acknowledge'):
            self.prepared(result)
        request = self.prepared(result, acknowledge_unresolved=True)
        doc = generate(request)
        self.assertIn('QZX', doc['sections'][-1]['body'])
        from docx import Document
        text = '\n'.join(p.text for p in Document(io.BytesIO(word_bytes(doc))).paragraphs)
        self.assertIn('QZX', text)
        self.assertIn('Facility Handover Plan', text)

    def test_no_match_does_not_fabricate_context(self):
        self.data.update(title='zzzyyy', notes='zzzyyy qqqxxx')
        result = self.app.retrieve('alice', self.data)
        self.assertEqual(result['sources'], [])
        with self.assertRaisesRegex(ValueError, 'at least one'):
            self.prepared(result)

    def test_restricted_and_superseded_content_not_indexed_or_previewed(self):
        result = self.app.index.search('Cobra', 'RESTRICTED_TEST_SENTINEL obsolete 60 90 days')
        encoded = json.dumps(result)
        for forbidden in ('S112', 'S113', 'Restricted fictional Cobra prototype', 'Superseded Cobra booking policy'):
            self.assertNotIn(forbidden, encoded)
        for page in ('restricted-cobra', 'old-cobra-policy'):
            with self.assertRaises(KeyError): self.app.index.page_html(page)

    def test_foreign_retrieval_rejected(self):
        result = self.app.retrieve('bob', self.data)
        with self.assertRaises(KeyError): self.prepared(result)

    def test_stale_input_or_index_rejected(self):
        result = self.app.retrieve('alice', self.data)
        self.data['notes'] += '\nAdditional decision.'
        with self.assertRaises(Conflict): self.prepared(result)
        self.data['notes'] = RAG_NOTES
        self.app.index.index_version = 'changed'
        with self.assertRaises(Conflict): self.prepared(result)

    def test_context_confirmation_and_required_definitions(self):
        result = self.app.retrieve('alice', self.data)
        data = dict(self.data, kind='brd', retrieval_id=result['id'], source_ids=[s['id'] for s in result['sources']])
        with self.assertRaisesRegex(ValueError, 'Confirm'): self.app.prepare('alice', data)
        data['context_confirmed'] = True
        data['source_ids'].remove('fhp-workplace:definition')
        with self.assertRaisesRegex(ValueError, 'definition evidence'): self.app.prepare('alice', data)
        data['source_ids'].append('restricted-cobra:prototype')
        with self.assertRaisesRegex(ValueError, 'Unknown'): self.app.prepare('alice', data)

    def test_browser_cannot_replace_source_content(self):
        result = self.app.retrieve('alice', self.data)
        request = self.prepared(result, sources=[{'text': 'An injected fake policy'}])
        self.assertNotIn('injected', json.dumps(request['sources']))

    def test_copilot_import_preserves_retrieval_snapshot(self):
        request = self.prepared()
        pending = self.app.submit('alice', request, 'copilot')
        self.assertIn('Facility Handover Plan', pending['brief'])
        doc = self.app.store.mutate('alice', pending['id'], 'import', {'result': {'sections': generate(request)['sections']}})
        self.assertEqual(doc['retrieval'], request['retrieval'])
        self.assertEqual(doc['sources'], request['sources'])
        self.assertIn('index_version', copilot_brief(request))

    def test_fixture_change_rebuilds_index_without_old_content(self):
        corpus = Path(self.temp.name) / 'pages.json'
        pages = json.loads(CORPUS.read_text())
        corpus.write_text(json.dumps(pages))
        path = Path(self.temp.name) / 'changing.sqlite3'
        old = KnowledgeIndex(path, corpus)
        pages = [p for p in pages if p['id'] != 'cafeteria']
        pages[0]['version'] += 1
        corpus.write_text(json.dumps(pages))
        new = KnowledgeIndex(path, corpus)
        self.assertNotEqual(old.index_version, new.index_version)
        self.assertEqual(new.search('vegetarian', 'vegetarian')['sources'], [])
        self.assertNotIn('cafeteria', new.pages)

    def test_invalid_domain_or_definition_choice(self):
        for update in ({'domain': 'secret'}, {'choices': []}, {'choices': {'fhp': 'unknown'}}, {'choices': {'missing': 'x'}}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                self.app.retrieve('alice', dict(self.data, **update))


if __name__ == '__main__':
    unittest.main()
