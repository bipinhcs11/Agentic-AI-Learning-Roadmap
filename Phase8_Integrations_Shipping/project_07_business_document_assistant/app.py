"""Loopback-only POC server. No SSO or external publication is implemented."""
from __future__ import annotations

import argparse
import hmac
import json
import mimetypes
import re
import secrets
import threading
from concurrent.futures import ThreadPoolExecutor
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from domain import BASE, SAMPLE_NOTES, SOURCES, TEMPLATES, generate, page_html, validate_request, word_bytes
from store import Conflict, Store
from domain import clean_text, MAX_NOTES
from retrieval import KnowledgeIndex, RAG_NOTES, DOMAINS, fingerprint, domain_value
from meetings import meeting_identity, tracking_items, compare_meetings, history_version

MAX_BODY = 1_000_000


class Application:
    def __init__(self, data_dir):
        self.store = Store(Path(data_dir) / 'documents.sqlite3')
        self.index = KnowledgeIndex(Path(data_dir) / 'knowledge.sqlite3')
        self.pool = ThreadPoolExecutor(max_workers=2)
        self.slots = threading.BoundedSemaphore(8)
        self.lock = threading.Lock()

    def session(self, cookie):
        cookies = SimpleCookie()
        try:
            cookies.load(cookie or '')
            key = cookies['bda_session'].value if 'bda_session' in cookies else ''
        except Exception:
            key = ''
        with self.lock:
            with self.store.connect() as db:
                row = db.execute('SELECT csrf FROM sessions WHERE id=?', (key,)).fetchone()
                if row:
                    return key, row[0], False
                key, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
                db.execute('INSERT INTO sessions VALUES (?,?)', (key, csrf))
                return key, csrf, True

    def retrieve(self, owner, data):
        title = clean_text(data.get('title'), 'Title', 140)
        notes = clean_text(data.get('notes'), 'Notes', MAX_NOTES)
        if len([line for line in notes.splitlines() if line.strip()]) > 120:
            raise ValueError('Use at most 120 non-empty lines of meeting notes.')
        domain = domain_value(data.get('domain', 'all'))
        result = self.index.search(title, notes, domain, data.get('choices'))
        identity = meeting_identity(data)
        if identity:
            result['meeting_context'] = compare_meetings(identity, self.store.meeting_history(owner, identity), notes)
        return self.store.save_retrieval(owner, result)

    def save_meeting(self, owner, data):
        identity = meeting_identity(data)
        if not identity:
            raise ValueError('Enter a project and meeting date to save meeting history.')
        title = clean_text(data.get('title'), 'Title', 140)
        notes = clean_text(data.get('notes'), 'Notes', MAX_NOTES)
        if len([line for line in notes.splitlines() if line.strip()]) > 120:
            raise ValueError('Use at most 120 non-empty lines of meeting notes.')
        tracking_items(notes)
        return self.store.save_meeting(owner, dict(identity, title=title, notes=notes))

    def prepare(self, owner, data):
        key = data.get('retrieval_id')
        if not isinstance(key, str):
            raise ValueError('Find and confirm business context before drafting.')
        result = self.store.get_retrieval(owner, key)
        title = clean_text(data.get('title'), 'Title', 140)
        notes = clean_text(data.get('notes'), 'Notes', MAX_NOTES)
        domain = domain_value(data.get('domain', 'all'))
        if fingerprint(title, notes, domain) != result['input_fingerprint']:
            raise Conflict('Input changed. Find business context again before drafting.')
        if result['index_version'] != self.index.index_version:
            raise Conflict('The knowledge index changed. Retrieve fresh context.')
        identity = meeting_identity(data)
        context = result.get('meeting_context')
        if identity != ({k: context[k] for k in ('project', 'meeting_date')} if context else None):
            raise Conflict('Project or meeting date changed. Find business context again.')
        if context and history_version(self.store.meeting_history(owner, identity)) != context['history_version']:
            raise Conflict('Earlier meeting history changed. Find business context again.')
        if data.get('context_confirmed') is not True:
            raise ValueError('Confirm the retrieved context before drafting.')
        if any(t['status'] == 'ambiguous' for t in result['terms']):
            raise ValueError('Resolve ambiguous terms or narrow the business domain, then search again.')
        if result['unresolved'] and data.get('acknowledge_unresolved') is not True:
            raise ValueError('Acknowledge unresolved terminology before drafting.')
        request = validate_request(data, result['sources'])
        selected = {s['id'] for s in request['sources']}
        required = {t['selected']['source_id'] for t in result['terms'] if t['selected']}
        if required - selected:
            raise ValueError('Keep definition evidence selected for every resolved term.')
        request['retrieval'] = {k: result[k] for k in ('id', 'retrieved_at', 'domain', 'terms',
            'unresolved', 'method', 'index_version', 'input_fingerprint')}
        request['retrieval']['selected_source_ids'] = sorted(selected)
        request['retrieval']['unresolved_acknowledged'] = bool(result['unresolved'])
        if context:
            request['meeting_context'] = context
        return request

    def submit(self, owner, request, mode='offline'):
        if mode not in ('offline', 'copilot'):
            raise ValueError('Select offline or Copilot-assisted mode.')
        if mode == 'copilot':
            body = self.store.create(owner, request)
            return self.store.mutate(owner, body['id'], 'awaiting_copilot', request)
        if not self.slots.acquire(blocking=False):
            raise Conflict('The demo queue is full. Try again after a job finishes.')
        try:
            body = self.store.create(owner, request)
            self.pool.submit(self.worker, owner, body['id'], request)
            return body
        except Exception:
            self.slots.release()
            raise

    def worker(self, owner, key, request):
        try:
            self.store.mutate(owner, key, 'generating', {})
            result = generate(request)
            self.store.mutate(owner, key, 'generated', result)
        except Exception:
            # Do not leak upstream bodies, credentials, or notes into errors/logs.
            self.store.mutate(owner, key, 'failed', {'error': 'Draft assembly failed. Check the input size and template structure, then create a new draft. No fallback content was substituted.'})
        finally:
            self.slots.release()

    def close(self):
        self.pool.shutdown(wait=True)


def make_handler(application):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass  # Avoid logging document IDs, content, or authentication data.

        def respond(self, status, content, kind='application/json; charset=utf-8', filename=None):
            if not isinstance(content, bytes):
                content = json.dumps(content).encode() if kind.startswith('application/json') else content.encode()
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            if getattr(self, 'new_session', False):
                self.send_header('Set-Cookie', f'bda_session={self.owner}; HttpOnly; SameSite=Strict; Path=/')
            if filename:
                self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(content)

        def dispatch(self, post=False):
            host = self.headers.get('Host', '')
            allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            if host not in allowed:
                return self.respond(403, {'error': 'Only the local demo origin is accepted.'})
            self.owner, self.csrf, self.new_session = application.session(self.headers.get('Cookie'))
            if post:
                if self.headers.get('Origin') not in (None, f'http://{host}'):
                    return self.respond(403, {'error': 'Origin rejected.'})
                if not hmac.compare_digest(self.headers.get('X-CSRF-Token', ''), self.csrf):
                    return self.respond(403, {'error': 'Refresh the page to establish a valid session.'})
                if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    return self.respond(415, {'error': 'Use application/json.'})
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                except ValueError:
                    raise ValueError('Invalid request length.')
                if not 0 < length <= MAX_BODY:
                    return self.respond(413, {'error': 'Request exceeds the demo size limit.'})
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError('Expected a JSON object.')
            path = urlsplit(self.path).path
            if not post and path in ('/', '/static/app.js', '/static/styles.css', '/static/page.css'):
                file = BASE / 'static' / ('index.html' if path == '/' else path.rsplit('/', 1)[1])
                kind = mimetypes.guess_type(str(file))[0] or 'text/plain'
                return self.respond(200, file.read_bytes(), kind + '; charset=utf-8')
            if not post and path == '/api/config':
                return self.respond(200, {'csrf': self.csrf, 'provider': 'offline or Copilot-assisted',
                    'templates': TEMPLATES, 'sources': [], 'sample_notes': RAG_NOTES, 'domains': DOMAINS,
                    'knowledge': {'pages': len(application.index.pages), 'chunks': len(application.index.chunks), 'version': application.index.index_version},
                    'max_notes': 24000, 'publication': 'local simulation', 'identity': 'local browser session'})
            if post and path == '/api/retrieve':
                return self.respond(200, application.retrieve(self.owner, data))
            if post and path == '/api/meetings':
                return self.respond(200, application.save_meeting(self.owner, data))
            source_match = re.fullmatch(r'/api/sources/([a-z0-9-]+)', path)
            if not post and source_match:
                return self.respond(200, application.index.page_html(source_match.group(1)), 'text/html; charset=utf-8')
            if path == '/api/documents':
                if post:
                    return self.respond(202, application.submit(self.owner, application.prepare(self.owner, data), data.get('mode', 'offline')))
                return self.respond(200, application.store.listing(self.owner))
            match = re.fullmatch(r'/api/documents/([0-9a-f]{32})(?:/(save|approve|publish|word|page|audit|brief|import))?', path)
            if match:
                key, action = match.groups()
                if post and action in ('save', 'approve', 'publish', 'import'):
                    return self.respond(200, application.store.mutate(self.owner, key, action, data))
                if post:
                    return self.respond(405, {'error': 'Unsupported action.'})
                doc = application.store.get(self.owner, key)
                if action is None:
                    return self.respond(200, doc)
                if action == 'brief':
                    if 'brief' not in doc:
                        raise Conflict('No pending Copilot brief for this draft.')
                    return self.respond(200, doc['brief'], 'text/plain; charset=utf-8', 'copilot-brief.txt')
                if action == 'word':
                    if 'sections' not in doc:
                        raise Conflict('Wait for a completed draft.')
                    return self.respond(200, word_bytes(doc), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', f"document-{key[:8]}-r{doc['revision']}.docx")
                if action == 'page':
                    if not doc['publications']:
                        raise Conflict('No simulated publication exists yet.')
                    return self.respond(200, page_html(doc['publications'][-1]['snapshot']), 'text/html; charset=utf-8')
                if action == 'audit':
                    return self.respond(200, {'document_id': key, 'events': doc['events']}, filename=f'audit-{key[:8]}.json')
            return self.respond(404, {'error': 'Not found.'})

        def safe_dispatch(self, post=False):
            self.connection.settimeout(15)
            try:
                self.dispatch(post)
            except Conflict as exc:
                self.respond(409, {'error': str(exc)})
            except KeyError:
                self.respond(404, {'error': 'Document not found in this browser session.'})
            except (ValueError, UnicodeError) as exc:
                self.respond(400, {'error': str(exc) if not isinstance(exc, json.JSONDecodeError) else 'Invalid JSON.'})
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                pass
            except Exception:
                self.respond(500, {'error': 'Unexpected server error. No external publication was made.'})

        def do_GET(self):
            self.safe_dispatch()

        def do_POST(self):
            self.safe_dispatch(True)
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--data-dir', default=str(BASE / 'runtime'))
    args = parser.parse_args()
    app = Application(args.data_dir)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(app))
    print(f'Business Document Assistant: http://127.0.0.1:{args.port}', flush=True)
    print('Offline + Copilot-assisted drafting. Fictional data only. Confluence publication is simulated.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        app.close()


if __name__ == '__main__':
    main()
