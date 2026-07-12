"""Belief ledger — "what would you have to believe?" (Rivkin), COMPUTED, never generated. The conditions a
decision rests on are the argument kernel's MINIMAL CORES (smallest assumption-sets that, if they fail, flip the
verdict) plus the DOMINATORS (conditions on every support path — load-bearing everywhere). This is the
overfitting firewall: an LLM never *invents* the belief list — the ATMS enumerates it off the graph the human
built. The moment you let a model brainstorm "what you'd have to believe," you manufacture plausible unchecked
conditions that inflate the map; here the beliefs ARE the argument's structure.

Each condition carries its current BACKING TIER (proven / reproducible / cited / unchecked — the same plain
vocabulary as everywhere). The RISKS are the load-bearing conditions still only unchecked/cited: the beliefs you
are betting on without checking. "Next-best experiment" then falls out — the cheapest test that raises the
weakest load-bearing condition's tier (a recheck, or gathering cited evidence). No prediction, no generation.
"""
from __future__ import annotations

from ztare.scenarios.tiers import PROFILE_TIER as _PROFILE_TIER, TIER_RANK as _TIER_RANK  # noqa: E402 — one vocab

_EPS = 1e-6


def _tier_of(profile: "list[float]") -> str:
    """The best (hardest) tier at which a condition has any support — its backing quality."""
    p = list(profile or [0.0, 0.0, 0.0, 0.0])
    return next((_PROFILE_TIER[i] for i in range(len(p)) if float(p[i]) > _EPS), "unchecked")


def _firm_up(tier: str) -> str:
    """The cheapest way to raise a weakly-backed condition — plain language, points at existing doors."""
    if tier == "unchecked":
        return "cite a source, or attach a recompute (recheck) — it is backing nothing checkable yet"
    if tier == "cited":
        return "attach a recompute so it recomputes from the data (recheck) — today it rests on a quote"
    return "already reproducible or proven — nothing cheaper to do"


def belief_ledger(governed) -> dict:
    """The 'what would you have to believe' table. Returns {conditions, risks, cores, dominators, next_experiment}
    — all read off the argument graph (minimal cores + dominators + backing tiers). Deterministic, no LLM."""
    from ztare.scenarios.argument_kernel import dominators, minimal_cores
    from ztare.scenarios.strength import strength_profile

    cores = minimal_cores(governed)
    doms = set(dominators(governed))
    per = strength_profile(governed).get("per_node") or {}

    # The conditions = every id that appears in a core (a way the decision could be right) or is a dominator.
    ids = sorted({m for core in cores for m in core} | doms)
    rows: "list[dict]" = []
    for cid in ids:
        el = governed.by_id(cid)
        tier = _tier_of(per.get(cid))
        n_in = sum(1 for c in cores if cid in c)
        rows.append({"id": cid, "text": el.text if el else cid, "kind": el.kind if el else "",
                     "tier": tier, "load_bearing_everywhere": cid in doms,
                     "in_cores": n_in, "of_cores": len(cores)})
    # Order: load-bearing-everywhere first, then weakest backing (the risks bubble to the top).
    rows.sort(key=lambda r: (not r["load_bearing_everywhere"], _TIER_RANK[r["tier"]], r["id"]))

    # RISKS = load-bearing conditions still only unchecked/cited — the beliefs bet on without checking.
    risks = [r for r in rows if r["load_bearing_everywhere"] and _TIER_RANK[r["tier"]] <= 1]

    # Next-best experiment = firm up the single weakest load-bearing condition (fall back to the weakest of any).
    pool = risks or [r for r in rows if _TIER_RANK[r["tier"]] <= 1]
    weakest = min(pool, key=lambda r: (_TIER_RANK[r["tier"]], not r["load_bearing_everywhere"])) if pool else None
    next_experiment = None
    if weakest:
        next_experiment = {"target": weakest["id"], "text": weakest["text"], "tier": weakest["tier"],
                           "do": _firm_up(weakest["tier"])}

    return {"conditions": rows, "risks": risks, "cores": [sorted(c) for c in cores],
            "dominators": sorted(doms), "next_experiment": next_experiment}


def _selftest() -> int:
    from ztare.scenarios.governed_types import GovernedEdge, GovernedElement, GovernedState

    # thesis grounded through ONE intermediate claim c (a dominator), c backed only by an unchecked edge.
    els = [GovernedElement("t", "thesis", "the roadmap bet pays off"),
           GovernedElement("c", "claim", "users will adopt the guided flow"),
           GovernedElement("e", "evidence", "a stated expectation")]
    g = GovernedState(els, [GovernedEdge("e", "SUPPORTS", "c", "W3"), GovernedEdge("c", "SUPPORTS", "t", "W3")])
    led = belief_ledger(g)

    ids = {r["id"] for r in led["conditions"]}
    assert "c" in ids, led                                   # the intermediate claim is a load-bearing condition
    crow = next(r for r in led["conditions"] if r["id"] == "c")
    assert crow["load_bearing_everywhere"], crow             # c is a dominator (whole conclusion routes through it)
    assert crow["tier"] == "unchecked", crow                 # and it is bet on blind
    assert any(r["id"] == "c" for r in led["risks"]), led["risks"]
    assert led["next_experiment"] and led["next_experiment"]["target"] == "c", led["next_experiment"]

    print("BELIEF-LEDGER SELFTEST PASSED",
          {"risks": [r["id"] for r in led["risks"]], "next": led["next_experiment"]["target"]})
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
