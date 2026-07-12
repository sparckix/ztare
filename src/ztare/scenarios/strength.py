"""Graded argument strength — a deterministic, prior-free strength profile per claim.

The crisp grounded verdict is the wrong primitive for a research substrate: nothing is ever settled, so every
live map reads BLOCKED and the apparatus is inert. This module adds a GRADED strength via a gradual argumentation
semantics over the same bipolar argument graph, so a grounded-but-contested thesis and an ungrounded one are
maximally distinguished.

Design (Fable-reviewed; every choice is load-bearing):
- **Semantics: the Quadratic Energy Model** (Potyka, KR 2018), damped forward-Euler iteration. Chosen over
  DF-QuAD (acyclic-only; our maps have CONTRADICTS 2-cycles) and h-categoriser (attack-only; our graph is
  bipolar). QEM's squashing `h(x)=max(0,x)²/(1+max(0,x)²)` satisfies h(x)<x on (0,1], so a pure support cycle
  with internal base 0 decays to 0 (no self-lifting). Determinism is unconditional (Lipschitz); convergence is
  proven for acyclic graphs — cyclic graphs have NO universal theorem in this literature (none does), so a run
  that hits the iteration cap is surfaced as the honest state NONCONVERGENT, never a fabricated number.
- **Prior-free weights via warrant FILTRATION, not cardinal weights.** Mapping W0..W3 to numbers (0.7/0.4/…)
  would smuggle a prior (why 0.7?). Instead run the semantics 4×: stratum k keeps only edges at least as
  checkable as tier k (k=0 → W0 only; k=3 → all). Emit the PROFILE (s₀,s₁,s₂,s₃) = thesis strength if you trust
  only kernel certs / +re-executable / +quotes / +proposals. Uses only the warrant PARTIAL ORDER — zero free
  parameters, moat intact. `(0.9,·,·,0.91)` = kernel-hard; `(0,·,·,0.9)` = a castle of quotes/proposals.
- **Base scores, prior-free**: leaf evidence w=1, every internal claim/thesis/finding w=0. An unsupported open
  challenge therefore has strength 0 and cannot drag a well-evidenced thesis — a challenge bites only once it is
  itself evidence-backed. That is both grounded-semantics-correct and product-correct.
- **Per-source collapse** before energy aggregation (max within a provenance source, sum across sources), so
  fifty real-but-redundant quotes from one source do not saturate a stratum. The one surviving gaming vector
  Fable named. (Ceiling: keyed on the support node's own source identity until document-level provenance is
  threaded from the evidence packet — see `_source_key`.)
- **Override lattice**: REFUTED (a surviving W0/W1 attack on the thesis) ≻ NONCONVERGENT ≻ UNSUPPORTED (no
  support at any tier) ≻ CONTESTED (show the profile — essentially every live research map). Arithmetic never
  launders a kernel-grade refutation into "strength 0.12".

No LLM, no priors, deterministic.
"""
from __future__ import annotations

from ztare.scenarios.argument_kernel import WARRANT_RANK, _ATTACK, _SUPPORT, _targets
from ztare.scenarios.governed_types import GovernedState

_CHALLENGE = _ATTACK + ("CHALLENGES",)     # what drags a node down (attacks + softer challenges)
_STRATA = 4                                # W0-only, +W1, +W2, +all
_DELTA = 0.1                               # forward-Euler damping (Potyka)
_TOL = 1e-9
_TMAX = 4000                               # tiny graphs converge in << this; cap → NONCONVERGENT
_REFUTE_EPS = 0.05                         # an attacker below this is not "surviving"


def _h(x: float) -> float:
    m = x if x > 0.0 else 0.0
    return (m * m) / (1.0 + m * m)


def _lineage_sources(governed: GovernedState) -> "dict[str, str]":
    """Provenance grouping for per-source collapse via union-find over DERIVED_FROM edges: sources in one
    derivation lineage collapse to a single group, so `B`, `C`, `D` all deriving from `A` count ONCE, not four
    times (the epistemic-cascade / citation-incest defense — max across the whole lineage, not just one file).
    Inert until the carrier emits DERIVED_FROM (build_research_graph does not yet), where it degrades to per-node
    — each compiled source is then its own group, which is the current honest granularity."""
    parent = {e.id: e.id for e in governed.elements}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for e in governed.edges:
        if e.kind == "DERIVED_FROM" and e.src in parent and e.dst in parent:
            parent[find(e.src)] = find(e.dst)  # b DERIVED_FROM a → same lineage group
    # Byte-identical or explicitly lineage-keyed evidence is one source even when it appears under several
    # paths/IDs. Union-find keeps this O((V+E) α(V)); it also shrinks the Shapley player set below.
    owner: "dict[str, str]" = {}
    for element in governed.of_kind("evidence"):
        if not element.source_key:
            continue
        prior = owner.get(element.source_key)
        if prior is None:
            owner[element.source_key] = element.id
        else:
            parent[find(element.id)] = find(prior)
    return {nid: find(nid) for nid in parent}


def _collapsed_support(supporter_ids: "list[str]", s: "dict[str, float]", source_of: "dict[str, str]") -> float:
    """Sum across provenance sources of the MAX strength within each source — so N redundant supports from one
    source (or one derivation lineage) count once, but independent corroboration adds up."""
    by_source: "dict[str, float]" = {}
    for b in supporter_ids:
        k = source_of.get(b, b)
        v = s.get(b, 0.0)
        if v > by_source.get(k, 0.0):
            by_source[k] = v
    return sum(by_source.values())


def _qem_fixpoint(base_w: "dict[str, float]", supporters: "dict[str, list]", attackers: "dict[str, list]",
                  source_of: "dict[str, str]") -> "tuple[dict[str, float], bool]":
    """Damped simultaneous (Jacobi) iteration of the Quadratic Energy Model to a fixed point. Returns
    (strengths, converged)."""
    s = dict(base_w)
    for _ in range(_TMAX):
        nxt: "dict[str, float]" = {}
        max_delta = 0.0
        for a, w in base_w.items():
            energy = _collapsed_support(supporters.get(a, ()), s, source_of) - sum(s.get(b, 0.0) for b in attackers.get(a, ()))
            f = w - w * _h(-energy) + (1.0 - w) * _h(energy)
            ns = s[a] + _DELTA * (f - s[a])
            nxt[a] = ns
            d = ns - s[a]
            if d < 0.0:
                d = -d
            if d > max_delta:
                max_delta = d
        s = nxt
        if max_delta < _TOL:
            return s, True
    return s, False


def _stratum_edges(governed: GovernedState, min_rank: int):
    """Supporters/attackers restricted to edges at least `min_rank` checkable (warrant rank ≥ min_rank). A
    challenge from a RULED_OUT finding is dropped — the graded twin of `argument_kernel._open_findings`, which
    the crisp verdict already honors (Fable eigenreview): without this, `rule_out` moves the crisp verdict but
    never the strength profile, so a settled tension would drag the thesis forever."""
    ruled_out = {e.src for e in governed.edges if e.kind == "RULED_OUT"}  # a RULED_OUT edge FROM a finding settles it
    supporters: "dict[str, list]" = {}
    attackers: "dict[str, list]" = {}
    for e in governed.edges:
        if WARRANT_RANK.get(getattr(e, "warrant", "W3") or "W3", 0) < min_rank:
            continue
        if e.kind in _SUPPORT:
            supporters.setdefault(e.dst, []).append(e.src)
        elif e.kind in _CHALLENGE and e.src not in ruled_out:
            attackers.setdefault(e.dst, []).append(e.src)
    return supporters, attackers


def _override_status(governed: GovernedState, target: "str | None", profile: "list[float]",
                     converged: bool, strata: "list[dict]") -> str:
    if not converged:
        return "NONCONVERGENT"
    if target is None:
        return "UNSUPPORTED"
    # REFUTED: a surviving W0/W1-warranted attack ON THE THESIS (attacker has real strength in its own stratum).
    for e in governed.edges:
        if e.dst == target and e.kind in _ATTACK:
            rank = WARRANT_RANK.get(getattr(e, "warrant", "W3") or "W3", 0)
            if rank >= 2:  # W0 (3) or W1 (2)
                k = _STRATA - 1 - rank  # the stratum where this warrant first appears
                if strata[k].get(e.src, 0.0) > _REFUTE_EPS:
                    return "REFUTED"
    if profile[_STRATA - 1] <= 1e-6:  # no support survives at ANY tier
        return "UNSUPPORTED"
    return "CONTESTED"


def _base_weights(governed: GovernedState, active_evidence: "set[str] | None") -> "dict[str, float]":
    """Prior-free base scores: leaf evidence 1, every internal node 0. `active_evidence` (for counterfactuals /
    Shapley) restricts which evidence is 'present' — an absent source drops to base 0."""
    return {e.id: (1.0 if (e.kind == "evidence" and (active_evidence is None or e.id in active_evidence)) else 0.0)
            for e in governed.elements}


def _thesis_strength_at(governed: GovernedState, active_evidence: "set[str] | None", min_rank: int = 0,
                        source_of: "dict[str, str] | None" = None) -> float:
    """One QEM solve (a single stratum, all edges by default) → the thesis strength scalar. The characteristic
    function for Shapley / counterfactuals. Cheap: one fixed point on a small graph."""
    if source_of is None:
        source_of = _lineage_sources(governed)
    supporters, attackers = _stratum_edges(governed, min_rank)
    s, _ = _qem_fixpoint(_base_weights(governed, active_evidence), supporters, attackers, source_of)
    targets = _targets(governed)
    return s.get(targets[0], 0.0) if targets else 0.0


def shapley_support(governed: GovernedState, *, max_assumptions: int = 13) -> dict:
    """WHAT THE DECISION RESTS ON — exact removal-Shapley of each evidence source's contribution to the thesis
    strength (full stratum). Characteristic function `v(A) = thesis strength given only sources A present`;
    contributions sum to the total strength (Shapley efficiency), so it apportions the decision across its
    sources. Exact at 2^n over evidence; caps (and says so) past `max_assumptions`. The ATMS `minimal_cores`
    heir under a continuous strength — attribution that satisfies efficiency/symmetry/dummy (Yin–Potyka–Toni)."""
    import hashlib
    import random
    from itertools import combinations
    from math import factorial

    evidence = [e.id for e in governed.of_kind("evidence")]
    source_of = _lineage_sources(governed)
    groups: "dict[str, list[str]]" = {}
    for evidence_id in evidence:
        groups.setdefault(source_of.get(evidence_id, evidence_id), []).append(evidence_id)
    players = sorted(groups)
    n = len(players)
    if n == 0:
        return {"contributions": [], "total": 0.0, "capped": False, "n": 0}
    total = round(_thesis_strength_at(governed, None, source_of=source_of), 4)

    def active_ids(active_players) -> "set[str]":
        return {evidence_id for player in active_players for evidence_id in groups[player]}

    if n > max_assumptions:
        # Exact Shapley is 2^n — for a large connected component, DEGRADE to seeded Monte-Carlo permutation
        # sampling (approximate but bounded, and deterministic: the seed is derived from the source set, so the
        # result is bit-reproducible). This is the P2 fix — a large graph must never freeze the kernel.
        rng = random.Random(int(hashlib.sha256("|".join(players).encode()).hexdigest()[:12], 16))
        samples = max(64, min(400, 6000 // n))  # bound total solves ~ samples*n ≤ ~6000
        acc = {player: 0.0 for player in players}
        for _ in range(samples):
            perm = players[:]
            rng.shuffle(perm)
            active: "set[str]" = set()
            prev = 0.0  # v(∅) = 0 (no active evidence ⇒ nothing supports the thesis)
            for player in perm:
                active.add(player)
                cur = _thesis_strength_at(governed, active_ids(active), source_of=source_of)
                acc[player] += cur - prev
                prev = cur
        contributions = {player: round(acc[player] / samples, 4) for player in players}
        ranked = sorted(contributions.items(), key=lambda kv: -kv[1])
        return {"contributions": ranked, "total": total, "capped": True, "approx": "monte_carlo",
                "samples": samples, "n": n, "evidence_nodes": len(evidence)}
    vcache = {frozenset(S): _thesis_strength_at(governed, active_ids(S), source_of=source_of)
              for r in range(n + 1) for S in combinations(players, r)}
    contributions: "dict[str, float]" = {}
    for i in players:
        rest = [e for e in players if e != i]
        total = 0.0
        for r in range(len(rest) + 1):
            weight = factorial(r) * factorial(n - r - 1) / factorial(n)
            for S in combinations(rest, r):
                total += weight * (vcache[frozenset(S + (i,))] - vcache[frozenset(S)])
        contributions[i] = round(total, 4)
    ranked = sorted(contributions.items(), key=lambda kv: -kv[1])
    return {"contributions": ranked, "total": round(vcache[frozenset(players)], 4), "capped": False,
            "n": n, "evidence_nodes": len(evidence)}


def strength_profile(governed: GovernedState, active_evidence: "set[str] | None" = None) -> dict:
    """The graded read of the argument graph: a per-claim warrant-filtration strength profile (s₀,s₁,s₂,s₃), the
    thesis profile, an honest convergence flag, and the override-lattice status. Deterministic, prior-free.
    `active_evidence` restricts which sources are present (for counterfactuals / Shapley); None = all."""
    base_w = _base_weights(governed, active_evidence)
    source_of = _lineage_sources(governed)
    strata: "list[dict]" = []
    converged_all = True
    for k in range(_STRATA):
        supporters, attackers = _stratum_edges(governed, min_rank=_STRATA - 1 - k)  # k=0→rank≥3 (W0 only)
        s, conv = _qem_fixpoint(base_w, supporters, attackers, source_of)
        converged_all = converged_all and conv
        strata.append(s)
    per_node = {nid: [round(strata[k].get(nid, 0.0), 4) for k in range(_STRATA)] for nid in base_w}
    targets = _targets(governed)
    # A multi-target decision is the CONJUNCTION (crisp `verdict` treats it so), so the HEADLINE must be the WORST
    # target on the override lattice — never mask a refuted/weak thesis behind a strong sibling by taking
    # targets[0] (Fable eigenreview). Single-thesis maps (the common case) have one candidate ⇒ unchanged.
    _SEV = {"REFUTED": 4, "NONCONVERGENT": 3, "UNSUPPORTED": 2, "CONTESTED": 1}
    if targets:
        scored = [(t, per_node.get(t, [0.0] * _STRATA)) for t in targets]
        scored = [(t, pr, _override_status(governed, t, pr, converged_all, strata)) for t, pr in scored]
        target, profile, status = max(scored, key=lambda x: (_SEV.get(x[2], 0), -x[1][_STRATA - 1]))
    else:
        target, profile = None, [0.0] * _STRATA
        status = _override_status(governed, None, profile, converged_all, strata)
    return {"targets": targets, "thesis": target, "profile": profile, "status": status,
            "converged": converged_all, "per_node": per_node}


def _selftest() -> int:
    from ztare.scenarios.governed_types import GovernedEdge, GovernedElement

    def st(elements, edges):
        return GovernedState(elements, edges)

    ev = GovernedElement("e1", "evidence", "measured X")
    th = GovernedElement("t1", "thesis", "thesis T")

    # (1) evidence (W2 quote) supports thesis, an UNSUPPORTED open challenge exists → CONTESTED, s2/s3 > 0,
    #     s0/s1 = 0 (no kernel/re-executable warrant), and the bare challenge does NOT drag the thesis.
    tension = GovernedElement("k1", "tension", "an open question")
    g = st([ev, th, tension],
           [GovernedEdge("e1", "SUPPORTS", "t1", "W2"), GovernedEdge("k1", "CHALLENGES", "t1", "W3")])
    r = strength_profile(g)
    assert r["status"] == "CONTESTED", r["status"]
    assert r["profile"][0] == 0.0 and r["profile"][1] == 0.0, r["profile"]      # nothing kernel/re-executable
    assert r["profile"][2] > 0.0 and r["profile"][3] > 0.0, r["profile"]        # rests on the W2 quote
    bare = strength_profile(st([ev, th], [GovernedEdge("e1", "SUPPORTS", "t1", "W2")]))
    assert bare["profile"][3] == r["profile"][3], "an unsupported challenge must not drag the thesis"

    # (2) no support at all → UNSUPPORTED, profile all ~0
    u = strength_profile(st([th], []))
    assert u["status"] == "UNSUPPORTED" and max(u["profile"]) <= 1e-6, u

    # (3) evidence-backed (W1) CONTRADICTS the thesis → REFUTED (a surviving hard attack), overrides the number
    ev2 = GovernedElement("e2", "evidence", "counter-measurement")
    ref = st([ev, th, ev2],
             [GovernedEdge("e1", "SUPPORTS", "t1", "W2"), GovernedEdge("e2", "CONTRADICTS", "t1", "W1")])
    assert strength_profile(ref)["status"] == "REFUTED", strength_profile(ref)["status"]

    # (4) a CONTRADICTS 2-cycle between two evidence-backed claims must still CONVERGE (damped QEM)
    a = GovernedElement("a", "claim", "A"); b = GovernedElement("b", "claim", "B")
    ea = GovernedElement("ea", "evidence", "for A"); eb = GovernedElement("eb", "evidence", "for B")
    cyc = st([a, b, ea, eb],
             [GovernedEdge("ea", "SUPPORTS", "a", "W2"), GovernedEdge("eb", "SUPPORTS", "b", "W2"),
              GovernedEdge("a", "CONTRADICTS", "b", "W2"), GovernedEdge("b", "CONTRADICTS", "a", "W2")])
    assert strength_profile(cyc)["converged"], "damped QEM must converge on a 2-cycle"

    # (5) per-source collapse: two supports from the SAME source count once (max), two INDEPENDENT sources add up
    e_a = GovernedElement("sa", "evidence", "src A"); e_b = GovernedElement("sb", "evidence", "src B")
    one_src = st([th, e_a], [GovernedEdge("sa", "SUPPORTS", "t1", "W2"), GovernedEdge("sa", "SUPPORTS", "t1", "W2")])
    two_src = st([th, e_a, e_b], [GovernedEdge("sa", "SUPPORTS", "t1", "W2"), GovernedEdge("sb", "SUPPORTS", "t1", "W2")])
    two_src_strength = strength_profile(two_src)["profile"][3]
    assert two_src_strength > 0.0
    assert strength_profile(one_src)["profile"][3] < two_src_strength, "independent corroboration must beat one loud source"

    # (6) Shapley efficiency: contributions apportion the thesis strength (sum ≈ total), and independent
    #     corroboration splits credit while one source keeps it.
    sh = shapley_support(two_src)
    assert abs(sum(v for _, v in sh["contributions"]) - sh["total"]) < 1e-3, sh
    assert len(sh["contributions"]) == 2 and sh["contributions"][0][1] > 0.0

    # (7) P4 lineage collapse: B,C,D support the thesis but all DERIVED_FROM A → count as ONE source (max), so
    #     citation-incest cannot inflate strength the way independent corroboration does.
    th2 = GovernedElement("t2", "thesis", "T2")
    src_nodes = [GovernedElement(x, "evidence", x) for x in ("A", "B", "C", "D")]
    supp = [GovernedEdge(x, "SUPPORTS", "t2", "W2") for x in ("B", "C", "D")]
    flat = st([th2, *src_nodes], supp)                                  # 3 independent supports → sum
    lineage = st([th2, *src_nodes], supp + [GovernedEdge(x, "DERIVED_FROM", "A", "W2") for x in ("B", "C", "D")])
    assert strength_profile(lineage)["profile"][3] < strength_profile(flat)["profile"][3], "lineage must collapse incest"

    # (8) P2 Monte-Carlo Shapley (forced by a low cap): bounded, sums≈total, and DETERMINISTIC (seeded).
    mc = shapley_support(two_src, max_assumptions=1)
    assert mc.get("approx") == "monte_carlo" and abs(sum(v for _, v in mc["contributions"]) - mc["total"]) < 0.05
    assert shapley_support(two_src, max_assumptions=1) == mc, "seeded Monte-Carlo must be reproducible"

    # (9) Byte-identical source copies are one independent player and cannot increase strength or Shapley cost.
    dup_a = GovernedElement("dup-a", "evidence", "copy A", "same-content-hash")
    dup_b = GovernedElement("dup-b", "evidence", "copy B", "same-content-hash")
    duplicate_paths = st([th, dup_a, dup_b], [GovernedEdge("dup-a", "SUPPORTS", "t1", "W2"),
                                               GovernedEdge("dup-b", "SUPPORTS", "t1", "W2")])
    one_copy = st([th, dup_a], [GovernedEdge("dup-a", "SUPPORTS", "t1", "W2")])
    assert strength_profile(duplicate_paths)["profile"] == strength_profile(one_copy)["profile"]
    dup_shapley = shapley_support(duplicate_paths)
    assert dup_shapley["n"] == 1 and dup_shapley["evidence_nodes"] == 2, dup_shapley

    print("STRENGTH SELFTEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
