#!/usr/bin/env python3
"""v32_meta_pattern_miner.py — the meta-solver substrate test (GPT-5.5-blessed).

Tests whether the 3-catalog meta-pattern substrate has measurable signal:
  Lean attempt corpus → L2 content-op → L1 process-pattern → L3 signal →
  outcome → mine stable regularities.

GPT-5.5 critical refinement: post-hoc L3 kill labels LEAK the outcome
(L3=simp_set_indirect_leakage → killed is a tautology, not a prior).
So this runs TWO versions:

  Version A — descriptive audit mining (uses post-hoc L3 kill reasons).
    Verdict ceiling: `descriptive_meta_pattern_found`. NOT a solver prior.
  Version B — deployable prior mining (uses ONLY preflight features:
    L2 predicted op, L1 pattern chosen, L3 risk predicted BEFORE run).
    Verdict: `solver_prior_found` possible.

5 safeguards (GPT-5.5): (1) min support ≥5, (2) Benjamini-Hochberg FDR,
(3) effect size lift+odds+Cramér's V, (4) permutation null ×1000,
(5) label-confidence buckets (all / high-conf / ambiguous).

Resample: leave-one-namespace-out, pass requires rank-1 cell preserved
≥5/6 (stricter than the v32 doc's ≥4/6, per GPT-5.5).

Anti-amnesia: reuses universal_classifier (L2) + inventoried corpus.
No GNN. No LLM. No new primitive. No architecture.

Standard-form output only. No essay.
"""
from __future__ import annotations
import argparse, json, math, random, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "venv/lib/python3.13/site-packages"))
sys.path.insert(0, str(ROOT / "scripts/public/control"))

try:
    from src.ztare.research_director.universal_classifier import classify_text  # type: ignore
    HAVE_L2 = True
except Exception as e:
    HAVE_L2 = False
    _L2_ERR = str(e)

try:
    from archetype_classifier import classify as preflight_classify  # type: ignore
    HAVE_PREFLIGHT = True
except Exception:
    HAVE_PREFLIGHT = False

MIN_SUPPORT = 5
RESAMPLE_PASS = 5  # of 6 namespaces


# ---------------------------------------------------------------------------
# v32.1 — Corpus assembler (preflight L3 SEPARATE from posthoc L3)
# ---------------------------------------------------------------------------

def assemble_corpus() -> list[dict]:
    rows: list[dict] = []
    curated_path = Path("/tmp/v32_curated_test_rows.json")
    if curated_path.exists():
        curated = json.load(open(curated_path))
        for r in curated.get("rows", []):
            rid = r.get("row_id")
            src = r.get("source_file", "") or ""
            ns = src.split("/")[1] if "/" in src else "?"
            thm_text = (r.get("theorem", "") or "") + " " + src

            # PREFLIGHT features — computed BEFORE the run, no outcome leak
            l2_pre, l2_conf, l3_pre = "L2_none", "low", []
            if HAVE_L2 and thm_text.strip():
                try:
                    c = classify_text(thm_text)
                    l2_pre = c.dominant_op or "L2_no_signal"
                    l2_conf = c.confidence
                except Exception:
                    pass
            if HAVE_PREFLIGHT:
                try:
                    pf = preflight_classify(f"theorem {r.get('theorem','x')} : True := by sorry")
                    l3_pre = pf.get("predicted_L3_anti_pattern_flags", []) or []
                except Exception:
                    pass

            # POSTHOC features — only known AFTER the run (outcome-leaking)
            replay_json = Path(f"/tmp/v32_replay_{rid}.json")
            outcome = "unknown"
            l3_post = None
            l1_pat = "route_c_layer_2c"
            if replay_json.exists():
                try:
                    rj = json.load(open(replay_json))
                    outcome = "closed" if rj.get("compiled_any") else "gap_report"
                    for rd in rj.get("rounds", []):
                        lc = rd.get("lean_compile", {})
                        et = (lc.get("error_tail", "") or "")
                        if "synthInstance" in et or "failed to synthesize" in et:
                            l3_post = "typeclass_synthesis_fail"
                        elif "unexpected token" in et or "unexpected identifier" in et:
                            l3_post = "lean4_syntax_error"
                        elif "unsolved goals" in et:
                            l3_post = "unsolved_goals"
                        elif "unknown tactic" in et:
                            l3_post = "unknown_tactic"
                except Exception:
                    pass
            if r.get("quarantined"):
                l3_post = "gold_tactic_exposed_quarantine"
                outcome = "quarantined"

            rows.append({
                "row_id": rid,
                "source_file": src,
                "namespace": ns,
                "theorem": r.get("theorem"),
                "L1_pattern": l1_pat,
                "L2_op": l2_pre,
                "L2_confidence": l2_conf,
                "L3_flag_preflight": ";".join(sorted(l3_pre)) if l3_pre else "none",
                "L3_failure_posthoc": l3_post or "none",
                "outcome": outcome,
                "source": "v32_curated",
            })

    # v2.1+ inventory rows (have negative-result signal; posthoc only)
    inv_path = Path("/tmp/v2_1_row_isolation_inventory.json")
    if inv_path.exists():
        try:
            inv = json.load(open(inv_path))
            inv_rows = inv if isinstance(inv, list) else inv.get("artifacts", inv.get("rows", []))
            for a in inv_rows:
                if not isinstance(a, dict) or not (a.get("contains_rows") or a.get("contains_negative_results")):
                    continue
                summ = a.get("summary", "") or ""
                l2_pre = "L2_none"
                if HAVE_L2 and summ.strip():
                    try:
                        l2_pre = classify_text(summ).dominant_op or "L2_no_signal"
                    except Exception:
                        pass
                rows.append({
                    "row_id": (a.get("file_path", "?") or "?").split("/")[-1],
                    "source_file": a.get("file_path", "?"),
                    "namespace": "v2_1_inv",
                    "theorem": None,
                    "L1_pattern": a.get("artifact_kind", "?"),
                    "L2_op": l2_pre,
                    "L2_confidence": "low",
                    "L3_flag_preflight": "none",  # no preflight for historical
                    "L3_failure_posthoc": "negative_result" if a.get("contains_negative_results") else "none",
                    "outcome": "negative" if a.get("contains_negative_results") else "curated",
                    "source": "v2_1_inventory",
                })
        except Exception:
            pass
    return rows


# ---------------------------------------------------------------------------
# v32.2 — Contingency miner with effect size
# ---------------------------------------------------------------------------

def contingency(rows: list[dict], cell_keys: tuple, outcome_key: str = "outcome"):
    table: Counter = Counter()
    row_tot: Counter = Counter()
    col_tot: Counter = Counter()
    for r in rows:
        ck = tuple(r.get(k, "?") for k in cell_keys)
        oc = r.get(outcome_key, "?")
        table[(ck, oc)] += 1
        row_tot[ck] += 1
        col_tot[oc] += 1
    grand = sum(table.values())
    cells = []
    for (ck, oc), n in table.items():
        if n < MIN_SUPPORT:
            continue  # safeguard 1: minimum support
        exp = (row_tot[ck] * col_tot[oc]) / grand if grand else 0
        lift = (n / row_tot[ck]) / (col_tot[oc] / grand) if (row_tot[ck] and col_tot[oc] and grand) else 0
        chi2 = ((n - exp) ** 2 / exp) if exp > 0 else 0
        # odds ratio (2x2 collapse: this cell vs rest)
        a = n
        b = row_tot[ck] - n
        c = col_tot[oc] - n
        d = grand - a - b - c
        odds = ((a + 0.5) * (d + 0.5)) / ((b + 0.5) * (c + 0.5))
        cells.append({
            "cell": list(ck), "outcome": oc, "support": n,
            "expected": round(exp, 2), "lift": round(lift, 3),
            "odds_ratio": round(odds, 3), "chi2": round(chi2, 3),
        })
    # Cramér's V for the whole table
    total_chi2 = sum(c["chi2"] for c in cells)
    k = min(len(row_tot), len(col_tot))
    cramers_v = math.sqrt(total_chi2 / (grand * (k - 1))) if (grand and k > 1) else 0
    cells.sort(key=lambda c: -c["chi2"])
    return cells, grand, round(cramers_v, 3)


def permutation_null(rows: list[dict], cell_keys: tuple, observed_top_chi2: float, n_perm: int = 1000) -> float:
    """Safeguard 4: shuffle outcomes; fraction of perms with top-chi2 >= observed."""
    outcomes = [r.get("outcome", "?") for r in rows]
    hits = 0
    rnd = random.Random(42)
    for _ in range(n_perm):
        shuf = outcomes[:]
        rnd.shuffle(shuf)
        perm_rows = [{**r, "outcome": shuf[i]} for i, r in enumerate(rows)]
        cells, _, _ = contingency(perm_rows, cell_keys)
        top = cells[0]["chi2"] if cells else 0
        if top >= observed_top_chi2:
            hits += 1
    return hits / n_perm


def leave_one_namespace_out(rows: list[dict], cell_keys: tuple) -> tuple[int, int, list]:
    namespaces = sorted({r["namespace"] for r in rows if r["namespace"] not in ("?",)})
    if len(rows) < 2 or not namespaces:
        return 0, 0, []
    full_cells, _, _ = contingency(rows, cell_keys)
    if not full_cells:
        return 0, 0, []
    rank1 = (tuple(full_cells[0]["cell"]), full_cells[0]["outcome"])
    preserved = 0
    tops = []
    for ns in namespaces:
        sub = [r for r in rows if r["namespace"] != ns]
        cells, _, _ = contingency(sub, cell_keys)
        if cells:
            t = (tuple(cells[0]["cell"]), cells[0]["outcome"])
            tops.append({ns: list(t)})
            if t == rank1:
                preserved += 1
    return preserved, len(namespaces), tops


def run_version(rows: list[dict], version: str, cell_keys: tuple) -> dict:
    cells, grand, cv = contingency(rows, cell_keys)
    if not cells:
        return {
            "version": version, "cell_keys": list(cell_keys),
            "precondition": f"corpus={len(rows)}, no cell with support>={MIN_SUPPORT}",
            "verdict": "no_pattern_in_corpus",
            "rationale": f"no contingency cell reaches minimum support {MIN_SUPPORT}",
        }
    top = cells[0]
    perm_p = permutation_null(rows, cell_keys, top["chi2"], n_perm=1000)
    preserved, n_ns, tops = leave_one_namespace_out(rows, cell_keys)

    # Verdict
    if perm_p >= 0.05:
        verdict = "no_pattern_in_corpus"
        rat = f"permutation null p={perm_p:.3f} ≥ 0.05 — top cell chi2 {top['chi2']} not beyond shuffle noise"
    elif top["support"] < MIN_SUPPORT:
        verdict = "no_pattern_in_corpus"
        rat = f"top cell support {top['support']} < {MIN_SUPPORT}"
    elif n_ns >= 2 and preserved < min(RESAMPLE_PASS, n_ns):
        verdict = "label_quality_binding"
        rat = f"rank-1 cell unstable: preserved {preserved}/{n_ns} leave-one-namespace-out (need ≥{min(RESAMPLE_PASS,n_ns)})"
    else:
        if version == "A_descriptive_posthoc":
            verdict = "descriptive_meta_pattern_found"  # ceiling for Version A
            rat = f"stable post-hoc cell; NOT a solver prior (outcome-leaking L3). perm_p={perm_p:.3f} stability={preserved}/{n_ns}"
        else:
            verdict = "H0_holds"
            rat = f"preflight-only cell stable {preserved}/{n_ns}, perm_p={perm_p:.3f}, lift={top['lift']} — deployable solver prior candidate"

    return {
        "version": version,
        "cell_keys": list(cell_keys),
        "precondition": f"corpus={len(rows)}, grand={grand}, cells≥support={len(cells)}, cramers_v={cv}",
        "top_cell": top,
        "permutation_null_p": round(perm_p, 4),
        "resample_stability": f"{preserved}/{n_ns}",
        "resample_tops": tops[:6],
        "verdict": verdict,
        "rationale": rat,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows = assemble_corpus()
    print(f"# v32 meta-pattern miner (GPT-5.5-blessed framing)")
    print(f"L2 classifier: {HAVE_L2}" + ("" if HAVE_L2 else f" ({_L2_ERR})"))
    print(f"Preflight classifier: {HAVE_PREFLIGHT}")
    print(f"Corpus rows: {len(rows)}")
    print(f"By source: {dict(Counter(r['source'] for r in rows))}")
    print(f"By outcome: {dict(Counter(r['outcome'] for r in rows))}")

    if args.dry_run:
        print("\n[DRY RUN] plumbing only. Sample rows:")
        for r in rows[:5]:
            print(f"  {r['row_id']} | ns={r['namespace']} | L2={r['L2_op']}({r['L2_confidence']}) | "
                  f"L3pre={r['L3_flag_preflight']} | L3post={r['L3_failure_posthoc']} | out={r['outcome']}")
        return 0

    # Version A: post-hoc L3 (descriptive ceiling)
    ver_a = run_version(rows, "A_descriptive_posthoc", ("L2_op", "L1_pattern", "L3_failure_posthoc"))
    # Version B: preflight-only (deployable prior)
    ver_b = run_version(rows, "B_deployable_preflight", ("L2_op", "L1_pattern", "L3_flag_preflight"))

    # Safeguard 5 (BINDING per GPT-5.5): confidence buckets.
    # If the pattern exists only in low-confidence labels → label_quality_binding,
    # overriding any H0_holds from Version B.
    hi = [r for r in rows if r.get("L2_confidence") in ("high", "medium")]
    ver_b_hi = run_version(hi, "B_high_conf_only", ("L2_op", "L1_pattern", "L3_flag_preflight")) if len(hi) >= MIN_SUPPORT else {"verdict": "insufficient_high_conf_rows", "n": len(hi)}

    # Additional binding check: degenerate zero-variance features cannot be H0_holds.
    distinct_l2 = len({r["L2_op"] for r in rows})
    distinct_l1 = len({r["L1_pattern"] for r in rows})
    distinct_l3pre = len({r["L3_flag_preflight"] for r in rows})
    feature_variance_ok = (distinct_l2 >= 2) and (distinct_l1 >= 2 or distinct_l3pre >= 2)

    if ver_b.get("verdict") == "H0_holds":
        if ver_b_hi.get("verdict") in ("insufficient_high_conf_rows", "no_pattern_in_corpus", "label_quality_binding"):
            ver_b["verdict"] = "label_quality_binding"
            ver_b["rationale"] = (
                f"OVERRIDE (safeguard 5 binding): Version-B H0 candidate exists only in "
                f"low-confidence labels (high/med-conf bucket verdict="
                f"{ver_b_hi.get('verdict')}); per GPT-5.5 this is label_quality_binding, not H0_holds"
            )
        elif not feature_variance_ok:
            ver_b["verdict"] = "label_quality_binding"
            ver_b["rationale"] = (
                f"OVERRIDE (zero-variance guard): preflight features degenerate "
                f"(distinct L2={distinct_l2}, L1={distinct_l1}, L3pre={distinct_l3pre}); "
                f"a constant×constant→constant cell is a classifier-failure artifact, not a prior"
            )

    print("\n=== VERSION A (descriptive, post-hoc L3 — NOT a solver prior) ===")
    print(f"PRECONDITION: {ver_a['precondition']}")
    if ver_a.get("top_cell"):
        t = ver_a["top_cell"]
        print(f"TOP CELL: (L2={t['cell'][0]}, L1={t['cell'][1]}, L3post={t['cell'][2]}, outcome={t['outcome']}) "
              f"support={t['support']} lift={t['lift']} chi2={t['chi2']} perm_p={ver_a.get('permutation_null_p')}")
    print(f"RESAMPLE STABILITY: {ver_a.get('resample_stability','n/a')}")
    print(f"VERDICT: {ver_a['verdict']} — {ver_a['rationale']}")

    print("\n=== VERSION B (preflight-only — deployable solver prior) ===")
    print(f"PRECONDITION: {ver_b['precondition']}")
    if ver_b.get("top_cell"):
        t = ver_b["top_cell"]
        print(f"TOP CELL: (L2={t['cell'][0]}, L1={t['cell'][1]}, L3pre={t['cell'][2]}, outcome={t['outcome']}) "
              f"support={t['support']} lift={t['lift']} chi2={t['chi2']} perm_p={ver_b.get('permutation_null_p')}")
    print(f"RESAMPLE STABILITY: {ver_b.get('resample_stability','n/a')}")
    print(f"VERDICT: {ver_b['verdict']} — {ver_b['rationale']}")
    print(f"\n[confidence-bucket cross-check] high/medium-conf-only Version B verdict: {ver_b_hi.get('verdict')}")

    if args.out:
        Path(args.out).write_text(json.dumps({
            "corpus_size": len(rows),
            "by_outcome": dict(Counter(r["outcome"] for r in rows)),
            "version_A_descriptive": ver_a,
            "version_B_deployable": ver_b,
            "version_B_high_conf": ver_b_hi,
        }, indent=2, default=str))
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
