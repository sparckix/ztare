#!/usr/bin/env python3
"""GP-135 — Unlock F6 holdout evidence AFTER a prediction has been sealed.

Refuses to unlock:
  - if no sealed prediction exists under research_areas/private/mlh_predictions/
  - without --confirm
  - if the manifest hash does not match the file in _holdout_locked/
    (tamper check)

Writes an unlock record at projects/mlh_f6/_unlock_record.json that
subsequent scoring scripts read to confirm the unlock was authorized.

Usage:
    python scripts/unlock_mlh_holdout.py --confirm
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
F6 = REPO / "projects" / "mlh_f6"
LOCKED = F6 / "_holdout_locked"
PRED_DIR = REPO / "research_areas" / "private" / "mlh_predictions"
MANIFEST = REPO / "research_areas" / "private" / "mlh_family_manifest.json"
UNLOCK_RECORD = F6 / "_unlock_record.json"


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirm", action="store_true", help="Required to perform the unlock.")
    args = ap.parse_args()

    if not args.confirm:
        print(
            "refuse to unlock: --confirm is required. This is a one-way "
            "operation; F6 evidence becomes visible to any subsequent live run.",
            file=sys.stderr,
        )
        sys.exit(2)

    if UNLOCK_RECORD.exists():
        print(f"already unlocked (see {UNLOCK_RECORD}).", file=sys.stderr)
        sys.exit(0)

    if not PRED_DIR.exists() or not any(PRED_DIR.glob("*_sealed.json")):
        print(
            "❌ refuse to unlock: no sealed prediction found under "
            f"{PRED_DIR}. Seal a prediction first via "
            "`python scripts/seal_mlh_prediction.py --prediction <path>`.",
            file=sys.stderr,
        )
        sys.exit(2)

    if not LOCKED.exists():
        print(f"❌ _holdout_locked not found: {LOCKED}", file=sys.stderr)
        sys.exit(2)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = manifest.get("sealed_holdout_hash", {})
    errs = []
    for name in ("evidence.txt", "evidence_holdout.txt"):
        src = LOCKED / name
        if not src.exists():
            errs.append(f"missing {src}")
            continue
        want = expected.get(name, {}).get("sha256", "")
        got = _sha256(src)
        if want != got:
            errs.append(f"hash mismatch on {name}: manifest={want} actual={got}")
    if errs:
        print("❌ refuse to unlock: tamper check failed", file=sys.stderr)
        for e in errs:
            print(f"    {e}", file=sys.stderr)
        sys.exit(2)

    # Find most recent sealed prediction
    sealed = sorted(PRED_DIR.glob("*_sealed.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    latest_sealed = sealed[0]

    # Move _holdout_locked/ contents back to live paths
    for name in ("evidence.txt", "evidence_holdout.txt"):
        src = LOCKED / name
        dst = F6 / name
        shutil.copy(src, dst)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    UNLOCK_RECORD.write_text(
        json.dumps({
            "unlocked_at": now,
            "sealed_prediction": str(latest_sealed.relative_to(REPO)),
            "unlocked_files": [
                {"name": "evidence.txt", "sha256": expected["evidence.txt"]["sha256"]},
                {"name": "evidence_holdout.txt", "sha256": expected["evidence_holdout.txt"]["sha256"]},
            ],
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"🔓 unlocked F6 evidence.")
    print(f"   sealed prediction: {latest_sealed.relative_to(REPO)}")
    print(f"   unlock record:     {UNLOCK_RECORD.relative_to(REPO)}")
    print(f"\nnext: `python scripts/score_mlh_prediction.py --prediction {latest_sealed.relative_to(REPO)}`")


if __name__ == "__main__":
    main()
