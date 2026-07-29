from __future__ import annotations

from contextlib import contextmanager
import copy
import hashlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

import ztare.leanmill.construction_artifact_ratification as construction_ratification_module

from ztare.common.task_discharge import TaskDischargeContract, TaskDischargeReceipt
from ztare.leanmill.adapters.binary_linear_code import (
    ADAPTER_ID,
    BINARY_FORMAL_MAX_NONZERO_MESSAGES,
    BinaryGeneratorMatrix,
    binary_code_predicate,
    binary_construction_artifact_formal_certificate,
    binary_construction_artifact_formal_interface,
    binary_generator_matrix_schema,
    binary_witness_construction_interface,
    normalize_binary_generator_candidate,
    verify_binary_generator_candidate,
)
from ztare.leanmill.construction_artifact_ratification import (
    ConstructionArtifactRatificationCapabilityUnavailable,
    build_construction_artifact_formal_input,
    build_construction_artifact_formal_interface,
    build_construction_artifact_ratification_contract,
    construction_artifact_ratification_filename,
    ratify_construction_artifact_formal_input_action,
    ratify_construction_artifact_action,
    replay_ratified_construction_artifact_result,
    render_construction_artifact_certificate,
    validate_construction_artifact_ratification_aggregate,
)
from ztare.leanmill.common import read_json, write_json_atomic
from ztare.leanmill.frontier_campaign_runner import (
    _consume_theory_task_discharge,
    _pending_construction_artifact_ratifications,
    execute_frontier_construction_artifact_ratification,
)
from ztare.leanmill.exploration_budget import (
    ExplorationBudgetLedger,
    budget_preset,
)
from ztare.leanmill.lean_source import replace_decl_proof
from ztare.leanmill.governed_ratification import normalized_target_signature
from ztare.leanmill.ratification_policy import (
    TARGET_GOVERNANCE_AUTHORITIES,
    TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256,
)
from ztare.leanmill.solver.closed_artifact import finalize_solver_validation
from ztare.leanmill.theory_program import THEORY_PROGRAM_V2, TheoryProgram
from ztare.leanmill.theory_task_discharge_successor import (
    build_construction_ratification_successor_bundle,
    validate_construction_ratification_successor_bundle,
)
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.witness_construction_boundary import (
    adjudicate_governed_witness_construction_task,
    build_witness_constructor_output,
    build_witness_constructor_request,
    compile_governed_witness_construction_task,
    execute_governed_witness_construction_task,
)


def _orientation() -> dict[str, str]:
    return {
        "eigenquestion": "Can this exact generator meet the frozen code predicate?",
        "representation_choice": "Use one row-basis-normalized generator matrix.",
        "expected_failure_mode": "A nonzero message may yield a low-weight word.",
        "next_revision_if_rejected": "Mint a successor artifact with different rows.",
    }


def _outer_boundary(contract: TaskDischargeContract, row: dict) -> dict:
    core = {
        "schema": "leanmill.frontier_boundary_result.v1",
        "context_hash": contract.parameters["context_hash"],
        "query_results": [row],
        "stop_reason": "completed",
        "next_epoch_proposal": None,
    }
    return {**core, "result_sha256": content_hash(core)}


def _small_binary_task(
    *,
    matrix: BinaryGeneratorMatrix | None = None,
    minimum_distance: int = 2,
    label: str = "small",
) -> tuple[
    TaskDischargeContract, dict, TaskDischargeReceipt
]:
    matrix = matrix or BinaryGeneratorMatrix(3, 2, (3, 5))
    target = f"[{matrix.length},{matrix.dimension},{minimum_distance}]"
    required_messages = (1 << matrix.dimension) - 1
    interface = binary_witness_construction_interface(
        length=matrix.length,
        dimension=matrix.dimension,
        minimum_distance=minimum_distance,
        target_snapshot_sha256="a" * 64,
        max_nonzero_messages=required_messages,
        target_config_sha256="b" * 64,
    )
    context = SimpleNamespace(
        context_hash=f"context:binary-{label}",
        formula_ids=(f"formula:binary-{label}",),
    )
    evidence_refs = [f"selection:binary-{label}"]
    constructor_request = build_witness_constructor_request(
        context_hash=context.context_hash,
        adapter_id=ADAPTER_ID,
        construction_interface=interface,
        task_intent={
            "presentation_formula_ids": list(context.formula_ids),
            "goal": f"Construct an explicit binary {target} generator.",
            "observable": "Exact replay accepts full rank and the stated distance.",
            "evidence_refs": evidence_refs,
            "kill_condition": "Reject a rank defect or a word below the distance.",
            "construction_brief": "Author the declared binary generator matrix.",
        },
    )
    authored = build_witness_constructor_output(
        constructor_request,
        artifact=matrix.to_json(),
        orientation=_orientation(),
        role="witness_constructor",
        agent_id=f"binary-{label}-fixture-author",
        call_receipt_sha256="c" * 64,
    )
    visible = (
        "predicate_ir", "witness_schema", "normalizer", "verifier",
        "discharge_policy", "target_config_sha256", "interface_sha256",
    )
    core = {
        "schema": "leanmill.theory_task_request.v1",
        "context_hash": context.context_hash,
        "context_epoch": 0,
        "presentation_formula_ids": list(context.formula_ids),
        "goal": f"Construct an explicit binary {target} generator.",
        "observable": "Exact replay accepts full rank and the stated distance.",
        "adjudicator_capability": "governed_witness_construction",
        "evidence_refs": evidence_refs + [
            "witness-constructor-authorship:"
            + authored["authorship_receipt"]["receipt_sha256"]
        ],
        "kill_condition": "Reject a rank defect or a word below the distance.",
        "authority": "leaf_request_host_bound",
        "witness_construction": {
            **{field: interface[field] for field in visible},
            "constructor_request": constructor_request,
            "artifact": authored["artifact"],
            "orientation": authored["orientation"],
            "authorship_receipt": authored["authorship_receipt"],
        },
    }
    request = {**core, "request_id": "theory-task-request:" + content_hash(core)}
    lowered = compile_governed_witness_construction_task(
        request=request,
        context=context,
        adapter_id=ADAPTER_ID,
        construction_interface=interface,
    )
    assert lowered is not None
    contract = TaskDischargeContract(
        contract_id=f"task:binary-{label}-ratification",
        adjudicator_id=lowered["adjudicator_id"],
        lifecycle_scope=f"campaign:binary-{label}",
        owner=f"lineage:binary-{label}",
        parameters=lowered["parameters"],
    )
    row = execute_governed_witness_construction_task(
        contract,
        normalizer_fn=normalize_binary_generator_candidate,
        verifier_fn=verify_binary_generator_candidate,
    )
    assert row["status"] == "witness_verified"
    outer = _outer_boundary(contract, row)
    prior = adjudicate_governed_witness_construction_task(
        contract=contract,
        boundary_result=outer,
    )
    assert prior.status == "open"
    return contract, outer, prior


def _positive_validation_bundle() -> dict:
    producer = {
        "contract_schema": "leanmill.proof_contract.v1",
        "receipts": {
            "kernel_compile_receipt": {
                "available": True,
                "passed": True,
                "tail": "compiled",
            },
            "matched_negative_control_receipt": {
                "available": True,
                "passed": True,
                "admitted_under_policy": True,
                "status": "pass",
                "tail": "negated conclusion rejected",
            },
            "governance_kernel_receipt": {
                "available": True,
                "passed": True,
                "confirmed": [],
                "flags": [],
                "tail": "clean",
            },
            "axiom_allowlist_receipt": {
                "available": True,
                "passed": True,
                "axioms": ["propext", "Quot.sound"],
                "tail": "allowlisted",
            },
        },
        "credit_ready_at_solver_layer": True,
        "required_receipts_all_passed_at_solver_layer": True,
        "axiom_tier": "kernel_pure",
        "positive_axiom_receipt_required": True,
        "discriminating_mnc_required": True,
    }
    return finalize_solver_validation(producer, _governance_summary())


def _governance_summary() -> dict:
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
        "margin_of_safety": {
            "tests": {
                "conclusion_discrimination": {
                    "detail": {"differential": "confirmed"},
                    "verdict": "strengthen",
                }
            }
        },
    }


def _successful_fake_solver(tmp_path: Path, captured: dict):
    def solve(target: str, posed: str, goal: str, **kwargs) -> dict:
        captured.update({"target": target, "posed": posed, "goal": goal, "kwargs": kwargs})
        proof = str(kwargs["preverified_proof"])
        closed = replace_decl_proof(posed, target, proof)
        assert closed and "sorry" not in closed
        validation = _positive_validation_bundle()
        governance = _governance_summary()
        provider = "construction_artifact_certificate"
        signature_hash = hashlib.sha256(
            normalized_target_signature(posed, target).encode()
        ).hexdigest()
        record = {
            "certificate_schema": "leanmill.governed_closure.v2",
            "target": target,
            "goal_sha256": hashlib.sha256(goal.encode()).hexdigest(),
            "source_sha256": hashlib.sha256(posed.encode()).hexdigest(),
            "recompilable_probe_sha256": hashlib.sha256(closed.encode()).hexdigest(),
            "proof_sha256": hashlib.sha256(proof.strip().encode()).hexdigest(),
            "posed_target_signature_sha256": signature_hash,
            "closed_target_signature_sha256": signature_hash,
            "outcome": "closed",
            "provider": provider,
            "proof_text": proof.strip(),
            "recompilable_probe": closed,
            "recompilable_probe_reconstructed": False,
            "closure_lean": "closures/binary-small.lean",
            "governance": governance,
            "solver_validation": validation,
            "matched_negative_control": {"passed": True},
            "ratification_only": True,
            "substrate": str(tmp_path),
            "checker": "lean_lake",
        }
        ledger = tmp_path / "adhoc_closure_certificates.jsonl"
        ledger.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")
        record_sha = content_hash(record)
        primary = {
            "outcome": "closed",
            "proof_text": proof.strip(),
            "provider": provider,
            "providers_tried": [{
                "provider": provider,
                "outcome": "compiled",
                "compile_ok": True,
                "agent_kind": "preverified_champion",
                "contract_validation": validation,
            }],
            "contract_validation": validation,
            "matched_negative_control": {"passed": True},
        }
        return {
            "outcome": "closed",
            "results": [primary],
            "closure_candidates": 1,
            "ratification_only": True,
            "provider_calls": 0,
            "governance": governance,
            "closure_certificate": str(ledger),
            "closure_certificate_record_sha256": record_sha,
            "closure_lean": "closures/binary-small.lean",
        }

    return solve


def test_successor_binds_outer_boundary_and_exact_prior_receipt() -> None:
    contract, outer, prior = _small_binary_task()
    formal_input = build_construction_artifact_formal_input(contract, outer, prior)
    assert formal_input["outer_boundary_result_sha256"] == outer["result_sha256"]
    assert formal_input["prior_open_discharge_receipt_sha256"] == prior.sha256
    assert formal_input["normalized_artifact"]["rows_hex"] == ["0x5", "0x6"]

    changed_prior = copy.deepcopy(prior.to_dict())
    changed_prior["observed"]["next_obligation"] = "resume_navigation"
    with pytest.raises(ValueError, match="replayed frontier adjudication"):
        build_construction_artifact_formal_input(contract, outer, changed_prior)

    changed_outer = copy.deepcopy(outer)
    changed_outer["stop_reason"] = "tampered"
    with pytest.raises(ValueError, match="digest"):
        build_construction_artifact_formal_input(contract, changed_outer, prior)


def test_formal_interface_freezes_semantic_theorem_and_proof_only() -> None:
    contract, outer, prior = _small_binary_task()
    formal_input = build_construction_artifact_formal_input(contract, outer, prior)
    interface = binary_construction_artifact_formal_interface(
        formal_input=formal_input
    )
    ratification_contract = build_construction_artifact_ratification_contract(
        contract, outer, prior, interface
    )
    proof = binary_construction_artifact_formal_certificate(
        ratification_contract=ratification_contract
    )
    closed, posed, carried, target = render_construction_artifact_certificate(
        ratification_contract, proof
    )
    assert target.startswith("AxiomPack.BinaryLinearCodeCertificate.certificate_")
    assert "Generator.mk" in interface["target_signature"]
    assert "Satisfies" in interface["target_signature"]
    assert formal_input["interface_sha256"] in interface["target_signature"]
    assert formal_input["target_config_sha256"] in interface["target_signature"]
    assert "theorem certificate_" in closed
    assert "sorry" not in closed
    assert "native_decide" not in closed
    assert "bv_decide" not in closed
    assert "ofReduceBool" not in closed
    assert "sorry" in posed
    assert carried.startswith("by\n  change Satisfies artifact_")
    assert "exact ⟨metadata_" in carried
    assert "blocks.all fun block" in interface["source_prefix"]
    assert formal_input["normalized_artifact_sha256"] in interface[
        "target_signature"
    ]
    assert formal_input["predicate_sha256"] in interface["target_signature"]

    with pytest.raises(ValueError, match="semantic theorem bridge"):
        build_construction_artifact_formal_interface(
            formal_input,
            adapter_id=ADAPTER_ID,
            certificate_capability_id="test_proof",
            target_selector="Demo.hashOnly",
            target_written_name="hashOnly",
            target_signature=': "abc" = "abc"',
            source_prefix="namespace Demo\n",
            source_suffix="end Demo\n",
            claim_predicate="Demo.Satisfies",
            artifact_constructor="Demo.Generator.mk",
        )


def test_formal_source_ceiling_returns_typed_pre_kernel_unavailability(
    tmp_path: Path, monkeypatch
) -> None:
    contract, outer, prior = _small_binary_task()
    formal_input = build_construction_artifact_formal_input(contract, outer, prior)
    calls = {"certificate": 0, "solver": 0}

    def certificate(**_kwargs):
        calls["certificate"] += 1
        raise AssertionError("source-ceiling failure reached certificate production")

    def solver(*_args, **_kwargs):
        calls["solver"] += 1
        raise AssertionError("source-ceiling failure reached governance")

    monkeypatch.setattr(
        construction_ratification_module,
        "_MAX_FORMAL_SOURCE_COMPONENT_BYTES",
        1,
    )
    result = ratify_construction_artifact_formal_input_action(
        formal_input,
        substrate=tmp_path,
        formal_interface_fn=binary_construction_artifact_formal_interface,
        formal_certificate_fn=certificate,
        governed_solve_fn=solver,
    )

    assert result["status"] == "unavailable"
    assert result["stage"] == "formal_interface"
    assert result["resource_unavailable"] == {
        "reason_code": "construction_formal_source_prefix_limit_exhausted",
        "resource": "construction_formal_source_prefix_bytes",
        "observed": result["resource_unavailable"]["observed"],
        "ceiling": 1,
    }
    assert result["resource_unavailable"]["observed"] > 1
    assert calls == {"certificate": 0, "solver": 0}


def test_formal_proof_ceiling_returns_typed_pre_kernel_unavailability(
    tmp_path: Path, monkeypatch
) -> None:
    contract, outer, prior = _small_binary_task()
    formal_input = build_construction_artifact_formal_input(contract, outer, prior)
    calls = {"solver": 0}

    def solver(*_args, **_kwargs):
        calls["solver"] += 1
        raise AssertionError("proof-ceiling failure reached governance")

    monkeypatch.setattr(
        construction_ratification_module,
        "_MAX_FORMAL_PROOF_BYTES",
        1,
    )
    result = ratify_construction_artifact_formal_input_action(
        formal_input,
        substrate=tmp_path,
        formal_interface_fn=binary_construction_artifact_formal_interface,
        formal_certificate_fn=binary_construction_artifact_formal_certificate,
        governed_solve_fn=solver,
    )

    assert result["status"] == "unavailable"
    assert result["stage"] == "formal_certificate"
    assert result["resource_unavailable"]["reason_code"] == (
        "construction_formal_proof_limit_exhausted"
    )
    assert result["resource_unavailable"]["resource"] == (
        "construction_formal_proof_bytes"
    )
    assert result["resource_unavailable"]["observed"] > 1
    assert result["resource_unavailable"]["ceiling"] == 1
    assert calls == {"solver": 0}


def test_closed_source_projection_returns_typed_pre_kernel_unavailability(
    tmp_path: Path, monkeypatch
) -> None:
    contract, outer, prior = _small_binary_task()
    formal_input = build_construction_artifact_formal_input(contract, outer, prior)
    calls = {"solver": 0}

    def solver(*_args, **_kwargs):
        calls["solver"] += 1
        raise AssertionError("closed-source ceiling reached governance")

    monkeypatch.setattr(
        construction_ratification_module,
        "_MAX_CLOSED_FORMAL_SOURCE_BYTES",
        1,
    )
    result = ratify_construction_artifact_formal_input_action(
        formal_input,
        substrate=tmp_path,
        formal_interface_fn=binary_construction_artifact_formal_interface,
        formal_certificate_fn=binary_construction_artifact_formal_certificate,
        governed_solve_fn=solver,
    )

    assert result["status"] == "unavailable"
    assert result["stage"] == "formal_certificate"
    assert result["resource_unavailable"]["reason_code"] == (
        "closed_construction_certificate_byte_limit_exhausted"
    )
    assert result["resource_unavailable"]["resource"] == (
        "closed_construction_certificate_bytes"
    )
    assert result["resource_unavailable"]["observed"] > 1
    assert result["resource_unavailable"]["ceiling"] == 1
    assert calls == {"solver": 0}


def test_formal_protocol_depth_returns_typed_pre_kernel_unavailability(
    tmp_path: Path, monkeypatch
) -> None:
    contract, outer, prior = _small_binary_task()
    formal_input = build_construction_artifact_formal_input(contract, outer, prior)
    interface = binary_construction_artifact_formal_interface(
        formal_input=formal_input
    )
    deep: list = []
    for _index in range(24):
        deep = [deep]
    malformed = {**interface, "fixture_deep": deep}
    calls = {"certificate": 0, "solver": 0}

    def certificate(**_kwargs):
        calls["certificate"] += 1
        raise AssertionError("depth failure reached certificate production")

    def solver(*_args, **_kwargs):
        calls["solver"] += 1
        raise AssertionError("depth failure reached governance")

    monkeypatch.setattr(
        construction_ratification_module,
        "_MAX_PROTOCOL_JSON_DEPTH",
        16,
    )
    result = ratify_construction_artifact_formal_input_action(
        formal_input,
        substrate=tmp_path,
        formal_interface_fn=lambda **_kwargs: malformed,
        formal_certificate_fn=certificate,
        governed_solve_fn=solver,
    )

    assert result["status"] == "unavailable"
    assert result["stage"] == "formal_interface"
    assert result["resource_unavailable"] == {
        "reason_code": "construction_formal_json_depth_limit_exhausted",
        "resource": "formal_protocol_json_depth",
        "observed": 17,
        "ceiling": 16,
    }
    assert calls == {"certificate": 0, "solver": 0}


def test_binary_small_certificate_is_kernel_reducible(
    tmp_path: Path,
) -> None:
    contract, outer, prior = _small_binary_task()
    formal_input = build_construction_artifact_formal_input(contract, outer, prior)
    interface = binary_construction_artifact_formal_interface(
        formal_input=formal_input
    )
    ratification_contract = build_construction_artifact_ratification_contract(
        contract, outer, prior, interface
    )
    proof = binary_construction_artifact_formal_certificate(
        ratification_contract=ratification_contract
    )
    closed, _posed, _carried, target = render_construction_artifact_certificate(
        ratification_contract, proof
    )
    source = closed + f"\n#print axioms {target}\n"
    path = tmp_path / "BinarySmallCertificate.lean"
    path.write_text(source, encoding="utf-8")
    completed = subprocess.run(
        ["lake", "env", "lean", str(path)],
        cwd=Path(__file__).resolve().parents[1] / "ztare_proofs",
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    transcript = completed.stdout + "\n" + completed.stderr
    assert completed.returncode == 0, transcript
    assert "sorryAx" not in transcript
    assert "depends on axioms: [propext]" in transcript
    assert "native_decide" not in source
    assert "bv_decide" not in source
    assert "ofReduceBool" not in source


def test_binary_chunked_certificate_larger_than_fixture_is_kernel_reducible(
    tmp_path: Path,
) -> None:
    dimension = 14
    parity = 1 << dimension
    matrix = BinaryGeneratorMatrix(
        length=dimension + 1,
        dimension=dimension,
        rows=tuple((1 << index) | parity for index in range(dimension)),
    )
    contract, outer, prior = _small_binary_task(
        matrix=matrix,
        minimum_distance=2,
        label="chunked-15-14-2",
    )
    formal_input = build_construction_artifact_formal_input(contract, outer, prior)
    interface = binary_construction_artifact_formal_interface(
        formal_input=formal_input
    )
    ratification_contract = build_construction_artifact_ratification_contract(
        contract, outer, prior, interface
    )
    proof = binary_construction_artifact_formal_certificate(
        ratification_contract=ratification_contract
    )
    closed, _posed, _carried, target = render_construction_artifact_certificate(
        ratification_contract, proof
    )
    assert interface["source_prefix"].count("= true := by decide") == 3
    assert " 1 8192 = true := by decide" in interface["source_prefix"]
    assert " 8193 8191 = true := by decide" in interface["source_prefix"]
    assert "blocks.all fun block" in interface["source_prefix"]
    source = closed + f"\n#print axioms {target}\n"
    assert all(
        shortcut not in source
        for shortcut in ("sorry", "admit", "native_decide", "bv_decide", "ofReduceBool")
    )
    path = tmp_path / "BinaryChunkedCertificate.lean"
    path.write_text(source, encoding="utf-8")
    completed = subprocess.run(
        ["lake", "env", "lean", str(path)],
        cwd=Path(__file__).resolve().parents[1] / "ztare_proofs",
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    transcript = completed.stdout + "\n" + completed.stderr
    assert completed.returncode == 0, transcript
    assert "depends on axioms: [propext]" in transcript
    assert "sorryAx" not in transcript
    assert "Lean.ofReduceBool" not in transcript


@pytest.mark.parametrize(
    "proof_text",
    ("by sorry", "by admit", "by native_decide", "ofReduceBool true rfl"),
)
def test_formal_certificate_rejects_trust_shortcuts(proof_text: str) -> None:
    from ztare.leanmill.construction_artifact_ratification import (
        build_construction_artifact_proof_receipt,
    )

    contract, outer, prior = _small_binary_task()
    formal_input = build_construction_artifact_formal_input(contract, outer, prior)
    interface = binary_construction_artifact_formal_interface(
        formal_input=formal_input
    )
    ratification_contract = build_construction_artifact_ratification_contract(
        contract, outer, prior, interface
    )
    with pytest.raises(ValueError, match="forbidden trust shortcut"):
        build_construction_artifact_proof_receipt(
            ratification_contract, proof_text=proof_text
        )


def test_python_acceptance_without_formal_capability_stays_open(tmp_path: Path) -> None:
    contract, outer, prior = _small_binary_task()

    def unavailable(**_kwargs):
        raise ConstructionArtifactRatificationCapabilityUnavailable(
            "formal_bridge_not_implemented"
        )

    aggregate = ratify_construction_artifact_action(
        contract,
        outer,
        prior,
        substrate=tmp_path,
        formal_interface_fn=unavailable,
        governed_solve_fn=lambda *_a, **_k: (_ for _ in ()).throw(
            AssertionError("Python verification must not enter theorem credit")
        ),
    )
    result = aggregate["ratification_result"]
    final = TaskDischargeReceipt.from_dict(
        aggregate["final_task_discharge_receipt"]
    )
    assert result["status"] == "unavailable"
    assert result["stage"] == "formal_interface"
    assert final.status == "open"
    assert final.observed["next_obligation"] == "construction_artifact_ratification"


def test_binary_formal_capability_accepts_dimension_14_and_rejects_15() -> None:
    contract, outer, prior = _small_binary_task()
    formal_input = build_construction_artifact_formal_input(contract, outer, prior)

    def retarget(dimension: int) -> dict:
        predicate = binary_code_predicate(
            length=dimension,
            dimension=dimension,
            minimum_distance=1,
            target_snapshot_sha256="d" * 64,
        )
        schema = binary_generator_matrix_schema(
            length=dimension, dimension=dimension
        )
        artifact = BinaryGeneratorMatrix(
            dimension,
            dimension,
            tuple(1 << index for index in range(dimension)),
        ).to_json()
        construction_interface = binary_witness_construction_interface(
            length=dimension,
            dimension=dimension,
            minimum_distance=1,
            target_snapshot_sha256="d" * 64,
            max_nonzero_messages=(1 << dimension) - 1,
            target_config_sha256="e" * 64,
        )
        row = {
            **formal_input,
            "interface_sha256": construction_interface["interface_sha256"],
            "target_config_sha256": "e" * 64,
            "predicate_ir": predicate,
            "predicate_sha256": content_hash(predicate),
            "witness_schema": schema,
            "witness_schema_sha256": content_hash(schema),
            "normalized_artifact": artifact,
            "normalized_artifact_sha256": content_hash(artifact),
        }
        core = {key: value for key, value in row.items() if key != "input_sha256"}
        return {**core, "input_sha256": content_hash(core)}

    accepted = binary_construction_artifact_formal_interface(
        formal_input=retarget(14)
    )
    assert accepted["source_prefix"].count("= true := by decide") == 3
    assert accepted["source_prefix"].count("theorem group_pass_") == 1
    assert BINARY_FORMAL_MAX_NONZERO_MESSAGES == 2**14 - 1
    with pytest.raises(
        ConstructionArtifactRatificationCapabilityUnavailable,
        match="message_bound_exceeded",
    ):
        binary_construction_artifact_formal_interface(formal_input=retarget(15))


def test_action_ratifies_once_without_provider_search_and_replays(tmp_path: Path) -> None:
    contract, outer, prior = _small_binary_task()
    prior_bytes = prior.to_dict()
    captured: dict = {}
    aggregate = ratify_construction_artifact_action(
        contract,
        outer,
        prior,
        substrate=tmp_path,
        governed_solve_fn=_successful_fake_solver(tmp_path, captured),
    )
    final = TaskDischargeReceipt.from_dict(
        aggregate["final_task_discharge_receipt"]
    )
    result = aggregate["ratification_result"]
    assert result["status"] == "ratified"
    assert final.status == "discharged"
    assert final.contract_sha256 == contract.sha256
    assert captured["kwargs"]["provider"] is None
    assert captured["kwargs"]["preverified_only"] is True
    assert captured["kwargs"]["require_positive_axiom_receipt"] is True
    assert captured["kwargs"]["preverified_provider"] == (
        "construction_artifact_certificate"
    )
    assert prior.to_dict() == prior_bytes
    assert validate_construction_artifact_ratification_aggregate(
        contract, outer, prior, aggregate
    ) == aggregate
    assert construction_artifact_ratification_filename(aggregate) == (
        "construction_artifact_ratification."
        + aggregate["aggregate_sha256"][:16]
        + ".json"
    )


def test_authoritative_replay_rejects_raw_solver_provider_calls(
    tmp_path: Path,
) -> None:
    contract, outer, prior = _small_binary_task()
    aggregate = ratify_construction_artifact_action(
        contract,
        outer,
        prior,
        substrate=tmp_path,
        governed_solve_fn=_successful_fake_solver(tmp_path, {}),
    )
    tampered = copy.deepcopy(aggregate["ratification_result"])
    tampered["governed_solver_result"]["provider_calls"] = 1
    core = {
        key: value for key, value in tampered.items() if key != "receipt_sha256"
    }
    tampered["receipt_sha256"] = content_hash(core)
    with pytest.raises(ValueError, match="provider-free solver outcome"):
        replay_ratified_construction_artifact_result(tampered)


def test_closed_solver_with_missing_certificate_digest_stays_open(
    tmp_path: Path,
) -> None:
    contract, outer, prior = _small_binary_task()
    successful = _successful_fake_solver(tmp_path, {})

    def missing_digest(target: str, posed: str, goal: str, **kwargs) -> dict:
        result = successful(target, posed, goal, **kwargs)
        result["closure_certificate_record_sha256"] = ""
        return result

    aggregate = ratify_construction_artifact_action(
        contract,
        outer,
        prior,
        substrate=tmp_path,
        governed_solve_fn=missing_digest,
    )
    result = aggregate["ratification_result"]
    assert result["status"] == "open"
    assert result["reason_code"] == (
        "governed_closure_evidence_rejected:ValueError"
    )
    assert result["closure_record_ref"] is None


def test_governance_rejection_stays_open_and_has_no_closure_credit(
    tmp_path: Path,
) -> None:
    contract, outer, prior = _small_binary_task()

    def rejected(_target, _posed, _goal, **kwargs):
        return {
            "results": [{
                "outcome": "rejected_governance",
                "proof_text": kwargs["preverified_proof"],
                "provider": "construction_artifact_certificate",
                "providers_tried": [{
                    "provider": "construction_artifact_certificate",
                    "agent_kind": "preverified_champion",
                }],
            }],
            "closure_certificate": None,
        }

    aggregate = ratify_construction_artifact_action(
        contract,
        outer,
        prior,
        substrate=tmp_path,
        governed_solve_fn=rejected,
    )
    result = aggregate["ratification_result"]
    final = TaskDischargeReceipt.from_dict(
        aggregate["final_task_discharge_receipt"]
    )
    assert result["status"] == "open"
    assert result["reason_code"] == "rejected_governance"
    assert result["closure_record_ref"] is None
    assert final.status == "open"


def test_nondeterministic_formal_producer_is_rejected_before_solver(
    tmp_path: Path,
) -> None:
    contract, outer, prior = _small_binary_task()
    counter = {"value": 0}

    def changing_interface(*, formal_input):
        counter["value"] += 1
        row = binary_construction_artifact_formal_interface(
            formal_input=formal_input
        )
        row["source_suffix"] += f"\n-- replay {counter['value']}\n"
        core = {key: value for key, value in row.items() if key != "interface_sha256"}
        row["interface_sha256"] = content_hash(core)
        return row

    with pytest.raises(ValueError, match="nondeterministic"):
        ratify_construction_artifact_action(
            contract,
            outer,
            prior,
            substrate=tmp_path,
            formal_interface_fn=changing_interface,
            governed_solve_fn=lambda *_a, **_k: (_ for _ in ()).throw(
                AssertionError("nondeterministic interface reached governance")
            ),
        )


def _ratification_campaign_fixture(tmp_path: Path):
    from test_theory_navigator import _context_and_blueprint

    contract, boundary, prior = _small_binary_task()
    program = TheoryProgram(
        campaign_id="campaign:binary-ratification",
        lineage_id="lineage:binary-ratification",
        context_hash=str(boundary["context_hash"]),
        context_epoch=0,
        presentation_formula_ids=("formula:binary-ratification",),
        prediction_formula_ids=(),
        selection_receipt_id="selection:binary-ratification",
        schema=THEORY_PROGRAM_V2,
        task_discharge_contracts=(contract,),
    )
    discharge_row_core = {
        "schema": "leanmill.theory_task_discharge_row.v1",
        "program_id": program.program_id,
        "source": "explicit_task",
        "contract": contract.to_dict(),
        "contract_sha256": contract.sha256,
        "receipt": prior.to_dict(),
    }
    discharge_row = {
        **discharge_row_core,
        "receipt_sha256": content_hash(discharge_row_core),
    }
    bundle_core = {
        "schema": "leanmill.theory_task_discharge.v1",
        "adapter_id": ADAPTER_ID,
        "boundary_result_sha256": boundary["result_sha256"],
        "rows": [discharge_row],
        "program_outcomes": {program.program_id: "open"},
        "explicit_program_status": "open",
        "authority": "registered_adapter_receipts_host_aggregation",
    }
    bundle = {**bundle_core, "receipt_sha256": content_hash(bundle_core)}
    completion_core = {
        "schema": "leanmill.frontier_boundary_completion.v1",
        "status": "campaign_completed",
        "attempt_dir": str(tmp_path),
        "context_hash": boundary["context_hash"],
        "boundary_result": boundary,
        "theory_task_discharge": bundle,
        "provider_calls": 0,
    }
    completion = {
        **completion_core,
        "completion_sha256": content_hash(completion_core),
    }
    synthesis = {
        "route": "proceed_boundary",
        "objective_contract": {
            "schema": "leanmill.frontier_objective_contract.v1",
            "instruction": "Construct and ratify the frozen binary code.",
        },
        "program_ids": [program.program_id],
    }
    run_core = {
        "schema": "leanmill.frontier_exploration_run.v1",
        "status": "frontier_candidates_frozen_awaiting_boundary_approval",
        "context_hash": boundary["context_hash"],
        "context_summary": {"context_epoch": 0},
        "navigation": {
            "context_epoch": 0,
            "finalists": [{
                "lineage_id": program.lineage_id,
                "theory_program": program.to_json(),
                "theory_program_id": program.program_id,
            }],
            "lineage_synthesis": synthesis,
        },
    }
    run = {**run_core, "run_digest": content_hash(run_core)}
    write_json_atomic(tmp_path / "run.json", run)
    write_json_atomic(tmp_path / "boundary_result.json", boundary)
    write_json_atomic(tmp_path / "theory_task_discharge.json", bundle)
    write_json_atomic(tmp_path / "boundary_completion.json", completion)
    _context, blueprint = _context_and_blueprint()
    write_json_atomic(tmp_path / "blueprint.json", blueprint.to_json())
    consumed = _consume_theory_task_discharge(tmp_path, run, completion)
    assert consumed["navigation"]["theory_task_discharge"]["objective_status"] == (
        "open"
    )
    return contract, boundary, prior, program, bundle, completion, consumed


def _lease_stub(context_hash: str):
    return SimpleNamespace(
        binding={"root_context_hash": context_hash},
        bind_epoch=lambda **_kwargs: None,
    )


def test_successor_bundle_preserves_and_replays_both_authorities(
    tmp_path: Path,
) -> None:
    contract, boundary, prior, program, bundle, _completion, _run = (
        _ratification_campaign_fixture(tmp_path)
    )
    aggregate = ratify_construction_artifact_action(
        contract,
        boundary,
        prior,
        substrate=tmp_path,
        governed_solve_fn=_successful_fake_solver(tmp_path, {}),
    )
    predecessor_bytes = copy.deepcopy(bundle)
    successor = build_construction_ratification_successor_bundle(
        bundle,
        boundary,
        [{
            "program_id": program.program_id,
            "task_contract_sha256": contract.sha256,
            "aggregate": aggregate,
        }],
    )
    assert bundle == predecessor_bytes
    assert successor["receipt_sha256"] != bundle["receipt_sha256"]
    assert successor["program_outcomes"][program.program_id] == "discharged"
    assert validate_construction_ratification_successor_bundle(
        successor, boundary
    ) == successor

    tampered = copy.deepcopy(successor)
    tampered["rows"][0]["receipt"]["status"] = "open"
    row_core = {
        key: value
        for key, value in tampered["rows"][0].items()
        if key != "receipt_sha256"
    }
    tampered["rows"][0]["receipt_sha256"] = content_hash(row_core)
    core = {key: value for key, value in tampered.items() if key != "receipt_sha256"}
    tampered["receipt_sha256"] = content_hash(core)
    with pytest.raises(ValueError, match="ratified task row"):
        validate_construction_ratification_successor_bundle(tampered, boundary)


def test_campaign_action_consumes_ratified_successor_once(
    tmp_path: Path,
) -> None:
    contract, boundary, prior, _program, bundle, completion, _run = (
        _ratification_campaign_fixture(tmp_path)
    )
    aggregate = ratify_construction_artifact_action(
        contract,
        boundary,
        prior,
        substrate=tmp_path,
        governed_solve_fn=_successful_fake_solver(tmp_path, {}),
    )
    calls = {"count": 0}

    def ratifier(*_args, **_kwargs):
        calls["count"] += 1
        return aggregate

    original_completion = copy.deepcopy(completion)
    result = execute_frontier_construction_artifact_ratification(
        tmp_path,
        lean_root=tmp_path,
        ratify_fn=ratifier,
        _attempt_lease=_lease_stub(str(boundary["context_hash"])),
    )
    assert result["status"] == "objective_discharged"
    assert calls["count"] == 1
    assert read_json(tmp_path / "boundary_completion.json", {}) == original_completion
    assert read_json(tmp_path / "theory_task_discharge.json", {}) == bundle
    closed = read_json(tmp_path / "run.json", {})
    consumption = closed["navigation"]["theory_task_discharge"]
    assert closed["status"] == "frontier_objective_discharged"
    assert consumption["predecessor_bundle_receipt_sha256"] == bundle["receipt_sha256"]
    assert consumption["objective_status"] == "discharged"
    assert list(tmp_path.glob("lineage_disposition.*.json"))
    assert not _pending_construction_artifact_ratifications(
        tmp_path, closed, original_completion
    )

    second = execute_frontier_construction_artifact_ratification(
        tmp_path,
        lean_root=tmp_path,
        ratify_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("ratification repeated after successor consumption")
        ),
        _attempt_lease=_lease_stub(str(boundary["context_hash"])),
    )
    assert second["status"] == "no_pending_construction_ratification"


def test_malformed_construction_ratification_conservatively_closes_reservation(
    tmp_path: Path,
) -> None:
    _contract, boundary, _prior, _program, _bundle, _completion, _run = (
        _ratification_campaign_fixture(tmp_path)
    )
    budget = budget_preset("smoke_20m")
    write_json_atomic(tmp_path / "budget.json", budget.to_json())

    with pytest.raises(ValueError):
        execute_frontier_construction_artifact_ratification(
            tmp_path,
            lean_root=tmp_path,
            ratify_fn=lambda *_args, **_kwargs: {},
            _attempt_lease=_lease_stub(str(boundary["context_hash"])),
        )

    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget,
        attempt_id=tmp_path.name,
    )
    state = ledger.state()
    assert state["reservations"] == {}
    assert state["usage"]["lean_attempts"] == 1
    assert ledger._strict_rows()[-1]["event_type"] == "wall_clock_frozen"


def test_construction_ratification_no_lease_entry_recurses_with_keywords(
    tmp_path: Path, monkeypatch
) -> None:
    from ztare.leanmill import frontier_campaign_runner as runner_module

    contract, boundary, prior, _program, _bundle, _completion, _run = (
        _ratification_campaign_fixture(tmp_path)
    )
    aggregate = ratify_construction_artifact_action(
        contract,
        boundary,
        prior,
        substrate=tmp_path,
        governed_solve_fn=_successful_fake_solver(tmp_path, {}),
    )

    @contextmanager
    def lease(_directory, *, action):
        assert action == "construction_artifact_ratification"
        yield _lease_stub(str(boundary["context_hash"]))

    monkeypatch.setattr(runner_module, "frontier_attempt_lease", lease)
    result = execute_frontier_construction_artifact_ratification(
        tmp_path,
        lean_root=tmp_path,
        ratify_fn=lambda *_args, **_kwargs: aggregate,
    )
    assert result["status"] == "objective_discharged"


def test_open_successor_routes_back_without_repeating_ratification(
    tmp_path: Path,
) -> None:
    contract, boundary, prior, _program, bundle, completion, _run = (
        _ratification_campaign_fixture(tmp_path)
    )

    def rejected(_target, _posed, _goal, **kwargs):
        return {
            "results": [{
                "outcome": "rejected_governance",
                "proof_text": kwargs["preverified_proof"],
                "provider": "construction_artifact_certificate",
                "providers_tried": [{
                    "provider": "construction_artifact_certificate",
                    "agent_kind": "preverified_champion",
                }],
            }],
            "closure_certificate": None,
        }

    aggregate = ratify_construction_artifact_action(
        contract,
        boundary,
        prior,
        substrate=tmp_path,
        governed_solve_fn=rejected,
    )
    result = execute_frontier_construction_artifact_ratification(
        tmp_path,
        lean_root=tmp_path,
        ratify_fn=lambda *_args, **_kwargs: aggregate,
        _attempt_lease=_lease_stub(str(boundary["context_hash"])),
    )
    assert result["status"] == "successor_consumed_open"
    current = read_json(tmp_path / "run.json", {})
    consumption = current["navigation"]["theory_task_discharge"]
    successor = consumption["successor_task_discharge"]
    assert consumption["objective_status"] == "open"
    assert successor["receipt_sha256"] != bundle["receipt_sha256"]
    observed = successor["rows"][0]["receipt"]["observed"]
    assert observed["reason_code"] == "rejected_governance"
    assert observed["next_obligation"] == "construction_artifact_ratification"
    assert not _pending_construction_artifact_ratifications(
        tmp_path, current, completion
    )
