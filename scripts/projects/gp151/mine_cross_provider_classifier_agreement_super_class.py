"""GP-151 super-class agreement test — re-aggregation of 3-provider data.

Reuses the fine-grained labels already produced by
`mine_cross_provider_classifier_agreement.py` (100 records × 3 providers,
gpt-4.1-mini / claude-haiku-4.5 / gemini-3.1-flash-lite, 2026-04-24 run).
Collapses each fine label to one of three super-classes using the same
mapping as `docs/concepts/anti_pattern_catalog.md`, then recomputes
pairwise Cohen's kappa and three-way agreement at the super-class level.

Zero new API calls. Purely offline aggregation.

Decision gate per GP-151 seam §5.4:
  ≥ 90%  three-way agreement → adopt Path A (super-class routing)
  70-90% three-way agreement → observability-only (keep Path C)
  < 70%  three-way agreement → abandon super-class; pure Path C

Output:
  analytics/queries/cross_provider_classifier_agreement_super_class_<DATE>.json

Usage:
  python scripts/mine_cross_provider_classifier_agreement_super_class.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FINE_INPUT = REPO / "analytics" / "queries" / "cross_provider_classifier_agreement_2026-04-24.json"
OUT_DIR = REPO / "analytics" / "queries"


# Super-class mapping — matches docs/concepts/anti_pattern_catalog.md
# Part 1 (structural blockers) vs Part 2 (ceiling breakers) vs residual.
#
# Reasoning for each bucket:
#   structural_blocker: classes with lift < 1 in ≥85-score iters (per GP-149
#     mining). Avoiding these is a PRECONDITION for high score. Includes the
#     runtime-meaningful fast-kill classes.
#   ceiling_breaker: classes that APPEAR MORE at ≥85 scores (lift > 1).
#     These are the "top-of-distribution residual critiques" the judge
#     finds at high scores.
#   other: residuals not clearly in either bucket OR the catch-all label.
#
# Load-bearing note: the mapping is derived from mining lifts, not from
# vibes. If a class's lift is disputed, its super-class may also be disputed.
# The experiment this script runs is: even WITH per-class lift dispute, do
# the SUPER-CLASS memberships stay stable across three LLMs?
SUPER_CLASS_MAP: dict[str, str] = {
    # --- structural blockers (lift < 1 in ≥85 iters; GP-149 PART 1) ---
    "unfalsifiable_claim": "structural_blocker",
    "catastrophic_fit_failure": "structural_blocker",
    "missing_baseline": "structural_blocker",
    "temporal_mismatch": "structural_blocker",
    "unmeasurable_construct": "structural_blocker",
    "definition_ambiguity": "structural_blocker",
    "non_identifiability": "structural_blocker",
    # --- ceiling breakers (lift > 1 at ≥85 iters; GP-149 PART 2) ---
    "overclaimed_scope": "ceiling_breaker",
    "overclaimed_exclusivity": "ceiling_breaker",
    "missing_mechanism": "ceiling_breaker",
    "missing_counterfactual": "ceiling_breaker",
    "parameter_sensitivity": "ceiling_breaker",
    "unsupported_assumption": "ceiling_breaker",
    "missing_derivation": "ceiling_breaker",
    # --- residual ---
    "other": "other",
}


def cohens_kappa(labels_a: list[str], labels_b: list[str]) -> float:
    if len(labels_a) != len(labels_b) or not labels_a:
        return 0.0
    n = len(labels_a)
    po = sum(1 for a, b in zip(labels_a, labels_b) if a == b) / n
    ca = Counter(labels_a)
    cb = Counter(labels_b)
    pe = sum((ca[x] / n) * (cb[x] / n) for x in set(ca) | set(cb))
    if pe >= 1.0:
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1 - pe)


def main() -> int:
    if not FINE_INPUT.is_file():
        print(f"ERROR: fine-grained input not found at {FINE_INPUT}", file=sys.stderr)
        return 1

    data = json.loads(FINE_INPUT.read_text())
    records = data.get("records", [])
    providers: list[str] = data.get("providers", [])
    if not records or not providers:
        print("ERROR: malformed input (no records or providers).", file=sys.stderr)
        return 1

    n = len(records)
    super_labels: dict[str, list[str]] = {p: [] for p in providers}
    per_record = []
    for r in records:
        fine = r.get("labels", {})
        super_for_record = {
            p: SUPER_CLASS_MAP.get(fine.get(p, "other"), "other")
            for p in providers
        }
        for p in providers:
            super_labels[p].append(super_for_record[p])
        per_record.append({
            "project": r.get("project"),
            "iter_timestamp": r.get("iter_timestamp"),
            "score": r.get("score"),
            "weakest_point_snippet": r.get("weakest_point_snippet"),
            "fine_labels": fine,
            "super_labels": super_for_record,
            "all_agree_super": len(set(super_for_record.values())) == 1,
        })

    three_way_agree = sum(1 for rec in per_record if rec["all_agree_super"])
    three_way_rate = three_way_agree / max(n, 1)

    pairwise_kappa = {}
    for i, p1 in enumerate(providers):
        for p2 in providers[i + 1:]:
            k = cohens_kappa(super_labels[p1], super_labels[p2])
            pairwise_kappa[f"{p1}__{p2}"] = round(k, 3)

    # Per-super-class stability
    per_super_class_stability = {}
    for sc in ("structural_blocker", "ceiling_breaker", "other"):
        in_any = [rec for rec in per_record if sc in rec["super_labels"].values()]
        if not in_any:
            continue
        all_3 = sum(1 for rec in in_any if all(v == sc for v in rec["super_labels"].values()))
        per_super_class_stability[sc] = {
            "n_at_least_one": len(in_any),
            "n_three_way_agreement": all_3,
            "stability_rate": round(all_3 / len(in_any), 3),
        }

    # Verdict per GP-151 seam §5.4
    if three_way_rate >= 0.90:
        verdict = "PATH_A_GREEN (>=0.90): adopt super-class routing"
    elif three_way_rate >= 0.70:
        verdict = "PATH_C_ONLY (0.70-0.90): keep observability; defer Path A"
    else:
        verdict = "PATH_C_PURE (<0.70): abandon super-class; regex-only observability"

    out = {
        "generated": str(date.today()),
        "source_fine_input": str(FINE_INPUT.relative_to(REPO)),
        "n_sampled": n,
        "providers": providers,
        "pairwise_kappa_super_class": pairwise_kappa,
        "three_way_agreement_count": three_way_agree,
        "three_way_agreement_rate": round(three_way_rate, 3),
        "per_super_class_stability": per_super_class_stability,
        "fine_grained_baseline_three_way_rate": data.get("three_way_agreement_rate"),
        "fine_grained_baseline_pairwise_kappa": data.get("pairwise_kappa"),
        "super_class_map": SUPER_CLASS_MAP,
        "verdict": verdict,
        "records": per_record,
    }

    out_path = OUT_DIR / f"cross_provider_classifier_agreement_super_class_{date.today()}.json"
    out_path.write_text(json.dumps(out, indent=2))

    print("=" * 70)
    print(f"GP-151 super-class agreement aggregation")
    print("=" * 70)
    print(f"Source: {FINE_INPUT.name}")
    print(f"N sampled: {n}")
    print(f"Providers: {providers}")
    print("")
    print(f"Fine-grained baseline 3-way agreement: {data.get('three_way_agreement_rate'):.1%}")
    print(f"Super-class 3-way agreement:           {three_way_rate:.1%}")
    print("")
    print("Super-class pairwise kappa:")
    for k, v in pairwise_kappa.items():
        print(f"  {k}: {v}")
    print("")
    print("Per-super-class stability:")
    for sc, stats in per_super_class_stability.items():
        print(f"  {sc:>22}: {stats['stability_rate']:.1%}  "
              f"({stats['n_three_way_agreement']}/{stats['n_at_least_one']})")
    print("")
    print(f"Verdict: {verdict}")
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
