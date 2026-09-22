"""SQLite persistence with browser-session ownership and optimistic revision checks."""
import json
import sqlite3
import uuid
from pathlib import Path
from domain import now, validate_sections, generate, copilot_brief


class Conflict(ValueError):
    pass


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS meetings (id TEXT PRIMARY KEY, owner TEXT NOT NULL, project TEXT NOT NULL, day TEXT NOT NULL, body TEXT NOT NULL, UNIQUE(owner, id))')
            db.execute('CREATE TABLE IF NOT EXISTS retrieval_runs (id TEXT PRIMARY KEY, owner TEXT NOT NULL, body TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, csrf TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, owner TEXT NOT NULL, body TEXT NOT NULL)')
            # Queued work is not durable across process restarts in this POC.
            for key, raw in db.execute('SELECT id, body FROM documents').fetchall():
                body = json.loads(raw)
                if body['status'] in ('queued', 'generating'):
                    body.update(status='failed', error='Server restarted during generation. Create a new draft.')
                    self._write(db, key, body)

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def save_meeting(self, owner, record):
        import hashlib
        key = hashlib.sha256((owner + json.dumps(record, sort_keys=True)).encode()).hexdigest()
        body = dict(record, id=key, saved_at=now())
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO meetings VALUES (?,?,?,?,?)',
                       (key, owner, record['project'], record['meeting_date'], json.dumps(body)))
            row = db.execute('SELECT body FROM meetings WHERE id=? AND owner=?', (key, owner)).fetchone()
        return json.loads(row[0])

    def meeting_history(self, owner, identity):
        with self.connect() as db:
            rows = db.execute('SELECT body FROM meetings WHERE owner=? AND project=? AND day<? ORDER BY day, rowid LIMIT 51',
                              (owner, identity['project'], identity['meeting_date'])).fetchall()
        if len(rows) > 50:
            raise ValueError('This demo supports at most 50 earlier meetings per project. Use a narrower project name.')
        return [json.loads(row[0]) for row in rows]

    def _write(self, db, key, body):
        db.execute('UPDATE documents SET body=? WHERE id=?', (json.dumps(body), key))

    def save_retrieval(self, owner, result):
        key = uuid.uuid4().hex
        result = dict(result, id=key, retrieved_at=now())
        with self.connect() as db:
            db.execute('INSERT INTO retrieval_runs VALUES (?,?,?)', (key, owner, json.dumps(result)))
        return result

    def get_retrieval(self, owner, key):
        with self.connect() as db:
            row = db.execute('SELECT body FROM retrieval_runs WHERE id=? AND owner=?', (key, owner)).fetchone()
        if not row:
            raise KeyError('Retrieval not found in this browser session.')
        return json.loads(row[0])

    def create(self, owner, request):
        key = uuid.uuid4().hex
        body = dict(request, id=key, revision=0, status='queued', approved_revision=None,
                    created_at=now(), events=[{'at': now(), 'action': 'queued', 'revision': 0}], publications=[])
        with self.connect() as db:
            db.execute('INSERT INTO documents VALUES (?,?,?)', (key, owner, json.dumps(body)))
        return body

    def get(self, owner, key):
        with self.connect() as db:
            row = db.execute('SELECT body FROM documents WHERE id=? AND owner=?', (key, owner)).fetchone()
        if not row:
            raise KeyError('Document not found in this browser session.')
        return json.loads(row[0])

    def listing(self, owner):
        with self.connect() as db:
            rows = db.execute('SELECT body FROM documents WHERE owner=? ORDER BY rowid DESC LIMIT 50', (owner,)).fetchall()
        return [{k: b[k] for k in ('id', 'title', 'kind', 'status', 'revision', 'created_at')}
                for b in (json.loads(row[0]) for row in rows)]

    def mutate(self, owner, key, action, data):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT body FROM documents WHERE id=? AND owner=?', (key, owner)).fetchone()
            if not row:
                raise KeyError('Document not found in this browser session.')
            body = json.loads(row[0])
            if action in ('save', 'approve', 'publish'):
                if type(data.get('revision')) is not int or data['revision'] != body['revision']:
                    raise Conflict('This draft changed. Reload it before continuing.')
                if body['status'] not in ('ready', 'approved', 'published'):
                    raise Conflict('Wait for a completed draft.')
            if action == 'awaiting_copilot':
                body.update(status='awaiting_copilot', brief=copilot_brief(data))
            elif action == 'import':
                if body['status'] != 'awaiting_copilot':
                    raise Conflict('This draft is not waiting for a Copilot response.')
                result = data.get('result')
                if not isinstance(result, dict) or set(result) != {'sections'} or not isinstance(result['sections'], list):
                    raise ValueError('Paste a JSON object containing only a sections array.')
                request = {k: body[k] for k in ('title', 'notes', 'kind', 'sources')}
                if 'retrieval' in body:
                    request['retrieval'] = body['retrieval']
                if 'meeting_context' in body:
                    request['meeting_context'] = body['meeting_context']
                body.update(generate(request, result['sections']), status='ready', revision=1)
                body.pop('brief', None)
            elif action == 'generating':
                body['status'] = 'generating'
            elif action == 'generated':
                body.update(data, status='ready', revision=1)
            elif action == 'failed':
                body.update(status='failed', error=data['error'])
            elif action == 'save':
                body['sections'] = validate_sections(data.get('sections'), body['kind'], body['sources'], body.get('meeting_context'))
                body.update(revision=body['revision'] + 1, status='ready', approved_revision=None)
            elif action == 'approve':
                if data.get('reviewed') is not True:
                    raise ValueError('Confirm that you reviewed the sources and open questions.')
                body.update(status='approved', approved_revision=body['revision'])
            elif action == 'publish':
                if body['approved_revision'] != body['revision']:
                    raise Conflict('Approve the current revision before publishing.')
                if data.get('parent') not in ('product-discovery', 'change-proposals'):
                    raise ValueError('Choose a demo destination.')
                # Idempotent for a given revision; snapshots survive subsequent edits.
                existing = next((p for p in body['publications'] if p['revision'] == body['revision']), None)
                if existing:
                    return body
                snapshot = {k: v for k, v in body.items() if k not in ('publications', 'events')}
                snapshot['status'] = 'published'
                snapshot['destination'] = data['parent']
                body['publications'].append({'revision': body['revision'], 'parent': data['parent'],
                                              'at': now(), 'snapshot': snapshot})
                body['status'] = 'published'
            else:
                raise ValueError('Unknown document action.')
            body['events'].append({'at': now(), 'action': action, 'revision': body['revision']})
            self._write(db, key, body)
        return body
