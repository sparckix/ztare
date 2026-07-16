"""Research-map signals — the live read of a perpetually-contested argument graph (Fable's B-lane).

When nothing is ever settled, the useful signals are not a verdict but: how many independent legs the thesis
stands on, which two hard facts are in tension, which open challenges most threaten it, and what moved since last
run. All deterministic and prior-free — they read the same warrant-filtration strength as `strength.py`.
"""
from __future__ import annotations

from ztare.scenarios.argument_kernel import _ATTACK, _SUPPORT, _targets
from ztare.scenarios.governed_types import GovernedEdge, GovernedElement, GovernedState

_CHALLENGE = _ATTACK + ("CHALLENGES",)
_FINDING_KINDS = ("tension", "gap")


def corroboration_independence(governed: GovernedState) -> "list[int]":
    """B4: how many INDEPENDENT sources (post-lineage collapse) back the thesis at each warrant stratum
    (s0..s3). One source quoted five times — or five sources all deriving from one — counts once. The honest
    'how many legs does it stand on', distinct from raw strength (which one loud source can inflate)."""
    from ztare.scenarios.argument_kernel import WARRANT_RANK
    from ztare.scenarios.strength import _STRATA, _lineage_sources

    source_of = _lineage_sources(governed)
    targets = set(_targets(governed))
    # the thesis's support chain (so a source two hops away still counts as backing it)
    backing = set(targets)
    changed = True
    while changed:
        changed = False
        for e in governed.edges:
            if e.kind in _SUPPORT and e.dst in backing and e.src not in backing:
                backing.add(e.src)
                changed = True
    out: "list[int]" = []
    for k in range(_STRATA):
        min_rank = _STRATA - 1 - k
        groups = {source_of.get(e.src, e.src) for e in governed.edges
                  if e.kind in _SUPPORT and e.dst in backing
                  and WARRANT_RANK.get(getattr(e, "warrant", "W3") or "W3", 0) >= min_rank}
        out.append(len(groups))
    return out


def crux_pairs(governed: GovernedState, *, min_rank: int = 2) -> "list[dict]":
    """B2: pairs of CHECKABLE (W0/W1 by default) nodes in direct conflict — the two hard artifacts that cannot
    both survive. Generalizes cores from 'what the thesis rests on' to 'which two facts are in tension'; that
    pair IS the next experiment. Restricted to `min_rank` so it flags real conflicts, not opinion clashes."""
    from ztare.scenarios.argument_kernel import WARRANT_RANK
    from ztare.scenarios.strength import strength_profile

    s3 = {nid: prof[-1] for nid, prof in strength_profile(governed)["per_node"].items()}
    text = {e.id: e.text for e in governed.elements}
    seen: "set[frozenset]" = set()
    cruxes: "list[dict]" = []
    for e in governed.edges:
        if e.kind in _ATTACK and WARRANT_RANK.get(getattr(e, "warrant", "W3") or "W3", 0) >= min_rank:
            key = frozenset((e.src, e.dst))
            if key in seen or s3.get(e.src, 0.0) <= 0.0 or s3.get(e.dst, 0.0) <= 0.0:
                continue  # both sides must actually be standing for it to be a live crux
            seen.add(key)
            cruxes.append({"a": e.src, "b": e.dst, "relation": e.kind,
                           "a_text": text.get(e.src, e.src)[:80], "b_text": text.get(e.dst, e.dst)[:80]})
    return cruxes


def _pin_as_evidence(governed: GovernedState, node_id: str) -> GovernedState:
    """A counterfactual copy where one node is treated as leaf evidence (base strength 1) — 'what if this
    challenge became evidence-backed?'. Edges unchanged."""
    els = [GovernedElement(e.id, "evidence" if e.id == node_id else e.kind, e.text) for e in governed.elements]
    return GovernedState(els, list(governed.edges))


def challenge_queue(governed: GovernedState) -> "list[dict]":
    """D4: open challenges ranked by DRAG — how far the thesis strength would fall if that challenge became
    evidence-backed. The load-bearing contests to resolve first. (Staleness × drag once run-history accumulates;
    drag alone for now — an honest ordering that needs no history.)"""
    from ztare.scenarios.strength import strength_profile

    base_s3 = strength_profile(governed)["profile"][-1]
    ruled = {e.src for e in governed.edges if e.kind == "RULED_OUT"}
    text = {e.id: e.text for e in governed.elements}
    rows: "list[dict]" = []
    for c in [el.id for kind in _FINDING_KINDS for el in governed.of_kind(kind)]:
        if c in ruled:
            continue
        drag = round(base_s3 - strength_profile(_pin_as_evidence(governed, c))["profile"][-1], 4)
        if drag > 0.0:
            rows.append({"id": c, "drag": drag, "text": text.get(c, c)[:80]})
    return sorted(rows, key=lambda r: -r["drag"])


# ── B1: strength trajectory (forward-accumulating — "what moved since last run") ────────────────────────────
def _history_path(project: str, repo_root=None):
    if repo_root is None:
        from ztare.common.paths import PROJECTS_DIR
        projects_dir = PROJECTS_DIR
    else:
        from pathlib import Path
        projects_dir = Path(repo_root) / "projects"
    return projects_dir / project / "workspace" / "strength_history.jsonl"


def snapshot_strength(project: str, governed: GovernedState, *, now: str = "", repo_root=None) -> dict:
    """Append the compiled decision posture to the existing strength ledger when its fingerprint moves."""
    import hashlib
    import json
    from datetime import datetime, timezone

    from ztare.scenarios.decision_state import compile_decision_state
    from ztare.scenarios.strength import strength_profile

    sp = strength_profile(governed)
    decision = compile_decision_state(governed).to_payload()
    graph_material = {
        "nodes": sorted((element.id, element.kind, element.text, element.source_key)
                        for element in governed.elements),
        "edges": sorted((edge.src, edge.kind, edge.dst, edge.warrant) for edge in governed.edges),
    }
    graph_hash = hashlib.sha256(json.dumps(graph_material, ensure_ascii=False, separators=(",", ":"))
                                .encode("utf-8")).hexdigest()
    rec = {
        "timestamp": now or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "profile": sp["profile"],
        "status": sp["status"],
        "graph": {"hash": graph_hash, "nodes": len(governed.elements), "edges": len(governed.edges)},
        "decision": {
            key: decision.get(key)
            for key in ("fingerprint", "status", "headline", "reason", "coverage", "warrant_ceiling",
                        "hinge", "next_test", "open_test_count")
        },
    }
    p = _history_path(project, repo_root)
    # DEDUP (2026-07-10): skip an unchanged (profile, status) so calling this on every workbench read records a
    # real MOVE (after a wager/recheck/reingest recompile) — never refresh-spam a fabricated series, and never
    # bump the project mtime (which would needlessly invalidate the snapshot cache) when nothing moved.
    if p.is_file():
        lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if lines:
            try:
                last = json.loads(lines[-1])
                last_fingerprint = ((last.get("decision") or {}).get("fingerprint"))
                last_graph_hash = ((last.get("graph") or {}).get("hash"))
                if (last_fingerprint and last_fingerprint == rec["decision"]["fingerprint"]
                        and (not last_graph_hash or last_graph_hash == graph_hash)):
                    return last
                if not last_fingerprint and last.get("profile") == rec["profile"] and last.get("status") == rec["status"]:
                    return last
            except Exception:  # noqa: BLE001
                pass
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    return rec


def strength_trajectory(project: str) -> dict:
    """The series of strength snapshots + the delta from the previous one (B1/D3). Empty until snapshots
    accumulate — honest for a project that has not been snapshotted yet."""
    import json

    p = _history_path(project)
    if not p.is_file():
        return {"series": [], "delta": None}
    series: "list[dict]" = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                series.append(json.loads(line))
            except Exception:  # noqa: BLE001
                pass
    delta = None
    if len(series) >= 2:
        a, b = series[-2]["profile"], series[-1]["profile"]
        delta = [round(b[k] - a[k], 4) for k in range(min(len(a), len(b)))]
    return {"series": series, "delta": delta, "latest": series[-1] if series else None}


def decision_trajectory(project: str) -> dict:
    """B1/D3: the decision's trajectory across the run iterations that ALREADY EXIST — per-iteration score +
    weakest point from `eval_history.jsonl`, merged with any forward strength-profile snapshots. This is the
    'what moved' surface: the score/weakest-point series is available immediately from run history; the faithful
    strength-profile series accumulates as `strength --snapshot` runs (the evidence layer is not versioned per
    iteration, so past strength profiles cannot be faithfully reconstructed). Empty only if the project never ran."""
    import json

    from ztare.common.paths import PROJECTS_DIR

    iterations: "list[dict]" = []
    p = PROJECTS_DIR / project / "workspace" / "eval_history.jsonl"
    if p.is_file():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            iterations.append({"iteration": r.get("iteration"), "score": r.get("score"),
                               "weakest_point": (r.get("weakest_point") or "")[:140]})
    score_delta = None
    scored = [it for it in iterations if isinstance(it.get("score"), (int, float))]
    if len(scored) >= 2:
        score_delta = scored[-1]["score"] - scored[-2]["score"]
    snaps = strength_trajectory(project)
    return {"iterations": iterations, "score_delta": score_delta,
            "strength_series": snaps.get("series", []), "strength_delta": snaps.get("delta")}


def _selftest() -> int:
    ev1 = GovernedElement("e1", "evidence", "source one")
    ev2 = GovernedElement("e2", "evidence", "source two")
    th = GovernedElement("t", "thesis", "thesis")
    # two independent W2 sources back the thesis → corroboration 0,0,2,2 (nothing kernel/re-executable)
    g = GovernedState([ev1, ev2, th],
                      [GovernedEdge("e1", "SUPPORTS", "t", "W2"), GovernedEdge("e2", "SUPPORTS", "t", "W2")])
    assert corroboration_independence(g) == [0, 0, 2, 2], corroboration_independence(g)

    # a W1 CONTRADICTS between two standing evidence-backed claims → a crux
    a = GovernedElement("a", "claim", "A"); b = GovernedElement("b", "claim", "B")
    ea = GovernedElement("ea", "evidence", "for A"); eb = GovernedElement("eb", "evidence", "for B")
    gc = GovernedState([a, b, ea, eb, th],
                       [GovernedEdge("ea", "SUPPORTS", "a", "W2"), GovernedEdge("eb", "SUPPORTS", "b", "W2"),
                        GovernedEdge("a", "CONTRADICTS", "b", "W1"), GovernedEdge("a", "SUPPORTS", "t", "W2")])
    cx = crux_pairs(gc)
    assert len(cx) == 1 and {cx[0]["a"], cx[0]["b"]} == {"a", "b"}, cx

    # an open challenge that would drag the thesis ranks in the queue; a ruled-out one does not
    gq = GovernedState([ev1, th, GovernedElement("k1", "tension", "open worry"),
                        GovernedElement("k2", "gap", "ruled-out worry")],
                       [GovernedEdge("e1", "SUPPORTS", "t", "W2"),
                        GovernedEdge("k1", "CHALLENGES", "t", "W2"),
                        GovernedEdge("k2", "CHALLENGES", "t", "W2"), GovernedEdge("k2", "RULED_OUT", "k2", "W2")])
    q = challenge_queue(gq)
    assert [r["id"] for r in q] == ["k1"], q
    assert q[0]["drag"] > 0.0

    print("RESEARCH-SIGNALS SELFTEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
