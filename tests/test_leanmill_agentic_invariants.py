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


def test_refutation_reuse_requires_current_statement():
    """A same-name counterexample for an older weaker statement must not be reused for a strengthened target."""
    from ztare.leanmill.solver.conjecture import _current_goal_prop, _refutation_matches_current_goal
    goal = ("theorem capstone (fullList : Nat → List Nat) "
            "(hComplete : ∀ m w, w ∈ fullList m) : ∀ m w, m = m")
    current = _current_goal_prop("capstone", goal, "")
    stale_probe = (
        "theorem capstone_counterexample : "
        "¬ (∀ (fullList : Nat → List Nat), ∀ m w, m = m) := by\n"
        "  intro h\n"
        "  exact False.elim (by contradiction)\n"
    )
    matching_probe = (
        "theorem witness : "
        "¬ (∀ (fullList : Nat → List Nat) (hComplete : ∀ m w, w ∈ fullList m), ∀ m w, m = m) := by\n"
        "  intro h\n"
        "  exact False.elim (by contradiction)\n"
    )
    assert current
    assert _refutation_matches_current_goal(stale_probe, "capstone", current) is False
    assert _refutation_matches_current_goal(matching_probe, "capstone", current) is True


def test_control_plane_statement_id_and_cache_authority():
    """Statement identity changes on strengthened propositions; semantic/staged caches stay advisory."""
    from ztare.leanmill.control_plane import CacheAuthority, StatementId, cache_authority
    weak = StatementId.from_parts(
        target_name="capstone",
        source_text="theorem capstone : ∀ m, m = m := by sorry",
        closed_prop="∀ m, m = m",
        nl_exact="prove capstone",
        substrate_text="def A := Nat",
    )
    strong = StatementId.from_parts(
        target_name="capstone",
        source_text="theorem capstone (h : True) : ∀ m, m = m := by sorry",
        closed_prop="True → ∀ m, m = m",
        nl_exact="prove capstone",
        substrate_text="def A := Nat",
    )
    assert weak.closed_prop_hash != strong.closed_prop_hash
    assert weak.cache_key() != strong.cache_key()
    assert cache_authority("proof_cache") is CacheAuthority.PROOF_CREDIT
    assert cache_authority("banked_rung") is CacheAuthority.PROOF_CREDIT
    assert cache_authority("staged_reuse") is CacheAuthority.AFFORDANCE
    assert cache_authority("semantic_shelf") is CacheAuthority.AFFORDANCE


def test_staged_proof_store_marks_reuse_as_affordance(tmp_path):
    """Staged proof reuse is a seed only; it must never present itself as proof-credit."""
    import json
    from ztare.leanmill.solver.proof_cache import StagedProofStore

    store = StagedProofStore(tmp_path)
    (tmp_path / "k1.lean").write_text(
        "theorem g (a b : Nat) : a + b = b + a := by exact Nat.add_comm a b",
        encoding="utf-8",
    )
    store.stage("k1", "g", "theorem g (a b : Nat) : a + b = b + a := by sorry")

    rows = [
        json.loads(line)
        for line in (tmp_path / "_staged_index.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert rows[-1]["schema"] == "leanmill.staged_proof.v1"
    assert rows[-1]["cache_authority"] == "affordance"
    assert rows[-1]["proof_credit_eligible"] is False

    hit = store.retrieve("theorem g (x y : Nat) : x + y = y + x := by sorry", "g")
    assert hit is not None
    assert hit["cache_authority"] == "affordance"
    assert hit["proof_credit_eligible"] is False


def test_defeq_reuse_candidate_marks_kernel_verified_credit():
    """Defeq-filtered banked reuse is not semantic advice; it is credit only through kernel/governance."""
    from ztare.leanmill.solver.proof_cache import defeq_reuse_candidate

    hit = defeq_reuse_candidate(
        "theorem g (x y : Nat) : x + y = y + x := by sorry",
        "g",
        [{"name": "addComm_banked", "statement": "theorem addComm_banked (a b : Nat) : a + b = b + a := by sorry"}],
        lean_root=None,
        equiv_fn=lambda _goal, _candidate: True,
    )
    assert hit is not None
    assert hit["cache_authority"] == "proof_credit"
    assert hit["proof_credit_eligible"] is True
    assert hit["proof_credit_authority"] == "kernel_defeq_then_governance_reverify"


def test_memory_regression_registry_points_to_executable_guards():
    """Every promoted LeanMill memory/RCA class should point at an executable regression guard."""
    from pathlib import Path
    from ztare.leanmill.memory_regressions import REGRESSIONS, validate_memory_regressions

    repo = Path(__file__).resolve().parents[1]
    missing = validate_memory_regressions(repo)
    assert not missing, "\n".join(missing)
    ids = {r.id for r in REGRESSIONS}
    for required in {
        "stale_refutation_dropped_hypothesis",
        "falsify_probe_glob_single_door",
        "exact_nl_verbatim_reference_reuse",
        "cold_dependency_resolution_is_inconclusive",
        "transactional_bank_rollback",
        "bank_candidate_reverify_before_live_swap",
        "reorder_fallback_rollback",
        "substrate_mutation_receipt",
        "run_manifest_authority_modes",
        "diagnostics_reads_run_manifest",
        "observability_bundle_joins_ledgers",
        "substrate_liveness_typed_verdicts",
        "statement_false_conflict_detection",
        "statement_false_typed_verdict_surface",
        "strategy_falsify_single_door",
        "soft_refutation_not_confirmed_memory",
        "governance_no_good_typed_verdict_surface",
        "no_good_statement_id_metadata",
        "faithfulness_statement_id_metadata",
        "definition_api_receipt",
        "cache_env_observability_matrix",
        "proof_flow_observability_timeline",
        "run_manifest_code_fingerprints",
        "observability_layering_no_factory_bypass",
        "definition_api_summary_in_diagnostics",
        "library_delta_receipt",
        "library_delta_summary_in_diagnostics",
        "control_plane_audit_covers_roadmap",
        "triviality_targets_multidecl_theorem_signature",
        "cheap_triviality_probe_bounded_tactics",
    }:
        assert required in ids


def test_control_plane_audit_covers_roadmap():
    """The cleanup roadmap should have a machine-readable artifact+guard coverage audit."""
    from pathlib import Path
    from ztare.leanmill.control_plane_audit import audit_control_plane

    repo = Path(__file__).resolve().parents[1]
    audit = audit_control_plane(repo)
    assert audit["schema"] == "leanmill.control_plane_audit.v1"
    assert audit["ok"], audit
    assert audit["item_count"] == 9
    assert audit["objective_1_7"]["schema"] == "leanmill.control_plane_objective_1_7.v1"
    assert audit["objective_1_7"]["ok"], audit["objective_1_7"]
    assert audit["objective_1_7"]["item_count"] == 7
    by_title = {item["title"]: item for item in audit["items"]}
    assert by_title["first_class_statement_identity"]["regression_ids"]
    assert "bank_candidate_reverify_before_live_swap" in by_title["transactional_substrate_mutation"]["regression_ids"]
    assert "observability_layering_no_factory_bypass" in by_title["unified_run_observability"]["regression_ids"]


def test_observability_layering_no_factory_bypass():
    """Factory should consume the unified run bundle instead of rebuilding run RCA from lower-level readers."""
    import inspect
    from pathlib import Path
    from ztare.leanmill import run_observability as ro

    repo = Path(__file__).resolve().parents[1]
    factory_src = (repo / "scripts/public/control/leanmill/factory_intelligence.py").read_text(encoding="utf-8")
    assert "build_observability_bundle" in factory_src
    assert "from ztare.leanmill.run_diagnostics import" not in factory_src
    assert "summarize_run(" not in factory_src
    obs_src = inspect.getsource(ro.build_observability_bundle)
    assert "from ztare.leanmill.run_diagnostics import summarize_run" in obs_src
    assert "from ztare.leanmill.verdict_store import summarize_verdicts" in obs_src


def test_falsify_refutation_reuse_uses_canonical_robust_probe_glob():
    """The falsify reuse reader must route through the canonical robust-probe glob, not only `*target*`."""
    import inspect
    from ztare.leanmill.solver import conjecture

    src = inspect.getsource(conjecture._reverify_agent_refutation)
    assert "robust_probe_glob" in src
    assert "_rpg(target_name)" in src
    assert 'f"*{target_name}*.lean"' in src


def test_reference_reuse_verbatim_requires_exact_nl_match():
    """Semantic reference recall may guide the gate, but verbatim reuse requires an exact NL key hit."""
    import inspect
    from ztare.leanmill.solver import autoformalize

    src = inspect.getsource(autoformalize.autoformalize_and_solve)
    assert '_ref_exact = bool(_ref0.get("exact"))' in src
    assert '_reuse_stmt = (_ref_stmt or "").strip() if locals().get("_ref_exact") else ""' in src


def test_cold_compile_dependency_resolution_failure_is_inconclusive(monkeypatch, tmp_path):
    """A cold toolchain/dependency failure is unavailable instrumentation, not a broken substrate verdict."""
    from types import SimpleNamespace
    import os
    import subprocess
    import shutil
    from ztare.formal import repl_compile

    fake_lake = os.sys.executable
    monkeypatch.setattr(shutil, "which", lambda _cmd: fake_lake)

    def run_dep_fail(*_args, **_kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="error: unknown module prefix 'Mathlib'")

    monkeypatch.setattr(subprocess, "run", run_dep_fail)
    assert repl_compile._substrate_cold_compiles(tmp_path / "T.lean", str(tmp_path), 1) is None

    def run_real_error(*_args, **_kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="T.lean:1:1: error: unsolved goals")

    monkeypatch.setattr(subprocess, "run", run_real_error)
    assert repl_compile._substrate_cold_compiles(tmp_path / "T.lean", str(tmp_path), 1) is False

    def run_clean(*_args, **_kwargs):
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", run_clean)
    assert repl_compile._substrate_cold_compiles(tmp_path / "T.lean", str(tmp_path), 1) is True


def test_substrate_liveness_emits_typed_verdicts(tmp_path, monkeypatch):
    """Warm/cold substrate RCA should expose unavailable vs broken as typed verdicts, not prose only."""
    from ztare.formal import repl_compile
    from ztare.leanmill.verdict_store import iter_verdict_rows

    verdicts = tmp_path / "verdicts.jsonl"
    theory = tmp_path / "T.lean"
    theory.write_text("theorem t : True := by trivial\n", encoding="utf-8")
    monkeypatch.setenv("ZTARE_LEANMILL_VERDICT_TRACE", str(verdicts))
    monkeypatch.setenv("ZTARE_SOLVER_RUN_TAG", "run-substrate")
    src = theory.read_text(encoding="utf-8")
    repl_compile._emit_substrate_verdict(theory, str(tmp_path), "unavailable", "toolchain unavailable", src)
    repl_compile._emit_substrate_verdict(theory, str(tmp_path), "broken", "unexpected token", src)
    rows = iter_verdict_rows(verdicts, run_tag="run-substrate", target_name="T.lean")
    assert [r["verdict"]["kind"] for r in rows] == ["substrate_unavailable", "substrate_broken"]
    assert rows[0]["extra"]["substrate_verdict"] == "unavailable"
    assert rows[1]["extra"]["substrate_verdict"] == "broken"


def test_typed_verdict_store_writes_locked_jsonl(tmp_path, monkeypatch):
    """Typed verdicts should have one append surface instead of ad hoc prose-log reconstruction."""
    import json
    from ztare.leanmill.control_plane import StatementId, Verdict, VerdictKind
    from ztare.leanmill.verdict_store import emit_verdict, iter_verdict_rows, summarize_verdicts

    out = tmp_path / "verdicts.jsonl"
    monkeypatch.setenv("ZTARE_LEANMILL_VERDICT_TRACE", str(out))
    monkeypatch.setenv("ZTARE_SOLVER_RUN_TAG", "run-a")
    sid = StatementId.from_parts(target_name="T", closed_prop="∀ n : Nat, n = n")
    ok = emit_verdict(Verdict(
        kind=VerdictKind.UNVERIFIED,
        statement_id=sid,
        provenance="unit_test",
        detail="candidate did not compile",
    ), extra={"probe": "p"})
    row = json.loads(out.read_text(encoding="utf-8").strip())
    assert ok is True
    assert row["schema"] == "leanmill.verdict.v1"
    assert row["verdict"]["kind"] == "unverified"
    assert row["verdict"]["statement_id"]["closed_prop_hash"] == sid.closed_prop_hash
    assert row["extra"]["probe"] == "p"
    out.write_text(out.read_text(encoding="utf-8") + "not-json\n", encoding="utf-8")
    rows = iter_verdict_rows(out, run_tag="run-a", target_name="T")
    assert len(rows) == 1
    assert iter_verdict_rows(out, run_tag="other") == []
    summary = summarize_verdicts(out, run_tag="run-a")
    assert summary["total"] == 1
    assert summary["by_kind"]["unverified"] == 1
    assert summary["latest_provenance"] == "unit_test"


def test_substrate_mutation_receipt_shape():
    """Transactional bank diagnostics should be typed, not only legacy prose/dict fields."""
    from ztare.leanmill.control_plane import SubstrateMutationKind, SubstrateMutationReceipt
    rec = SubstrateMutationReceipt(
        kind=SubstrateMutationKind.BANK_DECL_TO_ENV,
        target_name="foo",
        context_path="theory.lean",
        stage="missing_banked_name_reverted",
        before_sha256="a",
        after_sha256="b",
        changed=True,
        result={"banked_as": None, "reason": "reverted_noncompile"},
    ).to_json()
    assert rec["kind"] == "bank_decl_to_env"
    assert rec["changed"] is True
    assert rec["result"]["reason"] == "reverted_noncompile"


def test_bank_attempts_emit_typed_mutation_receipt():
    """The transactional bank logger should carry the typed receipt beside legacy fields."""
    import inspect
    from ztare.leanmill.solver import family_lemma_library

    src = inspect.getsource(family_lemma_library._record_bank_attempt)
    assert "leanmill.substrate_mutation.v1" in src
    assert "SubstrateMutationReceipt" in src
    assert '"run_tag": os.environ.get("ZTARE_SOLVER_RUN_TAG", "")' in src
    assert '"mutation": receipt.to_json()' in src


def test_falsify_gate_emits_typed_verdict_telemetry():
    """The falsify single door should emit typed verdict telemetry without changing its tuple API."""
    import inspect
    from ztare.leanmill.solver.conjecture import (
        adjudicate_statement_false_verdict,
        verify_statement_false_claim,
    )

    gate_src = inspect.getsource(adjudicate_statement_false_verdict)
    verify_src = inspect.getsource(verify_statement_false_claim)
    assert "emit_verdict" in gate_src
    assert "_remember_refutation" in gate_src
    assert "VerdictKind.UNVERIFIED" in gate_src
    assert "verify_statement_false_claim" in verify_src
    assert "adjudicate_statement_false_verdict" in verify_src


def test_statement_false_adjudicator_records_memo_and_typed_verdict(tmp_path, monkeypatch):
    """A kernel-confirmed ¬G from any producer should feed the same memo and typed verdict surface."""
    from ztare.leanmill.solver import conjecture
    from ztare.leanmill.verdict_store import iter_verdict_rows

    out = tmp_path / "verdicts.jsonl"
    monkeypatch.setenv("ZTARE_LEANMILL_VERDICT_TRACE", str(out))
    monkeypatch.setenv("ZTARE_SOLVER_RUN_TAG", "run-falsify")
    conjecture._CONFIRMED_REFUTATIONS.clear()
    goal = "theorem target_false_route (n : Nat) : n = n := by sorry"
    block = "theorem target_false_route_refute : ¬ (∀ n : Nat, n = n) := by intro h; exact False.elim (by contradiction)"
    ok, detail, kept = conjecture.adjudicate_statement_false_verdict(
        "target_false_route", "", goal, True, "unit-confirmed", block,
        provenance="unit.strategy_falsify")
    assert ok is True
    assert detail == "unit-confirmed"
    assert kept == block
    assert conjecture.confirmed_refutation("target_false_route", "", goal) == block
    typed = conjecture.confirmed_refutation_verdict("target_false_route", "", goal)
    assert typed is not None
    assert typed["kind"] == "refuted"
    assert typed["artifacts"]["lean_source"] == block
    rows = iter_verdict_rows(out, run_tag="run-falsify", target_name="target_false_route")
    assert len(rows) == 1
    assert rows[0]["verdict"]["kind"] == "refuted"
    assert rows[0]["verdict"]["provenance"] == "unit.strategy_falsify"


def test_soft_refutation_does_not_pollute_statement_false_memory(tmp_path, monkeypatch):
    """Soft reformulation feedback is not confirmed no-good memory."""
    from ztare.leanmill.solver import autoformalize, solver_core

    monkeypatch.setenv("ZTARE_LEANMILL_VERDICT_TRACE", "0")
    monkeypatch.setattr(solver_core, "OUT_DIR", tmp_path)
    statement = "theorem soft_refutation_target : True := by trivial"
    assert autoformalize._record_statement_false_no_good(
        statement, "leaf marker only", confirmed=False, source="unit_soft") is False
    assert not (tmp_path / "solver_lane_no_good_store.jsonl").exists()
    assert autoformalize._record_statement_false_no_good(
        statement, "kernel-confirmed counterexample", confirmed=True, source="unit_confirmed") is True
    txt = (tmp_path / "solver_lane_no_good_store.jsonl").read_text(encoding="utf-8")
    assert '"failure_class": "statement_false"' in txt
    assert '"source": "unit_confirmed"' in txt


def test_strategy_falsify_uses_shared_statement_false_gate():
    """The strategist falsify/corroborate sink should not bypass the shared ¬G verdict door."""
    import inspect
    from ztare.leanmill.solver import solver_core

    src = inspect.getsource(solver_core._build_dag_move_runner)
    assert "adjudicate_statement_false_verdict" in src
    assert "strategy_move." in src
    assert "NoGoodStore" in src
    assert 'source=f"strategy_{_mkey}' in src


def test_closure_certificate_emits_typed_verdict_telemetry():
    """Governed closure certificates should also feed the typed verdict ledger."""
    import inspect
    from ztare.leanmill.solver import solver_core

    src = inspect.getsource(solver_core.solve_adhoc)
    assert "solve_adhoc_governed_closure_certificate" in src
    assert "VerdictKind.CLOSED if r0.get(\"outcome\") == \"closed\" and _gov_verified" in src
    assert "VerdictKind.REJECTED_BY_GOVERNANCE" in src
    assert "emit_verdict(Verdict(" in src


def test_definition_api_receipt_surfaces_reuse_risks():
    """Definition/API receipts expose noncomputable defs and target-used defs without named API."""
    from ztare.leanmill.definition_contract import emit_definition_api_receipt
    src = """
def ReducibleThing (n : Nat) : Nat := n + 1

noncomputable def picked (p : ∃ n : Nat, n = n) : Nat := Classical.choose p

structure Matching where
  held : Nat -> Option Nat

theorem target : picked ⟨0, rfl⟩ = picked ⟨0, rfl⟩ := by
  rfl
"""
    receipt = emit_definition_api_receipt(src, target_name="target")
    by_name = {d.name: d for d in receipt.definitions}
    assert by_name["picked"].computability == "noncomputable"
    assert by_name["picked"].name_signature_text.startswith("picked :: noncomputable def picked")
    assert "target_depends_without_named_api" in by_name["picked"].flags
    assert "structure_without_visible_invariant" in by_name["Matching"].flags
    assert "has_noncomputable_definition" in receipt.summary_flags


def test_library_delta_receipt_surfaces_api_graph_risks():
    """Library-delta receipts expose public declaration identity, graph edges, namespaces, and API warnings."""
    from ztare.leanmill.library_delta import emit_library_delta_receipt
    src = """
namespace Ledger

def total (xs : List Int) : Int := xs.foldl (· + ·) 0

def isolated : Nat := 0

theorem applyLeg_total (xs : List Int) : total xs = total xs := by
  rfl

theorem punit_bad : PUnit = PUnit := by
  rfl

end Ledger
"""
    receipt = emit_library_delta_receipt(src, target_name="applyLeg_total")
    assert receipt.schema == "leanmill.library_delta_receipt.v1"
    assert receipt.summary["target_present"] is True
    by_name = {d.name: d for d in receipt.public_decls}
    assert by_name["total"].namespace == "Ledger"
    assert by_name["total"].signature_hash
    assert by_name["applyLeg_total"].kind == "theorem"
    assert any(e.source == "applyLeg_total" and e.target == "total" for e in receipt.dependency_edges)
    assert "definition_without_theorem_surface" in by_name["isolated"].warnings
    assert "unit_surface_outside_named_counterexample" in by_name["punit_bad"].warnings
    assert receipt.summary["dependency_edge_count"] >= 1
    assert "definition_without_theorem_surface" in receipt.warnings


def test_definition_api_policy_accessor_reads_factory_shape():
    """Definition/API contract readers should go through policy.py, not parse JSON locally."""
    from ztare.leanmill.policy import definition_api_contract_policy_from_policy
    pol = definition_api_contract_policy_from_policy({"operations": {"definition_api_contract": {
        "mode": "diagnostic",
        "require_receipt_for_public_review": True,
        "warn_on_noncomputable_definition": False,
    }}})
    assert pol["mode"] == "diagnostic"
    assert pol["require_receipt_for_public_review"] is True
    assert pol["warn_on_noncomputable_definition"] is False
    assert pol["warn_on_target_definition_without_named_api"] is True


def test_gale_filed_artifact_has_definition_api_receipt():
    """The filed Gale artifact should emit a reusable API receipt for reviewer-visible modeling facts."""
    from pathlib import Path
    from ztare.leanmill.definition_contract import emit_definition_api_receipt
    p = Path(__file__).resolve().parents[2] / "nonmathlib4" / "Nonmathlib" / "SocialChoice" / (
        "DeferredAcceptanceStabilityAndQuiescenceLoadBearing.lean")
    if not p.exists():
        return
    receipt = emit_definition_api_receipt(
        p.read_text(encoding="utf-8", errors="replace"),
        target_name="deferred_acceptance_stability_and_quiescence_load_bearing",
    )
    names = {d.name for d in receipt.definitions}
    assert "ProposalRun" in names
    assert "BlockingPairNoDecidable" in names
    assert any("noncomputable" in d.flags for d in receipt.definitions if d.name == "BlockingPairNoDecidable")


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


def test_pool_honors_dead_api_cache():
    """The proposer pool's API path honors the SAME process dead-API cache as the leaf. The bug (2026-06-22):
    the leaf's dead-API protection lived only in `agentic_leaf.default_dispatch`, so the pool's API proposers
    (`llm_runtime.call_text`, default 300s + cross-model fallback) hung the whole proposer WAVE on a dead model
    — the forgotten sibling of the dead-API-leaf class. A known-dead API model must now be skipped (None) without
    a call_text, and a dispatch_fn injection must still bypass the API path entirely."""
    from ztare.leanmill.solver.agentic_leaf import _DEAD_API_RUNTIMES
    from ztare.leanmill.solver.proposer_pool import propose_with_model
    _DEAD_API_RUNTIMES.discard("kimi")
    try:
        _DEAD_API_RUNTIMES.add("kimi")
        # kimi is an API model (not a subscription leaf) → API branch → dead-cache skip → None (no call_text)
        assert propose_with_model("kimi", "prove it", repo=".", timeout=10) is None
        # an injected dispatch_fn bypasses the API path and still works even for a dead-cached model
        out = propose_with_model("kimi", "p", repo=".", timeout=10,
                                 dispatch_fn=lambda m, p: "```lean\nby rfl\n```")
        assert out is not None and out.proof_text == "by rfl", out
    finally:
        _DEAD_API_RUNTIMES.discard("kimi")


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


def test_closure_conservation_flags_unratified_closed():
    """Every `closed` attempt must trace to a RATIFICATION (a ratified=1 row OR a closure cert). A `closed` with
    NEITHER is a producer that recorded a closure it never put through governance — the proposer-pool drop, where
    the pool wrote a bare-name `closed/ratified=NULL` row while governance stamped a DIFFERENT row_id, so the
    target read closed-NOT-ratified and the run summaries reported it as a win. trust_conservation_audit checks
    ratified⟹cert; this is the inverse net (closed⟹ratification) that would have caught it. Hermetic: a temp
    sqlite + jsonl ledger, no Lean / DB-of-record. (Verified on the real buggy run: it flags exactly the two
    factorization targets the pool 'closed' but never ratified.)"""
    import json
    import sqlite3
    import tempfile
    from pathlib import Path
    from ztare.leanmill.run_standards import closure_telemetry_conservation_audit
    d = tempfile.mkdtemp()
    db = str(Path(d) / "attempts.db")
    led = str(Path(d) / "certs.jsonl")
    con = sqlite3.connect(db)
    con.execute("create table attempts (row_id text, attempt_at text, outcome text, compile_ok int, "
                "ratified int, move text, run_tag text)")
    ts = "2026-06-22T01:00:00+00:00"
    con.executemany("insert into attempts values (?,?,?,?,?,?,?)", [
        # (a) THE BUG: a 'closed' compile_ok row with NO ratified and NO cert → MUST be flagged
        ("dropped_target", ts, "closed", 1, None, "proposer_pool", "t"),
        # (b) a legit closure: 'closed' with ratified=1 stamped → conserved (excluded from the claim set)
        ("adhoc::good_target", ts, "closed", 1, 1, "native_hammer", "t"),
        # (c) a 'closed' with no ratified but a CERT for it → conserved (traceable to ratification evidence)
        ("adhoc::cert_target", ts, "closed", 1, None, "claude_warm", "t"),
    ])
    con.commit()
    con.close()
    Path(led).write_text(json.dumps({"target": "cert_target", "outcome": "closed", "ts": ts}) + "\n",
                         encoding="utf-8")
    res = closure_telemetry_conservation_audit("2026-06-22T00:00:00+00:00", run_tag="t", db_path=db, ledger=led)
    assert res["ok"] is False, res
    assert any("dropped_target" in v for v in res["violations"]), res
    assert not any("good_target" in v for v in res["violations"]), res    # ratified=1 → conserved
    assert not any("cert_target" in v for v in res["violations"]), res    # has a cert → conserved


def test_run_diagnostics_reads_run_manifest_even_when_attempts_db_missing(tmp_path):
    """Diagnostics should preserve launch authority state from run_manifest, not rely only on attempts/logs."""
    import json
    import time
    from ztare.leanmill.run_diagnostics import read_run_manifest, render, summarize_run

    manifest = tmp_path / "run_manifest.json"
    manifest.write_text(json.dumps({
        "schema": "leanmill.run_manifest.v1",
        "run_tag": "r1",
        "run_scratch": "r1",
        "git_head": "abc123",
        "blueprint": {"path": "bp.md", "sha256": "b"},
        "substrate": {"path": "theory.lean", "sha256": "s"},
        "providers": {
            "schema": "leanmill.provider_manifest.v1",
            "solve_providers": ["codex"],
            "subscription_runtime": "codex",
        },
        "code_fingerprints": {
            "schema": "leanmill.code_fingerprints.v1",
            "files": {"src/ztare/leanmill/solver/autoformalize_notes.py": "abc"},
        },
        "authority_modes": {"proposer_pool": "0", "staged_reuse": "0", "bank_env_ratify": "1"},
        "cache_authority_classes": {"proof_cache": "proof_credit", "staged_reuse": "affordance"},
        "definition_api_receipt": {
            "schema": "leanmill.definition_api_receipt.v1",
            "target_name": "target",
            "summary_flags": ["has_noncomputable_definition"],
            "definitions": [
                {
                    "name": "picked",
                    "kind": "def",
                    "computability": "noncomputable",
                    "flags": ["noncomputable", "target_depends_without_named_api"],
                },
                {"name": "Plain", "kind": "structure", "computability": "computable_or_structural", "flags": []},
            ],
        },
        "library_delta_receipt": {
            "schema": "leanmill.library_delta_receipt.v1",
            "target_name": "target",
            "summary": {
                "public_decl_count": 3,
                "theorem_count": 1,
                "definition_count": 2,
                "dependency_edge_count": 2,
                "warning_count": 1,
            },
            "warnings": ["definition_without_theorem_surface"],
            "public_decls": [
                {
                    "name": "target",
                    "kind": "theorem",
                    "namespace": "",
                    "warnings": [],
                },
                {
                    "name": "picked",
                    "kind": "def",
                    "namespace": "",
                    "warnings": ["definition_without_theorem_surface"],
                },
            ],
        },
    }), encoding="utf-8")

    mf = read_run_manifest(manifest_path=manifest)
    assert mf["authority_modes"]["bank_env_ratify"] == "1"
    assert mf["cache_authority_classes"]["staged_reuse"] == "affordance"
    assert mf["providers"]["solve_providers"] == ["codex"]
    assert mf["code_fingerprints"]["files"]["src/ztare/leanmill/solver/autoformalize_notes.py"] == "abc"
    assert mf["definition_api_summary"]["definition_count"] == 2
    assert mf["definition_api_summary"]["flagged_definition_count"] == 1
    assert mf["definition_api_summary"]["summary_flags"] == ["has_noncomputable_definition"]
    assert mf["library_delta_summary"]["public_decl_count"] == 3
    assert mf["library_delta_summary"]["dependency_edge_count"] == 2
    assert mf["library_delta_summary"]["flagged_decl_count"] == 1
    assert mf["library_delta_summary"]["warnings"] == ["definition_without_theorem_surface"]
    assert "definition_api_receipt" not in mf
    assert "library_delta_receipt" not in mf

    summary = summarize_run(db_path=tmp_path / "missing.db", run_tag="r1", manifest_path=manifest)
    assert summary["total"] == 0 and "error" in summary
    assert summary["run_manifest"]["path"] == str(manifest)
    assert summary["run_manifest"]["definition_api_summary"]["flagged_definition_count"] == 1
    assert summary["run_manifest"]["library_delta_summary"]["flagged_decl_count"] == 1
    assert "manifest:" in render(summary)
    assert "definition/api:" in render(summary)
    assert "library-delta:" in render(summary)

    verdicts = tmp_path / "verdicts.jsonl"
    verdicts.write_text(json.dumps({
        "schema": "leanmill.verdict.v1",
        "ts": time.time(),
        "run_tag": "r1",
        "verdict": {
            "kind": "refuted",
            "statement_id": {"target_name": "T", "closed_prop_hash": "h"},
            "provenance": "unit",
        },
    }) + "\n", encoding="utf-8")
    summary2 = summarize_run(
        db_path=tmp_path / "missing.db",
        run_tag="r1",
        manifest_path=manifest,
        verdict_path=verdicts,
    )
    assert summary2["typed_verdicts"]["by_kind"]["refuted"] == 1
    assert "typed verdicts:" in render(summary2)


def test_run_observability_bundle_joins_existing_ledgers(tmp_path):
    """One RCA bundle should join manifest, attempts, verdicts, bank, formalize, notes, and CoT ledgers."""
    import json
    import sqlite3
    from ztare.leanmill.run_observability import build_observability_bundle, render_bundle

    run_tag = "run-obs"
    manifest = tmp_path / "run_manifest.json"
    substrate = tmp_path / "theory.lean"
    substrate.write_text("theorem t : True := by trivial\n", encoding="utf-8")
    manifest.write_text(json.dumps({
        "schema": "leanmill.run_manifest.v1",
        "run_tag": run_tag,
        "substrate": {"path": str(substrate), "sha256": "s"},
        "authority_modes": {"proposer_pool": "0", "staged_reuse": "0", "bank_env_ratify": "1"},
        "cache_authority_classes": {"proof_cache": "proof_credit"},
    }), encoding="utf-8")

    attempts = tmp_path / "attempts.db"
    con = sqlite3.connect(attempts)
    con.execute("CREATE TABLE attempts (row_id TEXT, attempt_at TEXT, move TEXT, outcome TEXT, "
                "error_class TEXT, notes TEXT, ratified INT, run_tag TEXT)")
    con.execute("INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)",
                ("T", "2026-07-07T00:00:00+00:00", "codex", "failed_compile",
                 "other_error", "unknown identifier Foo", None, run_tag))
    con.commit()
    con.close()

    verdicts = tmp_path / "verdicts.jsonl"
    verdicts.write_text(json.dumps({
        "schema": "leanmill.verdict.v1",
        "ts": 1,
        "run_tag": run_tag,
        "verdict": {"kind": "unverified", "statement_id": {"target_name": "T"}, "provenance": "unit"},
    }) + "\n", encoding="utf-8")
    bank = tmp_path / "bank.jsonl"
    bank.write_text(
        json.dumps({
            "schema": "leanmill.substrate_mutation.v1",
            "run_tag": run_tag,
            "context": str(substrate),
            "target": "T",
            "stage": "final_revert",
            "result": {"reason": "reverted_noncompile"},
            "changed": False,
        }) + "\n" +
        json.dumps({
            "schema": "leanmill.substrate_mutation.v1",
            "context": str(substrate),
            "stage": "legacy",
            "result": {"reason": "legacy_unscoped"},
        }) + "\n",
        encoding="utf-8",
    )
    formalize = tmp_path / "formalize.jsonl"
    formalize.write_text(json.dumps({
        "run_tag": run_tag,
        "phase": "lemma",
        "render_hash": "abc",
        "outcome": "rejected",
        "reason": "UNFAITHFUL to the registered substrate",
    }) + "\n", encoding="utf-8")
    notes = tmp_path / "notes.jsonl"
    notes.write_text(json.dumps({"run_tag": run_tag, "kind": "write_refined_notes"}) + "\n", encoding="utf-8")
    cot = tmp_path / "cot.jsonl"
    cot.write_text(json.dumps({"run_tag": run_tag, "runtime": "codex", "gap": "need helper"}) + "\n", encoding="utf-8")
    proof_cache = tmp_path / "proof_cache.jsonl"
    proof_cache.write_text(json.dumps({
        "schema": "leanmill.proof_cache.v1",
        "key": "H:abc",
        "proof": "by trivial",
        "source": "adhoc_closure:T",
        "cache_authority": "proof_credit",
        "proof_credit_eligible": True,
        "statement_id": {"target_name": "T", "closed_prop_hash": "h"},
    }) + "\n", encoding="utf-8")
    staged_dir = tmp_path / "checkpoints"
    staged_dir.mkdir()
    (staged_dir / "s1.lean").write_text("theorem t : True := by trivial\n", encoding="utf-8")
    staged_index = staged_dir / "_staged_index.jsonl"
    staged_index.write_text(json.dumps({
        "schema": "leanmill.staged_proof.v1",
        "key": "s1",
        "target": "T",
        "body_path": "s1.lean",
        "cache_authority": "affordance",
        "proof_credit_eligible": False,
    }) + "\n", encoding="utf-8")
    no_good = tmp_path / "no_good.jsonl"
    no_good.write_text(json.dumps({
        "key": "H:abc",
        "failure_class": "statement_false",
        "source": "unit",
        "statement_id": {"target_name": "T", "closed_prop_hash": "h"},
    }) + "\n", encoding="utf-8")
    faithfulness = tmp_path / "faithfulness.jsonl"
    faithfulness.write_text(json.dumps({
        "kind": "faithful",
        "source": "unit",
        "statement_id": {"target_name": "T", "closed_prop_hash": "h"},
    }) + "\n", encoding="utf-8")
    decomp = tmp_path / "decomp.jsonl"
    decomp.write_text(json.dumps({
        "schema": "leanmill.decomposition_cache.v1",
        "target": "T",
        "lemmas": ["a", "b"],
    }) + "\n", encoding="utf-8")

    bundle = build_observability_bundle(
        run_tag=run_tag,
        attempts_db=attempts,
        manifest_path=manifest,
        verdicts_path=verdicts,
        bank_attempts_path=bank,
        formalize_attempts_path=formalize,
        notes_trace_path=notes,
        cot_traces_path=cot,
        proof_cache_path=proof_cache,
        no_good_path=no_good,
        faithfulness_path=faithfulness,
        decomposition_cache_path=decomp,
        staged_index_path=staged_index,
    )
    assert bundle["schema"] == "leanmill.run_observability_bundle.v1"
    assert bundle["attempts"]["by_failure_class"]["unknown_identifier"] == 1
    assert bundle["typed_verdicts"]["by_kind"]["unverified"] == 1
    assert bundle["bank_mutations"]["by_reason"]["reverted_noncompile"] == 1
    assert bundle["bank_mutations"]["unscoped_rows_seen"] == 1
    assert bundle["bank_mutations"]["scope"] == "run_tag"
    assert "bank_attempt_rows_without_run_tag_present" not in bundle["warnings"]
    assert bundle["formalize_attempts"]["unique_render_hashes"] == 1
    assert bundle["notes_writebacks"]["by_kind"]["write_refined_notes"] == 1
    assert bundle["cot_traces"]["gaps"]["need helper"] == 1
    assert bundle["cache_surfaces"]["proof_cache"]["expr_key_rows"] == 1
    assert bundle["cache_surfaces"]["proof_cache"]["scope"] == "cross_run_store"
    assert bundle["cache_surfaces"]["proof_cache"]["proof_credit_eligible"] == 1
    assert bundle["cache_surfaces"]["staged_reuse"]["active_rows"] == 1
    assert bundle["cache_surfaces"]["staged_reuse"]["scope"] == "explicit_index"
    assert bundle["cache_surfaces"]["staged_reuse"]["proof_credit_eligible"] == 0
    assert bundle["cache_surfaces"]["no_good"]["by_failure_class"]["statement_false"] == 1
    assert bundle["cache_surfaces"]["faithfulness"]["by_kind"]["faithful"] == 1
    assert bundle["cache_surfaces"]["decomposition_cache"]["avg_lemmas"] == 2.0
    assert bundle["cache_surfaces"]["authority_totals"]["proof_credit"] == 1
    assert bundle["cache_surfaces"]["authority_totals"]["affordance"] == 1
    assert bundle["env_transitions"]["chain"][1]["environment"] == "campaign_warm_repl"
    assert bundle["env_transitions"]["chain"][3]["environment"] == "lake_env_lean_from_byte_zero"
    flow = bundle["proof_flows"]["targets"]["T"]
    assert flow["by_state"]["attempt"] == 1
    assert flow["by_state"]["typed_verdict"] == 1
    assert flow["by_state"]["substrate_mutation"] == 1
    assert flow["by_state"]["cache_surface"] >= 3
    assert "governance_certificate" in flow["by_environment"] or "typed_verdict_ledger" in flow["by_environment"]
    assert "persisted_substrate_file_then_cold_reverify" in flow["by_environment"]
    assert bundle["operator_readout"]["status"] == "blocked"
    assert bundle["operator_readout"]["primary_bottleneck"] == "substrate_env_parity"
    rendered = render_bundle(bundle)
    assert "leanmill-observability" in rendered
    assert "operator: status=blocked bottleneck=substrate_env_parity" in rendered
    assert "cache:" in rendered and "env:" in rendered and "flows:" in rendered


def test_axiom_pack_priority_pilot_is_quarantined_and_observable(tmp_path):
    """AxiomPack v1 should stress a pilot pack without granting theorem credit."""
    import json
    from ztare.leanmill.axiom_pack import (
        append_axiom_pack_event,
        generate_candidate_axiom_pack,
        lint_axiom_pack_blueprint,
        priority_uncrossed_order_blueprint,
        stress_axiom_pack,
        stress_pack_for_domain,
        theorem_campaign_consumption_gate,
    )
    from ztare.leanmill.run_observability import build_observability_bundle, render_bundle

    blueprint = priority_uncrossed_order_blueprint()
    lint = lint_axiom_pack_blueprint(blueprint)
    assert lint["ok"] is True

    pack, generation = generate_candidate_axiom_pack(blueprint)
    assert generation["ok"] is True
    assert generation["move_card"]["canonical_engine"] == "ztare.research_director.research_isomorphism"
    stressed = stress_pack_for_domain(pack, blueprint)
    stress = stress_axiom_pack(stressed)

    assert stress["ok"] is False
    assert {"strength_comparison", "separation_or_interpretation", "downstream_yield"} <= set(
        stress["missing_stress_receipts"]
    )
    assert stressed.to_json()["proof_credit_eligible"] is False
    assert stressed.to_json()["theorem_campaign_admissible"] is False
    assert theorem_campaign_consumption_gate(stressed)["allowed"] is False
    semantic = next(
        row for row in stressed.stress_receipts if row.get("dimension") == "semantic_certification"
    )
    assert semantic["suite"]["status"] == "SAT_WITHOUT_COMPLETE_INDEPENDENCE_WITNESSES"

    store = tmp_path / "axiom_pack_candidates.jsonl"
    append_axiom_pack_event(store, pack=stressed, stress=stress, blueprint=blueprint, generation=generation)
    bundle = build_observability_bundle(
        run_tag="",
        attempts_db=tmp_path / "missing.db",
        verdicts_path=tmp_path / "missing_verdicts.jsonl",
        bank_attempts_path=tmp_path / "missing_bank.jsonl",
        formalize_attempts_path=tmp_path / "missing_formalize.jsonl",
        notes_trace_path=tmp_path / "missing_notes.jsonl",
        cot_traces_path=tmp_path / "missing_cot.jsonl",
        proof_cache_path=tmp_path / "missing_proof_cache.jsonl",
        no_good_path=tmp_path / "missing_no_good.jsonl",
        faithfulness_path=tmp_path / "missing_faithfulness.jsonl",
        decomposition_cache_path=tmp_path / "missing_decomp.jsonl",
        axiom_packs_path=store,
    )
    assert bundle["axiom_packs"]["total"] == 1
    assert bundle["axiom_packs"]["by_status"]["quarantined"] == 1
    assert bundle["axiom_packs"]["proof_credit_eligible_rows"] == 0
    assert "axiom_packs:" in render_bundle(bundle)


def test_agent_isomorphism_tool_uses_canonical_research_engine_without_credit():
    """The leaf move must delegate to research_isomorphism and remain advisory."""
    import inspect
    from ztare.leanmill import agent_tools

    src = inspect.getsource(agent_tools._tool_isomorphism)
    assert "ztare.research_director" in src
    assert "research_isomorphism" in src
    assert "proof_credit_eligible" in src
    assert "can_mutate_substrate" in src


def test_axiom_pack_discovery_eval_scores_cached_agent_trial():
    """A cached agent blueprint trial should be measurable but remain quarantined."""
    from ztare.leanmill.axiom_pack import run_axiom_pack_discovery_eval

    report = run_axiom_pack_discovery_eval(domain="priority", include_second_domain=True)

    assert report["schema"] == "leanmill.axiom_pack_discovery_eval.v1"
    assert report["ok"] is False
    assert report["mode"] == "cached"
    assert report["hand_tooled_risk"] is True
    assert report["primary"]["agent_blueprint_lint"]["ok"] is False
    assert any(
        str(reason).startswith("typed_formula_ir:")
        for reason in report["primary"]["agent_blueprint_lint"]["violations"]
    )
    criteria = {
        row["name"]: row["pass"]
        for row in report["primary"]["usefulness_score"]["criteria"]
    }
    assert criteria["no_proof_credit_leakage"] is True
    assert report["primary"]["isomorphism_receipt"]["canonical_engine"] == "ztare.research_director.research_isomorphism"
    second = report["second_domain_eval"]
    assert second is not None
    assert second["domain"] == "inverse_semigroup_partial_symmetry_structures"
    assert second["usefulness_score"]["ok"] is False


def test_inverse_semigroup_cheap_stress_surfaces_second_domain():
    """The second AxiomPack domain should separate partial inverse behavior from group collapse."""
    from ztare.leanmill.axiom_pack import (
        generate_candidate_axiom_pack,
        inverse_semigroup_axiom_blueprint,
        score_axiom_pack_usefulness,
        stress_axiom_pack,
        stress_pack_for_domain,
    )

    blueprint = inverse_semigroup_axiom_blueprint()
    pack, generation = generate_candidate_axiom_pack(blueprint)
    assert generation["ok"] is True
    stressed = stress_pack_for_domain(pack, blueprint)
    stress = stress_axiom_pack(stressed)
    score = score_axiom_pack_usefulness(stressed, stress)

    assert stress["ok"] is False
    assert score["ok"] is False
    semantic = next(
        row for row in stressed.stress_receipts if row.get("dimension") == "semantic_certification"
    )
    assert semantic["suite"]["joint_satisfiability"]["status"] == "SAT"
    assert semantic["suite"]["status"] == "SAT_WITHOUT_COMPLETE_INDEPENDENCE_WITNESSES"


def test_state_convergence_conflicts_include_statement_false(tmp_path):
    """A cached proof and a kernel-¬G no-good for the same key must surface as a convergence conflict."""
    import json
    from ztare.leanmill.state_convergence import detect_conflicts

    (tmp_path / "solver_lane_proof_cache.jsonl").write_text(
        json.dumps({"key": "K", "proof": "by trivial"}) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "solver_lane_no_good_store.jsonl").write_text(
        json.dumps({"key": "K", "failure_class": "statement_false", "witness": "counterexample"}) + "\n",
        encoding="utf-8",
    )
    conflicts = detect_conflicts(tmp_path)
    assert len(conflicts) == 1
    assert conflicts[0].key == "K"
    assert "statement_false" in conflicts[0].detail


def test_no_good_statement_false_emits_typed_refuted_verdict(tmp_path, monkeypatch):
    """The shared statement_false ledger should also feed the typed verdict surface."""
    import json
    from ztare.leanmill.solver.no_good_store import NoGoodStore
    from ztare.leanmill.verdict_store import iter_verdict_rows

    verdicts = tmp_path / "verdicts.jsonl"
    monkeypatch.setenv("ZTARE_LEANMILL_VERDICT_TRACE", str(verdicts))
    monkeypatch.setenv("ZTARE_SOLVER_RUN_TAG", "run-ng")
    store = NoGoodStore(tmp_path / "solver_lane_no_good_store.jsonl")
    stmt = "theorem refuted_target : False := by sorry"
    assert store.record(stmt, "statement_false", "counterexample", confirmed=True, source="unit")
    assert not store.record(stmt, "statement_false", "counterexample", confirmed=True, source="unit")

    rows = iter_verdict_rows(verdicts, run_tag="run-ng", target_name="refuted_target")
    assert len(rows) == 1
    verdict = rows[0]["verdict"]
    assert verdict["kind"] == "refuted"
    assert verdict["provenance"] == "no_good_store.confirmed_no_good"
    assert verdict["statement_id"]["target_name"] == "refuted_target"
    assert json.loads((tmp_path / "solver_lane_no_good_store.jsonl").read_text())["failure_class"] == "statement_false"


def test_no_good_governance_classes_emit_typed_rejected_verdict(tmp_path, monkeypatch):
    """Confirmed governance no-goods should not bypass the typed verdict surface."""
    from ztare.leanmill.solver.no_good_store import NoGoodStore
    from ztare.leanmill.verdict_store import iter_verdict_rows

    verdicts = tmp_path / "verdicts.jsonl"
    monkeypatch.setenv("ZTARE_LEANMILL_VERDICT_TRACE", str(verdicts))
    store = NoGoodStore(tmp_path / "solver_lane_no_good_store.jsonl")
    stmt = "theorem altered_target : Nat = Nat := by sorry"
    assert store.record(stmt, "definition_altered", "definition_altered: helper changed", confirmed=True, source="unit")

    rows = iter_verdict_rows(verdicts, target_name="altered_target")
    assert len(rows) == 1
    assert rows[0]["verdict"]["kind"] == "rejected_by_governance"
    assert rows[0]["verdict"]["provenance"] == "no_good_store.confirmed_no_good"
    assert rows[0]["extra"]["failure_class"] == "definition_altered"


def test_no_good_rows_carry_statement_id_and_legacy_rows_still_load(tmp_path, monkeypatch):
    """New no-good rows should carry StatementId metadata without orphaning legacy key-only rows."""
    import json
    from ztare.leanmill.solver.no_good_store import NoGoodStore

    monkeypatch.setenv("ZTARE_LEANMILL_VERDICT_TRACE", "0")
    path = tmp_path / "solver_lane_no_good_store.jsonl"
    store = NoGoodStore(path)
    stmt = "theorem no_good_target (n : Nat) : n = n := by sorry"
    assert store.record(stmt, "definition_altered", "definition_altered: helper changed", confirmed=True)
    row = json.loads(path.read_text(encoding="utf-8").strip())
    assert row["statement_id"]["target_name"] == "no_good_target"
    assert row["statement_id"]["closed_prop_hash"]
    assert row["statement_id"]["target_source_hash"]
    assert store.matches("theorem renamed_target (n : Nat) : n = n := by sorry")

    legacy = tmp_path / "legacy_no_good.jsonl"
    legacy.write_text(json.dumps({
        "key": row["key"],
        "statement": stmt,
        "failure_class": "definition_altered",
        "witness": "legacy witness",
    }) + "\n", encoding="utf-8")
    legacy_store = NoGoodStore(legacy)
    assert legacy_store.matches(stmt)[0]["witness"] == "legacy witness"


def test_faithfulness_rows_carry_statement_id_and_legacy_rows_still_load(tmp_path):
    """Faithfulness correspondences should expose StatementId metadata while preserving legacy `norm` matching."""
    import json
    from ztare.leanmill.solver.faithfulness_store import FaithfulnessStore, _stmt_identity

    path = tmp_path / "solver_lane_faithfulness_store.jsonl"
    nl = "addition on natural numbers commutes"
    stmt = "theorem faithful_target (a b : Nat) : a + b = b + a := by sorry"
    store = FaithfulnessStore(path)
    assert store.record(nl, stmt, confirmed=True, fingerprint={"conclusion_op": "eq"}, source="unit")
    row = json.loads(path.read_text(encoding="utf-8").strip())
    assert row["statement_id"]["target_name"] == "faithful_target"
    assert row["statement_id"]["closed_prop_hash"]
    assert row["statement_id"]["nl_exact_hash"]
    assert store.confirms(nl, "theorem renamed_target (a b : Nat) : a + b = b + a := by sorry")

    legacy = tmp_path / "legacy_faithfulness.jsonl"
    legacy.write_text(json.dumps({
        "key": row["key"],
        "kind": "faithful",
        "nl": nl,
        "statement": stmt,
        "norm": _stmt_identity(stmt),
        "fingerprint": {"conclusion_op": "eq"},
    }) + "\n", encoding="utf-8")
    legacy_store = FaithfulnessStore(legacy)
    assert (legacy_store.reference(nl) or {}).get("statement") == stmt
    assert legacy_store.confirms(nl, "theorem renamed_target (a b : Nat) : a + b = b + a := by sorry")


def test_except_audit_catches_swallowed_nameerror():
    """A stdlib name used inside a SWALLOWING try/except with no in-scope import is flagged (the silent-
    NameError / dead-instrument class — the `try/except: pass` that uses `re`/`json`/`Path` without importing
    it, NameErrors on every call, and silently no-ops). The four CORRECT patterns are NOT flagged: a local
    `import`, an aliased local import (the fix idiom), a re-raise (not swallowing), and a module-level import."""
    import tempfile
    import textwrap
    from pathlib import Path
    from ztare.leanmill.except_audit import scan_file
    d = Path(tempfile.mkdtemp())
    bug = d / "bug.py"
    bug.write_text(textwrap.dedent('''
        def f(x):
            try:
                return re.sub("a", "b", x)   # `re` never imported in scope -> NameError, swallowed
            except Exception:
                pass
    '''), encoding="utf-8")
    hits = scan_file(bug)
    assert any(nm == "re" and fn == "f" for (_f, _ln, fn, nm) in hits), hits
    clean = d / "clean.py"
    clean.write_text(textwrap.dedent('''
        import os
        def local_import(x):
            try:
                import re
                return re.sub("a", "b", x)
            except Exception:
                pass
        def aliased(x):
            import re as _re
            try:
                return _re.sub("a", "b", x)
            except Exception:
                pass
        def reraises(x):
            try:
                return re.sub("a", "b", x)
            except Exception:
                raise
        def module_imported(x):
            try:
                return os.path.join(x, "y")
            except Exception:
                pass
    '''), encoding="utf-8")
    assert scan_file(clean) == [], scan_file(clean)


def test_no_swallowed_nameerror_in_leanmill():
    """The leanmill tree carries no swallowed-NameError pattern (the going-forward net for the silent-no-op
    class — like flag_audit for split-brain defaults). A new `try/except: pass` that uses a stdlib name without
    importing it fails here instead of silently no-opping in production."""
    from ztare.leanmill.except_audit import scan_tree
    hits = scan_tree()
    assert not hits, ("swallowed-NameError candidate(s) — add a local `import <name>` in the function:\n"
                      + "\n".join(f"  {f.split('/src/')[-1]}:{ln} in {fn}() uses `{nm}`"
                                  for (f, ln, fn, nm) in hits))


def test_no_cross_file_duplicate_function_bodies():
    """No two module-level leanmill functions in DIFFERENT files share a byte-identical body — the forgotten-
    sibling shape (fix one copy, the other rots; it false-rejected a whole campaign via the kernel-equiv oracle
    copies). Consolidate to ONE canonical home, callers re-export. Found + fixed 3 on build (the depth-0 colon
    finder, `_public_path`, `_read_policy` → lean_source/common/policy, 2026-06-22)."""
    from ztare.leanmill.structural_audit import duplicate_function_bodies
    dups = duplicate_function_bodies()
    assert not dups, ("cross-file duplicate function bodies — consolidate to one canonical home:\n"
                      + "\n".join("  " + "  ==  ".join(f"{f.split('/src/')[-1]}:{ln} {fn}()"
                                                       for f, fn, ln in g) for g in dups))


def test_ratification_has_single_chokepoint():
    """The ratification stamp (`UPDATE attempts SET ratified`) has exactly ONE writer
    (`_record_governance_verdict`). A second writer is a PARALLEL ratification path — precisely how the pool's
    'closed' telemetry diverged from real governance (the closure-drop). A new writer fails here: route it
    through the chokepoint, or justify the exception."""
    from ztare.leanmill.structural_audit import ratification_chokepoint_violations
    viol = ratification_chokepoint_violations()
    assert not viol, ("parallel ratification-stamp writer(s) — route through _record_governance_verdict:\n"
                      + "\n".join(f"  {f.split('/src/')[-1]}:{ln} {fn}()" for f, fn, ln in viol))


def test_dup_detector_actually_fires():
    """The duplicate-body detector is not trivially passing — it fires on a real cross-file byte-identical
    non-trivial function. Hermetic: two temp files with the same body."""
    import tempfile
    import textwrap
    from pathlib import Path
    from ztare.leanmill.structural_audit import duplicate_function_bodies
    d = Path(tempfile.mkdtemp())
    body = textwrap.dedent('''
        def shared(xs):
            total = 0
            seen = []
            for x in xs:
                if x > 0:
                    total += x * 2
                    seen.append(x)
                elif x < 0:
                    total -= x
                else:
                    total += 1
            return total, seen
    ''')
    (d / "a.py").write_text(body, encoding="utf-8")
    (d / "b.py").write_text(body, encoding="utf-8")
    groups = duplicate_function_bodies(root=d)
    assert any(len(g) == 2 and {fn for _f, fn, _ln in g} == {"shared"} for g in groups), groups


def test_campaign_probe_assembler_citable_in_scope():
    """Notes-path cure (the 'text-context ≠ compile-scope' bug class): `assemble_campaign_probe` is the SINGLE
    source of truth for a target's COMPILE SCOPE. It MUST put every proven shelf lemma IN SCOPE (before the
    target) so a lemma advertised 'citable' in the notes is actually citable, AND dedup shared definitions
    (theory-building targets inline the same `def`/`structure`) so composing never duplicate-declares; on an
    unresolvable conflict it falls back to the bare target, never a wrong merge. This is the notes-path analogue
    of the conservation/chokepoint guards: it fails CI if the assembler ever stops enforcing citable⟺in-scope, or
    if `default_solve` reintroduces a hand-rolled concat instead of routing through the assembler."""
    from ztare.leanmill.solver.autoformalize import assemble_campaign_probe

    # citable ⟺ in-scope: shelf theorems land BEFORE the target; exactly one import header
    shelf = "import Mathlib\ntheorem lemA : True := trivial\n\ntheorem lemB : True := trivial"
    tgt = "import Mathlib\ntheorem tgt : True := by have := lemA; have := lemB; trivial"
    body, info = assemble_campaign_probe(tgt, [shelf])
    assert info["composed"] and info["shelf_theorems"] == 2, info
    assert body.count("import Mathlib") == 1, "exactly one import header"
    assert body.index("theorem lemA") < body.index("theorem tgt"), "shelf must be in scope before the target"
    assert body.index("theorem lemB") < body.index("theorem tgt")

    # theory-building: shared def/structure dedup to ONCE, ordered defs < shelf < target (no duplicate-declare)
    sh = "import Mathlib\ndef Foo : Nat := 0\nstructure M where x : Nat\n\ntheorem lemA : Foo = 0 := rfl"
    tg = ("import Mathlib\ndef Foo : Nat := 0\nstructure M where x : Nat\n\n"
          "theorem tgt : Foo = 0 := by have := lemA; rfl")
    b2, i2 = assemble_campaign_probe(tg, [sh])
    assert i2["composed"] and b2.count("def Foo") == 1 and b2.count("structure M") == 1, (i2, b2)
    assert b2.index("def Foo") < b2.index("theorem lemA") < b2.index("theorem tgt"), "defs < shelf < target"

    # conflict (same name, DIFFERENT body) ⇒ fall back to the bare target, never a silent wrong merge
    c_sh = "import Mathlib\ndef Foo : Nat := 0\ntheorem lemA : Foo = 0 := rfl"
    c_tg = "import Mathlib\ndef Foo : Nat := 1\ntheorem tgt : Foo = 1 := rfl"
    b3, i3 = assemble_campaign_probe(c_tg, [c_sh])
    assert not i3["composed"] and i3["reason"] == "conflict" and "lemA" not in b3, i3
    # OBSERVABILITY: the conflict must NAME the drifted decl + carry both divergent bodies (so the orphaned-shelf
    # cause is readable in the log, never hand-diffed from the cert ledger — the APR `AbsolutePriority` drift class).
    assert i3["conflicts"] and i3["conflicts"][0]["name"] == "Foo", i3
    assert i3["conflicts"][0]["kept"] != i3["conflicts"][0]["rejected"], i3["conflicts"]

    # COMMENT-INSENSITIVE compose (2026-06-24): with the established-vocabulary cure the target copies the canonical
    # def VERBATIM incl. the theory file's trailing `/-- … -/` doc-comment, while the banked lemma probes carry the
    # comment-free body. These are SEMANTICALLY identical → they MUST compose (the old whitespace-only `_norm_block`
    # false-conflicted on the doc-comment alone, which would have re-orphaned the shelf even after the vocab fix).
    cc_sh = "import Mathlib\ndef AP (n : Nat) : Prop := n = 0\ntheorem apL : AP 0 := rfl"
    cc_tg = "import Mathlib\ndef AP (n : Nat) : Prop := n = 0\n/-- Anchor: AP is the zero predicate. -/\ntheorem apT : AP 0 := rfl"
    bcc, icc = assemble_campaign_probe(cc_tg, [cc_sh])
    assert icc["composed"] and bcc.count("def AP ") == 1, ("comment-only diff must compose to one def", icc)
    # but a REAL semantic difference (extra conjunct) must STILL conflict — soundness of the check is intact
    sem_tg = "import Mathlib\ndef AP (n : Nat) : Prop := n = 0 ∧ True\ntheorem apT : AP 0 := And.intro rfl trivial"
    _, isem = assemble_campaign_probe(sem_tg, [cc_sh])
    assert not isem["composed"] and isem["reason"] == "conflict", ("semantic diff must still conflict", isem)


def test_leaf_recovers_proof_from_response_not_just_file():
    """The 2026-06-23 'leaf solved it but didn't write the file' RCA: the warm leaf (claude opus) emitted a
    CORRECT proof in its RESPONSE but left the probe `sorry`, so the harness verified the untouched file and
    discarded a solved lemma as `uses_sorry` (the Topkis iso_lemma2, a 7-line proof). `_recover_proof_from_response`
    salvages it — extract the fenced Lean from the response, splice into the probe, RE-VERIFY (kernel-gated).
    Fails CI if recovery stops working OR stops being sound (a sorried/failing response must NOT be 'recovered',
    and the probe must be restored — never leave a broken file or mint a false closure)."""
    import tempfile
    from pathlib import Path
    from ztare.leanmill.solver.agentic_leaf import _recover_proof_from_response
    orig = "import Mathlib\n\ntheorem foo : True := by\n  sorry\n"
    with tempfile.TemporaryDirectory() as d:
        def mk(p):
            return lambda: (("sorry" not in p.read_text(encoding="utf-8")) and ("trivial" in p.read_text(encoding="utf-8")), "")
        # proof-body in the response ⇒ recovered (returns the proof string, TRUTHY); file no longer sorried
        p = Path(d) / "a.lean"; p.write_text(orig, encoding="utf-8")
        assert _recover_proof_from_response("done.\n```lean\ntrivial\n```", p, "foo", mk(p))  # truthy proof str
        assert "sorry" not in p.read_text(encoding="utf-8")
        # SOUND: a sorried response is NOT recovered (falsy ""), and the probe is restored unchanged
        p2 = Path(d) / "b.lean"; p2.write_text(orig, encoding="utf-8")
        assert not _recover_proof_from_response("```lean\nby sorry\n```", p2, "foo", mk(p2))
        assert p2.read_text(encoding="utf-8") == orig
        # SOUND: a candidate that fails re-verify restores the probe (no broken file, no false closure)
        p3 = Path(d) / "c.lean"; p3.write_text(orig, encoding="utf-8")
        assert not _recover_proof_from_response("```lean\nbogus_tactic\n```", p3, "foo", lambda: (False, ""))
        assert p3.read_text(encoding="utf-8") == orig


def test_direct_leaf_warmcheck_rejects_sorry():
    """The 2026-06-23 "agent thinks the file is proven" RCA: the warm-check (`lean_check_server --check`) defaults
    to ACCEPTING `sorry` ("OK — zero errors (1 sorry)"), so in DIRECT mode the agent read the sorried stub as
    "compiled cleanly" and stopped — the harness verify then rejected the sorry. The DIRECT leaf prompt must pass
    `--reject-sorry` so the agent's checker AGREES with the harness (sorry = error); DECOMPOSE must NOT (its
    `-- GAP:` sub-lemma sorries are intentional). Fails CI if that mode-targeting regresses."""
    import os
    from ztare.leanmill.solver.agentic_leaf import _leaf_prompt
    prev = os.environ.get("ZTARE_LEANMILL_LEAN_SOCKET")
    os.environ["ZTARE_LEANMILL_LEAN_SOCKET"] = "/tmp/test_sock"
    try:
        # check the COMMAND carries the flag (not just the explanatory mention `` `--reject-sorry` ``)
        assert "p.lean --reject-sorry" in _leaf_prompt("foo", "True", "p.lean", mode="direct"), \
            "DIRECT leaf warm-check COMMAND must pass --reject-sorry (else a sorried stub reads as 'compiled cleanly')"
        assert "p.lean --reject-sorry" not in _leaf_prompt("foo", "True", "p.lean", mode="decompose"), \
            "DECOMPOSE warm-check command must NOT reject sorry (intentional -- GAP: sub-lemmas)"
    finally:
        if prev is None:
            os.environ.pop("ZTARE_LEANMILL_LEAN_SOCKET", None)
        else:
            os.environ["ZTARE_LEANMILL_LEAN_SOCKET"] = prev


def test_probe_ref_matches_verified_probe_path():
    """THE 2026-06-23 root-cause bug ("leanmill can't close a trivial target"): `solve_leaf` told the agent to
    edit `probe_ref` while the harness wrote the stub to + verified `probe = probe_dir(...)`. With
    ZTARE_LEANMILL_RUN_SCRATCH set, `probe_dir` adds a run subdir but the hard-coded `.solver_scratch/<name>`
    probe_ref OMITTED it — so the agent wrote a CORRECT, sorry-free proof to one path and the harness read the
    sorried stub at another and discarded EVERY proof. probe_ref MUST be derived from `probe` so the path the
    agent edits and the path the harness verifies can never drift. Fails CI if the hard-coded form returns."""
    import os
    from ztare.leanmill.solver.agentic_leaf import probe_dir
    # behaviorally: with a run subdir set, probe_ref carries it (so it equals the verified probe's rel path)
    prev = os.environ.get("ZTARE_LEANMILL_RUN_SCRATCH")
    os.environ["ZTARE_LEANMILL_RUN_SCRATCH"] = "guardrun"
    try:
        import tempfile
        d = tempfile.mkdtemp()
        probe = probe_dir(d) / "RobustProbe_x.lean"
        assert os.path.relpath(str(probe), d) == os.path.join(".solver_scratch", "guardrun", "RobustProbe_x.lean")
    finally:
        if prev is None:
            os.environ.pop("ZTARE_LEANMILL_RUN_SCRATCH", None)
        else:
            os.environ["ZTARE_LEANMILL_RUN_SCRATCH"] = prev


def test_path_drift_visibility_net_recovers_sibling_proof():
    """VISIBILITY for the 2026-06-23 RCA class: when the harness verifies a non-closing probe but a sorry-free,
    kernel-verifying proof of the SAME target sits at a SIBLING scratch path (the silent-discard signature of a
    probe-path drift), the leaf surfaces it LOUDLY and recovers it — and a sorried sibling is never recovered (no
    false closure). This is the operator's "we had no visibility, the engine ran for hours discarding correct
    proofs" lesson turned into a self-healing alarm."""
    from ztare.leanmill.solver.agentic_leaf import _selftest_scratch_drift_recovery
    _selftest_scratch_drift_recovery()


def test_solve_adhoc_exposes_preverified_proof_governance_path():
    """The canonical 'send a compiling proof straight to governance' entry: solve_adhoc accepts a
    `preverified_proof` that routes through the SAME `_preverified_proof` seam the pool champion uses
    (kernel compile + MNC + axiom audit + statement_integrity + cert), NO re-derivation. Guards that the
    public param exists and wires to row['_preverified_proof']."""
    import inspect
    from ztare.leanmill.solver.solver_core import solve_adhoc
    sig = inspect.signature(solve_adhoc)
    assert "preverified_proof" in sig.parameters, "solve_adhoc must expose a public preverified_proof param"
    assert "preverified_only" in sig.parameters, "ratification-only must be able to forbid derivation fallback"

    # The ratification lifecycle must bypass both the forecast router and DAG move search even when the CLI's
    # ordinary default is dag_search.  These are executable source-shape guards around the two dispatch seams;
    # the end-to-end kernel ratification test exercises the resulting governance route.
    src = inspect.getsource(solve_adhoc)
    assert '_execution_mode = "cascade" if preverified_only else mode' in src
    solve_src = inspect.getsource(__import__(
        "ztare.leanmill.solver.solver_core", fromlist=["solve"]
    ).solve)
    assert '_ratification_only_batch = bool(rows) and all(' in solve_src
    assert 'if not _ratification_only_batch:' in solve_src
    assert 'if r.get("_preverified_only")' in solve_src
    assert '_pv_raw' in solve_src
    assert 'if preverified_only:' in src
    assert 'res["ratification_only"] = True' in src
    governed_src = inspect.getsource(__import__(
        "ztare.leanmill.solver.solver_core", fromlist=["solve_adhoc_governed"]
    ).solve_adhoc_governed)
    assert 'if kw.get("preverified_only"):' in governed_src
    assert 'max_gov_retries = 0' in governed_src


def test_robust_probe_name_single_sourced_no_drift():
    """The 2026-06-23 winner_probe bug: solve_robust WROTE `RobustProbe_<target>_<provider>_<i>` but recorded
    winner_probe (and solver_core read back) as `RobustProbe_<provider>_<i>` — so a kernel-VALID closure's probe
    was 'unreadable' and the proof was discarded (fail-closed). World-class cure (the operator's anti-sibling
    principle): ONE canonical namer (`robust_probe_name`/`robust_probe_glob`), every writer + recorder + reader
    routed through it. This guard fails if a produced name isn't matched by the reader glob, or a stale inline
    `RobustProbe_{...provider...}` pattern reappears at any write/read site."""
    import fnmatch
    from ztare.leanmill.solver.agentic_leaf import robust_probe_name, robust_probe_glob
    # (a) round-trip: every produced name is found by the canonical glob (odd chars + i>0 included)
    for tgt in ("iso_lemma1", "topkis::weird name/v2", "supermodular_argmaxSet_isSublatticeSet"):
        for prov in ("claude", "codex"):
            for i in (0, 3, 11):
                nm = robust_probe_name(tgt, prov, i)
                assert fnmatch.fnmatch(nm, robust_probe_glob(tgt, prov)), (nm, robust_probe_glob(tgt, prov))
                assert fnmatch.fnmatch(nm, robust_probe_glob(tgt)), nm   # provider-agnostic glob matches too


def test_redundant_subsumed_instance_lint_catches_diamond():
    """The 2026-06-23 iso_lemma1 RCA: the planner formalized a sub-lemma with `[LE α]` ON TOP OF `[Preorder α]`
    — an instance diamond (the bare `[LE α]` shadows Preorder's transitive `≤`) that makes the statement
    UNPROVABLE (verified on the VPS: the same statement WITHOUT the `[LE α]` proves, WITH it fails). The
    canonical-parser lint must flag the bare order class, and must NOT false-flag `[Add α]` (Preorder doesn't
    provide Add) or a clean statement."""
    from ztare.leanmill.lean_source import redundant_subsumed_instances as rsi
    diamond = ("theorem iso_lemma1 {α : Type*} [Add α] [LE α] [Preorder α] [AddLeftMono α] "
               "[AddRightReflectLE α] {a b c d : α} (h : a + b ≤ c + d) (hd : d ≤ b) : a ≤ c := by sorry")
    off = rsi(diamond, "iso_lemma1")
    assert any(o.startswith("LE α") for o in off), off
    clean = ("theorem ok {α : Type*} [Add α] [Preorder α] [AddLeftMono α] {a b : α} (h : a ≤ b) : a ≤ b := by sorry")
    assert rsi(clean, "ok") == [], rsi(clean, "ok")


def test_statement_false_extraction_catches_proved_refutation():
    """The 2026-06-23 iso_lemma1 RCA: the agent PROVED the counterexample as a `theorem …_statement_false`
    rather than leaving the `-- STATEMENT-FALSE:` comment, so the comment-only scan missed it and the malformed
    sub-lemma was recorded `failed_compile` instead of routing to the kernel-gated reformulation. Extraction must
    now catch BOTH forms (the kernel still re-verifies ¬G downstream, so this can never launder)."""
    import tempfile, os
    from ztare.leanmill.solver.agentic_leaf import _extract_statement_false
    # comment form (unchanged)
    p1 = tempfile.NamedTemporaryFile("w", suffix=".lean", delete=False)
    p1.write("theorem t : P := by\n  -- STATEMENT-FALSE: cex n=2\n  sorry\n"); p1.close()
    assert "cex n=2" in _extract_statement_false(p1.name)
    os.remove(p1.name)
    # proved-theorem form (the codex deviation that was missed)
    p2 = tempfile.NamedTemporaryFile("w", suffix=".lean", delete=False)
    p2.write("import Mathlib\ntheorem iso_lemma1_statement_false : True := trivial\n"); p2.close()
    assert "refutation decl" in _extract_statement_false(p2.name)
    os.remove(p2.name)


def test_denotation_anchor_prompt_offers_weaker_anchors_not_equality_only():
    """The 2026-06-23 StrongSetLE denotation gap: the anti-decoy prompt offered only a FULL Mathlib-equality
    anchor, so a theory-building concept Mathlib lacks (the Veinott strong set order) fell through to
    `@no-anchor` → UNDERDETERMINED even though it is pinnable (`StrongSetLE {a} {b} ↔ a ≤ b`, kernel-proven).
    GENERAL-PURPOSE fix (not StrongSetLE-specific): the prompt must offer the weaker kernel anchors —
    special-case REDUCTION and CHARACTERIZATION — and reserve `@no-anchor` for genuinely unanchorable defs, so
    ANY built def of a Mathlib-absent concept can reach PINNED."""
    import inspect
    from ztare.leanmill.solver import prompts
    src = inspect.getsource(prompts)
    for route in ("OVERLAP-AGREEMENT", "SPECIAL-CASE REDUCTION", "CHARACTERIZATION"):
        assert route in src, f"denotation anchor prompt must offer the {route} route (not equality-only)"
    assert "is NOT sufficient when a reduction or characterization exists" in src, \
        "@no-anchor must require ruling out reduction/characterization, not just 'no Mathlib equal'"


def test_nonvacuity_check_flags_unwitnessed_set_property():
    """Gemini's 2026-06-23 empty-set critique: a ∀-over-membership Prop def (StrongSetLE, IsSublatticeSet) is
    VACUOUSLY true on ∅, so a theorem concluding it of a constructed set (the parametric argmax) can be true-
    but-empty. The vacuity leg (sibling of denotation, same kernel boundary) flags an unwitnessed vacuity-prone
    def as VACUITY_EXPOSED, accepts a kernel-verified witness as WITNESSED, and respects an honest
    `@vacuity-scope` flag. General + advisory (never gates), grounded in the canonical parser via `def_body`."""
    from ztare.leanmill.solver.def_denotation import (
        certify_nonvacuity, vacuity_prone_defs, VACUITY_EXPOSED, WITNESSED, VACUITY_SCOPED, NOT_APPLICABLE)
    src = ("import Mathlib\n\ndef StrongSetLE {X : Type*} [SemilatticeSup X] [SemilatticeInf X] (s u : Set X) : "
           "Prop :=\n  ∀ ⦃x y : X⦄, x ∈ s → y ∈ u → x ⊓ y ∈ s ∧ x ⊔ y ∈ u\n")
    assert "StrongSetLE" in vacuity_prone_defs(src)
    assert certify_nonvacuity(src, verify_fn=lambda w: True)["verdict"] == VACUITY_EXPOSED
    w = src + ("theorem witness_StrongSetLE_nonvacuous {X : Type*} [SemilatticeSup X] "
               "[SemilatticeInf X] : ∃ s u : Set X, s.Nonempty ∧ u.Nonempty ∧ "
               "StrongSetLE s u := by sorry\n")
    assert certify_nonvacuity(w, verify_fn=lambda x: True)["verdict"] == WITNESSED
    assert certify_nonvacuity(src + "-- @vacuity-scope: StrongSetLE: empty when unbounded\n",
                              verify_fn=lambda x: False)["verdict"] == VACUITY_SCOPED
    assert certify_nonvacuity("import Mathlib\ndef f : Nat := 0\n", verify_fn=lambda x: True)["verdict"] == NOT_APPLICABLE
    import inspect
    from ztare.leanmill.solver import prompts
    psrc = inspect.getsource(prompts)
    assert "GUARD AGAINST VACUOUS TRUTH" in psrc and "witness_" in psrc, "prompt must offer the vacuity guard"


def test_structural_triggers_general_not_overfit_and_map_to_real_moves():
    """Channel-2 move-recall triggers (move_atlas dual-channel, 2026-06-23 across-the-board extension) key on
    GENERAL goal shapes — not target-specific tokens — guarantee a shape-keyed move reaches the menu when
    prose-cosine misses it (hybrid dense+sparse retrieval), and must not over-fire on lattice ALGEBRA. Each maps
    to a move that EXISTS in the corpus (a trigger can't surface a phantom)."""
    from ztare.leanmill.solver import move_atlas as A
    # extremal: general optimization fires; lattice algebra / unrelated does NOT
    assert A._shape_extremal("IsGreatest S m") and A._shape_extremal("∃ x, IsLUB s x") and A._shape_extremal("⨆ i, f i")
    assert not A._shape_extremal("a ⊔ b = b ⊔ a") and not A._shape_extremal("Continuous f")
    # uniqueness / decidable: general fires; unrelated does not
    assert A._shape_uniqueness_forcing("∃! x, P x") and A._shape_uniqueness_forcing("Subsingleton G")
    assert not A._shape_uniqueness_forcing("a + b = c")
    assert A._shape_decidable("Decidable p") and A._shape_decidable("s : Finset α")
    assert not A._shape_decidable("x : ℝ")
    # every trigger surfaces a REAL corpus move
    from ztare.leanmill.solver.move_corpus import build_corpus
    ids = {e.move_id for e in build_corpus()}
    for _m, mid in A._STRUCTURAL_TRIGGERS:
        assert mid in ids, f"trigger surfaces non-existent move {mid}"


def test_statement_false_short_circuits_before_decompose(monkeypatch):
    """The 2026-06-23 iso_lemma1 LOOP: an agent flags STATEMENT-FALSE and the kernel confirms ¬goal, but the
    verify ran only in solve_adhoc's END epilogue — so the leaf burned the whole decompose + best-of-N (claude
    ~545s × N) on a provably-false lemma before the re-plan could fire. Fix: a flag-time kernel verifier
    short-circuits (skip decompose, stop best-of-N). A None verifier preserves old behavior (parity).
    Soundness unchanged — governance re-verifies ¬goal before any re-plan; this only stops wasted dispatches."""
    from ztare.leanmill.solver import agentic_leaf as A
    monkeypatch.setenv("ZTARE_LEANMILL_LEAN_WARM", "0")
    monkeypatch.setattr(A, "_extract_statement_false", lambda p: "cex: take n=0")
    common = dict(defs="", project_dir=".", repo=".", lake_bin="lake",
                  dispatch=lambda p, **k: "ALIVE", verify=lambda: (False, "uses_sorry"))
    # kernel-confirmed false ⇒ short-circuit: no decompose, flagged confirmed, only the direct round
    r = A.solve_leaf("True", target="t", statement_false_verifier=lambda: True, **common)
    assert r.statement_false_confirmed and not r.decomposed and r.rounds == 1, (r.statement_false_confirmed, r.decomposed, r.rounds)
    # NOT confirmed (agent wrong) ⇒ continue to decompose (don't abandon a possibly-provable lemma)
    r2 = A.solve_leaf("True", target="t", statement_false_verifier=lambda: False, **common)
    assert not r2.statement_false_confirmed and r2.decomposed, (r2.statement_false_confirmed, r2.decomposed)
    # no verifier ⇒ old behavior (decompose runs) — parity
    r3 = A.solve_leaf("True", target="t", statement_false_verifier=None, **common)
    assert not r3.statement_false_confirmed and r3.decomposed
    # wiring threaded all the way (leaf → best-of-N → solver_core)
    import inspect
    assert "statement_false_verifier" in inspect.signature(A.solve_robust).parameters


def test_governed_def_revision_self_correction_path():
    """The autonomous self-correction path (2026-06-23): a kernel-confirmed-false lemma → governed def-revision
    → the agent STRENGTHENS the weak def, GATED so only a kernel-proven strengthening passes (anti-gaming) →
    re-attack. Guards the gate's soundness (strengthening accepted; unverified-witness rejected) + that the
    trigger is actually wired into the campaign loop (so it can't silently regress to a dead-end)."""
    from ztare.leanmill.solver.autoformalize_notes import governed_def_revision_gate, _detect_revised_def
    before = "import Mathlib\ndef D (n : Nat) : Prop := n ≥ 0\ntheorem other : True := trivial\n"
    after = ("import Mathlib\ndef D__pre (n : Nat) : Prop := n ≥ 0\ndef D (n : Nat) : Prop := n ≥ 0 ∧ n ≤ 9\n"
             "theorem witness_strengthen_D : ∀ n, D n → D__pre n := fun _ h => h.1\ntheorem other : True := trivial\n")
    assert _detect_revised_def(after) == "D"
    assert governed_def_revision_gate(before, after, "D", verify_fn=lambda w: w == "witness_strengthen_D")[0]
    assert not governed_def_revision_gate(before, after, "D", verify_fn=lambda w: False)[0]   # anti-gaming


def test_self_correction_loop_agent_elects_falsify_goldilocks():
    """Self-correction LOOP (2026-06-23, topkis_general RCA) — the GOLDILOCKS form (the operator's "why
    deterministic instead of the agent seeing it?"). The target pass, faithful to the literal NL
    ("single-crossing"), formalizes the WEAK def → FALSE. The DECISION to falsify is the AGENT's (a strategy/move,
    upstream agency), NOT a deterministic harness "falsify-on-stall" (that creep was tried + REVERTED). The agent
    elects FALSIFY at the strategy fork — MECE: Dim A (TRUTH: true→prove / false→falsify) × Dim B (HOW: direct/
    decompose); FALSIFY is the truth-branch, not a flat peer (docs §4.3a). A kernel-CONFIRMED ¬G then drives the
    EXISTING reformulation re-entry (`_solve_refutation` HARD path on outcome="falsified" → re-attack stronger).
    The kernel is the ONLY deterministic part (the soundness boundary)."""
    import inspect
    from ztare.leanmill.solver import solver_core, autoformalize
    import ztare.leanmill.solver.autoformalize_notes as an_mod
    # (a) the deterministic creep is GONE: no advisory steer, no falsify-on-stall in solve_adhoc.
    assert not hasattr(an_mod, "_supersession_steer") and not hasattr(an_mod, "_substrate_falsity_proofs"), \
        "the subsumed advisory steer must be REMOVED (replaced by the agency loop), not left as a 2nd surface"
    # (b) the strategy fork is the MECE 3-way verdict (truth × how); FALSIFY is an agent-electable strategy.
    assert hasattr(solver_core, "_agent_strategy_verdict") and not hasattr(solver_core, "_agent_recommends_decompose"), \
        "the binary decompose-ask must be replaced by the 3-way truth×how verdict (SOLVE_DIRECT/DECOMPOSE/FALSIFY)"
    from ztare.leanmill.solver import prompts as _p
    assert "FALSIFY" in _p.STRATEGY_ASSESSMENT_PROMPT and "TRUE" in _p.STRATEGY_ASSESSMENT_PROMPT, \
        "the strategy prompt must offer FALSIFY truth-first (Dim A), not a prove-only fork"
    # (e) the reformulation feedback ORIENTS strengthening (the agent kept re-emitting the weak/refuted reading
    #     because the old text over-constrained it to "don't weaken / stay faithful"). Un-blind, do NOT launder:
    #     it must say STRENGTHEN, show the refuting case, and name NO specific def (no overfit / no answer-feeding).
    fb = autoformalize._reformulate_feedback("theorem t (h : Weak f) : G := by sorry", "counterexample at x=0 (ties)")
    assert "STRENGTHEN" in fb and "too weak" in fb and "counterexample at x=0" in fb, \
        "reformulate feedback must orient STRENGTHENING + surface the refuting case (the agent's evidence)"
    assert "OrdinalStrongSingleCrossing" not in fb and "Milgrom" not in fb, \
        "reformulate feedback must NOT name a specific def (that would be laundering / overfitting, not orienting)"
    # prompt TEXT lives in prompts.py (not inline in autoformalize) — the operator's "prompts go in prompts.py"
    from ztare.leanmill.solver import prompts as _pr
    assert hasattr(_pr, "REFORMULATE_FEEDBACK") and "REFORMULATE_FEEDBACK" in inspect.getsource(autoformalize._reformulate_feedback), \
        "reformulation prompt text must live in prompts.py, assembled (not inlined) by _reformulate_feedback"
    # (f) ROUTE THE AGENT'S OWN CORRECTION: the consolidation pass proves the corrected (strong) theorem, but the
    #     fresh re-formalizer re-derives weak from the NL. `_substrate_proven_shelf` surfaces the substrate's OWN
    #     proven (sorry-free) theorems so the reformulation can ADOPT + CITE one (operator: "the agent proposed a
    #     reformulation — why isn't that the path?"). Proven listed, sorried + scaffolding excluded; feedback says CITE.
    #     2026-06-23: reads the registered substrate .lean CONTENT (where consolidation BANKS proofs), NOT the notes
    #     markdown — canonical `decl_blocks`/`_decl_is_definition`/`extract_signature`, NO regex.
    substrate_lean = ("import Mathlib\n"
                      "theorem strong_ok (h : Strict f) : G := by exact h.elim\n"
                      "theorem weak_bad (h : Weak f) : G := by sorry\n"
                      "theorem witness_scaffold (h : Strict f) : True := by trivial\n")
    shelf = autoformalize._substrate_proven_shelf(substrate_lean)
    assert "strong_ok" in shelf and "weak_bad" not in shelf and "witness_scaffold" not in shelf, \
        "proven-shelf must list the PROVEN result, EXCLUDE the sorried one AND the engine's own witness_/anchor_ scaffolding"
    fb2 = autoformalize._reformulate_feedback("theorem t (h : Weak f) : G := by sorry", "cex", shelf)
    assert "ALREADY-PROVEN" in fb2 and "CITE" in fb2 and "strong_ok" in fb2, \
        "with a proven shelf, the reformulation must route the agent to ADOPT + CITE its OWN proven theorem"
    assert "if none matches" in fb2, "the shelf block must be ADVISORY (agent judges relevance), not coercive"


def test_established_vocabulary_single_door_prevents_def_drift():
    """ORPHANED-SHELF / def-drift cure (2026-06-24). The class bug: every formalization-context path surfaced def
    NAMES (via lemma signatures) but never the canonical def BODIES, so each self-contained probe re-authored the
    shared vocabulary from the prose — and a target that minted a divergent same-named def (APR `AbsolutePriority`:
    2-clause vs the proven 1-clause) silently orphaned its own shelf at compose time → exact_gap. The cure is the
    DEFINITION companion to `_substrate_proven_shelf`, injected at the ONE formalize chokepoint (no sibling)."""
    import inspect
    from ztare.leanmill.solver import autoformalize, prompts
    SRC = ("import Mathlib\n"
           "def AbsolutePriority (c p : Nat) : Prop := c = p\n"
           "abbrev ClaimSchedule := Nat\n"
           "theorem anchor_AbsolutePriority_iff : True := trivial\n"
           "theorem ap_main (c p : Nat) : AbsolutePriority c p ∨ True := Or.inr trivial\n")
    # the new extractor surfaces def BODIES verbatim (copy-pasteable); the proven-shelf companion drops them
    defs = autoformalize._substrate_established_defs(SRC)
    assert "def AbsolutePriority (c p : Nat) : Prop := c = p" in defs and "abbrev ClaimSchedule" in defs, defs
    assert "theorem" not in defs and "ap_main" not in defs, "vocabulary block is DEFS only (results go via _substrate_proven_shelf)"
    # the reuse-verbatim norm + escape hatch are present (agency: reuse OR extend-under-a-new-name)
    note = prompts.ESTABLISHED_DEFS_NOTE.format(defs=defs)
    assert "do NOT redefine" in note and "NEW name" in note and "bridge" in note, note
    # SINGLE DOOR: the formalize chokepoint builds the formalizer context with the vocabulary, and the multistep
    # escalation is NOT a context-blind sibling — it threads the SAME _fctx. 2026-06-25: the chokepoint now ALSO
    # surfaces the proven-lemma SHELF (each banked rung's exact conclusion), not just the def BODIES — the AMM
    # `reachable_pool_wellFormed` gap RCA (a compounding target was formalized blind to what its named banked rung
    # actually CONCLUDES: the bank proved the trajectory predicate, not the endpoint the prose asked to "cite").
    # Assert the behavioral invariant (one reader feeds BOTH surfacers), NOT the exact call nesting (brittle).
    # PROVEN-SHELF AT FORMALIZE (2026-06-25): the proven-lemma shelf prompt exists and orients CITE/bridge.
    assert hasattr(prompts, "PROVEN_SHELF_NOTE"), "proven-shelf prompt constant must exist in prompts.py"
    assert "CITE" in prompts.PROVEN_SHELF_NOTE and "do NOT" in prompts.PROVEN_SHELF_NOTE, \
        "the proven-shelf note must orient CITE/bridge and warn against restating a rung under a wrong conclusion"
    assert "context" in inspect.signature(autoformalize.default_formalize_multistep).parameters, \
        "default_formalize_multistep must accept context (so the escalation reuses canonical vocabulary)"


def test_planner_steering_surfaces_relevant_banked_rungs_not_recent():
    """Decomposition-steering cure (2026-06-24): the rung-adjacency advisory that steers the planner toward
    proven infrastructure surfaces the rungs most IDENTIFIER-RELEVANT to the goal, not merely the k most RECENT
    (recency silently hid the relevant banked atoms behind newer unrelated closures → the planner re-derived).
    Goldilocks: still advisory + deterministic surfacing; the agent decides the decomposition, the kernel audits."""
    from ztare.leanmill.solver.rung_adjacency import render_adjacency_block
    # a deeply-buried RELEVANT rung followed by >k unrelated recent closures
    relevant = "theorem feas_of_linearOrder (claims : ClaimSchedule ι) : DistributionFeasible claims (WaterfallDistribution claims)"
    proven = [relevant] + [f"theorem recent_unrelated_{i} : Nat.Prime {7+i}" for i in range(10)]
    goal = "theorem tgt (claims : ClaimSchedule ι) : ∃ pay, DistributionFeasible claims pay"
    recency = render_adjacency_block(proven, k=8)              # last-8 ⇒ EXCLUDES the buried relevant rung
    relev = render_adjacency_block(proven, goal=goal, k=8)     # overlap ⇒ surfaces it
    assert "feas_of_linearOrder" not in recency, "recency-mode buries the relevant rung (the bug)"
    assert "feas_of_linearOrder" in relev, "relevance-mode must surface the goal-relevant banked rung"
    # parity: no goal ⇒ recency behaviour unchanged
    assert render_adjacency_block(proven, k=8) == render_adjacency_block(proven, goal="", k=8)


def test_proof_cache_keyed_on_canonical_expr_hash_not_text():
    """The cache-never-hits cure (2026-06-24): proof reuse is keyed on the kernel `Expr.hash` of the target's
    de-Bruijn TYPE (α-/∀-fronting-invariant), computed from the warm REPL — NOT a text regex over the probe (which
    mis-keyed multi-decl `define_then_state` probes on their leading def's `:=`). solve_adhoc computes the key ONCE
    and passes it to BOTH the pre-attack lookup and the closure deposit, so deposit-key == lookup-key; the cache
    dual-indexes (Expr key + text key) and re-verifies every hit (so the key needs only recall, never precision)."""
    from ztare.leanmill.solver.proof_cache import ProofCache
    from ztare.formal import repl_compile
    # the canonical-hash helper exists and is wired into solve_adhoc for BOTH lookup and deposit
    assert hasattr(repl_compile, "canonical_type_hash_via_repl")
    # the cache stores/reads under the supplied key, dual-indexed with the text key, and re-keys H: keys on reload
    import json
    import tempfile, os as _os
    p = tempfile.mktemp(suffix=".jsonl")
    c = ProofCache(p)
    assert c.put("theorem a (h:p) : q := by sorry", "by exact e", key="K1")
    row = json.loads(open(p, encoding="utf-8").read().strip())
    assert row["schema"] == "leanmill.proof_cache.v1"
    assert row["cache_authority"] == "proof_credit"
    assert row["proof_credit_eligible"] is True
    assert row["proof_credit_authority"] == "caller_kernel_verified_then_reverify_on_use"
    assert row["statement_id"]["closed_prop_hash"]
    assert c.get("theorem a (h:p) : q := by sorry", key="K1") == "by exact e"           # Expr-key hit
    assert c.get("theorem DIFFERENT_TEXT : zzz := by sorry", key="K1") == "by exact e"   # variant, same Expr key ⇒ hit
    assert c.get("theorem a (h:p) : q := by sorry") == "by exact e"                       # text-key fallback (no REPL)
    assert ProofCache(p).get("theorem whatever : w", key="K1") == "by exact e"            # survives reopen
    _os.remove(p)


def test_proof_cache_legacy_rows_still_load(tmp_path):
    """Adding proof-credit metadata must not orphan existing legacy proof-cache JSONL rows."""
    import json
    from ztare.leanmill.solver.proof_cache import ProofCache, _key_for

    stmt = "theorem legacy (n : Nat) : n = n := by sorry"
    p = tmp_path / "proof_cache.jsonl"
    p.write_text(json.dumps({
        "key": _key_for(stmt),
        "statement": stmt,
        "proof": "by rfl",
        "source": "legacy",
    }) + "\n", encoding="utf-8")
    assert ProofCache(p).get(stmt) == "by rfl"


def test_proof_cache_declines_missing_run_local_dependency_only(tmp_path):
    from ztare.leanmill.solver.proof_cache import ProofCache

    p = tmp_path / "proof_cache.jsonl"
    cache = ProofCache(p)
    statement = "theorem target : True := by sorry"
    assert cache.put(
        statement,
        "by exact denef_lipshitz_auxiliary_bridge",
        source="legacy-run-local",
    )
    assert cache.get(statement) == "by exact denef_lipshitz_auxiliary_bridge"
    assert cache.compatibility(statement) == (
        "legacy_unassessed", "by exact denef_lipshitz_auxiliary_bridge"
    )
    assert cache.get(statement, context_source=statement) is None
    assert cache.compatibility(statement, context_source=statement) == ("incompatible", None)
    assert cache.get(
        statement,
        context_source="theorem denef_lipshitz_auxiliary_bridge : True := by trivial\n" + statement,
    ) == "by exact denef_lipshitz_auxiliary_bridge"

    ordinary = "theorem ordinary : 1 = 1 := by sorry"
    assert cache.put(ordinary, "by rfl", source="ordinary", context_source=ordinary)
    assert cache.get(ordinary, context_source=ordinary) == "by rfl"
    assert cache.compatibility(ordinary) == ("context_unassessed", "by rfl")
    assert cache.compatibility(ordinary, context_source=ordinary) == ("compatible", "by rfl")


def test_cache_forecast_requires_compatible_context(tmp_path):
    from ztare.leanmill.solver.forecast_router import ProofCacheForecaster, WorkCandidate
    from ztare.leanmill.solver.proof_cache import ProofCache

    path = tmp_path / "proof_cache.jsonl"
    statement = "theorem target : True := by sorry"
    context = "theorem iso_lemma1 : True := by trivial\n" + statement
    ProofCache(path).put(statement, "by exact iso_lemma1", source="new", context_source=context)
    forecaster = ProofCacheForecaster(path)
    unassessed = forecaster.forecast(WorkCandidate("u", statement=statement))
    incompatible = forecaster.forecast(WorkCandidate(
        "i", statement=statement, context_features={"source_text": statement}
    ))
    compatible = forecaster.forecast(WorkCandidate(
        "c", statement=statement,
        context_features={"source_text": context},
    ))
    assert unassessed.abstain and unassessed.rationale == "cache context_unassessed"
    assert incompatible.abstain and incompatible.rationale == "cache incompatible"
    assert compatible.route_first and compatible.p_close == 0.98

    malformed_statement = "theorem malformed : 1 = 1 := by sorry"
    from ztare.leanmill.solver.proof_cache import _key_for
    with path.open("a", encoding="utf-8") as handle:
        handle.write(__import__("json").dumps({
            "key": _key_for(malformed_statement), "statement": malformed_statement,
            "proof": ":= by rfl", "source": "legacy",
        }) + "\n")
    malformed = ProofCacheForecaster(path).forecast(WorkCandidate(
        "m", statement=malformed_statement, context_features={"source_text": malformed_statement}
    ))
    assert malformed.abstain and malformed.rationale == "cache malformed"
    assert not ProofCache(path).put("theorem new_bad : 2 = 2", "```lean\nrfl\n```", source="leaf")


def test_permove_cap_uses_canonical_move_override(monkeypatch):
    from ztare.leanmill.solver.solver_core import _permove_cap

    monkeypatch.setenv("ZTARE_LEANMILL_CAP_WARM", "17")
    monkeypatch.setenv("ZTARE_LEANMILL_CAP_COLD_FRONTIER", "19")
    assert _permove_cap("warm", 999, 999) == 17
    assert _permove_cap("cold_frontier", 999, 999) == 19


def test_dag_failure_classifier_receives_trace_errors():
    import inspect
    from ztare.leanmill.solver import solver_core

    source = inspect.getsource(solver_core)
    assert '_dag_terminal = dag_res.get("terminal_signal") or {}' in source
    assert '"tail": str(_dag_terminal.get("tail") or _dag_terminal.get("error_class") or "")' in source
    assert '"terminal_signal": _dag_terminal' in source


def test_phase_timing_surfaces_dispatch_budget_utilization(tmp_path, monkeypatch):
    from ztare.leanmill.phase_timing import record_phase, summarize_phase_timings

    ledger = tmp_path / "timings.jsonl"
    monkeypatch.setenv("ZTARE_LEANMILL_PHASE_TIMING_LEDGER", str(ledger))
    record_phase("leaf.dispatch", 9.7, run_tag="r1",
                 extra={"requested_timeout_s": 10, "requested_runtime": "codex"})
    record_phase("leaf.dispatch", 2.0, run_tag="other",
                 extra={"requested_timeout_s": 20, "requested_runtime": "claude"})
    budget = summarize_phase_timings(run_tag="r1", ledger=ledger)["dispatch_budget"]
    assert budget["count"] == 1
    assert budget["near_cap_count"] == 1
    assert budget["utilization_mean"] == 0.97
    assert budget["by_runtime"] == {"codex": 1}


def test_observability_counts_orphaned_cache_environments(tmp_path):
    import json
    from ztare.leanmill.run_observability import _summarize_proof_cache
    from ztare.leanmill.solver.proof_cache import _key_for

    path = tmp_path / "proof_cache.jsonl"
    rows = [
        {"key": _key_for("theorem a : True"), "statement": "theorem a : True",
         "proof": "by exact iso_lemma1", "source": "legacy"},
        {"key": _key_for("theorem b : True"),
         "statement": "theorem iso_lemma2 : True := by trivial\ntheorem b : True",
         "proof": "by exact iso_lemma2\n#print axioms iso_lemma2", "source": "banked"},
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    summary = _summarize_proof_cache(path, "")
    assert summary["dependency_bearing_rows"] == 2
    assert summary["orphaned_environment_rows"] == 1


def test_statement_integrity_accepts_bare_target_probe_for_namespaced_original():
    """Cache-reuse probes may preserve the target statement while emitting the target outside the source namespace."""
    from ztare.leanmill.solver.statement_integrity import check
    original = (
        "namespace GaleShapleyStableMatchingProbe\n"
        "theorem rejected_man_stays_below_later_holds : True := by\n"
        "  sorry\n"
        "end GaleShapleyStableMatchingProbe\n"
    )
    probe = "theorem rejected_man_stays_below_later_holds : True := by\n  trivial\n"
    bad_probe = "theorem rejected_man_stays_below_later_holds : False := by\n  contradiction\n"

    ok = check(original, probe, "rejected_man_stays_below_later_holds")
    assert ok.ok, ok.violations

    bad = check(original, bad_probe, "rejected_man_stays_below_later_holds")
    assert any("target_signature_altered" in v for v in bad.violations), bad.violations


def test_warm_verify_self_contained_probe_audits_probe_namespace_not_campaign_namespace():
    """A self-contained probe may use a formalizer namespace; Path A must audit that decl before env-stripping."""
    import inspect
    from ztare.formal import repl_compile

    src = inspect.getsource(repl_compile.warm_verify_campaign)
    assert "_probe_decl_name(code, decl_name)" in src
    assert "_warm_check_audit(pl, project, code, _qual(decl_name), None, timeout)" not in src
    assert "_emit_verify_trace" in src


def test_warm_verify_trace_writes_jsonl_without_affecting_verdict(tmp_path, monkeypatch):
    """Verifier routing needs one-row RCA breadcrumbs; the trace must be best-effort and external to verdicts."""
    import json
    from ztare.formal import repl_compile

    out = tmp_path / "trace.jsonl"
    monkeypatch.setenv("ZTARE_LEANMILL_VERIFY_TRACE", str(out))
    repl_compile._emit_verify_trace(str(tmp_path), {
        "kind": "warm_verify_campaign",
        "target": "t",
        "path": "self_contained_base",
        "result": False,
        "diag": "type mismatch",
    })
    row = json.loads(out.read_text(encoding="utf-8").strip())
    assert row["kind"] == "warm_verify_campaign"
    assert row["target"] == "t"
    assert row["path"] == "self_contained_base"
    assert row["result"] is False


def test_notes_writeback_trace_writes_jsonl(tmp_path, monkeypatch):
    """Notes mutation must leave a compact breadcrumb: what file changed and what counts changed."""
    import json
    from ztare.leanmill.solver import autoformalize_notes as notes

    out = tmp_path / "notes_trace.jsonl"
    monkeypatch.setenv("ZTARE_LEANMILL_NOTES_TRACE", str(out))
    monkeypatch.setenv("ZTARE_SOLVER_RUN_TAG", "run-x")
    notes._emit_notes_writeback_trace({
        "kind": "write_refined_notes",
        "notes_path": "blueprint.md",
        "closed_count": 2,
        "open_count": 1,
    })
    row = json.loads(out.read_text(encoding="utf-8").strip())
    assert row["kind"] == "write_refined_notes"
    assert row["run_tag"] == "run-x"
    assert row["closed_count"] == 2
    assert row["open_count"] == 1


def test_compounding_dedup_message_does_not_claim_lost_citability():
    """A bank-env no-op is not automatically a lost reuse event; proof_cache/certs can still carry reuse."""
    import inspect
    from ztare.leanmill.solver import solver_core

    src = inspect.getsource(solver_core)
    assert "closure remains reusable through proof_cache/certs" in src
    assert "not citable next run; investigate bank_decl_to_env" not in src


def test_bank_reverify_uses_central_cold_compile_budget():
    """Bank-env ratification should honor the same cold_compile budget surfaced in the run manifest."""
    import inspect
    from ztare.formal import repl_compile
    from ztare.leanmill.solver import family_lemma_library

    src = inspect.getsource(family_lemma_library._default_reverify)
    assert 'timeout_s("cold_compile")' in src
    assert "_substrate_cold_compiles(fp, root, 600)" not in src
    assert "cold_timeout = 480" not in src
    cold_src = inspect.getsource(repl_compile._substrate_cold_compiles)
    assert "min(timeout, 600)" not in cold_src
    live_src = inspect.getsource(repl_compile)
    assert "_substrate_cold_compiles(p.resolve(), str(Path(lean_root).resolve()), 600)" not in live_src
    assert 'timeout_s("cold_compile")' in live_src


def test_def_shell_detection_canonical_and_shared_with_vocab():
    """Tasteful consolidation (2026-06-24): the def-shell GATE and the vocabulary EXCLUSION share ONE degeneracy
    core (`_degenerate_def_body`) over the canonical `decl_blocks` parser — NO hand-rolled decl regex, NO bare-vs-
    qualified name band-aid (the two never match on names; they ask the same predicate of the same block). Behavior
    is preserved: only `def`/`abbrev` constant shells are flagged (a structure/instance/axiom is not a 'shell')."""
    from ztare.leanmill.solver import autoformalize
    SRC = ("import Mathlib\nnamespace NS\n"
           "abbrev ClaimSchedule (ι : Type*) := ι → NNReal\n"
           "def AbsolutePriority {ι : Type*} (c p : ClaimSchedule ι) : Prop := ∀ i : ι, p i = c i\n"
           "def ZeroPay (ι : Type*) : ClaimSchedule ι := fun _ => 0\n"     # degenerate witness (shell)
           "abbrev Genus : Prop := True\n"                                   # degenerate (shell)
           "instance : Inhabited Nat := ⟨0⟩\n"                              # NOT a shell (instance, not def/abbrev)
           "structure Conc where a : Nat\nend NS\n")
    shells = {n for n, _ in autoformalize.detect_def_shells(SRC)}
    assert "NS.ZeroPay" in shells and "NS.Genus" in shells, ("def/abbrev constant shells must be flagged", shells)
    assert not any(k in shells for k in ("NS.AbsolutePriority", "NS.ClaimSchedule", "NS.Conc")) \
        and not any("Inhabited" in s or "instance" in s for s in shells), ("concept/structure/instance NOT shells", shells)
    # the GATE and the VOCAB agree by construction: the same shells the gate flags are the ones vocab drops, and
    # the concept defs the gate keeps are the ones vocab surfaces — no name-matching, so no namespace band-aid.
    vocab = autoformalize._substrate_established_defs(SRC)
    assert "AbsolutePriority" in vocab and "ClaimSchedule" in vocab and "Conc" in vocab
    assert "ZeroPay" not in vocab and "def Genus" not in vocab and "Genus : Prop" not in vocab


def test_faithfulness_reference_consults_single_refutation_ledger():
    """Single-LEDGER supersession (2026-06-23 — operator: false-negative + single entry point + NO parallel
    surface). A WEAK rendering can be faithful-to-NL yet FALSE → admitted + deposited as the store reference → it
    then wrongly gates the corrected STRONG rendering via the structural silent-weakening guard (the false-
    negative). Fix WITHOUT a parallel surface: the kernel ¬G is recorded to the EXISTING refutation ledger
    (`NoGoodStore`, failure class `statement_false`, canonical statement key); `FaithfulnessStore.reference()`
    CONSULTS that one ledger and drops the refuted rendering. Anti-gaming: recording requires the kernel ¬G;
    consulting only ever DROPS a gate-reference, never admits."""
    import tempfile
    from pathlib import Path
    from ztare.leanmill.solver.faithfulness_store import FaithfulnessStore
    from ztare.leanmill.solver.no_good_store import NoGoodStore
    # (a) NO parallel surface: the faithfulness store has NO own refutation recorder — refutations live in ONE ledger
    assert not hasattr(FaithfulnessStore, "mark_refuted"), \
        "refutations must route through the ONE ledger (NoGoodStore), not a parallel FaithfulnessStore.mark_refuted"
    with tempfile.TemporaryDirectory() as d:
        dd = Path(d)
        fs = FaithfulnessStore(dd / "solver_lane_faithfulness_store.jsonl")
        NL = "f single-crossing implies the argmax set is monotone"
        WEAK = "theorem t (h : SC f) : Mono := by sorry"
        fs.record(NL, WEAK, confirmed=True, fingerprint={"n_explicit_binders": 1}, source="firewall")
        assert (fs.reference(NL) or {}).get("statement") == WEAK     # weak is the reference (faithful-but-false)
        # the kernel ¬G is recorded to the ONE ledger (same dir, canonical key) — not a parallel store
        ng = NoGoodStore(dd / "solver_lane_no_good_store.jsonl")
        ng.record(WEAK, "statement_false", "cex: ties at the high parameter", confirmed=True)
        assert WEAK and ng.statement_false_keys(), "NoGoodStore must expose the statement_false keys for the consult"
        fs2 = FaithfulnessStore(dd / "solver_lane_faithfulness_store.jsonl")   # fresh instance (drops the cache)
        assert fs2.reference(NL) is None, "reference() must DROP a rendering the ONE ledger marked statement_false"


def test_disclosed_strengthening_override_is_non_gamable():
    """Disclosed-strengthening override (refute-and-correct, 2026-06-23) — the firewall admits a round-trip-
    REJECTED strengthening ONLY when the literal NL is kernel-FALSE (¬G license). NON-GAMABLE: it ADMITS the
    legit licensed strengthening but REJECTS every laundering case — weakened conclusion, non-strengthening,
    vacuous, trivial/goal-as-hyp, and (default) no-license. A SIBLING of the prior_confirmed round-trip bypass;
    fail-closed; reuses the ONE refutation ledger + the firewall's own non_vacuous/non_trivial legs + the
    existing fingerprint parser (no parallel surface). This is the soundness-boundary regression guard."""
    import tempfile
    from pathlib import Path
    from ztare.leanmill.solver import autoformalize as A, solver_core, faithfulness_store as FS, no_good_store as NG
    _save = solver_core.OUT_DIR
    try:
        with tempfile.TemporaryDirectory() as d:
            dd = Path(d); solver_core.OUT_DIR = dd
            NL = "single-crossing implies monotone"
            WEAK = "theorem t (h1 : A) : B ∧ C := by sorry"
            STRONG = "theorem t (h1 : A) (h2 : D) : B ∧ C := by sorry"
            WEAKENED = "theorem t (h1 : A) (h2 : D) : B ∨ C := by sorry"
            FS.FaithfulnessStore(dd / "solver_lane_faithfulness_store.jsonl").record(
                NL, WEAK, confirmed=True, fingerprint=A._parse_lean_statement(WEAK))
            NG.NoGoodStore(dd / "solver_lane_no_good_store.jsonl").record(WEAK, "statement_false", "cex", confirmed=True)
            ok = {"non_vacuous": True, "non_trivial": True}
            assert A._licensed_strengthening_admit(NL, STRONG, ok), "must ADMIT a licensed strengthening"
            assert A._licensed_strengthening_admit(NL, WEAKENED, ok) is None, "REJECT a weakened conclusion"
            assert A._licensed_strengthening_admit(NL, WEAK, ok) is None, "REJECT a non-strengthening (no added hyp)"
            assert A._licensed_strengthening_admit(NL, STRONG, {"non_vacuous": False, "non_trivial": True}) is None, "REJECT vacuous"
            assert A._licensed_strengthening_admit(NL, STRONG, {"non_vacuous": True, "non_trivial": False}) is None, "REJECT trivial/goal-as-hyp"
            assert A._licensed_strengthening_admit("unrelated claim", STRONG, ok) is None, "REJECT without the ¬G license"
            # GATE2 PRODUCTION-WIRING regression (2026-06-23): the production `autoformalize_and_solve` path supplies
            # NO consistency_fn, so `non_vacuous` is ABSENT (not True) — the gate must NOT require it (else the
            # override is DEAD e2e). It MUST require `non_trivial` (always populated; subsumes the vacuity probe) and
            # still reject an EXPLICIT consistency failure when one is supplied.
            assert A._licensed_strengthening_admit(NL, STRONG, {"non_trivial": True}), \
                "must ADMIT on the production signal set (non_trivial only; non_vacuous absent) — else override is dead"
            assert A._licensed_strengthening_admit(NL, STRONG, {"non_trivial": True, "non_vacuous": False}) is None, \
                "must still REJECT when a SUPPLIED consistency leg found a contradiction (non_vacuous False)"
            assert A._licensed_strengthening_admit(NL, STRONG, {"non_trivial": False}) is None, \
                "must REJECT a trivial/vacuous strengthening (non_trivial False subsumes the cheap-vacuity + instance probe)"
    finally:
        solver_core.OUT_DIR = _save


def test_literal_first_recovery_closes_the_loop_end_to_end(monkeypatch):
    """LITERAL-FIRST RECOVERY e2e (2026-06-23) — the INTEGRATION close, not a unit. The prior session built each
    component sound IN ISOLATION (firewall faithful-to-literal, FALSIFY election, the ONE statement_false ledger,
    the reformulation re-entry, the disclosed-strengthening override), but the firewall-REJECT path DEAD-ENDED: a
    substrate-primed agent that formalizes the STRENGTHENED claim directly is rejected as round-trip-weakened, no ¬G
    license is ever minted, and the override has nothing to act on (diagnosis: integration/sequencing, NOT iatrogenic
    harness). This drives the WHOLE pipeline through injected mocks (no LLM / no kernel / no tokens) and asserts the
    loop CLOSES: reject(strong) → literal-first re-entry → admit(literal) → kernel-refute(literal) → mint license in
    the ONE ledger → reformulation re-strengthens → override admits(strong) → close. Plus the NON-GAMABLE dual: NO
    kernel ¬G ⇒ NO license ⇒ NO override admit (the strengthening is never laundered)."""
    import tempfile
    from pathlib import Path
    from ztare.leanmill.solver import autoformalize as A, solver_core, no_good_store as NG
    # deterministic + infra-free: disable multistep escalation (would dispatch a real formalizer); loop legs ON.
    for k, v in {"ZTARE_LEANMILL_MULTISTEP_ESCALATE": "0", "ZTARE_LEANMILL_LITERAL_FIRST_RECOVERY": "1",
                 "ZTARE_LEANMILL_DISCLOSED_STRENGTHENING": "1", "ZTARE_LEANMILL_REFORMULATE": "1",
                 "ZTARE_LEANMILL_REFORMULATE_ROUNDS": "1", "ZTARE_LEANMILL_FAITHFULNESS_STORE": "1"}.items():
        monkeypatch.setenv(k, v)
    # PRODUCTION-SHAPE fixture (2026-06-23 uplevel): a MULTI-DECL `define_then_state` blob (defs THEN the target
    # theorem) — the real autoformalizer output shape that HID GATE2 (non_vacuous) + GATE3 (wrong-decl fingerprint).
    # The correction is a weak→strict DEF-SWAP on a hypothesis (SAME binder arity), which the old "more binders"
    # GATE3 + whole-blob `_parse_lean_statement` BOTH missed. A single-decl toy would NOT exercise either bug.
    NL = "single-crossing complementarity implies existence and strong-set monotonicity"
    DEFS = ("def WeakSC {X : Type*} [Preorder X] (f : X → X) : Prop := ∀ x, True\n"
            "def StrongSC {X : Type*} [Preorder X] (f : X → X) : Prop := ∀ x, True\n"
            "def Concl {X : Type*} [Preorder X] (f : X → X) : Prop := ∀ x, True\n")
    WEAK   = DEFS + "theorem tgt {X : Type*} [Preorder X] (f : X → X) (h : WeakSC f) : Concl f := by sorry"
    STRONG = DEFS + "theorem tgt {X : Type*} [Preorder X] (f : X → X) (h : StrongSC f) : Concl f := by sorry"

    def make_mocks(literal_refutable: bool):
        calls: list = []
        def formalize_fn(_nl):
            calls.append(_nl)
            # call 0: top pass-1 → STRONG (the over-strengthen); 1: literal-first re-entry → WEAK; 2: reformulation → STRONG
            return [STRONG, WEAK, STRONG][min(len(calls) - 1, 2)]
        # distinguish by the THEOREM's HYPOTHESIS binder, not the substring "StrongSC" — the DEFS block defines BOTH
        # WeakSC and StrongSC, so a substring check matches the literal too (the real LLM reads the actual theorem).
        backtranslate_fn = lambda s: ("strong corrected nl" if "(h : StrongSC f)" in s else "weak literal nl")
        judge_fn = lambda nl, back: "weak" in back              # round-trip ACCEPTS the literal, REJECTS the strong
        def solve_fn(name, stmt):
            if "(h : StrongSC f)" in stmt:                      # the corrected (def-swapped) theorem → closes
                return {"results": [{"outcome": "closed"}], "governance": {"ratified": 1}}
            if literal_refutable:                               # the WEAK literal → kernel ¬G (agent elected FALSIFY)
                return {"results": [{"outcome": "falsified", "falsifier": "cex: ties at the high parameter"}]}
            return {"results": [{"outcome": "open"}]}            # could not establish ⇒ NO license minted
        return formalize_fn, (lambda s: True), (lambda s: False), backtranslate_fn, judge_fn, solve_fn

    # (1) POSITIVE — the literal IS kernel-refutable ⇒ the loop closes the corrected theorem via the override
    with tempfile.TemporaryDirectory() as d:
        dd = Path(d); monkeypatch.setattr(solver_core, "OUT_DIR", dd)
        f, c, t, b, j, s = make_mocks(literal_refutable=True)
        out = A.autoformalize_and_solve(NL, sandbox=dd, formalize_fn=f, compile_fn=c, triviality_fn=t,
                                        backtranslate_fn=b, judge_fn=j, solve_fn=s, structural_fn=None, max_refines=0)
        assert out.get("faithful") is True and out.get("solved") == "closed", \
            f"recovery must CLOSE the corrected theorem e2e, got faithful={out.get('faithful')} solved={out.get('solved')}"
        assert (out.get("faithfulness_checks") or {}).get("licensed_strengthening"), \
            "the corrected theorem must be admitted via the DISCLOSED-STRENGTHENING override (license minted by the recovery)"
        assert out.get("literal_first_recovery_from") == STRONG, \
            "the result must record it was recovered from the over-strengthened first formalization"
        assert NG.NoGoodStore(dd / "solver_lane_no_good_store.jsonl").statement_false_keys(), \
            "the kernel ¬G of the literal must be recorded as statement_false in the ONE ledger (the license)"

    # (2) NON-GAMABLE — the literal is NOT refutable ⇒ NO license ⇒ the strengthening is NOT laundered
    with tempfile.TemporaryDirectory() as d:
        dd = Path(d); monkeypatch.setattr(solver_core, "OUT_DIR", dd)
        f, c, t, b, j, s = make_mocks(literal_refutable=False)
        out = A.autoformalize_and_solve(NL, sandbox=dd, formalize_fn=f, compile_fn=c, triviality_fn=t,
                                        backtranslate_fn=b, judge_fn=j, solve_fn=s, structural_fn=None, max_refines=0)
        assert not (out.get("faithful") is True and out.get("solved") == "closed"), \
            "with NO kernel ¬G the over-strengthened theorem must NOT be admitted+closed (no laundering)"
        assert not (out.get("faithfulness_checks") or {}).get("licensed_strengthening"), \
            "no license ⇒ the disclosed-strengthening override must NOT fire"
        assert not NG.NoGoodStore(dd / "solver_lane_no_good_store.jsonl").statement_false_keys(), \
            "no kernel ¬G ⇒ nothing recorded statement_false (no fabricated license)"


def test_reformulation_refine_hint_does_not_fight_strengthening():
    """REFINE↔REFORMULATE conflict fix (2026-06-23). Inside a reformulation re-entry the literal was kernel-REFUTED,
    so a round-trip mismatch on the CORRECTION is EXPECTED — but the generic refine hint said 'neither weaker nor
    stronger', which pushed the agent to re-emit the refuted reading (the prior run unfolded instead of strengthened).
    `strengthening_mode` flips the round-trip guidance; the reformulation re-entry sets `_strengthening_mode=True`."""
    from ztare.leanmill.solver import autoformalize as A
    class _V:  # a round-trip-rejected verdict
        checks = {"compiles": True, "non_trivial": True, "round_trip_faithful": False}
        reason = "round-trip does NOT match the NL"
    rt = A._formalize_feedback_hint(_V(), "theorem t (h : Weak f) : G := by sorry")
    rt_str = A._formalize_feedback_hint(_V(), "theorem t (h : Weak f) : G := by sorry", strengthening_mode=True)
    assert "neither weaker nor stronger" in rt, "default round-trip hint preserved (faithfulness mode)"
    assert "neither weaker nor stronger" not in rt_str and "STRONGER" in rt_str and "refuted" in rt_str, \
        "strengthening_mode must NOT tell the agent to keep it un-strengthened — it must orient toward the corrected theorem"


def test_firewall_gates_validated_on_production_shape_not_toys():
    """UPLEVELED INVARIANT (2026-06-23) — the class-preventer for the recurring integration-seam bugs. ROOT of
    'why do we keep having bugs': the disclosed-strengthening override family (GATE2 last session, GATE3 this
    session) was unit-tested on SYNTHETIC inputs that do NOT match the REAL producer's output — GATE2 injected a
    `checks` key (`non_vacuous`) the production firewall wiring never populates; GATE3 used a SINGLE-decl toy while
    the autoformalizer emits MULTI-decl `define_then_state` blobs. Both slipped through because the fixture's
    PROVENANCE + SHAPE diverged from production. This guard mechanizes the invariant so the class fails CI:
      (1) STATEMENT FINGERPRINTING is on the canonical TARGET theorem, never the whole multi-decl blob;
      (2) a gate's required `checks` keys ⊆ the keys the PRODUCTION firewall wiring actually populates."""
    import tempfile
    from pathlib import Path
    from ztare.leanmill.solver import autoformalize as A, solver_core, faithfulness_store as FS, no_good_store as NG
    # production-shape multi-decl blob: a leading `def` THEN the target theorem (the autoformalizer's real output).
    DEFS = ("def WeakSC {X : Type*} [Preorder X] (f : X → X) : Prop := ∀ x, True\n"
            "def StrongSC {X : Type*} [Preorder X] (f : X → X) : Prop := ∀ x, True\n")
    LIT  = DEFS + "theorem tgt {X : Type*} [Preorder X] (f : X → X) (h : WeakSC f) : (∀ x : X, x ≤ x) := by sorry"
    CORR = DEFS + "theorem tgt {X : Type*} [Preorder X] (f : X → X) (h : StrongSC f) : (∀ x : X, x ≤ x) := by sorry"

    # (1) FINGERPRINT-THE-TARGET invariant — `_target_signature` returns the THEOREM signature, NOT the leading
    #     `def`; and the naive whole-blob `_parse_lean_statement` is demonstrably WRONG here (the GATE3 regression
    #     witness): it parses the first decl, so it cannot tell LIT from CORR (both → the def's fingerprint).
    sig_lit, sig_corr = A._target_signature(LIT), A._target_signature(CORR)
    assert "WeakSC f" in sig_lit and "def WeakSC" not in sig_lit and ":= ∀ x, True" not in sig_lit, \
        "_target_signature must extract the TARGET theorem's signature, not the leading def of a multi-decl blob"
    assert A._hypotheses_of(sig_lit) != A._hypotheses_of(sig_corr), \
        "the target-theorem hypotheses must distinguish the weak literal from the def-swapped correction"
    blob_lit, blob_corr = A._parse_lean_statement(LIT), A._parse_lean_statement(CORR)
    assert blob_lit == blob_corr, \
        "REGRESSION WITNESS: whole-blob _parse_lean_statement CANNOT tell the correction from the literal (it parses " \
        "the leading def) — exactly the GATE3 bug; any gate fingerprinting statements MUST use _target_signature"

    # (2) CHECKS-KEY PROVENANCE invariant — drive faithfulness_gate through the EXACT production fn-set that
    #     `autoformalize_and_solve` passes (compile/triviality/backtranslate/judge ONLY — no consistency_fn /
    #     battery_fn / crossvote_fn), on a round-trip-REJECTED candidate, and capture which `checks` keys it
    #     populates. Then assert the override admits using ONLY that production key-set — so no gate may require a
    #     key production never sets (the GATE2 bug: it required `non_vacuous`, never populated ⇒ override DEAD e2e).
    with tempfile.TemporaryDirectory() as d:
        dd = Path(d); solver_core.OUT_DIR = dd
        NL = "weak condition implies the conclusion"
        FS.FaithfulnessStore(dd / "solver_lane_faithfulness_store.jsonl").record(
            NL, LIT, confirmed=True, fingerprint=A._parse_lean_statement(LIT))
        NG.NoGoodStore(dd / "solver_lane_no_good_store.jsonl").record(LIT, "statement_false", "cex", confirmed=True)
        v = A.faithfulness_gate(NL, CORR, compile_fn=lambda s: True, triviality_fn=lambda s: False,
                                backtranslate_fn=lambda s: "a different, stronger claim",
                                judge_fn=lambda a, b: False)   # round-trip REJECTS (mirrors the real strengthened case)
        populated = set(v.checks.keys())
        assert "non_vacuous" not in populated, \
            "PROVENANCE: production wiring (no consistency_fn) must NOT populate non_vacuous — a gate requiring it is dead"
        assert "non_trivial" in populated, "production wiring DOES populate non_trivial (the load-bearing GATE2 signal)"
        # the override must ADMIT the real def-swap correction using ONLY the production-populated keys
        assert A._licensed_strengthening_admit(NL, CORR, {k: v.checks[k] for k in populated}), \
            "override must ADMIT the def-swap correction on the PRODUCTION key-set (else it is dead e2e — the GATE2 class)"
        assert v.accepted and v.checks.get("licensed_strengthening"), \
            "faithfulness_gate end-to-end must admit the correction via the override on production wiring"
        # and it still REJECTS a same-hypotheses re-statement (the prior run's non-correction) — no laundering
        assert A._licensed_strengthening_admit(NL, LIT, {k: v.checks[k] for k in populated}) is None, \
            "a same-hypotheses re-statement is NOT a correction — must be rejected even with the license"
    # the door itself targets the theorem of a multi-decl blob (else the whole consolidation is moot)
    DD = "def D {X:Type*}[Preorder X](f:X→X):Prop := ∀ x, True\n"
    fp_door = A.statement_fingerprint(DD + "theorem t {X:Type*}[Preorder X](f:X→X)(h:D f)(g:D f):(∀ x:X, x≤x) := by sorry")
    assert (fp_door.get("n_explicit_binders") or 0) >= 2, \
        "statement_fingerprint must count the TARGET theorem's binders (≥2), not the leading def's"


def test_default_triviality_risk_detector_targets_theorem_in_multidecl(monkeypatch):
    """Production formalizations often use define-then-state blobs. The cheap-tactic gate must run lexical risk
    detection on the target theorem signature, not the leading definition/abbrev; otherwise a useful theorem can
    be rejected because the detector inspected `abbrev Ledger ...` instead of `theorem target ...`."""
    from ztare.leanmill.solver import autoformalize as A
    from ztare.gates import v33_preflight_risk_detector as R

    seen = {}

    def fake_detect(sig):
        seen["sig"] = sig
        return {"vacuity_suspected": sig.lstrip().startswith(("def ", "abbrev ", "structure "))}

    def fail_compile_probe(body, *a, **k):
        raise AssertionError("multi-decl define-then-state triviality must not run the cold cheap-proof probe")

    monkeypatch.setattr(R, "detect_risks", fake_detect)
    monkeypatch.setattr(R, "_compile_probe", fail_compile_probe)
    monkeypatch.setattr(R, "nondegenerate_instance_probe", lambda *a, **k: {"vacuity_confirmed": False})

    stmt = (
        "abbrev Ledger (Account : Type u) : Type u := Account → Int\n"
        "def totalBalance {Account : Type u} [Fintype Account] (ledger : Ledger Account) : Int := "
        "Finset.univ.sum ledger\n"
        "theorem target {Account : Type u} [Fintype Account] (ledger : Ledger Account) : "
        "totalBalance ledger = totalBalance ledger := by sorry"
    )
    assert A.default_triviality(stmt, sandbox=".") is False
    assert "ledger : Ledger Account" in (seen.get("sig") or ""), seen
    assert "totalBalance ledger = totalBalance ledger" in (seen.get("sig") or ""), seen
    assert "abbrev Ledger" not in (seen.get("sig") or ""), "risk detector must not see the leading abbrev"
    assert "def totalBalance" not in (seen.get("sig") or ""), "risk detector must not see the leading def"


def test_default_triviality_single_theorem_uses_bounded_cheap_tactics(monkeypatch):
    from ztare.leanmill.solver import autoformalize as A
    from ztare.gates import v33_preflight_risk_detector as R

    seen = {}
    monkeypatch.setattr(R, "detect_risks", lambda sig: {"vacuity_suspected": False})
    monkeypatch.setattr(R, "nondegenerate_instance_probe", lambda *a, **k: {"vacuity_confirmed": False})

    def fake_compile_probe(body, *a, **k):
        seen["probe_body"] = body
        return False

    monkeypatch.setattr(R, "_compile_probe", fake_compile_probe)
    assert A.default_triviality("theorem target (n : Nat) : n = n := by sorry", sandbox=".") is False
    assert "aesop" not in (seen.get("probe_body") or ""), "the cheap-tactic probe must stay bounded; no aesop"


# ── METAMORPHIC guards (2026-06-25, the AMM vocab-orphan RCA) ─────────────────────────────────────────────
# The recurring class = a check correct for the SHAPE it was authored against, silently wrong on an
# equivalent RE-ENCODING (research_isomorphism named it: read the invariant, not the coordinate). The cure
# is a METAMORPHIC assertion: the output must be INVARIANT under a content-preserving transformation. These
# FAIL on the pre-fix code (so they are non-iatrogenic — they encode a real invariant, not a tautology).

def test_proven_shelf_invariant_under_namespace_wrap():
    """METAMORPHIC: the proven-shelf must surface the SAME theorems whether or not the theory is wrapped in
    `namespace N … end N`. The pre-2026-06-25 code re-extracted signatures by the decl_blocks-QUALIFIED name
    (`extract_signature(src, 'N.foo')`), which finds nothing in a source that writes `theorem foo` short →
    EMPTY shelf on every namespaced theory → the planner re-proved already-banked lemmas (the AMM
    ConstantProductPool→PoolState orphaning). Cure: render the signature from the BLOCK we already hold."""
    from ztare.leanmill.solver.autoformalize import _substrate_proven_shelf
    flat = ("import Mathlib\n\n"
            "theorem foo_lemma (n : Nat) : n + 0 = n := by simp\n\n"
            "theorem bar_lemma (n : Nat) : 0 + n = n := by simp\n")
    wrapped = ("import Mathlib\n\nnamespace Demo\n\n"
               "theorem foo_lemma (n : Nat) : n + 0 = n := by simp\n\n"
               "theorem bar_lemma (n : Nat) : 0 + n = n := by simp\n\nend Demo\n")
    sf, sw = _substrate_proven_shelf(flat), _substrate_proven_shelf(wrapped)
    assert "foo_lemma" in sf and "bar_lemma" in sf, "shelf must surface flat-file theorems"
    # the invariant: namespacing is a content-preserving re-encoding → identical theorems surfaced
    assert "foo_lemma" in sw and "bar_lemma" in sw, \
        "proven-shelf must be INVARIANT under namespace-wrap (pre-fix: returned EMPTY → re-proved banked lemmas)"


def test_proven_shelf_excludes_directly_sorried_but_keeps_comment_mentioning_sorry():
    """The 'proven' filter must key on the INVARIANT (a real `sorry` in the proof), not the PROXY
    (`"sorry" in block`, a substring that dropped a proven theorem whose COMMENT said 'sorry')."""
    from ztare.leanmill.solver.autoformalize import _substrate_proven_shelf
    src = ("import Mathlib\n\n"
           "-- this proof avoids sorry entirely\n"
           "theorem clean_one (n : Nat) : n + 0 = n := by simp\n\n"
           "theorem open_one (n : Nat) : n + 0 = n := by sorry\n")
    sh = _substrate_proven_shelf(src)
    assert "clean_one" in sh, "a proven theorem whose COMMENT mentions sorry must still surface (comment-robust)"
    assert "open_one" not in sh, "a genuinely sorried theorem must NOT surface as proven"


def test_theory_identity_guard_refuses_reset_with_prior_banked(monkeypatch, tmp_path):
    """A RESET substrate (no theorems) WITH prior banked facts must REFUSE to re-formalize from prose — the
    trigger that orphaned the AMM proofs in a new vocabulary. FAILS the pre-2026-06-25 code (which would
    dispatch the agent and rebuild fresh)."""
    import ztare.leanmill.solver.family_lemma_library as fll
    import ztare.leanmill.solver.autoformalize_notes as an
    monkeypatch.setattr(fll, "read_bank_events",
                        lambda *a, **k: [{"substrate": "t.lean", "name": "x",
                                          "decl_text": "theorem x : True := trivial"}])
    (tmp_path / "t.lean").write_text("import Mathlib\n")           # reset: no theorems
    r = an.theory_consolidation("## Theory file\nt.lean\n", "t.lean", lean_root=tmp_path,
                                dispatch=lambda *a, **k: None)
    assert r.get("theory_reset_detected") is True and r.get("ok") is False, \
        "reset+prior-banked must REFUSE re-formalization (theory-identity guard)"
    (tmp_path / "t.lean").write_text("import Mathlib\n\ntheorem a : True := trivial\n")  # established
    r2 = an.theory_consolidation("## Theory file\nt.lean\n", "t.lean", lean_root=tmp_path, dispatch=None)
    assert not r2.get("theory_reset_detected"), "an established theory (has theorems) must NOT trip the guard"


def test_forall_fronting_signature_accepted_env_free_but_weakening_rejected():
    """METAMORPHIC + soundness (2026-06-25, the AMM `reachable_pool_wellFormed` gap RCA): a faithful proof that
    states the SAME Pi type with ∀-FRONTED binders (`theorem t : ∀ (a)(b), C`) instead of named-before-colon
    (`theorem t (a)(b) : C`) MUST pass statement_integrity — and must do so ENV-FREE (no campaign env / kernel
    oracle). The pre-fix code only accepted it via the kernel type-equiv oracle, which needs the campaign env to
    resolve bespoke vocab; a single broken substrate decl made that env DEAD, so the oracle fell back to a
    Mathlib-only probe, failed `unknown identifier`, and FALSE-REJECTED a CORRECT proof as
    `target_signature_altered` (the whole reason lemma 1 gapped after closing 15/15 the day before). Binder
    placement is a purely syntactic env-free equivalence; `pi_normalized_signature` normalizes it. SOUNDNESS: a
    real weakening (dropped hyp / altered conclusion) MUST still be rejected env-free (the normalizer is
    upgrade-only, never admits a different type)."""
    from ztare.leanmill.solver.statement_integrity import check
    from ztare.leanmill.lean_source import pi_normalized_signature as pin, extract_signature as es
    base    = "theorem t (a : Nat) (b : Nat) (h : a = b) : a + 0 = b := by sorry"
    fronted = "theorem t : ∀ (a : Nat) (b : Nat) (h : a = b), a + 0 = b := by sorry"   # SAME Pi type
    dropped = "theorem t (a : Nat) (b : Nat) : a + 0 = b := by sorry"                  # weakening (dropped hyp)
    altered = "theorem t (a : Nat) (b : Nat) (h : a = b) : a + 1 = b := by sorry"      # altered conclusion
    # the metamorphic invariant: the normalizer makes ∀-fronting a fixed point of the comparison
    assert pin(es(base, "t")) == pin(es(fronted, "t")), "∀-fronting must normalize to the SAME signature"
    assert pin(es(base, "t")) != pin(es(dropped, "t")), "a dropped hypothesis must NOT normalize equal"
    assert pin(es(base, "t")) != pin(es(altered, "t")), "an altered conclusion must NOT normalize equal"
    # ENV-FREE integrity (lean_root=None ⇒ NO kernel oracle): accept the reformulation, reject the weakenings
    assert check(base, fronted, "t").violations == [], \
        "∀-fronted reformulation must pass integrity env-free (no dead-env false-reject of a correct proof)"
    assert any("target_signature_altered" in v for v in check(base, dropped, "t").violations), \
        "a dropped-hypothesis weakening must STILL be rejected env-free (soundness, not just brittleness)"
    assert any("target_signature_altered" in v for v in check(base, altered, "t").violations), \
        "an altered-conclusion weakening must STILL be rejected env-free"


def test_env_provided_substrate_decl_not_flagged_deleted(tmp_path, monkeypatch):
    """A cache-cite / warm-env proof legitimately OMITS the campaign substrate's defs from its probe (they are
    resolved in the pre-elaborated env, not re-inlined). statement_integrity's text-only `deleted: original decl
    missing` check must NOT flag a decl that lives in the REGISTERED substrate as a laundering deletion — that
    false-reject rejected the AMM headline target (`no_history_enables_round_trip_arbitrage`) even though its math
    was already banked+ratified (2026-06-25 RCA, the env-based-cite sibling of the ∀-fronting false-reject).
    SOUND: a decl that is NEITHER inlined NOR in the substrate is still flagged `deleted`; a redefinition (present
    but divergent) still trips `definition_altered`."""
    import ztare.formal.repl_compile as rc
    from ztare.leanmill.solver.statement_integrity import check
    sub = tmp_path / "substrate.lean"
    sub.write_text("import Mathlib\nstructure Pool where x : Nat\ndef WF (p : Pool) : Prop := True\n", encoding="utf-8")
    monkeypatch.setattr(rc, "_CAMPAIGN_SUBSTRATE", str(sub), raising=False)
    rc.set_campaign_substrate(str(sub))
    orig = ("structure Pool where x : Nat\ndef WF (p : Pool) : Prop := True\ndef LocalHelper : Nat := 0\n"
            "theorem t (p : Pool) : WF p := by sorry")
    probe = "theorem t (p : Pool) : WF p := by trivial"   # env-based cite: defs NOT inlined
    v = check(orig, probe, "t")
    assert not any("Pool" in x or "`WF`" in x for x in v.violations), \
        f"substrate-provided defs (Pool/WF) must NOT be flagged deleted (env-provided), got {v.violations}"
    assert any("LocalHelper" in x for x in v.violations), \
        "a decl that is NEITHER inlined NOR in the substrate MUST still be flagged deleted (soundness)"
    # parity: with NO substrate registered, the strict text check stands (all omitted decls flagged)
    rc.set_campaign_substrate(None)
    v2 = check(orig, probe, "t")
    assert any("Pool" in x for x in v2.violations) and any("LocalHelper" in x for x in v2.violations), \
        "with no substrate registered the strict deleted-check must flag every omitted decl (byte-parity)"


def test_supersede_preserves_structure_after_target():
    """Banking a mid-file lemma must NOT delete a `structure`/`class`/`inductive` that sits between it and the
    next `def`. RCA 2026-07-01 (VCG DSIC): `_DECL_START` matched lemma/theorem/def/abbrev/instance but NOT
    structure/class/inductive, so `_supersede_in_place` bounded the superseded target's span by the next
    RECOGNIZED start (a later `def`), swallowing an intervening `structure` into the span → it was DELETED on
    splice → the substrate stopped compiling → reverted_noncompile (a valid, ratified proof lost + the campaign
    env went dead). Latent until VCG banked lemma 1 with its multi-unit-witness `structure` right after it (prior
    campaigns banked the last decl, nothing after to eat). The fix adds all named decl kinds to `_DECL_START`."""
    from ztare.leanmill.solver.family_lemma_library import _supersede_in_place, decl_names
    text = ("namespace VCG\n\ntheorem T (n : Nat) : True := by sorry\n\n"
            "structure S (K : Type*) where\n  a : K\n\n"
            "inductive I where | c\n\nclass C (K : Type*) where d : K\n\n"
            "def useS {K} (s : S K) : K := s.a\n\nend VCG\n")
    new_text, banked = _supersede_in_place(text, "T", "theorem T (n : Nat) : True := by trivial")
    assert new_text is not None, "supersession should locate the target span"
    for keep in ("structure S", "inductive I", "class C", "def useS"):
        assert keep in new_text, f"supersession DELETED `{keep}` between the target and the next def — span over-extended"
    assert "by trivial" in new_text and new_text.count("sorry") == 0, "target's sorry should be replaced by the proof"
    # the boundary regex must also let decl_names SEE the non-def kinds (else banking dedup mis-treats them as new)
    names = decl_names(text)
    assert {"S", "I", "C", "useS"} <= names, f"decl_names must recognize structure/inductive/class, got {names}"


def test_decl_span_parser_recognizes_every_canonical_kind():
    """Anti-DRIFT guard for the RCA-2026-07-01 class. The banking span parser (`family_lemma_library._DECL_START`)
    is a SIBLING of the canonical `lean_source` decl recogniser; when it recognises FEWER named decl kinds than
    the canonical one, it over-extends a superseded decl's span and DELETES the unrecognised decl on splice (the
    VCG `structure`-eating corruption). This guard fails the moment the two drift: every NAMED top-level decl kind
    `lean_source` recognises must also be a boundary the banking parser recognises. (Anonymous `example` is
    excluded — it has no name and is never a banked rung.)"""
    from ztare.leanmill.solver import family_lemma_library as fll
    from ztare.leanmill import lean_source as ls
    # CONSOLIDATED (2026-07-01): the banking span parser is now the CANONICAL `lean_source` parser (re-export),
    # not a sibling — so drift is structurally impossible. Assert the identity so no one re-forks it.
    assert fll._DECL_START is ls.DECL_START, "banking parser must BE lean_source.DECL_START (no re-forked sibling)"
    assert fll.decl_blocks is ls.decl_blocks, "banking decl_blocks must BE the canonical lean_source.decl_blocks"
    canonical_named_kinds = ["theorem", "lemma", "def", "abbrev", "instance",
                             "structure", "class", "inductive", "opaque", "axiom"]
    missed = [k for k in canonical_named_kinds if not ls.DECL_START.match(f"{k} Foo : T := t")]
    assert not missed, (f"lean_source.DECL_START misses {missed} — a decl of that kind between a banked target and "
                        f"the next recognised decl is SWALLOWED + deleted on bank-splice (RCA 2026-07-01).")
    # anonymous `example` is a span BOUNDARY (name '') but never a named/bankable decl
    blks = ls.decl_blocks("theorem A : T := t\nexample : T := t\ntheorem B : T := t\n")
    assert [n for n, _ in blks] == ["A", "", "B"], f"example must be a boundary with empty name, got {blks}"


def test_banked_lemma_reuse_skips_already_proven(tmp_path, monkeypatch):
    """(b) BANKED-DECL REUSE (2026-06-25, operator "don't re-formalize, reuse"): a lemma whose `**(name)**` names
    an ALREADY-proven (sorry-free) substrate decl is REUSED (returns its banked signature ⇒ campaign skips the
    re-formalize+attack), while a sorried decl or an unbanked name is NOT (returns None ⇒ normal attack). This is
    the prevention for re-formalization WASTE + the vocab-drift that orphans the shelf. NO regex: decl names come
    from the canonical lean parser (`decl_blocks`); the bullet→decl link is a substring test on the real names."""
    import ztare.formal.repl_compile as rc
    from ztare.leanmill.solver.autoformalize_notes import _banked_lemma_reuse
    sub = tmp_path / "substrate.lean"
    sub.write_text("import Mathlib\n"
                   "def some_def (n : Nat) : Nat := n\n"
                   "theorem proven_lemma (n : Nat) : n + 0 = n := by simp\n"
                   "theorem open_lemma (n : Nat) : 0 + n = n := by sorry\n", encoding="utf-8")
    monkeypatch.setattr(rc, "_CAMPAIGN_SUBSTRATE", str(sub), raising=False)
    rc.set_campaign_substrate(str(sub))
    reused_paren = _banked_lemma_reuse("**(proven_lemma)** the foundational fact", str(tmp_path))
    assert reused_paren and reused_paren.startswith("theorem proven_lemma "), \
        "a bullet naming a PROVEN sorry-free banked decl must be REUSED (skip re-formalize)"
    reused_code = _banked_lemma_reuse("`proven_lemma`: the same fact in blueprint-code style", str(tmp_path))
    assert reused_code and reused_code.startswith("theorem proven_lemma "), \
        "a backtick-named blueprint bullet must reuse the existing proven decl"
    reused_colon = _banked_lemma_reuse("proven_lemma: the same fact in compact queue style", str(tmp_path))
    assert reused_colon and reused_colon.startswith("theorem proven_lemma "), \
        "a colon-named blueprint bullet must reuse the existing proven decl"
    assert _banked_lemma_reuse("`some_def`: looks like a lemma bullet but names a definition", str(tmp_path)) is None
    assert _banked_lemma_reuse("**(open_lemma)** still has a hole", str(tmp_path)) is None, \
        "a bullet naming a SORRIED decl must NOT be reused (it isn't proven)"
    assert _banked_lemma_reuse("**(nonexistent_decl)** not banked", str(tmp_path)) is None, \
        "a bullet naming an unbanked decl must fall through to the normal attack"
    rc.set_campaign_substrate(None)
    assert _banked_lemma_reuse("**(proven_lemma)** x", str(tmp_path)) is None, \
        "no registered substrate ⇒ no reuse (byte-parity with the pre-(b) behavior)"


def test_graph_expansion_rerank_surfaces_seed_neighbour(monkeypatch):
    """Graph-expansion premise re-rank (2026-06-30, MEASURED lift): a candidate that is a dependency-neighbour
    of the top cosine SEEDS gets a co-occurrence boost (`cosine + α·log1p(#seed-neighbours)`), so a true premise
    that cosine ranked just-too-low is surfaced. Inductive Mathlib A/B: recall@10 0.225→0.266, @20 0.270→0.360,
    @50 0.330→0.491. RETRIEVAL only (reorders the same atlas candidates; the kernel still ratifies). Hermetic:
    a synthetic adjacency + scored list. Flag-off and empty-adjacency are byte-parity no-ops (soundness: it can
    never inject an un-embedded name, only reorder)."""
    import ztare.research_director.mathlib_semantic as ms
    rows = [{"name": "seedA"}, {"name": "seedB"}, {"name": "midC"}, {"name": "farX"}]
    scored = [(0.90, 0), (0.85, 1), (0.60, 2), (0.50, 3)]   # farX is LAST by raw cosine
    # farX is a dep-neighbour of BOTH top seeds → boosted above midC
    monkeypatch.setitem(ms._ADJ_CACHE, "adj", {"seedA": ["farX"], "seedB": ["farX"]})
    monkeypatch.setenv("ZTARE_LEANMILL_GRAPH_EXPAND", "1")
    out = [rows[i]["name"] for _c, i in ms._graph_expand_rerank(scored, rows)]
    assert out.index("farX") < out.index("midC"), \
        f"a seed-neighbour true-premise must be re-ranked above a non-neighbour it trailed on cosine, got {out}"
    assert out[0] == "seedA", "the boost must not displace a strictly-higher-cosine candidate the seeds don't point to"
    # flag OFF → unchanged (byte-parity)
    monkeypatch.setenv("ZTARE_LEANMILL_GRAPH_EXPAND", "0")
    assert ms._graph_expand_rerank(scored, rows) == scored, "flag-off must be a no-op"
    # empty adjacency → unchanged (fail-safe parity)
    monkeypatch.setenv("ZTARE_LEANMILL_GRAPH_EXPAND", "1")
    monkeypatch.setitem(ms._ADJ_CACHE, "adj", {})
    assert ms._graph_expand_rerank(scored, rows) == scored, "no adjacency artifact must be a no-op (cosine-only)"


def test_promote_reads_p0_sidecar(tmp_path):
    """P0 SINGLE-DOOR (2026-06-30): the honest persisted-world axioms + this-run banked/reused counts are STAMPED
    at campaign CLOSE (autoformalize_notes, warm env) beside the closure; promote_campaign_artifact READS that
    stamp instead of re-deriving P0 from the cold probe-world closure — which timed out (→ `axioms ?`), reported
    probe-world stub axioms, and whose log-regex missed intra-run banking (→ `reuse 0`). This is the recurring
    P0-at-promote bug closed at its root. Guards the read + the field contract so a rename on either side fails
    CI, not silently at promote time. Hermetic (no lake / no DB — bogus run_tag ⇒ graceful `—`)."""
    import importlib.util as _ilu
    import json
    from pathlib import Path
    _p = Path(__file__).resolve().parents[1] / "scripts/public/control/leanmill/promote_campaign_artifact.py"
    spec = _ilu.spec_from_file_location("promote_campaign_artifact", _p)
    pca = _ilu.module_from_spec(spec); spec.loader.exec_module(pca)

    closure = tmp_path / "vcg_demo.lean"
    closure.write_text("theorem vcg_demo : True := trivial\n", encoding="utf-8")
    (tmp_path / "vcg_demo.p0.json").write_text(json.dumps({
        "axioms": "propext, Classical.choice, Quot.sound",
        "composite_decl": "vcg_demo__abc123", "theory_file": "vcg.lean",
        "banked_this_run": 9, "reused_from_bank": 0,
    }), encoding="utf-8")
    hdr = pca.build_header("no_such_run", "vcg_demo", closure, None)  # stamp drives axioms + reuse
    assert "axioms propext, Classical.choice, Quot.sound" in hdr, f"stamped persisted-world axioms must win:\n{hdr}"
    assert "axioms ?" not in hdr, "must never fall back to the cold-probe `?` when a P0 stamp exists"
    assert "9 rung(s) banked this run" in hdr and "0 reused from prior bank" in hdr, \
        f"reuse must report the stamped intra-run banked count, not log-regex `cited 0`:\n{hdr}"

    # NO sidecar (pre-fix runs) ⇒ graceful fallback: still builds a header, never crashes. `axioms=` skips the
    # cold `lake env lean` so the test stays hermetic/fast.
    closure2 = tmp_path / "old_run.lean"
    closure2.write_text("theorem t : True := trivial\n", encoding="utf-8")
    hdr2 = pca.build_header("no_such_run", "old_run", closure2, None, axioms="n/a")
    assert "cited 0 banked rung(s)" in hdr2, "no-sidecar path must fall back to the log-regex reuse line"


def test_auto_promote_blocks_underdetermined_denotation_for_theory_campaign(monkeypatch):
    """A theorem can close while its introduced defs remain modeling-underdetermined. That should block only
    publish-review staging, not theorem closure."""
    from ztare.leanmill.solver import autoformalize_notes as notes

    monkeypatch.delenv("ZTARE_LEANMILL_ALLOW_UNPINNED_AUTO_PROMOTE", raising=False)
    res = {"target": {"solved": True}, "denotation": {
        "verdict": "UNDERDETERMINED",
        "reason": "under-determined def(s): ['proposalStep']",
    }}
    blockers = notes._auto_promote_blockers(res, "Demo.lean")
    assert blockers and "proposalStep" in blockers[0]


def test_auto_promote_allows_pinned_or_mathlib_only_denotation(monkeypatch):
    from ztare.leanmill.solver import autoformalize_notes as notes

    monkeypatch.delenv("ZTARE_LEANMILL_ALLOW_UNPINNED_AUTO_PROMOTE", raising=False)
    assert notes._auto_promote_blockers(
        {"denotation": {"verdict": "PINNED", "reason": "ok"}}, "Demo.lean") == []
    assert notes._auto_promote_blockers(
        {"denotation": {"verdict": "NOT_APPLICABLE", "reason": "Mathlib only"}}, "Demo.lean") == []


def test_promote_refuses_probe_stub_body(tmp_path, monkeypatch):
    """PUBLISH-BOUNDARY GUARD (2026-06-30 RCA): promote must REFUSE to file a probe-world standalone (cited rungs
    stubbed as local `axiom`s) or a body with a `sorry` under a clean-axioms header — that is the laundering-looking
    disconnect Gemini flagged on VCG (the first composite filed): the real substrate proof is axiom-clean but the
    portable standalone stubs its deps, so `#print axioms` on the FILE shows stubs and contradicts the header. A
    self-contained kernel-clean body (no local `axiom`, no `sorry`; `#print axioms` command is fine) must file."""
    import importlib.util as _ilu
    from pathlib import Path
    _p = Path(__file__).resolve().parents[1] / "scripts/public/control/leanmill/promote_campaign_artifact.py"
    spec = _ilu.spec_from_file_location("promote_campaign_artifact", _p)
    pca = _ilu.module_from_spec(spec); spec.loader.exec_module(pca)

    # probe-world stub body → REFUSED
    stub = ("import Mathlib\naxiom exists_welfareMaximizer : True\n"
            "theorem t : True := exists_welfareMaximizer\n")
    assert pca._laundering_markers(stub), "an `axiom` stub decl must be flagged"
    # a `sorry` body → REFUSED
    assert pca._laundering_markers("import Mathlib\ntheorem t : True := by sorry\n"), "a `sorry` must be flagged"
    # comment mentions are NOT hits (canonical comment-aware scan)
    assert not pca._laundering_markers("import Mathlib\n-- axiom foo, sorry later\ntheorem t: True := trivial\n"), \
        "a `sorry`/`axiom` inside a comment must NOT false-positive"
    # a self-contained clean body WITH a `#print axioms` verification line → allowed (not a decl)
    assert not pca._laundering_markers("import Mathlib\ntheorem t : True := trivial\n#print axioms t\n"), \
        "`#print axioms` is a command, not an `axiom` declaration — must not be flagged"


def test_sledgehammer_consensus_empty_trace_is_not_a_false_conflict():
    """Math x-substrate consensus signal (2026-06-30, live-validated). The consensus validates the Isabelle→Mathlib
    PREMISE MAPPING, so it is meaningful only with a NON-EMPTY dependency trace. An Isabelle proof by `simp` has an
    EMPTY trace (no premises) → the smuggle injects nothing (tactic='') → feeding `isabelle_found=True` there
    manufactured a false Isabelle-yes/Lean-no `faithfulness_conflict` (the bug: the call site used a key-presence /
    bool(proof) signal instead of bool(trace)). Empty trace ⇒ only the Lean verdict ⇒ INSUFFICIENT; a real trace
    that Lean reconstructs ⇒ CORROBORATED; a real trace Lean rejects ⇒ the valuable localized mapping conflict."""
    from ztare.leanmill.solver.sledgehammer import sledgehammer_consensus
    # empty trace (simp-proved or no-proof) → the caller passes isabelle_found=bool(trace)=False → INSUFFICIENT
    assert sledgehammer_consensus("n+0=n", isabelle_found=False, lean_compiles=False).status == "insufficient"
    assert sledgehammer_consensus("n+0=n", isabelle_found=False, lean_compiles=True).status == "insufficient"
    # non-empty trace + Lean reconstruction OK → corroborated (cross-kernel trust-lift)
    assert sledgehammer_consensus("a+b=b+a", isabelle_found=True, lean_compiles=True).status == "corroborated"
    # non-empty trace + Lean reconstruction fails → the localized Isabelle→Mathlib mapping-bug conflict
    assert sledgehammer_consensus("g", isabelle_found=True, lean_compiles=False).status == "faithfulness_conflict"


def test_strip_dead_sorried_orphans():
    """SUBSTRATE HYGIENE (2026-07-01): a sorried decl NOTHING references (dead scaffolding from a superseded stub —
    the VCG general witness vs its concrete `_closed`) is swept; a still-CITED sorry (a genuine open rung) is KEPT;
    surrounding decls + namespace structure survive. Uses the canonical `lean_source.decl_spans` for deletion."""
    from ztare.leanmill.solver.family_lemma_library import strip_dead_sorried_orphans
    src = (
        "namespace N\n"
        "theorem live_dep : True := trivial\n"
        "theorem dead_orphan : True := by\n  sorry\n"          # nothing references it → dead
        "theorem cited_open : True := by\n  sorry\n"           # referenced below → KEEP
        "def uses_it : True := cited_open\n"
        "structure S where\n  x : Nat\n"                       # must survive
        "end N\n")
    out, removed = strip_dead_sorried_orphans(src)
    assert removed == ["dead_orphan"], f"only the uncited sorry is dead, got {removed}"
    assert "dead_orphan" not in out, "dead orphan must be removed"
    assert "cited_open" in out and "def uses_it" in out, "a cited sorry (open rung) must be KEPT"
    assert "structure S where" in out and "namespace N" in out and "end N" in out, "structure/namespace must survive"
    # idempotent + no-op when clean
    assert strip_dead_sorried_orphans(out)[1] == [], "second pass removes nothing (idempotent)"
    assert strip_dead_sorried_orphans("theorem t : True := trivial\n")[1] == [], "no sorries → no-op"


def test_notation_command_is_span_boundary_not_swallowed():
    """DEF-NOTATION ANCHORING (2026-07-01, preventive — same span-swallow class as #51). A theory-building
    campaign may ANCHOR a bespoke `def` with custom `notation`/`macro`/`infixl`. Such a command between two decls
    must END the preceding decl's span (a COMMAND, not a bankable named decl) so supersession never absorbs +
    deletes it. Guards `lean_source.decl_spans`/`decl_blocks` treating the notation family as a terminator."""
    from ztare.leanmill import lean_source as ls
    src = ("def myOp (a b : Nat) : Nat := a + b\n"
           "notation:65 a \" ⊕ \" b => myOp a b\n"
           "theorem after_notation : True := trivial\n")
    spans = ls.decl_spans(src)
    names = [n for n, _i, _e in spans]
    assert names == ["myOp", "after_notation"], f"notation must not be a named decl, got {names}"
    myop_block = dict(ls.decl_blocks(src))["myOp"]
    assert "notation" not in myop_block, "the notation command must NOT be swallowed into myOp's span (would be deleted on splice)"
    for cmd in ("macro", "infixl", "attribute", "elab"):
        assert ls.DECL_TERMINATORS.match(f"{cmd} foo"), f"{cmd} must be a span terminator"


def test_all_decl_start_parsers_share_one_kind_list():
    """FULL PARSER CONSOLIDATION drift-guard (2026-07-01). Two decl-start regexes exist for two purposes — the
    banking span parser (`lean_source.DECL_START`, column-0, top-level) and the firewall parser
    (`statement_integrity._DECL_START`, indentation + namespace-qualified). Their SHAPES legitimately differ, but
    the KIND LIST must be ONE (`lean_source.DECL_KINDS`): a kind in one but not the other silently mis-bounds a
    span — the #51 structure-eating class. Assert every canonical kind is recognised by BOTH."""
    from ztare.leanmill import lean_source as ls
    from ztare.leanmill.solver import statement_integrity as si
    # NAMED kinds must be recognised by BOTH parsers (drift on these = the #51 span-swallow class).
    assert set(ls.NAMED_DECL_KINDS) == set(ls.DECL_KINDS) - {"example"}, "NAMED_DECL_KINDS = DECL_KINDS minus example"
    for kind in ls.NAMED_DECL_KINDS:
        probe = f"{kind} Foo : T := t"
        assert ls.DECL_START.match(probe), f"lean_source.DECL_START must recognise `{kind}`"
        assert si._DECL_START.match(probe), f"statement_integrity._DECL_START must recognise `{kind}` (kind drift → #51)"
    # `example` is BANKING-ONLY (span boundary); the firewall must NOT recognise it (its anonymous-name
    # comparison would false-flag a shifted/dropped example as `deleted`). Guard the deliberate asymmetry.
    assert ls.DECL_START.match("example : T := t"), "banking parser needs `example` as a span boundary"
    assert not si._DECL_START.match("example : T := t"), "firewall parser must NOT recognise `example` (false `deleted`)"


def test_oneshot_formalize_extract_does_not_span_theorems():
    """AUTOFORMALIZE oneshot extractor (2026-07-01 audit). `_extract_lean_from_dispatch(..., 'oneshot')` grabs the
    LAST `theorem|lemma … := (by) sorry`. Bug: the body `.*?` could cross a `theorem`/`lemma` keyword, so a
    `theorem helper … := by <proof>` FOLLOWED by `theorem target … := sorry` matched as ONE mangled blob (helper's
    name + target's sorry) → compile failure (fail-SAFE, but a wasted formalize round). The tempered bound keeps
    each match to a single decl. Fail-safe by design (a mis-extraction never becomes a closure — it fails to
    compile), so this guards the round-efficiency fix, not a soundness boundary."""
    from ztare.leanmill.solver.autoformalize import _extract_lean_from_dispatch as ex
    blob = "```lean\ntheorem helper : P := by\n  simp\ntheorem target : Q := by sorry\n```"
    assert ex(blob, "oneshot") == "theorem target : Q := by sorry", "must extract only the sorried target, not a mangle"
    # single theorem + indented output still handled (leniency preserved — not switched to column-0 decl_blocks)
    assert ex("```lean\ntheorem t : Q := by sorry\n```", "oneshot") == "theorem t : Q := by sorry"
    assert ex("```lean\n  theorem t : Q := sorry\n```", "oneshot").strip() == "theorem t : Q := sorry"


def test_campaign_cycle_time_splits_formalize_and_prove(tmp_path):
    """P0 TIMING SPLIT (2026-07-01 RCA — recurring under-report). The attempts ledger has no row before the SOLVE
    phase, so `closure − first_attempt` is only the PROVING window; measuring it AS time-to-closure drops the
    theory-consolidation + statement-formalize minutes (BFT read 207s vs the true ~804s). The fix uses the
    `campaign` marker (stamped at launch) so: time_to_formalize (launch→first attempt) + time_to_close (first
    attempt→closure) == wall (launch→closure). Guards that the split sums and that a MISSING marker falls back."""
    from ztare.leanmill import phase_timing as pt
    import json
    led = tmp_path / "ledger.jsonl"
    # campaign launched at epoch 1000; first solve attempt at 1600 (600s of formalize); closure at 1800 (200s prove)
    led.write_text(json.dumps({"kind": "phase_timing", "phase": "campaign", "duration_s": 0.0,
                               "run_tag": "camp", "tags": {"domain": "formalization-nonmath"}, "ts": "1000"}) + "\n",
                   encoding="utf-8")
    rows = [{"run_tag": "camp", "attempt_at": "1600", "outcome": "failed_compile", "wallclock_s": 10},
            {"run_tag": "camp", "attempt_at": "1800", "outcome": "closed", "wallclock_s": 20}]
    c = pt.summarize_campaign_cycle_time(rows, ledger=str(led))["campaigns"]["camp"]
    assert c["time_to_formalize_s"] == 600.0, c            # launch→first attempt
    assert c["time_to_close_s"]["first"] == 200.0, c       # first attempt→closure (proving)
    assert c["wall_s"]["first"] == 800.0, c                # launch→closure == formalize + prove
    assert c["time_to_closure_s"]["first"] == 200.0, c     # backward-compat alias == proving window
    assert abs(c["time_to_formalize_s"] + c["time_to_close_s"]["first"] - c["wall_s"]["first"]) < 0.01, "must sum"
    # NO marker (old run) → fall back to first-attempt start: formalize 0, wall == prove
    rows2 = [{"run_tag": "nomark", "attempt_at": "1600", "outcome": "closed", "wallclock_s": 5}]
    c2 = pt.summarize_campaign_cycle_time(rows2, ledger=str(led))["campaigns"]["nomark"]
    assert c2["time_to_formalize_s"] == 0.0 and c2["wall_s"]["first"] == 0.0, c2


def test_unified_instrument_liveness_battery(monkeypatch):
    """UNIFIED LIVENESS (2026-07-01). One run-start battery probes the ADVISORY external instruments whose silent
    death false-degrades/false-rejects — the semantic-shelf embedder AND the firewall round-trip judge (the latter
    was previously unprobed → the BFT false-reject). A dead instrument ⇒ LOUD banner (never a silent absence);
    injectable ⇒ hermetic. Guards both legs + the gate."""
    from ztare.leanmill.run_standards import run_instrument_liveness_battery as batt
    monkeypatch.setenv("ZTARE_LEANMILL_INSTRUMENT_LIVENESS", "1")
    # both LIVE (good embedder returns a vector; live backtranslate returns non-empty NL) → no banners
    ok = batt(embed_fn=lambda t: [0.1] * 768, atlas_nonempty=True, backtranslate_fn=lambda s: "for all n, n plus zero is n")
    assert ok["embedder"]["live"] and ok["roundtrip"]["live"] and not ok["banners"], ok
    # both DEAD (embedder None; backtranslate empty = dead judge) → two LOUD banners
    dead = batt(embed_fn=lambda t: None, atlas_nonempty=True, backtranslate_fn=lambda s: "")
    assert not dead["embedder"]["live"] and not dead["roundtrip"]["live"], dead
    assert len(dead["banners"]) == 2 and all("INADMISSIBLE" in b for b in dead["banners"]), dead
    # a raising backtranslate (crashed judge) is DEAD, not an exception that aborts the run
    d2 = batt(embed_fn=lambda t: [0.1] * 768, atlas_nonempty=True,
              backtranslate_fn=lambda s: (_ for _ in ()).throw(RuntimeError("quota")))
    assert d2["embedder"]["live"] and not d2["roundtrip"]["live"], d2
    # gate off → skipped
    monkeypatch.setenv("ZTARE_LEANMILL_INSTRUMENT_LIVENESS", "0")
    assert batt(embed_fn=lambda t: None)["skipped"] is True


def test_denotation_composition_anchor_pins_target_used_defs():
    """DENOTATION ANCHORING (2026-07-01). A built def used in a kernel-verified proof/STATEMENT is denotationally
    PINNED by that theorem (UC / composition anchor) — no separate anchor_ theorem needed. The UC scan's proof
    blob previously included only the sub-rung deep_closures, MISSING defs used only in the TARGET composite's
    statement (BFT's `ThresholdSafeAndAvailableBound`, used in the composite `iff`, was falsely UNDERDETERMINED;
    the fix adds the target composite to the blob). Guards the principle: a composed def is PINNED; an unanchored,
    uncomposed def stays UNDERDETERMINED (honest — genuinely unexercised)."""
    from ztare.leanmill.solver import def_denotation as dd
    src = ("namespace N\ndef UsedBound (n:Nat):Prop := n=n\ndef Orphan (n:Nat):Prop := n=n\n"
           "theorem t : True := trivial\nend N\n")
    r = dd.certify_def_denotation(src, verify_anchor_fn=lambda a: True, composed_defs={"UsedBound"})
    pd = r["per_def"]
    assert pd["UsedBound"]["status"] == "PINNED" and pd["UsedBound"]["composition_anchor"], pd
    assert pd["Orphan"]["status"] == "UNDERDETERMINED", pd   # not composed, no anchor → honest gap (correct)


def test_campaign_verify_strips_env_declared_decls_single_door():
    """Chronic 'already been declared' campaign-verify fix (2026-07-01; NOT a session regression — present since
    2026-06-08 across putnam/consc/topkis/apr, acute on def-heavy Shamir). A self-contained probe re-declares
    campaign DEFS + proven shelf lemmas already live in the warm campaign env ⇒ `X has already been declared` ⇒ a
    VALID proof never ratifies (thrash; native-only proofs escaped it). The SINGLE-DOOR strip
    (`lean_source.strip_env_declared_decls`, called inside `warm_verify_campaign` so ALL callers — leaf,
    conjecture/refute, solver_core — inherit it) drops env-dup DEFS (always) + PROVEN env theorems (safe to cite),
    and KEEPS the target, genuinely-new helpers, and SORRIED env theorems (dropping those ⇒ sorryAx). SOUND: env
    decls are canonical."""
    from ztare.leanmill.lean_source import strip_env_declared_decls
    env = ("import Mathlib\nnamespace X\n"
           "def Foo (n : Nat) : Nat := n + 1\n"
           "theorem proven_shelf (n : Nat) : Foo n = n + 1 := rfl\n"
           "theorem sorried_shelf (n : Nat) : Foo n = n + 1 := by sorry\n"
           "theorem target_thm (n : Nat) : Foo n = n + 1 := by sorry\n"
           "end X\n")
    probe = ("import Mathlib\nnamespace X\n"
             "def Foo (n : Nat) : Nat := n + 1\n"                                   # env DEF -> strip
             "def NewHelper (n : Nat) : Nat := n\n"                                 # new def -> keep
             "theorem proven_shelf (n : Nat) : Foo n = n + 1 := rfl\n"             # PROVEN env thm -> strip
             "theorem sorried_shelf (n : Nat) : Foo n = n + 1 := by simp [Foo]\n"  # SORRIED in env -> KEEP
             "theorem target_thm (n : Nat) : Foo n = n + 1 := by simp [Foo]\n")    # target -> keep
    out = strip_env_declared_decls(probe, env, keep="target_thm")
    assert "def Foo (n : Nat)" not in out, "env-dup def must be stripped"
    assert "def NewHelper" in out, "new (not-in-env) def must be kept"
    assert "theorem proven_shelf" not in out, "proven env theorem stripped (safe to cite the env copy)"
    assert "theorem sorried_shelf" in out, "SORRIED env theorem KEPT (dropping it => sorryAx on the cite)"
    assert "theorem target_thm" in out, "the target being proved must be kept"
    assert "import Mathlib" in out and "namespace X" in out, "prelude (imports/namespace) untouched"
    # COMPLETION of the cure: the target is SORRIED in the env, so a probe re-declaring it must be verified under a
    # FRESH name (the 'fresh decl name' contract; mirrors solver_core's _zwv) or it clashes with its own env copy.
    from ztare.leanmill.lean_source import rename_decl
    rn = rename_decl(probe, "target_thm", "target_thm_wv")
    assert "theorem target_thm_wv (n : Nat)" in rn, "target decl head renamed to a fresh name"
    assert "def Foo (n : Nat)" in rn, "rename_decl touches ONLY the named decl head (Foo untouched)"


def test_supersede_sorried_twins_folds_proven_twin_into_canonical():
    """Sorried-sibling dedup (2026-07-01): theory_consolidation's APPEND-ONLY gate forbids the agent editing
    `X := sorry`→proof, so it appends a proven twin `X_banked` and the canonical stays sorried (dup pairs
    accumulate; artifact won't file clean). The harness supersession folds each proven twin into its sorried
    canonical (`:= by exact <twin>` — a kernel-checkable cite of an identical-statement proof), leaving a
    no-twin canonical un-sorried and a no-twin sorried lemma alone. SOUND (only replaces a sorry with a cite)."""
    from ztare.leanmill.lean_source import supersede_sorried_twins
    theory = ("namespace X\n"
              "theorem foo (a : Nat) : a = a := by sorry\n"          # sorried canonical (has proven twin)
              "theorem foo_banked (b : Nat) : b = b := rfl\n"        # proven twin (same alpha-statement)
              "theorem bar : True := by sorry\n"                     # sorried, NO twin -> untouched
              "end X\n")
    out, rep = supersede_sorried_twins(theory)
    assert rep == [("foo", "foo_banked")], f"expected foo folded into foo_banked, got {rep}"
    assert "theorem foo (a : Nat) : a = a := by exact foo_banked" in out, "canonical folded to cite the proven twin"
    assert "theorem foo_banked" in out, "the proven twin is kept (canonical now cites it)"
    assert "theorem bar : True := by sorry" in out, "a sorried lemma with NO proven twin is left untouched"
    assert out.count("sorry") == 1, "only the twinned canonical is healed; the no-twin sorry remains"
