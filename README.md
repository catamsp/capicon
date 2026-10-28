# capicons

A static, CDN-served icon repository for launcher apps. Merges two upstream
icon collections — **Lawnicons** (monochrome outlined/themed icons) and
**Simple Icons** (solid brand glyphs) — plus your own custom icons
(**capicons**), behind one unified mapping file.

- **No app, no server.** This repo *is* the CDN asset source. Point your app at
  jsDelivr (or GitHub Pages) and render with Coil / any image loader.
- **Upstream preserved.** Both upstreams are vendored in full (with git
  history) under `third_party/` and synced on a schedule; the CDN-ready tree is
  regenerated from them, never hand-edited.

## Layout

```
icons/<source>/svg/*.svg        # canonical SVGs (lawnicons | simpleicons | capicons)
png/<source>/<size>/*.png       # pre-rendered PNGs: 48, 96, 192, 432 px
metadata/mapping.json           # ★ unified mapping: app name -> components -> icon files
metadata/appfilter.xml          # generated, launcher-standard appfilter format
metadata/lawnicons.json         # upstream appfilter parsed (component -> drawable)
metadata/simple-icons.json      # upstream brand metadata (slug -> title/hex/license/source)
metadata/capicons.json          # your custom icons' metadata
metadata/reports/               # triage reports (unmatched icons, license review)
third_party/lawnicons/          # full upstream repo + history (Apache-2.0)
third_party/simple-icons/       # full upstream repo + history (CC0, see DISCLAIMER)
tools/                          # the pipeline: sync, map, render, validate
```

## Usage from your app (Coil)

```
https://cdn.jsdelivr.net/gh/<owner>/<repo>@<tag>/metadata/mapping.json
https://cdn.jsdelivr.net/gh/<owner>/<repo>@<tag>/png/lawnicons/192/spotify.png
```

1. Fetch `mapping.json` once per app start (cache it).
2. Look up an icon by key (or by Android component ID).
3. Fetch the PNG at the density you need, or the SVG as fallback.

Pin a release tag for stability, or use a branch name for live updates
(jsDelivr caches branch URLs for 12h — prefer tags for predictable rollouts).

## Pipeline

```console
python tools/sync_upstream.py     # copy vendored upstream assets into icons/, metadata/, refresh lockfile
python tools/build_mapping.py     # join the 3 sources -> mapping.json, appfilter.xml, reports
python tools/render_png.py        # SVG -> PNG at 48/96/192/432 px (needs resvg, hash-cached)
python tools/validate.py --strict # CI gate: files exist, denylist enforced, XML sorted, license review
```

### Syncing upstream

```console
git fetch <lawnicons-remote> develop
git subtree add --prefix=third_party/lawnicons <lawnicons-remote> <sha>   # first time only
git subtree pull  --prefix=third_party/lawnicons <lawnicons-remote> develop  # later
# same for simple-icons, prefix third_party/simple-icons
python tools/sync_upstream.py && python tools/build_mapping.py && python tools/render_png.py && python tools/validate.py --strict
```

A scheduled GitHub Action (see `.github/workflows/`) runs this weekly and opens
a pull request with a summary of icon changes.

### Adding your own icons (capicons)

1. Drop the SVG into `icons/capicons/svg/<key>.svg`.
2. Add an entry to `metadata/capicons.json` (name, optional Android component
   IDs / packages, color, license).
3. Run `python tools/build_mapping.py && python tools/render_png.py && python tools/validate.py`.

### Blocking an icon (brand removal)

Add its mapping key to `DENYLIST.json`. It is excluded from every generated
output at every future sync.

## License

Original tooling, mapping and capicons: MIT (see `LICENSE`).
Vendored icons: Lawnicons Apache-2.0, Simple Icons CC0 — see
`THIRD_PARTY_NOTICES.md`. Brand icons are trademarks of their owners; this
repo grants no trademark rights.
