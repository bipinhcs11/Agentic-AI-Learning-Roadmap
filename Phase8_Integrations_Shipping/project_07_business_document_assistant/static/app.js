'use strict';
const $ = id => document.getElementById(id);
let config, current, dirty = false, pollToken = 0;
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
    $('evidence').append(element('p', `[${source.citation}] ${source.title} · version ${source.version}\n${source.url}\n${source.text}`));
  }
  $('evidence').append(element('p', `[N1] Meeting notes snapshot\n${doc.notes}`));
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
  finally { button.disabled = false; if (current?.sections) setDirty(dirty); }
}
$('sample').onclick = () => {
  $('title').value = 'Meeting room booking improvements'; $('notes').value = config.sample_notes;
  document.querySelectorAll('[name=source]').forEach(e => e.checked = true);
  message('Fictional sample loaded. Choose Copilot-assisted drafting or offline sample mode.');
};
$('mode').onchange = () => $('generate').textContent = $('mode').value === 'copilot' ? 'Prepare Copilot brief →' : 'Generate offline sample →';
$('upload').onchange = async event => {
  const file = event.target.files[0]; if (!file) return;
  try {
    if (!/\.(txt|md)$/i.test(file.name) || file.size > 96000) throw new Error('Choose a .txt or .md file under 96 KB.');
    const text = await file.text();
    if (text.length > config.max_notes) throw new Error('Notes must be at most 24,000 characters.');
    $('notes').value = text; message(`Loaded ${file.name}.`);
  } catch (error) { message(error.message, true); }
  finally { event.target.value = ''; }
};
$('create-form').onsubmit = event => {
  event.preventDefault(); if (!canLeave()) return;
  action($('generate'), async () => {
    const doc = await api('/api/documents', {title: $('title').value, notes: $('notes').value,
      kind: $('kind').value, mode: $('mode').value,
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
  for (const source of config.sources) {
    const card = element('div', undefined, 'source'); const label = element('label');
    const input = element('input'); input.type = 'checkbox'; input.name = 'source'; input.value = source.id;
    const info = element('span', source.title); info.append(element('small', `${source.citation} · Version ${source.version} · Fictional context`));
    label.append(input, info); const details = element('details');
    details.append(element('summary', 'Read source'), element('p', source.text)); card.append(label, details); $('sources').append(card);
  }
  await history();
}
init().catch(error => message(error.message, true));
