#!/usr/bin/env python3
"""GP-135 — Seal a cross-substrate prediction before F6 unlock.

Input: a prediction JSON authored by the operator after running F1..F5.
Output: a sealed copy of the prediction under
`research_areas/private/mlh_predictions/` with a self-hash + timestamp
that cannot be edited without detection.

Required prediction fields (validated here; see
docs/concepts/mlh_family_protocol.md for semantics):
  training_substrates (list[str])
  holdout_substrate (str == "mlh_f6")
  invariant_statement (str, non-empty)
  composition_class_prediction (one of: additive, multiplicative, neither)
  composition_rule (str, non-empty)
  prime_power_rule (str, non-empty)
  predicted_holdout_values (dict[int, int], min 20 entries)
  predicted_at_n1 (int)
  confidence (float in [0, 1])
  derivation_source (one of: engine, operator, joint)
  source_packet_hash (str; must match a registered sanitized prediction packet)

This script refuses to seal:
  - if F6 holdout is already unlocked (an unlock record exists)
  - if the prediction JSON fails schema validation
  - if `seal_hash` is already present (prevents double-seal + edit)
  - if the training substrates do not yet have real run outputs
  - if the prediction is not tied to a registered sanitized packet

Usage:
    python scripts/seal_mlh_prediction.py --prediction path/to/pred.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PRED_DIR = REPO / "research_areas" / "private" / "mlh_predictions"
PACKET_DIR = REPO / "research_areas" / "private" / "mlh_prediction_packets"
UNLOCK_RECORD = REPO / "projects" / "mlh_f6" / "_unlock_record.json"

REQUIRED_FIELDS = {
    "training_substrates": list,
    "holdout_substrate": str,
    "invariant_statement": str,
    "composition_class_prediction": str,
    "composition_rule": str,
    "prime_power_rule": str,
    "predicted_holdout_values": dict,
    "predicted_at_n1": int,
    "confidence": float,
    "derivation_source": str,
    "source_packet_hash": str,
}
ALLOWED_CLASSES = {"additive", "multiplicative", "neither"}
ALLOWED_SOURCES = {"engine", "operator", "joint"}


def _validate(pred: dict) -> list[str]:
    errs = []
    for k, t in REQUIRED_FIELDS.items():
        if k not in pred:
            errs.append(f"missing field: {k}")
            continue
        v = pred[k]
        if t is float:
            if not isinstance(v, (int, float)):
                errs.append(f"{k}: expected number, got {type(v).__name__}")
        elif t is int:
            if not isinstance(v, int) or isinstance(v, bool):
                errs.append(f"{k}: expected int, got {type(v).__name__}")
        elif not isinstance(v, t):
            errs.append(f"{k}: expected {t.__name__}, got {type(v).__name__}")

    if pred.get("holdout_substrate") != "mlh_f6":
        errs.append("holdout_substrate must be 'mlh_f6'")
    if pred.get("composition_class_prediction") not in ALLOWED_CLASSES:
        errs.append(f"composition_class_prediction must be one of {ALLOWED_CLASSES}")
    if pred.get("derivation_source") not in ALLOWED_SOURCES:
        errs.append(f"derivation_source must be one of {ALLOWED_SOURCES}")
    conf = pred.get("confidence")
    if isinstance(conf, (int, float)) and not (0.0 <= float(conf) <= 1.0):
        errs.append("confidence must be in [0.0, 1.0]")
    vals = pred.get("predicted_holdout_values")
    if isinstance(vals, dict) and len(vals) < 20:
        errs.append(f"predicted_holdout_values must have >= 20 entries (have {len(vals)})")
    if "seal_hash" in pred:
        errs.append("prediction JSON already contains seal_hash; refuse to re-seal")

    errs.extend(_validate_training_outputs(pred.get("training_substrates")))
    errs.extend(_validate_source_packet(pred.get("source_packet_hash")))
    return errs


def _validate_training_outputs(training_substrates: object) -> list[str]:
    errs = []
    if not isinstance(training_substrates, list) or not training_substrates:
        return ["training_substrates must be a non-empty list"]

    for slug in training_substrates:
        project_dir = REPO / "projects" / str(slug)
        champion = project_dir / "champion_eval_results.json"
        latest = project_dir / "latest_eval_results.json"
        if not champion.exists() and not latest.exists():
            errs.append(
                f"training substrate {slug!r} has no eval output; run it before sealing"
            )
    return errs


def _validate_source_packet(packet_hash: object) -> list[str]:
    if not isinstance(packet_hash, str) or not packet_hash.strip():
        return ["source_packet_hash must be a non-empty string"]
    if not PACKET_DIR.exists():
        return [f"no registered prediction packets found under {PACKET_DIR}"]

    for manifest_path in PACKET_DIR.glob("*_packet_manifest.json"):
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if manifest.get("packet_hash") == packet_hash:
            return []

    return [f"source_packet_hash {packet_hash!r} does not match a registered packet"]


def _canonical_bytes(pred: dict) -> bytes:
    pred_no_seal = {k: v for k, v in pred.items() if k != "seal_hash"}
    return json.dumps(pred_no_seal, indent=2, sort_keys=True).encode("utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prediction", required=True)
    ap.add_argument("--tag", default=None, help="short tag for the filename; default from timestamp")
    args = ap.parse_args()

    if UNLOCK_RECORD.exists():
        print(
            f"❌ refuse to seal: F6 already unlocked (see {UNLOCK_RECORD}). "
            f"Start a new prediction only after authoring a fresh sealed family.",
            file=sys.stderr,
        )
        sys.exit(2)

    pred_path = Path(args.prediction).resolve()
    if not pred_path.exists():
        print(f"❌ prediction file not found: {pred_path}", file=sys.stderr)
        sys.exit(2)

    try:
        pred = json.loads(pred_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"❌ prediction JSON parse error: {exc}", file=sys.stderr)
        sys.exit(2)

    errs = _validate(pred)
    if errs:
        print("❌ prediction schema errors:", file=sys.stderr)
        for e in errs:
            print(f"    {e}", file=sys.stderr)
        sys.exit(2)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    pred["date_sealed"] = now
    seal_hash = hashlib.sha256(_canonical_bytes(pred)).hexdigest()
    pred["seal_hash"] = seal_hash

    PRED_DIR.mkdir(parents=True, exist_ok=True)
    tag = args.tag or now.replace(":", "-")
    out = PRED_DIR / f"{tag}_sealed.json"
    out.write_text(json.dumps(pred, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"✅ sealed prediction → {out}")
    print(f"   self-hash: {seal_hash}")
    print(f"   sealed_at: {now}")
    print(f"\nnext: `python scripts/unlock_mlh_holdout.py --confirm` then `python scripts/score_mlh_prediction.py --prediction {out}`")


if __name__ == "__main__":
    main()
