"""Argument kernel — a deterministic, ATMS/ABA-style verdict over the governed argument graph (Fable's EQ1/EQ2
"floor"). NOTHING here is theoretically novel and it would be laundering to pretend otherwise; it REUSES 40 years
of theory:

  * verdict-over-assumptions + minimal cores  = an Assumption-based Truth Maintenance System (Reiter & de Kleer,
    AAAI-1987); our `minimal_cores` are their MINIMAL ENVIRONMENTS / prime implicants / minimal supports.
  * the graph is an assumption-based argumentation framework (Dung 1995; Bondarenko, Dung, Kowalski & Toni 1997);
    `verdict` is grounded (least-fixpoint) acceptance.
  * edges carry Toulmin (1958) WARRANTS.
  * `test_agenda` is query-by-committee active learning (Seung, Opper & Sompolinsky 1992), reusing the existing
    `common.information_yield_pricing` primitive — deterministic entropy, NO priors (Fable killed probabilistic VoI).

The LLM→argumentation APPLICATION is a crowded 2025-26 frontier (Argumentative LLMs / QBAF; Graph-of-Verification;
Compliance-by-Construction Argument Graphs) — ZTARE is a parallel discovery there, not a first-mover. What is
actually OURS and worth claiming: (a) the strict determinism boundary — NO LLM in the gate, verbatim-not-semantic,
all semantics pushed to edge-ADMISSION; (b) warrant-typed edges by RE-EXECUTABLE checkability (W0..W3); (c) [roadmap]
LeanMill as a formal-oracle metrology lab measuring gate discrimination. This module is the domain-neutral lift of
the discipline the formal substrate already runs (theory_ir / formalization_admission / axiom_authority).

Set-valued by design (cores, dominators, flip-sets), not scalar (Fable: ad-hoc scalars are where determinism dies).
No LLM.
"""
from __future__ import annotations

from ztare.scenarios.governed_types import EDGE_KINDS, GovernedState

# Toulmin warrant classes ranked by DETERMINISTIC checkability. The verdict is monotone in warrant strength:
# The warrant vocabulary lives in ONE module (scenarios.tiers); re-exported here so existing
# `from argument_kernel import WARRANT_RANK` importers are unaffected. No untyped trust: a conclusion is never
# more trusted than the weakest warrant on a load-bearing support edge.
from ztare.scenarios.tiers import WARRANT_LABEL, WARRANT_RANK  # noqa: F401,E402 — re-export (single source)
_SUPPORT = ("SUPPORTS", "DERIVES")
_ATTACK = ("FALSIFIES", "CONTRADICTS")
_STATUS_RANK = {"REFUTED": 0, "BLOCKED": 1, "SUPPORTED": 2}


def edge_warrant(edge) -> str:
    w = getattr(edge, "warrant", "") or "W3"
    return w if w in WARRANT_RANK else "W3"


def _claims(governed: GovernedState) -> "list":
    return governed.of_kind("thesis") + governed.of_kind("claim")


def _targets(governed: GovernedState) -> "list[str]":
    """What the verdict is ABOUT: the thesis if present, else every claim (the conjunction)."""
    thesis = governed.of_kind("thesis")
    return [t.id for t in (thesis or _claims(governed))]


def assumptions(governed: GovernedState) -> "list[str]":
    """The defeasible atoms (ABA assumptions) the verdict is a function of — claims + open tension/gap findings.
    Evidence is GROUND (data), not an assumption. Sorted for reproducibility."""
    finding_ids = [e.id for kind in ("tension", "gap") for e in governed.of_kind(kind)]
    return sorted({c.id for c in _claims(governed)} | set(finding_ids))


def _accepted(governed: GovernedState, failed: "frozenset[str]") -> "set[str]":
    """Grounded (least-fixpoint) acceptance WITH attack propagation (Fable eigenreview — the crisp verdict must
    agree with the graded strength layer, which subtracts attackers at every node; without this a thesis reads
    SUPPORTED while its sole support is CONTRADICTED). Evidence is ground (always in); a claim is IN iff it is not
    `failed`, is supported by an IN source, AND every node that attacks it is OUT (defeated). A node is OUT once
    attacked by an IN node — so defeat propagates down the support chain (an attacked claim can no longer prop up
    what rests on it) and an attacker that is itself defeated is reinstated. A `failed` assumption is OUT
    (not-assumed, NOT asserted false) — the distinction that lets JOINTLY-pivotal sets exist (two supports for one
    claim: dropping either leaves the other; dropping both defeats it). Monotone fixpoint, so it terminates."""
    supports = [(e.src, e.dst) for e in governed.edges if e.kind in _SUPPORT]
    attacks = [(e.src, e.dst) for e in governed.edges if e.kind in _ATTACK]
    evidence = {e.id for e in governed.of_kind("evidence")}
    claim_ids = [c.id for c in _claims(governed) if c.id not in failed]
    # support-closure ignoring attacks: a claim with NO support path from evidence can never be IN, so it is OUT
    # (and thus can never DEFEAT anything) — without this an unsupported attacker would wrongly block acceptance.
    reachable = set(evidence)
    changed = True
    while changed:
        changed = False
        for c in claim_ids:
            if c not in reachable and any(s in reachable for s, d in supports if d == c):
                reachable.add(c)
                changed = True
    # An attacker with no support path from evidence (a declared `falsifier` watch-condition, or any ungrounded
    # attacker node) is OUT: it cannot defeat a target until it becomes evidence-rooted. Without this it sits in
    # limbo — neither IN nor OUT — and the "every attacker OUT" accept-rule never fires, so a declared falsifier
    # wrongly forces its target to BLOCKED instead of SUPPORTED (grounded-ABA: an attacker refutes only if IN).
    accepted = set(evidence)                                          # IN
    defeated = (set(failed) | {c for c in claim_ids if c not in reachable}
                | {s for s, _ in attacks if s not in reachable}) - evidence  # OUT
    changed = True
    while changed:
        changed = False
        for src, dst in attacks:                                     # defeat: attacked by an IN node ⇒ OUT
            if src in accepted and dst not in evidence and dst not in defeated:
                defeated.add(dst)
                changed = True
        for c in claim_ids:                                          # accept: supported by IN, every attacker OUT
            if c in accepted or c in defeated:
                continue
            if any(s in accepted for s, d in supports if d == c) \
               and all(s in defeated for s, d in attacks if d == c):
                accepted.add(c)
                changed = True
    return accepted


def _open_findings(governed: GovernedState) -> "list[str]":
    return [e.id for kind in ("tension", "gap") for e in governed.of_kind(kind)
            if not any(x.src == e.id and x.kind == "RULED_OUT" for x in governed.edges)]


def _verdict_from_accepted(governed: GovernedState, failed: "frozenset[str]", accepted: "set[str]") -> str:
    targets = _targets(governed)
    attacked = {edge.dst for edge in governed.edges if edge.kind in _ATTACK and edge.src in accepted}
    if any(target in attacked for target in targets):
        return "REFUTED"
    open_findings = [finding for finding in _open_findings(governed) if finding not in failed]
    if open_findings or any(target not in accepted for target in targets):
        return "BLOCKED"
    return "SUPPORTED"


def verdict(governed: GovernedState, failed: "frozenset[str] | None" = None) -> str:
    """The deterministic verdict under an assumption-configuration (`failed` = the OUT assumptions). Grounded
    ABA semantics with attack propagation (see `_accepted`): REFUTED if a target is attacked by an accepted node;
    BLOCKED if a target is unaccepted — including one whose support chain was defeated by an upstream attack — or
    an open tension/gap remains; else SUPPORTED. This is the EQ1 verdict FUNCTION — `minimal_cores`/`test_agenda`
    interrogate it, so it must be principled, not an ad-hoc fold."""
    failed = failed or frozenset()
    return _verdict_from_accepted(governed, failed, _accepted(governed, failed))


def minimal_cores(governed: GovernedState, *, max_size: int = 3) -> "list[frozenset[str]]":
    """The ATMS MINIMAL ENVIRONMENTS: the minimal assumption-sets whose JOINT failure changes the verdict from
    its baseline. Size-1 cores are exactly the single-toggle load-bearing hinges (so this SUBSUMES
    `decision_sensitivity`); size≥2 cores are the jointly-pivotal sets it cannot see. Brute-force up to
    `max_size` — exact but exponential; the argument graphs here are small. ponytail: max_size caps the search;
    raise it (or switch to a real prime-implicant/QuickXplain enumerator) only if graphs grow past a few dozen
    assumptions."""
    from ztare.common.hitting_sets import minimal_hitting_sets

    base = verdict(governed)
    return minimal_hitting_sets(
        assumptions(governed),
        lambda cs: verdict(governed, cs) != base,
        max_size,
    )


def dominators(governed: GovernedState) -> "list[str]":
    """The claims that sit on EVERY support path from evidence to a target — removing one disconnects the target
    from all evidence (a purely structural, devastating finding: 'your whole conclusion routes through this one
    claim'). Deterministic graph reachability, no semantics."""
    support = [(e.src, e.dst) for e in governed.edges if e.kind in _SUPPORT]
    evidence = {e.id for e in governed.of_kind("evidence")}
    targets = _targets(governed)

    def reaches_target(blocked: str) -> bool:
        seen = set(evidence) - {blocked}
        frontier = list(seen)
        while frontier:
            n = frontier.pop()
            for src, dst in support:
                if src == n and dst not in seen and dst != blocked:
                    seen.add(dst)
                    frontier.append(dst)
        return any(t in seen for t in targets)

    base_reachable = reaches_target(blocked="")
    return sorted(c.id for c in _claims(governed)
                  if c.id not in targets and base_reachable and not reaches_target(c.id))


def warrant_ceiling(governed: GovernedState, accepted: "set[str] | None" = None) -> str:
    """Monotone-in-warrant: the verdict's trust is capped by the WEAKEST warrant on any accepted support edge
    into a target (or a claim on a support path to it). Returns the ceiling warrant class ('W3' if any
    load-bearing edge is proposed-unchecked). '' when there is no support at all."""
    accepted = accepted if accepted is not None else _accepted(governed, frozenset())
    load_bearing = [edge for edge in governed.edges
                    if edge.kind in _SUPPORT and edge.src in accepted and edge.dst in accepted]
    if not load_bearing:
        return ""
    return min((edge_warrant(e) for e in load_bearing), key=lambda w: WARRANT_RANK[w])


def test_agenda(governed: GovernedState, *, cost: "dict[str, float] | None" = None,
                cores: "list[frozenset[str]] | None" = None,
                accepted_nodes: "set[str] | None" = None) -> "list[dict]":
    """The POSSIBILISTIC test agenda (Fable — deterministic, no invented priors): rank the UNTESTED assumptions
    by (a) does testing it flip the verdict on its own (size-1 core), (b) how many minimal cores it sits in
    (joint pivotalness), (c) declared cost from the mandate. 'What do I test next' — the domain-neutral daily
    driver. (The old query-by-committee `identification` column was provably 1.0 iff `flips_alone` — a Shannon
    restatement of the first key — and was cut in the Fable de-slop. Value-of-information ranking lives once, in
    the unified wager agenda.)"""
    cores = minimal_cores(governed) if cores is None else cores
    accepted = _accepted(governed, frozenset()) if accepted_nodes is None else accepted_nodes
    supported = {e.dst for e in governed.edges if e.kind in _SUPPORT and e.src in accepted}
    # untested = a claim with no accepted support yet, or an open finding.
    untested = [a for a in assumptions(governed) if a not in supported]
    cost = cost or {}
    agenda = [{"assumption": a, "flips_alone": frozenset({a}) in cores,
               "in_cores": sum(1 for c in cores if a in c), "cost": float(cost.get(a, 1.0))}
              for a in untested]
    agenda.sort(key=lambda r: (not r["flips_alone"], -r["in_cores"], r["cost"], r["assumption"]))
    return agenda


def verdict_reason(governed: GovernedState, *, status: "str | None" = None,
                   core_count: "int | None" = None) -> str:
    """A human, actionable one-liner for the verdict — what it means and what to do next. The bare status
    (SUPPORTED/BLOCKED/REFUTED) is for machines; this is what a person reads. It separates the common
    'BLOCKED because nothing is bound yet' (a workflow step, not a failure) from 'BLOCKED because a tension is
    open' so the next action is obvious rather than a cryptic status. Single door: every surface uses it."""
    status = status or verdict(governed)
    if status == "REFUTED":
        return "A load-bearing claim is contradicted by an evidence-rooted node — the decision does not stand as written."
    if status == "SUPPORTED":
        n = len(minimal_cores(governed)) if core_count is None else core_count
        return f"Every claim this decision rests on is evidence-rooted; {n} minimal core(s) show what it turns on."
    if not governed.of_kind("evidence"):
        return ("No evidence is bound to this decision yet — fetch or compile evidence for the open gaps, then "
                "re-run. Nothing grounds the decision, so it cannot be graded (this is a workflow step, not a failure).")
    accepted = _accepted(governed, frozenset())
    claims = _claims(governed)
    grounded_claims = sum(1 for claim in claims if claim.id in accepted)
    targets = _targets(governed)
    if any(target not in accepted for target in targets):
        if claims and grounded_claims == 0:
            return (f"Sources are mapped, but none of the {len(claims)} decision claims has admitted support. "
                    "The run score evaluates the draft; it does not establish the claim-to-source inferences.")
        if claims:
            return (f"{grounded_claims} of {len(claims)} decision claims have admitted support, but the "
                    "conclusion is not fully grounded yet. Verify the remaining claim-to-source inferences.")
    open_findings = _open_findings(governed)
    if open_findings:
        count = len(open_findings)
        noun = "issue remains" if count == 1 else "issues remain"
        return (f"{count} unresolved {noun} — see the test agenda for the cheapest question to close next.")
    return ("A claim this decision rests on is not yet evidence-rooted — connect supporting evidence or drop the "
            "claim. See the test agenda.")


def argument_analysis(governed: GovernedState) -> dict:
    """The JSON-able argument-kernel bundle for the artifact / brief / CLI: the grounded verdict, a human-readable
    reason, the minimal cores (set-valued, not a scalar), the dominators, the warrant ceiling, and the test
    agenda. One call so every surface reads the same principled analysis."""
    from collections import Counter

    accepted = _accepted(governed, frozenset())
    status = _verdict_from_accepted(governed, frozenset(), accepted)
    cores = minimal_cores(governed)
    counts = Counter(assumption for core in cores for assumption in core)
    highest = max(counts.values(), default=0)
    hinge_ties = sorted(assumption for assumption, count in counts.items() if count == highest) if highest else []
    attacked = {edge.dst for edge in governed.edges if edge.kind in _ATTACK and edge.src in accepted}
    claims = _claims(governed)
    coverage = round(sum(1 for claim in claims if claim.id in accepted) / len(claims), 3) if claims else 0.0
    bundle = {
        "verdict": status,
        "reason": verdict_reason(governed, status=status, core_count=len(cores)),
        "coverage": coverage,
        "warrant_ceiling": warrant_ceiling(governed, accepted),
        "minimal_cores": [sorted(core) for core in cores],
        "hinge": hinge_ties[0] if hinge_ties else "",
        "hinge_ties": hinge_ties,
        "dominators": dominators(governed),
        "test_agenda": test_agenda(governed, cores=cores, accepted_nodes=accepted),
        "node_states": {
            element.id: claim_status(governed, element.id, accepted, attacked)
            for element in governed.elements
        },
    }
    # Graded strength (QEM warrant-filtration profile + override status) — CHEAP (a few fixed-point solves on a
    # small graph), so it rides the hot path. Shapley "what it rests on" is 2^n and lives behind `shapley_support`
    # for the brief/rests-on surface, NOT here. Lazy import (strength depends on this module) + additive.
    try:
        from ztare.scenarios.strength import strength_profile
        sp = strength_profile(governed)
        bundle["strength"] = {
            "profile": sp["profile"], "status": sp["status"], "converged": sp["converged"],
            "per_node": sp.get("per_node", {}),
        }
    except Exception:  # noqa: BLE001
        pass
    return bundle


def claim_status(governed: GovernedState, cid: str,
                 accepted: "set[str] | None" = None, attacked: "set[str] | None" = None) -> str:
    """A claim's lifecycle state under grounded acceptance: CONTRADICTED (attacked by an accepted node) >
    BACKED (accepted) > UNTESTED. The per-claim view `annotate` shows; here it's derived from the SAME grounded
    kernel so annotation and verdict can never disagree."""
    if accepted is None:
        accepted = _accepted(governed, frozenset())
    if attacked is None:
        attacked = {e.dst for e in governed.edges if e.kind in _ATTACK and e.src in accepted}
    if cid in attacked:
        return "CONTRADICTED"
    if cid in accepted:
        return "BACKED"
    return "UNTESTED"


def recompile(old: GovernedState, new: GovernedState) -> dict:
    """Incremental recompilation (Fable EQ3) — a `make` for arguments. Recompute the verdict against a NEW
    governed state (new evidence bound, an assumption flipped) and return the DIFF: which claims changed
    lifecycle state, whether the DECISION went stale, and the re-ranked test agenda. This is an ATMS label
    update promoted to a first-class product event — *'assumption A4 flipped to CONTRADICTED by the new data;
    your decision now stands on a refuted hinge — here's the diff and the cheapest test.'* Domain-neutral: the
    identical call serves the scientist (new dataset vs. manuscript) and the mathematician (dep bump vs. proof)."""
    was, now = verdict(old), verdict(new)
    oa = _accepted(old, frozenset())
    oatt = {e.dst for e in old.edges if e.kind in _ATTACK and e.src in oa}
    na = _accepted(new, frozenset())
    natt = {e.dst for e in new.edges if e.kind in _ATTACK and e.src in na}
    flipped: "list[dict]" = []
    for cid in sorted({c.id for c in _claims(old)} | {c.id for c in _claims(new)}):
        so = claim_status(old, cid, oa, oatt) if old.by_id(cid) else "ABSENT"
        sn = claim_status(new, cid, na, natt) if new.by_id(cid) else "ABSENT"
        if so != sn:
            flipped.append({"id": cid, "was": so, "now": sn})
    return {"was": was, "now": now, "decision_stale": was != now, "flipped": flipped,
            "agenda": test_agenda(new)}


def _selftest() -> int:
    from ztare.scenarios.governed_types import GovernedEdge, GovernedElement

    fails: "list[str]" = []

    def ok(name: str, cond: bool) -> None:
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    # THE joint-pivot graph: thesis supported by TWO independent claims (c1, c2). Neither alone is load-bearing;
    # TOGETHER they are. This is the case single-toggle `decision_sensitivity` provably misses.
    g = GovernedState(
        [GovernedElement("t", "thesis", "T"), GovernedElement("c1", "claim", "C1"),
         GovernedElement("c2", "claim", "C2"), GovernedElement("e1", "evidence", "E1"),
         GovernedElement("e2", "evidence", "E2")],
        [GovernedEdge("e1", "SUPPORTS", "c1"), GovernedEdge("e2", "SUPPORTS", "c2"),
         GovernedEdge("c1", "SUPPORTS", "t"), GovernedEdge("c2", "SUPPORTS", "t")])
    ok("baseline verdict is SUPPORTED (grounded acceptance)", verdict(g) == "SUPPORTED")
    ok("failing EITHER support alone does NOT flip (redundant supports)",
       verdict(g, frozenset({"c1"})) == "SUPPORTED" and verdict(g, frozenset({"c2"})) == "SUPPORTED")
    ok("failing BOTH flips the verdict (joint pivot)", verdict(g, frozenset({"c1", "c2"})) != "SUPPORTED")
    cores = minimal_cores(g)
    ok("the joint pivot {c1,c2} IS a minimal core", frozenset({"c1", "c2"}) in cores)
    ok("neither singleton {c1} nor {c2} is a core (single-toggle would report NO hinge)",
       frozenset({"c1"}) not in cores and frozenset({"c2"}) not in cores)

    # A single-support chain: the one claim is a dominator + a size-1 core.
    chain = GovernedState(
        [GovernedElement("t", "thesis", "T"), GovernedElement("c", "claim", "C"),
         GovernedElement("e", "evidence", "E")],
        [GovernedEdge("e", "SUPPORTS", "c", "W1"), GovernedEdge("c", "SUPPORTS", "t", "W1")])
    ok("the sole intermediate claim is a dominator", dominators(chain) == ["c"])
    ok("dropping it is a size-1 core", frozenset({"c"}) in minimal_cores(chain))
    ok("warrant ceiling = the weakest load-bearing warrant (all W1 here → W1)", warrant_ceiling(chain) == "W1")
    ok("a single proposed-unchecked support caps the ceiling at W3 (monotone-in-warrant)",
       warrant_ceiling(GovernedState(list(chain.elements),
                        [GovernedEdge("e", "SUPPORTS", "c"), GovernedEdge("c", "SUPPORTS", "t", "W1")])) == "W3")

    # REFUTED via an accepted attacker; BLOCKED via an open gap.
    ref = GovernedState([GovernedElement("t", "thesis", "T"), GovernedElement("f", "evidence", "F")],
                        [GovernedEdge("f", "FALSIFIES", "t")])
    ok("an accepted attacker REFUTES the target", verdict(ref) == "REFUTED")
    blk = GovernedState([GovernedElement("t", "thesis", "T"), GovernedElement("e", "evidence", "E"),
                         GovernedElement("g", "gap", "open"), GovernedElement("c", "claim", "C")],
                        [GovernedEdge("e", "SUPPORTS", "t")])
    ok("an open gap BLOCKS", verdict(blk) == "BLOCKED")
    mapped_not_admitted = GovernedState(
        [GovernedElement("t", "thesis", "T"), GovernedElement("c", "claim", "C"),
         GovernedElement("e", "evidence", "E"), GovernedElement("g", "gap", "open")],
        [GovernedEdge("e", "REPORTS", "g")])
    ok("blocked reason leads with missing admitted support before secondary gaps",
       "none of the 2 decision claims has admitted support" in verdict_reason(mapped_not_admitted))

    # test agenda: an unsupported claim `c` is untested → it must surface in the agenda.
    ag = test_agenda(GovernedState(
        [GovernedElement("t", "thesis", "T"), GovernedElement("c", "claim", "C"),
         GovernedElement("e", "evidence", "E")],
        [GovernedEdge("e", "SUPPORTS", "t")]))  # c has no support edge → untested
    ok("test agenda surfaces the untested assumption", any(r["assumption"] == "c" for r in ag))
    ok("agenda ranks by flip / joint-pivotalness / cost (no dead identification column)",
       all({"flips_alone", "in_cores", "cost"} <= set(r) and "identification" not in r for r in ag))

    # incremental recompile / stale-decision diff: new evidence attacks the thesis → the decision goes stale, diff shows it.
    old_state = GovernedState([GovernedElement("t", "thesis", "T"), GovernedElement("e", "evidence", "E")],
                              [GovernedEdge("e", "SUPPORTS", "t", "W2")])
    new_state = GovernedState(list(old_state.elements) + [GovernedElement("f", "evidence", "NewData")],
                              list(old_state.edges) + [GovernedEdge("f", "FALSIFIES", "t")])
    rc = recompile(old_state, new_state)
    ok("recompile detects a decision gone stale (SUPPORTED → REFUTED)",
       rc["was"] == "SUPPORTED" and rc["now"] == "REFUTED" and rc["decision_stale"])
    ok("recompile diffs the flipped claim (BACKED → CONTRADICTED)",
       any(f["id"] == "t" and f["was"] == "BACKED" and f["now"] == "CONTRADICTED" for f in rc["flipped"]))
    ok("recompile returns a re-ranked test agenda", "agenda" in rc)
    ok("claim_status agrees with the grounded verdict (no annotate/verdict drift)",
       claim_status(old_state, "t") == "BACKED" and claim_status(new_state, "t") == "CONTRADICTED")

    print("ARGUMENT-KERNEL SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
