#!/usr/bin/env python3
"""sync_upstream.py - copy vendored upstream assets into the CDN-ready tree.

Reads third_party/ (populated by `git subtree add/pull`) and produces:
  icons/lawnicons/svg/*.svg        from third_party/lawnicons/svgs/
  icons/simpleicons/svg/*.svg      from third_party/simple-icons/icons/
  metadata/simple-icons.json       from third_party/simple-icons data file (vendor copy)

Also refreshes upstreams.lock.json with the currently vendored commit SHAs
(recovered from git history of the subtree prefixes). Denylisted icons are
deleted from the served trees.

Run from anywhere; all paths are resolved relative to the repo root.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "upstreams.lock.json"
DENYLIST = ROOT / "DENYLIST.json"

LAWN_SVG_SRC = ROOT / "third_party" / "lawnicons" / "svgs"
SI_SVG_SRC = ROOT / "third_party" / "simple-icons" / "icons"
# Data file location has moved over the project's life; check known locations.
SI_DATA_CANDIDATES = [
    ROOT / "third_party" / "simple-icons" / "data" / "simple-icons.json",
    ROOT / "third_party" / "simple-icons" / "_data" / "simple-icons" / "simple-icons.json",
]


def die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def git_last_sha(prefix: str) -> str:
    """Last commit touching the subtree prefix == upstream tip for full-history subtrees."""
    out = subprocess.check_output(
        ["git", "log", "-1", "--format=%H", "--", prefix], cwd=ROOT, text=True
    ).strip()
    return out or "unknown"


def copy_svgs(src: Path, dst: Path) -> int:
    if not src.is_dir():
        die(f"missing vendored source {src} - run `git subtree add` first (see README)")
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    n = 0
    for svg in sorted(src.glob("*.svg")):
        shutil.copy2(svg, dst / svg.name)
        n += 1
    return n


def load_keys(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return {entry["key"] for entry in data.get("icons", []) if "key" in entry}


def main() -> None:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    denied = load_keys(DENYLIST)

    # --- Lawnicons ---
    n_lawn = copy_svgs(LAWN_SVG_SRC, ROOT / "icons" / "lawnicons" / "svg")
    lock["lawnicons"]["commit"] = git_last_sha("third_party/lawnicons")

    # --- Simple Icons ---
    n_si = copy_svgs(SI_SVG_SRC, ROOT / "icons" / "simpleicons" / "svg")
    lock["simple-icons"]["commit"] = git_last_sha("third_party/simple-icons")

    si_data = next((p for p in SI_DATA_CANDIDATES if p.is_file()), None)
    if si_data is None:
        die(f"simple-icons data file not found; looked at: {SI_DATA_CANDIDATES}")
    meta_dir = ROOT / "metadata"
    meta_dir.mkdir(exist_ok=True)
    (meta_dir / "simple-icons.json").write_bytes(si_data.read_bytes())

    # --- Denylist enforcement: purge denied keys from served trees ---
    purged = []
    for svg_dir in (ROOT / "icons" / "lawnicons" / "svg", ROOT / "icons" / "simpleicons" / "svg"):
        for key in denied:
            f = svg_dir / f"{key}.svg"
            if f.is_file():
                f.unlink()
                purged.append(f"{svg_dir.parent.parent.name}/{key}.svg")
    for png_root in (ROOT / "png" / "lawnicons", ROOT / "png" / "simpleicons"):
        if not png_root.is_dir():
            continue
        for size_dir in png_root.iterdir():
            for key in denied:
                f = size_dir / f"{key}.png"
                if f.is_file():
                    f.unlink()
                    purged.append(f"{png_root.name}/{size_dir.name}/{key}.png")

    LOCK.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    print(f"lawnicons:  {n_lawn} svgs -> icons/lawnicons/svg (commit {lock['lawnicons']['commit'][:12]})")
    print(f"simple-icons: {n_si} svgs -> icons/simpleicons/svg (commit {lock['simple-icons']['commit'][:12]})")
    print(f"simple-icons metadata -> metadata/simple-icons.json")
    if purged:
        print(f"denylist: purged {len(purged)} files: {', '.join(purged)}")


if __name__ == "__main__":
    main()
