# Third-party notices

This repository vendors and redistributes content from two upstream open-source
projects. Both remain the property of their respective owners. Brand icons are
trademarks of their respective owners; this repository grants no trademark
rights. This repository is not affiliated with, endorsed by, or sponsored by
Lawnchair Launcher, Simple Icons, or any brand represented by an icon herein.

## Lawnicons

- Source: https://github.com/LawnchairLauncher/lawnicons
- License: Apache License 2.0 (full text in `third_party/lawnicons/LICENSE`)
- Vendored at: `third_party/lawnicons/` (full upstream history, unmodified)
- Redistribution: SVG icons under `icons/lawnicons/svg/` and rendered PNGs under
  `png/lawnicons/` are unmodified copies of upstream assets. The generated file
  `metadata/appfilter.xml` and `metadata/lawnicons.json` are derived from
  upstream `app/assets/appfilter.xml` and are additionally licensed under this
  repository's MIT license.

Apache License 2.0 notice: the icons and data derived from Lawnicons are
provided "AS IS", without warranty of any kind. See the Apache-2.0 license text
for the full terms, including the requirements on modified files (none of the
vendored Lawnicons files are modified).

## Simple Icons

- Source: https://github.com/simple-icons/simple-icons
- License: CC0 1.0 Universal (full text in `third_party/simple-icons/LICENSE.md`)
- Important: read `third_party/simple-icons/LICENSE.md` and
  `third_party/simple-icons/DISCLAIMER.md` — although the collection is CC0,
  individual icons are brand assets. Some icons carry per-icon license data in
  `metadata/simple-icons.json` (field `license`); such icons are surfaced in
  `metadata/reports/license-review.json` for manual review before commercial
  use, and can be blocked via `tools/overrides.json`.
- Vendored at: `third_party/simple-icons/` (full upstream history, unmodified)
- Redistribution: SVG icons under `icons/simpleicons/svg/` and rendered PNGs
  under `png/simpleicons/` are unmodified copies of upstream assets.

## Brand removal requests

If you own a brand represented in this repository and want it removed, open an
issue with proof of affiliation, or a pull request adding the icon key to
`DENYLIST.json`. Denylisted icons are excluded from `metadata/mapping.json`,
`metadata/appfilter.xml`, `icons/` and `png/` at every upstream sync.
