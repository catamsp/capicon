# IMPORTANT — PENDING ACTIONS (look later)

Status: repo built and committed locally (branch `main`), **not pushed**.
License triage **EXECUTED** (see section 1) — `validate.py --strict` now passes: 13,066 icons, 0 warnings.

---

## 1. License triage — ✅ DONE (2026-10-29)

Risky icons reviewed and removed automatically by `tools/triage_licenses.py`:

- 🗑️ **37 icons BLOCKED** → `DENYLIST.json` (files purged from `icons/`, `png/`, `metadata/`, `site/`):
  - 11 non-commercial (`CC-BY-NC*`): `cocoapods`, `gamebanana`, `letsencrypt`, `nodebb`, `pycqa`, `rubocop`, `tauri`, `misskey`, `robotframework`, `sass`, `vuedotjs`
  - 24 custom/unknown ToS: `broadcom`, `chianetwork`, `contentstack`, `coreboot`, `dify`, `douban`, `doubanread`, `effect`, `f_lux`, `fcc`, `fedora`, `flux`, `graphite_editor`, `harbor`, `kedro`, `keycloak`, `lemmy`, `minimax`, `pleroma`, `qase`, `quasar`, `rustfs`, `webex`, `webpack`
  - 2 no-derivatives (`CC-BY-ND*`, we rasterize SVG→PNG): `jpeg`, `slint`
- ✅ **188 icons REVIEWED & APPROVED** → `tools/overrides.json` `simpleicons_license_allowlist`
  (permissive Apache/MIT/CC0/BSD/Unlicense/MPL + CC-BY/CC-BY-SA attribution + GPL/AGPL unmodified aggregation)
- 🔄 **Auto-triage on every sync**: `.github/workflows/sync-upstream.yml` runs
  `triage_licenses.py` between builds — new NC/ND/custom icons from upstream are
  blocked without human review; new permissive/copyleft icons are allowlisted.

**Rule: never modify upstream SVGs** — the "keep" verdict depends on byte-identical
redistribution (pipeline already does this).

**Retriage / audit**: `python tools/build_mapping.py && python tools/triage_licenses.py && python tools/build_mapping.py && python tools/validate.py --strict`

### Trademark layer (separate from licenses, never solved by them)
Every logo is its own brand's trademark. Nominative use inside an icon pack is the
norm (Lawnicons ships on Play Store doing this), but removal requests can arrive at
any time → `DENYLIST.json` must stay ready; honor within hours (add `{"key": "..."}`
entries, then run the retriage line above).

---

## 2. Optional work items (choose when ready — NONE executed)

- [ ] **B. `ATTRIBUTIONS.md` generator** — new `tools/build_attributions.py` reading
      license fields out of `metadata/mapping.json`; link from app's licenses screen.
      (The approved list already exists: `tools/overrides.json` + `metadata/reports/license-review.json`)
- [ ] **C. Validator check: upstream SVGs byte-identical** — compare
      `icons/lawnicons/svg/*` and `icons/simpleicons/svg/*` against `third_party/` copies.
- [ ] **D. Source-scoped denylist** — support entries like `"simpleicons:rust"` so a
      flagged Simple Icons glyph can be dropped while keeping a Lawnicons outline of
      the same brand (5 dual-set brands were fully removed in the triage: `douban`,
      `f_lux`, `flux`, `minimax`, `webex`).
- [ ] ~~**A. Populate `DENYLIST.json`**~~ ✅ done (37 entries)
- [ ] ~~**E. Custom-ToS review pass**~~ ✅ done (blanket-blocked pending individual review)

---

## 3. Launch checklist (repo mechanics, also not done)

- [ ] Set real git identity (currently placeholder `capicons <capicons@users.noreply.github.com>`):
      `git config user.name "..." && git config user.email "..."`
- [ ] Create public GitHub repo + `git push -u origin main` (~430 MiB packed)
- [ ] Actions settings: enable write permissions + "Allow GitHub Actions to create PRs"
      (needed by `.github/workflows/sync-upstream.yml` 4-monthly sync)
- [ ] Settings → Pages → Source: **GitHub Actions** (needed by `.github/workflows/deploy-pages.yml`)
- [ ] Verify first scheduled sync PR works end-to-end
- [ ] Tag first release (e.g. `v2026.10.29`) for jsDelivr pinning:
      `https://cdn.jsdelivr.net/gh/<you>/capicons@<tag>/png/lawnicons/192/<key>.png`
- [ ] Add first custom icon: `python tools/add_capicon.py my.svg --name "My App" --component pkg/pkg.Activity`

---

*See `THIRD_PARTY_NOTICES.md` for licensing details and `README.md` for the pipeline.*
