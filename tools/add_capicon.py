#!/usr/bin/env python3
"""add_capicon.py - add one of your custom icons to the pack.

Usage:
  python tools/add_capicon.py path/to/icon.svg --name "My App" \
      --component com.myapp/com.myapp.MainActivity --color 1DB954

It copies the SVG into icons/capicons/svg/<key>.svg (key = slugified name unless
--key is given), appends an entry to metadata/capicons.json, then runs the
mapping + render + validate steps for you.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAP_DIR = ROOT / "icons" / "capicons" / "svg"
CAP_JSON = ROOT / "metadata" / "capicons.json"


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s or "icon"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("svg", type=Path, help="source SVG file")
    ap.add_argument("--name", required=True, help="display name of the app/icon")
    ap.add_argument("--key", help="mapping key (default: slugified --name)")
    ap.add_argument("--component", action="append", default=[],
                    help="Android component 'pkg/activity' (repeatable)")
    ap.add_argument("--package", action="append", default=[],
                    help="Android package name (repeatable; derived from components if omitted)")
    ap.add_argument("--color", help="brand hex color without #")
    ap.add_argument("--license", help="SPDX license id or custom URL for your own icon")
    args = ap.parse_args()

    if not args.svg.is_file():
        sys.exit(f"error: {args.svg} not found")

    key = args.key or slugify(args.name)
    if not re.fullmatch(r"[a-z0-9_]+", key):
        sys.exit(f"error: key '{key}' must be [a-z0-9_]")

    CAP_DIR.mkdir(parents=True, exist_ok=True)
    dest = CAP_DIR / f"{key}.svg"
    shutil.copy2(args.svg, dest)

    data = json.loads(CAP_JSON.read_text(encoding="utf-8")) if CAP_JSON.is_file() else {"icons": []}
    data["icons"] = [i for i in data["icons"] if Path(i["svg"]).stem != key]
    entry = {"name": args.name, "svg": f"icons/capicons/svg/{key}.svg"}
    if args.component:
        entry["components"] = args.component
    packages = args.package or sorted({c.split("/")[0] for c in args.component if "/" in c})
    if packages:
        entry["packages"] = packages
    if args.color:
        entry["color"] = args.color.lstrip("#")
    if args.license:
        entry["license"] = args.license
    data["icons"].append(entry)
    data["icons"].sort(key=lambda i: Path(i["svg"]).stem)
    CAP_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"added {dest.relative_to(ROOT)} and metadata/capicons.json entry (key={key})")
    for step in (["build_mapping.py"], ["render_png.py", "capicons"], ["validate.py"]):
        print(f"\n> python tools/{' '.join(step)}")
        subprocess.run([sys.executable, str(ROOT / "tools" / step[0]), *step[1:]], cwd=ROOT, check=False)


if __name__ == "__main__":
    main()
