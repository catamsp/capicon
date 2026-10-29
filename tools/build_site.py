#!/usr/bin/env python3
"""Build the static search/browse site (GitHub Pages) from metadata/mapping.json.

Outputs site/ containing:
  - web shell (index.html, app.js, styles.css, search.worker.js, vendor/)
  - site/data/index.json   compact search index (name, key, packages, components,
                           license tier, colors, asset paths)
  - site/data/meta.json    counts, upstream SHAs, CDN base URL
  - site/icons/<source>/svg/*.svg     full SVGs (detail drawer + downloads)
  - site/png/<source>/48/*.png        48px thumbnails (virtualized grid)

The site is fully static: search runs in a Web Worker with MiniSearch.
Local preview:  python tools/build_site.py && python -m http.server -d site

CDN_BASE below is used for the "copy CDN URL" buttons. Edit it once after the
GitHub repo exists (owner/repo), or pass --cdn-base.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

# TODO(owner): set to your real GitHub repo after creating it, e.g.
# "https://cdn.jsdelivr.net/gh/you/capicons@main/"
CDN_BASE = "https://cdn.jsdelivr.net/gh/OWNER/REPO@main/"

SRC_PREFERENCE = ("lawnicons", "simpleicons", "capicons")


def tier_of(license_type: str | None, slug: str | None, allowlist: set[str]) -> int:
    """0 = keep, 1 = review, 2 = block (see IMPORTANT.md tiers)."""
    if not license_type:
        return 0
    if slug and slug in allowlist:
        return 0
    lt = license_type.strip()
    if "NC" in lt.upper():
        return 2
    if lt.lower() == "custom":
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cdn-base", default=CDN_BASE)
    args = ap.parse_args()
    t0 = time.time()

    mapping = json.loads((ROOT / "metadata" / "mapping.json").read_text(encoding="utf-8"))
    deny = json.loads((ROOT / "DENYLIST.json").read_text(encoding="utf-8"))
    overrides = json.loads((ROOT / "tools" / "overrides.json").read_text(encoding="utf-8"))
    allowlist = set(overrides.get("simpleicons_license_allowlist", []))
    denied = set(deny.get("icons", []))

    icons = mapping["icons"]
    records = []
    tier_counts = {0: 0, 1: 0, 2: 0}
    src_counts: dict[str, int] = {}

    for key, v in icons.items():
        if key in denied:  # belt & braces; build_mapping already excludes these
            continue
        sources = v.get("sources", [])
        for s in sources:
            src_counts[s] = src_counts.get(s, 0) + 1

        lic = (v.get("license") or {}).get("type")
        slug = v.get("simpleicons_slug")
        tier = tier_of(lic, slug, allowlist)
        tier_counts[tier] += 1

        files = v.get("files", {})
        pngs = files.get("png", {})
        svgs = files.get("svg", {})
        # png keys come in two shapes: "simpleicons/48" (si-style) or bare "48" (lawn-style)
        f48 = None
        for s in SRC_PREFERENCE:
            f48 = pngs.get(f"{s}/48") or (pngs.get("48") if s in sources else None)
            if f48:
                break
        fs = None
        for s in SRC_PREFERENCE:
            fs = svgs.get(s)
            if fs:
                break
        if not f48 or not fs:
            continue

        records.append(
            {
                "k": key,
                "n": v.get("name", key),
                "s": sources,
                "p": v.get("packages", []),
                "comp": v.get("components", []),
                "ss": slug,
                "col": v.get("color"),
                "lt": lic,
                "t": tier,
                "f48": f48,
                "fs": fs,
            }
        )

    records.sort(key=lambda r: r["n"].lower())

    # --- data files -------------------------------------------------------
    data_dir = SITE / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "index.json").write_text(
        json.dumps(records, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    meta = {
        "total": len(records),
        "tiers": {"keep": tier_counts[0], "review": tier_counts[1], "block": tier_counts[2]},
        "sources": src_counts,
        "upstreams": {
            "lawnicons": mapping.get("upstreams", {}).get("lawnicons", "unknown"),
            "simpleicons": mapping.get("upstreams", {}).get("simple-icons")
            or mapping.get("upstreams", {}).get("simpleicons", "unknown"),
        },
        "cdn": args.cdn_base,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (data_dir / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")

    # --- web shell --------------------------------------------------------
    web = ROOT / "web"
    for name in ("index.html", "app.js", "styles.css", "search.worker.js"):
        shutil.copy2(web / name, SITE / name)
    shutil.copytree(web / "vendor", SITE / "vendor", dirs_exist_ok=True)

    # --- assets: 48px thumbnails + SVGs (mirrors repo-relative paths, so the
    #     same paths work locally and as jsDelivr URLs) ----------------------
    copied_png = copied_svg = 0
    for src in sorted(src_counts):
        # thumbnails
        src_png = ROOT / "png" / src / "48"
        dst_png = SITE / "png" / src / "48"
        if src_png.is_dir():
            dst_png.mkdir(parents=True, exist_ok=True)
            for f in src_png.glob("*.png"):
                shutil.copy2(f, dst_png / f.name)
                copied_png += 1
        # svgs
        src_svg = ROOT / "icons" / src / "svg"
        dst_svg = SITE / "icons" / src / "svg"
        if src_svg.is_dir():
            dst_svg.mkdir(parents=True, exist_ok=True)
            for f in src_svg.glob("*.svg"):
                shutil.copy2(f, dst_svg / f.name)
                copied_svg += 1

    idx_kb = (data_dir / "index.json").stat().st_size / 1024
    print(f"site built in {time.time() - t0:.1f}s")
    print(f"  records:  {len(records)}")
    print(f"  tiers:    keep={tier_counts[0]}  review={tier_counts[1]}  block={tier_counts[2]}")
    print(f"  assets:   {copied_png} png48, {copied_svg} svg")
    print(f"  index:    {idx_kb:.0f} KB   cdn base: {args.cdn_base}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
