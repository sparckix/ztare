#!/usr/bin/env python3
"""GP-135 — Score a sealed cross-substrate prediction against F6 ground truth.

Requires F6 to be unlocked (`_unlock_record.json` present). Reads F6 GT
values from the Division A module and scores the sealed prediction on
three axes per docs/concepts/mlh_family_protocol.md:

  1. composition-class accuracy (binary)
  2. point-prediction accuracy (fraction of predicted_holdout_values matching)
  3. rule-validity (AST-bounded parsimony check on prime_power_rule + composition_rule)

Newton-gate pass:
  composition-class accuracy = 1.0
  point-prediction accuracy >= 0.9
  rule-validity >= 0.8

Output: a scorecard JSON under research_areas/private/mlh_predictions/
and human-readable verdict to stdout.

Usage:
    python scripts/score_mlh_prediction.py --prediction path/to/sealed.json
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
F6 = REPO / "projects" / "mlh_f6"
UNLOCK_RECORD = F6 / "_unlock_record.json"
PRED_DIR = REPO / "research_areas" / "private" / "mlh_predictions"

NEWTON_GATE = {
    "composition_class_accuracy": 1.0,
    "point_prediction_accuracy": 0.9,
    "rule_validity": 0.8,
}

# Rule-validity: simple AST-complexity bound; lookup-table-style predictions
# have very high node count per unit predictive power. A rule whose AST has
# > MAX_AST_NODES is considered a lookup.
MAX_AST_NODES = 100


def _load_f6_gt():
    mod = importlib.import_module("src.ztare.substrates.mlh_f6_gt")
    return mod.f_true


def _infer_class_from_gt(f_true) -> str:
    """Compute the actual composition class of F6 from its GT values.

    Tests f(a*b) against f(a)+f(b), f(a)*f(b), max(f(a),f(b)) on coprime
    pairs. If one closed relation holds across all test pairs, that is
    the class.
    """
    import math as _m
    pairs = [
        (2, 3), (2, 5), (3, 5), (2, 7), (3, 7), (5, 7),
        (2, 9), (3, 4), (2, 11), (3, 11), (5, 9), (4, 5),
    ]
    coprime = [(a, b) for a, b in pairs if _m.gcd(a, b) == 1]
    add_ok = all(f_true(a * b) == f_true(a) + f_true(b) for a, b in coprime)
    mul_ok = all(f_true(a * b) == f_true(a) * f_true(b) for a, b in coprime)
    if add_ok:
        return "additive"
    if mul_ok:
        return "multiplicative"
    return "neither"


def _point_accuracy(pred_vals: dict, f_true) -> tuple[float, int, int]:
    if not pred_vals:
        return 0.0, 0, 0
    correct = 0
    for k_str, v in pred_vals.items():
        try:
            n = int(k_str)
            expected = int(f_true(n))
            if int(v) == expected:
                correct += 1
        except Exception:
            pass
    total = len(pred_vals)
    return (correct / total if total else 0.0), correct, total


def _rule_validity(rule_text: str) -> tuple[float, str]:
    """Heuristic parsimony check on a rule string."""
    if not rule_text or not rule_text.strip():
        return 0.0, "empty rule"
    try:
        tree = ast.parse(rule_text.strip(), mode="exec")
    except SyntaxError:
        # Not Python — don't penalize; text description of a rule can still
        # be valid.
        text_len = len(rule_text.strip())
        if text_len > 800:
            return 0.3, f"non-python rule, {text_len} chars (prolix)"
        return 0.7, f"non-python rule, {text_len} chars (concise)"
    n_nodes = sum(1 for _ in ast.walk(tree))
    if n_nodes > MAX_AST_NODES:
        return 0.0, f"rule AST has {n_nodes} nodes > {MAX_AST_NODES} (lookup-shaped)"
    if n_nodes > 50:
        return 0.5, f"rule AST has {n_nodes} nodes (complex but bounded)"
    return 1.0, f"rule AST has {n_nodes} nodes (parsimonious)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prediction", required=True)
    args = ap.parse_args()

    if not UNLOCK_RECORD.exists():
        print(f"❌ F6 not unlocked. Run `python scripts/unlock_mlh_holdout.py --confirm` first.", file=sys.stderr)
        sys.exit(2)

    pred_path = Path(args.prediction).resolve()
    if not pred_path.exists():
        print(f"❌ prediction not found: {pred_path}", file=sys.stderr)
        sys.exit(2)

    pred = json.loads(pred_path.read_text(encoding="utf-8"))
    seal_hash_claimed = pred.get("seal_hash", "")
    # Verify seal integrity — recompute hash on the payload minus seal_hash
    pred_no_seal = {k: v for k, v in pred.items() if k != "seal_hash"}
    recomputed = hashlib.sha256(
        json.dumps(pred_no_seal, indent=2, sort_keys=True).encode("utf-8")
    ).hexdigest()
    seal_ok = (recomputed == seal_hash_claimed)

    f_true = _load_f6_gt()
    actual_class = _infer_class_from_gt(f_true)
    predicted_class = pred.get("composition_class_prediction", "")
    class_accuracy = 1.0 if predicted_class == actual_class else 0.0

    point_acc, correct_pts, total_pts = _point_accuracy(
        pred.get("predicted_holdout_values", {}), f_true
    )

    pp_rule = pred.get("prime_power_rule", "")
    comp_rule = pred.get("composition_rule", "")
    pp_score, pp_reason = _rule_validity(pp_rule)
    comp_score, comp_reason = _rule_validity(comp_rule)
    rule_validity = (pp_score + comp_score) / 2.0

    predicted_n1 = pred.get("predicted_at_n1", None)
    actual_n1 = int(f_true(1))
    n1_ok = (predicted_n1 == actual_n1)

    newton_pass = (
        class_accuracy >= NEWTON_GATE["composition_class_accuracy"]
        and point_acc >= NEWTON_GATE["point_prediction_accuracy"]
        and rule_validity >= NEWTON_GATE["rule_validity"]
    )

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    scorecard = {
        "scored_at": now,
        "prediction_file": str(pred_path.relative_to(REPO)),
        "seal_ok": seal_ok,
        "composition_class": {
            "predicted": predicted_class,
            "actual": actual_class,
            "accuracy": class_accuracy,
        },
        "point_predictions": {
            "correct": correct_pts,
            "total": total_pts,
            "accuracy": round(point_acc, 4),
        },
        "rule_validity": {
            "prime_power_rule_score": pp_score,
            "prime_power_rule_reason": pp_reason,
            "composition_rule_score": comp_score,
            "composition_rule_reason": comp_reason,
            "combined": round(rule_validity, 4),
        },
        "at_n1": {
            "predicted": predicted_n1,
            "actual": actual_n1,
            "match": n1_ok,
        },
        "newton_gate": {
            "thresholds": NEWTON_GATE,
            "pass": newton_pass,
        },
    }

    out_path = PRED_DIR / f"{pred_path.stem}_scorecard.json"
    out_path.write_text(json.dumps(scorecard, indent=2) + "\n", encoding="utf-8")

    print("=" * 60)
    print("GP-135 MLH family prediction — scorecard")
    print("=" * 60)
    print(f"seal integrity      : {'OK' if seal_ok else 'TAMPERED'}")
    print(f"composition class   : predicted={predicted_class!r}  actual={actual_class!r}  {'✅' if class_accuracy else '❌'}")
    print(f"point predictions   : {correct_pts}/{total_pts} ({point_acc*100:.1f}%)")
    print(f"rule validity       : prime-power={pp_score:.2f} ({pp_reason})")
    print(f"                    : composition={comp_score:.2f} ({comp_reason})")
    print(f"                    : combined={rule_validity:.2f}")
    print(f"f(1)                : predicted={predicted_n1}  actual={actual_n1}  {'✅' if n1_ok else '❌'}")
    print(f"newton gate         : {'✅ PASS' if newton_pass else '❌ FAIL (informative null)'}")
    print(f"scorecard written   : {out_path.relative_to(REPO)}")
    sys.exit(0 if newton_pass else 1)


if __name__ == "__main__":
    main()
