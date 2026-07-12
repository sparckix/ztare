"""Wager — a protected, thin-evidence LATERAL BET on a BLOCKED claim, scored prior-free.

The grounded verdict is symmetric in payoff: a bold thin-evidence bet with huge asymmetric upside grades
identically to a thin-evidence dead end (both BLOCKED). A `wager` gives the bet dignity WITHOUT laundering it
into a fact: the claim stays BLOCKED (a wager is NOT a fourth epistemic verdict — that would be an idea-parking
exemption), but the wager is a first-class object that names a real experiment and is ranked by how much the
test would move the decision.

Design (all classical parts, novel COMBINATION): prior-free experiment ranking over deterministically
recompiled warrant graphs, with a verdict-preserving lifecycle and anti-laundering expiry. What is COMPUTED vs.
DECLARED is the whole moat: bits and flips are computed (deterministic functions of the graph); dollars and odds
are declared (displayed verbatim, never aggregated). Specifically —

- The outcome→graph-edit map is the ONE uncompromising contract. Each edit is TYPED (evidence and relations,
  never a verdict), warrant-scoped, and NAMES the exact node/edge it changes. The kernel simulates EVERY
  declared outcome (not only the favorable one) by `recompile`; no edit may set the verdict — `recompile` alone
  derives it.
- Wager outcomes cannot promote an existing edge's warrant. Stronger backing is earned through the dedicated
  recheck/promotion door, which runs a bound check and records a receipt; otherwise a test would mint trust by
  declaration and drift from the warrant ledger.
- A decision test must name at least two unique plausible outcomes. The author attests that the set is exhaustive;
  an explicitly inconclusive outcome is the honest third branch when the observation may fail to resolve the issue.
- `flip` is an ADMISSIBILITY GATE, not a ranking signal (so nobody optimizes flips): a wager is admissible iff
  the author attests the outcomes are exhaustive, every edit is valid, and AT LEAST ONE outcome changes the
  compiled decision. Admissible wagers rank by `identification_bits` (Shannon info-yield over the PRE-baseline
  minimal cores — anti-gaming: junk authored after registration can't pump it), then by declared cost.
- Anti-laundering teeth (both essential): no simulated flip ⇒ not a wager; deadline reached ⇒ auto-expires back
  to ordinary BLOCKED backlog; extending a deadline REQUIRES a fresh evidence/feasibility receipt (else wagers
  roll forward forever).

Reuses `recompile` / `verdict` / `minimal_cores` (argument_kernel) and `identification_bits`
(information_yield_pricing). Deterministic, no LLM, no priors.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from ztare.common.information_yield_pricing import identification_bits
from ztare.scenarios.argument_kernel import _ATTACK, minimal_cores, recompile, verdict
from ztare.scenarios.governed_types import GovernedEdge, GovernedElement, GovernedState

# The ONLY edits an outcome may make — each modifies EVIDENCE or WARRANTS; none sets a verdict/status (there is
# no such field, and `recompile` alone derives the verdict). This allowlist IS the trust boundary.
EDIT_OPS = ("add_evidence", "support", "attack", "rule_out")
_WARRANTS = ("W0", "W1", "W2", "W3")


@dataclass(frozen=True)
class GraphEdit:
    """One typed, warrant-scoped edit that NAMES exactly what it changes. `add_evidence` adds a ground node;
    `support`/`attack` bind a new edge from `source` to the `target` claim. Warrant promotion is a separate
    check/recheck operation. Nothing here can assert a verdict."""
    op: str
    target: str            # the node/edge endpoint this edit changes (named exactly)
    source: str = ""       # evidence/source node id (support/attack/set_warrant)
    relation: str = ""     # CONTRADICTS|FALSIFIES (attack) / the edge kind (set_warrant)
    warrant: str = "W3"
    text: str = ""         # add_evidence node text


@dataclass(frozen=True)
class Outcome:
    """A declared outcome of the test + the graph edits it would license. The kernel simulates ALL of them."""
    id: str
    edits: "tuple[GraphEdit, ...]" = ()
    label: str = ""  # human observation label; the id remains the stable execution key


@dataclass(frozen=True)
class Wager:
    """A protected lateral bet on a BLOCKED claim. `lifecycle` never touches the claim's verdict. Declared fields
    (cost, deadline, exhaustive, stakes) are the human's attestations — displayed, never aggregated into a score."""
    id: str
    claim_ref: str
    test: str
    outcomes: "tuple[Outcome, ...]" = ()
    declared_cost: float = 0.0
    deadline: str = ""             # ISO date; declared. Compared lexicographically (ISO sorts correctly).
    exhaustive: bool = False       # author attests the outcome set is collectively exhaustive (declared, like stakes)
    stakes: str = ""               # declared payoff-direction free text — shown, never scored
    lifecycle: str = "open"        # open | executed | expired | invalidated
    receipt: str = ""              # evidence/feasibility receipt backing the CURRENT deadline
    resolved_outcome: str = ""      # durable execution receipt; empty until lifecycle=executed


def apply_edit(state: GovernedState, edit: GraphEdit) -> GovernedState:
    """Apply one typed edit, returning a NEW state (the base is never mutated). Fail-closed: any illegal op,
    bad warrant, missing target, or edge-that-doesn't-exist raises — so a malformed outcome can never silently
    count toward admissibility."""
    if edit.op not in EDIT_OPS:
        raise ValueError(f"illegal edit op {edit.op!r} — an edit may modify evidence/warrants, never the verdict "
                         f"(allowed: {EDIT_OPS})")
    if edit.warrant not in _WARRANTS:
        raise ValueError(f"edit warrant must be one of {_WARRANTS}, got {edit.warrant!r}")
    elements, edges = list(state.elements), list(state.edges)
    if edit.op == "add_evidence":
        if not edit.target or not edit.text.strip():
            raise ValueError("add_evidence needs a target id and text")
        if state.by_id(edit.target):
            raise ValueError(f"add_evidence target {edit.target!r} already exists")
        elements.append(GovernedElement(edit.target, "evidence", edit.text))
    elif edit.op in ("support", "attack"):
        if not edit.source or not edit.target:
            raise ValueError(f"{edit.op} names a source and a target")
        if not state.by_id(edit.target):
            raise ValueError(f"{edit.op} target claim {edit.target!r} is not in the graph")
        if not state.by_id(edit.source):  # fail-closed per the module contract (Fable): an edge from a phantom
            raise ValueError(f"{edit.op} source {edit.source!r} is not in the graph — add it via add_evidence "
                             f"first (a dangling attacker would crash the strength solve, not silently no-op)")
        rel = "SUPPORTS" if edit.op == "support" else (edit.relation if edit.relation in _ATTACK else "CONTRADICTS")
        edges.append(GovernedEdge(edit.source, rel, edit.target, edit.warrant))
    elif edit.op == "rule_out":
        # Resolve an OPEN finding (tension/gap): a RULED_OUT edge FROM the finding marks it settled
        # (argument_kernel._open_findings + strength._stratum_edges), which flips a map BLOCKED solely by that
        # finding — the "this tension resolves benignly" outcome. Never asserts a verdict; it retires a defeater.
        # Fail-closed on a non-finding target (a typo'd id), like support/attack validate their endpoints.
        _tgt = state.by_id(edit.target)
        if _tgt is None or _tgt.kind not in ("tension", "gap"):
            raise ValueError(f"rule_out names an OPEN FINDING (tension/gap), got {edit.target!r}")
        if edit.source and not state.by_id(edit.source):
            elements.append(GovernedElement(edit.source, "evidence", edit.text or f"resolves {edit.target}"))
        edges.append(GovernedEdge(edit.target, "RULED_OUT", edit.source or edit.target, edit.warrant))
    return GovernedState(elements, edges)


def apply_outcome(state: GovernedState, outcome: Outcome) -> GovernedState:
    """Apply an outcome's edits in order (a later edit sees earlier additions), returning a new state."""
    s = state
    for edit in outcome.edits:
        s = apply_edit(s, edit)
    return s


def simulate(state: GovernedState, wager: Wager, baseline_cores: "set | None" = None) -> dict:
    """The kernel's read of a wager against the CURRENT graph — the computed half. Simulates every declared
    outcome via `recompile`, records which flip the decision, and prices the info-yield as RESIDUAL
    `identification_bits` over the minimal cores a cheap baseline leaves OPEN (`base_cores - baseline_cores`).
    This is the shared residual-pricing rule (`common.information_yield_pricing`): never re-buy information a
    cheap reasoner already yields — buy only the marginal bit (Fable, one door). The subtraction lives here; the
    baseline + prediction semantics live in the SUBSTRATE. The decision substrate has no cheap executable solver
    yet, so `baseline_cores` defaults to ∅ (residual = full yield); it subtracts for real once a substrate (ARC
    symmetries, LeanMill bounded deductions, the autoresearch cheap baseline) supplies one. Admissibility is the
    gate: exhaustive + all edits valid + at least one flip + still open. No probabilities, no payoffs."""
    base_cores = {frozenset(c) for c in minimal_cores(state)}
    priced_cores = base_cores - set(baseline_cores or ())  # residual: only the cores the cheap baseline leaves open
    rows: "list[dict]" = []
    per_outcome_cores: "dict[str, set]" = {}
    for o in wager.outcomes:
        try:
            gp = apply_outcome(state, o)
        except ValueError as exc:
            rows.append({"id": o.id, "label": o.label or o.id, "edits_valid": False, "error": str(exc), "flips": False,
                         "was": None, "verdict": None, "settled_cores": []})
            continue
        rc = recompile(state, gp)
        gp_cores = {frozenset(c) for c in minimal_cores(gp)}
        per_outcome_cores[o.id] = gp_cores
        rows.append({"id": o.id, "label": o.label or o.id, "edits_valid": True, "flips": bool(rc["decision_stale"]),
                     "was": rc["was"], "verdict": rc["now"],
                     "settled_cores": sorted(sorted(c) for c in (base_cores - gp_cores))})
    if priced_cores:
        cells: "dict[frozenset, list]" = {}
        for core in priced_cores:  # residual cores only; each core's signature = the outcomes that SETTLE it
            sig = frozenset(oid for oid, oc in per_outcome_cores.items() if core not in oc)
            cells.setdefault(sig, []).append(core)
        bits = identification_bits(cells, len(priced_cores))
    else:
        bits = 0.0
    any_flip = any(r["flips"] for r in rows)
    all_valid = bool(wager.outcomes) and all(r["edits_valid"] for r in rows)
    outcome_ids = [str(o.id).strip() for o in wager.outcomes]
    outcome_shape_valid = len(outcome_ids) >= 2 and all(outcome_ids) and len(set(outcome_ids)) == len(outcome_ids)
    admissible = bool(wager.exhaustive and outcome_shape_valid and all_valid and any_flip and wager.lifecycle == "open")
    if wager.lifecycle != "open":
        reason = f"not open (lifecycle={wager.lifecycle})"
    elif not wager.outcomes:
        reason = "no declared outcomes"
    elif not outcome_shape_valid:
        reason = "at least two uniquely named plausible outcomes are required"
    elif not all_valid:
        reason = "an outcome has an invalid edit (fail-closed)"
    elif not wager.exhaustive:
        reason = "outcomes not attested exhaustive (MECE)"
    elif not any_flip:
        reason = "no declared outcome changes the decision — not a wager, just a claim"
    else:
        reason = "admissible: a real test whose outcome would move the decision"
    return {"wager_id": wager.id, "claim_ref": wager.claim_ref, "base_verdict": verdict(state),
            "outcomes": rows, "identification_bits": round(bits, 4),
            "baseline_explained_cores": len(base_cores) - len(priced_cores), "any_flip": any_flip,
            "exhaustive": wager.exhaustive, "outcome_shape_valid": outcome_shape_valid,
            "all_edits_valid": all_valid, "declared_cost": wager.declared_cost,
            "lifecycle": wager.lifecycle, "admissible": admissible, "reason": reason}


# Wager ranking lives in ONE place — `scenarios.agenda.unified_agenda` (info-yield + severity + cost + Pareto
# frontier, one admission gate). The old `rank_wagers` / `rank_wagers_by_severity` doors were deleted (Fable
# eigenreview): they were unused and gated differently than the agenda, a latent ranker-drift trap.


# ── Graded twin: the wager under continuous strength (Fable's severe-test generalization) ────────────────────
def strength_displacement(governed: GovernedState, wager: Wager) -> dict:
    """How much each declared outcome would move the thesis's STRENGTH PROFILE, and the maximin value = the
    SMALLEST such move across outcomes. An experiment is SEVERE iff every outcome moves the decision (worst-case
    displacement > 0) — Mayo's severity criterion, made deterministic and prior-free (no outcome probabilities;
    worst-case, not expectation — the same maximin epistemology as the crisp info-yield). Coexists with
    `simulate`; profile displacements are compared lexicographically (hardest stratum first)."""
    from ztare.scenarios.strength import strength_profile

    base_sp = strength_profile(governed)
    base, base_status = base_sp["profile"], base_sp.get("status")
    zero = tuple(0.0 for _ in base)
    rows: "list[dict]" = []
    for o in wager.outcomes:
        try:
            gp = apply_outcome(governed, o)
        except ValueError as exc:
            rows.append({"id": o.id, "edits_valid": False, "error": str(exc), "displacement": list(zero)})
            continue
        spr = strength_profile(gp)
        prof = spr["profile"]
        disp = tuple(round(abs(prof[k] - base[k]), 4) for k in range(len(base)))
        rows.append({"id": o.id, "edits_valid": True, "profile": prof, "status": spr.get("status"),
                     "displacement": list(disp)})
    disps = [tuple(r["displacement"]) for r in rows if r["edits_valid"]]
    min_disp = min(disps) if disps else zero          # lexicographic min = the worst-case outcome (severity)
    max_disp = max(disps) if disps else zero
    # SEVERE (Mayo): the test could have come out the other way AND every way moves the decision. Requires the
    # honesty attestation `exhaustive=True` AND ≥2 outcomes — a single cherry-picked confirmation is NOT a severe
    # test, however far it moves the profile (Fable eigenreview) — AND every outcome actually moves (min > 0).
    severe = bool(wager.exhaustive and len(wager.outcomes) >= 2
                  and len(disps) == len(wager.outcomes) and min_disp > zero)
    # status_change: some outcome moves the graded verdict across the override lattice — the principled graded
    # analog of a crisp flip (not mere ε-motion), used by the agenda's admission gate.
    status_change = any(r.get("edits_valid") and r.get("status") and r["status"] != base_status for r in rows)
    return {"wager_id": wager.id, "baseline_profile": base, "base_status": base_status, "outcomes": rows,
            "min_displacement": list(min_disp), "max_displacement": list(max_disp),
            "severe": severe, "status_change": status_change}


# ── Lifecycle (verdict-preserving; the claim stays BLOCKED throughout) ──────────────────────────────────────
def expire_if_due(wager: Wager, now: str) -> Wager:
    """Anti-laundering tooth #2: a passed deadline auto-expires an open wager back to the ordinary BLOCKED
    backlog. `now`/`deadline` are ISO dates (lexicographic compare)."""
    if wager.lifecycle == "open" and wager.deadline and now > wager.deadline:
        return replace(wager, lifecycle="expired")
    return wager


def extend_deadline(wager: Wager, new_deadline: str, receipt: str) -> Wager:
    """Extending REQUIRES a fresh evidence/feasibility receipt (else wagers roll forward forever). Only an open
    wager can be extended, and only to a LATER deadline."""
    if wager.lifecycle != "open":
        raise ValueError(f"only an open wager can be extended (is {wager.lifecycle})")
    if not (receipt or "").strip():
        raise ValueError("deadline extension requires a new evidence/feasibility receipt")
    if not new_deadline or new_deadline <= wager.deadline:
        raise ValueError("new deadline must be later than the current one")
    return replace(wager, deadline=new_deadline, receipt=receipt)


def execute(wager: Wager, outcome_id: str) -> Wager:
    """Mark the test as run (the caller applies the chosen outcome's edits to the real graph separately)."""
    if wager.lifecycle != "open":
        raise ValueError(f"only an open wager can be executed (is {wager.lifecycle})")
    if outcome_id not in {o.id for o in wager.outcomes}:
        raise ValueError(f"unknown outcome {outcome_id!r}")
    return replace(wager, lifecycle="executed", resolved_outcome=outcome_id)


def invalidate(wager: Wager, reason: str = "") -> Wager:
    return replace(wager, lifecycle="invalidated")


def to_payload(wager: Wager) -> dict:
    """Serialize a Wager back to declared JSON (round-trips with `wager_from_payload`) — for persistence."""
    return {"id": wager.id, "claim_ref": wager.claim_ref, "test": wager.test,
            "declared_cost": None if wager.declared_cost < 0 else wager.declared_cost,
            "deadline": wager.deadline, "exhaustive": wager.exhaustive,
            "stakes": wager.stakes, "lifecycle": wager.lifecycle, "receipt": wager.receipt,
            "resolved_outcome": wager.resolved_outcome,
            "outcomes": [{"id": o.id, "label": o.label, "edits": [
                {"op": e.op, "target": e.target, "source": e.source, "relation": e.relation,
                 "warrant": e.warrant, "text": e.text} for e in o.edits]} for o in wager.outcomes]}


def wager_from_payload(payload: dict) -> Wager:
    """Build a Wager from declared JSON (the CLI/workbench door). Best-effort typing; simulate() fail-closes on
    anything malformed."""
    outcomes = tuple(
        Outcome(str(o.get("id", "")), tuple(
            GraphEdit(op=str(ed.get("op", "")), target=str(ed.get("target", "")), source=str(ed.get("source", "")),
                      relation=str(ed.get("relation", "")), warrant=str(ed.get("warrant", "W3") or "W3"),
                      text=str(ed.get("text", "")))
            for ed in (o.get("edits") or [])), label=str(o.get("label", "") or ""))
        for o in (payload.get("outcomes") or []))
    raw_cost = payload.get("declared_cost")
    if raw_cost is None or str(raw_cost).strip() == "":
        declared_cost = -1.0  # unknown is not free; it sorts behind a declared cost
    else:
        try:
            declared_cost = max(0.0, float(raw_cost))
        except (TypeError, ValueError):
            declared_cost = -1.0
    return Wager(id=str(payload.get("id", "")), claim_ref=str(payload.get("claim_ref", "")),
                 test=str(payload.get("test", "")), outcomes=outcomes,
                 declared_cost=declared_cost,
                 deadline=str(payload.get("deadline", "")),
                 exhaustive=bool(payload.get("exhaustive", False)), stakes=str(payload.get("stakes", "")),
                 lifecycle=str(payload.get("lifecycle", "open") or "open"), receipt=str(payload.get("receipt", "")),
                 resolved_outcome=str(payload.get("resolved_outcome", "")))


def _prepare_project_outcome(project: str, wager_id: str, outcome_id: str, repo_root):
    """Resolve and simulate one stored outcome without writing. Shared by preview, CLI, and Workbench execute."""
    from ztare.scenarios.adapters import governed_state_from_research_map
    from ztare.scenarios.decision_state import compile_decision_state, diff_decision_states

    governed = governed_state_from_research_map(project, repo_root)
    if not governed.elements:
        raise ValueError(f"no governed research map for {project!r}")
    payloads = load_wagers(project)
    wager_payload = next((payload for payload in payloads if payload.get("id") == wager_id), None)
    if wager_payload is None:
        raise ValueError(f"unknown wager {wager_id!r}")
    wager = wager_from_payload(wager_payload)
    if wager.lifecycle != "open":
        raise ValueError(f"only an open wager can be executed (is {wager.lifecycle})")
    outcome = next((candidate for candidate in wager.outcomes if candidate.id == outcome_id), None)
    if outcome is None:
        raise ValueError(f"wager {wager_id!r} has no outcome {outcome_id!r}")

    next_state = apply_outcome(governed, outcome)
    prior_element_ids = {element.id for element in governed.elements}
    prior_edges = {(edge.src, edge.kind, edge.dst) for edge in governed.edges}
    new_elements = [
        {"id": element.id, "kind": element.kind, "text": element.text}
        for element in next_state.elements if element.id not in prior_element_ids
    ]
    new_edges = [
        {"src": edge.src, "kind": edge.kind, "dst": edge.dst, "warrant": getattr(edge, "warrant", "W3")}
        for edge in next_state.edges if (edge.src, edge.kind, edge.dst) not in prior_edges
    ]
    decision_before = compile_decision_state(governed).to_payload()
    decision_after = compile_decision_state(next_state).to_payload()
    decision_delta = diff_decision_states(decision_before, decision_after)
    return governed, payloads, wager, outcome, new_elements, new_edges, decision_before, decision_after, decision_delta


def preview_project_outcome(project: str, wager_id: str, outcome_id: str, repo_root) -> dict:
    """Typed, read-only execution preview for confirmation surfaces."""
    (_governed, _payloads, wager, outcome, new_elements, new_edges,
     decision_before, decision_after, decision_delta) = _prepare_project_outcome(
        project, wager_id, outcome_id, repo_root
    )
    return {
        "ok": True,
        "status": "needs_confirmation",
        "project": project,
        "wager": {"id": wager.id, "test": wager.test, "claim_ref": wager.claim_ref},
        "outcome": {"id": outcome.id, "label": outcome.label or outcome.id},
        "applied": {"evidence": len(new_elements), "edges": len(new_edges)},
        "decision_before": decision_before,
        "decision_after": decision_after,
        "decision_delta": decision_delta,
    }


def execute_project_outcome(project: str, wager_id: str, outcome_id: str, repo_root) -> dict:
    """Apply one stored outcome through the governed overlay and persist its typed execution receipt."""
    from ztare.scenarios.adapters import append_governed_overlay

    (_governed, payloads, wager, outcome, new_elements, new_edges,
     decision_before, decision_after, decision_delta) = _prepare_project_outcome(
        project, wager_id, outcome_id, repo_root
    )
    append_governed_overlay(project, repo_root, new_elements, new_edges)
    executed = execute(wager, outcome.id)
    save_wagers(project, [to_payload(executed) if payload.get("id") == wager.id else payload for payload in payloads])
    return {
        "ok": True,
        "status": "executed",
        "project": project,
        "wager": {"id": wager.id, "test": wager.test, "claim_ref": wager.claim_ref,
                  "lifecycle": executed.lifecycle, "resolved_outcome": executed.resolved_outcome},
        "outcome": {"id": outcome.id, "label": outcome.label or outcome.id},
        "applied": {"evidence": len(new_elements), "edges": len(new_edges)},
        "decision_before": decision_before,
        "decision_after": decision_after,
        "decision_delta": decision_delta,
    }


# ── Persistence: one door for wagers, shared by the CLI and the workbench server ────────────────────────────
def wagers_path(project: str):
    from ztare.common.paths import PROJECTS_DIR
    return PROJECTS_DIR / project / "workspace" / "wagers.json"


def load_wagers(project: str) -> "list[dict]":
    """The project's wager payloads (declared JSON). A missing/corrupt store reads as empty, never crashes."""
    import json
    p = wagers_path(project)
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:  # noqa: BLE001
        return []


def save_wagers(project: str, payloads: "list[dict]") -> None:
    import json
    p = wagers_path(project)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payloads, indent=2), encoding="utf-8")


def _selftest() -> int:
    base = GovernedState([GovernedElement("t1", "thesis", "claim T")], [])
    assert verdict(base) == "BLOCKED", "a thesis with no evidence is BLOCKED"

    confirmed = Outcome("confirmed", (GraphEdit("add_evidence", "e_c", text="the metered/billed audit"),
                                      GraphEdit("support", "t1", source="e_c", warrant="W1")))
    refuted = Outcome("refuted", (GraphEdit("add_evidence", "e_r", text="counter-evidence"),
                                  GraphEdit("attack", "t1", source="e_r", relation="CONTRADICTS", warrant="W1")))
    w = Wager("w1", "t1", "run the audit", (confirmed, refuted), declared_cost=5.0,
              deadline="2026-09-01", exhaustive=True, stakes="unlocks tier redesign")

    r = simulate(base, w)
    assert r["admissible"], r["reason"]
    assert r["outcomes"][0]["verdict"] == "SUPPORTED" and r["outcomes"][0]["flips"]
    assert r["outcomes"][1]["verdict"] == "REFUTED" and r["outcomes"][1]["flips"]
    assert r["any_flip"] and r["base_verdict"] == "BLOCKED"
    assert verdict(base) == "BLOCKED", "simulate must not mutate the base state / claim verdict"

    # no outcome flips → not a wager
    meh = Wager("w2", "t1", "look around", (Outcome("meh", (GraphEdit("add_evidence", "e_m", text="unrelated"),)),),
                exhaustive=True, deadline="2026-09-01")
    assert not simulate(base, meh)["admissible"] and "outcomes" in simulate(base, meh)["reason"]

    # flips but NOT attested exhaustive → not admissible
    assert not simulate(base, replace(w, exhaustive=False))["admissible"]

    # an invalid edit (warrant promotion is not a wager edit) fails closed → not admissible
    bad = Wager("w3", "t1", "x", (Outcome("o", (GraphEdit("set_warrant", "t1", source="nope",
                                                          relation="SUPPORTS", warrant="W0"),)),), exhaustive=True)
    br = simulate(base, bad)
    assert not br["admissible"] and not br["outcomes"][0]["edits_valid"]

    # no edit op can set a verdict/status
    for illegal in ("set_warrant", "set_verdict", "set_status", "accept", "refute"):
        assert illegal not in EDIT_OPS
        try:
            apply_edit(base, GraphEdit(illegal, "t1"))
            raise AssertionError(f"{illegal} should be rejected")
        except ValueError:
            pass

    # lifecycle + anti-laundering teeth
    assert expire_if_due(w, "2026-12-01").lifecycle == "expired"
    assert expire_if_due(w, "2026-01-01").lifecycle == "open"
    try:
        extend_deadline(w, "2026-12-01", "")            # extension without a receipt is refused
        raise AssertionError("extend without receipt must raise")
    except ValueError:
        pass
    assert extend_deadline(w, "2026-12-01", "vendor feasibility quote").deadline == "2026-12-01"
    try:
        extend_deadline(w, "2026-01-01", "receipt")     # earlier deadline refused
        raise AssertionError("earlier deadline must raise")
    except ValueError:
        pass
    assert execute(w, "confirmed").lifecycle == "executed"
    try:
        execute(w, "ghost")
        raise AssertionError("unknown outcome must raise")
    except ValueError:
        pass
    assert invalidate(w).lifecycle == "invalidated"
    assert not simulate(base, expire_if_due(w, "2027-01-01"))["admissible"], "an expired wager is not admissible"

    # round-trips through the declared-JSON door, and to_payload is the exact inverse
    payload = {"id": "wp", "claim_ref": "t1", "test": "audit", "exhaustive": True, "declared_cost": 3.0,
               "outcomes": [{"id": "confirmed", "edits": [
                   {"op": "add_evidence", "target": "e_p", "text": "audit result"},
                   {"op": "support", "source": "e_p", "target": "t1", "warrant": "W1"}]},
                           {"id": "refuted", "label": "The audit finds a material gap", "edits": [
                   {"op": "add_evidence", "target": "e_n", "text": "audit counter-result"},
                   {"op": "attack", "source": "e_n", "target": "t1", "relation": "CONTRADICTS", "warrant": "W1"}]}]}
    wp = wager_from_payload(payload)
    assert simulate(base, wp)["admissible"]
    assert wp.outcomes[1].label == "The audit finds a material gap"
    assert wager_from_payload(to_payload(wp)) == wp, "to_payload must round-trip"
    unknown_cost = wager_from_payload({"id": "wu", "claim_ref": "t1", "test": "audit", "exhaustive": True,
                                       "outcomes": payload["outcomes"]})
    assert unknown_cost.declared_cost < 0 and to_payload(unknown_cost)["declared_cost"] is None, \
        "an omitted cost must remain unknown, never silently become free"

    # graded twin — severity: BOTH outcomes must move the strength profile (Mayo severity, prior-free)
    sbase = GovernedState([GovernedElement("t1", "thesis", "claim T"), GovernedElement("e0", "evidence", "seed")],
                          [GovernedEdge("e0", "SUPPORTS", "t1", "W2")])
    severe_w = Wager("sv", "t1", "test", (
        Outcome("up", (GraphEdit("add_evidence", "e_up", text="more support"),
                       GraphEdit("support", "t1", source="e_up", warrant="W2"))),
        Outcome("down", (GraphEdit("add_evidence", "e_dn", text="counter"),
                         GraphEdit("attack", "t1", source="e_dn", relation="CONTRADICTS", warrant="W2")))),
        exhaustive=True)
    assert strength_displacement(sbase, severe_w)["severe"], "both outcomes move the strength → severe"
    mild_w = Wager("mv", "t1", "test", (
        Outcome("up", (GraphEdit("add_evidence", "e_up2", text="more"),
                       GraphEdit("support", "t1", source="e_up2", warrant="W2"))),
        Outcome("noop", (GraphEdit("add_evidence", "e_x", text="unrelated to the thesis"),))), exhaustive=True)
    assert not strength_displacement(sbase, mild_w)["severe"], "a non-moving outcome → not severe"
    # a single cherry-picked confirmation (exhaustive=False, 1 outcome) is NOT severe even though it moves (Fable F2)
    cherry = Wager("ch", "t1", "one-sided", (
        Outcome("up", (GraphEdit("add_evidence", "e_ch", text="backing"),
                       GraphEdit("support", "t1", source="e_ch", warrant="W2"))),), exhaustive=False)
    assert not strength_displacement(sbase, cherry)["severe"], "1-outcome non-exhaustive bet must not be severe"

    # residual pricing (Fable one-door): a baseline explaining every core leaves 0 marginal bits; ∅ baseline = full
    _cores = {frozenset(c) for c in minimal_cores(sbase)}
    assert simulate(sbase, severe_w, baseline_cores=_cores)["identification_bits"] == 0.0, "full baseline → 0 residual"
    assert (simulate(sbase, severe_w)["identification_bits"]
            == simulate(sbase, severe_w, baseline_cores=set())["identification_bits"]), "empty baseline = full yield"

    print("WAGER SELFTEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
