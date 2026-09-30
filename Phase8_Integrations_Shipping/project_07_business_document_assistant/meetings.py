"""Deterministic meeting comparisons; discussion status is never policy approval."""
import hashlib
import json
import re
from datetime import date
from domain import clean_text


def meeting_identity(data):
    project = data.get('project', '')
    day = data.get('meeting_date', '')
    if project == '' and day == '':
        return None
    project = clean_text(project, 'Project', 80).casefold()
    try:
        if not isinstance(day, str) or date.fromisoformat(day).isoformat() != day:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError('Choose a meeting date in YYYY-MM-DD format.')
    return {'project': project, 'meeting_date': day}


def tracking_items(notes):
    """Only explicit user-authored states count as tracked progress."""
    items = {}
    for line in notes.splitlines():
        match = re.fullmatch(r'\s*\[(OPEN|IN_PROGRESS|DONE|BLOCKED|DECIDED)\]\s+([A-Za-z0-9_-]{1,40})\s*\|\s*(.+)', line)
        if match:
            status, key, text = match.groups()
            key = key.upper()
            if key in items:
                raise ValueError(f'Duplicate tracking ID: {key}. Use one state per item per meeting.')
            items[key] = {'key': key, 'status': status, 'text': text.strip()}
        elif re.match(r'\s*\[(OPEN|IN_PROGRESS|DONE|BLOCKED|DECIDED)\]', line):
            raise ValueError('Tracking lines must use [OPEN] ITEM-1 | description (or IN_PROGRESS, DONE, BLOCKED, DECIDED).')
    return items


def history_version(records):
    return hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()


def compare_meetings(identity, records, notes):
    # Store returns a bounded chronological list, scoped to this session and project.
    prior = {}
    snapshots = []
    for i, record in enumerate(records, 1):
        snapshot = dict(record, citation=f'M{i}')
        snapshots.append(snapshot)
        for key, item in tracking_items(record['notes']).items():
            prior[key] = dict(item, meeting_id=record['id'], date=record['meeting_date'], citation=f'M{i}')
    current = tracking_items(notes)
    changes = []
    for key, item in current.items():
        old = prior.get(key)
        change = 'new' if not old else ('status changed' if old['status'] != item['status'] else
                 'description changed' if old['text'] != item['text'] else 'unchanged')
        changes.append(dict(item, change=change, previous=old))
    carried = [item for key, item in prior.items() if key not in current and item['status'] not in ('DONE', 'DECIDED')]
    previous_lines = set(records[-1]['notes'].splitlines()) if records else set()
    current_lines = set(notes.splitlines())
    return {**identity, 'history_version': history_version(records), 'meetings': snapshots,
            'changes': changes, 'carried_forward': carried,
            'new_lines': sorted(current_lines - previous_lines),
            'not_repeated': sorted(previous_lines - current_lines),
            'method': 'Explicit tracking IDs/statuses and exact line comparison; no semantic inference. Missing items are not completed.'}
