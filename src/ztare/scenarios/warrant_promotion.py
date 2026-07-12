"""Warrant promotion — mint a stronger warrant on an edge ONLY when a re-executable check passes.

This is what makes the warrant ladder DYNAMIC (Fable C4): a `W2` verbatim-quote becomes a `W1` re-executable
claim when a recomputation is attached and re-runs green; a `W1` becomes a `W0` when a kernel certificate is
attached. The promotion is minted by the CHECK, never by fiat — you cannot *assert* a higher warrant, you must
attach a check that re-executes and passes. This is the graph effect a wager's "survive recheck" outcome earns:
running the experiment promotes the edge, which (under the filtration) raises the thesis strength at a harder
stratum. Deterministic; the check is injected (like the metrology oracle) so importing this never runs anything.
"""
from __future__ import annotations

from ztare.scenarios.argument_kernel import WARRANT_RANK
from ztare.scenarios.governed_types import GovernedEdge, GovernedState

# A check TYPE bounds the warrant it may mint — a recomputation earns W1, a kernel certificate earns W0. Nothing
# here can mint a warrant a passing check of the matching kind does not license.
CHECK_WARRANT = {"recompute": "W1", "kernel_cert": "W0"}


def promote_warrant(governed: GovernedState, *, src: str, kind: str, dst: str, check_type: str,
                    check: "callable", check_ref: str = "") -> dict:
    """Attempt to promote the (src, kind, dst) edge's warrant by RE-RUNNING `check`. `check_type` bounds the
    target warrant (recompute→W1, kernel_cert→W0). Returns {receipt, governed}: the receipt records whether it
    promoted and why (auditable — an auditor can re-run `check_ref`); `governed` is the updated state (unchanged
    if the edge is missing, already at/above target, the check errors, or the check does not pass). Monotone: this
    door only promotes UP the ladder, never demotes. The promotion is minted by the check, not asserted."""
    target = CHECK_WARRANT.get(check_type)
    receipt = {"src": src, "kind": kind, "dst": dst, "check_type": check_type, "check_ref": check_ref,
               "promoted": False, "from": None, "to": target, "reason": ""}
    if target is None:
        receipt["reason"] = f"unknown check type {check_type!r} (allowed: {sorted(CHECK_WARRANT)})"
        return {"receipt": receipt, "governed": governed}
    idx = next((i for i, e in enumerate(governed.edges) if e.src == src and e.kind == kind and e.dst == dst), None)
    if idx is None:
        receipt["reason"] = "edge not found"
        return {"receipt": receipt, "governed": governed}
    current = getattr(governed.edges[idx], "warrant", "W3") or "W3"
    receipt["from"] = current
    if WARRANT_RANK.get(current, 0) >= WARRANT_RANK.get(target, 0):
        receipt["reason"] = f"edge already at {current} (>= {target}) — no promotion"
        return {"receipt": receipt, "governed": governed}
    try:
        passed = bool(check())  # the promotion is minted here — by the check re-executing and passing
    except Exception as exc:  # noqa: BLE001 — a check that errors does not promote (fail-closed)
        receipt["reason"] = f"check errored: {type(exc).__name__}"
        return {"receipt": receipt, "governed": governed}
    if not passed:
        receipt["reason"] = "check did not pass — no promotion (a warrant is never minted by fiat)"
        return {"receipt": receipt, "governed": governed}
    edges = list(governed.edges)
    e = edges[idx]
    edges[idx] = GovernedEdge(e.src, e.kind, e.dst, target)
    receipt["promoted"] = True
    receipt["reason"] = f"{current} -> {target} minted by a passing {check_type} check"
    return {"receipt": receipt, "governed": GovernedState(list(governed.elements), edges)}


def demote_warrant(governed: GovernedState, *, src: str, kind: str, dst: str, to: str = "W3",
                   reason: str = "") -> dict:
    """The DOWN sibling of `promote_warrant`: lower the (src, kind, dst) edge's warrant to `to` (default W3
    proposed-unchecked). Used when a re-executable check FAILS to re-pass, or a warrant EXPIRES past its
    half-life — a warrant that can only ever be minted and never lost would be a ratchet, not evidence.
    Monotone DOWN (only lowers; a no-op if the edge is already at/below `to`, missing, or `to` is unknown).
    Returns {receipt, governed}; the receipt is auditable (records from/to/reason)."""
    target_rank = WARRANT_RANK.get(to)
    receipt = {"src": src, "kind": kind, "dst": dst, "demoted": False, "from": None, "to": to, "reason": ""}
    if target_rank is None:
        receipt["reason"] = f"unknown warrant {to!r} (allowed: {sorted(WARRANT_RANK)})"
        return {"receipt": receipt, "governed": governed}
    idx = next((i for i, e in enumerate(governed.edges) if e.src == src and e.kind == kind and e.dst == dst), None)
    if idx is None:
        receipt["reason"] = "edge not found"
        return {"receipt": receipt, "governed": governed}
    current = getattr(governed.edges[idx], "warrant", "W3") or "W3"
    receipt["from"] = current
    if WARRANT_RANK.get(current, 0) <= target_rank:
        receipt["reason"] = f"edge already at {current} (<= {to}) — no demotion"
        return {"receipt": receipt, "governed": governed}
    edges = list(governed.edges)
    e = edges[idx]
    edges[idx] = GovernedEdge(e.src, e.kind, e.dst, to)
    receipt["demoted"] = True
    receipt["reason"] = reason or f"{current} -> {to}"
    return {"receipt": receipt, "governed": GovernedState(list(governed.elements), edges)}


def _promotions_path(project: str):
    from ztare.common.paths import PROJECTS_DIR
    return PROJECTS_DIR / project / "workspace" / "warrant_promotions.jsonl"


def record_promotion(project: str, receipt: dict) -> None:
    """Append a promotion receipt to the project's audit trail (only successful promotions are worth recording)."""
    import json

    p = _promotions_path(project)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(receipt) + "\n")


def _selftest() -> int:
    from ztare.scenarios.governed_types import GovernedElement

    ev = GovernedElement("e1", "evidence", "a quoted figure")
    th = GovernedElement("t", "thesis", "T")
    g = GovernedState([ev, th], [GovernedEdge("e1", "SUPPORTS", "t", "W2")])

    def _warrant(state):
        return state.edges[0].warrant

    # a passing recompute check promotes W2 -> W1
    r = promote_warrant(g, src="e1", kind="SUPPORTS", dst="t", check_type="recompute",
                        check=lambda: True, check_ref="recompute figure from bound data")
    assert r["receipt"]["promoted"] and r["receipt"]["to"] == "W1" and _warrant(r["governed"]) == "W1", r["receipt"]

    # a FAILING check does not promote — no minting by fiat
    r2 = promote_warrant(g, src="e1", kind="SUPPORTS", dst="t", check_type="recompute", check=lambda: False)
    assert not r2["receipt"]["promoted"] and _warrant(r2["governed"]) == "W2", r2["receipt"]

    # an ERRORING check fails closed
    def _boom():
        raise RuntimeError("recompute unavailable")
    r3 = promote_warrant(g, src="e1", kind="SUPPORTS", dst="t", check_type="recompute", check=_boom)
    assert not r3["receipt"]["promoted"] and "errored" in r3["receipt"]["reason"]

    # an unknown check type is refused
    r4 = promote_warrant(g, src="e1", kind="SUPPORTS", dst="t", check_type="llm_opinion", check=lambda: True)
    assert not r4["receipt"]["promoted"] and "unknown check type" in r4["receipt"]["reason"]

    # a kernel_cert check mints W0; promoting an already-W1 edge to W1 is a no-op
    g1 = promote_warrant(g, src="e1", kind="SUPPORTS", dst="t", check_type="recompute", check=lambda: True)["governed"]
    r5 = promote_warrant(g1, src="e1", kind="SUPPORTS", dst="t", check_type="kernel_cert", check=lambda: True)
    assert r5["receipt"]["promoted"] and _warrant(r5["governed"]) == "W0"
    r6 = promote_warrant(g1, src="e1", kind="SUPPORTS", dst="t", check_type="recompute", check=lambda: True)
    assert not r6["receipt"]["promoted"] and "already at" in r6["receipt"]["reason"]

    # the ladder is DYNAMIC: promoting the edge raises the thesis strength at the harder (re-executable) stratum
    from ztare.scenarios.strength import strength_profile
    before = strength_profile(g)["profile"]
    after = strength_profile(g1)["profile"]
    assert before[1] == 0.0 and after[1] > 0.0, (before, after)  # W1 stratum lights up only after promotion

    print("WARRANT-PROMOTION SELFTEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
