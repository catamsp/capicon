#!/usr/bin/env python3
"""triage_licenses.py - apply the commercial-serving license policy automatically.

Policy (agreed with the project owner, see IMPORTANT.md):
  DENYLIST (never serve):
    - non-commercial licenses (CC-BY-NC*)
    - no-derivatives licenses (CC-BY-ND*) - we rasterize SVG->PNG, too gray
    - "custom"/unknown terms - cannot verify commercial redistribution
  ALLOWLIST (reviewed & approved for commercial serving):
    - permissive: Apache-2.0, MIT, CC0, BSD, Unlicense, MPL
    - attribution: CC-BY*
    - share-alike: CC-BY-SA* (served unmodified)
    - copyleft: GPL*/AGPL* (icons are unmodified data files; SVG = source,
      served alongside THIRD_PARTY_NOTICES.md)

What it does:
  * reads metadata/reports/license-review.json (written by build_mapping.py)
  * for each offending icon: adds its mapping key AND its simple-icons slug
    (when different) to DENYLIST.json, unlinks every svg/png it owns
  * for each approved icon: adds key + slug to tools/overrides.json
    simpleicons_license_allowlist so validate.py --strict passes
  * idempotent - run again after each upstream sync to catch new offenders

Pipeline order:
  sync_upstream -> build_mapping -> triage_licenses -> build_mapping
  -> validate --strict -> render_png -> build_site
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "metadata" / "reports" / "license-review.json"
MAPPING = ROOT / "metadata" / "mapping.json"
DENYLIST = ROOT / "DENYLIST.json"
OVERRIDES = ROOT / "tools" / "overrides.json"


def delete_reason(license_type: str) -> str | None:
    """Return why the license is too risky for commercial serving, or None."""
    t = (license_type or "").strip()
    up = t.upper()
    if "NC" in up:
        return "non-commercial license"
    if "ND" in up:
        return "no-derivatives license (we rasterize SVG to PNG)"
    if t.lower() == "custom":
        return "custom/unknown terms - commercial redistribution not verified"
    return None


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    if not REPORT.is_file():
        print("error: run tools/build_mapping.py first (no license report)", file=sys.stderr)
        return 1

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    icons = json.loads(MAPPING.read_text(encoding="utf-8"))["icons"]
    deny = json.loads(DENYLIST.read_text(encoding="utf-8"))
    ovr = json.loads(OVERRIDES.read_text(encoding="utf-8"))

    deny_keys = {e["key"] for e in deny.get("icons", []) if isinstance(e, dict) and "key" in e}
    allow = set(ovr.get("simpleicons_license_allowlist", []))

    deleted: list[tuple[str, str, str]] = []  # (key, license, reason)
    kept_names: set[str] = set()
    purged_files = 0
    deny_new: list[dict] = []

    for entry in report.get("icons", []):
        key = entry["key"]
        lic = (entry.get("license") or {}).get("type", "")
        meta = icons.get(key, {})
        names = {key}
        slug = meta.get("simpleicons_slug")
        if slug:
            names.add(slug)

        reason = delete_reason(lic)
        if reason:
            # unlink every file this icon currently owns (both sources, all sizes)
            files = meta.get("files", {})
            for rel in list(files.get("svg", {}).values()) + list(files.get("png", {}).values()):
                path = ROOT / rel
                if path.is_file():
                    path.unlink()
                    purged_files += 1
            for name in sorted(names):
                if name not in deny_keys:
                    deny_new.append({"key": name, "license": lic, "reason": reason})
                    deny_keys.add(name)
            allow -= names  # never allowlist a denylisted icon
            deleted.append((key, lic, reason))
        else:
            kept_names |= names

    # --- write DENYLIST ---
    if deny_new:
        deny["icons"] = deny.get("icons", []) + deny_new
        DENYLIST.write_text(json.dumps(deny, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # --- write allowlist ---
    new_allow = sorted(allow | kept_names)
    if new_allow != ovr.get("simpleicons_license_allowlist", []):
        ovr["simpleicons_license_allowlist"] = new_allow
        OVERRIDES.write_text(json.dumps(ovr, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # --- summary ---
    reasons = Counter(r for _, _, r in deleted)
    print(f"license triage: {len(deleted)} icons blocked, {len(kept_names)} approved")
    for reason, n in reasons.most_common():
        print(f"  block {n:3}: {reason}")
    if purged_files:
        print(f"  purged {purged_files} files from icons/ and png/")
    if deleted:
        print("  blocked keys:", ", ".join(sorted(k for k, _, _ in deleted)))
    if new_allow:
        print(f"  allowlist grew to {len(new_allow)} entries (keys + slugs)")
    print("next: python tools/build_mapping.py && python tools/validate.py --strict")
    return 0


if __name__ == "__main__":
    sys.exit(main())
