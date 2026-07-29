from __future__ import annotations

import inspect

import pytest

from ztare.leanmill.solver import solver_core


def test_axiom_output_requires_an_explicit_recognized_verdict() -> None:
    from ztare.formal.lean_axiom_audit import (
        axiom_output_recognized,
        parse_axioms,
    )

    no_axioms = "'Demo.target' does not depend on any axioms"
    some_axioms = "'Demo.target' depends on axioms: [propext, Quot.sound]"
    assert axiom_output_recognized(no_axioms)
    assert parse_axioms(no_axioms) == []
    assert axiom_output_recognized(some_axioms)
    assert parse_axioms(some_axioms) == ["Quot.sound", "propext"]
    assert not axiom_output_recognized("compiled with no diagnostics")


def test_axiom_subset_rejects_recognized_line_from_failed_compile(
    tmp_path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ztare.formal import repl_compile
    from ztare.gates import lean_compile_primitives

    monkeypatch.setattr(repl_compile, "axioms_raw_via_repl", lambda *_a, **_k: None)
    monkeypatch.setattr(
        lean_compile_primitives,
        "run_lake_compile",
        lambda *_a, **_k: {
            "ok": False,
            "returncode": 1,
            "axioms": {"Demo.target": []},
        },
    )

    assert lean_compile_primitives.audit_axioms_subset(
        "theorem target : True := by trivial",
        "Demo.target",
        tmp_path / "AxiomProbe.lean",
        tmp_path,
        timeout_s=1,
    ) == (False, False, [])


def test_axiom_subset_resolves_one_qualified_namespace_identity(
    tmp_path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ztare.formal import repl_compile
    from ztare.gates import lean_compile_primitives

    monkeypatch.setattr(repl_compile, "axioms_raw_via_repl", lambda *_a, **_k: None)
    monkeypatch.setattr(
        lean_compile_primitives,
        "run_lake_compile",
        lambda *_a, **_k: {
            "ok": True,
            "returncode": 0,
            "axioms": {"Demo.target": ["propext"]},
        },
    )

    assert lean_compile_primitives.audit_axioms_subset(
        "namespace Demo\ntheorem target : True := by trivial\nend Demo",
        "target",
        tmp_path / "AxiomProbe.lean",
        tmp_path,
        timeout_s=1,
    ) == (True, False, ["propext"])


def test_axiom_subset_keeps_ambiguous_qualified_names_inconclusive(
    tmp_path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ztare.formal import repl_compile
    from ztare.gates import lean_compile_primitives

    monkeypatch.setattr(repl_compile, "axioms_raw_via_repl", lambda *_a, **_k: None)
    monkeypatch.setattr(
        lean_compile_primitives,
        "run_lake_compile",
        lambda *_a, **_k: {
            "ok": True,
            "returncode": 0,
            "axioms": {"Left.target": [], "Right.target": []},
        },
    )

    assert lean_compile_primitives.audit_axioms_subset(
        "theorem target : True := by trivial",
        "target",
        tmp_path / "AxiomProbe.lean",
        tmp_path,
        timeout_s=1,
    ) == (False, False, [])


def test_gold_name_detector_counts_nested_support_as_composition() -> None:
    from ztare.gates.v33_paraphrase_gate import detect_gold_name_verbatim

    derived = """import Mathlib
theorem derived (a b c : Nat) (h : a ≤ b) : a ≤ b + c := by
  exact le_trans h <| Nat.le_add_right b c
"""
    receipt = detect_gold_name_verbatim(derived)

    assert receipt["supporting_cited_lemmas"] == ["Nat.le_add_right"]
    assert receipt["has_multistep_composition"] is True
    assert receipt["gold_name_verbatim_suspect"] is True
    assert receipt["trivial_restatement"] is False


def _contract() -> dict:
    return {
        "schema": "test.contract.v1",
        "required_receipts": [
            {"name": "kernel_compile_receipt", "required": True},
            {"name": "matched_negative_control_receipt", "required": True},
            {"name": "axiom_allowlist_receipt", "required": True},
            {"name": "l3_anti_pattern_receipt", "required": True},
        ],
    }


def _positive_target_governance() -> dict:
    from ztare.leanmill.ratification_policy import (
        TARGET_GOVERNANCE_AUTHORITIES,
        TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256,
    )

    return {
        "governance_kernel": {
            "available": True,
            "passed": True,
            "policy_profile": "target_ratification",
            "required_authorities": sorted(TARGET_GOVERNANCE_AUTHORITIES),
            "authority_disposition": {
                authority: "passed"
                for authority in TARGET_GOVERNANCE_AUTHORITIES
            },
            "authority_roster_sha256": (
                TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256
            ),
        },
        "statement_integrity": {"ok": True},
        "integrity_unverified": False,
    }


def test_ratification_forbids_provider_override_and_uses_inert_carrier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        solver_core,
        "_policy_model",
        lambda: (_ for _ in ()).throw(AssertionError("policy provider consulted")),
    )

    assert solver_core._adhoc_routing_provider(
        None, preverified_only=True
    ) == "placebo"
    for provider in ("native_hammer", "claude_opus", "placebo"):
        with pytest.raises(ValueError, match="forbids provider overrides"):
            solver_core._adhoc_routing_provider(
                provider, preverified_only=True
            )


def test_ratification_solver_contract_describes_source_aware_control(
    tmp_path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ztare.leanmill.solver import contract as solver_contract

    cue = {
        "source_cue_check_status": "passed",
        "source_cue_receipts": [],
        "missing_source_cues": [],
    }
    monkeypatch.setattr(solver_core, "_source_cue_check", lambda _row: cue)
    row = {
        "row_id": "ratify-target",
        "target_theorem_name": "Demo.target",
        "goal": ": True",
        "_preverified_only": True,
    }
    strict = solver_core._build_solver_action_contract(row, tmp_path)
    ordinary = solver_core._build_solver_action_contract(
        {**row, "_preverified_only": False}, tmp_path
    )
    canonical = solver_contract.build_solver_action_contract(
        row, tmp_path, tmp_path
    )

    def mnc_receipt(contract: dict) -> dict:
        return next(
            receipt
            for receipt in contract["required_receipts"]
            if receipt["name"] == "matched_negative_control_receipt"
        )

    strict_check = mnc_receipt(strict)["acceptance_check"]
    assert strict["ratification_only"] is True
    assert strict["scope"] == "carried_theorem_ratification"
    assert strict["requested_residual_class"] == "carried_theorem_ratification"
    assert strict["action_program"] == [
        "bind_exact_carried_artifact",
        "compile_exact_target",
        "run_source_aware_matched_control",
        "run_finite_ratification_authorities",
        "finalize_content_addressed_certificate",
    ]
    assert strict["rd_primitive_hits"] == []
    assert "native_hammer" not in strict["action_program"]
    assert not any("agent" in step for step in strict["action_program"])
    assert not any("provider" in step for step in strict["action_program"])
    assert strict["matched_negative_control_mode"] == (
        "source_aware_conclusion_perturbation"
    )
    assert "exact carried posed/closure source" in strict_check
    assert "replacing only C by ¬(C)" in strict_check
    assert "status=inconclusive does not satisfy ratification" in strict_check
    assert "bare `import Mathlib`" not in strict_check
    behavior = strict["reject_or_repair_behavior"]
    assert behavior["matched_negative_control_pass"].startswith("PROCEED")
    assert "zero differential" in behavior["matched_negative_control_fail"]
    assert "rejected_mnc_inconclusive" in behavior[
        "matched_negative_control_inconclusive"
    ]
    assert "status=pass" in strict["program_counter_rule"]

    # The public contract builder and the live embedded builder consume one
    # projection, so their ratification receipt semantics stay byte-identical.
    assert canonical["matched_negative_control_mode"] == strict[
        "matched_negative_control_mode"
    ]
    assert mnc_receipt(canonical)["acceptance_check"] == strict_check
    for key in (
        "matched_negative_control_pass",
        "matched_negative_control_fail",
        "matched_negative_control_inconclusive",
    ):
        assert canonical["reject_or_repair_behavior"][key] == behavior[key]

    # Ordinary search keeps its existing context-stripped contract.
    ordinary_check = mnc_receipt(ordinary)["acceptance_check"]
    assert ordinary["ratification_only"] is False
    assert ordinary["scope"] == "solver_lane_no_positive_family_template"
    assert ordinary["action_program"][0] == "layer2_native_hammer_cascade"
    assert ordinary["matched_negative_control_mode"] == "context_stripped"
    assert "bare `import Mathlib`" in ordinary_check
    assert ordinary["reject_or_repair_behavior"][
        "matched_negative_control_pass"
    ].startswith("REJECT closure as leakage")


def test_ratification_requires_positive_axiom_receipt(
    tmp_path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(solver_core, "OUT_DIR", tmp_path)
    monkeypatch.setattr(
        solver_core,
        "_verify_matched_negative_control",
        lambda *_args, **_kwargs: (True, "pass"),
    )
    monkeypatch.setattr(
        solver_core,
        "_campaign_aware_axioms",
        lambda *_args, **_kwargs: None,
    )

    from ztare.gates import lean_compile_primitives, lean_proof_gate

    monkeypatch.setattr(
        lean_proof_gate,
        "run_anti_laundering_kernel",
        lambda *_args, **_kwargs: {
            "available": True,
            "passed": True,
            "confirmed": [],
            "flags": [],
        },
    )
    monkeypatch.setattr(
        lean_compile_primitives,
        "audit_axioms_subset",
        lambda *_args, **_kwargs: (False, False, []),
    )

    common = dict(
        contract=_contract(),
        proof_text="by\n  trivial",
        enriched_goal="theorem target : True := by",
        target_name="target",
        lean_root=tmp_path,
        timeout_s=1,
        kernel_compile_ok=True,
        kernel_compile_tail="ok",
        goal_type=": True",
        closure_source="theorem target : True := by\n  trivial\n",
        posed_source="theorem target : True := by\n  sorry\n",
    )

    legacy = solver_core._validate_against_contract(**common)
    ratification = solver_core._validate_against_contract(
        **common, require_positive_axiom_receipt=True
    )

    assert legacy["credit_ready_at_solver_layer"] is True
    assert ratification["credit_ready_at_solver_layer"] is False
    assert ratification["positive_axiom_receipt_required"] is True
    assert ratification["receipts"]["axiom_allowlist_receipt"]["passed"] is None
    assert solver_core._reject_reason_from_validation(ratification)[0] == (
        "rejected_axiom_inconclusive"
    )


@pytest.mark.parametrize("failure_mode", ["exception", "diagnostic_disabled"])
def test_governance_unavailability_never_awards_solver_credit(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    failure_mode: str,
) -> None:
    from ztare.gates import lean_compile_primitives, lean_proof_gate

    monkeypatch.setattr(solver_core, "OUT_DIR", tmp_path)
    monkeypatch.setattr(
        solver_core,
        "_verify_matched_negative_control",
        lambda *_args, **_kwargs: (True, "pass"),
    )
    monkeypatch.setattr(solver_core, "_campaign_aware_axioms", lambda *_a, **_k: None)
    monkeypatch.setattr(
        lean_compile_primitives,
        "audit_axioms_subset",
        lambda *_args, **_kwargs: (True, False, []),
    )
    if failure_mode == "exception":
        def crash(*_args, **_kwargs) -> dict:
            raise RuntimeError("injected governance failure")

        monkeypatch.setattr(lean_proof_gate, "run_anti_laundering_kernel", crash)
    else:
        monkeypatch.setenv("ZTARE_KERNEL_AUTHORITATIVE", "0")

    validation = solver_core._validate_against_contract(
        contract=_contract(),
        proof_text="by\n  trivial",
        enriched_goal="theorem target : True := by",
        target_name="target",
        lean_root=tmp_path,
        timeout_s=1,
        kernel_compile_ok=True,
        kernel_compile_tail="ok",
        goal_type=": True",
        closure_source="theorem target : True := by\n  trivial\n",
        posed_source="theorem target : True := by\n  sorry\n",
        require_positive_axiom_receipt=True,
    )

    receipt = validation["receipts"]["governance_kernel_receipt"]
    assert receipt["passed"] is None
    assert receipt["status"] == "unavailable"
    assert validation["credit_ready_at_solver_layer"] is False
    assert validation["required_receipts_all_passed_at_solver_layer"] is False


@pytest.mark.parametrize("failure_mode", ["exception", "typed_unavailable"])
def test_falsifier_governance_unavailability_is_inconclusive(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
    failure_mode: str,
) -> None:
    from ztare.gates import lean_proof_gate

    if failure_mode == "exception":
        def kernel(*_args, **_kwargs) -> dict:
            raise RuntimeError("injected falsifier governance failure")
    else:
        def kernel(*_args, **_kwargs) -> dict:
            return {
                "available": False,
                "passed": False,
                "confirmed": [],
                "unavailable_organs": ["v33_paraphrase_gate"],
            }

    monkeypatch.setattr(lean_proof_gate, "run_anti_laundering_kernel", kernel)
    passed, detail = solver_core._govern_falsifier_source(
        "theorem candidate_refute : ¬ True := by contradiction",
        "",
        tmp_path,
        "candidate_refute",
    )

    assert passed is None
    assert detail.startswith("governance unavailable:")


def test_falsifier_governance_explicit_pass_is_accepted(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ztare.gates import lean_proof_gate

    monkeypatch.setattr(
        lean_proof_gate,
        "run_anti_laundering_kernel",
        lambda *_args, **_kwargs: {
            "available": True,
            "passed": True,
            "confirmed": [],
        },
    )
    passed, detail = solver_core._govern_falsifier_source(
        "theorem candidate_refute : ¬ True := by contradiction",
        "",
        tmp_path,
        "candidate_refute",
    )

    assert passed is True
    assert detail == "organs confirmed=[]"


def test_falsifier_governs_the_exact_host_owned_target(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ztare.gates import lean_proof_gate

    selected: list[str] = []

    def kernel(*_args, **kwargs) -> dict:
        selected.append(kwargs["target_name"])
        return {"available": True, "passed": True, "confirmed": []}

    monkeypatch.setattr(lean_proof_gate, "run_anti_laundering_kernel", kernel)
    source = """\
theorem agent_helper_refute : True := by trivial
theorem host_refute : True := by trivial
"""

    passed, _detail = solver_core._govern_falsifier_source(
        source,
        "",
        tmp_path,
        "host_refute",
    )

    assert passed is True
    assert selected == ["host_refute"]


def _composite_inputs() -> tuple[str, str, dict]:
    posed = "theorem goal (P : Prop) (h : P) : P := by sorry"
    closed = "theorem goal (P : Prop) (h : P) : P := by exact h"
    result = {"lemmas": [], "lnames": [], "chain": closed}
    return posed, closed, result


def _patch_composite_assembly(
    monkeypatch: pytest.MonkeyPatch,
    closed: str,
) -> None:
    from ztare.gates import v33_preflight_risk_detector
    from ztare.leanmill.solver import isomorphism_decompose

    monkeypatch.setattr(
        isomorphism_decompose,
        "deanchor",
        lambda *_args, **_kwargs: ("", "", "", []),
    )
    monkeypatch.setattr(
        isomorphism_decompose,
        "assemble_composite_proof",
        lambda *_args, **_kwargs: closed,
    )
    monkeypatch.setattr(
        v33_preflight_risk_detector,
        "_compile_probe",
        lambda *_args, **_kwargs: True,
    )


def test_composite_kernel_unavailability_cannot_close_parent(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ztare.gates import lean_proof_gate
    from ztare.leanmill.solver import isomorphism_decompose

    posed, closed, result = _composite_inputs()
    _patch_composite_assembly(monkeypatch, closed)
    monkeypatch.setattr(
        lean_proof_gate,
        "run_anti_laundering_kernel",
        lambda *_args, **_kwargs: {
            "available": False,
            "passed": True,
            "unavailable_organs": ["canonical_reelaboration"],
        },
    )

    receipt = isomorphism_decompose.composite_ratify(
        result,
        posed,
        "goal",
        {},
        lean_root=tmp_path,
        original_source=posed,
    )

    assert receipt["parent_closed"] is False
    assert receipt["status"] == "governance_unavailable"


def test_composite_axiom_audit_unavailability_cannot_close_parent(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ztare.gates import lean_compile_primitives, lean_proof_gate
    from ztare.leanmill.solver import isomorphism_decompose

    posed, closed, result = _composite_inputs()
    _patch_composite_assembly(monkeypatch, closed)
    monkeypatch.setattr(
        lean_proof_gate,
        "run_anti_laundering_kernel",
        lambda *_args, **_kwargs: {
            "available": True,
            "passed": True,
            "confirmed": [],
        },
    )
    monkeypatch.setattr(
        lean_compile_primitives,
        "audit_axioms_subset",
        lambda *_args, **_kwargs: (False, False, []),
    )

    receipt = isomorphism_decompose.composite_ratify(
        result,
        posed,
        "goal",
        {},
        lean_root=tmp_path,
        original_source=posed,
    )

    assert receipt["parent_closed"] is False
    assert receipt["status"] == "axiom_audit_unavailable"
    assert receipt["axiom_allowlist_receipt"]["available"] is False


def test_composite_compares_binders_and_hypotheses_before_compilation(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ztare.gates import v33_preflight_risk_detector
    from ztare.leanmill.solver import isomorphism_decompose

    posed, _closed, result = _composite_inputs()
    changed = "theorem goal (P : Prop) : P := by sorry"
    result["chain"] = changed
    _patch_composite_assembly(monkeypatch, changed)

    def compile_forbidden(*_args, **_kwargs):
        raise AssertionError("signature mismatch reached compilation")

    monkeypatch.setattr(
        v33_preflight_risk_detector,
        "_compile_probe",
        compile_forbidden,
    )
    receipt = isomorphism_decompose.composite_ratify(
        result,
        posed,
        "goal",
        {},
        lean_root=tmp_path,
        original_source=posed,
    )

    assert receipt["parent_closed"] is False
    assert "DIFFERENT statement" in receipt["reason"]


def test_composite_requires_all_positive_authorities(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ztare.gates import lean_compile_primitives, lean_proof_gate
    from ztare.leanmill.solver import isomorphism_decompose

    posed, closed, result = _composite_inputs()
    _patch_composite_assembly(monkeypatch, closed)
    monkeypatch.setattr(
        lean_proof_gate,
        "run_anti_laundering_kernel",
        lambda *_args, **_kwargs: {
            "available": True,
            "passed": True,
            "confirmed": [],
        },
    )
    monkeypatch.setattr(
        lean_compile_primitives,
        "audit_axioms_subset",
        lambda *_args, **_kwargs: (True, False, []),
    )

    receipt = isomorphism_decompose.composite_ratify(
        result,
        posed,
        "goal",
        {},
        lean_root=tmp_path,
        original_source=posed,
    )

    assert receipt["parent_closed"] is True
    assert receipt["status"] == "ratified"
    assert receipt["governance_kernel_receipt"]["available"] is True
    assert receipt["axiom_allowlist_receipt"] == {
        "passed": True,
        "available": True,
        "bad_axioms": [],
        "axioms": [],
    }


def test_context_stripped_unknown_identifier_is_typed_inconclusive(
    tmp_path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ztare.formal import repl_compile

    monkeypatch.setattr(
        repl_compile,
        "compile_probe_via_repl",
        lambda *_args, **_kwargs: (
            False,
            "error: unknown identifier 'CampaignVocabulary'",
        ),
    )

    passed, tail = solver_core._verify_matched_negative_control(
        "target",
        "by exact campaignLemma",
        tmp_path,
        1,
        goal_type=": CampaignVocabulary",
    )

    assert passed is None
    assert tail.startswith("inconclusive:")


def test_source_aware_conclusion_control_preserves_context_and_identity(
    tmp_path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ztare.gates import v33_preflight_risk_detector
    from ztare.leanmill.solver.proof_margin_of_safety import (
        conclusion_discrimination_control,
    )

    source = (
        "import Mathlib\n"
        "namespace Demo\n"
        "def CampaignVocabulary : Prop := True\n"
        "theorem target (h : CampaignVocabulary) : CampaignVocabulary := by\n"
        "  exact h\n"
        "theorem trailing (h : CampaignVocabulary) : CampaignVocabulary :=\n"
        "  target h\n"
        "end Demo\n"
    )
    probes: list[tuple[str, str]] = []

    def compile_probe(probe: str, _root, tag: str, _timeout: int):
        probes.append((tag, probe))
        return tag == "MoS_discrimination_positive"

    monkeypatch.setattr(v33_preflight_risk_detector, "_compile_probe", compile_probe)

    receipt = conclusion_discrimination_control(
        source, "Demo.target", tmp_path, timeout_s=1
    )

    assert receipt["status"] == "pass"
    assert receipt["passed"] is True
    assert receipt["discriminating"] is True
    assert [tag for tag, _probe in probes] == [
        "MoS_discrimination_positive",
        "MoS_discrimination",
    ]
    positive, negative = probes[0][1], probes[1][1]
    assert "def CampaignVocabulary" in positive
    assert "theorem trailing" not in positive
    assert positive.rstrip().endswith("end Demo")
    assert "theorem target" in negative
    assert ": ¬ (CampaignVocabulary) := by\n  exact h" in negative
    assert "theorem target_negdisc" not in negative


def test_bound_conclusion_control_rejects_every_identity_drift() -> None:
    import hashlib

    from ztare.leanmill.solver.proof_margin_of_safety import (
        bind_conclusion_discrimination_receipt,
        build_conclusion_discrimination_probes,
        validate_conclusion_discrimination_receipt,
    )

    closed = (
        "import Mathlib\n"
        "namespace Demo\n"
        "theorem target (P : Prop) (h : P) : P := by exact h\n"
        "end Demo\n"
    )
    posed = closed.replace("by exact h", "by sorry")
    evidence, positive, negative = build_conclusion_discrimination_probes(
        closed, "Demo.target"
    )
    receipt = {
        **evidence,
        "status": "pass",
        "available": True,
        "passed": True,
        "discriminating": True,
        "differential": "confirmed",
        "positive_compiled": True,
        "negative_compiled": False,
        "posed_source_sha256": hashlib.sha256(posed.encode()).hexdigest(),
        "closure_source_sha256": hashlib.sha256(closed.encode()).hexdigest(),
        "admitted_under_policy": True,
        "policy": "require_discriminating_control",
    }

    assert positive and negative
    assert validate_conclusion_discrimination_receipt(
        receipt,
        closed,
        "Demo.target",
        posed_source=posed,
    ) == receipt
    rebound = bind_conclusion_discrimination_receipt(
        {
            **evidence,
            "status": "pass",
            "available": True,
            "passed": True,
            "discriminating": True,
            "differential": "confirmed",
            "positive_compiled": True,
            "negative_compiled": False,
            "interpretation": "positive compiled and negative did not",
        },
        closed,
        "Demo.target",
        posed_source=posed,
    )
    assert rebound is not None
    assert rebound["posed_source_sha256"] == receipt["posed_source_sha256"]
    assert rebound["closure_source_sha256"] == receipt[
        "closure_source_sha256"
    ]
    mutations = {
        "target_identity": "Other.target",
        "target_signature_sha256": "0" * 64,
        "positive_probe_sha256": "1" * 64,
        "negative_probe_sha256": "2" * 64,
        "posed_source_sha256": "3" * 64,
        "closure_source_sha256": "4" * 64,
        "negative_compiled": True,
    }
    for field, value in mutations.items():
        assert validate_conclusion_discrimination_receipt(
            {**receipt, field: value},
            closed,
            "Demo.target",
            posed_source=posed,
        ) is None


def test_ratification_blocks_inconclusive_source_aware_control_but_ordinary_search_abstains(
    tmp_path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ztare.gates import lean_compile_primitives, lean_proof_gate
    from ztare.leanmill.solver import proof_margin_of_safety

    monkeypatch.setattr(solver_core, "OUT_DIR", tmp_path)
    monkeypatch.setattr(
        solver_core,
        "_verify_matched_negative_control",
        lambda *_args, **_kwargs: (None, "inconclusive: context control abstained"),
    )
    monkeypatch.setattr(solver_core, "_campaign_aware_axioms", lambda *_a, **_k: None)
    monkeypatch.setattr(
        lean_proof_gate,
        "run_anti_laundering_kernel",
        lambda *_args, **_kwargs: {
            "available": True,
            "passed": True,
            "confirmed": [],
            "flags": [],
        },
    )
    monkeypatch.setattr(
        lean_compile_primitives,
        "audit_axioms_subset",
        lambda *_args, **_kwargs: (True, False, []),
    )
    monkeypatch.setattr(
        proof_margin_of_safety,
        "conclusion_discrimination_control",
        lambda *_args, **_kwargs: {
            "kind": "source_aware_conclusion_perturbation",
            "status": "inconclusive",
            "passed": None,
            "discriminating": False,
            "reason": "negative control compiler unavailable",
        },
    )
    posed = "theorem target : True := by\n  sorry\n"
    closed = "theorem target : True := by\n  trivial\n"
    common = dict(
        contract=_contract(),
        proof_text="by\n  trivial",
        enriched_goal="theorem target : True := by",
        target_name="target",
        lean_root=tmp_path,
        timeout_s=1,
        kernel_compile_ok=True,
        kernel_compile_tail="ok",
        goal_type=": True",
        closure_source=closed,
        posed_source=posed,
    )

    ordinary = solver_core._validate_against_contract(**common)
    strict = solver_core._validate_against_contract(
        **common,
        require_positive_axiom_receipt=True,
        require_discriminating_mnc=True,
    )

    ordinary_mnc = ordinary["receipts"]["matched_negative_control_receipt"]
    assert ordinary["credit_ready_at_solver_layer"] is True
    assert ordinary_mnc["passed"] is None
    assert ordinary_mnc["status"] == "inconclusive"
    assert ordinary_mnc["admitted_under_policy"] is True
    strict_mnc = strict["receipts"]["matched_negative_control_receipt"]
    assert strict["credit_ready_at_solver_layer"] is False
    assert strict_mnc["kind"] == "source_aware_conclusion_perturbation"
    assert strict_mnc["passed"] is None
    assert strict_mnc["status"] == "inconclusive"
    assert strict_mnc["admitted_under_policy"] is False
    assert solver_core._reject_reason_from_validation(strict)[0] == (
        "rejected_mnc_inconclusive"
    )


def test_ratification_accepts_positive_source_aware_differential(
    tmp_path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ztare.gates import lean_compile_primitives, lean_proof_gate
    from ztare.leanmill.solver import proof_margin_of_safety

    monkeypatch.setattr(solver_core, "OUT_DIR", tmp_path)
    monkeypatch.setattr(solver_core, "_campaign_aware_axioms", lambda *_a, **_k: None)
    monkeypatch.setattr(
        lean_proof_gate,
        "run_anti_laundering_kernel",
        lambda *_args, **_kwargs: {
            "available": True,
            "passed": True,
            "confirmed": [],
            "flags": [],
        },
    )
    monkeypatch.setattr(
        lean_compile_primitives,
        "audit_axioms_subset",
        lambda *_args, **_kwargs: (True, False, []),
    )
    monkeypatch.setattr(
        proof_margin_of_safety,
        "conclusion_discrimination_control",
        lambda *_args, **_kwargs: {
            "kind": "source_aware_conclusion_perturbation",
            "status": "pass",
            "passed": True,
            "discriminating": True,
            "differential": "confirmed",
            "positive_compiled": True,
            "negative_compiled": False,
        },
    )

    validation = solver_core._validate_against_contract(
        contract=_contract(),
        proof_text="by\n  trivial",
        enriched_goal="theorem target : True := by",
        target_name="target",
        lean_root=tmp_path,
        timeout_s=1,
        kernel_compile_ok=True,
        kernel_compile_tail="ok",
        goal_type=": True",
        closure_source="theorem target : True := by\n  trivial\n",
        posed_source="theorem target : True := by\n  sorry\n",
        require_positive_axiom_receipt=True,
        require_discriminating_mnc=True,
    )

    receipt = validation["receipts"]["matched_negative_control_receipt"]
    assert validation["credit_ready_at_solver_layer"] is True
    assert receipt["kind"] == "source_aware_conclusion_perturbation"
    assert receipt["status"] == "pass"
    assert receipt["positive_compiled"] is True
    assert receipt["negative_compiled"] is False


def test_ratification_requires_kernel_integrity_and_differential_receipts() -> None:
    complete = {
        "governance_kernel": {"available": True, "passed": True},
        "statement_integrity": {"ok": True},
        "margin_of_safety": {
            "tests": {
                "conclusion_discrimination": {
                    "detail": {"differential": "confirmed"}
                }
            }
        },
    }

    assert solver_core._ratification_receipt_blockers(complete) == []
    assert solver_core._ratification_receipt_blockers({}) == [
        "kernel:ratification_receipt_unverified",
        "margin:differential_unverified",
    ]
    no_differential = {
        **complete,
        "margin_of_safety": {"error": "battery unavailable"},
    }
    assert solver_core._ratification_receipt_blockers(no_differential) == [
        "margin:differential_unverified"
    ]


def test_ratification_stamp_requires_positive_governance_receipts() -> None:
    assert solver_core._governance_ratification_eligible(
        _positive_target_governance()
    ) is True
    assert solver_core._governance_ratification_eligible({
        "error": "outer governance crashed",
    }) is False
    assert solver_core._governance_ratification_eligible({
        "governance_kernel": {"passed": None},
        "statement_integrity": {"ok": True},
        "integrity_unverified": True,
    }) is False


def test_campaign_warm_compile_failure_falls_back_to_full_module_cold_compile(
    tmp_path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    campaign = tmp_path / "Campaign.lean"
    campaign.write_text("theorem existing : True := by trivial\n", encoding="utf-8")
    source = "namespace Demo\ntheorem target : True := by\n  sorry\nend Demo\n"

    from ztare.formal import repl_compile
    from ztare.gates import v33_preflight_risk_detector

    monkeypatch.setattr(repl_compile, "get_campaign_substrate", lambda: campaign)
    monkeypatch.setattr(repl_compile, "campaign_file_env", lambda *_args: object())
    monkeypatch.setattr(
        repl_compile,
        "warm_verify_campaign",
        lambda *_args, **_kwargs: (False, "warm namespace mismatch"),
    )
    cold_probes: list[str] = []
    monkeypatch.setattr(
        v33_preflight_risk_detector,
        "_compile_probe",
        lambda probe, *_args, **_kwargs: cold_probes.append(probe) or True,
    )
    diagnostics: list[str] = []

    assert solver_core._campaign_aware_proof_compiles(
        source,
        "by\n  trivial",
        tmp_path,
        1,
        diag_out=diagnostics,
        target_name="Demo.target",
    )
    assert cold_probes and "namespace Demo" in cold_probes[0]
    assert "warm namespace mismatch" in diagnostics[0]


def test_ratification_certificate_carries_exact_solver_receipts() -> None:
    source = inspect.getsource(solver_core.solve_adhoc)
    assert '"solver_validation": _public_sanitize(' in source
    assert '"ratification_only": bool(preverified_only)' in source
    assert "require_positive_axiom_receipt=bool(" in inspect.getsource(
        solver_core.solve
    )
