/* capicons search worker — MiniSearch over the icon index.
   Runs fully off the main thread; the UI just exchanges small messages. */
'use strict';
importScripts('vendor/minisearch.js');

let docs = [];          // full record array (name-sorted, from build_site.py)
let byKey = new Map();  // key -> doc
let ms = null;
let ready = false;
const MAX_RESULTS = 5000;

function passes(doc, sources, tiers) {
  if (tiers.length && !tiers.includes(doc.t)) return false;
  if (sources.length) {
    let hit = false;
    for (const s of doc.s) { if (sources.includes(s)) { hit = true; break; } }
    if (!hit) return false;
  }
  return true;
}

self.onmessage = (e) => {
  const msg = e.data;
  if (msg.type === 'init') {
    docs = msg.docs;
    for (const d of docs) byKey.set(d.k, d);
    ms = new MiniSearch({
      idField: 'k',
      fields: ['n', 'k', 'p', 'comp'],
      storeFields: ['t'],
      searchOptions: {
        prefix: true,
        fuzzy: 0.2,
        boost: { k: 4, n: 3, p: 2, comp: 1 },
        combineWith: 'AND',
      },
    });
    ms.addAll(docs.map(d => ({ k: d.k, n: d.n, p: d.p, comp: d.comp, t: d.t })));
    ready = true;
    self.postMessage({ type: 'ready', total: docs.length });
    return;
  }
  if (msg.type !== 'search') return;
  if (!ready) { self.postMessage({ type: 'results', id: msg.id, keys: [], total: 0 }); return; }
  const { q, sources, tiers, id } = msg;
  let keys;
  if (!q) {
    keys = [];
    for (const d of docs) if (passes(d, sources, tiers)) keys.push(d.k);
  } else {
    const hits = ms.search(q);
    keys = [];
    for (const h of hits) {
      if (keys.length >= MAX_RESULTS) break;
      const d = byKey.get(h.id);
      if (d && passes(d, sources, tiers)) keys.push(d.k);
    }
  }
  self.postMessage({ type: 'results', id, keys, total: keys.length });
};
