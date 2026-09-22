'use strict';
const $ = id => document.getElementById(id);
let config, current, dirty = false, pollToken = 0, retrieval = null, retrievalEpoch = 0;
function message(text, error = false) {
  $('message').textContent = text; $('message').className = error ? 'error' : '';
  $('message').hidden = false;
}
async function api(path, body) {
  const options = body === undefined ? {} : {method: 'POST', headers: {
    'Content-Type': 'application/json', 'X-CSRF-Token': config.csrf}, body: JSON.stringify(body)};
  const response = await fetch(path, options);
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || 'The request failed.');
  return value;
}
function element(tag, text, className) {
  const e = document.createElement(tag); if (text !== undefined) e.textContent = text;
  if (className) e.className = className; return e;
}
function endpoint(action) { return `/api/documents/${current.id}${action ? '/' + action : ''}`; }
function setDirty(value) {
  dirty = value;
  $('save').disabled = !dirty;
  $('save-state').textContent = dirty ? 'Unsaved changes — save before exporting or approving' : 'All changes saved';
  $('approve').disabled = dirty || !$('reviewed').checked || current?.approved_revision === current?.revision;
  $('publish').disabled = dirty || current?.approved_revision !== current?.revision;
  $('word').classList.toggle('disabled', dirty);
  $('word').setAttribute('aria-disabled', String(dirty));
}
function canLeave() { return !dirty || window.confirm('Discard unsaved draft edits?'); }
async function history() {
  const items = await api('/api/documents'); $('history').replaceChildren();
  for (const item of items) {
    const button = element('button', item.title);
    button.append(element('small', `${item.status.replaceAll('_', ' ')} · r${item.revision}`));
    button.onclick = () => { if (canLeave()) openDocument(item.id).catch(e => message(e.message, true)); };
    $('history').append(button);
  }
}
function render(doc) {
  current = doc; dirty = false;
  ['empty', 'busy', 'handoff', 'document'].forEach(id => $(id).hidden = true);
  $('status').textContent = doc.status.replaceAll('_', ' ');
  if (doc.status === 'failed') {
    $('empty').hidden = false; message(doc.error, true); return;
  }
  if (['queued', 'generating'].includes(doc.status)) {
    $('busy').hidden = false; $('progress').textContent = doc.status === 'queued' ? 'Your request is queued.' : 'Assembling the offline draft from selected context.'; return;
  }
  if (doc.status === 'awaiting_copilot') {
    $('handoff').hidden = false; $('brief').value = doc.brief; $('copilot-result').value = '';
    $('download-brief').href = endpoint('brief'); return;
  }
  $('document').hidden = false; $('doc-title').textContent = doc.title;
  $('doc-detail').textContent = `${config.templates[doc.kind].name} · Template ${doc.template_version} · Revision ${doc.revision} · ${doc.provider === 'offline' ? 'Offline sample assembly, not AI-generated' : 'Imported from your Copilot session'}`;
  $('warnings').replaceChildren();
  for (const warning of doc.warnings) $('warnings').append(element('div', warning + ' This is a source comparison flag, not a complete validation report.', 'warning'));
  $('sections').replaceChildren();
  doc.sections.forEach((section, index) => {
    const wrapper = element('div', undefined, 'section-editor');
    const label = element('label', section.heading); label.htmlFor = `section-${index}`;
    const text = element('textarea'); text.id = `section-${index}`; text.value = section.body;
    text.maxLength = 48000; text.rows = Math.min(12, Math.max(4, section.body.split('\n').length + 2));
    text.oninput = () => { $('reviewed').checked = false; setDirty(true); };
    wrapper.append(label, text); $('sections').append(wrapper);
  });
  $('evidence').replaceChildren();
  for (const source of doc.sources) {
    $('evidence').append(element('p', `[${source.citation}] ${source.title} · ${source.heading || 'Page'} · version ${source.version}\n${source.url}\n${source.text}`));
  }
  if (doc.retrieval) {
    $('evidence').append(element('p', `${doc.retrieval.method} · Domain ${doc.retrieval.domain} · Index ${doc.retrieval.index_version}`));
    for (const term of doc.retrieval.terms) $('evidence').append(element('p', term.selected ? `${term.term}: ${term.selected.definition} [${term.selected.citation}]` : `${term.term}: unresolved`));
  }
  $('evidence').append(element('p', `[N1] Meeting notes snapshot\n${doc.notes}`));
  for (const meeting of doc.meeting_context?.meetings || []) $('evidence').append(element('p', `[${meeting.citation}] Earlier meeting · ${meeting.meeting_date} · ${meeting.title}\n${meeting.notes}`));
  $('evidence').append(element('p', `Generated ${doc.generated_at}\nInput SHA256: ${doc.input_sha256}\n${doc.model}`));
  $('word').href = endpoint('word'); $('audit').href = endpoint('audit');
  $('reviewed').checked = false;
  $('publication').replaceChildren();
  if (doc.publications.length) {
    const last = doc.publications.at(-1);
    const link = element('a', `View simulated Confluence page · published revision ${last.revision}`);
    link.href = endpoint('page'); link.target = '_blank'; link.rel = 'noopener';
    $('publication').append(link);
  }
  setDirty(false);
}
async function openDocument(id) {
  const token = ++pollToken;
  const doc = await api(`/api/documents/${id}`);
  if (token !== pollToken) return;
  render(doc);
  if (['queued', 'generating'].includes(doc.status)) {
    setTimeout(() => { if (token === pollToken) openDocument(id).catch(e => message(e.message, true)); }, 650);
  } else await history();
}
async function action(button, task) {
  button.disabled = true;
  try { await task(); } catch (error) { message(error.message, true); }
  finally { button.disabled = false; if (current?.sections) setDirty(dirty); updateGenerate(); }
}
function updateGenerate() {
  const hasAmbiguity = retrieval?.terms.some(t => t.status === 'ambiguous');
  const hasUnknown = retrieval?.terms.some(t => t.status === 'unknown');
  $('generate').disabled = !retrieval || !retrieval.sources.length || hasAmbiguity ||
    (hasUnknown && !$('unknown-ack').checked) || !$('context-confirmed').checked ||
    !document.querySelector('[name=source]:checked');
}
function invalidateRetrieval() {
  retrieval = null; retrievalEpoch++; $('retrieval-panel').hidden = true;
  $('sources').replaceChildren(); $('terms').replaceChildren();
  $('context-confirmed').checked = false; $('unknown-ack').checked = false; updateGenerate();
}
for (const id of ['title', 'notes', 'project', 'meeting-date']) $(id).addEventListener('input', invalidateRetrieval);
$('domain').onchange = invalidateRetrieval;
$('context-confirmed').onchange = updateGenerate;
$('unknown-ack').onchange = updateGenerate;
function renderRetrieval(result) {
  retrieval = result; $('retrieval-panel').hidden = false;
  $('context-confirmed').checked = false; $('unknown-ack').checked = false;
  $('terms').replaceChildren(); $('sources').replaceChildren();
  renderMeetings(result.meeting_context);
  const required = new Set(result.terms.filter(t => t.selected).map(t => t.selected.source_id));
  for (const term of result.terms) {
    const card = element('div', undefined, 'term-card');
    card.append(element('strong', term.term));
    if (term.selected) {
      card.append(element('p', `${term.selected.definition} [${term.selected.citation}]`));
      card.append(element('small', `${config.domains[term.selected.domain]} · ${term.selected.page_title} · v${term.selected.version}`));
    } else if (term.status === 'ambiguous') {
      card.classList.add('ambiguous'); card.append(element('p', 'Multiple meanings found. Choose one, then click Find business context again.'));
      const label = element('label', `Meaning of ${term.term}`); const select = element('select');
      select.id = `meaning-${term.term.toLowerCase()}`; label.htmlFor = select.id;
      select.className = 'term-choice'; select.dataset.term = term.term.toLowerCase();
      const empty = element('option', 'Choose a meaning…'); empty.value = ''; select.append(empty);
      for (const candidate of term.candidates) {
        const option = element('option', `${candidate.definition} — ${config.domains[candidate.domain]}`);
        option.value = candidate.source_id; select.append(option);
      }
      card.append(label, select);
    } else card.append(element('p', 'No definition found in this domain. Add context or keep this as an unresolved question.'));
    $('terms').append(card);
  }
  if (!result.terms.length) $('terms').append(element('p', 'No known glossary term or uppercase acronym detected.', 'helper'));
  $('retrieval-info').textContent = `${result.method} · Index ${result.index_version.slice(0, 10)} · ${result.sources.length} sections found`;
  if (!result.sources.length) $('sources').append(element('div', 'No relevant context found. Add more specific notes or change the business domain before drafting.', 'warning'));
  for (const source of result.sources) {
    const card = element('div', undefined, 'source'); const label = element('label');
    const input = element('input'); input.type = 'checkbox'; input.name = 'source'; input.value = source.id;
    input.checked = true; input.disabled = required.has(source.id);
    input.onchange = () => { $('context-confirmed').checked = false; updateGenerate(); };
    const info = element('span', `[${source.citation}] ${source.title}`);
    info.append(element('small', `${source.heading} · ${source.space} · v${source.version}`));
    label.append(input, info); card.append(label, element('p', source.text, 'source-excerpt'));
    card.append(element('small', `${source.reason}${required.has(source.id) ? ' · Required definition' : ''}`));
    const link = element('a', 'View fictional Confluence page ↗', 'text-link');
    link.href = `/api/sources/${source.page_id}`; link.target = '_blank'; link.rel = 'noopener'; card.append(link);
    const details = element('details'); details.append(element('summary', 'Original reference'), element('p', source.url)); card.append(details);
    $('sources').append(card);
  }
  $('unknown-label').hidden = !result.terms.some(t => t.status === 'unknown');
  updateGenerate();
}
function meetingFields() { return {project: $('project').value.trim(), meeting_date: $('meeting-date').value}; }
function renderMeetings(context) {
  const panel = $('meeting-history'); panel.replaceChildren(); panel.hidden = !context;
  if (!context) return;
  panel.append(element('h3', 'Since the previous meeting'), element('p', context.method, 'helper'));
  panel.append(element('p', `${context.meetings.length} earlier meeting${context.meetings.length === 1 ? '' : 's'} in ${context.project}. Same-day and later meetings are excluded.`));
  for (const meeting of context.meetings) {
    const detail = element('details'); detail.append(element('summary', `[${meeting.citation}] ${meeting.meeting_date} · ${meeting.title}`), element('p', meeting.notes, 'source-excerpt'));
    panel.append(detail);
  }
  for (const item of context.changes) panel.append(element('p', `${item.key}: ${item.previous ? item.previous.status + ' → ' : ''}${item.status} (${item.change}) — ${item.text}`, 'term-card'));
  for (const item of context.carried_forward) panel.append(element('p', `Carry forward ${item.key}: ${item.status} — ${item.text} — Not mentioned this time; still unresolved.`, 'warning'));
  const diff = element('details'); diff.append(element('summary', 'Text changes since the latest earlier meeting'));
  diff.append(element('h4', 'New or reworded lines'), element('p', context.new_lines.join('\n'), 'source-excerpt'));
  diff.append(element('h4', 'Not repeated — does not mean resolved'), element('p', context.not_repeated.join('\n'), 'source-excerpt')); panel.append(diff);
  panel.append(element('p', 'Statuses are reported in the notes. They do not approve changes to Confluence policy.', 'helper'));
}
$('save-meeting').onclick = () => action($('save-meeting'), async () => {
  await api('/api/meetings', {...meetingFields(), title: $('title').value, notes: $('notes').value});
  invalidateRetrieval(); message('Meeting saved. Use this project with a later meeting date to compare progress. Find business context again before drafting.');
});
$('meeting-sample').onclick = () => action($('meeting-sample'), async () => {
  await api('/api/meetings', {project: 'Fictional Cobra pilot', meeting_date: '2026-09-01', title: 'Cobra discovery',
    notes: 'FICTIONAL EDUCATIONAL EXAMPLE\nDiscuss Cobra and FHP room readiness.\n[OPEN] PILOT-1 | Assign a pilot owner.\n[OPEN] RULE-1 | Ask the policy owner about 30 days in advance.\n[BLOCKED] ACCESS-1 | Review room accessibility.'});
  $('project').value = 'Fictional Cobra pilot'; $('meeting-date').value = '2026-09-08';
  $('title').value = 'Cobra pilot follow-up'; $('domain').value = 'workplace';
  $('notes').value = 'FICTIONAL EDUCATIONAL EXAMPLE\nFollow up on Cobra and FHP readiness.\n[DONE] PILOT-1 | Fictional team reports a pilot owner was assigned.\n[IN_PROGRESS] RULE-1 | Policy owner is reviewing 30 days in advance; no approval yet.\n[OPEN] REMINDER-1 | Explore reminders for an incomplete handover checklist.';
  invalidateRetrieval(); message('Saved a fictional September 1 meeting and loaded September 8 notes. Click Find business context to compare them.');
});
$('retrieve').onclick = () => action($('retrieve'), async () => {
  const choices = Object.fromEntries([...document.querySelectorAll('.term-choice')].filter(e => e.value).map(e => [e.dataset.term, e.value]));
  for (const term of retrieval?.terms || []) if (term.selected) choices[term.term.toLowerCase()] = term.selected.source_id;
  const epoch = ++retrievalEpoch;
  const result = await api('/api/retrieve', {...meetingFields(), title: $('title').value, notes: $('notes').value, domain: $('domain').value, choices});
  if (epoch !== retrievalEpoch) return;
  renderRetrieval(result); message('Business context retrieved. Review the definitions and source excerpts before drafting.');
});
$('sample').onclick = () => {
  $('project').value = ''; $('meeting-date').value = '';
  $('title').value = 'Cobra room readiness improvements'; $('notes').value = config.sample_notes;
  $('domain').value = 'workplace'; invalidateRetrieval();
  message('Cobra/FHP sample loaded. Click Find business context. Choose All domains to demonstrate ambiguous FHP terminology.');
};
$('mode').onchange = () => $('generate').textContent = $('mode').value === 'copilot' ? 'Prepare Copilot brief →' : 'Generate offline sample →';
$('upload').onchange = async event => {
  const file = event.target.files[0]; if (!file) return;
  try {
    if (!/\.(txt|md)$/i.test(file.name) || file.size > 96000) throw new Error('Choose a .txt or .md file under 96 KB.');
    const text = await file.text();
    if (text.length > config.max_notes) throw new Error('Notes must be at most 24,000 characters.');
    $('notes').value = text; invalidateRetrieval(); message(`Loaded ${file.name}.`);
  } catch (error) { message(error.message, true); }
  finally { event.target.value = ''; }
};
$('create-form').onsubmit = event => {
  event.preventDefault(); if (!canLeave()) return;
  action($('generate'), async () => {
    const doc = await api('/api/documents', {...meetingFields(), title: $('title').value, notes: $('notes').value,
      kind: $('kind').value, mode: $('mode').value, domain: $('domain').value,
      retrieval_id: retrieval?.id, context_confirmed: $('context-confirmed').checked,
      acknowledge_unresolved: $('unknown-ack').checked,
      source_ids: [...document.querySelectorAll('[name=source]:checked')].map(e => e.value)});
    $('message').hidden = true; await openDocument(doc.id); await history();
  });
};
$('copy-brief').onclick = () => action($('copy-brief'), async () => {
  try { await navigator.clipboard.writeText($('brief').value); message('Brief copied. Paste it into your approved Copilot Chat.'); }
  catch { $('brief').select(); message('Copy the selected brief, or use Download brief.'); }
});
$('import').onclick = () => action($('import'), async () => {
  let raw = $('copilot-result').value.trim();
  raw = raw.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '');
  let result; try { result = JSON.parse(raw); } catch { throw new Error('The response is not valid JSON. Ask Copilot to correct it using the exact brief schema.'); }
  render(await api(endpoint('import'), {result})); await history();
  message('Draft imported. Citation IDs and section structure passed checks; factual accuracy still requires your review.');
});
$('save').onclick = () => action($('save'), async () => {
  const sections = current.sections.map((s, i) => ({heading: s.heading, body: $(`section-${i}`).value}));
  render(await api(endpoint('save'), {revision: current.revision, sections}));
  await history(); message('Changes saved as a new revision. Approval must be renewed.');
});
$('reviewed').onchange = () => setDirty(dirty);
$('approve').onclick = () => action($('approve'), async () => {
  render(await api(endpoint('approve'), {revision: current.revision, reviewed: $('reviewed').checked}));
  await history(); message('Current revision approved in this local demo. You can now create a simulated Confluence page.');
});
$('word').onclick = event => { if (dirty) { event.preventDefault(); message('Save edits before downloading.', true); } };
$('publish').onclick = () => {
  $('publish-summary').textContent = `${current.title} · revision ${current.revision}`;
  $('publish-dialog').showModal();
};
$('confirm-publish').onclick = () => action($('confirm-publish'), async () => {
  render(await api(endpoint('publish'), {revision: current.revision, parent: $('parent').value}));
  $('publish-dialog').close(); await history(); message('Demo page created locally. Nothing was sent to Confluence.');
});
window.addEventListener('beforeunload', event => { if (dirty) { event.preventDefault(); event.returnValue = ''; } });
async function init() {
  config = await api('/api/config');
  for (const [id, template] of Object.entries(config.templates)) {
    const option = element('option', template.name); option.value = id; $('kind').append(option);
  }
  for (const [id, name] of Object.entries(config.domains)) {
    const option = element('option', name); option.value = id; $('domain').append(option);
  }
  $('index-info').textContent = `${config.knowledge.pages} fictional pages · ${config.knowledge.chunks} indexed sections · local retrieval`;
  await history();
}
init().catch(error => message(error.message, true));
