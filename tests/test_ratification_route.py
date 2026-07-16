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
        lambda *_args, **_kwargs: {"passed": True, "confirmed": [], "flags": []},
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
        lambda *_args, **_kwargs: {"passed": True, "confirmed": [], "flags": []},
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
        "governance_kernel": {"passed": True},
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
