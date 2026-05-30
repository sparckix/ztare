#!/usr/bin/env python3
"""Lollapalooza hypothesis test (Popper P1) -- GP-148 Stage 2, Ticket C.

PURPOSE
Tests the pre-registered Lollapalooza hypothesis from GP-148 seam §3.3 and §9
P1: iterations scoring >= 90 have structurally different thesis-term
distributions from iterations at 70-89 (multi-constraint coverage). If high-
scoring theses consistently engage MORE orthogonal constraints/primitives/
dimensions simultaneously, this supports the Mungerian Lollapalooza thesis
that breakthroughs require multi-factor convergence, not single-variable
improvements.

METHODOLOGY
Three structural features are extracted from each record in the high (>=90)
and mid (70-89) score buckets:

    (a) primitive_count: number of distinct thesis primitives named. Primary
        source: thesis_primitive_names field (populated only for the
        best-iteration per project). Fallback: regex count of primitive-like
        terms in weakest_point + rationale text.

    (b) dimension_term_count: count of rubric-dimension-related terms appearing
        in the weakest_point and rationale fields. Uses a fixed vocabulary
        derived from common ZTARE rubric dimension names.

    (c) active_constraint_count: length of the active_constraints list for that
        record.

For each feature, a two-sample Kolmogorov-Smirnov test (scipy.stats.ks_2samp)
compares the distributions between the two buckets.

Falsifier (from seam §9 P1): if KS p > 0.05 for EVERY feature, the
Lollapalooza hypothesis is REFUTED. If ANY feature shows p <= 0.05, the
hypothesis is SUPPORTED (with the specific distinguishing feature identified).

KNOWN LIMITATIONS
1. thesis_primitive_names is only populated for the best iteration per project,
   not historically. Most records have an empty list, so primitive_count is
   dominated by the fallback regex extraction, which is noisy.
2. active_constraints reflects the CURRENT state of each project's rubric and
   charter, not the state at iteration time. This is an approximation flagged
   by the enrichment script (active_constraints_source: "current").
3. The mid bucket (70-89) has ~3x the sample size of the high bucket (>=90),
   which is adequate for KS but means the test has more power to detect
   differences in the mid distribution's shape than vice versa.
4. Score >= 90 includes a small number of anomalous scores (>100) from
   early rubric versions that did not cap at 100.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    from scipy.stats import ks_2samp
except ImportError:
    print("ERROR: scipy is required for this script. Install with: pip install scipy", file=sys.stderr)
    sys.exit(1)

REPO = Path(__file__).resolve().parents[3]
ARCHIVE = REPO / "analytics" / "public" / "ledgers" / "trajectory" / "trajectory_archive_enriched.jsonl"
OUTPUT = REPO / "analytics" / "public" / "queries" / "classification" / "lollapalooza_test_2026-04-24.json"

# Rubric dimension vocabulary -- terms that signal engagement with a specific
# rubric evaluation dimension.
DIMENSION_TERMS = [
    "falsification", "falsifiable", "unfalsifiable", "testable", "untestable",
    "derivation", "derived", "underived", "first.?principles",
    "parsimony", "parsimonious", "occam", "overfitt",
    "generali[sz]", "out.?of.?sample", "holdout", "cross.?valid",
    "novelty", "novel", "non.?trivial", "trivial",
    "interpretab", "explain", "explanatory", "mechanism",
    "robustness", "robust", "fragile", "brittle",
    "precision", "accuracy", "residual", "error",
    "completeness", "exhaustive", "coverage",
    "consistency", "consistent", "contradiction",
    "scope", "broad", "narrow",
    "evidence", "empirical", "supported", "unsupported",
    "reproducib", "replicab",
]
DIMENSION_RE = re.compile("|".join(DIMENSION_TERMS), re.IGNORECASE)

# Primitive-like terms in text (fallback when thesis_primitive_names is empty)
PRIMITIVE_TERMS = [
    r"primitive\s+\d+",
    r"pmdl", r"tracy.?widom", r"noether", r"wasserstein",
    r"lll\b", r"lattice", r"sindy", r"compress",
    r"invert", r"eigenquestion", r"basis.?change",
    r"dimensional.?shift", r"reciprocal", r"entropy.?strip",
    r"topolog",
]
PRIMITIVE_RE = re.compile("|".join(PRIMITIVE_TERMS), re.IGNORECASE)


def extract_features(rec: dict[str, Any]) -> dict[str, float]:
    """Extract the three structural features from a record."""
    # (a) primitive count
    names = rec.get("thesis_primitive_names", [])
    if names:
        prim_count = len(names)
    else:
        # Fallback: regex scan of text fields
        text = (rec.get("weakest_point") or "") + " " + (rec.get("rationale") or "")
        prim_count = len(PRIMITIVE_RE.findall(text))

    # (b) dimension term count
    text = (rec.get("weakest_point") or "") + " " + (rec.get("rationale") or "")
    dim_count = len(DIMENSION_RE.findall(text))

    # (c) active constraint count
    constraints = rec.get("active_constraints", [])
    constraint_count = len(constraints)

    return {
        "primitive_count": prim_count,
        "dimension_term_count": dim_count,
        "active_constraint_count": constraint_count,
    }


def main() -> int:
    if not ARCHIVE.is_file():
        print(f"ERROR: {ARCHIVE} not found.", file=sys.stderr)
        return 1

    # Load and bucket
    high_features: list[dict[str, float]] = []  # score >= 90
    mid_features: list[dict[str, float]] = []   # 70 <= score < 90

    with ARCHIVE.open() as f:
        for line in f:
            rec = json.loads(line.strip())
            score = rec.get("score")
            if score is None:
                continue
            feats = extract_features(rec)
            if score >= 90:
                high_features.append(feats)
            elif 70 <= score < 90:
                mid_features.append(feats)

    print(f"High bucket (>=90): {len(high_features)} records")
    print(f"Mid bucket (70-89): {len(mid_features)} records")

    if len(high_features) < 10 or len(mid_features) < 10:
        print("ERROR: insufficient sample sizes for KS test.", file=sys.stderr)
        return 1

    # Run KS tests
    feature_names = ["primitive_count", "dimension_term_count", "active_constraint_count"]
    results = []
    any_significant = False

    for fname in feature_names:
        high_vals = [f[fname] for f in high_features]
        mid_vals = [f[fname] for f in mid_features]
        stat, pval = ks_2samp(high_vals, mid_vals)

        # Descriptive stats
        high_mean = sum(high_vals) / len(high_vals)
        mid_mean = sum(mid_vals) / len(mid_vals)
        high_median = sorted(high_vals)[len(high_vals) // 2]
        mid_median = sorted(mid_vals)[len(mid_vals) // 2]

        significant = bool(pval <= 0.05)
        if significant:
            any_significant = True

        result = {
            "feature": fname,
            "ks_statistic": round(float(stat), 4),
            "p_value": round(float(pval), 6),
            "significant_at_005": significant,
            "high_bucket_mean": round(high_mean, 2),
            "mid_bucket_mean": round(mid_mean, 2),
            "high_bucket_median": high_median,
            "mid_bucket_median": mid_median,
            "high_bucket_n": len(high_vals),
            "mid_bucket_n": len(mid_vals),
        }
        results.append(result)
        print(f"  {fname}: KS={stat:.4f}, p={pval:.6f} {'*** SIGNIFICANT' if significant else '(not significant)'}")
        print(f"    high mean={high_mean:.2f} median={high_median}, mid mean={mid_mean:.2f} median={mid_median}")

    # Verdict
    if any_significant:
        verdict = "SUPPORTED"
        verdict_detail = (
            "At least one structural feature shows a statistically significant "
            "difference (p <= 0.05) between high-scoring (>=90) and mid-scoring "
            "(70-89) iterations. The Lollapalooza hypothesis -- that breakthroughs "
            "require multi-constraint convergence -- is supported by the data, though "
            "the specific distinguishing features should be interpreted with caution "
            "given the known limitations of the thesis_primitive_names field."
        )
    else:
        verdict = "REFUTED"
        verdict_detail = (
            "No structural feature shows a statistically significant difference "
            "(all p > 0.05) between high-scoring (>=90) and mid-scoring (70-89) "
            "iterations. Per the pre-registered falsifier in seam section 9 P1, the "
            "Lollapalooza hypothesis is refuted: high-scoring iterations do not "
            "exhibit detectably different structural signatures from mid-scoring ones "
            "on the features tested."
        )

    output = {
        "generated": "2026-04-24",
        "source": str(ARCHIVE),
        "hypothesis": "Lollapalooza: iterations scoring >= 90 have structurally different thesis-term distributions from iterations at 70-89",
        "falsifier": "KS p > 0.05 for every feature => REFUTED",
        "high_bucket": {"threshold": "score >= 90", "n": len(high_features)},
        "mid_bucket": {"threshold": "70 <= score < 90", "n": len(mid_features)},
        "features_tested": results,
        "verdict": verdict,
        "verdict_detail": verdict_detail,
        "anti_overfitting_notes": [
            "thesis_primitive_names is only populated for the best iteration per project; most records use regex fallback.",
            "active_constraints reflects current rubric state, not historical state at iteration time.",
            f"High bucket N={len(high_features)} is adequate for KS but smaller than mid bucket N={len(mid_features)}.",
        ],
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nVerdict: {verdict}")
    print(f"Wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
