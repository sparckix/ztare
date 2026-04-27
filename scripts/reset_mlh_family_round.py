#!/usr/bin/env python3
"""Invalidate and rewind a contaminated GP-135 MLH round."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PRED_DIR = REPO / "research_areas" / "private" / "mlh_predictions"
F6_DIR = REPO / "projects" / "mlh_f6"
LOCKED_DIR = F6_DIR / "_holdout_locked"
MANIFEST = REPO / "research_areas" / "private" / "mlh_family_manifest.json"
UNLOCK_RECORD = F6_DIR / "_unlock_record.json"


def _restore_placeholder(name: str, manifest_entry: dict) -> None:
    live_path = F6_DIR / name
    placeholder = (
        f"# SEALED HOLDOUT — {name}\n"
        "# This substrate is part of the MLH family program (GP-135).\n"
        "# Its evidence is sealed until the mutator has committed a\n"
        "# cross-substrate invariant prediction. Do not replace this\n"
        "# placeholder manually; use the MLH reset/export/seal flow.\n"
        f"# Sealed SHA-256: {manifest_entry['sha256']}\n"
        f"# n_points: {manifest_entry['n_points']}\n"
        f"# Raw evidence location: _holdout_locked/{name}\n"
    )
    live_path.write_text(placeholder, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true", help="Required to invalidate and rewind the round.")
    ap.add_argument(
        "--reason",
        default="protocol contamination: prediction authored from repo-visible holdout/GT surface",
        help="Reason recorded in the invalidation archive.",
    )
    args = ap.parse_args()

    if not args.confirm:
        print("refuse to reset: --confirm is required", file=sys.stderr)
        sys.exit(2)

    if not MANIFEST.exists():
        print(f"missing manifest: {MANIFEST}", file=sys.stderr)
        sys.exit(2)
    if not LOCKED_DIR.exists():
        print(f"missing locked holdout directory: {LOCKED_DIR}", file=sys.stderr)
        sys.exit(2)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    archive_dir = PRED_DIR / "invalidated" / now.replace(":", "-")
    archive_dir.mkdir(parents=True, exist_ok=True)

    for pred_path in sorted(PRED_DIR.glob("*.json")):
        shutil.move(str(pred_path), str(archive_dir / pred_path.name))

    if UNLOCK_RECORD.exists():
        shutil.move(str(UNLOCK_RECORD), str(archive_dir / "mlh_f6_unlock_record.json"))

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = manifest.get("sealed_holdout_hash", {})
    for name in ("evidence.txt", "evidence_holdout.txt"):
        if name not in expected:
            print(f"manifest missing {name}", file=sys.stderr)
            sys.exit(2)
        _restore_placeholder(name, expected[name])

    invalidation_note = {
        "invalidated_at": now,
        "reason": args.reason,
        "archived_predictions": sorted(p.name for p in archive_dir.glob("*.json")),
        "restored_files": ["projects/mlh_f6/evidence.txt", "projects/mlh_f6/evidence_holdout.txt"],
    }
    (archive_dir / "INVALIDATION_NOTE.json").write_text(
        json.dumps(invalidation_note, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"✅ invalidated contaminated MLH round → {archive_dir.relative_to(REPO)}")
    print("   F6 live evidence restored to sealed placeholders")
    print("   next: rerun F1..F5, export a sanitized packet, author a new prediction outside the repo, then seal")


if __name__ == "__main__":
    main()
