#!/usr/bin/env python3
"""Step 1b (cold-review): PURE-PYTHON, zero-Lean, rerunnable-for-free
cost-accounted policy replay over a VERIFIED probe_matrix.json.

The matrix is the environment oracle: probing (cand,action) returns its
recorded outcome. A POLICY may use ONLY the outcomes of probes it has
ALREADY spent budget on (strict no-peek). EVERY scoring probe counts.
A row 'succeeds' at probe t iff that probe is a GENUINE governance
closure OR a clean exact_gap (single_lemma / axiom_smuggled / unverified
NEVER count — Path-B governance is authoritative).

Policies: P0 random (1000 shuffles, mean) ; P1 BM25/text rank ;
P2 source-rank (= text rank here unless a source provided) ;
P3 action-major sweep (all cands × act0, then × act1, …) ;
P4 kernel-FEEDBACK-sequential (NO pre-probe signal; adapts only on
   already-paid outcomes: drop a candidate after its `exact`/`apply`
   fails; after any `simp`-family progress prefer `simp`-family; else
   round-robin) ;
P5 oracle (upper bound ONLY — never the claim).

Primary metric: median failed-probes-before-first success (lower=better),
∞ if never. Secondary: closed_or_exact_gap@{3,5,10}, false_ratify,
wrong_kind. Verdict per the frozen gate.
"""
from __future__ import annotations
import argparse, json, random, statistics
from pathlib import Path

ORD_ACT = ["exact {C}", "apply {C}", "simp only [{C}]", "rw [{C}]",
           "exact?", "simp", "simp_all",
           "ext i j <;> simp only [{C}]", "ext i <;> simp [{C}]",
           "ext i j <;> simp_all", "constructor <;> simp_all",
           "simp only [{C}] <;> exact?", "rw [{C}] <;> simp",
           "refine {C} ?_ <;> exact?"]


def success(rec):
    if rec["lean_result"] == "closed" and rec["governance_verdict"] == "genuine":
        return "closure"
    if rec["lean_result"] == "exact_gap":
        return "exact_gap"
    return None


def grid(rowrec):
    g = {}
    for r in rowrec["probes"]:
        g[(r["candidate_id"], r["action_id"])] = r
    return g


def walk(seq, g, budget):
    """seq = ordered list of (cand,action) keys. Return (failed_before,
    hit_at, false_ratify, wrong_kind). Each examined probe costs 1."""
    fr = wk = 0
    for i, key in enumerate(seq[:budget], 1):
        rec = g.get(key)
        if rec is None:
            continue
        s = success(rec)
        # false-ratify = lean closed but governance NOT genuine yet some
        # arm would have credited it (we never credit → fr counts the
        # governance saves, i.e. laundering attempts blocked)
        if rec["lean_result"] == "closed" and rec["governance_verdict"] \
                not in ("genuine",):
            fr += 1
        if s == "closure" or s == "exact_gap":
            return (i - 1), i, fr, wk
    return budget, None, fr, wk


def p_random(keys, g, budget, n=1000):
    rng = random.Random(7)
    fb = []
    for _ in range(n):
        s = list(keys); rng.shuffle(s)
        f, hit, _, _ = walk(s, g, budget)
        fb.append(f if hit else budget + 1)
    return fb


def p_fixed(keys, g, budget):
    f, hit, fr, wk = walk(keys, g, budget)
    return (f if hit else budget + 1), fr, wk


def kernel_seq(pool, acts, g, budget):
    """No pre-probe signal. Adaptive on PAID outcomes only."""
    tried = set()
    cand_dead = set()
    prefer_simp = False
    order = []
    # round-robin candidates × actions, but adapt
    ci = 0
    while len(order) < len(pool) * len(acts):
        progressed = False
        for c in pool:
            if c in cand_dead:
                continue
            acts_o = (["simp only [{C}]", "simp", "simp_all", "exact {C}",
                       "apply {C}", "rw [{C}]", "exact?"] if prefer_simp
                      else acts)
            for a in acts_o:
                key = (c if "{C}" in a else None, a)
                if key in tried:
                    continue
                tried.add(key); order.append(key)
                rec = g.get(key)
                if rec is not None:
                    lr = rec["lean_result"]
                    if a in ("exact {C}", "apply {C}") and lr == "failed":
                        cand_dead.add(c)
                    if "simp" in a and lr in ("closed", "exact_gap"):
                        prefer_simp = True
                break
        ci += 1
        if ci > len(pool) * len(acts) + 2:
            break
    # append any unvisited keys (incl. dead-cand ones) so budget can run
    for c in pool:
        for a in acts:
            k = (c if "{C}" in a else None, a)
            if k not in tried:
                order.append(k); tried.add(k)
    f, hit, fr, wk = walk(order, g, budget)
    return (f if hit else budget + 1), fr, wk


def oracle(keys, g, budget):
    best = budget + 1
    for i, key in enumerate(keys, 1):
        if success(g.get(key, {})):
            return 0  # an oracle reaches it first probe
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--matrix", required=True)
    ap.add_argument("--budget", type=int, default=24)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    M = json.load(open(a.matrix))
    rows = {k: v for k, v in M["rows"].items() if "probes" in v}
    pol = {p: {"failed_before": [], "false_ratify": 0, "wrong_kind": 0,
               "hit@3": 0, "hit@5": 0, "hit@10": 0, "n": 0}
           for p in ("P0_random", "P1_bm25", "P2_source", "P3_action_sweep",
                     "P4_kernel_seq", "P5_oracle")}
    in_grid_closures = 0
    for rid, rr in rows.items():
        g = grid(rr)
        pool = rr["pool"]
        in_grid_closures += rr.get("n_closed_genuine", 0) + \
            rr.get("n_exact_gap", 0)
        # candidate keys per policy
        bm25 = sorted(pool, key=lambda c: next(
            (p["candidate_source_rank"] for p in rr["probes"]
             if p["candidate_id"] == c
             and p["candidate_source_rank"] is not None), 1e9))
        def seq_for(cands):
            s = []
            for c in cands:
                for act in ORD_ACT:
                    s.append((c if "{C}" in act else None, act))
            return s
        action_sweep = [(c if "{C}" in act else None, act)
                        for act in ORD_ACT for c in pool]
        allkeys = list(g.keys())
        for name, val in (
            ("P1_bm25", p_fixed(seq_for(bm25), g, a.budget)),
            ("P2_source", p_fixed(seq_for(bm25), g, a.budget)),
            ("P3_action_sweep", p_fixed(action_sweep, g, a.budget)),
            ("P4_kernel_seq", kernel_seq(pool, ORD_ACT, g, a.budget)),
        ):
            fb, fr, wk = val
            d = pol[name]; d["failed_before"].append(fb)
            d["false_ratify"] += fr; d["wrong_kind"] += wk; d["n"] += 1
            for kk, t in (("hit@3", 3), ("hit@5", 5), ("hit@10", 10)):
                d[kk] += 1 if fb < t else 0
        rb = p_random(allkeys, g, a.budget)
        dr = pol["P0_random"]
        dr["failed_before"].append(statistics.mean(rb)); dr["n"] += 1
        for kk, t in (("hit@3", 3), ("hit@5", 5), ("hit@10", 10)):
            dr[kk] += sum(1 for x in rb if x < t) / len(rb)
        do = pol["P5_oracle"]
        ofb = oracle(allkeys, g, a.budget)
        do["failed_before"].append(ofb); do["n"] += 1
        # FIX (false-negative audit): oracle hit@ was never accumulated
        # → spurious oracle soeg=0.0 < real policies (logical
        # contradiction). Cosmetic for the P1–P4 verdict but a wrong
        # ledgered upper-bound is laundering-adjacent. Accumulate it.
        for kk, t in (("hit@3", 3), ("hit@5", 5), ("hit@10", 10)):
            do[kk] += 1 if ofb < t else 0

    def med(p):
        xs = pol[p]["failed_before"]
        return round(statistics.median(xs), 2) if xs else None

    n = max(1, len(rows))
    base = min(med("P1_bm25") or 1e9, med("P3_action_sweep") or 1e9,
               med("P0_random") or 1e9)
    k = med("P4_kernel_seq")
    soeg5_base = max(pol["P1_bm25"]["hit@5"], pol["P3_action_sweep"]["hit@5"],
                     pol["P0_random"]["hit@5"]) / n
    soeg5_k = pol["P4_kernel_seq"]["hit@5"] / n
    PASS = bool(k is not None and base < 1e9 and (
        (base / max(k, 1e-9)) >= 2.0 or (soeg5_k - soeg5_base) >= 0.20)
        and pol["P4_kernel_seq"]["false_ratify"] == 0
        and pol["P4_kernel_seq"]["wrong_kind"] == 0)
    verdict = ("rung1_live" if PASS else
               "apparatus_blocked" if in_grid_closures == 0 else
               "rung1_killed")
    rep = {"budget": a.budget, "n_rows": len(rows),
           "in_grid_closures": in_grid_closures,
           "median_failed_before": {p: med(p) for p in pol},
           "soeg@5": {p: round(pol[p]["hit@5"] / n, 3) for p in pol},
           "soeg@3": {p: round(pol[p]["hit@3"] / n, 3) for p in pol},
           "soeg@10": {p: round(pol[p]["hit@10"] / n, 3) for p in pol},
           "false_ratify": {p: pol[p]["false_ratify"] for p in pol},
           "pass_gate": {"baseline_med (min P0/P1/P3)": base,
                         "kernel_med P4": k, "soeg5_base": round(soeg5_base, 3),
                         "soeg5_kernel": round(soeg5_k, 3), "PASS": PASS},
           "VERDICT": verdict,
           "note": "P5 oracle = upper bound only, never the claim; "
                   "single_lemma/axiom/unverified NEVER counted (Path-B "
                   "governance authoritative); all scoring probes counted"}
    # Tier separation (cold-roadmap HARD requirement: NO aggregate claim
    # across tiers). EVIDENCE-based: a row whose only closures are
    # single_lemma is Tier-0/1 (trivial at pin), NOT Tier-2 — never lump
    # it with a genuine Tier-2 closure.
    def _tier(rr):
        if rr.get("n_closed_genuine", 0) > 0:
            return "T2_escape_route_genuine"
        gv = {p.get("governance_verdict") for p in rr["probes"]}
        if "single_lemma" in gv:
            return "T0_1_single_lemma_trivial_at_pin"
        return "T2_escape_route_unclosed"
    tiers = {}
    for rid, rr in rows.items():
        t = _tier(rr)
        d = tiers.setdefault(t, {"rows": [], "genuine": 0})
        d["rows"].append(rid)
        d["genuine"] += rr.get("n_closed_genuine", 0)
    rep["tiers"] = {t: {"n": len(v["rows"]), "rows": v["rows"],
                        "genuine_closures": v["genuine"]}
                    for t, v in tiers.items()}
    rep["NO_AGGREGATE_ACROSS_TIERS"] = (
        "VERDICT/pass_gate are NOT a cross-tier success rate; a Tier-0/1 "
        "single-lemma row's outcome must never be reported with a genuine "
        "Tier-2 closure. Per-tier breakdown above is authoritative.")
    assert "T2" in "".join(rep["tiers"]) or not rows, "tier tagging failed"
    Path(a.out).write_text(json.dumps(rep, indent=1))
    md = a.out.rsplit(".", 1)[0] + ".md"
    Path(md).write_text(
        f"# Rung-1 cost-accounted offline replay\n\n"
        f"VERDICT: **{verdict}**\n\n"
        f"- rows={len(rows)} in_grid_closures={in_grid_closures} "
        f"budget={a.budget}\n"
        f"- median failed-before: {rep['median_failed_before']}\n"
        f"- closed_or_exact_gap@5: {rep['soeg@5']}\n"
        f"- pass_gate: {rep['pass_gate']}\n"
        f"- false_ratify: {rep['false_ratify']}\n\n"
        f"P5 oracle is an upper bound only. Kernel = P4_kernel_seq "
        f"(strict no-peek, cost-accounted). Path-B governance "
        f"authoritative (single_lemma/axiom/unverified never counted).\n")
    print(json.dumps(rep, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
