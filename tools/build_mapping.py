#!/usr/bin/env python3
"""build_mapping.py - join the three icon sources into the unified mapping.

Inputs:
  third_party/lawnicons/app/assets/appfilter.xml   upstream component->drawable mapping
  metadata/simple-icons.json                        upstream brand metadata (slug/hex/license)
  metadata/capicons.json                            your custom icons
  tools/overrides.json                              manual join rules
  DENYLIST.json                                     icons that must never be served

Outputs:
  metadata/mapping.json        unified mapping (sorted, deterministic)
  metadata/appfilter.xml       generated launcher-standard appfilter (sorted)
  metadata/lawnicons.json      upstream appfilter parsed verbatim (provenance)
  metadata/reports/unmatched.json  triage report
  metadata/reports/license-review.json  icons carrying explicit per-icon licenses
"""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
META = ROOT / "metadata"
REPORTS = META / "reports"

LAWN_APPFILTER = ROOT / "third_party" / "lawnicons" / "app" / "assets" / "appfilter.xml"
SI_DATA = META / "simple-icons.json"
CAPICONS = META / "capicons.json"
OVERRIDES = ROOT / "tools" / "overrides.json"
DENYLIST = ROOT / "DENYLIST.json"
LOCK = ROOT / "upstreams.lock.json"


def slugify(name: str) -> str:
    """Normalize a display name to a comparable slug: 'A&W' -> 'aw', '北京一卡通' -> ''."""
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "", s)  # drop everything non-latin (CJK names match by alias only)
    return s


def load_json(path: Path):
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def parse_lawnicons() -> dict[str, dict]:
    """appfilter.xml -> {drawable: {'name': str, 'components': [...]}}"""
    tree = ET.parse(LAWN_APPFILTER)
    drawables: dict[str, dict] = {}
    for item in tree.getroot().findall("item"):
        component = item.get("component", "")
        drawable = item.get("drawable", "")
        name = item.get("name", "")
        if not component or not drawable:
            continue
        entry = drawables.setdefault(drawable, {"name": name or drawable, "components": []})
        entry["components"].append(component)
        if name and not entry["name"]:
            entry["name"] = name
    for entry in drawables.values():
        entry["components"] = sorted(set(entry["components"]))
    return drawables


def parse_simple_icons() -> dict[str, dict]:
    """simple-icons data -> {slug: {'title', 'hex', 'license', 'source', 'guidelines'}}"""
    data = load_json(SI_DATA)
    if data is None:
        die("metadata/simple-icons.json missing - run sync_upstream.py first")
    by_slug: dict[str, dict] = {}
    for brand in data:
        slug = brand.get("slug") or slugify(brand["title"])
        by_slug[slug] = {
            "title": brand["title"],
            "hex": brand.get("hex"),
            "license": brand.get("license"),
            "source": brand.get("source"),
            "guidelines": brand.get("guidelines"),
        }
    return by_slug


def build_si_index(si: dict[str, dict]) -> dict[str, str]:
    """slugified title/aliases -> slug, for fuzzy joins."""
    index: dict[str, str] = {}
    for slug, meta in si.items():
        index.setdefault(slugify(meta["title"]), slug)
    return index


def die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    lock = load_json(LOCK) or {}
    overrides = load_json(OVERRIDES) or {}
    denylist = {e["key"] for e in (load_json(DENYLIST) or {}).get("icons", [])}
    manual_join: dict[str, str] = overrides.get("lawnicons_to_simpleicons", {})

    lawn = parse_lawnicons()
    si = parse_simple_icons()
    si_index = build_si_index(si)
    cap = (load_json(CAPICONS) or {}).get("icons", [])

    icons: dict[str, dict] = {}
    unmatched_lawn: list[str] = []
    matched_si: set[str] = set()

    # ---- 1. Lawnicons drawables (outline/themed set) ----
    for drawable, meta in sorted(lawn.items()):
        if drawable in denylist:
            continue
        si_slug = None
        if drawable in si:
            si_slug = drawable
        elif drawable in manual_join:
            si_slug = manual_join[drawable]
        elif slugify(meta["name"]) in si_index:
            si_slug = si_index[slugify(meta["name"])]
        if si_slug and si_slug not in si:
            si_slug = None  # bad manual join; report below

        sources = ["lawnicons"] + (["simpleicons"] if si_slug else [])
        if not si_slug:
            unmatched_lawn.append(drawable)
        else:
            matched_si.add(si_slug)
        si_meta = si.get(si_slug, {})
        packages = sorted({c.split("/")[0] for c in meta["components"]})

        files: dict[str, dict] = {
            "svg": {"lawnicons": f"icons/lawnicons/svg/{drawable}.svg"},
            "png": {str(sz): f"png/lawnicons/{sz}/{drawable}.png" for sz in (48, 96, 192, 432)},
        }
        if si_slug:
            files["svg"]["simpleicons"] = f"icons/simpleicons/svg/{si_slug}.svg"
            files["png"].update(
                {f"simpleicons/{sz}": f"png/simpleicons/{sz}/{si_slug}.png" for sz in (48, 96, 192, 432)}
            )

        icons[drawable] = {
            "name": meta["name"],
            "sources": sources,
            "components": meta["components"],
            "packages": packages,
            "color": si_meta.get("hex"),
            "license": si_meta.get("license"),
            "simpleicons_slug": si_slug,
            "files": files,
        }

    # ---- 2. Simple Icons slugs not matched to any app (solid set standalone) ----
    for slug, si_meta in sorted(si.items()):
        if slug in denylist or slug in matched_si:
            continue
        icons[slug] = {
            "name": si_meta["title"],
            "sources": ["simpleicons"],
            "components": [],
            "packages": [],
            "color": si_meta.get("hex"),
            "license": si_meta.get("license"),
            "simpleicons_slug": slug,
            "files": {
                "svg": {"simpleicons": f"icons/simpleicons/svg/{slug}.svg"},
                "png": {f"simpleicons/{sz}": f"png/simpleicons/{sz}/{slug}.png" for sz in (48, 96, 192, 432)},
            },
        }

    # ---- 3. Capicons (custom, highest precedence) ----
    for entry in cap:
        key = Path(entry["svg"]).stem
        if key in icons:
            print(f"warning: capicons key '{key}' overrides an existing icon")
        if key in denylist:
            die(f"capicons key '{key}' is denylisted - remove it or the DENYLIST entry")
        files: dict[str, dict] = {"svg": {"capicons": entry["svg"]}, "png": {}}
        for sz in (48, 96, 192, 432):
            files["png"][f"capicons/{sz}"] = f"png/capicons/{sz}/{key}.png"
        components = entry.get("components", [])
        icons[key] = {
            "name": entry["name"],
            "sources": ["capicons"],
            "components": components,
            "packages": entry.get("packages") or sorted({c.split("/")[0] for c in components}),
            "color": entry.get("color"),
            "license": entry.get("license"),
            "simpleicons_slug": None,
            "files": files,
        }

    # ---- 4. Emit mapping.json (deterministic) ----
    mapping = {
        "format": 1,
        "upstreams": {k: v.get("commit") for k, v in lock.items()},
        "icons": {k: icons[k] for k in sorted(icons)},
    }
    (META / "mapping.json").write_text(
        json.dumps(mapping, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # ---- 5. Emit appfilter.xml (sorted by name, then component) ----
    rows = []
    for key, meta in icons.items():
        for component in meta["components"]:
            rows.append((meta["name"], component, key))
    rows.sort()
    lines = [
        "<?xml version='1' encoding='utf-8'?>",
        "<resources>",
        "    <!-- Generated by tools/build_mapping.py from metadata/mapping.json - DO NOT EDIT -->",
    ]
    for name, component, drawable in rows:
        esc = name.replace("&", "&amp;").replace("<", "&lt;").replace('"', "'")
        lines.append(f'    <item component="{component}" drawable="{drawable}" name="{esc}" />')
    lines.append("</resources>")
    (META / "appfilter.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---- 6. Provenance: upstream appfilter parsed verbatim ----
    (META / "lawnicons.json").write_text(
        json.dumps({"drawables": lawn}, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # ---- 7. Reports ----
    (REPORTS / "unmatched.json").write_text(
        json.dumps(
            {
                "lawnicons_without_simpleicons": sorted(unmatched_lawn),
                "counts": {
                    "mapping_total": len(icons),
                    "lawnicons_drawables": len(lawn),
                    "simpleicons_slugs": len(si),
                    "capicons": len(cap),
                    "matched_lawnicons_to_simpleicons": len(matched_si),
                    "unmatched_lawnicons": len(unmatched_lawn),
                    "simpleicons_standalone": len(si) - len(matched_si),
                },
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    flagged = sorted(
        {"key": k, "title": v["name"], "license": v["license"]}
        for k, v in icons.items()
        if v["sources"] == ["simpleicons"] and v.get("license")
    , key=lambda d: d["key"])
    (REPORTS / "license-review.json").write_text(
        json.dumps(
            {
                "comment": "Icons carrying explicit per-icon license data from Simple Icons. Review before commercial serving; block via tools/overrides.json simpleicons_license_allowlist is the opposite (allow) - use DENYLIST.json to block.",
                "icons": flagged,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"mapping.json: {len(icons)} icons "
        f"(lawnicons {len(lawn)}, simple-icons {len(si)}, capicons {len(cap)}; "
        f"{len(matched_si)} lawn<->si matches, {len(unmatched_lawn)} unmatched)"
    )
    print(f"appfilter.xml: {len(rows)} items")
    print(f"license review: {len(flagged)} icons flagged -> metadata/reports/license-review.json")


if __name__ == "__main__":
    main()
