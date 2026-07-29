from __future__ import annotations

from itertools import combinations
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from ztare.leanmill.ratification_policy import (
    TARGET_GOVERNANCE_AUTHORITIES,
    TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256,
)
from ztare.leanmill.solver.closed_artifact import finalize_solver_validation

from ztare.common.schema_routes import audit_project_schema_routes
from ztare.leanmill.axiompack_leaf_workbench import AXIOMPACK_LEAF_WORKBENCH_CONTRACT
from ztare.leanmill.common import (
    read_json,
    sha256_file,
    write_json_atomic,
    write_text_atomic,
)
from ztare.leanmill.exploration_budget import ExplorationBudgetLedger, budget_preset
from ztare.leanmill.external_science_admission import (
    EXTERNAL_REVIEW_SCHEMA,
    EXTERNAL_SEMANTIC_PROJECTION_SCHEMA,
    EXTERNAL_SCIENCE_REQUEST_SCHEMA,
    _formal_statement,
    _mapping_audit_context,
    _persist_review_request_core,
    _persist_review_supersession,
    _request_path,
    admit_external_science_recovery,
    external_science_negative_disposition_is_superseded,
    external_science_review_output_schema,
    external_science_review_prompt,
    materialize_external_science_formal_evidence,
    materialize_external_science_review_execution,
    materialize_external_science_resume_context,
    record_external_science_review_rejection,
)
from ztare.leanmill.finite_theory_context import save_formal_theory_context
from ztare.leanmill.formal_verification_provider import generate_keypair
from ztare.leanmill.frontier_campaign import packet_for_exact_context, sign_frontier_campaign
from ztare.leanmill.frontier_campaign_runner import (
    _pending_external_science_admission,
    deliver_external_science_resume_context,
    resume_frontier_campaign_navigation,
    run_external_science_recovery_admission,
)
from ztare.leanmill.frontier_agent_runtime import (
    FrontierAgentConfig,
    SubscriptionJSONRole,
)
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.theory_interest import CHEAP_CONSEQUENCE_EVALUATOR_REF
from ztare.leanmill.theory_program import TheoryProgram

from test_theory_navigator import _context_and_blueprint


def _artifact_ref(attempt: Path, relative: str) -> dict[str, str]:
    path = attempt / relative
    digest = sha256_file(path)
    assert digest is not None
    return {"root": "attempt", "path": relative, "sha256": digest}


def _write_jsonl(attempt: Path, relative: str, rows: list[dict]) -> Path:
    path = attempt / relative
    write_text_atomic(
        path,
        "".join(
            json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
            for row in rows
        ),
    )
    return path


def _settle_stub_transport(
    role,
    prefix: Path,
    *,
    prompt: str,
    stdout: str,
    stderr: str,
    returncode: int,
) -> None:
    """Exercise the same dispatch hooks/provenance contract as the CLI stub."""

    from ztare.common import subscription_agent_runtime as runtime

    hooks = runtime._DISPATCH_BUDGET_HOOKS.get()
    context = runtime._DISPATCH_PROVENANCE_CONTEXT.get()
    assert hooks is not None and hooks[2] is not None and context is not None
    reservation = hooks[0](role.config.runtime, ("fixture",))
    result = subprocess.CompletedProcess(
        ["fixture"], returncode, stdout=stdout, stderr=stderr
    )
    charged = bool(hooks[2](reservation, result))
    write_text_atomic(prefix.with_suffix(".stdout.txt"), stdout)
    write_text_atomic(prefix.with_suffix(".stderr.txt"), stderr)
    write_json_atomic(
        prefix.with_suffix(".dispatch.json"),
        {
            "schema": "ztare.owned_dispatch.v1",
            "call_id": f"fixture-{prefix.name}",
            "leader_pid": 910001 + len(role.calls),
            "pgid": 910001 + len(role.calls),
            "sid": 910001 + len(role.calls),
            "parent_pgid": 910000,
            "command_sha256": "sha256:" + "4" * 64,
            "stdin_sha256": "",
            "stdout_path": str(prefix.with_suffix(".stdout.txt").resolve()),
            "stderr_path": str(prefix.with_suffix(".stderr.txt").resolve()),
            "started_at_epoch": 1.0,
            "status": "completed",
            "returncode": returncode,
            "updated_at_epoch": 2.0,
        },
    )

    def raw_sha(value: str) -> str:
        return "sha256:" + hashlib.sha256(value.encode()).hexdigest()

    artifact_path = Path(context["artifact_dir"]) / f"fixture-{prefix.name}.json"
    core = {
        "schema": "ztare.subscription_dispatch_provenance.v1",
        "call_id": f"dispatch:fixture-{prefix.name}",
        "role": context["role"],
        "agent_id": context["agent_id"],
        "transport_agent_id": context["agent_id"],
        "run_tag": context["run_tag"],
        "runtime": role.config.runtime,
        "model": role.config.model,
        "reasoning_effort": context["reasoning_effort"],
        "config_sha256": context["config_sha256"],
        "command_sha256": "sha256:" + "5" * 64,
        "prompt_sha256": raw_sha(prompt),
        "stdout_sha256": raw_sha(stdout),
        "stderr_sha256": raw_sha(stderr),
        "result_sha256": raw_sha(f"{returncode}\n{stdout}\n{stderr}"),
        "session_id": "",
        "returncode": returncode,
        "timeout_seconds": role.config.timeout_seconds,
        "reservation_id": reservation.reservation_id,
        "reservation_action_id": reservation.action_id,
        "reservation_phase": reservation.phase,
        "reservation_resources": dict(reservation.resources),
        "charged_reservation": charged,
        "artifact_path": str(artifact_path.resolve()),
        "authority": "subscription_transport_post_commit_observation",
    }
    row = {**core, "receipt_sha256": content_hash(core)}
    write_json_atomic(artifact_path, row)
    context["collector"].append(row)


def _write_review_call(
    attempt: Path,
    request_core: dict,
    *,
    statement: str,
    statement_sha: str,
    anonymous_witness: dict,
    mapping_audit_context: dict,
    reviewer_ref: str | None = None,
    projection: dict | None = None,
    decision: str = "admit_for_resume_context",
    finite_witness_relevance: str = "statement_reviewed_against_preserved_witness",
) -> tuple[dict[str, str], dict[str, str]]:
    reviewer_ref = reviewer_ref or request_core["reviewer_ref"]
    projection = projection or {
        "schema": EXTERNAL_SEMANTIC_PROJECTION_SCHEMA,
        "result_shape": "universal implication",
        "abstract_summary": (
            "A checked implication connects the reviewed hypotheses to a stable "
            "operation law on arbitrary carriers."
        ),
        "hypothesis_shape": [
            "one operation with a pointwise preservation premise",
            "the reviewed finite chart supplies a nonempty witness",
        ],
        "conclusion_shape": "the same operation law holds for every input triple",
        "open_residuals": [
            "the campaign must decide how this result changes its own theory task",
            "classification and novelty remain unadjudicated",
        ],
        "next_discriminator": (
            "compile the reviewed result into a campaign-owned generalization task"
        ),
        "claim_boundary": "resume_context_only_pending_campaign_owned_discharge",
    }
    prompt = external_science_review_prompt(
        request_core_sha256=content_hash(request_core),
        formal_statement=statement,
        formal_statement_sha256=statement_sha,
        reviewed_presentation_formula_ids=list(
            request_core["reviewed_presentation_formula_ids"]
        ),
        anonymous_witness=anonymous_witness,
        submitted_by=request_core["submitted_by"],
        reviewer_ref=request_core["reviewer_ref"],
        mapping_audit_context=mapping_audit_context,
    )
    review = {
        "schema": EXTERNAL_REVIEW_SCHEMA,
        "author_ref": reviewer_ref,
        "decision": decision,
        "scope": "resume_context_only_no_objective_or_closure_credit",
        "reviewed_request_core_sha256": content_hash(request_core),
        "formal_statement_sha256": statement_sha,
        "reviewed_audit_context_sha256": mapping_audit_context[
            "audit_context_sha256"
        ],
        "finite_witness_relevance": finite_witness_relevance,
        "claim_boundary_acknowledged": True,
        "semantic_projection": projection,
    }
    call_dir = attempt / "agent_calls" / "external_science_reviewer"
    result_text = json.dumps(review, sort_keys=True, separators=(",", ":"))
    schema = external_science_review_output_schema()
    write_text_atomic(call_dir / "000.prompt.txt", prompt)
    write_text_atomic(call_dir / "000.result.json", result_text)
    write_text_atomic(call_dir / "000.stdout.txt", result_text)
    write_text_atomic(call_dir / "000.stderr.txt", "")
    write_json_atomic(call_dir / "000.schema.json", schema)
    write_json_atomic(
        call_dir / "000.call.json",
        {
            "schema": "leanmill.frontier_subscription_role_call.v1",
            "role": "external_science_reviewer",
            "agent_id": reviewer_ref,
            "runtime": "codex",
            "model": "fixture-model",
            "prompt_digest": content_hash({"prompt": prompt}),
            "returncode": 0,
            "provider_call_charge": 1,
            "wallclock_s": 1.0,
            "stdout_digest": content_hash({"stdout": result_text}),
            "stderr_digest": content_hash({"stderr": ""}),
            "result_digest": content_hash({"result": result_text}),
            "output_schema_digest": content_hash(schema),
        },
    )
    call_path = call_dir / "000.call.json"
    dispatch_path = call_dir / "000.dispatch.json"
    write_json_atomic(
        dispatch_path,
        {
            "schema": "ztare.owned_dispatch.v1",
            "call_id": "fixture-owned-dispatch",
            "leader_pid": 900001,
            "pgid": 900001,
            "sid": 900001,
            "parent_pgid": 900000,
            "command_sha256": "sha256:" + "1" * 64,
            "stdin_sha256": "",
            "stdout_path": str((call_dir / "000.stdout.txt").resolve()),
            "stderr_path": str((call_dir / "000.stderr.txt").resolve()),
            "started_at_epoch": 1.0,
            "status": "completed",
            "returncode": 0,
            "updated_at_epoch": 2.0,
        },
    )
    request_core_sha = content_hash(request_core)
    action_id = f"external_science_review:{request_core_sha[:16]}:000"
    ledger = ExplorationBudgetLedger(
        attempt / "budget.events.jsonl",
        budget_preset("smoke_20m"),
        attempt_id=attempt.name,
    )
    reservation = ledger.reserve(
        action_id,
        "interpretation",
        {"provider_calls": 1, "agent_turns": 1},
    )
    ledger.commit(reservation, {"provider_calls": 1, "agent_turns": 1})

    def raw_sha(value: str) -> str:
        return "sha256:" + hashlib.sha256(value.encode()).hexdigest()

    provenance_dir = call_dir / "transport"
    provenance_path = provenance_dir / "external_science_reviewer.fixture.json"
    provenance_core = {
        "schema": "ztare.subscription_dispatch_provenance.v1",
        "call_id": "dispatch:fixture",
        "role": "external_science_reviewer",
        "agent_id": reviewer_ref,
        "transport_agent_id": reviewer_ref,
        "run_tag": f"{attempt.name}:{action_id}",
        "runtime": "codex",
        "model": "fixture-model",
        "reasoning_effort": "medium",
        "config_sha256": "2" * 64,
        "command_sha256": "sha256:" + "3" * 64,
        "prompt_sha256": raw_sha(prompt),
        "stdout_sha256": raw_sha(result_text),
        "stderr_sha256": raw_sha(""),
        "result_sha256": raw_sha(f"0\n{result_text}\n"),
        "session_id": "",
        "returncode": 0,
        "timeout_seconds": 300,
        "reservation_id": reservation.reservation_id,
        "reservation_action_id": action_id,
        "reservation_phase": "interpretation",
        "reservation_resources": {"provider_calls": 1, "agent_turns": 1},
        "charged_reservation": True,
        "artifact_path": str(provenance_path.resolve()),
        "authority": "subscription_transport_post_commit_observation",
    }
    write_json_atomic(
        provenance_path,
        {**provenance_core, "receipt_sha256": content_hash(provenance_core)},
    )
    event_shas = [
        row["event_sha256"]
        for row in ledger._rows()
        if row.get("reservation_id") == reservation.reservation_id
    ]
    execution_ref = materialize_external_science_review_execution(
        attempt,
        request_core=request_core,
        reviewer_ref=reviewer_ref,
        prompt_digest=content_hash({"prompt": prompt}),
        action_id=action_id,
        outcome="review_completed",
        role_call_path=call_path,
        owned_dispatch_path=dispatch_path,
        transport_provenance_path=provenance_path,
        budget_reservation_id=reservation.reservation_id,
        budget_event_sha256s=event_shas,
    )
    return (
        _artifact_ref(
            attempt, "agent_calls/external_science_reviewer/000.call.json"
        ),
        execution_ref,
    )


def _request_fixture(tmp_path: Path) -> tuple[Path, dict, dict]:
    context, blueprint = _context_and_blueprint()
    attempt = tmp_path / "attempt-recovery"
    attempt.mkdir()
    save_formal_theory_context(context, attempt / "formal_context.json")
    write_json_atomic(attempt / "blueprint.json", blueprint.to_json())

    campaign_id = "campaign:external-recovery-test"
    packet = packet_for_exact_context(
        campaign_id=campaign_id,
        blueprint_id=blueprint.blueprint_id,
        eigenquestion=blueprint.eigenquestion,
        context=context,
        formula_grammar=blueprint.formula_grammar,
        pack_arity=blueprint.pack_arity,
        navigator_contract=AXIOMPACK_LEAF_WORKBENCH_CONTRACT,
        sealed_context_manifest_digest="sha256:" + "0" * 64,
        query_budget={"countermodels": 2},
        stop_rule={"freeze_before_interpretation": True},
    )
    private, public = generate_keypair()
    signed = sign_frontier_campaign(
        packet, private_key_pem=private, signer_ref="campaign-authority"
    )
    write_json_atomic(attempt / "campaign.json", signed.to_json())
    write_text_atomic(attempt / "campaign_signer_public.pem", public)

    pair = next(
        tuple(row)
        for row in combinations(context.formula_ids, 2)
        if context.extent_model_ids(row)
    )
    target_formula = next(item for item in context.formula_ids if item not in pair)
    program = TheoryProgram(
        campaign_id=campaign_id,
        lineage_id="theory-lineage:recovery-test",
        context_hash=context.context_hash,
        context_epoch=0,
        presentation_formula_ids=pair,
        prediction_formula_ids=(target_formula,),
        selection_receipt_id="selection:recovery-test",
    )
    run_core = {
        "status": "frontier_candidates_frozen_awaiting_boundary_approval",
        "context_hash": context.context_hash,
        "navigation": {
            "context_hash": context.context_hash,
            "context_epoch": 0,
            "finalists": [
                {
                    "theory_program_id": program.program_id,
                    "theory_program": program.to_json(),
                    "baseline_evaluator_ref": CHEAP_CONSEQUENCE_EVALUATOR_REF,
                }
            ],
        },
    }
    run = {**run_core, "run_digest": content_hash(run_core)}
    write_json_atomic(attempt / "run.json", run)

    source = (
        "import Mathlib\n\n"
        "namespace RecoveryFixture\n\n"
        "theorem finalistOneRecoveredResult {X : Type} "
        "(T : X → X → X → X)\n"
        "    (h : ∀ x y z, T x y z = y) : "
        "∀ x y z, T x y z = y := by\n"
        "  exact h\n\n"
        "end RecoveryFixture\n"
    )
    source_path = attempt / "evidence" / "result.lean"
    write_text_atomic(source_path, source)
    theorem_target = "RecoveryFixture.finalistOneRecoveredResult"
    statement = _formal_statement(source, theorem_target)
    statement_sha = content_hash({"formal_statement": statement})
    mapping_audit = _mapping_audit_context(
        context=context,
        reviewed_presentation_formula_ids=list(pair),
        source_text=source,
        theorem_target=theorem_target,
        formal_statement=statement,
    )
    governance = {
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
    receipt_bundle = finalize_solver_validation({
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
                "tail": "stripped control rejected",
            },
            "governance_kernel_receipt": {
                "available": True,
                "passed": True,
                "confirmed": [],
                "flags": [],
            },
            "axiom_allowlist_receipt": {
                "available": True,
                "passed": True,
                "axioms": ["propext"],
                "tail": "clean ['propext']",
            },
        },
        "credit_ready_at_solver_layer": True,
        "required_receipts_all_passed_at_solver_layer": True,
        "axiom_tier": "kernel_pure",
        "positive_axiom_receipt_required": True,
        "discriminating_mnc_required": True,
        "downstream_required": "leanmill_proof_audit",
    }, governance)
    job_id = "attempt-recovery-formal-1"
    run_tag = "run-recovery-formal-1"
    goal_hash = hashlib.sha256(b"").hexdigest()
    source_hash = hashlib.sha256(source.encode()).hexdigest()
    probe_hash = source_hash
    signature_hash = hashlib.sha256(statement.encode("utf-8")).hexdigest()
    parity_core = {
        "schema": "leanmill.kernel_parity_record.v2",
        "ts": "2026-07-18T00:00:00Z",
        "target": theorem_target,
        "job_id": job_id,
        "run_tag": run_tag,
        "goal_sha256": goal_hash,
        "source_sha256": source_hash,
        "recompilable_probe_sha256": probe_hash,
        "posed_target_signature_sha256": signature_hash,
        "closed_target_signature_sha256": signature_hash,
        "final_authority_roster_sha256": receipt_bundle[
            "final_authority_roster_sha256"
        ],
        "final_authority_disposition": receipt_bundle[
            "final_authority_disposition"
        ],
        "hand_wired": {"kc": True, "mnc": True},
        "kernel": {"available": True, "passed": True, "confirmed": []},
        "kernel_blocked": False,
        "toolchain_identity_sha256": "a" * 64,
        "environment_parity": {"attempted": False, "reason": "fixture"},
    }
    parity = {
        **parity_core,
        "record_sha256": content_hash(parity_core),
    }
    closure = {
        "certificate_schema": "leanmill.governed_closure.v2",
        "target": theorem_target,
        "job_id": job_id,
        "run_tag": run_tag,
        "goal_sha256": goal_hash,
        "source_sha256": source_hash,
        "recompilable_probe_sha256": probe_hash,
        "outcome": "closed",
        "checker": "lean_lake",
        "ratification_only": True,
        "recompilable_probe": source,
        "closure_lean": "evidence/result.lean",
        "matched_negative_control": {"available": True, "passed": True},
        "posed_target_signature_sha256": signature_hash,
        "closed_target_signature_sha256": signature_hash,
        "kernel_parity_record_sha256": parity["record_sha256"],
        "solver_validation": receipt_bundle,
        "governance": governance,
    }
    closure_path = _write_jsonl(
        attempt, "evidence/adhoc_closure_certificates.jsonl", [closure]
    )
    parity_path = _write_jsonl(attempt, "evidence/kernel_parity.jsonl", [parity])
    formal_ref = materialize_external_science_formal_evidence(
        attempt,
        source_path=source_path,
        theorem_target=theorem_target,
        closure_ledger_path=closure_path,
        kernel_parity_ledger_path=parity_path,
        repo_root=tmp_path,
    )
    write_text_atomic(
        attempt / "evidence" / "literature.md",
        "# Bounded literature audit\n\nThe exact implication boundary was reviewed.\n",
    )
    model_id = context.extent_model_ids(pair)[0]
    model = next(row for row in context.universe.models if row.model_id == model_id)
    request_core = {
        "schema": EXTERNAL_SCIENCE_REQUEST_SCHEMA,
        "attempt_id": attempt.name,
        "campaign_id": campaign_id,
        "campaign_packet_digest": packet.digest,
        "run_digest": run["run_digest"],
        "context_hash": context.context_hash,
        "context_epoch": 0,
        "lineage_id": program.lineage_id,
        "theory_program_id": program.program_id,
        "reviewed_presentation_formula_ids": list(pair),
        "finite_witness": {
            "model_id": model_id,
            "model_table_sha256": content_hash(model.model.to_json()),
        },
        "formal_artifact": formal_ref,
        "literature_audit": _artifact_ref(attempt, "evidence/literature.md"),
        "submitted_by": "recovery-author",
        "reviewer_ref": "external-science-reviewer:fixture",
    }
    review_ref, execution_ref = _write_review_call(
        attempt,
        request_core,
        statement=statement,
        statement_sha=statement_sha,
        anonymous_witness=model.model.to_json(),
        mapping_audit_context=mapping_audit,
    )
    request_without_digest = {
        **request_core,
        "independent_review": review_ref,
        "independent_review_execution": execution_ref,
    }
    request = {
        **request_without_digest,
        "request_sha256": content_hash(request_without_digest),
    }
    return attempt, request, {
        "context": context,
        "blueprint": blueprint,
        "campaign": signed.to_json(),
        "program": program,
        "target_formula": target_formula,
        "model": model,
        "model_id": model_id,
        "theorem_target": theorem_target,
        "source_path": "evidence/result.lean",
        "closure_path": closure_path,
        "parity_path": parity_path,
        "statement": statement,
        "statement_sha": statement_sha,
        "mapping_audit": mapping_audit,
    }


def _rebind_review(attempt: Path, request: dict, fixture: dict, **kwargs) -> dict:
    core = {
        key: value
        for key, value in request.items()
        if key
        not in {
            "independent_review",
            "independent_review_execution",
            "request_sha256",
        }
    }
    ref, execution_ref = _write_review_call(
        attempt,
        core,
        statement=fixture["statement"],
        statement_sha=fixture["statement_sha"],
        anonymous_witness=fixture["model"].model.to_json(),
        mapping_audit_context=fixture["mapping_audit"],
        **kwargs,
    )
    without_digest = {
        **core,
        "independent_review": ref,
        "independent_review_execution": execution_ref,
    }
    return {**without_digest, "request_sha256": content_hash(without_digest)}


def _route(attempt: Path, route_id: str) -> dict:
    return next(
        row
        for row in audit_project_schema_routes(attempt)["routes"]
        if row["route_id"] == route_id
    )


def test_external_science_delivery_is_resume_only_and_source_free(tmp_path) -> None:
    attempt, request, sensitive = _request_fixture(tmp_path)
    admission = admit_external_science_recovery(attempt, request, repo_root=tmp_path)

    assert _route(
        attempt, "external_science_admission_to_resume_projection.v1"
    )["unconsumed_count"] == 1
    resume = deliver_external_science_resume_context(attempt, admission)

    assert admission["authority"] == "resume_context_only"
    assert admission["reviewer_ref"] == request["reviewer_ref"]
    assert admission["outer_objective_credit"].startswith("withheld")
    assert admission["campaign_closure"] == "forbidden"
    assert admission["theory_task_discharge"] == "forbidden"
    rendered = repr(resume)
    for identity in (
        sensitive["model_id"],
        sensitive["theorem_target"],
        sensitive["source_path"],
        sensitive["statement"],
        admission["admission_sha256"],
    ):
        assert identity not in rendered
    assert "formal_statement" not in resume
    assert "evidence_bindings" not in resume
    assert "finite_witness_model_id" not in resume
    run = read_json(attempt / "run.json", {})
    assert run["status"] == "frontier_leaf_decision_pending"
    assert "theory_task_discharge" not in run["navigation"]
    checkpoint = read_json(attempt / "navigation_epoch_checkpoint.json", {})
    assert checkpoint["trace"][-1]["receipt"] == resume
    assert deliver_external_science_resume_context(attempt, admission) == resume

    # A later navigation wave may rematerialize its run view without this
    # convenience index. Durable first-fire identity still prevents redelivery.
    run = read_json(attempt / "run.json", {})
    navigation = dict(run["navigation"])
    navigation.pop("external_science_resume_context_by_lineage")
    core = {
        **{key: value for key, value in run.items() if key != "run_digest"},
        "navigation": navigation,
    }
    write_json_atomic(
        attempt / "run.json", {**core, "run_digest": content_hash(core)}
    )
    assert _pending_external_science_admission(
        attempt, read_json(attempt / "run.json", {})
    ) is None

    # Once first-fired, the one-shot admission remains a historical receipt
    # even after navigation legitimately retires or replaces its source lineage.
    run = read_json(attempt / "run.json", {})
    navigation = dict(run["navigation"])
    navigation["objective_survivors"] = []
    navigation["finalists"] = []
    core = {
        **{key: value for key, value in run.items() if key != "run_digest"},
        "navigation": navigation,
    }
    write_json_atomic(
        attempt / "run.json", {**core, "run_digest": content_hash(core)}
    )
    assert _pending_external_science_admission(
        attempt, read_json(attempt / "run.json", {})
    ) is None
    assert _route(
        attempt, "external_science_admission_to_resume_projection.v1"
    )["unconsumed_count"] == 0
    assert _route(
        attempt, "external_science_resume_context_to_navigation.v1"
    )["unconsumed_count"] == 0


def test_external_science_admission_rejects_model_table_drift(tmp_path) -> None:
    attempt, request, fixture = _request_fixture(tmp_path)
    request["finite_witness"]["model_table_sha256"] = "f" * 64
    request = _rebind_review(attempt, request, fixture)

    with pytest.raises(ValueError, match="finite witness does not replay"):
        admit_external_science_recovery(attempt, request, repo_root=tmp_path)


def test_external_science_admission_rejects_forged_canonical_receipt(tmp_path) -> None:
    attempt, request, _fixture = _request_fixture(tmp_path)
    formal = read_json(attempt / request["formal_artifact"]["path"], {})
    ledger = attempt / formal["closure_certificate"]["path"]
    row = json.loads(ledger.read_text(encoding="utf-8"))
    row["solver_validation"]["receipts"]["axiom_allowlist_receipt"]["passed"] = False
    _write_jsonl(attempt, formal["closure_certificate"]["path"], [row])

    with pytest.raises(ValueError, match="canonical record"):
        admit_external_science_recovery(attempt, request, repo_root=tmp_path)


def test_formal_evidence_rejects_independently_valid_crossed_parity_row(
    tmp_path,
) -> None:
    attempt, _request, fixture = _request_fixture(tmp_path)
    parity = json.loads(
        fixture["parity_path"].read_text(encoding="utf-8").strip()
    )
    crossed_core = {
        key: value for key, value in parity.items() if key != "record_sha256"
    }
    crossed_core["job_id"] = "attempt-crossed-parity"
    crossed_core["run_tag"] = "run-crossed-parity"
    crossed = {
        **crossed_core,
        "record_sha256": content_hash(crossed_core),
    }
    _write_jsonl(
        attempt,
        "evidence/crossed_kernel_parity.jsonl",
        [crossed],
    )

    with pytest.raises(
        ValueError,
        match="no closure-bound kernel parity record",
    ):
        materialize_external_science_formal_evidence(
            attempt,
            source_path=attempt / fixture["source_path"],
            theorem_target=fixture["theorem_target"],
            closure_ledger_path=fixture["closure_path"],
            kernel_parity_ledger_path=(
                attempt / "evidence/crossed_kernel_parity.jsonl"
            ),
            repo_root=tmp_path,
        )


def test_external_science_admission_rejects_self_review(tmp_path) -> None:
    attempt, request, fixture = _request_fixture(tmp_path)
    request["reviewer_ref"] = request["submitted_by"]
    request = _rebind_review(
        attempt,
        request,
        fixture,
        reviewer_ref=request["submitted_by"],
    )

    with pytest.raises(ValueError, match="independent review"):
        admit_external_science_recovery(attempt, request, repo_root=tmp_path)


def test_external_science_admission_cannot_promote_reviewer_rejection(
    tmp_path,
) -> None:
    attempt, request, fixture = _request_fixture(tmp_path)
    request = _rebind_review(
        attempt,
        request,
        fixture,
        decision="reject",
        finite_witness_relevance="not_established",
    )

    with pytest.raises(ValueError, match="did not authorize admission"):
        admit_external_science_recovery(attempt, request, repo_root=tmp_path)


def test_external_science_admission_rejects_source_identity_in_review(tmp_path) -> None:
    attempt, request, fixture = _request_fixture(tmp_path)
    projection = {
        "schema": EXTERNAL_SEMANTIC_PROJECTION_SCHEMA,
        "result_shape": "universal implication",
        "abstract_summary": "Replays finalistOneRecoveredResult.",
        "hypothesis_shape": ["reviewed assumptions"],
        "conclusion_shape": "a stable law",
        "open_residuals": ["campaign discharge remains"],
        "next_discriminator": "resume the campaign",
        "claim_boundary": "resume_context_only_pending_campaign_owned_discharge",
    }
    request = _rebind_review(attempt, request, fixture, projection=projection)

    with pytest.raises(ValueError, match="bound source identity"):
        admit_external_science_recovery(attempt, request, repo_root=tmp_path)


def test_external_science_projection_allows_benign_mathematical_slash(
    tmp_path,
) -> None:
    attempt, request, fixture = _request_fixture(tmp_path)
    projection = {
        "schema": EXTERNAL_SEMANTIC_PROJECTION_SCHEMA,
        "result_shape": "orbit implication",
        "abstract_summary": (
            "The quotient/action description records the reviewed operation law."
        ),
        "hypothesis_shape": ["the frozen operation identities hold"],
        "conclusion_shape": "an orbit action supplies the derived law",
        "open_residuals": ["campaign-owned discharge remains pending"],
        "next_discriminator": "test the next abstract classification residual",
        "claim_boundary": (
            "resume_context_only_pending_campaign_owned_discharge"
        ),
    }
    request = _rebind_review(attempt, request, fixture, projection=projection)

    admission = admit_external_science_recovery(
        attempt, request, repo_root=tmp_path
    )

    assert "quotient/action" in admission["semantic_projection"]["abstract_summary"]


def test_external_science_projection_rejects_path_like_token(tmp_path) -> None:
    attempt, request, fixture = _request_fixture(tmp_path)
    projection = {
        "schema": EXTERNAL_SEMANTIC_PROJECTION_SCHEMA,
        "result_shape": "universal implication",
        "abstract_summary": "Consult private/audit/context.json for the mapping.",
        "hypothesis_shape": ["reviewed assumptions"],
        "conclusion_shape": "a stable operation law",
        "open_residuals": ["campaign discharge remains pending"],
        "next_discriminator": "resume abstract classification",
        "claim_boundary": "resume_context_only_pending_campaign_owned_discharge",
    }
    request = _rebind_review(attempt, request, fixture, projection=projection)

    with pytest.raises(ValueError, match="audit identity"):
        admit_external_science_recovery(attempt, request, repo_root=tmp_path)


def test_reviewer_packet_contains_bound_campaign_to_formal_mapping(tmp_path) -> None:
    attempt, request, fixture = _request_fixture(tmp_path)
    prompt_path = attempt / request["independent_review"]["path"]
    prompt_path = prompt_path.with_name("000.prompt.txt")
    packet = json.loads(
        prompt_path.read_text(encoding="utf-8").split(
            "FROZEN REVIEW INPUT:\n", 1
        )[1]
    )
    audit = packet["mapping_audit_context"]
    audit_core = {
        key: value for key, value in audit.items() if key != "audit_context_sha256"
    }

    assert packet["reviewer_ref"] == request["reviewer_ref"]
    assert audit["audit_context_sha256"] == content_hash(audit_core)
    laws = audit["campaign_law_semantics"]
    assert [
        row["formula_id"] for row in laws["presentation_axioms"]
    ] == list(fixture["program"].presentation_formula_ids)
    assert all(row["axiom"]["formula"] for row in laws["presentation_axioms"])
    declaration = audit["formal_declaration_context"]
    assert fixture["theorem_target"].rsplit(".", 1)[-1] in declaration[
        "source_through_target"
    ]
    assert declaration["formal_statement"] == fixture["statement"]
    assert declaration["source_through_target_sha256"] == content_hash(
        {"source_through_target": declaration["source_through_target"]}
    )


def test_resume_rejects_stale_run_and_refined_lineage(tmp_path) -> None:
    attempt, request, fixture = _request_fixture(tmp_path)
    admission = admit_external_science_recovery(attempt, request, repo_root=tmp_path)
    run = read_json(attempt / "run.json", {})
    stale_core = {
        **{key: value for key, value in run.items() if key != "run_digest"},
        "stale_marker": True,
    }
    write_json_atomic(
        attempt / "run.json",
        {**stale_core, "run_digest": content_hash(stale_core)},
    )
    with pytest.raises(ValueError, match="current run"):
        materialize_external_science_resume_context(attempt, admission)

    write_json_atomic(attempt / "run.json", run)
    deliver_external_science_resume_context(attempt, admission)
    run = read_json(attempt / "run.json", {})
    program = fixture["program"]
    refined = TheoryProgram(
        campaign_id=program.campaign_id,
        lineage_id=program.lineage_id,
        context_hash=program.context_hash,
        context_epoch=program.context_epoch,
        presentation_formula_ids=(program.presentation_formula_ids[0],),
        prediction_formula_ids=(fixture["target_formula"],),
        selection_receipt_id="selection:refined",
    )
    navigation = dict(run["navigation"])
    navigation["objective_survivors"] = [
        {"theory_program_id": refined.program_id, "theory_program": refined.to_json()}
    ]
    refined_core = {
        **{key: value for key, value in run.items() if key != "run_digest"},
        "navigation": navigation,
    }
    write_json_atomic(
        attempt / "run.json",
        {**refined_core, "run_digest": content_hash(refined_core)},
    )
    with pytest.raises(ValueError, match="current lineage"):
        deliver_external_science_resume_context(attempt, admission)


def test_resume_rejects_recomputed_admission_tamper(tmp_path) -> None:
    attempt, request, _fixture = _request_fixture(tmp_path)
    admission = admit_external_science_recovery(attempt, request, repo_root=tmp_path)
    tampered_core = {
        key: value for key, value in admission.items() if key != "admission_sha256"
    }
    tampered_core["semantic_projection"] = {
        **tampered_core["semantic_projection"],
        "abstract_summary": "A caller-authored replacement.",
    }
    tampered_core["semantic_projection_sha256"] = content_hash(
        tampered_core["semantic_projection"]
    )
    tampered = {**tampered_core, "admission_sha256": content_hash(tampered_core)}
    write_json_atomic(
        attempt
        / f"external_science_resume_admission.{tampered['admission_sha256'][:16]}.json",
        tampered,
    )

    with pytest.raises(ValueError, match="governed evidence"):
        materialize_external_science_resume_context(attempt, tampered)


def test_stopped_boundary_admission_is_delivered_before_resume_early_return(
    tmp_path, monkeypatch
) -> None:
    attempt, request, fixture = _request_fixture(tmp_path)
    admission = admit_external_science_recovery(attempt, request, repo_root=tmp_path)
    assert admission
    write_json_atomic(
        attempt / "boundary_completion.json",
        {
            "boundary_result": {
                "stop_reason": "blocked_before_action:smt_calls",
                "query_results": [],
            }
        },
    )

    budget = budget_preset("smoke_20m")
    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner._load_campaign_attempt",
        lambda _directory: (
            None,
            fixture["blueprint"],
            budget.to_json(),
            fixture["campaign"],
            fixture["context"],
        ),
    )

    class ExhaustedLedger:
        def __init__(self, *_args, **_kwargs):
            pass

        def recover_interrupted_wall_clock(self):
            return None

        def recover_interrupted_reservations(self):
            return None

        def resume_wall_clock(self):
            return None

        def remaining_capacity(self, *_args):
            return 0

        def freeze_wall_clock(self, **_kwargs):
            return None

    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.ExplorationBudgetLedger",
        ExhaustedLedger,
    )
    resume_frontier_campaign_navigation(attempt)

    run = read_json(attempt / "run.json", {})
    assert run["status"] == "frontier_leaf_decision_pending"
    assert run["navigation"]["external_science_resume_context_by_lineage"]
    assert _route(
        attempt, "external_science_resume_context_to_navigation.v1"
    )["unconsumed_count"] == 0


def test_stopped_boundary_negative_disposition_precedes_resume_early_return(
    tmp_path, monkeypatch
) -> None:
    attempt, request, fixture = _request_fixture(tmp_path)
    request = _rebind_review(
        attempt,
        request,
        fixture,
        decision="reject",
        finite_witness_relevance="not_established",
    )
    disposition = record_external_science_review_rejection(
        attempt, request, repo_root=tmp_path
    )
    assert disposition["outcome"] == "review_rejected"
    write_json_atomic(
        attempt / "boundary_completion.json",
        {
            "boundary_result": {
                "stop_reason": "blocked_before_action:smt_calls",
                "query_results": [],
            }
        },
    )
    budget = budget_preset("smoke_20m")
    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner._load_campaign_attempt",
        lambda _directory: (
            None,
            fixture["blueprint"],
            budget.to_json(),
            fixture["campaign"],
            fixture["context"],
        ),
    )

    class ExhaustedLedger:
        def __init__(self, *_args, **_kwargs):
            pass

        def recover_interrupted_wall_clock(self):
            return None

        def recover_interrupted_reservations(self):
            return None

        def resume_wall_clock(self):
            return None

        def remaining_capacity(self, *_args):
            return 0

        def freeze_wall_clock(self, **_kwargs):
            return None

    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.ExplorationBudgetLedger",
        ExhaustedLedger,
    )
    resume_frontier_campaign_navigation(attempt)

    run = read_json(attempt / "run.json", {})
    assert run["status"] == "frontier_leaf_decision_pending"
    assert run["navigation"]["external_science_negative_dispositions"]
    assert _route(
        attempt, "external_science_negative_disposition_to_navigation.v1"
    )["unconsumed_count"] == 0


def test_recovery_orchestrator_charges_independent_review_and_first_fires(
    tmp_path, monkeypatch
) -> None:
    attempt, _request, fixture = _request_fixture(tmp_path)
    shutil.rmtree(attempt / "agent_calls" / "external_science_reviewer")
    (attempt / "budget.events.jsonl").unlink()
    budget = budget_preset("smoke_20m")
    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner._load_campaign_attempt",
        lambda _directory: (
            object(),
            fixture["blueprint"],
            budget.to_json(),
            fixture["campaign"],
            fixture["context"],
        ),
    )

    class ReviewerRole:
        def __init__(self, artifact_dir: Path) -> None:
            self.config = FrontierAgentConfig(runtime="codex", model="fixture-model")
            self.artifact_dir = artifact_dir / "external_science_reviewer"
            self.agent_id = "external-science-reviewer:independent-fixture"
            self.calls: list[dict] = []
            self.budget_ledger = None

        @property
        def provider_call_count(self) -> int:
            return sum(
                int(row.get("provider_call_charge", 0)) for row in self.calls
            )

        def __call__(self, prompt: str) -> dict:
            packet = json.loads(prompt.split("FROZEN REVIEW INPUT:\n", 1)[1])
            projection = {
                "schema": EXTERNAL_SEMANTIC_PROJECTION_SCHEMA,
                "result_shape": "universal implication",
                "abstract_summary": (
                    "A reviewed implication links the frozen hypotheses to a "
                    "stable operation law on arbitrary carriers."
                ),
                "hypothesis_shape": [
                    "a ternary operation obeys the reviewed preservation laws",
                    "an anonymous finite chart witnesses nonempty compatibility",
                ],
                "conclusion_shape": (
                    "the derived operation law holds for every input triple"
                ),
                "open_residuals": [
                    "campaign-owned task discharge remains pending",
                    "classification and novelty remain under adjudication",
                ],
                "next_discriminator": (
                    "test the abstract law against the campaign's next theory task"
                ),
                "claim_boundary": (
                    "resume_context_only_pending_campaign_owned_discharge"
                ),
            }
            review = {
                "schema": EXTERNAL_REVIEW_SCHEMA,
                "author_ref": packet["reviewer_ref"],
                "decision": "admit_for_resume_context",
                "scope": "resume_context_only_no_objective_or_closure_credit",
                "reviewed_request_core_sha256": packet["request_core_sha256"],
                "formal_statement_sha256": packet["formal_statement_sha256"],
                "reviewed_audit_context_sha256": packet[
                    "mapping_audit_context"
                ]["audit_context_sha256"],
                "finite_witness_relevance": (
                    "statement_reviewed_against_preserved_witness"
                ),
                "claim_boundary_acknowledged": True,
                "semantic_projection": projection,
            }
            result_text = json.dumps(review, sort_keys=True, separators=(",", ":"))
            schema = external_science_review_output_schema()
            failed_prefix = self.artifact_dir / "000"
            write_text_atomic(failed_prefix.with_suffix(".prompt.txt"), prompt)
            write_json_atomic(failed_prefix.with_suffix(".schema.json"), schema)
            _settle_stub_transport(
                self,
                failed_prefix,
                prompt=prompt,
                stdout="",
                stderr="invalid_json_schema",
                returncode=1,
            )
            failed_call = {
                "schema": "leanmill.frontier_subscription_role_call.v1",
                "role": "external_science_reviewer",
                "agent_id": self.agent_id,
                "runtime": self.config.runtime,
                "model": self.config.model,
                "prompt_digest": content_hash({"prompt": prompt}),
                "returncode": 1,
                "provider_call_charge": 0,
                "wallclock_s": 0.01,
                "stdout_digest": content_hash({"stdout": ""}),
                "stderr_digest": content_hash({"stderr": "invalid_json_schema"}),
                "result_digest": "",
                "output_schema_digest": content_hash(schema),
            }
            write_json_atomic(failed_prefix.with_suffix(".call.json"), failed_call)
            self.calls.append(failed_call)
            prefix = self.artifact_dir / "001"
            write_text_atomic(prefix.with_suffix(".prompt.txt"), prompt)
            write_text_atomic(prefix.with_suffix(".result.json"), result_text)
            write_json_atomic(prefix.with_suffix(".schema.json"), schema)
            _settle_stub_transport(
                self,
                prefix,
                prompt=prompt,
                stdout=result_text,
                stderr="",
                returncode=0,
            )
            call = {
                "schema": "leanmill.frontier_subscription_role_call.v1",
                "role": "external_science_reviewer",
                "agent_id": self.agent_id,
                "runtime": self.config.runtime,
                "model": self.config.model,
                "prompt_digest": content_hash({"prompt": prompt}),
                "returncode": 0,
                "provider_call_charge": 1,
                "wallclock_s": 0.01,
                "stdout_digest": content_hash({"stdout": result_text}),
                "stderr_digest": content_hash({"stderr": ""}),
                "result_digest": content_hash({"result": result_text}),
                "output_schema_digest": content_hash(schema),
            }
            write_json_atomic(prefix.with_suffix(".call.json"), call)
            self.calls.append(call)
            return review

    roles: list[ReviewerRole] = []

    def make_role(_definition, *, role_name, repo, artifact_dir, **_kwargs):
        assert role_name == "external_science_reviewer"
        assert repo == tmp_path.resolve()
        role = ReviewerRole(artifact_dir)
        roles.append(role)
        return role

    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.frontier_agent_role", make_role
    )
    completion = run_external_science_recovery_admission(
        attempt,
        source_path=attempt / fixture["source_path"],
        theorem_target=fixture["theorem_target"],
        finite_witness_model_id=fixture["model_id"],
        literature_audit_path=attempt / "evidence/literature.md",
        lineage_id=fixture["program"].lineage_id,
        submitted_by="recovery-author",
        closure_ledger_path=fixture["closure_path"],
        kernel_parity_ledger_path=fixture["parity_path"],
        model="fixture-model",
        repo=tmp_path,
    )

    assert completion["review_provider_calls"] == 1
    assert completion["replayed"] is False
    assert completion["receipt_sha256"] == content_hash(
        {key: value for key, value in completion.items() if key != "receipt_sha256"}
    )
    assert len(roles) == 1 and roles[0].provider_call_count == 1
    events = [
        json.loads(line)
        for line in (attempt / "budget.events.jsonl").read_text().splitlines()
    ]
    committed = [
        row
        for row in events
        if row.get("event_type") == "reservation_committed"
    ]
    assert len(committed) == 1
    assert committed[0]["actual_resources"] == {
        "agent_turns": 1,
        "provider_calls": 1,
    }
    run = read_json(attempt / "run.json", {})
    assert run["status"] == "frontier_leaf_decision_pending"
    assert "theory_task_discharge" not in run["navigation"]
    assert not (attempt / "boundary_completion.json").is_file()
    assert _route(
        attempt, "external_science_resume_context_to_navigation.v1"
    )["unconsumed_count"] == 0

    replay = run_external_science_recovery_admission(
        attempt,
        source_path=attempt / fixture["source_path"],
        theorem_target=fixture["theorem_target"],
        finite_witness_model_id=fixture["model_id"],
        literature_audit_path=attempt / "evidence/literature.md",
        lineage_id=fixture["program"].lineage_id,
        submitted_by="recovery-author",
        closure_ledger_path=fixture["closure_path"],
        kernel_parity_ledger_path=fixture["parity_path"],
        model="fixture-model",
        repo=tmp_path,
    )
    assert replay["replayed"] is True
    assert replay["review_provider_calls"] == 0
    assert "receipt_sha256" in replay
    events_after = [
        json.loads(line)
        for line in (attempt / "budget.events.jsonl").read_text().splitlines()
    ]
    assert sum(
        row.get("event_type") == "reservation_committed" for row in events_after
    ) == 1


def test_reviewer_rejection_becomes_resumable_no_credit_navigation_input(
    tmp_path, monkeypatch
) -> None:
    attempt, request, fixture = _request_fixture(tmp_path)
    request = _rebind_review(
        attempt,
        request,
        fixture,
        decision="reject",
        finite_witness_relevance="not_established",
    )
    budget = budget_preset("smoke_20m")
    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner._load_campaign_attempt",
        lambda _directory: (
            object(),
            fixture["blueprint"],
            budget.to_json(),
            fixture["campaign"],
            fixture["context"],
        ),
    )

    def make_role(_definition, *, role_name, repo, artifact_dir, **_kwargs):
        return SubscriptionJSONRole(
            role=role_name,
            agent_id=request["reviewer_ref"],
            repo=repo,
            artifact_dir=artifact_dir / role_name,
            config=FrontierAgentConfig(runtime="codex", model="fixture-model"),
            output_schema=external_science_review_output_schema(),
        )

    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.frontier_agent_role", make_role
    )
    completion = run_external_science_recovery_admission(
        attempt,
        source_path=attempt / fixture["source_path"],
        theorem_target=fixture["theorem_target"],
        finite_witness_model_id=fixture["model_id"],
        literature_audit_path=attempt / "evidence/literature.md",
        lineage_id=fixture["program"].lineage_id,
        submitted_by="recovery-author",
        closure_ledger_path=fixture["closure_path"],
        kernel_parity_ledger_path=fixture["parity_path"],
        model="fixture-model",
        repo=tmp_path,
    )

    assert completion["schema"].endswith("negative_completion.v1")
    assert completion["outcome"] == "review_rejected"
    assert completion["review_provider_calls"] == 0
    run = read_json(attempt / "run.json", {})
    assert run["status"] == "frontier_leaf_decision_pending"
    disposition = run["navigation"]["external_science_negative_dispositions"][-1]
    assert disposition["projection_authority"] == "independent_reviewer"
    assert disposition["outer_objective_credit"].startswith("withheld")
    assert disposition["campaign_closure"] == "forbidden"
    assert disposition["theory_task_discharge"] == "forbidden"
    checkpoint = read_json(attempt / "navigation_epoch_checkpoint.json", {})
    assert checkpoint["trace"][-1]["decision"] == (
        "external_science_negative_disposition"
    )
    assert not list(attempt.glob("external_science_resume_admission.*.json"))
    assert _route(
        attempt, "external_science_negative_disposition_to_navigation.v1"
    )["unconsumed_count"] == 0


def test_retryable_reviewer_unavailability_becomes_resumable_typed_input(
    tmp_path, monkeypatch
) -> None:
    attempt, request, fixture = _request_fixture(tmp_path)
    shutil.rmtree(attempt / "agent_calls" / "external_science_reviewer")
    (attempt / "budget.events.jsonl").unlink()
    budget = budget_preset("smoke_20m")
    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner._load_campaign_attempt",
        lambda _directory: (
            object(),
            fixture["blueprint"],
            budget.to_json(),
            fixture["campaign"],
            fixture["context"],
        ),
    )

    class UnavailableReviewer:
        def __init__(self, artifact_dir: Path) -> None:
            self.agent_id = "external-science-reviewer:unavailable-fixture"
            self.artifact_dir = artifact_dir / "external_science_reviewer"
            self.config = FrontierAgentConfig(runtime="codex", model="fixture-model")
            self.calls: list[dict] = []
            self.budget_ledger = None

        @property
        def provider_call_count(self) -> int:
            return sum(
                int(row.get("provider_call_charge", 0)) for row in self.calls
            )

        def __call__(self, prompt: str) -> dict:
            prefix = self.artifact_dir / "000"
            write_text_atomic(prefix.with_suffix(".prompt.txt"), prompt)
            _settle_stub_transport(
                self,
                prefix,
                prompt=prompt,
                stdout="",
                stderr="selected model is at capacity",
                returncode=1,
            )
            call = {
                "schema": "leanmill.frontier_subscription_role_call.v1",
                "role": "external_science_reviewer",
                "agent_id": self.agent_id,
                "runtime": "codex",
                "model": "fixture-model",
                "prompt_digest": content_hash({"prompt": prompt}),
                "returncode": 1,
                "provider_call_charge": 0,
            }
            write_json_atomic(prefix.with_suffix(".call.json"), call)
            self.calls.append(call)
            raise RuntimeError("reviewer runtime unavailable")

    monkeypatch.setattr(
        "ztare.leanmill.frontier_campaign_runner.frontier_agent_role",
        lambda _definition, *, artifact_dir, **_kwargs: UnavailableReviewer(
            artifact_dir
        ),
    )
    completion = run_external_science_recovery_admission(
        attempt,
        source_path=attempt / fixture["source_path"],
        theorem_target=fixture["theorem_target"],
        finite_witness_model_id=fixture["model_id"],
        literature_audit_path=attempt / "evidence/literature.md",
        lineage_id=fixture["program"].lineage_id,
        submitted_by="recovery-author",
        closure_ledger_path=fixture["closure_path"],
        kernel_parity_ledger_path=fixture["parity_path"],
        model="fixture-model",
        repo=tmp_path,
    )

    assert completion["outcome"] == "reviewer_transport_unavailable"
    assert completion["review_provider_calls"] == 0
    run = read_json(attempt / "run.json", {})
    assert run["status"] == "frontier_leaf_decision_pending"
    disposition = run["navigation"]["external_science_negative_dispositions"][-1]
    assert disposition["semantic_projection"] == {}
    assert disposition["projection_authority"] == "none_reviewer_unavailable"
    assert disposition["next_action"] == (
        "retry_or_reroute_the_independent_reviewer"
    )
    assert disposition["outer_objective_credit"].startswith("withheld")
    assert _route(
        attempt, "external_science_negative_disposition_to_navigation.v1"
    )["unconsumed_count"] == 0

    # Delivery of the typed outage changes run_digest. A successful retry is
    # still the same scientific review subject and must supersede this outage.
    replacement_core = {
        key: value
        for key, value in request.items()
        if key
        not in {
            "independent_review",
            "independent_review_execution",
            "request_sha256",
        }
    }
    replacement_core["run_digest"] = run["run_digest"]
    replacement_core_sha = _persist_review_request_core(
        attempt, replacement_core
    )
    replacement_without_digest = {
        **replacement_core,
        "independent_review": request["independent_review"],
        "independent_review_execution": request[
            "independent_review_execution"
        ],
    }
    replacement_request = {
        **replacement_without_digest,
        "request_sha256": content_hash(replacement_without_digest),
    }
    write_json_atomic(
        _request_path(attempt, replacement_request["request_sha256"]),
        replacement_request,
    )
    _persist_review_supersession(
        attempt,
        request_core_sha256=replacement_core_sha,
        replacement_request_sha256=replacement_request["request_sha256"],
    )
    assert external_science_negative_disposition_is_superseded(
        attempt, disposition
    )
