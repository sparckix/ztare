#!/usr/bin/env python3
"""test_archetype_classifier_accuracy.py — measure archetype_classifier.py
precision on the v3 ground-truth catalog (40 curated exemplars, 5 per
ARCH-001..008).

Each v3 row has a hand-labeled `archetype` field (ARCH-001..008). We feed the
row's `goal_before` + `local_context` through classify() and compare.

Output:
  * Top-1 accuracy (overall + per-archetype breakdown)
  * Confusion matrix
  * Honest verdict (does L4 prediction beat random 1/8 = 12.5%?)

This is a STRUCTURAL test of Mode D's foundation — if the classifier can't
recover the labels on its own training-style data, Mode D can't add signal
beyond bare tactic enumeration.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/public/control"))
from archetype_classifier import classify, classify_by_goal_shape, classify_by_goal_shape_topk, parse_lean_goal  # noqa

V3_CATALOG = ROOT / "analytics/public/leanmill/results/v30_layer4_v3_pattern_seed_catalog.json"


def main():
    catalog = json.loads(V3_CATALOG.read_text())
    rows = catalog["rows"]
    print(f"Loaded {len(rows)} ground-truth rows from v3 catalog\n")

    # Map ARCH-001 (no underscore) → ARCH-001_direct_library_chain (classifier output format)
    GROUND_TO_CLASSIFIER = {
        "ARCH-001": "ARCH-001_direct_library_chain",
        "ARCH-002": "ARCH-002_calc_inequality_chain",
        "ARCH-003": "ARCH-003_normalization_first",
        "ARCH-004": "ARCH-004_constructor_refine_decomposition",
        "ARCH-005": "ARCH-005_induction_recursion",
        "ARCH-006": "ARCH-006_monotonicity_gcongr_chain",
        "ARCH-007": "ARCH-007_duality_holder_cs_route",
        "ARCH-008": "ARCH-008_measure_measurability_automation",
    }

    correct = 0
    top3_correct = 0
    per_archetype = defaultdict(lambda: {"correct": 0, "top3_correct": 0, "total": 0})
    confusion = Counter()  # (true, predicted) -> count

    misclassified = []

    for row in rows:
        true_arch = row["archetype"]  # e.g. "ARCH-001"
        true_classifier_label = GROUND_TO_CLASSIFIER[true_arch]
        goal = row.get("goal_before", "")
        local_ctx = row.get("local_context", [])
        # If local_ctx is list of strings already, use it; else convert
        if isinstance(local_ctx, list):
            ctx_list = [str(c) for c in local_ctx]
        else:
            ctx_list = []

        pred = classify_by_goal_shape(goal, ctx_list)
        pred_arch = pred["predicted_L4_archetype"]
        topk = classify_by_goal_shape_topk(goal, ctx_list, k=3)
        topk_archs = [t["predicted_L4_archetype"] for t in topk]

        per_archetype[true_arch]["total"] += 1
        if pred_arch == true_classifier_label:
            correct += 1
            per_archetype[true_arch]["correct"] += 1
        else:
            misclassified.append({
                "name": row.get("name", "?"),
                "true": true_arch,
                "predicted": pred_arch,
                "topk": topk_archs,
                "in_topk": true_classifier_label in topk_archs,
                "goal_snippet": goal[:100],
            })
        if true_classifier_label in topk_archs:
            top3_correct += 1
            per_archetype[true_arch]["top3_correct"] += 1
        confusion[(true_arch, pred_arch)] += 1

    n = len(rows)
    acc = correct / n if n else 0
    top3_acc = top3_correct / n if n else 0
    random_baseline = 1 / 8
    random_top3 = 3 / 8

    print(f"## Overall accuracy")
    print(f"Top-1: {correct}/{n} = {100*acc:.1f}% (random {100*random_baseline:.1f}%)")
    print(f"Top-3: {top3_correct}/{n} = {100*top3_acc:.1f}% (random {100*random_top3:.1f}%)")
    print(f"Top-1 beats random: {'YES' if acc > random_baseline else 'NO'} (by {100*(acc-random_baseline):+.1f} pts)")
    print(f"Top-3 beats random: {'YES' if top3_acc > random_top3 else 'NO'} (by {100*(top3_acc-random_top3):+.1f} pts)\n")

    print(f"## Per-archetype accuracy (top-1 / top-3)")
    print(f"{'Archetype':<12} {'Top-1':<11} {'Top-3':<11} {'Top error':<60}")
    for arch in sorted(per_archetype.keys()):
        stats = per_archetype[arch]
        a = stats["correct"] / stats["total"] if stats["total"] else 0
        a3 = stats["top3_correct"] / stats["total"] if stats["total"] else 0
        errors = Counter()
        for (t, p), c in confusion.items():
            if t == arch and p != GROUND_TO_CLASSIFIER[arch]:
                errors[p] += c
        top_error = errors.most_common(1)[0] if errors else ("—", 0)
        print(f"{arch:<12} {stats['correct']}/{stats['total']} ({100*a:>3.0f}%)   "
              f"{stats['top3_correct']}/{stats['total']} ({100*a3:>3.0f}%)   "
              f"{'→ '+top_error[0]+' x'+str(top_error[1]) if top_error[0]!='—' else '(all correct)'}")
    print()

    if misclassified:
        print(f"## Sample misclassifications (first 8)")
        for m in misclassified[:8]:
            print(f"  {m['name'][:50]:<50} true={m['true']} pred={m['predicted']}")
            print(f"    goal: {m['goal_snippet'][:140]}")
        print()

    print(f"## Honest verdict")
    if acc < 0.30:
        print(f"**FAIL**: classifier accuracy {100*acc:.1f}% is in the 'no better than weak prior' range. Mode D will route to wrong tactic packs on the majority of rows. Either (a) rewrite classifier rules with v3 exemplars as training data, or (b) replace heuristic with a learned classifier (small LM, ~30M params, trained on the v3 + larger Mathlib corpus).")
    elif acc < 0.60:
        print(f"**MARGINAL**: classifier accuracy {100*acc:.1f}% beats random ({100*random_baseline:.1f}%) but not by enough to make Mode D >> Mode A. Refine rules or add 2-3 more discriminating features (e.g. specific Mathlib namespaces in local context, structural patterns).")
    elif acc < 0.80:
        print(f"**ACCEPTABLE**: classifier accuracy {100*acc:.1f}% is good enough that Mode D should beat Mode A on rows where archetype routing matters. Proceed to ablation.")
    else:
        print(f"**STRONG**: classifier accuracy {100*acc:.1f}% means Mode D's archetype routing is structurally sound. If ablation still doesn't show Mode D > Mode A, the bottleneck is the *tactic pack* per archetype, not the prediction.")


if __name__ == "__main__":
    sys.exit(main() or 0)
