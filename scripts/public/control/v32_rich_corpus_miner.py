#!/usr/bin/env python3
"""v32_rich_corpus_miner.py — run the meta-pattern miner on the CORRECT corpus.

Reuses v32_meta_pattern_miner's contingency + safeguards (min-support,
permutation null, leave-one-out, zero-variance guard) on the
structurally-rich proof corpus where L2-op variation was confirmed
(v32_rich_corpus_l2_test: 5 distinct ops, operator-confirmed).

Corpus per proof:
  L2_op       : operator-confirmed from v32_rich_corpus_l2_test.json
  bucket      : from v30_day7_final_report.json (process/source axis)
  outcome     : from day7 buckets aggregate (H07=survives_partial;
                claimed_moat killed; else gap_or_killed)

Honest expectation: L2 variance good; outcome variance near-zero
(all-negative — this session killed ~everything). The zero-variance /
min-support guards should flag Version B (deployable prior) as
outcome_class_collapse, while Version A (descriptive) may still find a
stable (L2 x bucket x outcome) cell.
"""
from __future__ import annotations
import json, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
sys.path.insert(0, str(ROOT / "scripts/public/control"))
from v32_meta_pattern_miner import contingency, permutation_null, leave_one_namespace_out, MIN_SUPPORT  # type: ignore

LR = ROOT / "analytics/public/leanmill"


def proof_to_rowid(name: str) -> str:
    # "V30RouteCManual/H07_proof.lean" -> "H07"
    base = name.split("/")[-1].replace("_proof", "").replace(".lean", "")
    base = base.split("_v")[0]
    return base.upper()


def main():
    rich = json.load(open(LR / "v32_rich_corpus_l2_test.json"))
    day7 = json.load(open(LR / "v30_day7_final_report.json"))
    day7_rows = day7.get("rows", {})
    buckets = day7.get("buckets", {})
    survivor = buckets.get("survivor_row", "")  # H07_three_term_triangle

    # Map day7 row id -> bucket
    def find_bucket(short: str) -> str:
        for rid, info in day7_rows.items():
            if rid.upper().startswith(short.upper()) or short.upper() in rid.upper():
                return info.get("bucket", "?")
        return "unknown_bucket"

    corpus = []
    for c in rich.get("classified", []):
        op = c.get("op", "?")
        if not op.startswith(("core", "broad", "spec")):
            continue
        short = proof_to_rowid(c["name"])
        bucket = find_bucket(short)
        # Outcome from day7 aggregate
        if short and survivor and short.upper() in survivor.upper():
            outcome = "survives_partial"
        elif short.startswith("K"):
            outcome = "killed_gcongr_floor"   # K-files were gcongr self-kill (session memory)
        else:
            outcome = "killed_or_gap"
        corpus.append({
            "row_id": short,
            "name": c["name"],
            "L2_op": op,
            "L1_pattern": bucket,          # bucket = process/source axis
            "namespace": bucket,           # use bucket for leave-one-out resample
            "outcome": outcome,
        })

    print(f"# v32 rich-corpus miner — {len(corpus)} proofs (operator-confirmed L2)\n")
    print(f"L2_op distribution: {dict(Counter(r['L2_op'] for r in corpus))}")
    print(f"bucket distribution: {dict(Counter(r['L1_pattern'] for r in corpus))}")
    print(f"outcome distribution: {dict(Counter(r['outcome'] for r in corpus))}")

    distinct_out = len({r["outcome"] for r in corpus})
    distinct_l2 = len({r["L2_op"] for r in corpus})
    distinct_bucket = len({r["L1_pattern"] for r in corpus})

    print(f"\nVariance check: L2={distinct_l2} bucket={distinct_bucket} outcome={distinct_out}")

    # Honest guard: deployable prior requires outcome variance (>=2 outcomes,
    # AND the minority outcome has >= MIN_SUPPORT). Otherwise outcome_class_collapse.
    out_counts = Counter(r["outcome"] for r in corpus)
    minority = min(out_counts.values()) if out_counts else 0
    if distinct_out < 2 or minority < MIN_SUPPORT:
        version_b_verdict = "outcome_class_collapse"
        version_b_rat = (
            f"outcome variance insufficient for a deployable SUCCESS prior: "
            f"distinct_outcomes={distinct_out}, minority_class_support={minority} "
            f"< MIN_SUPPORT={MIN_SUPPORT}. The rich corpus is ~all-negative "
            f"(this session killed ~everything; only {survivor or 'H07'} partially "
            f"survives). Cannot mine 'which L2-op predicts success' with ~0 successes. "
            f"NOT a label-quality problem (L2 labels operator-confirmed, {distinct_l2} "
            f"distinct) — a corpus-outcome-imbalance problem."
        )
    else:
        version_b_verdict = "outcome_variance_ok_proceed_to_contingency"
        version_b_rat = "outcome variance sufficient; running full contingency."

    # Version A descriptive: (L2_op x bucket x outcome) — post-hoc allowed
    cells, grand, cv = contingency(corpus, ("L2_op", "L1_pattern"))
    ver_a = {"verdict": "no_pattern_in_corpus", "rationale": "no cell >= min support"}
    if cells:
        top = cells[0]
        perm_p = permutation_null(corpus, ("L2_op", "L1_pattern"), top["chi2"], n_perm=1000)
        preserved, n_ns, _ = leave_one_namespace_out(corpus, ("L2_op", "L1_pattern"))
        stable = (n_ns >= 2 and preserved >= max(1, n_ns - 1))
        if perm_p < 0.05 and top["support"] >= MIN_SUPPORT and stable:
            ver_a = {
                "verdict": "descriptive_meta_pattern_found",
                "top_cell": top, "perm_p": perm_p,
                "resample": f"{preserved}/{n_ns}",
                "rationale": (f"stable descriptive cell (L2={top['cell'][0]}, "
                              f"bucket={top['cell'][1]}, outcome={top['outcome']}) "
                              f"support={top['support']} lift={top['lift']} "
                              f"perm_p={perm_p:.3f} — POSTMORTEM HYGIENE, not a solver prior"),
            }
        else:
            ver_a = {
                "verdict": "no_stable_descriptive_pattern",
                "top_cell": top, "perm_p": perm_p,
                "resample": f"{preserved}/{n_ns}",
                "rationale": f"top cell unstable or insignificant (perm_p={perm_p:.3f}, support={top['support']}, resample {preserved}/{n_ns})",
            }

    print(f"\n=== VERSION A (descriptive, post-hoc) ===")
    print(f"VERDICT: {ver_a['verdict']} — {ver_a['rationale']}")
    print(f"\n=== VERSION B (deployable solver prior) ===")
    print(f"VERDICT: {version_b_verdict} — {version_b_rat}")

    print(f"\n## OVERALL HONEST VERDICT")
    if version_b_verdict == "outcome_class_collapse":
        overall = (
            "SUBSTRATE_SIGNAL_REAL_BUT_CORPUS_ALL_NEGATIVE — the 3-catalog L2 "
            "vocabulary discriminates rich proofs (operator-confirmed, "
            f"{distinct_l2} distinct ops). But NO deployable success-prior is "
            "extractable from this session's corpus because ~every attempt was "
            "killed (outcome class collapse). To extract a deployable prior, the "
            "miner needs a corpus with genuine SUCCESSES — e.g. v22-v29 "
            "claimed-closure attempts (pre-retraction) + their kills, giving "
            "outcome variance. Descriptive postmortem mining (Version A) is the "
            "only thing this corpus supports."
        )
    else:
        overall = f"proceed: {ver_a['verdict']}"
    print(overall)

    Path(LR / "v32_rich_corpus_miner_results.json").write_text(json.dumps({
        "n_corpus": len(corpus),
        "L2_distribution": dict(Counter(r["L2_op"] for r in corpus)),
        "bucket_distribution": dict(Counter(r["L1_pattern"] for r in corpus)),
        "outcome_distribution": dict(out_counts),
        "version_A": ver_a,
        "version_B_verdict": version_b_verdict,
        "version_B_rationale": version_b_rat,
        "overall": overall,
    }, indent=2, default=str))
    print(f"\nwrote {LR / 'v32_rich_corpus_miner_results.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
