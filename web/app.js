/* capicons site — virtualized grid + worker search + triage console. */
'use strict';

const $ = s => document.querySelector(s);
const viewport = $('#viewport'), spacer = $('#spacer'), cells = $('#cells');
const qInput = $('#q'), statsEl = $('#stats'), countEl = $('#count');
const drawer = $('#drawer'), drawerBody = $('#drawerbody'), scrim = $('#scrim');
const triageBar = $('#triagebar');

let docs = [];              // name-sorted records from build_site.py
let byKey = new Map();
let results = [];           // array of keys, current result set
let meta = null;
let sel = new Set();        // triage selection
let triageMode = false;
let activeFilters = { sources: ['lawnicons', 'simpleicons', 'capicons'], tiers: [0, 1, 2] };
let msgId = 0, pending = new Map();

const worker = new Worker('search.worker.js');
worker.onmessage = e => {
  const m = e.data;
  if (m.type === 'ready') runSearch();
  else if (m.type === 'results') {
    const cb = pending.get(m.id);
    if (cb) { pending.delete(m.id); cb(m.keys); }
  } else if (m.type === 'error') toast('worker error: ' + m.message);
};

function search(q, cb) {
  const id = ++msgId;
  pending.set(id, cb);
  worker.postMessage({ type: 'search', id, q, sources: activeFilters.sources, tiers: activeFilters.tiers });
}

let searchTimer = null;
function runSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    const q = qInput.value.trim();
    search(q, keys => {
      results = keys;
      viewport.scrollTop = 0;
      updateStats(q);
      render();
    });
  }, 50);
}

function updateStats(q) {
  const n = results.length;
  statsEl.textContent = (q ? `${n.toLocaleString()} match${n === 1 ? '' : 'es'}` : `${n.toLocaleString()} shown`);
  $('#empty').hidden = n !== 0;
}

/* ---------------- virtualized grid ---------------- */

const CELL_W = 108, CELL_H = 118, PAD = 8;
let cols = 1, winStart = 0, winEnd = 0;

function layout() {
  cols = Math.max(1, Math.floor(viewport.clientWidth / CELL_W));
  const rows = Math.ceil(results.length / cols);
  spacer.style.height = rows * CELL_H + 'px';
}

function render() {
  layout();
  const first = Math.max(0, Math.floor(viewport.scrollTop / CELL_H) - 2);
  const last = Math.ceil((viewport.scrollTop + viewport.clientHeight) / CELL_H) + 2;
  winStart = first * cols;
  winEnd = Math.min(results.length, last * cols);
  const html = [];
  for (let i = winStart; i < winEnd; i++) html.push(cell(results[i], i));
  cells.innerHTML = html.join('');
}

function cell(key, i) {
  const d = byKey.get(key);
  if (!d) return '';
  const row = Math.floor(i / cols), col = i % cols;
  const left = col * CELL_W + PAD, top = row * CELL_H + PAD;
  const checked = sel.has(key) ? ' checked' : '';
  return `<div class="cell${triageMode ? ' triage' : ''}" data-k="${esc(key)}" style="left:${left}px;top:${top}px">
    ${triageMode ? `<input type="checkbox" class="selbox" data-k="${esc(key)}"${checked}>` : ''}
    <span class="thumb mask" data-color="${d.col ? '#' + d.col : ''}" data-src="${esc(d.f48)}"></span>
    <span class="label" title="${esc(d.n)}">${esc(short(d.n))}</span>
  </div>`;
}

function short(s) { return s.length > 14 ? s.slice(0, 13) + '…' : s; }

function paintThumbs(root) {
  for (const el of (root || cells).querySelectorAll('.thumb.mask:not(.painted)')) {
    const url = `url("${el.dataset.src}")`;
    el.style.webkitMaskImage = url;
    el.style.maskImage = url;
    el.style.background = el.dataset.color || 'currentColor';
    el.classList.add('painted');
  }
}

/* ---------------- detail drawer ---------------- */

function openDrawer(key) {
  const d = byKey.get(key);
  if (!d) return;
  const tierBadge = ['<span class="badge t0">✓ keep</span>', '<span class="badge t1">▲ review</span>', '<span class="badge t2">✕ block</span>'][d.t];
  const srcBadges = d.s.map(s => `<span class="badge src">${s}</span>`).join(' ');
  const lic = d.lt
    ? `<div class="row"><span class="muted">License</span><span class="mono">${esc(d.lt)}${d.ss ? ` · <a href="https://simpleicons.org/icons/${esc(d.ss)}.svg" target="_blank" rel="noopener">upstream page</a>` : ''}</span></div>`
    : '<div class="row"><span class="muted">License</span><span class="mono">no explicit license (see THIRD_PARTY_NOTICES.md)</span></div>';
  const pkgs = d.p.length
    ? `<div class="pkgs">${d.p.map(p => `<code class="pkg">${esc(p)}</code>`).join('')}</div>`
    : '<span class="muted">—</span>';
  const compList = d.comp.length
    ? `<details><summary>${d.comp.length} component${d.comp.length === 1 ? '' : 's'}</summary>
       <div class="comps">${d.comp.map(c => `<code class="pkg">${esc(c)}</code>`).join('')}</div></details>`
    : '';

  drawerBody.innerHTML = `
    <div class="preview mask" id="dpreview"></div>
    <h2>${esc(d.n)}</h2>
    <div class="badges">${tierBadge} ${srcBadges} <span class="badge key mono">${esc(d.k)}</span></div>
    <div class="row"><span class="muted">Color</span><span class="mono">${d.col ? '#' + esc(d.col) : '—'}</span></div>
    ${lic}
    <div class="row"><span class="muted">Packages</span>${pkgs}</div>
    ${compList}
    <div class="btnrow">
      <button class="btn" data-copy="${esc(meta.cdn + d.f48)}">Copy CDN PNG (48)</button>
      <button class="btn" data-copy="${esc(meta.cdn + d.f48.replace('/48/', '/192/'))}">Copy CDN PNG (192)</button>
      <button class="btn" data-copy="${esc(meta.cdn + d.fs)}">Copy CDN SVG</button>
    </div>`;

  const prev = $('#dpreview');
  const url = `url("${d.fs}")`;
  prev.style.webkitMaskImage = url;
  prev.style.maskImage = url;
  prev.style.background = d.col ? '#' + d.col : 'currentColor';
  prev.classList.add('painted');

  drawerBody.querySelectorAll('[data-copy]').forEach(b =>
    b.addEventListener('click', () => copy(b.dataset.copy, 'URL copied')));

  drawer.hidden = false;
  scrim.hidden = false;
  document.body.classList.add('drawer-open');
}

function closeDrawer() {
  drawer.hidden = true;
  scrim.hidden = true;
  document.body.classList.remove('drawer-open');
}

/* ---------------- triage console ---------------- */

function setTriage(on) {
  triageMode = on;
  $('#triage').classList.toggle('on', on);
  triageBar.hidden = !on;
  updateSelCount();
  render();
}

function updateSelCount() {
  $('#selcount').textContent = `${sel.size} selected`;
}

function toggleSel(key, on) {
  if (on) sel.add(key); else sel.delete(key);
  updateSelCount();
}

$('#selallvisible').onclick = () => { for (const k of results) sel.add(k); updateSelCount(); render(); };
$('#clearsel').onclick = () => { sel.clear(); updateSelCount(); render(); };

$('#copydeny').onclick = () => {
  const keys = [...sel].sort();
  copy(JSON.stringify({ icons: keys }, null, 2) + '\n', `${keys.length} keys copied — paste into DENYLIST.json "icons"`);
};
$('#copyallow').onclick = () => {
  const slugs = [...sel].map(k => byKey.get(k)).filter(d => d && d.ss).map(d => d.ss).sort();
  copy(JSON.stringify(slugs, null, 2) + '\n', `${slugs.length} slugs copied — paste into tools/overrides.json "simpleicons_license_allowlist"`);
};

/* ---------------- chips / theme / misc ---------------- */

document.querySelectorAll('.chipgroup').forEach(g => {
  g.addEventListener('click', e => {
    const chip = e.target.closest('.chip');
    if (!chip) return;
    chip.classList.toggle('on');
    const kind = g.dataset.kind;
    const on = [...g.querySelectorAll('.chip.on')].map(c => c.dataset.v);
    if (kind === 'source') activeFilters.sources = on;
    else activeFilters.tiers = on.map(Number);
    runSearch();
  });
});

$('#theme').onclick = () => {
  const dark = document.documentElement.dataset.theme !== 'dark';
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  localStorage.setItem('theme', dark ? 'dark' : 'light');
};
document.documentElement.dataset.theme = localStorage.getItem('theme') || 'dark';

$('#triage').onclick = () => setTriage(!triageMode);
$('#closedrawer').onclick = closeDrawer;
scrim.onclick = closeDrawer;
qInput.addEventListener('input', runSearch);
viewport.addEventListener('scroll', () => requestAnimationFrame(render), { passive: true });
window.addEventListener('resize', render);

document.addEventListener('keydown', e => {
  if (e.key === '/' && document.activeElement !== qInput) { e.preventDefault(); qInput.focus(); qInput.select(); }
  if (e.key === 'Escape') closeDrawer();
});

cells.addEventListener('click', e => {
  const box = e.target.closest('.selbox');
  if (box) { toggleSel(box.dataset.k, box.checked); return; }
  const c = e.target.closest('.cell');
  if (c) openDrawer(c.dataset.k);
});

function esc(s) {
  return String(s).replace(/[&<>"']/g, ch =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
}

function copy(text, okMsg) {
  navigator.clipboard.writeText(text).then(
    () => toast(okMsg || 'Copied'),
    () => toast('clipboard failed — see console') || console.log(text)
  );
}

let toastTimer = null;
function toast(msg) {
  const t = $('#toast');
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, 2600);
}

/* ---------------- boot ---------------- */

(async function boot() {
  meta = await (await fetch('data/meta.json')).json();
  docs = await (await fetch('data/index.json')).json();
  for (const d of docs) byKey.set(d.k, d);
  countEl.textContent = `${meta.total.toLocaleString()} icons`;
  $('#geninfo').textContent =
    `built ${meta.generated.slice(0, 10)} · lawnicons ${meta.upstreams.lawnicons.slice(0, 7)} · simple-icons ${meta.upstreams.simpleicons.slice(0, 7)}`;
  render();
  worker.postMessage({ type: 'init', docs });  // one fetch, worker indexes its own copy
})();
