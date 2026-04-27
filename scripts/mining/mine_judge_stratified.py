"""GP-149 Oracle Illusion countermeasure — stratified mining by (mutator, judge).

Every earlier Stage 2 query aggregated across all (mutator, judge) pairs. That's
incorrect if judge family materially affects score distributions (which the
operator 2026-04-24 finding confirmed: claude-sonnet judge gives o3 mutator
mean 15.4 while gpt-4.1 judge gives same mutator mean 42.6 — 3x delta).

This script re-runs three key analyses STRATIFIED by judge family:
  1. B3 structural-blocker vs ceiling-breaker lift analysis
  2. Pivot-effectiveness per cluster
  3. Top-3 walls / ceilings

Patterns that replicate across judge families are STRUCTURAL. Patterns that
appear in only one judge family are JUDGE-SPECIFIC aesthetic. Only structural
patterns should be promoted to kernel-default interventions.

Output: analytics/queries/judge_stratified_analysis_<YYYY-MM-DD>.json
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ARCH = REPO / "analytics" / "trajectory_archive_enriched.jsonl"
REGEX_CLUSTERS = REPO / "analytics" / "queries" / "weakest_link_clusters_2026-04-24.json"
LLM_CLUSTERS = REPO / "analytics" / "queries" / "weakest_link_llm_subclasses_2026-04-24.json"
OUT = REPO / "analytics" / "queries"

MIN_N_PER_CELL = 10


def canon_family(m):
    if not m:
        return "unknown"
    m = str(m).lower()
    for fam in ("o3-mini", "o3-pro", "o3", "o4-mini", "o4", "o1",
                "gpt-4.1-mini", "gpt-4.1", "gpt-4o",
                "claude-opus", "claude-sonnet", "claude-haiku",
                "gemini-3.1-pro-preview", "gemini-3.1-flash-lite",
                "gemini-2.5-flash", "gemini"):
        if m.startswith(fam):
            return fam
    return m.split("-")[0] if "-" in m else m


def load_classes():
    cls = {}
    if REGEX_CLUSTERS.is_file():
        r = json.loads(REGEX_CLUSTERS.read_text())
        for cl in r.get("clusters", []):
            name = cl.get("cluster_id") or cl.get("cluster_name")
            for p, ts in cl.get("members", []):
                cls[(p, int(ts))] = name
    if LLM_CLUSTERS.is_file():
        l = json.loads(LLM_CLUSTERS.read_text())
        for c in l.get("categories", []):
            cat = c.get("category")
            for p, ts in c.get("members", []):
                cls[(p, int(ts))] = cat
    return cls


def main():
    cls_by_key = load_classes()
    records = []
    with ARCH.open() as f:
        for line in f:
            r = json.loads(line)
            r["mutator_family"] = canon_family(r.get("mutator_model_id"))
            r["judge_family"] = canon_family(r.get("judge_model_id"))
            r["cluster"] = cls_by_key.get((r.get("project"), r.get("iter_timestamp")))
            records.append(r)

    # Enumerate judge families with enough records for meaningful stats
    judge_counts = Counter(r["judge_family"] for r in records)
    judges = [j for j, n in judge_counts.most_common() if n >= 50 and j != "unknown"]

    report = {
        "generated": str(date.today()),
        "total_records": len(records),
        "min_n_per_cell": MIN_N_PER_CELL,
        "judge_families_analyzed": judges,
        "judge_record_counts": {j: judge_counts[j] for j in judges},
        "oracle_illusion_warning": (
            "Patterns that do NOT replicate across judge families are judge-specific "
            "aesthetic, NOT structural. Only cross-judge-replicated patterns should "
            "be promoted to kernel-default interventions."
        ),
        "per_judge": {},
    }

    for judge in judges:
        cell = [r for r in records if r["judge_family"] == judge]
        n = len(cell)

        # 1. B3 lift by score bucket for key classes
        bucket_n = Counter()
        bucket_cls = defaultdict(lambda: Counter())
        for r in cell:
            score = r.get("score")
            if score is None:
                continue
            b = "high" if score >= 85 else ("mid" if score >= 60 else "low")
            bucket_n[b] += 1
            if r["cluster"]:
                bucket_cls[b][r["cluster"]] += 1

        b3_report = {}
        for cls_name in [
            "Circularity / Tautology / Self-Reference", "Harness / Test-Suite Defect",
            "overclaimed_scope", "missing_mechanism", "missing_counterfactual",
            "Tail / Extrapolation / Far-Field Generalization Failure",
            "Unverified Bound / Unproven Claim", "Catastrophic / Load-Bearing Assumption",
            "parameter_sensitivity", "Exhaustiveness / Completeness Over-Claim",
            "unfalsifiable_claim",
        ]:
            hf = bucket_cls["high"].get(cls_name, 0) / max(bucket_n["high"], 1)
            mf = bucket_cls["mid"].get(cls_name, 0) / max(bucket_n["mid"], 1)
            lf = bucket_cls["low"].get(cls_name, 0) / max(bucket_n["low"], 1)
            lift = (hf / lf) if lf > 0 else (float("inf") if hf > 0 else 0.0)
            b3_report[cls_name] = {
                "high_freq": round(hf, 3), "mid_freq": round(mf, 3), "low_freq": round(lf, 3),
                "lift_high_over_low": round(lift, 2) if lift != float("inf") else "inf",
                "insufficient": bucket_n["high"] < MIN_N_PER_CELL,
            }

        # 2. Score distribution
        scores = [r["score"] for r in cell if isinstance(r.get("score"), (int, float))]
        if scores:
            sorted_s = sorted(scores)
            score_report = {
                "n_scored": len(scores),
                "mean": round(sum(scores) / len(scores), 2),
                "median": sorted_s[len(sorted_s) // 2],
                "p25": sorted_s[len(sorted_s) // 4],
                "p75": sorted_s[3 * len(sorted_s) // 4],
                "pct_high_85": round(sum(1 for s in scores if s >= 85) / len(scores) * 100, 1),
            }
        else:
            score_report = None

        # 3. Top mutator families paired with this judge
        mut_dist = Counter(r["mutator_family"] for r in cell)
        top_muts = [(m, n) for m, n in mut_dist.most_common(5)]

        report["per_judge"][judge] = {
            "n_records": n,
            "n_scored": len(scores) if scores else 0,
            "score_summary": score_report,
            "top_mutator_pairs": top_muts,
            "B3_lift_by_class": b3_report,
            "bucket_counts": dict(bucket_n),
        }

    # Cross-judge replication check: for each class, count how many judges show
    # the same lift direction
    print("=" * 76)
    print("B3 lift-direction replication across judge families")
    print("=" * 76)
    classes = list(next(iter(report["per_judge"].values()))["B3_lift_by_class"].keys())
    print(f"{'class':<52}  " + "  ".join(f"{j[:12]:<12}" for j in judges))
    for c in classes:
        row = [f"  {c[:50]:<52}"]
        for j in judges:
            lift = report["per_judge"][j]["B3_lift_by_class"][c]["lift_high_over_low"]
            if isinstance(lift, float):
                row.append(f"{lift:<12.2f}")
            else:
                row.append(f"{str(lift):<12}")
        print("  ".join(row))

    print()
    print("Score distribution by judge:")
    print(f"  {'judge':<28}  {'n':>5}  {'mean':>6}  {'median':>7}  {'≥85%':>5}")
    for j in judges:
        ss = report["per_judge"][j]["score_summary"]
        if ss:
            print(f"  {j:<28}  {ss['n_scored']:>5}  {ss['mean']:>6}  {ss['median']:>7}  {ss['pct_high_85']:>5}")

    out_path = OUT / f"judge_stratified_analysis_{date.today()}.json"
    out_path.write_text(json.dumps(report, indent=2))
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
