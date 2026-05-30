#!/usr/bin/env python3
"""Forecasting-specific statistical analysis on top of `src.ztare.experiment_stats`.

General-purpose statistics (power, bootstrap, permutation, Spearman, TOST,
BH-FDR, Bayes factor, power-aware verdict, reproducibility manifest) live in
the reusable package `src/ztare/experiment_stats/`.

This module wires those primitives to the calibration SQLite database
(`analytics/public/calibration/forecaster_calibration.db`) and adds a few
forecasting-specific helpers (Brier decomposition, per-family rho-from-pilot,
finding-replication harness).

CLI:
  brier-ci      --primitive --corpus [--family] [--pilot] [--phase]
  delta-test    --primitive --corpus [--family]
  spearman      --pilot --x [--y]
  elo           --corpus
  finding       <name>
  power-n       --rho
  power-detectable --n
  tost          --pilot-a --pilot-b --bound
  fdr           --finding
  brier-decomp  --pilot --family
"""
from __future__ import annotations
import argparse
import json
import math
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DB_PATH = REPO / "analytics" / "public" / "calibration" / "forecaster_calibration.db"
# Make ztare importable when this file is run directly OR imported as ztare.forecasting.calibration_stats
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from ztare.experiment_stats import (
    n_required_for_rho, detectable_rho_at_n, n_required_for_brier_delta,
    bootstrap_ci,
    paired_permutation_test,
    spearman_rho, spearman_rho_with_ci,
    tost_equivalence,
    bh_fdr,
    power_aware_verdict,
    bf_bic_paired_t,
    reproducibility_hash,
)


def conn():
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    return c


# ============================== Per-family Brier with CI ==============================

def brier_with_ci(primitive_base=None, corpus=None, family=None, pilot_id=None,
                   phase="full"):
    c = conn()
    sql = """
        SELECT pc.brier, pc.family
          FROM pilot_calls pc
          JOIN pilot_runs  pr ON pr.pilot_id = pc.pilot_id
         WHERE pc.schema_ok = 1
           AND pc.brier IS NOT NULL
           AND pc.family IS NOT NULL
    """
    args = []
    if primitive_base:
        sql += " AND pc.primitive_base = ?"; args.append(primitive_base)
    if phase is not None:
        sql += " AND pc.phase = ?"; args.append(phase)
    if corpus:
        sql += " AND pr.corpus = ?"; args.append(corpus)
    if family:
        sql += " AND pc.family = ?"; args.append(family)
    if pilot_id:
        sql += " AND pr.pilot_id = ?"; args.append(pilot_id)
    rows = c.execute(sql, args).fetchall()
    c.close()
    by_family = defaultdict(list)
    for r in rows:
        by_family[r["family"]].append(r["brier"])
    out = []
    for f, vs in sorted(by_family.items()):
        mean_v, lo, hi = bootstrap_ci(vs)
        out.append({"family": f, "n": len(vs),
                    "mean_brier": round(mean_v, 4) if mean_v is not None else None,
                    "ci_lo": round(lo, 4) if lo is not None else None,
                    "ci_hi": round(hi, 4) if hi is not None else None})
    return out


# ============================== Δ-Brier permutation ==============================

def delta_brier_test(primitive_base, corpus, family,
                      baseline_primitive="baseline", n_perm=5000):
    c = conn()
    rows_v = c.execute("""
        SELECT pc.contract_id, pc.brier
          FROM pilot_calls pc JOIN pilot_runs pr ON pr.pilot_id=pc.pilot_id
         WHERE pc.primitive_base=? AND pc.phase='full' AND pr.corpus=?
           AND pc.family=? AND pc.schema_ok=1 AND pc.brier IS NOT NULL
    """, (primitive_base, corpus, family)).fetchall()
    rows_b = c.execute("""
        SELECT pc.contract_id, pc.brier
          FROM pilot_calls pc JOIN pilot_runs pr ON pr.pilot_id=pc.pilot_id
         WHERE pc.primitive_base=? AND pc.phase='full' AND pr.corpus=?
           AND pc.family=? AND pc.schema_ok=1 AND pc.brier IS NOT NULL
    """, (baseline_primitive, corpus, family)).fetchall()
    c.close()
    v_map = {r["contract_id"]: r["brier"] for r in rows_v}
    b_map = {r["contract_id"]: r["brier"] for r in rows_b}
    common = sorted(set(v_map) & set(b_map))
    a = [v_map[c] for c in common]
    b = [b_map[c] for c in common]
    result = paired_permutation_test(a, b, n_perm=n_perm)
    # Augment with BIC-approximation Bayes factor — continuous evidence ratio.
    if len(a) >= 4:
        bf = bf_bic_paired_t(a, b)
        result["bf_10"] = bf.get("bf_10")
        result["bf_interp"] = bf.get("interpretation")
    result["family"] = family
    return result


# ============================== Spearman per family from a pilot ==============================

def spearman_per_family(pilot_id, x_field, y_field=None):
    """For a given pilot, compute Spearman ρ per family between parsed[x_field]
    and parsed[y_field] (or brier if y_field is None)."""
    c = conn()
    rows = c.execute("""
        SELECT pc.family, pc.parsed_json, pc.brier
          FROM pilot_calls pc
         WHERE pc.pilot_id = ?
           AND pc.schema_ok = 1
           AND pc.family IS NOT NULL
    """, (pilot_id,)).fetchall()
    c.close()
    by_family = defaultdict(list)
    for r in rows:
        try:
            parsed = json.loads(r["parsed_json"] or "{}")
        except Exception:
            continue
        x = parsed.get(x_field)
        y = parsed.get(y_field) if y_field else r["brier"]
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            continue
        by_family[r["family"]].append((x, y))
    out = []
    for f, pairs in sorted(by_family.items()):
        if len(pairs) < 4:
            out.append({"family": f, "n": len(pairs), "rho": None,
                        "ci_lo": None, "ci_hi": None, "note": "n<4"})
            continue
        xs, ys = zip(*pairs)
        rho, lo, hi = spearman_rho_with_ci(list(xs), list(ys))
        out.append({"family": f, "n": len(pairs),
                    "rho": round(rho, 3) if rho is not None else None,
                    "ci_lo": round(lo, 3) if lo is not None else None,
                    "ci_hi": round(hi, 3) if hi is not None else None})
    return out


# ============================== Elo from contract-level Brier wins ==============================

def family_elo(corpus, k=32, n_iter=10, seed=42):
    import random as _random
    c = conn()
    rows = c.execute("""
        SELECT pc.contract_id, pc.family, pc.brier
          FROM pilot_calls pc JOIN pilot_runs pr ON pr.pilot_id = pc.pilot_id
         WHERE pr.corpus = ? AND pc.primitive_base = 'baseline'
           AND pc.phase = 'full' AND pc.schema_ok = 1
           AND pc.brier IS NOT NULL AND pc.family IS NOT NULL
    """, (corpus,)).fetchall()
    c.close()
    by_contract = defaultdict(dict)
    for r in rows:
        by_contract[r["contract_id"]][r["family"]] = r["brier"]
    families = set()
    for d in by_contract.values():
        families.update(d.keys())
    rating = {f: 1500.0 for f in families}
    pairs = []
    for f_briers in by_contract.values():
        fs = list(f_briers.keys())
        for i in range(len(fs)):
            for j in range(i + 1, len(fs)):
                a, b = fs[i], fs[j]
                if f_briers[a] < f_briers[b]: pairs.append((a, b, 1))
                elif f_briers[a] > f_briers[b]: pairs.append((a, b, 0))
                else: pairs.append((a, b, 0.5))
    rng = _random.Random(seed)
    for _ in range(n_iter):
        rng.shuffle(pairs)
        for a, b, sa in pairs:
            ea = 1 / (1 + 10 ** ((rating[b] - rating[a]) / 400))
            rating[a] += k * (sa - ea)
            rating[b] += k * ((1 - sa) - (1 - ea))
    return [{"family": f, "elo": round(rating[f], 1)}
            for f in sorted(rating, key=lambda x: -rating[x])]


# ============================== Brier decomposition (Murphy) ==============================

def brier_decomposition(pilot_id, family, n_bins=10):
    """Murphy decomposition: Brier = reliability − resolution + uncertainty.

    reliability  = E[(p_bin − y_bin)²]  (lower is better)
    resolution   = E[(y_bin − y_overall)²] (higher is better)
    uncertainty  = y_overall * (1 − y_overall) (fixed property of the dataset)
    """
    c = conn()
    rows = c.execute("""
        SELECT pc.p_success, c.y_known
          FROM pilot_calls pc
          JOIN contracts c ON c.contract_id = pc.contract_id
         WHERE pc.pilot_id = ? AND pc.family = ?
           AND pc.schema_ok = 1 AND pc.p_success IS NOT NULL
           AND c.y_known IS NOT NULL
    """, (pilot_id, family)).fetchall()
    c.close()
    if not rows:
        return {"error": "no rows"}
    n = len(rows)
    y_overall = sum(r["y_known"] for r in rows) / n
    # Bin by p_success
    bins = [[] for _ in range(n_bins)]
    for r in rows:
        p = r["p_success"]
        idx = min(int(p * n_bins), n_bins - 1)
        bins[idx].append((p, r["y_known"]))
    reliability = resolution = 0.0
    for b in bins:
        if not b: continue
        p_avg = sum(p for p, _ in b) / len(b)
        y_avg = sum(y for _, y in b) / len(b)
        w = len(b) / n
        reliability += w * (p_avg - y_avg) ** 2
        resolution  += w * (y_avg - y_overall) ** 2
    uncertainty = y_overall * (1 - y_overall)
    brier = reliability - resolution + uncertainty
    return {"n": n, "y_overall": round(y_overall, 4),
            "reliability": round(reliability, 4),
            "resolution": round(resolution, 4),
            "uncertainty": round(uncertainty, 4),
            "brier_implied": round(brier, 4)}


# ============================== Finding-replication harness ==============================

FINDINGS = {
    "F54": {
        "description": "Frequency framing (v26d) Δ-Brier vs baseline per family per corpus",
        "expected": {
            "internal": {"claude": "null", "codex_55": "null", "codex_mini": "improves",
                         "gemini": "improves", "deepseek": "degrades"},
            "v25_external": {"claude": "null", "codex_55": "improves", "codex_mini": "null",
                              "gemini": "degrades", "deepseek": "improves"},
        },
        "primitive": "v26d",
    },
    "F56": {
        "description": "Bid-ask spread (v27a) correlates with Brier per family",
        "expected": {
            "internal": {"claude": "improves", "codex_55": "null", "codex_mini": "improves",
                         "gemini": "improves", "deepseek": "improves"},
        },
        "primitive": "v27a", "metric": "spread_vs_brier",
    },
}


def check_finding(name):
    f = FINDINGS.get(name)
    if not f:
        return {"finding": name, "error": "unknown finding"}
    out = {"finding": name, "description": f["description"], "results": {}}
    for corpus, expected in f["expected"].items():
        results = []
        for family, exp_dir in expected.items():
            test = delta_brier_test(f["primitive"], corpus, family)
            d = test.get("observed_delta")
            verdict = "?"
            if d is None: verdict = "no data"
            elif test.get("p_value", 1) > 0.10: verdict = "null"
            elif d < 0: verdict = "improves"
            elif d > 0: verdict = "degrades"
            match = "✓" if verdict == exp_dir else "✗"
            results.append({**test, "expected": exp_dir, "verdict": verdict, "match": match})
        out["results"][corpus] = results
    return out


# ============================== CLI ==============================

def _print_rows(rows):
    if not rows: print("(no rows)"); return
    cols = list(rows[0].keys())
    print(" | ".join(cols))
    print("-" * 80)
    for r in rows:
        print(" | ".join(str(r[c]) for c in cols))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("brier-ci")
    p.add_argument("--primitive"); p.add_argument("--corpus")
    p.add_argument("--family"); p.add_argument("--pilot"); p.add_argument("--phase", default="full")

    p = sub.add_parser("delta-test")
    p.add_argument("--primitive", required=True); p.add_argument("--corpus", required=True)
    p.add_argument("--family"); p.add_argument("--target-rho", type=float, default=0.30)

    p = sub.add_parser("spearman")
    p.add_argument("--pilot", required=True); p.add_argument("--x", required=True)
    p.add_argument("--y"); p.add_argument("--target-rho", type=float, default=0.30)

    p = sub.add_parser("elo"); p.add_argument("--corpus", required=True)
    p = sub.add_parser("finding"); p.add_argument("name")

    p = sub.add_parser("power-n"); p.add_argument("--rho", type=float, required=True)
    p = sub.add_parser("power-detectable"); p.add_argument("--n", type=int, required=True)

    p = sub.add_parser("tost")
    p.add_argument("--primitive-a", required=True); p.add_argument("--primitive-b", required=True)
    p.add_argument("--corpus", required=True); p.add_argument("--family", required=True)
    p.add_argument("--bound", type=float, default=0.05)

    p = sub.add_parser("brier-decomp")
    p.add_argument("--pilot", required=True); p.add_argument("--family", required=True)

    p = sub.add_parser("verdict")
    p.add_argument("--rho", type=float, required=True); p.add_argument("--n", type=int, required=True)
    p.add_argument("--target-rho", type=float, default=0.30)

    args = ap.parse_args()

    if args.cmd == "brier-ci":
        _print_rows(brier_with_ci(primitive_base=args.primitive, corpus=args.corpus,
                                   family=args.family, pilot_id=args.pilot, phase=args.phase))
    elif args.cmd == "delta-test":
        fams = [args.family] if args.family else ["claude","codex_55","codex_mini","gemini","deepseek"]
        rows = [delta_brier_test(args.primitive, args.corpus, f) for f in fams]
        # Add power-aware verdict per row
        for r in rows:
            if r.get("observed_delta") is not None and r.get("n_paired", 0) > 3:
                # Translate Δ-Brier to an effective ρ via correlation against baseline isn't direct;
                # use p_value-based verdict instead
                p = r.get("p_value", 1.0)
                r["verdict"] = "h1_supported" if p < 0.05 else "inconclusive_underpowered"
        _print_rows(rows)
    elif args.cmd == "spearman":
        rows = spearman_per_family(args.pilot, args.x, args.y)
        for r in rows:
            if r.get("rho") is not None and r.get("n", 0) > 3:
                v, note = power_aware_verdict(r["rho"], r["n"], target_rho=args.target_rho)
                r["verdict"] = v
        _print_rows(rows)
    elif args.cmd == "elo":
        _print_rows(family_elo(args.corpus))
    elif args.cmd == "finding":
        print(json.dumps(check_finding(args.name), indent=2))
    elif args.cmd == "power-n":
        n = n_required_for_rho(args.rho)
        print(f"To detect ρ={args.rho} (α=0.05 two-tailed, 80% power): N ≥ {n}")
    elif args.cmd == "power-detectable":
        r = detectable_rho_at_n(args.n)
        print(f"At N={args.n}: smallest detectable |ρ| (α=0.05, 80% power) = {r:.3f}")
    elif args.cmd == "tost":
        # Paired Brier-equivalence between two primitives on same corpus+family
        c = conn()
        sql = """SELECT pc.contract_id, pc.brier FROM pilot_calls pc
                 JOIN pilot_runs pr ON pr.pilot_id=pc.pilot_id
                 WHERE pc.primitive_base=? AND pc.phase='full' AND pr.corpus=?
                   AND pc.family=? AND pc.schema_ok=1 AND pc.brier IS NOT NULL"""
        ra = {r["contract_id"]: r["brier"] for r in c.execute(sql, (args.primitive_a, args.corpus, args.family))}
        rb = {r["contract_id"]: r["brier"] for r in c.execute(sql, (args.primitive_b, args.corpus, args.family))}
        c.close()
        common = sorted(set(ra) & set(rb))
        a = [ra[k] for k in common]; b = [rb[k] for k in common]
        r = tost_equivalence(a, b, args.bound)
        print(json.dumps(r, indent=2))
    elif args.cmd == "brier-decomp":
        print(json.dumps(brier_decomposition(args.pilot, args.family), indent=2))
    elif args.cmd == "verdict":
        v, note = power_aware_verdict(args.rho, args.n, target_rho=args.target_rho)
        print(f"verdict: {v}\nnote: {note}")


if __name__ == "__main__":
    main()
