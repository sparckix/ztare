#!/usr/bin/env python3
"""tier_scoreboard.py — tier-tagged, NEVER-merged scoreboard + gate eval.

Allowed build (per the 2026-05-16 freeze directive, item #2). Thin
composition of gp233_adversary_yield_decomp's row classifier — NO new
measurement logic. Reads one or more (--tier N --result FILE) pairs;
prints a per-tier table that is never aggregated across tiers; evaluates
the Tier-2 / Tier-3 pass gates. Enforces failure-mode-1 (tier leakage):
there is no cross-tier total.

Per-tier columns: closures | exact_gaps(incl prover_self_gap) |
falsifiers | consequence_exposures | invalid_or_retired |
false_ratifications | wrong_target_kind.

Gates:
  Tier-2 pass: (closures>=2 OR exact_gaps+falsifiers>=5)
               AND false_ratifications==0 AND wrong_target_kind==0
  Tier-2 strong: closures>=5 AND exact_gaps+falsifiers>=5 AND above zeros
  Tier-3 pass: (closures+exact_gaps+falsifiers)>=3 of the packet
               AND false_ratifications==0 AND wrong_target_kind==0
"""
from __future__ import annotations
import argparse, json, importlib.util, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
GP233 = REPO / "scripts/public/control/gp233_adversary_yield_decomp.py"


def _classify_fn():
    spec = importlib.util.spec_from_file_location("gp233", GP233)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.classify


def _counts(result_file: Path, classify) -> dict:
    c = {"closures": 0, "exact_gaps": 0, "falsifiers": 0,
         "consequence_exposures": 0, "invalid_or_retired": 0,
         "false_ratifications": 0, "wrong_target_kind": 0, "rows": 0}
    if not result_file.exists():
        return c
    for ln in result_file.read_text().splitlines():
        if not ln.strip():
            continue
        r = classify(ln)
        if not r:
            continue
        _, cls = r.split("\t")
        c["rows"] += 1
        if cls == "genuine_novel_closure":
            c["closures"] += 1
        elif cls in ("honest_gap_or_pinned_port_fail", "prover_self_gap_valid"):
            c["exact_gaps"] += 1
        elif cls == "single_lemma_rejected":
            # governance correctly refused credit — not a closure, not a
            # gap; it is an anti-laundering rejection (false-ratify stays 0)
            c.setdefault("single_lemma_rejected", 0)
            c["single_lemma_rejected"] += 1
        elif cls == "pinned_env_broken_BLOCKING":
            c["invalid_or_retired"] += 1
    return c


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", action="append", default=[], type=int)
    ap.add_argument("--result", action="append", default=[])
    a = ap.parse_args()
    if len(a.tier) != len(a.result) or not a.tier:
        print("usage: --tier N --result FILE  (repeatable, paired)")
        return 2
    classify = _classify_fn()

    per_tier = {}
    for t, rf in zip(a.tier, a.result):
        per_tier.setdefault(t, []).append(Path(rf))

    out = {"never_merged": True, "tiers": {}}
    print("=" * 64)
    print("TIER-TAGGED SCOREBOARD (never merged — no cross-tier total)")
    print("=" * 64)
    for t in sorted(per_tier):
        agg = {}
        for rf in per_tier[t]:
            c = _counts(rf, classify)
            for k, v in c.items():
                agg[k] = agg.get(k, 0) + v
        gate = None
        if t == 2:
            base = (agg.get("false_ratifications", 0) == 0
                    and agg.get("wrong_target_kind", 0) == 0)
            eg = agg.get("exact_gaps", 0) + agg.get("falsifiers", 0)
            gate = {
                "tier2_pass": bool(base and (agg.get("closures", 0) >= 2 or eg >= 5)),
                "tier2_strong": bool(base and agg.get("closures", 0) >= 5 and eg >= 5),
            }
        elif t == 3:
            base = (agg.get("false_ratifications", 0) == 0
                    and agg.get("wrong_target_kind", 0) == 0)
            yld = (agg.get("closures", 0) + agg.get("exact_gaps", 0)
                   + agg.get("falsifiers", 0))
            gate = {"tier3_pass": bool(base and yld >= 3)}
        out["tiers"][t] = {"counts": agg, "gate": gate}
        print(f"\n[TIER {t}]  rows={agg.get('rows',0)}")
        for k in ("closures", "exact_gaps", "falsifiers",
                  "consequence_exposures", "invalid_or_retired",
                  "single_lemma_rejected", "false_ratifications",
                  "wrong_target_kind"):
            if k in agg:
                print(f"    {k:24s} {agg[k]}")
        if gate:
            print(f"    GATE: {gate}")
    print("\n" + "=" * 64)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
