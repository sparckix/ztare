"""The unified AGENDA — ONE door for "what do I test next", whoever authored the candidate (Fable eigenreview:
the AGENDA cell had 5+ parallel rankers that could silently disagree and drift). Everything is normalized to a
WAGER (a test + typed, verdict-simulatable outcomes), and ranked once, at read time, off the frozen graph — no
persisted ranking. Candidates:

  1. IMPLICIT wagers the graph itself implies — for each untested/weak assumption, the standard experiment
     "back it, refute it, or come back inconclusive" (kernel-built, no LLM). The kernel COMPUTES the bits/moves;
     it does NOT declare cost or exhaustiveness on the human's behalf (that would violate "dollars declared,
     bits computed") — implicit cost is None, and an explicit `inconclusive` outcome keeps the set honest.
  2. DECLARED wagers (the human's lateral bets).
  3. LOOP discriminators, translated (`discriminator_to_wager`) — text-matched to a real claim or FAIL CLOSED.

Admission is the graded flip, not float noise: a candidate enters iff it FLIPS the crisp verdict, or CHANGES the
graded status across the override lattice, or moves the profile by ≥ a declared materiality. Ranking is NOT a
lossy scalar: each candidate keeps its lens-scores (info-yield bits, severity, cost), and the Pareto
NON-DOMINATED FRONTIER is surfaced as "the real tradeoff choices" (operator: dissent is signal; MCDA: a single
weighted collapse is rank-reversal-unstable). `rank` is only the default-view order."""
from __future__ import annotations

MATERIALITY = 0.05  # declared display threshold: a profile move smaller than this is not decision-material


def implicit_wagers(governed) -> list:
    """The standing wagers the graph implies: per untested assumption, a MECE outcome set — findings get
    resolve/corroborate/inconclusive, claims get confirm/refute/inconclusive. Kernel-built, typed. The kernel
    does not declare cost (None) or fake a two-outcome MECE (the explicit `inconclusive` no-edit outcome is why
    `exhaustive=True` is honest and why `severe` correctly stays false — a test that can null isn't severe)."""
    from ztare.scenarios.argument_kernel import test_agenda
    from ztare.scenarios.wager import GraphEdit, Outcome, Wager

    inconclusive = Outcome("inconclusive", (), label="The test is inconclusive")  # a real null result
    out: list = []
    for row in test_agenda(governed):
        a = row["assumption"]
        el = governed.by_id(a)
        label = el.text if el else a
        if el and el.kind in ("tension", "gap"):
            resolved = Outcome("resolved", (GraphEdit("rule_out", a, source=f"ev.test.{a}.r",
                                                      text=f"resolves benignly: {label}", warrant="W2"),),
                               label="The open issue resolves benignly")
            corroborated = Outcome("corroborated", (GraphEdit("add_evidence", f"ev.test.{a}.c", text=f"corroborates: {label}"),
                                                    GraphEdit("support", a, source=f"ev.test.{a}.c", warrant="W2")),
                                   label="The evidence corroborates the claim")
            out.append(Wager(f"implicit:{a}", a, f"resolve the open question: {label}",
                             (resolved, corroborated, inconclusive), exhaustive=True, stakes="implicit"))
        else:
            confirmed = Outcome("confirmed", (GraphEdit("add_evidence", f"ev.test.{a}.c", text=f"backing for: {label}"),
                                              GraphEdit("support", a, source=f"ev.test.{a}.c", warrant="W2")),
                               label="The evidence confirms the claim")
            refuted = Outcome("refuted", (GraphEdit("add_evidence", f"ev.test.{a}.r", text=f"counter to: {label}"),
                                          GraphEdit("attack", a, source=f"ev.test.{a}.r", relation="CONTRADICTS", warrant="W2")),
                             label="The evidence contradicts the claim")
            out.append(Wager(f"implicit:{a}", a, f"gather evidence on: {label}",
                             (confirmed, refuted, inconclusive), exhaustive=True, stakes="implicit"))
    return out


def discriminator_to_wager(proposal, governed):
    """The loop→kernel bridge: translate a DiscriminatorProposal (dict or object) into a Wager. The loop names
    its claim by TEXT, so we normalized-TEXT-MATCH `claim_under_pressure` to a real element and target THAT —
    or, when the claim is empty and the graph has exactly one target, that target. Otherwise FAIL CLOSED (never
    silently retarget the wrong node — that would simulate the wrong counterfactual). Deterministic id (hashlib,
    not salted hash()). Returns None on no match / no typed outcome — a quality gate on the inverter."""
    import hashlib

    from ztare.scenarios.argument_kernel import _targets
    from ztare.scenarios.governed_types import normalize
    from ztare.scenarios.wager import GraphEdit, Outcome, Wager

    get = proposal.get if isinstance(proposal, dict) else (lambda k, d=None: getattr(proposal, k, d))
    kill = str(get("kill_condition") or "").strip()
    test = str(get("cheapest_discriminator") or "").strip()
    claim = str(get("claim_under_pressure") or "").strip()
    if not (kill and test):
        return None
    nc = normalize(claim)
    tgt = None
    if nc:  # match the loop's claim to graph elements; substring either way (claim is often the full thesis text)
        matches = [el.id for el in governed.elements
                   if (ne := normalize(el.text)) and (ne in nc or nc in ne)]
        tgt = matches[0] if len(matches) == 1 else None  # ≥2 ambiguous ⇒ fail closed, never silently retarget (Fable)
    else:
        tgts = _targets(governed)
        tgt = tgts[0] if len(tgts) == 1 else None
    if tgt is None:  # fail closed — no confident target
        return None
    tag = hashlib.sha256(f"{claim}|{test}|{tgt}".encode()).hexdigest()[:10]
    killed = Outcome("killed", (GraphEdit("add_evidence", f"ev.disc.{tag}.k", text=kill[:120]),
                                GraphEdit("attack", tgt, source=f"ev.disc.{tag}.k", relation="CONTRADICTS", warrant="W2")),
                   label="The test fails the claim")
    survived = Outcome("survived", (GraphEdit("add_evidence", f"ev.disc.{tag}.s", text=test[:120]),
                                    GraphEdit("support", tgt, source=f"ev.disc.{tag}.s", warrant="W2")),
                      label="The test supports the claim")
    cost = get("cost_estimate") or {}
    dc = float(cost["value"]) if isinstance(cost, dict) and "value" in cost else -1.0  # -1 = the loop declared none
    return Wager(f"disc:{tag}", tgt, test, (killed, survived, Outcome("inconclusive", (), label="The test is inconclusive")),
                 declared_cost=dc, exhaustive=True, stakes="loop-proposed")


def _row_cost(w) -> "float | None":
    """The DECLARED cost, or None when undeclared (implicit kernel wagers never declare; a loop wager may not).
    None sorts WORST on the cost lens — you cannot claim a bet is cheap without declaring it."""
    if w.stakes == "implicit" or w.declared_cost < 0:
        return None
    return float(w.declared_cost)


def unified_agenda(governed, declared: "list | None" = None, discriminators: "list | None" = None) -> "list[dict]":
    """The ONE ranking. Union implicit + declared + translated-discriminator wagers; admit on graded flip
    (crisp-flip OR status-change OR ≥ materiality); keep each lens-score; mark the Pareto non-dominated frontier;
    stamp a default-view `rank`. Read-time, deterministic."""
    from ztare.scenarios.wager import simulate, strength_displacement

    cands = list(implicit_wagers(governed)) + list(declared or [])
    for d in (discriminators or []):
        w = discriminator_to_wager(d, governed)
        if w is not None:
            cands.append(w)

    rows: "list[dict]" = []
    for w in cands:
        if w.lifecycle != "open":
            continue
        sim = simulate(governed, w)
        disp = strength_displacement(governed, w)
        max_disp = disp.get("max_displacement") or []
        material = any(float(x) >= MATERIALITY for x in max_disp)
        # The shape/exhaustiveness/edit gate is shared with the crisp simulator before the graded lane can admit
        # a status or materiality move. Otherwise a one-sided or partially malformed test could bypass the wager
        # contract through the strength shortcut.
        if not (sim.get("outcome_shape_valid") and sim.get("exhaustive") and sim.get("all_edits_valid")):
            continue
        # Admit on a GRADED FLIP: crisp verdict flip, OR override-lattice status change, OR a material profile
        # move. Not ε-noise (Fable).
        if not (sim.get("admissible") or disp.get("status_change") or material):
            continue
        outcome_specs = []
        for outcome in w.outcomes:
            operations = {edit.op for edit in outcome.edits}
            consequence = "contradict" if "attack" in operations else "support" if operations & {"support", "rule_out"} else "inconclusive"
            warrant = next((edit.warrant for edit in outcome.edits if edit.op in {"support", "attack", "rule_out"}), "W3")
            outcome_specs.append({"id": outcome.id, "label": outcome.label or outcome.id, "consequence": consequence, "warrant": warrant})
        target = governed.by_id(w.claim_ref)
        rows.append({"id": w.id, "test": w.test, "claim_ref": w.claim_ref,
                     "claim_text": target.text if target else "",
                     "source": (w.stakes if w.stakes in ("implicit", "loop-proposed") else "declared"),
                     "outcome_specs": outcome_specs,
                     "bits": float(sim.get("identification_bits", 0.0)), "cost": _row_cost(w),
                     "severe": bool(disp.get("severe")), "status_change": bool(disp.get("status_change")),
                     "min_displacement": list(disp.get("min_displacement") or []), "max_displacement": list(max_disp),
                     "flips_crisp": bool(sim.get("admissible"))})
    if not rows:
        return []

    # Lens scalars for ranking + Pareto: bits↑, severity↑ (biggest single-tier move), cost↓ (None = worst).
    def _sev(r):
        return max(r["max_displacement"]) if r["max_displacement"] else 0.0

    def _costk(r):
        return r["cost"] if r["cost"] is not None else float("inf")

    def _ranks(scalar, high_wins):
        order = sorted(rows, key=lambda r: (-scalar(r), r["id"]) if high_wins else (scalar(r), r["id"]))
        return {r["id"]: i + 1 for i, r in enumerate(order)}

    by_bits = _ranks(lambda r: r["bits"], True)
    by_sev = _ranks(_sev, True)
    by_cost = _ranks(_costk, False)

    # Pareto non-dominated FRONTIER: r is dominated if some other candidate is ≥ on bits & severity AND ≤ on cost,
    # with at least one strict. The frontier = the real tradeoff choices; everything else is strictly worse.
    def _dominates(a, b):
        ge = a["bits"] >= b["bits"] and _sev(a) >= _sev(b) and _costk(a) <= _costk(b)
        gt = a["bits"] > b["bits"] or _sev(a) > _sev(b) or _costk(a) < _costk(b)
        return ge and gt

    for r in rows:
        r["rank_by_bits"], r["rank_by_severity"], r["rank_by_cost"] = by_bits[r["id"]], by_sev[r["id"]], by_cost[r["id"]]
        r["on_frontier"] = not any(_dominates(o, r) for o in rows if o["id"] != r["id"])

    # default-view order (NOT a claim of one true ranking): frontier first, then bits, severity, cheaper cost.
    rows.sort(key=lambda r: (not r["on_frontier"], -r["bits"], -_sev(r), _costk(r), r["id"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


def _load_discriminators(project: str, repo_root) -> "list[dict]":
    """The loop's proposed discriminators (next_discriminator_queue.jsonl) as raw dicts, for translation."""
    import json
    from pathlib import Path

    p = Path(repo_root) / "projects" / project / "workspace" / "next_discriminator_queue.jsonl"
    if not p.is_file():
        return []
    out: "list[dict]" = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except Exception:  # noqa: BLE001 — a malformed line is skipped, never crashes the agenda
                pass
    return out


def project_agenda(project: str, repo_root) -> "list[dict]":
    """The unified agenda for a real project: the graph's implicit wagers + the human's declared wagers + the
    loop's proposed discriminators (translated), ranked once with the Pareto frontier marked. The single
    'what to test next' door for a PM."""
    from ztare.scenarios.adapters import governed_state_from_research_map
    from ztare.scenarios.wager import load_wagers, wager_from_payload

    g = governed_state_from_research_map(project, repo_root)
    if not g.elements:
        return []
    declared = [wager_from_payload(p) for p in load_wagers(project)]
    return unified_agenda(g, declared=declared, discriminators=_load_discriminators(project, repo_root))


def emit_governed_agenda(project: str, repo_root) -> dict:
    """CLOSE THE LOOP, kernel side: write the GOVERNED ranking of 'what to test next' to a stable artifact the
    autoresearch loop can act on. Today the loop PROPOSES discriminators (next_discriminator_queue.jsonl) and the
    kernel RANKS them (`unified_agenda`: governed VoI + Pareto + ONE admission gate) — but the loop picks its next
    action by its own order, so the two lanes can disagree (Fable's two-verdict split). This emits the governed
    ranking BACK so the loop can steer by the same order it's judged on. Each loop-proposed row carries a
    `source_discriminator` back-reference (the loop's own {claim, test, kill} key) so the loop matches a governed
    rank to its queue entry. Producer + contract only — the in-loop consumption lives in the loop (do not edit the
    457KB autoresearch_loop.py from here). Deterministic, no LLM. Returns {path, count, top, frontier}."""
    import json
    from pathlib import Path

    rows = project_agenda(project, repo_root)
    discs = _load_discriminators(project, repo_root)
    for r in rows:
        if r.get("source") == "loop-proposed":
            probe = (r.get("test") or "")[:40]  # wager.test = cheapest_discriminator[:56]; 40 is a distinctive key
            match = next((d for d in discs if str(d.get("cheapest_discriminator") or "").startswith(probe)), None)
            if match:
                r["source_discriminator"] = {k: match.get(k) for k in
                                             ("claim_under_pressure", "cheapest_discriminator", "kill_condition")}
    out = Path(repo_root) / "projects" / project / "workspace" / "governed_agenda.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return {"path": str(out), "count": len(rows), "top": (rows[0] if rows else None),
            "frontier": [r["id"] for r in rows if r.get("on_frontier")]}


def _selftest() -> int:
    from ztare.scenarios.governed_types import GovernedEdge, GovernedElement, GovernedState

    # a thesis grounded through claim c (untested) — testing c flips the verdict, so it makes the agenda.
    g = GovernedState(
        [GovernedElement("t", "thesis", "the bet pays off"), GovernedElement("c", "claim", "users adopt it"),
         GovernedElement("e", "evidence", "a weak signal")],
        [GovernedEdge("e", "SUPPORTS", "c", "W3")])
    rows = unified_agenda(g)
    assert rows, "an untested load-bearing assumption must yield at least one implicit wager"
    assert all({"rank", "on_frontier", "bits", "cost"} <= set(r) for r in rows), rows
    assert all(r["source"] == "implicit" and r["cost"] is None for r in rows), "kernel must NOT declare cost"
    assert any(r["on_frontier"] for r in rows), "the frontier is never empty"

    # the loop→kernel bridge: a well-formed discriminator matching the thesis text translates + enters the agenda;
    # a malformed one, and one whose claim matches NO element, both FAIL CLOSED.
    good = {"claim_under_pressure": "the bet pays off", "cheapest_discriminator": "run the pilot",
            "kill_condition": "pilot adoption < 20%", "cost_estimate": {"value": 3.0}}
    bad = {"claim_under_pressure": "the bet pays off", "cheapest_discriminator": "", "kill_condition": ""}
    nomatch = {"claim_under_pressure": "an unrelated claim about weather", "cheapest_discriminator": "x", "kill_condition": "y"}
    assert discriminator_to_wager(good, g) is not None, "well-formed + text-matched discriminator must translate"
    assert discriminator_to_wager(bad, g) is None, "no typed outcome → fail closed"
    assert discriminator_to_wager(nomatch, g) is None, "claim matching no element → fail closed (no silent retarget)"
    # determinism: same input → same id, twice.
    assert discriminator_to_wager(good, g).id == discriminator_to_wager(good, g).id, "id must be deterministic"
    with_loop = unified_agenda(g, discriminators=[good, bad, nomatch])
    loop_rows = [r for r in with_loop if r["source"] == "loop-proposed"]
    assert len(loop_rows) == 1 and loop_rows[0]["cost"] == 3.0, with_loop  # exactly the good one; its declared cost

    print("AGENDA SELFTEST PASSED",
          {"n": len(rows), "frontier": sum(r["on_frontier"] for r in with_loop), "loop": len(loop_rows)})
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
