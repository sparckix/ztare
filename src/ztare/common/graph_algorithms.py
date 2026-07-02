""" Purposefully not using NetworkX to ensure epistemic isolation.
Reusable graph-algorithm suite over the `graph_carrier` interface — extracted so ANY conformant
carrier (source_claim_graph, probability_dag, constraint_basin_graph …) can be analysed, not just the
NS proof basin where these lived (embedded in ns_graph.py). Pure Python, no NetworkX — small research
graphs don't need it, and a zero-dependency kernel library is the point.

A carrier is `{graph_kind, nodes:[{id,type,label,weight?}], edges:[{from,to,relation}]}` (see
`graph_carrier.canonical_graph_kind_specs`). `analyze(carrier, target=...)` returns the structural reads;
the individual algorithms are exported so other consumers (gates, CLI, the workbench Map) can compose them.

Algorithm family (the kernel constraint-basin set, generalised):
- support_load        — out-degree on support edges (the linchpin: what the most rests on)
- dominators          — target dominators: nodes every support-path to the target runs through (structural necessity)
- cycle               — feedback-arc / circular-reasoning detection (DFS colouring)
- contested           — in-degree on challenge/falsify edges (the most-attacked node)
- unsupported         — claim/candidate nodes with no incoming support (assertions without evidence)
"""
from __future__ import annotations

from typing import Any

# Edges that flow toward the conclusion/target (vs. challenge/rule-out edges).
SUPPORT_RELATIONS = frozenset({"SUPPORTS", "DERIVES", "TESTS", "CONSTRAINS"})
ATTACK_RELATIONS = frozenset({"CHALLENGES", "FALSIFIES"})


def _node_index(carrier: dict[str, Any]) -> dict[str, dict]:
    return {n["id"]: n for n in carrier.get("nodes", []) if isinstance(n, dict) and n.get("id")}


def support_load(carrier: dict[str, Any]) -> dict[str, int]:
    """node id -> count of support edges it provides (its support out-degree)."""
    out: dict[str, int] = {}
    for e in carrier.get("edges", []):
        if e.get("relation") in SUPPORT_RELATIONS and e.get("from"):
            out[e["from"]] = out.get(e["from"], 0) + 1
    return out


def attack_load(carrier: dict[str, Any]) -> dict[str, int]:
    """node id -> count of challenge/falsify edges aimed at it (attack in-degree)."""
    out: dict[str, int] = {}
    for e in carrier.get("edges", []):
        if e.get("relation") in ATTACK_RELATIONS and e.get("to"):
            out[e["to"]] = out.get(e["to"], 0) + 1
    return out


def dominators(carrier: dict[str, Any], target: str) -> list[str]:
    """Target dominators: the nodes every support-path to `target` must pass through — the claims the
    target structurally can't survive without. Iterative dataflow (Cooper-Harvey-Kennedy shape) over a
    synthetic super-source above the support leaves. Stronger than support-degree: structural necessity,
    not volume. Returns ids (excluding the target and the synthetic entry)."""
    ids = set(_node_index(carrier))
    if target not in ids:
        return []
    succ: dict[str, set[str]] = {nid: set() for nid in ids}
    indeg: dict[str, int] = {nid: 0 for nid in ids}
    for e in carrier.get("edges", []):
        f, t, rel = e.get("from"), e.get("to"), e.get("relation")
        if rel in SUPPORT_RELATIONS and f in ids and t in ids:
            if t not in succ[f]:
                succ[f].add(t)
                indeg[t] += 1
    ENTRY = "\0entry"
    leaves = {nid for nid in ids if indeg[nid] == 0}
    if not leaves:
        return []
    succ[ENTRY] = leaves
    universe = ids | {ENTRY}
    preds: dict[str, set[str]] = {n: set() for n in universe}
    for u, vs in succ.items():
        for v in vs:
            preds[v].add(u)
    dom: dict[str, set[str]] = {n: set(universe) for n in universe}
    dom[ENTRY] = {ENTRY}
    changed = True
    while changed:
        changed = False
        for n in universe:
            if n == ENTRY:
                continue
            new = set(universe)
            for p in preds[n]:
                new &= dom[p]
            new = {n} | new
            if new != dom[n]:
                dom[n] = new
                changed = True
    return sorted(dom.get(target, set()) - {ENTRY, target})


def cycle(carrier: dict[str, Any]) -> list[str] | None:
    """First directed cycle (circular reasoning) via DFS colouring, or None."""
    ids = set(_node_index(carrier))
    adj: dict[str, list[str]] = {}
    for e in carrier.get("edges", []):
        f, t = e.get("from"), e.get("to")
        if f in ids and t in ids:
            adj.setdefault(f, []).append(t)
    color: dict[str, int] = {}
    stack: list[str] = []

    def dfs(u: str) -> list[str] | None:
        color[u] = 1
        stack.append(u)
        for v in adj.get(u, []):
            if color.get(v, 0) == 1:
                return stack[stack.index(v):]
            if color.get(v, 0) == 0 and (c := dfs(v)):
                return c
        color[u] = 2
        stack.pop()
        return None

    for u in list(adj):
        if color.get(u, 0) == 0 and (c := dfs(u)):
            return c
    return None


def gradual_strength(carrier: dict[str, Any], *, iterations: int = 60) -> dict[str, float]:
    """DF-QuAD gradual semantics for a Quantitative Bipolar Argumentation Framework (QBAF): each node's
    ARGUMENT STRENGTH in [0,1] after propagating supports and attacks from its base weight — not its bare
    probability. Base = node `weight` (default 0.5). Aggregate supporters/attackers by probabilistic sum
    (1-Π(1-v)); combine s-a; nudge the base toward 1 (net support) or 0 (net attack). Iterate to a fixed
    point (converges on the mostly-acyclic argument graph).

    Grounded in weighted bipolar argumentation (DF-QuAD / quadratic-energy family) — Baroni/Rago/Toni,
    arXiv:1611.08572, arXiv:1807.06685.
    """
    by_id = _node_index(carrier)
    if not by_id:
        return {}
    supporters: dict[str, list[str]] = {nid: [] for nid in by_id}
    attackers: dict[str, list[str]] = {nid: [] for nid in by_id}
    for e in carrier.get("edges", []):
        f, t, rel = e.get("from"), e.get("to"), e.get("relation")
        if f not in by_id or t not in by_id:
            continue
        if rel in SUPPORT_RELATIONS:
            supporters[t].append(f)
        elif rel in ATTACK_RELATIONS:
            attackers[t].append(f)
    base = {nid: (float(n["weight"]) if isinstance(n.get("weight"), (int, float)) else 0.5) for nid, n in by_id.items()}
    strength = dict(base)

    def agg(ids: list[str]) -> float:
        prod = 1.0
        for i in ids:
            prod *= (1.0 - strength[i])
        return 1.0 - prod

    for _ in range(iterations):
        nxt = {}
        for nid in by_id:
            s, a = agg(supporters[nid]), agg(attackers[nid])
            c = s - a
            b = base[nid]
            nxt[nid] = b + c * (1.0 - b) if c >= 0 else b + c * b
        if all(abs(nxt[k] - strength[k]) < 1e-6 for k in nxt):
            strength = nxt
            break
        strength = nxt
    return {k: round(v, 4) for k, v in strength.items()}


def _support_reach_to(carrier: dict[str, Any], target: str, ids: set[str],
                      exclude: "tuple[str, str] | None" = None) -> set[str]:
    """Nodes with a directed SUPPORT-path to `target` (reverse traversal on support edges, minus one
    optionally-excluded edge). The set of claims/evidence whose support actually reaches the conclusion."""
    radj: dict[str, list[str]] = {}
    for e in carrier.get("edges", []):
        f, t, rel = e.get("from"), e.get("to"), e.get("relation")
        if rel in SUPPORT_RELATIONS and f in ids and t in ids:
            if exclude and (f, t) == exclude:
                continue
            radj.setdefault(t, []).append(f)
    seen: set[str] = set()
    stack = [target]
    while stack:
        u = stack.pop()
        for p in radj.get(u, []):
            if p not in seen:
                seen.add(p)
                stack.append(p)
    return seen


def critical_edges(carrier: dict[str, Any], target: str, *, top: int = 3) -> list[dict[str, Any]]:
    """MOST-VITAL SUPPORT EDGES: for each support edge, how many nodes lose their support-path to `target`
    if it's cut. The single link an attacker should break to disconnect the most support — a falsifier's
    highest-leverage target. Grounded in most-vital-edges / network-interdiction (single-edge min-cut
    sensitivity); O(E²) but E is tiny for a research graph (ponytail: brute per-edge recompute, swap for a
    residual-flow interdiction only if graphs get large)."""
    ids = set(_node_index(carrier))
    if target not in ids:
        return []
    base = _support_reach_to(carrier, target, ids)
    by_id = _node_index(carrier)
    seen_edges: set[tuple[str, str]] = set()
    results: list[dict[str, Any]] = []
    for e in carrier.get("edges", []):
        f, t, rel = e.get("from"), e.get("to"), e.get("relation")
        if rel not in SUPPORT_RELATIONS or f not in ids or t not in ids or (f, t) in seen_edges:
            continue
        seen_edges.add((f, t))
        lost = len(base - _support_reach_to(carrier, target, ids, exclude=(f, t)))
        if lost > 0:
            results.append({"from": f, "to": t, "disconnects": lost,
                            "from_label": by_id[f].get("label", f), "to_label": by_id[t].get("label", t)})
    results.sort(key=lambda r: -r["disconnects"])
    return results[:top]


def grounded_labelling(carrier: dict[str, Any]) -> dict[str, str]:
    """Dung GROUNDED labelling over the attack graph: each node IN (accepted/defended), OUT (defeated),
    or UNDEC (undecided — floats in an odd attack cycle). The discrete, sceptical complement to DF-QuAD's
    continuous strength: 'which claims actually survive the debate'. Grounded in Dung 1995 abstract
    argumentation + Caminada's labelling characterisation of the grounded extension."""
    ids = list(_node_index(carrier))
    attackers: dict[str, list[str]] = {n: [] for n in ids}
    for e in carrier.get("edges", []):
        f, t, rel = e.get("from"), e.get("to"), e.get("relation")
        if rel in ATTACK_RELATIONS and f in attackers and t in attackers:
            attackers[t].append(f)
    label = {n: "UNDEC" for n in ids}
    changed = True
    while changed:
        changed = False
        for n in ids:
            if label[n] != "UNDEC":
                continue
            atks = attackers[n]
            if all(label[a] == "OUT" for a in atks):          # no attackers, or all defeated → accepted
                label[n] = "IN"
                changed = True
            elif any(label[a] == "IN" for a in atks):          # an accepted attacker → defeated
                label[n] = "OUT"
                changed = True
    return label


def core_skeleton(carrier: dict[str, Any]) -> dict[str, Any]:
    """k-CORE decomposition on the (undirected) support graph: the innermost core is the load-bearing
    SKELETON — the densely-interlinked heart of the argument, once pendant/leaf nodes are peeled away.
    Use it to DECLUTTER the map (show the core, fold the periphery). Batagelj–Zaversnik coreness.
    Grounded in k-core (Seidman 1983) + graph-summarization. Degrades to empty skeleton on tree-like
    graphs (max core < 2), which is correct — a tree has no dense core."""
    ids = set(_node_index(carrier))
    adj: dict[str, set[str]] = {n: set() for n in ids}
    for e in carrier.get("edges", []):
        f, t, rel = e.get("from"), e.get("to"), e.get("relation")
        if rel in SUPPORT_RELATIONS and f in ids and t in ids and f != t and t not in adj[f]:
            adj[f].add(t)
            adj[t].add(f)
    deg = {n: len(adj[n]) for n in ids}
    remaining = set(ids)
    d = dict(deg)
    coreness: dict[str, int] = {}
    k = 0
    while remaining:
        u = min(remaining, key=lambda n: d[n])
        k = max(k, d[u])
        coreness[u] = k
        remaining.discard(u)
        for v in adj[u]:
            if v in remaining and d[v] > 0:
                d[v] -= 1
    max_core = max(coreness.values()) if coreness else 0
    by_id = _node_index(carrier)
    skeleton = ([{"id": n, "label": by_id[n].get("label", n)} for n in sorted(ids) if coreness.get(n, 0) >= max_core]
                if max_core >= 2 else [])
    return {"coreness": coreness, "max_core": max_core, "skeleton": skeleton}


def polarization(carrier: dict[str, Any], target: str) -> dict[str, Any] | None:
    """CONTROVERSY at the target: the balance of support mass vs attack mass reaching it. `score` in [0,1]
    is 1 - |s-a|/(s+a) — 1.0 is a dead heat (maximally contested, a coin-flip), 0.0 is one-sided. Uses
    DF-QuAD node strengths as each direct supporter/attacker's mass. Grounded in bipolar-argumentation
    polarization/controversy measures (a debate is 'controversial' when pro and con mass are near-balanced).
    Returns None when nothing attacks the target (no controversy story to tell)."""
    by_id = _node_index(carrier)
    if target not in by_id:
        return None
    strength = gradual_strength(carrier)
    s = a = 0.0
    for e in carrier.get("edges", []):
        if e.get("to") != target:
            continue
        f, rel = e.get("from"), e.get("relation")
        if f not in by_id:
            continue
        if rel in SUPPORT_RELATIONS:
            s += strength.get(f, 0.0)
        elif rel in ATTACK_RELATIONS:
            a += strength.get(f, 0.0)
    if a <= 0 or (s + a) <= 0:
        return None
    score = 1.0 - abs(s - a) / (s + a)
    return {"support": round(s, 3), "attack": round(a, 3), "score": round(score, 3),
            "leaning": "contested" if score >= 0.66 else ("supported" if s > a else "attacked")}


def fronts(carrier: dict[str, Any], target: str | None = None, *, min_size: int = 3) -> list[list[dict[str, Any]]]:
    """FRONTS — the independent lines of argument. A thesis graph converges on one apex, so it's always
    connected and hub-dominated; label-propagation and modularity collapse it to a single blob. The
    meaningful decomposition is structural: the apex (target + its dominators — the shared spine every
    thread runs through) is a cut set; remove it and the graph falls into the separate threads that each
    support the thesis on their own. Grounded in articulation-point / block-cut decomposition
    (Hopcroft-Tarjan). Returns components with >= min_size nodes only when there are >= 2; else [] (one
    thread). No dependency — right for 30-60 node graphs."""
    by_id = _node_index(carrier)
    apex: set[str] = set()
    if target and target in by_id:
        apex = {target} | set(dominators(carrier, target))
    kept = [n for n in sorted(by_id) if n not in apex]
    keptset = set(kept)
    adj: dict[str, set[str]] = {n: set() for n in kept}
    for e in carrier.get("edges", []):
        f, t = e.get("from"), e.get("to")
        if f in keptset and t in keptset and f != t:
            adj[f].add(t)
            adj[t].add(f)
    seen: set[str] = set()
    comps: list[list[str]] = []
    for start in kept:
        if start in seen:
            continue
        stack, comp = [start], []
        seen.add(start)
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        comps.append(sorted(comp))
    comms = [c for c in comps if len(c) >= min_size]
    if len(comms) < 2:
        return []
    comms.sort(key=lambda g: -len(g))
    return [[{"id": n, "label": by_id[n].get("label", n)} for n in g] for g in comms]


def correlated_support(carrier: dict[str, Any], target: str, *, threshold: float = 0.5,
                       min_evidence: int = 2, top: int = 3) -> list[dict[str, Any]]:
    """ILLUSORY REDUNDANCY: two claims that both back the target can look like independent legs while
    resting on the SAME evidence — you think you have two supports, it's really one. For each pair of
    target-supporting claims, Jaccard overlap of their evidence sets; flag pairs >= threshold. Surfaces a
    dependency the DAG hides (it draws both legs, not that they share a base) — a correlated-failure trap:
    one retracted source knocks out both. Evidence set = evidence-type nodes with a support-path to the claim."""
    by_id = _node_index(carrier)
    if target not in by_id:
        return []
    ids = set(by_id)
    supporters = sorted({e["from"] for e in carrier.get("edges", [])
                         if e.get("relation") in SUPPORT_RELATIONS and e.get("to") == target
                         and e.get("from") in by_id and by_id[e["from"]].get("type") in ("claim", "candidate")})
    ev_of = {c: {n for n in _support_reach_to(carrier, c, ids) if by_id.get(n, {}).get("type") == "evidence"}
             for c in supporters}
    out: list[dict[str, Any]] = []
    for i in range(len(supporters)):
        for j in range(i + 1, len(supporters)):
            a, b = ev_of[supporters[i]], ev_of[supporters[j]]
            if len(a) < min_evidence or len(b) < min_evidence:
                continue
            union = len(a | b)
            jac = len(a & b) / union if union else 0.0
            if jac >= threshold:
                ci, cj = supporters[i], supporters[j]
                out.append({"a": ci, "b": cj, "a_label": by_id[ci].get("label", ci),
                            "b_label": by_id[cj].get("label", cj), "jaccard": round(jac, 2),
                            "shared": len(a & b)})
    out.sort(key=lambda r: -r["jaccard"])
    return out[:top]


def analyze(carrier: dict[str, Any], *, target: str | None = None) -> dict[str, Any]:
    """Run the suite and return structural reads keyed for rendering. `target` defaults to the node
    with id 'thesis' (the source-claim-graph convention) or the highest-support sink."""
    by_id = _node_index(carrier)
    if not by_id:
        return {}
    if target is None:
        target = "thesis" if "thesis" in by_id else None
    sup = support_load(carrier)
    atk = attack_load(carrier)
    in_sup: dict[str, int] = {}
    for e in carrier.get("edges", []):
        if e.get("relation") in SUPPORT_RELATIONS and e.get("to"):
            in_sup[e["to"]] = in_sup.get(e["to"], 0) + 1

    def ref(nid: str, **extra: Any) -> dict | None:
        n = by_id.get(nid)
        return {"id": nid, "label": n.get("label", nid), **extra} if n else None

    out: dict[str, Any] = {}
    if sup and max(sup.values()) >= 2:
        lb = max(sup, key=lambda k: sup[k])
        out["linchpin"] = ref(lb, supports=sup[lb])
    if target:
        dom = [ref(d) for d in dominators(carrier, target) if ref(d)]
        if dom:
            out["essential"] = dom[:5]            # the target can't be reached without these
    spine = [n for n in by_id.values() if n.get("type") == "claim" and isinstance(n.get("weight"), (int, float))]
    if spine:
        wl = min(spine, key=lambda n: n["weight"])
        out["weakest_link"] = {"id": wl["id"], "label": wl.get("label", wl["id"]), "probability": wl["weight"]}
    if atk:
        mc = max(atk, key=lambda k: atk[k])
        out["most_contested"] = ref(mc, challenges=atk[mc])
    unsup = [ref(n["id"]) for n in by_id.values() if n.get("type") in ("claim", "candidate") and in_sup.get(n["id"], 0) == 0]
    unsup = [u for u in unsup if u]
    if unsup:
        out["unsupported"] = unsup[:5]
    cyc = cycle(carrier)
    if cyc:
        out["circular"] = [c for c in (ref(i) for i in cyc) if c]
    # QBAF argument strength (DF-QuAD): the thesis's strength after the debate, and the claim the
    # debate most CHANGES from its bare probability (attacked-down or supported-up).
    strength = gradual_strength(carrier)
    if target and target in strength:
        out["argument_strength"] = round(strength[target], 4)
    shifted = [
        (nid, strength[nid] - (float(n["weight"]) if isinstance(n.get("weight"), (int, float)) else 0.5))
        for nid, n in by_id.items()
        if n.get("type") in ("claim", "candidate") and isinstance(n.get("weight"), (int, float))
    ]
    shifted = [s for s in shifted if abs(s[1]) >= 0.08]
    if shifted:
        nid, delta = max(shifted, key=lambda s: abs(s[1]))
        out["debate_shift"] = ref(nid, delta=round(delta, 3), direction="weakened" if delta < 0 else "reinforced")
    # Most-vital support edge: the single link whose failure disconnects the most support from the target.
    # Distinct from `essential` (a necessary NODE) — this names the necessary EDGE to defend or attack.
    if target:
        ce = critical_edges(carrier, target, top=1)
        if ce and ce[0]["disconnects"] >= 2:
            out["critical_link"] = ce[0]
    # Grounded (sceptical) labelling names every node with an unrebutted attacker OUT — too blunt to surface
    # raw (a soft challenge would "defeat" a well-supported thesis, contradicting the weighted reads). Sharpen
    # it: report a claim DEFEATED only when a decisive FALSIFIES edge from an accepted node landed and stands
    # unrebutted, and never the target itself (its standing is the weighted argument_strength read).
    lab = grounded_labelling(carrier)
    falsified_by = {}
    for e in carrier.get("edges", []):
        if e.get("relation") == "FALSIFIES" and lab.get(e.get("from")) == "IN" and lab.get(e.get("to")) == "OUT":
            falsified_by.setdefault(e["to"], e["from"])
    defeated = [ref(nid, by=by_id[src].get("label", src)) for nid, src in falsified_by.items() if nid != target and by_id.get(nid)]
    if defeated:
        out["defeated"] = defeated[:5]
    # Load-bearing skeleton (k-core): the densely-interlinked heart once leaves are peeled — for decluttering
    # the map. Only meaningful when there's a real core (max_core >= 2); trees correctly yield nothing.
    sk = core_skeleton(carrier)
    if sk["skeleton"]:
        out["skeleton"] = {"max_core": sk["max_core"], "nodes": sk["skeleton"][:8]}
    # Controversy: how balanced support vs attack mass is at the thesis (a coin-flip vs one-sided).
    if target:
        pol = polarization(carrier, target)
        if pol:
            out["polarization"] = pol
    # Fronts: independent lines of argument once the shared apex is peeled — only when the graph splits.
    fr = fronts(carrier, target)
    if fr:
        out["fronts"] = [{"size": len(g), "nodes": g[:6]} for g in fr[:4]]
    # Illusory redundancy: "independent" supporting claims that actually share their evidence (Jaccard) —
    # a correlated-failure trap the DAG hides. On-thesis for a rigor tool: two legs, one base.
    if target:
        cs = correlated_support(carrier, target)
        if cs:
            out["correlated_support"] = cs
    return out


def _selfcheck() -> None:
    carrier = {
        "graph_kind": "source_claim_graph",
        "nodes": [
            {"id": "thesis", "type": "thesis", "label": "T", "weight": 0.7},
            {"id": "c1", "type": "claim", "label": "C1", "weight": 0.9},
            {"id": "c2", "type": "claim", "label": "C2", "weight": 0.4},
            {"id": "s1", "type": "evidence", "label": "S1"},
        ],
        "edges": [
            {"from": "s1", "to": "c1", "relation": "SUPPORTS"},
            {"from": "s1", "to": "thesis", "relation": "SUPPORTS"},
            {"from": "c1", "to": "thesis", "relation": "DERIVES"},
            {"from": "c2", "to": "thesis", "relation": "DERIVES"},
        ],
    }
    a = analyze(carrier)
    assert a["linchpin"]["id"] == "s1" and a["linchpin"]["supports"] == 2, a
    assert a["weakest_link"]["id"] == "c2", a
    assert any(u["id"] == "c2" for u in a["unsupported"]), a
    # dominators: s1 dominates thesis only if it's on every path — here c2→thesis bypasses s1, so none.
    assert "essential" not in a or all(d["id"] != "s1" for d in a["essential"]), a
    # funnel: make s1 the sole route → s1 dominates thesis.
    funnel = {"graph_kind": "x", "nodes": carrier["nodes"],
              "edges": [{"from": "s1", "to": "c1", "relation": "SUPPORTS"},
                        {"from": "c1", "to": "thesis", "relation": "DERIVES"}]}
    assert "s1" in dominators(funnel, "thesis") and "c1" in dominators(funnel, "thesis"), dominators(funnel, "thesis")
    assert cycle({"graph_kind": "x", "nodes": [{"id": "a"}, {"id": "b"}],
                  "edges": [{"from": "a", "to": "b", "relation": "X"}, {"from": "b", "to": "a", "relation": "X"}]})
    # QBAF gradual strength: an attacked claim drops below its base; a supported one rises.
    qbaf = {"graph_kind": "x", "nodes": [
        {"id": "t", "type": "thesis", "label": "T", "weight": 0.5},
        {"id": "atk", "type": "tension", "label": "A", "weight": 0.9},
        {"id": "sup", "type": "evidence", "label": "S", "weight": 0.8}]
        , "edges": [{"from": "atk", "to": "t", "relation": "CHALLENGES"},
                    {"from": "sup", "to": "t", "relation": "SUPPORTS"}]}
    st = gradual_strength(qbaf)
    assert 0.0 <= st["t"] <= 1.0, st
    only_atk = gradual_strength({"graph_kind": "x", "nodes": qbaf["nodes"],
                                 "edges": [{"from": "atk", "to": "t", "relation": "CHALLENGES"}]})
    assert only_atk["t"] < 0.5, only_atk          # net attack pulls the base (0.5) down
    # critical_edges: in the funnel s1→c1→thesis, cutting c1→thesis disconnects both s1 and c1 (2 nodes).
    ce = critical_edges(funnel, "thesis", top=3)
    assert ce and ce[0]["disconnects"] == 2 and (ce[0]["from"], ce[0]["to"]) == ("c1", "thesis"), ce
    # grounded_labelling: sup unattacked → IN; t attacked by IN node atk → OUT.
    lab = grounded_labelling(qbaf)
    assert lab["atk"] == "IN" and lab["t"] == "OUT" and lab["sup"] == "IN", lab
    # core_skeleton: a triangle (all support edges) has a 2-core; a path has none.
    tri = {"graph_kind": "x", "nodes": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
           "edges": [{"from": "a", "to": "b", "relation": "SUPPORTS"},
                     {"from": "b", "to": "c", "relation": "SUPPORTS"},
                     {"from": "c", "to": "a", "relation": "SUPPORTS"}]}
    assert core_skeleton(tri)["max_core"] == 2 and len(core_skeleton(tri)["skeleton"]) == 3, core_skeleton(tri)
    assert core_skeleton(funnel)["skeleton"] == [], core_skeleton(funnel)   # path/tree → no dense core
    # polarization: sup(0.8) vs atk(0.9) at t → near dead-heat, high controversy; None when unattacked.
    pol = polarization(qbaf, "t")
    assert pol and pol["score"] >= 0.66 and pol["leaning"] == "contested", pol
    assert polarization(funnel, "thesis") is None, "unattacked target → no controversy"
    # fronts: two 3-node threads that only meet at the thesis apex → two fronts once the apex is peeled;
    # without a target (no apex to remove) the whole thing is one component → none.
    twothreads = {"graph_kind": "x",
        "nodes": [{"id": x} for x in ("T", "a", "b", "c", "d", "e", "f")],
        "edges": [{"from": f_, "to": t_, "relation": "SUPPORTS"} for f_, t_ in
                  [("a", "b"), ("b", "c"), ("c", "T"), ("d", "e"), ("e", "f"), ("f", "T")]]}
    fr = fronts(twothreads, "T")
    assert len(fr) == 2 and all(len(g) == 3 for g in fr), [[n["id"] for n in g] for g in fr]
    assert fronts(twothreads) == [], "no apex peeled → one connected component → no fronts"
    # correlated_support: c1,c2 both back T; both rest on the SAME two evidence nodes → Jaccard 1.0.
    corr = {"graph_kind": "x", "nodes": [
        {"id": "T", "type": "thesis"}, {"id": "c1", "type": "claim"}, {"id": "c2", "type": "claim"},
        {"id": "e1", "type": "evidence"}, {"id": "e2", "type": "evidence"}],
        "edges": [{"from": "c1", "to": "T", "relation": "DERIVES"}, {"from": "c2", "to": "T", "relation": "DERIVES"},
                  {"from": "e1", "to": "c1", "relation": "SUPPORTS"}, {"from": "e2", "to": "c1", "relation": "SUPPORTS"},
                  {"from": "e1", "to": "c2", "relation": "SUPPORTS"}, {"from": "e2", "to": "c2", "relation": "SUPPORTS"}]}
    cs = correlated_support(corr, "T")
    assert cs and cs[0]["jaccard"] == 1.0 and cs[0]["shared"] == 2, cs
    # distinct evidence → no illusory redundancy flagged.
    corr2 = {"graph_kind": "x", "nodes": corr["nodes"] + [{"id": "e3", "type": "evidence"}, {"id": "e4", "type": "evidence"}],
             "edges": [{"from": "c1", "to": "T", "relation": "DERIVES"}, {"from": "c2", "to": "T", "relation": "DERIVES"},
                       {"from": "e1", "to": "c1", "relation": "SUPPORTS"}, {"from": "e2", "to": "c1", "relation": "SUPPORTS"},
                       {"from": "e3", "to": "c2", "relation": "SUPPORTS"}, {"from": "e4", "to": "c2", "relation": "SUPPORTS"}]}
    assert correlated_support(corr2, "T") == [], correlated_support(corr2, "T")
    print("graph_algorithms selfcheck: OK")


def main(argv: "list[str] | None" = None) -> int:
    """CLI: run the graph-algorithm suite over a carrier (any registered graph_kind) and print the reads.

        python -m ztare.common.graph_algorithms --carrier path/to/carrier.json [--target thesis]
        python -m ztare.common.graph_algorithms --project <slug>   # builds the source_claim_graph carrier
    """
    import argparse, json
    ap = argparse.ArgumentParser(description="Structural graph analysis over a graph_carrier (no LLM).")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--carrier", help="path to a graph_carrier JSON ({graph_kind,nodes,edges})")
    src.add_argument("--project", help="project slug — builds + analyses its source_claim_graph")
    ap.add_argument("--target", default=None, help="target node id for dominators (default: 'thesis')")
    ap.add_argument("--selfcheck", action="store_true")
    args = ap.parse_args(argv)
    if args.selfcheck:
        _selfcheck()
        return 0
    if args.project:
        from pathlib import Path
        from ztare.reports.research_graph import build_research_graph
        carrier = build_research_graph(args.project, Path.cwd())
    else:
        carrier = json.loads(open(args.carrier).read())
    print(json.dumps({"graph_kind": carrier.get("graph_kind"), "insights": analyze(carrier, target=args.target)}, indent=2))
    return 0


if __name__ == "__main__":
    import sys
    if "--selfcheck" in sys.argv or len(sys.argv) == 1:
        _selfcheck()
    else:
        raise SystemExit(main())
