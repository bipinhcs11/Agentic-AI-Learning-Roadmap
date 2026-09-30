"""Version preservation and direct provider failure-boundary tests; no AI calls."""
import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace, ModuleType
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import Application
from domain import generate, offline_sections, TEMPLATES, validate_request, SOURCES
from store import Conflict
import copilot_provider


class VersionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = Application(self.temp.name)
        self.request = validate_request(dict(title='Cobra requirements', notes='Cobra room readiness reminder.', kind='brd', source_ids=[s['id'] for s in SOURCES]))
        self.first = self.create(self.request)

    def tearDown(self):
        self.app.close(); self.temp.cleanup()

    def create(self, request):
        doc = self.app.store.create('alice', request)
        return self.app.store.mutate('alice', doc['id'], 'generated', generate(doc))

    def next_request(self, base=None, **extra):
        base = base or self.first
        return dict(self.request, workflow='revise', base_document_id=base['id'], base_revision=base['revision'], **extra)

    def test_versions_preserve_original_and_reject_stale_branch(self):
        second = self.create(self.next_request())
        third = self.create(self.next_request(second))
        self.assertEqual([d['document_version'] for d in self.app.store.versions('alice', third['id'])], ['1.0', '1.1', '1.2'])
        self.assertEqual(self.app.store.get('alice', self.first['id']), self.first)
        self.assertEqual(second['baseline']['sections'], self.first['sections'])
        with self.assertRaises(Conflict):
            self.create(self.next_request())
        with self.assertRaises(Conflict):
            self.app.store.mutate('alice', self.first['id'], 'save', {'revision': 1, 'sections': self.first['sections']})
        self.assertEqual(self.create(self.next_request(third, version_bump='major'))['document_version'], '2.0')

    def test_concurrent_successors_reserve_only_one_version(self):
        from concurrent.futures import ThreadPoolExecutor
        def attempt(_):
            try: return self.app.store.create('alice', self.next_request())['document_version']
            except Conflict: return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(attempt, range(2)))
        self.assertCountEqual(outcomes, ['1.1', 'conflict'])

    def test_provider_error_fails_without_fallback_or_error_leak(self):
        doc = self.app.store.create('alice', self.request)
        self.app.slots.acquire()
        with patch('copilot_provider.draft', side_effect=RuntimeError('sensitive upstream detail')):
            self.app.worker('alice', doc['id'], doc, 'copilot-sdk')
        failed = self.app.store.get('alice', doc['id'])
        self.assertEqual(failed['status'], 'failed')
        self.assertNotIn('sections', failed)
        self.assertNotIn('sensitive upstream detail', failed['error'])

    def test_failed_successor_allows_retry(self):
        doc = self.app.store.create('alice', self.next_request())
        self.app.store.mutate('alice', doc['id'], 'failed', {'error': 'Controlled failure'})
        self.assertEqual(self.create(self.next_request())['document_version'], '1.1')

    def test_ownership_stale_edit_and_type_checks(self):
        with self.assertRaises(KeyError):
            self.app.store.create('bob', self.next_request())
        request = self.next_request(); request['base_revision'] = 10
        with self.assertRaises(Conflict): self.create(request)
        request = self.next_request(); request['kind'] = 'mom'
        with self.assertRaises(ValueError): self.create(request)
        request['workflow'] = 'derive'
        derived = self.create(request)
        self.assertEqual(derived['document_version'], '1.0')
        self.assertNotEqual(derived['family_id'], self.first['family_id'])
        self.assertEqual(derived['baseline']['id'], self.first['id'])

    def test_edit_snapshots_and_baseline_tampering(self):
        sections = json.loads(json.dumps(self.first['sections']))
        sections[0]['body'] = 'Reviewed scope'
        self.app.store.mutate('alice', self.first['id'], 'save', {'revision': 1, 'sections': sections})
        edits = self.app.store.edits('alice', self.first['id'])
        self.assertEqual(len(edits), 2)
        self.assertEqual(edits[0]['sections'], self.first['sections'])
        self.assertEqual(edits[1]['sections'][0]['body'], 'Reviewed scope')
        request = self.next_request(); request['base_revision'] = 2
        request['baseline'] = {'title': 'Forged'}; request['document_version'] = '99.9'
        doc = self.create(request)
        self.assertEqual(doc['document_version'], '1.1')
        self.assertEqual(doc['baseline']['title'], self.first['title'])
        with self.assertRaises(KeyError): self.app.store.edits('bob', self.first['id'])

    def test_pasted_architecture_and_mom_missing_facts(self):
        original = self.app.import_baseline('alice', {'title':'Original architecture', 'content':'Cobra has no reminder service.', 'kind':'architecture'})
        self.assertEqual(original['document_version'], '1.0')
        self.assertIn('Cobra has no reminder service.', original['sections'][1]['body'])
        req = self.next_request(original); req['kind'] = 'architecture'
        updated = self.create(req)
        self.assertEqual(updated['document_version'], '1.1')
        self.assertIn('[B1]', updated['sections'][1]['body'])
        mom = generate(dict(self.request, kind='mom', notes='Date: 2026-09-23\nAttendee count: 10\nAction: Review reminders | Owner: Sam | Due: not agreed'))
        self.assertIn('Attendee count: 10', mom['sections'][0]['body'])
        self.assertIn('Attendees: Not recorded', mom['sections'][0]['body'])
        self.assertIn('Owner: Sam', mom['sections'][3]['body'])

    def test_sdk_unconfigured_does_not_create_or_fallback(self):
        before = self.app.store.listing('alice')
        with patch.dict('os.environ', {}, clear=True), self.assertRaises(copilot_provider.CopilotUnavailable):
            self.app.submit('alice', self.request, 'copilot-sdk')
        self.assertEqual(self.app.store.listing('alice'), before)


class SDKTests(unittest.TestCase):
    def test_sdk_contract_cleanup_and_validation(self):
        request = validate_request(dict(title='Cobra', notes='Review Cobra room readiness.', kind='brd', source_ids=[s['id'] for s in SOURCES]))
        calls = {}
        class Session:
            async def __aenter__(self): return self
            async def __aexit__(self, *args): calls['session_closed'] = True
            async def send_and_wait(self, prompt, timeout):
                calls['prompt'] = prompt
                return SimpleNamespace(data=SimpleNamespace(content=calls['response']))
        class Client:
            def __init__(self, **kwargs): calls['client'] = kwargs
            async def __aenter__(self): return self
            async def __aexit__(self, *args): calls['client_closed'] = True
            async def create_session(self, **kwargs): calls['session'] = kwargs; return Session()
        copilot = ModuleType('copilot'); copilot.CopilotClient = Client
        client = ModuleType('copilot.client'); client.RuntimeConnection = SimpleNamespace(for_stdio=lambda **k:k)
        rpc = ModuleType('copilot.rpc'); rpc.PermissionDecisionReject = lambda **k: {'denied':True}
        with patch.dict(sys.modules, {'copilot':copilot, 'copilot.client':client, 'copilot.rpc':rpc}), patch.dict('os.environ', {'BDA_COPILOT_CLI':'approved-runtime', 'BDA_COPILOT_MODEL':'approved-model'}):
            calls['response'] = json.dumps({'sections':offline_sections(request)})
            doc = asyncio.run(copilot_provider._generate(request))
            self.assertEqual(doc['provider'], 'copilot-sdk')
            self.assertEqual(calls['client']['mode'], 'empty')
            self.assertEqual(calls['session']['available_tools'], [])
            self.assertTrue(calls['session']['on_permission_request']()['denied'])
            self.assertIn('14 days', calls['prompt'])
            for response in ('not structured data', '{"sections":null}', '{"sections":[]}', '{"sections":[],"other":1}'):
                calls['response'] = response
                with self.assertRaises(ValueError): asyncio.run(copilot_provider._generate(request))
                self.assertTrue(calls['client_closed']); self.assertTrue(calls['session_closed'])

if __name__ == '__main__': unittest.main()
