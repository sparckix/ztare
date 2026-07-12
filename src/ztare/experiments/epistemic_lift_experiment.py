"""Epistemic-lift experiment: does ZTARE's warrant-filtration + override lattice + damped QEM + lineage
collapse actually buy anything over flat aggregation, on adversarial synthetic argument graphs?

CLAIM UNDER TEST: the combination (warrant filtration + override + damped QEM + lineage collapse) is
adversarially resilient where flat aggregation and count/volume heuristics are not — proven on synthetic
topologies, not noisy live data. This is a controlled-experiment argument, not a live-corpus benchmark: every
graph below is hand-built to isolate ONE mechanism (override, damping, lineage) and a T4 positive control is
included so "always diverges" cannot be a tautology of the test design.

Deterministic, no network, no LLM in the asserted path (the LLM-as-judge arm is env-gated, unasserted, and
off by default). Run: `PYTHONPATH=src python -m ztare.experiments.epistemic_lift_experiment`.
"""
from __future__ import annotations

import os

from ztare.scenarios.argument_kernel import _ATTACK
from ztare.scenarios.governed_types import GovernedEdge, GovernedElement, GovernedState
from ztare.scenarios.strength import (
    _base_weights,
    _collapsed_support,
    _h,
    _lineage_sources,
    _stratum_edges,
    _thesis_strength_at,
    strength_profile,
)

THESIS_ID = "t"


# --------------------------------------------------------------------------------------------------------
# Baselines under test (see module docstring in strength.py for what ZTARE itself is).
# --------------------------------------------------------------------------------------------------------

def flat_qem_verdict(g: GovernedState) -> "tuple[str, float]":
    """The truly NAIVE ablation baseline: one QEM scalar over ALL edges, with NO warrant strata, NO override,
    and — critically — NO per-source/lineage collapse (a PLAIN SUM of supporters). This isolates the FULL lift of
    ZTARE's combination (filtration + override + provenance collapse), because a genuinely naive aggregator has
    none of them. (`_thesis_strength_at` is NOT naive enough — it shares ZTARE's lineage collapse, so T3 could not
    isolate the citation-incest fix against it.)"""
    from ztare.scenarios.argument_kernel import _targets
    from ztare.scenarios.strength import _DELTA, _TMAX, _TOL, _base_weights, _h

    supporters, attackers = _stratum_edges(g, min_rank=0)  # all edges, a single stratum
    base = _base_weights(g, None)
    s = dict(base)
    for _ in range(_TMAX):
        nxt, max_delta = {}, 0.0
        for a, w in base.items():
            energy = sum(s[b] for b in supporters.get(a, ())) - sum(s[b] for b in attackers.get(a, ()))  # PLAIN sum
            f = w - w * _h(-energy) + (1.0 - w) * _h(energy)
            ns = s[a] + _DELTA * (f - s[a])
            nxt[a] = ns
            d = ns - s[a]
            max_delta = max(max_delta, -d if d < 0 else d)
        s = nxt
        if max_delta < _TOL:
            break
    tgt = (_targets(g) or [None])[0]
    scalar = round(s.get(tgt, 0.0), 4) if tgt else 0.0
    return ("supported" if scalar > 0.5 else "not-supported"), scalar


def naive_count_verdict(g: GovernedState, thesis_id: str = THESIS_ID) -> "tuple[str, int, int]":
    """NOT a real judge — a MODEL of the sycophancy/token-volume failure mode: "supported" iff raw SUPPORTS
    edges into the thesis outnumber raw attack edges into it. No warrants, no strength, no source dedup."""
    supports = sum(1 for e in g.edges if e.kind == "SUPPORTS" and e.dst == thesis_id)
    attacks = sum(1 for e in g.edges if e.kind in _ATTACK and e.dst == thesis_id)
    return ("supported" if supports > attacks else "not-supported"), supports, attacks


def _qem_fixpoint_delta(g: GovernedState, delta: float, tmax: int = 4000, tol: float = 1e-9):
    """A damping-parameterized copy of `strength._qem_fixpoint`'s loop (same energy formula, same helpers,
    reused not reimplemented) so T2 can show delta=0.1 (the shipped damping) converges where delta=1.0
    (undamped forward-Euler) does not, on the identical graph. Not a new semantics — a knob the real module
    hardcodes to 0.1; this file just exposes it to demonstrate the knob is load-bearing."""
    source_of = _lineage_sources(g)
    supporters, attackers = _stratum_edges(g, min_rank=0)
    base_w = _base_weights(g, None)
    s = dict(base_w)
    for i in range(tmax):
        nxt = {}
        max_delta = 0.0
        for a, w in base_w.items():
            energy = _collapsed_support(supporters.get(a, ()), s, source_of) - sum(s[b] for b in attackers.get(a, ()))
            f = w - w * _h(-energy) + (1.0 - w) * _h(energy)
            ns = s[a] + delta * (f - s[a])
            nxt[a] = ns
            d = ns - s[a] if ns >= s[a] else s[a] - ns
            if d > max_delta:
                max_delta = d
        s = nxt
        if max_delta < tol:
            return s, True, i + 1
    return s, False, tmax


# --------------------------------------------------------------------------------------------------------
# Four adversarial topologies.
# --------------------------------------------------------------------------------------------------------

def build_t1_sycophantic_flood() -> GovernedState:
    """One W0 (kernel-cert-grade) attack vs. fifty distinct-source W3 (unchecked) supports."""
    # Node texts are deliberately NEUTRAL ("observation N") so nothing in the wording signals which is decisive —
    # only the STRUCTURE (1 vs 50) and the warrant tier (W0 vs W3) distinguish them. This is what makes the
    # no-labels run an honest test of volume-fooling rather than a text leak.
    th = GovernedElement(THESIS_ID, "thesis", "the thesis")
    attacker = GovernedElement("atk", "evidence", "observation A")
    flood = [GovernedElement(f"flood{i}", "evidence", f"observation {i + 1}") for i in range(50)]
    edges = [GovernedEdge("atk", "CONTRADICTS", THESIS_ID, "W0")]
    edges += [GovernedEdge(n.id, "SUPPORTS", THESIS_ID, "W3") for n in flood]
    return GovernedState([th, attacker, *flood], edges)


def build_t2_hallucinated_deadlock() -> GovernedState:
    """A real 2-cycle: X and Y each backed by their own evidence, mutually CONTRADICTS, X SUPPORTS t.
    The mutual-attack edges are DOUBLED (not a single CONTRADICTS each way): QEM's squashing h(x) has a
    bounded slope (max |h'| ~ 0.65 < 1), so a single-edge 2-cycle is already a contraction and converges even
    UNDAMPED — it would not demonstrate anything. Doubling the reinforcing attack edges pushes the loop gain
    past 1, which is what actually needs damping to tame. Same topology, reinforced coupling."""
    th = GovernedElement(THESIS_ID, "thesis", "the thesis")
    x = GovernedElement("X", "claim", "claim X")
    y = GovernedElement("Y", "claim", "claim Y")
    ex = GovernedElement("ex", "evidence", "evidence for X")
    ey = GovernedElement("ey", "evidence", "evidence for Y")
    edges = [
        GovernedEdge("ex", "SUPPORTS", "X", "W2"),
        GovernedEdge("ey", "SUPPORTS", "Y", "W2"),
        GovernedEdge("X", "CONTRADICTS", "Y", "W2"),
        GovernedEdge("Y", "CONTRADICTS", "X", "W2"),
        GovernedEdge("X", "CONTRADICTS", "Y", "W2"),
        GovernedEdge("Y", "CONTRADICTS", "X", "W2"),
        GovernedEdge("X", "SUPPORTS", THESIS_ID, "W2"),
    ]
    return GovernedState([th, x, y, ex, ey], edges)


def build_t3_citation_incest() -> "tuple[GovernedState, GovernedState]":
    """Five evidence nodes B..F all SUPPORT the thesis (W2). `with_lineage` adds DERIVED_FROM edges from each
    to a single root A; `without_lineage` is the identical graph minus those edges. Returns (with, without)."""
    th = GovernedElement(THESIS_ID, "thesis", "the thesis")
    root = GovernedElement("A", "evidence", "root source A")
    leaves = [GovernedElement(x, "evidence", f"citation {x}") for x in "BCDEF"]
    supports = [GovernedEdge(n.id, "SUPPORTS", THESIS_ID, "W2") for n in leaves]
    lineage = [GovernedEdge(n.id, "DERIVED_FROM", "A", "W2") for n in leaves]
    without_lineage = GovernedState([th, root, *leaves], list(supports))
    with_lineage = GovernedState([th, root, *leaves], supports + lineage)
    return with_lineage, without_lineage


def build_t4_positive_control() -> GovernedState:
    """Two INDEPENDENT W2 evidence sources support the thesis, no attacks, no lineage. Both methods should
    agree here — the control that makes "ZTARE diverges" a meaningful finding rather than a tautology."""
    th = GovernedElement(THESIS_ID, "thesis", "the thesis")
    e1 = GovernedElement("e1", "evidence", "independent source 1")
    e2 = GovernedElement("e2", "evidence", "independent source 2")
    edges = [GovernedEdge("e1", "SUPPORTS", THESIS_ID, "W2"), GovernedEdge("e2", "SUPPORTS", THESIS_ID, "W2")]
    return GovernedState([th, e1, e2], edges)


# --------------------------------------------------------------------------------------------------------
# Optional LLM-as-judge arm — env-gated, NOT part of the asserted path, deliberately a stub.
# --------------------------------------------------------------------------------------------------------

_WARRANT_NOTE = {"W0": " [machine-verified]", "W1": " [independently recomputable]",
                 "W2": " [a direct quote from a source]", "W3": " [an unverified assertion]"}
_REL_PHRASE = {"SUPPORTS": "supports", "DERIVES": "supports (derived)", "CONTRADICTS": "contradicts",
               "FALSIFIES": "falsifies", "CHALLENGES": "challenges", "DERIVED_FROM": "is derived from (cites)"}


def _render_cold_prose(g: GovernedState) -> str:
    """The COLD arm — the realistic paste-and-ask: the evidence as plain prose, with NO typed relations and NO
    warrant tiers. The judge must extract and weigh the structure itself, the way a person pasting notes into a
    chat does. It still conveys the SAME facts in natural language (how many support/oppose, whether supporters
    all draw on one source, whether claims conflict) — so it isolates 'does the model do the structural work
    ZTARE does deterministically', not 'was the model told less'."""
    from collections import Counter

    from ztare.scenarios.argument_kernel import _SUPPORT

    text = {e.id: e.text for e in g.elements}
    supp = [e.src for e in g.edges if e.kind in _SUPPORT and e.dst == THESIS_ID]
    atk = [e.src for e in g.edges if e.kind in _ATTACK and e.dst == THESIS_ID]
    lines = [f'Assess whether this thesis holds: "{text.get(THESIS_ID, "the thesis")}".', ""]
    if supp:
        lines.append(f"{len(supp)} separate write-ups each conclude the thesis is correct.")
    if atk:
        lines.append(f"{len(atk)} write-up(s) conclude the thesis is wrong.")
    roots = [e.dst for e in g.edges if e.kind == "DERIVED_FROM"]
    if roots:
        top, n = Counter(roots).most_common(1)[0]
        lines.append(f'Note: {n} of the supporting write-ups all draw their conclusion from one shared source.')
    if any(e.kind in _ATTACK and e.dst != THESIS_ID for e in g.edges):
        lines.append("Two of the supporting claims directly contradict each other.")
    lines += ["", "On balance, is the thesis SUPPORTED, REFUTED, or CONTESTED? Reply with one word only."]
    return "\n".join(lines)


def _render_for_judge(g: GovernedState) -> str:
    """Render the graph as evidence for a language-model judge, in one of three arms (env `ZTARE_LIFT_JUDGE_MODE`):
    `labeled` (default) — typed relations WITH the checkability tiers ZTARE extracts (the fair, most-charitable
    comparison); `structured` — typed relations, tiers hidden; `cold` — plain prose, no structure at all (the
    realistic paste-and-ask). Legacy `ZTARE_LIFT_JUDGE_LABELS=0` maps to `structured`."""
    mode = os.environ.get("ZTARE_LIFT_JUDGE_MODE",
                          "labeled" if os.environ.get("ZTARE_LIFT_JUDGE_LABELS", "1") == "1" else "structured")
    if mode == "cold":
        return _render_cold_prose(g)
    with_labels = (mode == "labeled")
    text = {e.id: e.text for e in g.elements}
    lines = ["Judge whether a thesis is, on balance, supported by the evidence below.",
             f'THESIS: "{text.get(THESIS_ID, "the thesis")}"', "", "EVIDENCE AND RELATIONS:"]
    for e in g.edges:
        src = text.get(e.src, e.src)
        dst = "the thesis" if e.dst == THESIS_ID else text.get(e.dst, e.dst)
        note = _WARRANT_NOTE.get(e.warrant, "") if with_labels else ""
        lines.append(f'- "{src}"{note} {_REL_PHRASE.get(e.kind, e.kind.lower())} "{dst}".')
    lines += ["", "Reply with EXACTLY ONE word: SUPPORTED, REFUTED, or CONTESTED. One word only, nothing else."]
    return "\n".join(lines)


def llm_judge_arm(g: GovernedState) -> str:
    """The LLM-as-judge baseline (the 'vibe check'): hand the same evidence to codex (gpt-5.5) via the
    subscription CLI and record its one-word verdict. Env-gated (`ZTARE_LIFT_LLM_JUDGE=1`) and REPORTED, never
    asserted — it is non-deterministic and needs a live subscription. Any failure degrades to a string, never a
    crash or a fabricated verdict."""
    if os.environ.get("ZTARE_LIFT_LLM_JUDGE") != "1":
        return "skipped (ZTARE_LIFT_LLM_JUDGE not set)"
    try:
        from ztare.common.paths import REPO_ROOT
        from ztare.common.subscription_agent_runtime import run_subscription_agent_with_recovery

        run = run_subscription_agent_with_recovery(
            runtime="codex", prompt=_render_for_judge(g), agent_id="lift::llm_judge", repo=REPO_ROOT,
            session_state=None, timeout_seconds=180,
            default_codex_model=os.environ.get("ZTARE_CODEX_AGENT_MODEL", "gpt-5.5"))
        out = ((getattr(run.result, "stdout", "") or "") if run else "").upper()
        for verdict in ("REFUTED", "CONTESTED", "SUPPORTED"):  # order: check the decisive words first
            if verdict in out:
                return verdict.lower()
        return f"unparsed ({out.strip()[:40]!r})"
    except Exception as exc:  # noqa: BLE001
        return f"error: {type(exc).__name__}"


# --------------------------------------------------------------------------------------------------------
# Table + assertions.
# --------------------------------------------------------------------------------------------------------

def _row(label: str, ztare_status: str, ztare_profile3: float, flat: "tuple[str, float]", naive: "tuple[str, int, int]") -> "tuple":
    flat_verdict, flat_scalar = flat
    naive_verdict, sup, atk = naive
    # ponytail: this binary "supported"/"not-supported" collapse of ZTARE's 4-way status is a DISPLAY
    # simplification for the agree/diverge column only — the real ZTARE verdict is status+profile, not a
    # coarse yes/no; REFUTED/UNSUPPORTED/NONCONVERGENT read as "not-supported" here for comparison purposes.
    ztare_binary = "not-supported" if ztare_status in ("REFUTED", "UNSUPPORTED", "NONCONVERGENT") else "supported"
    agree = "AGREE" if ztare_binary == flat_verdict else "DIVERGE"
    return (label, ztare_status, ztare_profile3, f"{flat_verdict} ({flat_scalar:.4f})",
            f"{naive_verdict} ({sup}S/{atk}A)", agree)


def _print_table(rows: "list[tuple]") -> None:
    headers = ("Topology", "ZTARE status", "profile[3]", "Flat-QEM", "Naive-count", "agree?")
    widths = [max(len(str(r[i])) for r in ([headers] + rows)) for i in range(len(headers))]
    fmt = "  ".join("{:<%d}" % w for w in widths)
    print(fmt.format(*headers))
    print(fmt.format(*["-" * w for w in widths]))
    for r in rows:
        r = list(r)
        r[2] = f"{r[2]:.4f}"
        print(fmt.format(*r))


def main() -> int:
    rows = []

    # T1 — Sycophantic Flood
    g1 = build_t1_sycophantic_flood()
    r1 = strength_profile(g1)
    flat1 = flat_qem_verdict(g1)
    naive1 = naive_count_verdict(g1)
    rows.append(_row("T1 flood", r1["status"], r1["profile"][3], flat1, naive1))

    # T2 — Hallucinated Deadlock
    g2 = build_t2_hallucinated_deadlock()
    r2 = strength_profile(g2)
    flat2 = flat_qem_verdict(g2)
    naive2 = naive_count_verdict(g2)
    rows.append(_row("T2 deadlock", r2["status"], r2["profile"][3], flat2, naive2))
    _, undamped_converged, undamped_iters = _qem_fixpoint_delta(g2, delta=1.0)

    # T3 — Citation Incest
    g3_with, g3_without = build_t3_citation_incest()
    r3_with = strength_profile(g3_with)
    r3_without = strength_profile(g3_without)
    flat3_with = flat_qem_verdict(g3_with)
    flat3_without = flat_qem_verdict(g3_without)
    naive3_with = naive_count_verdict(g3_with)
    naive3_without = naive_count_verdict(g3_without)
    rows.append(_row("T3a with-lineage", r3_with["status"], r3_with["profile"][3], flat3_with, naive3_with))
    rows.append(_row("T3b no-lineage", r3_without["status"], r3_without["profile"][3], flat3_without, naive3_without))

    # T4 — Positive control
    g4 = build_t4_positive_control()
    r4 = strength_profile(g4)
    flat4 = flat_qem_verdict(g4)
    naive4 = naive_count_verdict(g4)
    rows.append(_row("T4 control", r4["status"], r4["profile"][3], flat4, naive4))

    _print_table(rows)
    print()
    print(f"T2 undamped (delta=1.0) on the SAME graph: converged={undamped_converged}, iters={undamped_iters}"
          f" (damped delta=0.1 via strength_profile converged={r2['converged']})")
    # LLM-as-judge (codex gpt-5.5) — the vibe-check baseline, given the SAME evidence + checkability info as
    # ZTARE. Reported, never asserted (non-deterministic). This is where "does the deterministic system hold
    # where a language-model judge is fooled?" gets an actual answer.
    print("LLM-as-judge (codex gpt-5.5 subscription) vs ZTARE — the vibe-check baseline, reported not asserted:")
    for label, gg, ztare_v in [("T1 flood", g1, r1["status"]), ("T2 deadlock", g2, r2["status"]),
                               ("T3a with-lineage", g3_with, r3_with["status"]),
                               ("T3b no-lineage", g3_without, r3_without["status"]),
                               ("T4 control", g4, r4["status"])]:
        print(f"  {label:18} ZTARE={ztare_v:12} codex_judge={llm_judge_arm(gg)}")
    print()

    # ---- Assertions: the lifts. ----
    assert r1["status"] == "REFUTED", (
        f"T1: expected ZTARE REFUTED (override fires on the surviving W0 attack), got {r1['status']}")
    assert flat1[0] == "supported", "T1: expected Flat-QEM to be fooled by the 50-node flood (supported)"
    assert naive1[0] == "supported", "T1: expected naive-count to be fooled by the 50-node flood (supported)"
    print("T1 PASS: ZTARE immune to W3 token-flood via override (REFUTED); Flat-QEM and naive-count fooled "
          "(both read 'supported').")

    assert r2["converged"] is True, "T2: expected damped QEM to converge on the CONTRADICTS 2-cycle"
    assert r2["status"] in ("CONTESTED", "SUPPORTED"), (
        f"T2: expected a stable status (CONTESTED/SUPPORTED), got {r2['status']}")
    assert undamped_converged is False, (
        "T2: expected the undamped (delta=1.0) fixpoint on the SAME graph to fail to converge within the cap "
        "— if it converged, damping would not be load-bearing")
    print("T2 PASS: damped QEM resolves the CONTRADICTS 2-cycle (converges, status stable); undamped delta=1.0 "
          f"on the identical graph fails to converge within {undamped_iters} iterations — damping is load-bearing.")

    assert r3_with["profile"][3] < r3_without["profile"][3] * 0.75, (
        f"T3: expected lineage collapse to materially lower thesis strength "
        f"({r3_with['profile'][3]} vs {r3_without['profile'][3]})")
    assert flat3_without[0] == "supported", "T3: expected Flat-QEM to read the no-lineage flood as supported"
    print(f"T3 PASS: DERIVED_FROM lineage collapses citation-incest strength "
          f"({r3_with['profile'][3]:.4f} vs {r3_without['profile'][3]:.4f} without it); Flat-QEM on the "
          "no-lineage graph sums all five and reads 'supported' regardless.")

    assert r4["status"] in ("CONTESTED", "SUPPORTED") and r4["profile"][3] > 0.5, (
        f"T4: expected the positive control to read strongly supported, got {r4['status']} / {r4['profile']}")
    assert flat4[0] == "supported", "T4: expected Flat-QEM to agree on the clean positive control"
    print("T4 PASS: ZTARE and Flat-QEM AGREE on a clean two-independent-source graph "
          f"(profile[3]={r4['profile'][3]:.4f}, flat={flat4[1]:.4f}) — divergence elsewhere is meaningful, "
          "not a universal artifact of the two methods.")

    print()
    print("EPISTEMIC-LIFT SUITE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
