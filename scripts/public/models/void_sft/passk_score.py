#!/usr/bin/env python3
"""World-class pass@k SCORER (design step 1) — runs ON the Lean VPS. Consumes the LIST-valued gens from
sample_vllm.py, kernel-compiles every sample (warm REPL, reject_sorry), and reports the UNBIASED pass@k
(Chen et al. 2021: pass@k = 1 − C(N−c, k)/C(N, k), averaged over targets) for k∈{1,4,8,16,32} PER ARM,
with target-bootstrap 95% CIs and the arm delta. Not greedy pass@1.

  python passk_score.py --gens void_gens_passk_r1.json           # both arms, default k grid
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kernel_check import _splice, _compiles   # reuse the SAME warm-REPL compile + splice (one door)

KS = (1, 4, 8, 16, 32)


def chen_passk(n: int, c: int, k: int) -> float:
    """Unbiased pass@k for a target with c/n compiling samples (Chen 2021). 1.0 if the non-compilers can't fill k."""
    if k > n:
        return float(c > 0)                       # k beyond N: degrade to "any compiled"
    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def score_arm(targets: list, arm_key: str) -> "list[tuple[int, int]]":
    """(N, c) per target — c = # samples that kernel-compile sorry-free."""
    out = []
    for t in targets:
        probe, gold, tgt = t.get("probe") or "", t.get("gold_proof") or "", t.get("target")
        samples = t.get(arm_key) or []
        c = sum(1 for gen in samples if (src := _splice(probe, gold, gen, target=tgt)) and _compiles(src))
        out.append((len(samples), c))
        print(f"  [{arm_key}] {tgt}: {c}/{len(samples)} compile", flush=True)
    return out


def curve(cs: list, ks=KS) -> dict:
    m = max(1, len(cs))
    return {k: round(sum(chen_passk(n, c, k) for n, c in cs) / m, 4) for k in ks}


def bootstrap_ci(cs: list, ks=KS, B: int = 1000) -> dict:
    idx = list(range(len(cs)))
    acc = {k: [] for k in ks}
    for _ in range(B):
        samp = [cs[random.choice(idx)] for _ in idx]
        m = max(1, len(samp))
        for k in ks:
            acc[k].append(sum(chen_passk(n, c, k) for n, c in samp) / m)
    return {k: (round(sorted(acc[k])[int(0.025 * B)], 4), round(sorted(acc[k])[int(0.975 * B)], 4)) for k in ks}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gens", type=Path, required=True)
    ap.add_argument("--arms", default="gen_ft,gen_fewshot")
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    random.seed(a.seed)                            # reproducible bootstrap
    targets = json.loads(a.gens.read_text())
    arms = a.arms.split(",")
    print(f"[passk] {len(targets)} targets · arms={arms}")
    res = {arm: score_arm(targets, arm) for arm in arms}
    report = {"n_targets": len(targets), "arms": {}}
    for arm in arms:
        cs = res[arm]
        report["arms"][arm] = {"pass@k": curve(cs), "ci95": {k: v for k, v in bootstrap_ci(cs, B=a.boot).items()},
                               "compilers_per_target": cs}
    # arm delta (adapter − fewshot) per k, with a bootstrap CI on the DIFFERENCE (the actual claim)
    if "gen_ft" in res and "gen_fewshot" in res:
        ft, fs = res["gen_ft"], res["gen_fewshot"]
        idx = list(range(len(ft)))
        dboot = {k: [] for k in KS}
        for _ in range(a.boot):
            ii = [random.choice(idx) for _ in idx]
            for k in KS:
                d = (sum(chen_passk(*ft[i], k) for i in ii) - sum(chen_passk(*fs[i], k) for i in ii)) / max(1, len(ii))
                dboot[k].append(d)
        report["delta_ft_minus_fewshot"] = {
            k: {"mean": round(curve(ft)[k] - curve(fs)[k], 4),
                "ci95": (round(sorted(dboot[k])[int(0.025 * a.boot)], 4), round(sorted(dboot[k])[int(0.975 * a.boot)], 4))}
            for k in KS}
    print(json.dumps(report, indent=2))
    out = a.gens.with_suffix(".passk.json")
    out.write_text(json.dumps(report, indent=2))
    print(f"[passk] wrote {out}")
    # headline: is the adapter delta's CI above 0 at pass@8/16? (the pre-registered claim)
    if "delta_ft_minus_fewshot" in report:
        for k in (8, 16):
            lo = report["delta_ft_minus_fewshot"][k]["ci95"][0]
            print(f"[passk] pass@{k} adapter−fewshot delta CI low = {lo}  → {'LIFT (CI>0)' if lo > 0 else 'not significant'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
