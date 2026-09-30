import io
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import Application
from domain import generate, word_bytes, storage_html
from meetings import meeting_identity, tracking_items
from store import Conflict


class MeetingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = Application(self.temp.name)
        self.earlier = dict(project='Cobra pilot', meeting_date='2026-09-01', title='Discovery',
            notes='Cobra FHP\n[OPEN] OWNER-1 | Assign an owner.\n[BLOCKED] ACCESS-1 | Review accessibility.')
        self.data = dict(project='cobra PILOT', meeting_date='2026-09-08', title='Cobra follow-up', domain='workplace',
            notes='Cobra FHP\n[DONE] OWNER-1 | Owner assigned.\n[OPEN] RULE-1 | Review 30 days in advance.')

    def tearDown(self):
        self.app.close()
        self.temp.cleanup()

    def prepare(self, result):
        return self.app.prepare('alice', dict(self.data, kind='brd', retrieval_id=result['id'],
            context_confirmed=True, source_ids=[s['id'] for s in result['sources']]))

    def test_progress_and_omitted_blocker_carry_forward(self):
        self.app.save_meeting('alice', self.earlier)
        result = self.app.retrieve('alice', self.data)
        self.assertFalse(result['unresolved'])
        ctx = result['meeting_context']
        self.assertEqual(ctx['changes'][0]['previous']['status'], 'OPEN')
        self.assertEqual(ctx['changes'][0]['status'], 'DONE')
        self.assertEqual(ctx['carried_forward'][0]['key'], 'ACCESS-1')
        self.assertEqual(ctx['changes'][1]['change'], 'new')
        doc = generate(self.prepare(result))
        self.assertIn('Carry forward ACCESS-1', doc['sections'][-1]['body'])
        self.assertIn('[M1]', storage_html(doc))
        from docx import Document
        text = '\n'.join(p.text for p in Document(io.BytesIO(word_bytes(doc))).paragraphs)
        self.assertIn('OPEN [M1] → DONE [N1]', text)

    def test_session_project_and_date_isolation_and_deduplication(self):
        a = self.app.save_meeting('alice', self.earlier)
        b = self.app.save_meeting('alice', self.earlier)
        self.assertEqual(a, b)
        self.app.save_meeting('bob', self.earlier)
        self.app.save_meeting('alice', dict(self.earlier, project='Other'))
        self.app.save_meeting('alice', dict(self.earlier, meeting_date='2026-09-08'))
        self.app.save_meeting('alice', dict(self.earlier, meeting_date='2026-09-09'))
        ctx = self.app.retrieve('alice', self.data)['meeting_context']
        self.assertEqual([m['id'] for m in ctx['meetings']], [a['id']])
        self.assertFalse(self.app.retrieve('carol', self.data)['meeting_context']['meetings'])

    def test_latest_prior_state_and_reopened_item(self):
        self.app.save_meeting('alice', self.earlier)
        self.app.save_meeting('alice', dict(self.earlier, meeting_date='2026-09-03', notes='[DONE] OWNER-1 | Assigned.'))
        self.data['notes'] = 'Cobra FHP\n[OPEN] OWNER-1 | Need a replacement.'
        ctx = self.app.retrieve('alice', self.data)['meeting_context']
        self.assertEqual(ctx['changes'][0]['previous']['status'], 'DONE')
        self.assertEqual(ctx['changes'][0]['previous']['citation'], 'M2')
        self.assertEqual(ctx['carried_forward'][0]['key'], 'ACCESS-1')

    def test_stale_history_and_changed_project_rejected(self):
        result = self.app.retrieve('alice', self.data)
        self.app.save_meeting('alice', self.earlier)
        with self.assertRaisesRegex(Conflict, 'history changed'): self.prepare(result)
        result = self.app.retrieve('alice', self.data)
        self.data['project'] = 'Other'
        with self.assertRaisesRegex(Conflict, 'Project'): self.prepare(result)

    def test_import_preserves_snapshot_and_rejects_fabricated_citation(self):
        self.app.save_meeting('alice', self.earlier)
        request = self.prepare(self.app.retrieve('alice', self.data))
        pending = self.app.submit('alice', request, 'copilot')
        self.assertIn('ACCESS-1', pending['brief'])
        sections = generate(request)['sections']
        sections[0]['body'] += ' [M99]'
        with self.assertRaisesRegex(ValueError, 'unselected'):
            self.app.store.mutate('alice', pending['id'], 'import', {'result': {'sections': sections}})
        sections[0]['body'] = sections[0]['body'].removesuffix(' [M99]')
        doc = self.app.store.mutate('alice', pending['id'], 'import', {'result': {'sections': sections}})
        self.assertEqual(doc['meeting_context'], request['meeting_context'])
        self.app.save_meeting('alice', dict(self.earlier, title='Later upload'))
        self.assertEqual(len(self.app.store.get('alice', doc['id'])['meeting_context']['meetings']), 1)

    def test_free_text_does_not_imply_completion(self):
        self.app.save_meeting('alice', self.earlier)
        self.data['notes'] = 'Cobra owner work looks good.'
        ctx = self.app.retrieve('alice', self.data)['meeting_context']
        self.assertFalse(ctx['changes'])
        self.assertEqual(len(ctx['carried_forward']), 2)
        self.assertIn('Cobra owner work looks good.', ctx['new_lines'])

    def test_validation(self):
        for data in ({'project': 'x'}, {'meeting_date': '2026-09-01'}, {'project': 'x', 'meeting_date': '2026-02-30'}):
            with self.assertRaises(ValueError): meeting_identity(data)
        for notes in ('[OPEN] X | First\n[DONE] x | Second', '[OPEN] no separator'):
            with self.assertRaises(ValueError): tracking_items(notes)


if __name__ == '__main__':
    unittest.main()
