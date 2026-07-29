from __future__ import annotations

import inspect


def _positive_target_governance() -> dict:
    from ztare.leanmill.ratification_policy import (
        TARGET_GOVERNANCE_AUTHORITIES,
        TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256,
    )

    return {
        "governance_kernel": {
            "available": True,
            "passed": True,
            "confirmed": [],
            "flags": ["advisory"],
            "detail": {"vacuity": {"vacuity_suspected": False}},
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
    }


def test_verified_closure_artifact_binds_the_full_target_type() -> None:
    from ztare.leanmill.solver.closed_artifact import (
        build_verified_closure_artifact,
        validate_verified_closure_artifact,
    )

    posed = "theorem target (P : Prop) (h : P) : P := by sorry"
    closed = "theorem target (P : Prop) (h : P) : P := by exact h"
    changed = "theorem target (P : Prop) : P := by sorry"

    artifact = build_verified_closure_artifact("target", closed, posed)

    assert artifact is not None
    assert artifact["schema"] == "leanmill.verified_closure_artifact.v2"
    assert artifact["posed_target_signature_sha256"] == artifact[
        "closed_target_signature_sha256"
    ]
    assert validate_verified_closure_artifact(artifact, "target") is artifact
    assert build_verified_closure_artifact("target", closed, changed) is None

    tampered = dict(artifact)
    tampered["posed_target_signature_sha256"] = "0" * 64
    assert validate_verified_closure_artifact(tampered, "target") is None


def test_toolchain_identity_is_content_bound_and_path_neutral(
    tmp_path, monkeypatch
) -> None:
    from ztare.leanmill.solver import closed_artifact

    root = tmp_path / "proofs"
    root.mkdir()
    (root / "lean-toolchain").write_text("leanprover/lean4:v4.19.0\n")
    (root / "lakefile.toml").write_text('name = "Proofs"\n')
    manifest = root / "lake-manifest.json"
    manifest.write_text('{"version": 1}\n')
    monkeypatch.setattr(
        closed_artifact,
        "_run_text",
        lambda command, **_kwargs: (
            "Lean (version 4.19.0)" if tuple(command)[-2:] == ("lean", "--version") else ""
        ),
    )
    closed_artifact._closure_toolchain_identity_cached.cache_clear()

    first = closed_artifact.closure_toolchain_identity(root)
    manifest.write_text('{"version": 2}\n')
    closed_artifact._closure_toolchain_identity_cached.cache_clear()
    second = closed_artifact.closure_toolchain_identity(root)

    assert first["schema"] == "leanmill.closure_toolchain_identity.v1"
    assert first["complete"] is True
    assert first["project"] == "proofs"
    assert str(tmp_path) not in repr(first)
    assert first["identity_sha256"] != second["identity_sha256"]


def test_kernel_parity_record_binds_closure_toolchain_and_environment() -> None:
    from ztare.leanmill.solver.closed_artifact import (
        build_kernel_parity_record,
        closure_certificate_identity,
        finalize_solver_validation,
    )
    from ztare.leanmill.ratification_policy import (
        FINAL_RATIFICATION_AUTHORITY_ROSTER_SHA256,
    )

    identity = closure_certificate_identity(
        row_id="attempt-17",
        run_tag="run-17",
        target="target",
        goal="True",
        source="theorem target : True := by trivial",
        probe="theorem target : True := by trivial",
        proof="by trivial",
    )
    validation = finalize_solver_validation(
        {
            "credit_ready_at_solver_layer": True,
            "receipts": {
                "kernel_compile_receipt": {"available": True, "passed": True},
                "matched_negative_control_receipt": {"available": True, "passed": True},
                "axiom_allowlist_receipt": {"available": True, "passed": True},
            },
        },
        _positive_target_governance(),
    )
    record = build_kernel_parity_record(
        target="target",
        timestamp="2026-07-18T00:00:00Z",
        certificate_identity=identity,
        solver_validation=validation,
        governance=_positive_target_governance(),
        toolchain_identity={"identity_sha256": "a" * 64},
        environment_parity={"attempted": True, "reason": "banked"},
    )

    assert record["schema"] == "leanmill.kernel_parity_record.v2"
    assert record["job_id"] == "attempt-17"
    assert record["run_tag"] == "run-17"
    assert record["source_sha256"] == identity["source_sha256"]
    assert record["toolchain_identity_sha256"] == "a" * 64
    assert record["hand_wired"] == {"kc": True, "mnc": True}
    assert record["kernel_blocked"] is False
    assert record["final_authority_roster_sha256"] == (
        FINAL_RATIFICATION_AUTHORITY_ROSTER_SHA256
    )
    assert set(record["final_authority_disposition"]) == set(
        validation["final_authority_disposition"]
    )
    assert len(record["record_sha256"]) == 64


def test_final_validation_resolves_deferred_governance_receipts() -> None:
    from ztare.leanmill.ratification_policy import (
        FINAL_RATIFICATION_AUTHORITIES,
        FINAL_RATIFICATION_AUTHORITY_ROSTER_SHA256,
    )
    from ztare.leanmill.solver.closed_artifact import (
        finalize_solver_validation,
        finalized_ratification_eligible,
    )

    producer = {
        "credit_ready_at_solver_layer": True,
        "receipts": {
            "kernel_compile_receipt": {"available": True, "passed": True},
            "matched_negative_control_receipt": {
                "available": True,
                "passed": True,
                "admitted_under_policy": True,
            },
            "axiom_allowlist_receipt": {"available": True, "passed": True},
            "governance_kernel_receipt": {
                "passed": None,
                "status": "deferred_to_closed_artifact_finalizer",
            },
            "l3_anti_pattern_receipt": {"passed": None},
        },
    }
    governance = _positive_target_governance()

    finalized = finalize_solver_validation(producer, governance)

    assert producer["receipts"]["governance_kernel_receipt"]["passed"] is None
    assert finalized["credit_ready_at_solver_layer"] is True
    assert finalized_ratification_eligible(finalized)
    assert finalized["final_authority_roster_sha256"] == (
        FINAL_RATIFICATION_AUTHORITY_ROSTER_SHA256
    )
    assert set(finalized["final_authority_disposition"]) == (
        FINAL_RATIFICATION_AUTHORITIES
    )
    assert all(
        value == "passed"
        for value in finalized["final_authority_disposition"].values()
    )
    assert finalized["final_governance_ratification_eligible"] is True
    assert finalized["receipts"]["governance_kernel_receipt"]["passed"] is True
    assert finalized["receipts"]["l3_anti_pattern_receipt"]["passed"] is True
    assert finalized["receipts"]["l3_anti_pattern_receipt"]["available"] is True
    assert (
        finalized["receipts"]["governance_kernel_receipt"]["producer_receipt"][
            "passed"
        ]
        is None
    )

    tampered = dict(finalized)
    tampered["final_authority_roster_sha256"] = "0" * 64
    assert not finalized_ratification_eligible(tampered)


def test_final_validation_withholds_credit_on_governance_rejection() -> None:
    from ztare.leanmill.solver.closed_artifact import finalize_solver_validation

    finalized = finalize_solver_validation(
        {
            "credit_ready_at_solver_layer": True,
            "receipts": {
                "governance_kernel_receipt": {"passed": None},
            },
        },
        {
            "governance_kernel": {
                "available": True,
                "passed": False,
                "confirmed": ["vacuity"],
            },
            "statement_integrity": {"ok": True},
        },
    )

    assert finalized["credit_ready_at_solver_layer"] is False
    assert finalized["receipts"]["governance_kernel_receipt"]["passed"] is False


def test_final_validation_requires_explicit_receipt_availability() -> None:
    from ztare.leanmill.solver.closed_artifact import (
        finalize_solver_validation,
        finalized_ratification_eligible,
    )

    finalized = finalize_solver_validation(
        {
            "credit_ready_at_solver_layer": True,
            "receipts": {
                "kernel_compile_receipt": {"passed": True},
                "matched_negative_control_receipt": {"passed": True},
                "axiom_allowlist_receipt": {"passed": True},
            },
        },
        _positive_target_governance(),
    )

    assert finalized["credit_ready_at_solver_layer"] is False
    assert finalized["final_ratification_eligible"] is False
    assert not finalized_ratification_eligible(finalized)
    assert {
        authority: finalized["final_authority_disposition"][authority]
        for authority in (
            "kernel_compile_receipt",
            "matched_negative_control_receipt",
            "axiom_allowlist_receipt",
        )
    } == {
        "kernel_compile_receipt": "unavailable",
        "matched_negative_control_receipt": "unavailable",
        "axiom_allowlist_receipt": "unavailable",
    }


def test_final_validation_requires_explicit_governance_availability() -> None:
    from ztare.leanmill.solver.closed_artifact import finalize_solver_validation

    finalized = finalize_solver_validation(
        {
            "credit_ready_at_solver_layer": True,
            "receipts": {"governance_kernel_receipt": {"passed": None}},
        },
        {
            "governance_kernel": {"passed": True, "confirmed": []},
            "statement_integrity": {"ok": True},
        },
    )

    assert finalized["credit_ready_at_solver_layer"] is False
    assert finalized["final_governance_ratification_eligible"] is False
    receipt = finalized["receipts"]["governance_kernel_receipt"]
    assert {key: receipt[key] for key in (
        "passed",
        "available",
        "status",
        "authority",
        "confirmed",
        "flags",
        "unavailable_organs",
        "detail",
        "producer_receipt",
    )} == {
        "passed": False,
        "available": False,
        "status": "finalized_by_closed_artifact_governance",
        "authority": "common_closed_artifact_finalizer",
        "confirmed": [],
        "flags": [],
        "unavailable_organs": [],
        "detail": {},
        "producer_receipt": {"passed": None},
    }
    assert finalized["receipts"]["l3_anti_pattern_receipt"]["passed"] is False
    assert finalized["receipts"]["l3_anti_pattern_receipt"]["available"] is False


def test_final_validation_withholds_credit_on_governance_unavailability() -> None:
    from ztare.leanmill.solver.closed_artifact import finalize_solver_validation

    finalized = finalize_solver_validation(
        {
            "credit_ready_at_solver_layer": True,
            "receipts": {"governance_kernel_receipt": {"passed": None}},
        },
        {
            "governance_kernel": {
                "available": False,
                "passed": True,
                "confirmed": [],
                "unavailable_organs": ["canonical_reelaboration"],
            },
            "statement_integrity": {"ok": True},
        },
    )

    assert finalized["credit_ready_at_solver_layer"] is False
    assert finalized["final_governance_ratification_eligible"] is False
    assert finalized["receipts"]["governance_kernel_receipt"]["passed"] is False


def test_finalizer_fault_has_a_complete_typed_no_credit_state() -> None:
    from ztare.leanmill.ratification_policy import (
        FINAL_RATIFICATION_AUTHORITIES,
        FINAL_RATIFICATION_AUTHORITY_ROSTER_SHA256,
    )
    from ztare.leanmill.solver.closed_artifact import (
        finalized_ratification_eligible,
        unavailable_finalized_validation,
    )

    validation = unavailable_finalized_validation("injected finalizer fault")

    assert validation["finalized_at_closed_artifact_boundary"] is True
    assert validation["credit_ready_at_solver_layer"] is False
    assert validation["final_ratification_eligible"] is False
    assert validation["final_authority_roster_sha256"] == (
        FINAL_RATIFICATION_AUTHORITY_ROSTER_SHA256
    )
    assert set(validation["final_authority_disposition"]) == (
        FINAL_RATIFICATION_AUTHORITIES
    )
    assert not finalized_ratification_eligible(validation)


def test_finalized_outcome_projects_the_failed_authority_without_collapsing() -> None:
    from ztare.leanmill.ratification_policy import (
        FINAL_RATIFICATION_AUTHORITIES,
        TARGET_GOVERNANCE_AUTHORITIES,
    )
    from ztare.leanmill.solver.closed_artifact import finalized_artifact_outcome

    def validation_with(*rejected: str) -> dict:
        return {
            "final_required_authorities": sorted(FINAL_RATIFICATION_AUTHORITIES),
            "final_authority_disposition": {
                authority: "rejected" if authority in rejected else "passed"
                for authority in FINAL_RATIFICATION_AUTHORITIES
            },
            "final_ratification_eligible": False,
            "finalized_at_closed_artifact_boundary": True,
        }

    assert finalized_artifact_outcome(
        validation_with("axiom_allowlist_receipt")
    ) == "rejected_banned_axiom"
    assert finalized_artifact_outcome(
        validation_with("matched_negative_control_receipt")
    ) == "rejected_mnc_leakage"
    assert finalized_artifact_outcome(
        validation_with(next(iter(TARGET_GOVERNANCE_AUTHORITIES)))
    ) == "rejected_governance"
    assert finalized_artifact_outcome(
        validation_with("axiom_allowlist_receipt", "kernel_compile_receipt")
    ) == "rejected_multiple_authorities"


def test_dag_closure_requires_full_contract_credit() -> None:
    from ztare.leanmill.solver.closed_artifact import dag_governance_axes
    from ztare.leanmill.solver.governed_dag_search import MoveResult

    validation = {
        "credit_ready_at_solver_layer": False,
        "receipts": {
            "kernel_compile_receipt": {"available": True, "passed": True},
            "matched_negative_control_receipt": {
                "available": True,
                "admitted_under_policy": True,
            },
            "governance_kernel_receipt": {"passed": False},
            "axiom_allowlist_receipt": {"passed": True},
        },
    }
    kernel, mnc, governed = dag_governance_axes(validation)

    assert (kernel, mnc, governed) == (True, False, False)
    assert not MoveResult(
        move="native_hammer",
        kernel_clean=kernel,
        mnc_passed=mnc,
        governance_ready=governed,
        proof_text="by exact candidate",
    ).ratified_close


def test_dynamic_conjecture_child_cannot_status_flip_parent() -> None:
    from ztare.leanmill.solver.governed_dag_search import (
        MOVE_CONJECTURE,
        DagNode,
        MoveResult,
        run_governed_dag_search,
    )

    proposed = {"done": False}

    def runner(node: DagNode, move: str, _budget: float) -> MoveResult:
        if node.kind == "root_goal":
            if move == MOVE_CONJECTURE and not proposed["done"]:
                proposed["done"] = True
                return MoveResult(
                    move=move,
                    new_sub_goal_text="lemma helper : True := by",
                )
            return MoveResult(move=move)
        return MoveResult(
            move=move,
            kernel_clean=True,
            mnc_passed=True,
            governance_ready=True,
            proof_text="by trivial",
        )

    result = run_governed_dag_search(
        {},
        "theorem root : True := by",
        runner,
        max_moves=30,
        move_budget_units=100,
        defer_threshold=0.0,
    )

    children = [
        node for key, node in result["nodes"].items() if key != "n0_root"
    ]
    assert children and all(node["composition_required"] for node in children)
    assert result["root_status"] != "closed"
    assert any(
        event.get("event")
        == "parent_close_withheld_pending_composite_ratification"
        for event in result["trace"]
    )


def test_decomposition_lift_carries_exact_artifact_and_proof_body() -> None:
    from ztare.leanmill.solver.solver_core import _lift_decomposition_closure

    posed = "import Mathlib\n\ntheorem target : True := by sorry\n"
    closed = "import Mathlib\n\ntheorem target : True := by trivial\n"
    result = {
        "results": [
            {
                "target_theorem_name": "target",
                "outcome": "exact_gap",
            }
        ]
    }
    route = {
        "solution": {
            "parent_closed": True,
            "composite": {
                "parent_closed": True,
                "target": "target",
                "composite_source": closed,
                "posed_source": posed,
                "governance_kernel_receipt": {
                    "available": True,
                    "passed": True,
                    "detail": {"statement_integrity": {"ok": True}},
                },
                "axiom_allowlist_receipt": {
                    "available": True,
                    "passed": True,
                    "axioms": [],
                },
            },
        }
    }

    assert _lift_decomposition_closure(result, route)
    lifted = result["results"][0]
    assert lifted["outcome"] == "closed"
    assert lifted["proof_text"] == "by trivial"
    assert lifted["verified_closure_artifact"]["closure_source"] == closed
    assert lifted["contract_validation"]["credit_ready_at_solver_layer"]


def test_margin_consumes_authoritative_kernel_receipt(monkeypatch) -> None:
    from ztare.gates import lean_proof_gate
    from ztare.leanmill.solver.proof_margin_of_safety import (
        proof_margin_of_safety,
    )

    def forbidden_second_kernel(*_args, **_kwargs):
        raise AssertionError("the margin battery invoked a second kernel")

    monkeypatch.setattr(
        lean_proof_gate,
        "run_anti_laundering_kernel",
        forbidden_second_kernel,
    )
    report = proof_margin_of_safety(
        "import Mathlib\n\ntheorem target : True := by trivial\n",
        "target",
        deep=False,
        soundness_kernel_receipt={
            "passed": True,
            "confirmed": [],
            "flags": [],
        },
    )

    assert report["tests"]["soundness"]["verdict"] == "strengthen"


def test_margin_reuses_one_exact_bound_conclusion_control(
    tmp_path,
    monkeypatch,
) -> None:
    import hashlib

    from ztare.leanmill.solver import proof_margin_of_safety as margin_module
    from ztare.leanmill.solver.proof_margin_of_safety import (
        build_conclusion_discrimination_probes,
        proof_margin_of_safety,
    )

    closed = "import Mathlib\n\ntheorem target : True := by trivial\n"
    posed = closed.replace("by trivial", "by sorry")
    evidence, _positive, _negative = build_conclusion_discrimination_probes(
        closed, "target"
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

    def forbidden_second_control(*_args, **_kwargs):
        raise AssertionError("the margin battery executed the matched control twice")

    monkeypatch.setattr(
        margin_module,
        "conclusion_discrimination_control",
        forbidden_second_control,
    )
    report = proof_margin_of_safety(
        closed,
        "target",
        lean_root=tmp_path,
        deep=True,
        original_source=posed,
        soundness_kernel_receipt={
            "passed": True,
            "confirmed": [],
            "flags": [],
        },
        conclusion_discrimination_receipt=receipt,
    )

    assert report["tests"]["conclusion_discrimination"]["detail"] == receipt
    assert report["tests"]["conclusion_discrimination"]["verdict"] == (
        "strengthen"
    )


def test_all_root_producers_converge_before_one_effect_epilogue() -> None:
    from ztare.leanmill.solver import solver_core

    source = inspect.getsource(solver_core.solve_adhoc)
    quarantine = source.index("with _gate.clean_capability")
    decompose = source.index("_ras_pre", quarantine)
    solve = source.index("res = solve(", decompose)
    finalizer = source.index('if r0.get("outcome") == "closed":', solve)
    parity = source.index("_environment_parity_decision(", finalizer)
    stamp = source.index("_record_governance_verdict(", parity)
    certificate = source.index("append_jsonl_locked", finalizer)

    assert quarantine < decompose < solve < finalizer < parity < stamp < certificate
    assert "return _decomposition_closed_result" not in source
    assert source.count("_environment_parity_decision(") == 1
    assert source.count("append_jsonl_locked(ADHOC_CLOSURE_CERTIFICATES") == 1
    assert source.count('source=f"adhoc_closure:{target_name}"') == 1


def test_dag_cache_reuse_calls_the_same_governance_door() -> None:
    from ztare.leanmill.solver import solver_core

    source = inspect.getsource(solver_core.solve)
    cache_start = source.index("def _cache_verify_node")
    cache_end = source.index("def _cache_put_node", cache_start)
    cache_verifier = source[cache_start:cache_end]

    assert 'getattr(move_runner, "_govern", None)' in cache_verifier
    assert "return bool(_kc and _mnc and _gov)" in cache_verifier
    cache_put_start = source.index("def _cache_put_node", cache_end)
    cache_put_end = source.index("_dag_max_moves", cache_put_start)
    cache_putter = source[cache_put_start:cache_put_end]
    assert 'and getattr(_node, "node_id", "") == "n0_root"' in cache_putter


def test_preverified_candidate_precedes_dag_dispatch() -> None:
    from ztare.leanmill.solver import solver_core

    source = inspect.getsource(solver_core.solve)
    phase = source.index("_preverified_phase = solve(")
    dag = source.index("run_governed_dag_search(")

    assert phase < dag


def test_certificate_identity_uses_existing_job_and_nonempty_run_tag() -> None:
    from ztare.leanmill.solver.closed_artifact import closure_certificate_identity
    from ztare.leanmill.solver import solver_core

    attempt_id = "adhoc::target::2026-07-18T18:03:27.346000+00:00"
    identity = closure_certificate_identity(
        row_id=attempt_id,
        run_tag="",
        target="target",
        goal="True",
        source="theorem target : True := by trivial",
        probe="theorem target : True := by trivial",
        proof="by trivial",
    )

    assert identity["job_id"] == attempt_id
    assert identity["run_tag"] == identity["job_id"]
    solve_source = inspect.getsource(solver_core.solve_adhoc)
    assert 'f"adhoc::{target_name}::{_run_start}"' in solve_source
    assert 'row_id=r0.get("row_id") or row["row_id"]' in solve_source
    assert all(
        identity[key]
        for key in (
            "goal_sha256",
            "source_sha256",
            "recompilable_probe_sha256",
            "proof_sha256",
            "posed_target_signature_sha256",
            "closed_target_signature_sha256",
        )
    )
