# IMPORTANT — PENDING ACTIONS (look later)

Status: repo built and committed locally (branch `main`), **not pushed**, license triage **deliberately skipped**. Nothing in this file has been executed yet.

---

## 1. License triage (225 flagged icons — READ before commercial launch)

Source of truth: `metadata/reports/license-review.json` (regenerated on every build).
Gate: `python tools/validate.py --strict` currently FAILS on these (by design) — run it in lenient mode until triaged.

### 🔴 Tier 1 — REMOVE: Non-commercial (`NC`) licenses, 11 icons — hard blockers
Commercial product + NC license = direct conflict. No ambiguity.
`cocoapods`, `gamebanana`, `letsencrypt`, `nodebb`, `pycqa`, `rubocop`, `tauri`, `misskey`, `robotframework`, `sass`, `vuedotjs`

### 🟡 Tier 2 — REVIEW: `custom` ToS/EULA, 24 icons
Each points at the brand's own logo/ToS policy (trademark-heavy). Read each or blanket-denylist until reviewed.
`broadcom`, `chianetwork`, `contentstack`, `coreboot`, `dify`, `douban`, `doubanread`, `effect`, `f_lux`, `fcc`, `fedora`, `flux`, `graphite_editor`, `harbor`, `kedro`, `keycloak`, `lemmy`, `minimax`, `pleroma`, `qase`, `quasar`, `rustfs`, `webex`, `webpack`

### 🟢 Tier 3 — KEEP (unmodified) + attribution notices, ~109 icons
GPL/AGPL/MPL/CC-BY-SA + all permissive + CC-BY. Safe to ship **unmodified**:
obligation is notices only (aggregation/collection principle — they do NOT make the
app copyleft; share-alike only triggers on *modified* versions).
Includes: LibreOffice suite, GIMP, Rust, Debian, PHP, Ruby, GTK, Inkscape, Neovim,
Jenkins, Zig, Monero, ... (full list in license-review.json) + 23 CC-BY
(`android`, `git`, `angular`, `godotengine`, `nixos`, `yarn`, ...) + 96 permissive (MIT/Apache/CC0/BSD).

**Rule: never modify upstream SVGs** — the "keep" verdict depends on byte-identical
redistribution (pipeline already does this; validator check below would enforce it).

### Trademark layer (separate from licenses, never solved by them)
Every logo is its own brand's trademark. Nominative use inside an icon pack is the
norm (Lawnicons ships on Play Store doing this), but removal requests can arrive at
any time → `DENYLIST.json` must stay ready; honor within hours.

---

## 2. Optional work items (choose when ready — NONE executed)

- [ ] **A. Populate `DENYLIST.json`** with Tier 1 (11 icons), optionally Tier 2 (24).
      Then run: `python tools/sync_upstream.py && python tools/build_mapping.py && python tools/render_png.py && python tools/validate.py --strict`
- [ ] **B. `ATTRIBUTIONS.md` generator** — new `tools/build_attributions.py` reading
      license fields out of `metadata/mapping.json`; link from app's licenses screen.
- [ ] **C. Validator check: upstream SVGs byte-identical** — compare
      `icons/lawnicons/svg/*` and `icons/simpleicons/svg/*` against `third_party/` copies.
- [ ] **D. Source-scoped denylist** — support entries like `"simpleicons:rust"` so a
      flagged Simple Icons glyph can be dropped while keeping the Apache-2.0 Lawnicons
      outline of the same brand.
- [ ] **E. Custom-ToS review pass** — go through Tier 2 list one by one.

---

## 3. Launch checklist (repo mechanics, also not done)

- [ ] Set real git identity (currently placeholder `capicons <capicons@users.noreply.github.com>`):
      `git config user.name "..." && git config user.email "..."`
- [ ] Create public GitHub repo + `git push -u origin main` (~430 MiB packed)
- [ ] Actions settings: enable write permissions + "Allow GitHub Actions to create PRs"
      (needed by `.github/workflows/sync-upstream.yml` weekly sync)
- [ ] Verify first scheduled sync PR works end-to-end
- [ ] Tag first release (e.g. `v2026.10.29`) for jsDelivr pinning:
      `https://cdn.jsdelivr.net/gh/<you>/capicons@<tag>/png/lawnicons/192/<key>.png`
- [ ] Add first custom icon: `python tools/add_capicon.py my.svg --name "My App" --component pkg/pkg.Activity`

---

*See `THIRD_PARTY_NOTICES.md` for licensing details and `README.md` for the pipeline.*
