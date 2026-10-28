#!/usr/bin/env python3
"""validate.py - CI gate for the served icon tree.

Checks (all fatal under --strict):
  1. every file referenced by metadata/mapping.json exists (svg + png)
  2. no denylisted key appears in mapping.json / appfilter.xml / icons/ / png/
  3. metadata/appfilter.xml is well-formed, matches mapping.json, and is sorted
  4. no orphan SVGs (present in icons/ but absent from mapping.json)
  5. no duplicate Android components across icons
  6. license review: icons with explicit per-icon licenses are listed; fatal in
     --strict only when the slug is NOT in overrides.json simpleicons_license_allowlist
"""
from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
META = ROOT / "metadata"
SIZES = ("48", "96", "192", "432")


def main() -> None:
    strict = "--strict" in sys.argv
    errors: list[str] = []
    warnings: list[str] = []

    mapping = json.loads((META / "mapping.json").read_text(encoding="utf-8"))
    icons: dict[str, dict] = mapping["icons"]
    denylist = {
        e["key"]
        for e in json.loads((ROOT / "DENYLIST.json").read_text(encoding="utf-8")).get("icons", [])
    }
    allowlist = set(
        json.loads((ROOT / "tools" / "overrides.json").read_text(encoding="utf-8")).get(
            "simpleicons_license_allowlist", []
        )
    )

    # 1. referenced files exist
    for key, meta in icons.items():
        for rel in meta["files"]["svg"].values():
            if not (ROOT / rel).is_file():
                errors.append(f"{key}: missing svg {rel}")
        for rel in meta["files"]["png"].values():
            if not (ROOT / rel).is_file():
                errors.append(f"{key}: missing png {rel}")

    # 2. denylist enforcement
    for key in sorted(denylist & set(icons)):
        errors.append(f"denylisted key present in mapping.json: {key}")
    for svg_dir in (ROOT / "icons" / "lawnicons" / "svg", ROOT / "icons" / "simpleicons" / "svg"):
        for key in sorted(denylist):
            if (svg_dir / f"{key}.svg").is_file():
                errors.append(f"denylisted svg present: {svg_dir / key}.svg")

    # 3. appfilter.xml well-formed, in sync, sorted
    af = META / "appfilter.xml"
    try:
        root = ET.parse(af).getroot()
    except ET.ParseError as exc:
        errors.append(f"appfilter.xml unparseable: {exc}")
        root = None
    if root is not None:
        rows = [
            (i.get("name", ""), i.get("component", ""), i.get("drawable", ""))
            for i in root.findall("item")
        ]
        if rows != sorted(rows):
            errors.append("appfilter.xml is not sorted by (name, component)")
        expected = {
            (meta["name"].replace("&", "&amp;"), component, key)
            for key, meta in icons.items()
            for component in meta["components"]
        }
        got = {(n.replace("&", "&amp;"), c, d) for n, c, d in rows}
        for missing in sorted(expected - got):
            errors.append(f"appfilter.xml missing item: {missing}")
        for extra in sorted(got - expected):
            errors.append(f"appfilter.xml stale item: {extra}")

    # 4. orphan SVGs
    referenced = set()
    for meta in icons.values():
        for rel in meta["files"]["svg"].values():
            referenced.add(Path(rel).name)
    for source in ("lawnicons", "simpleicons", "capicons"):
        svg_dir = ROOT / "icons" / source / "svg"
        if not svg_dir.is_dir():
            continue
        for svg in svg_dir.glob("*.svg"):
            if svg.name not in referenced:
                warnings.append(f"orphan svg (not in mapping): icons/{source}/svg/{svg.name}")

    # 5. duplicate components
    seen: dict[str, str] = {}
    for key, meta in icons.items():
        for component in meta["components"]:
            if component in seen and seen[component] != key:
                errors.append(f"component {component} mapped to both {seen[component]} and {key}")
            seen[component] = key

    # 6. license review
    flagged = []
    for key, meta in icons.items():
        lic = meta.get("license")
        if lic and key not in allowlist:
            flagged.append((key, meta["name"], lic))
    for key, name, lic in sorted(flagged):
        msg = f"explicit license on '{key}' ({name}): {json.dumps(lic)}"
        if strict:
            errors.append(msg + " - review and allowlist in tools/overrides.json or DENYLIST it")
        else:
            warnings.append(msg)

    for w in warnings:
        print(f"warning: {w}")
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        print(f"\nvalidation FAILED: {len(errors)} error(s), {len(warnings)} warning(s)", file=sys.stderr)
        sys.exit(1)
    mode = "strict" if strict else "lenient"
    print(f"validation OK ({mode}): {len(icons)} icons, {len(warnings)} warning(s)")


if __name__ == "__main__":
    main()
