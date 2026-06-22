"""Standing CI guards for the recurring LeanMill sibling / agency-creep bug class (2026-06-22).

These exist because the class kept recurring *despite* the principle being documented — the cure for the CLASS
(not an instance) is a test that asserts the BEHAVIOR, so a comment claiming an invariant the code doesn't
enforce fails CI. Two guards:

  1. INVARIANT B (agentic-first): decompose-vs-direct is the AGENT's call at EVERY node — `is_top`/`notes` must
     NOT force a decomposition. This is the exact bug commit 9612a8c16 shipped behind an overclaiming comment
     (`(_is_top and bool(notes))` short-circuited the agent strategy-ask, gapping a directly-provable nucleus).
  2. SPLIT-BRAIN flag defaults: the same boolean `ZTARE_*` gate read with conflicting `.get` defaults in
     different files (the proposer_pool `pool_enabled` bug). `flag_audit` is the mechanical detector.
"""
from __future__ import annotations


def test_invariant_b_agentic_decompose_vs_direct():
    """The agent decides decompose-vs-direct at every node; is_top/notes never force it. FAILS 9612a8c16."""
    from ztare.leanmill.solver.solver_core import (
        _should_decompose_first, _selftest_invariant_b_agentic_decompose)
    _selftest_invariant_b_agentic_decompose()  # the full battery (config gates, native-first, lazy agent)
    base = dict(cited_from_cache=False, iso_route_on=True, decompose_first_on=True, below_cap=True,
                strategy_assess_on=True)
    # the nucleus case: agent says SOLVE_DIRECT, native misses → must NOT decompose (used to force-decompose+gap)
    assert _should_decompose_first(**base, native_closes=lambda: False, agent_recommends=lambda: False) is False
    # hard target: agent says DECOMPOSE → decompose
    assert _should_decompose_first(**base, native_closes=lambda: False, agent_recommends=lambda: True) is True


def test_no_split_brain_flag_defaults():
    """No boolean ZTARE_* gate is read with conflicting .get defaults across files (the proposer_pool bug)."""
    from ztare.leanmill.flag_audit import split_brain_flags
    bad = split_brain_flags()
    assert not bad, ("split-brain boolean flag default(s) — route every reader through ONE canonical accessor:\n"
                     + "\n".join(f"  {f}: {dict(d)}" for f, d in sorted(bad.items())))


def test_governance_probe_comparand_no_sibling():
    """statement_integrity's comparand is THIS closure's probe, never a sibling attempt's body.

    The detbank_verify residual (2026-06-22): with several attempts writing probes for the same target into
    one scratch, the old finder recency-fell-back to a SIBLING when the stored proof_text didn't substring-
    match (a pool/cold splice reflows the proof). Comparing the original source against a sibling's signature
    both false-rejects a clean closure and risks false-admit. The fix matches whitespace-normalized AND
    refuses the sibling-fallback when proof_text is present-but-unmatched (withhold → integrity_unverified).
    """
    from ztare.leanmill.solver.solver_core import _match_closing_probe, _selftest_match_closing_probe
    _selftest_match_closing_probe()  # reflow-match + sibling-refusal + legacy-fallback battery
    sig = "theorem T (n : Nat) : n = n"
    own = f"import Mathlib\n{sig} := by\n    rfl\n#print axioms T\n"       # reflowed (4-space) `rfl`
    sib = "import Mathlib\ntheorem T (n : Nat) (h : False) : n = n := by\n  simp\n"  # weakened sibling
    # reflowed proof_text pins its OWN probe, never the altered sibling
    _, _, mk = _match_closing_probe([("/sib", sib), ("/own", own)], "T", "by rfl")
    assert mk == "matched"
    # present-but-unmatched ⇒ refuse the sibling comparand (withheld, not a wrong-comparand verdict)
    _, _, mk2 = _match_closing_probe([("/sib", sib)], "T", "by exact rfl")
    assert mk2 == "withheld_unmatched"


def test_dead_api_leaf_probed_once():
    """A 429-dead API leaf (kimi) is probed at most ONCE per process, then dispatch routes straight to CLI.

    The consc_camp_0622hard waste (2026-06-22): kimi passed the start-of-run liveness probe, then 429'd on
    every real dispatch — and nothing remembered, so each dispatch paid a probe-then-failover tax (9× in one
    run), burning the wall-clock the live CLI leaf needed to close the crux. Process-scoped, per-runtime,
    fail-safe (the cache only ever routes to the reliable CLI; the kernel re-verifies every closure)."""
    from ztare.leanmill.solver.agentic_leaf import _selftest_dead_api_cache
    _selftest_dead_api_cache()


def test_dag_audit_kernel_circularity_catches_renamed_restatement():
    """The decomposition audit rejects a sub-lemma that is the goal G with variables RENAMED (same Prop).

    The consc_camp_0622hard over-decomposition (2026-06-22): the planner offered `iso_lemma1` = the WHOLE
    target with `E→q, R→Q` renamed as a "sub-lemma." The textual circularity check (`_norm_ws(==)`) can't see
    an α-rename, so the no-op DAG was accepted and a directly-provable goal got fragmented. The kernel leg
    (`@G = @Lᵢ := rfl` via the canonical statement_integrity oracle) catches it. ENHANCEMENT-ONLY + fail-open:
    rfl fires only on a genuine defeq (never rejects a real sub-lemma) and the leg is GATED on the caller
    threading the goal statement (so it is byte-parity when absent — verified here without invoking Lean)."""
    from pathlib import Path
    import ztare.leanmill.solver.statement_integrity as _si
    import ztare.gates.v33_preflight_risk_detector as _v33
    from ztare.leanmill.solver.conjecture import decomposition_dag_audit
    G_src = "theorem G (E : Nat -> Nat) : (∀ a : Nat, E a = E a) := by sorry"
    L = "theorem isoL (q : Nat -> Nat) : (∀ a : Nat, q a = q a) := by sorry"   # G renamed E->q (same Prop)
    chain = "theorem G (E : Nat -> Nat) : (∀ a : Nat, E a = E a) := by exact isoL E"
    saved_eq, saved_cp = _si.kernel_type_equiv_fn, _v33._compile_probe
    factory_calls = {"n": 0}
    try:
        _v33._compile_probe = lambda *a, **k: False    # never touch real Lean in this unit test

        def _factory(name, root):
            factory_calls["n"] += 1
            return lambda a, b: True                    # oracle: the renamed sub-lemma IS the same Prop as G
        _si.kernel_type_equiv_fn = _factory
        # (1) WITH the goal statement threaded → kernel-circular reject (returns before any compile leg)
        passed, v = decomposition_dag_audit([L], chain, ["isoL"], Path("/tmp"), 30,
                                            goal_source=G_src, goal_name="G")
        assert passed is False and "CIRCULAR (kernel" in v.get("killed", ""), v
        # (2) PARITY: WITHOUT the goal statement the kernel leg is never entered (oracle factory not called)
        factory_calls["n"] = 0
        decomposition_dag_audit([L], chain, ["isoL"], Path("/tmp"), 30)   # no goal_source/goal_name
        assert factory_calls["n"] == 0, "kernel-circularity leg ran without goal_source (parity broken)"
    finally:
        _si.kernel_type_equiv_fn, _v33._compile_probe = saved_eq, saved_cp
