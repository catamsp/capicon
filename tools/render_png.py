#!/usr/bin/env python3
"""render_png.py - render served SVGs to PNGs at fixed densities using resvg.

Sizes: 48, 96, 192, 432 px (transparent background, icons render black -
the consumer tints them, matching Lawnicons' monochrome usage).

resvg discovery order:
  1. RESVG_BIN environment variable
  2. tools/bin/resvg(.exe)
  3. resvg on PATH

A JSON hash-cache (tools/.render_cache.json) skips re-rendering when the SVG
bytes + size + resvg version are unchanged, so a weekly upstream sync only
renders new/changed icons.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "tools" / ".render_cache.json"
SIZES = (48, 96, 192, 432)
SOURCES = ("lawnicons", "simpleicons", "capicons")


def find_resvg() -> str:
    candidates = [
        None,  # placeholder for env override
        str(ROOT / "tools" / "bin" / ("resvg.exe" if sys.platform == "win32" else "resvg")),
    ]
    env = __import__("os").environ.get("RESVG_BIN")
    if env:
        candidates[0] = env
    for c in candidates:
        if c and Path(c).is_file():
            return c
    found = shutil.which("resvg")
    if found:
        return found
    print(
        "error: resvg not found. Install it:\n"
        "  - download from https://github.com/RazrFalcon/resvg/releases into tools/bin/\n"
        "  - or set RESVG_BIN=/path/to/resvg\n"
        "  - or put resvg on PATH",
        file=sys.stderr,
    )
    sys.exit(1)


def resvg_version(resvg: str) -> str:
    try:
        out = subprocess.check_output([resvg, "--version"], text=True).strip()
        return out.split()[-1]
    except Exception:
        return "unknown"


def render(resvg: str, svg: Path, png: Path, size: int) -> None:
    png.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        subprocess.run(
            [resvg, str(svg), str(tmp_path), "-w", str(size)],
            check=True,
            capture_output=True,
        )
        # Atomic-ish replace so a failed run never leaves a truncated PNG in place.
        shutil.move(str(tmp_path), str(png))
    finally:
        tmp_path.unlink(missing_ok=True)


def main() -> None:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    force = "--force" in sys.argv

    resvg = find_resvg()
    version = resvg_version(resvg)
    cache = {}
    if CACHE.is_file() and not force:
        cache = json.loads(CACHE.read_text(encoding="utf-8"))

    rendered = skipped = 0
    for source in SOURCES:
        if only and source != only:
            continue
        svg_dir = ROOT / "icons" / source / "svg"
        if not svg_dir.is_dir():
            print(f"skip {source}: no {svg_dir}")
            continue
        for svg in sorted(svg_dir.glob("*.svg")):
            digest = hashlib.sha256(svg.read_bytes()).hexdigest()
            for size in SIZES:
                ck = f"{source}/{svg.stem}/{size}"
                png = ROOT / "png" / source / str(size) / f"{svg.stem}.png"
                if (
                    not force
                    and cache.get(ck, {}).get("sha") == digest
                    and cache.get(ck, {}).get("resvg") == version
                    and png.is_file()
                ):
                    skipped += 1
                    continue
                render(resvg, svg, png, size)
                cache[ck] = {"sha": digest, "resvg": version}
                rendered += 1
        print(f"{source}: done")

    CACHE.write_text(json.dumps(cache, indent=0, sort_keys=True) + "\n", encoding="utf-8")
    print(f"rendered {rendered} pngs, skipped {skipped} cached (resvg {version})")


if __name__ == "__main__":
    main()
