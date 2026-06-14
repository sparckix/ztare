#!/usr/bin/env python3
"""Dawid–Skene judge-reliability estimation (#116, from the apparatus isomorphism run — crowdsourcing
statistics): the faithfulness firewall aggregates N LLM judges by EQUAL-WEIGHT majority (#105). With no ground
truth, the principled upgrade is Dawid–Skene EM: treat the true verdict per item as a LATENT variable, jointly
estimate each judge's SENSITIVITY (P(yes|true-yes)) and SPECIFICITY (P(no|true-no)) and the per-item posterior —
so a consistently-flaky judge is automatically down-weighted, without an oracle.

PURE math (no LLM, no IO) — the data source is the faithfulness store's accumulated verdicts (default-on since
2026-06-12); WIRING into the majority-of-N vote is the follow-up once enough verdict history accrues. Binary
verdicts; missing votes allowed (a judge needn't see every item).

  python -m ztare.leanmill.solver.judge_reliability --selftest
"""
from __future__ import annotations

from typing import Optional


def dawid_skene(votes: "dict[str, dict[str, bool]]", *, iters: int = 30,
                prior: float = 0.5, smooth: float = 1.0) -> "Optional[dict]":
    """EM over binary votes. `votes[judge][item] = bool`. Returns
    {posterior: {item: P(true)}, judges: {judge: {sensitivity, specificity, n}}, iterations}
    or None when there is nothing to estimate (<2 judges or no items). Laplace-smoothed (`smooth`) so a
    degenerate judge never yields 0/1 certainty; `prior` is the class prior for the latent verdict."""
    judges = sorted(votes)
    items = sorted({i for j in judges for i in votes[j]})
    if len(judges) < 2 or not items:
        return None
    # init: per-item posterior = the equal-weight majority (the current #105 behaviour as the EM seed)
    post: "dict[str, float]" = {}
    for it in items:
        vs = [votes[j][it] for j in judges if it in votes[j]]
        post[it] = (sum(vs) + smooth * prior) / (len(vs) + smooth) if vs else prior
    sens: "dict[str, float]" = {}
    spec: "dict[str, float]" = {}
    it_count = 0
    for it_count in range(1, iters + 1):
        # M-step: judge confusion from the soft labels
        for j in judges:
            tp = fn = tn = fp = 0.0
            for it, v in votes[j].items():
                p = post[it]
                if v:
                    tp += p; fp += (1 - p)
                else:
                    fn += p; tn += (1 - p)
            sens[j] = (tp + smooth) / (tp + fn + 2 * smooth)
            spec[j] = (tn + smooth) / (tn + fp + 2 * smooth)
        # E-step: per-item posterior via Bayes over the (assumed-independent) judges
        new_post: "dict[str, float]" = {}
        moved = 0.0
        for it in items:
            lt = prior; lf = 1 - prior
            for j in judges:
                if it not in votes[j]:
                    continue
                if votes[j][it]:
                    lt *= sens[j]; lf *= (1 - spec[j])
                else:
                    lt *= (1 - sens[j]); lf *= spec[j]
            p = lt / (lt + lf) if (lt + lf) > 0 else prior
            moved = max(moved, abs(p - post[it]))
            new_post[it] = p
        post = new_post
        if moved < 1e-6:
            break
    return {"posterior": post,
            "judges": {j: {"sensitivity": round(sens[j], 4), "specificity": round(spec[j], 4),
                           "n": len(votes[j])} for j in judges},
            "iterations": it_count}


def weighted_verdict(votes_for_item: "dict[str, bool]", judges: "dict[str, dict]",
                     *, prior: float = 0.5) -> "tuple[bool, float]":
    """Score ONE new item with LEARNED judge reliabilities (the drop-in for the equal-weight majority once
    wired): returns (verdict, posterior). Judges absent from the learned table count as uninformative (0.5)."""
    lt = prior; lf = 1 - prior
    for j, v in votes_for_item.items():
        s = (judges.get(j) or {}).get("sensitivity", 0.5)
        c = (judges.get(j) or {}).get("specificity", 0.5)
        if v:
            lt *= s; lf *= (1 - c)
        else:
            lt *= (1 - s); lf *= c
    p = lt / (lt + lf) if (lt + lf) > 0 else prior
    return p >= 0.5, round(p, 4)


def _selftest() -> int:
    import random
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    # SEPARATE rng streams per judge (a shared stream interleaves draws and skews realized accuracies —
    # the first version of this test generated a "0.78" judge at 0.66 empirical and then asserted against the
    # NOMINAL accuracy: a broken test, not a broken estimator). Two strong + one coin = identifiable.
    rt = random.Random(1)
    truth = {f"i{k}": rt.random() < 0.5 for k in range(200)}

    def _mk(seed, a):
        r = random.Random(seed)
        return {it: (tv if r.random() < a else not tv) for it, tv in truth.items()}

    votes = {"g1": _mk(11, 0.9), "g2": _mk(12, 0.9), "coin": _mk(13, 0.5)}
    emp = {j: sum(votes[j][it] == tv for it, tv in truth.items()) / len(truth) for j in votes}
    r = dawid_skene(votes, iters=100)
    ok("returns a result", r is not None)
    js = r["judges"]
    rel = {j: (js[j]["sensitivity"] + js[j]["specificity"]) / 2 for j in js}
    ok("recovers the EMPIRICAL reliability ordering (strong judges > coin)",
       rel["g1"] > rel["coin"] and rel["g2"] > rel["coin"]
       and abs(rel["g1"] - emp["g1"]) < 0.12 and abs(rel["g2"] - emp["g2"]) < 0.12)
    ds_acc = sum((r["posterior"][it] >= 0.5) == tv for it, tv in truth.items()) / len(truth)
    maj_acc = sum((sum(votes[j][it] for j in votes) >= 2) == tv for it, tv in truth.items()) / len(truth)
    ok(f"EM >= equal-weight majority (ds={ds_acc:.2f} vs maj={maj_acc:.2f})", ds_acc >= maj_acc)
    v, p = weighted_verdict({"g1": True, "g2": True, "coin": False}, js)
    ok("weighted_verdict follows the reliable judges over the coin", v is True and p > 0.5)
    ok("degenerate input ⇒ None (fail-safe)", dawid_skene({"solo": {"i": True}}) is None)
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
