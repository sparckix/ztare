from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from ztare.common.task_discharge import TaskDischargeContract
from ztare.common.subscription_agent_runtime import (
    SUBSCRIPTION_DISPATCH_PRE_SPAWN_FAILURE_SCHEMA,
    current_subscription_dispatch_provenance_agent_id,
    current_subscription_dispatch_provenance_identity,
    subscription_dispatch_budget_scope,
    subscription_dispatch_role_scope,
)
from ztare.leanmill.campaign_closure_gate import (
    assert_campaign_closable,
    lineage_disposition_from_task_discharge,
    lineage_disposition_from_terminal_transition,
)
from ztare.leanmill.adapters.generic_fol_finite import (
    adjudicate_theory_task,
    build_model_universe,
    compile_theory_task,
)
from ztare.leanmill.axiompack_leaf_workbench import (
    axiompack_leaf_workbench_action_environment,
    navigator_decision_output_schema,
)
from ztare.leanmill.explore_axiom_space import _adjudicate_theory_program_tasks
from ztare.leanmill.common import write_json_atomic
from ztare.leanmill.exploration_budget import (
    BudgetReservation,
    ExplorationBudgetLedger,
    budget_preset,
)
from ztare.leanmill.finite_theory_context import build_formal_theory_context
from ztare.leanmill.formal_task_boundary import (
    GOVERNED_FORMAL_COUNTEREXAMPLE_ADJUDICATOR,
    build_formal_task_boundary_result,
    build_formal_task_faithfulness_receipt,
)
from ztare.leanmill.formal_task_campaign_executor import (
    FormalTaskAttemptDidNotClose,
    _kernel_replay_receipt,
    _mathlib_only_import_receipt,
    build_formal_task_role_registry_receipt,
    make_formalization_campaign_task_executor,
    validate_formal_task_attempt_outcome,
)
from ztare.leanmill.frontier_agent_runtime import FrontierAgentConfig
from ztare.leanmill.formalization_admission import FormalizationAdmission
from ztare.leanmill.ratification_policy import (
    TARGET_GOVERNANCE_AUTHORITIES,
    TARGET_GOVERNANCE_AUTHORITY_ROSTER_SHA256,
)
from ztare.leanmill.solver.closed_artifact import finalize_solver_validation
from ztare.leanmill.lean_source import has_sorry
from ztare.leanmill.frontier_campaign_runner import (
    _active_lineage_disposition_rows,
    _consume_theory_task_discharge,
    _open_terminal_obligation_feedback,
    drive_frontier_campaign,
    next_frontier_campaign_action,
)
from ztare.leanmill.frontier_boundary import run_frontier_boundaries
from ztare.leanmill.theory_campaign_journal import TheoryCampaignJournal
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    Binder,
    Formula,
    OperationSymbol,
    SortDecl,
    Term,
    TheorySignature,
    content_hash,
)
from ztare.leanmill.theory_program import THEORY_PROGRAM_V2, TheoryProgram
from ztare.leanmill.theory_interest import CHEAP_CONSEQUENCE_EVALUATOR_REF
from test_theory_navigator import _context_and_blueprint


def _budget_stop_receipt(context_hash: str) -> dict:
    core = {
        "schema": "leanmill.budget_stop_receipt.v1",
        "reason": "test_budget_boundary",
        "budget_digest": "budget:test",
        "elapsed_ms": 1,
        "usage": {},
        "phase_usage": {},
        "outstanding_reservations": [],
        "attempt_id": "attempt:test",
        "context_hash": context_hash,
        "last_information_observation": None,
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _test_transport_call(tmp_path, prompt: str) -> None:
    """Exercise the process chokepoint without invoking a provider in tests."""

    from ztare.common.subscription_agent_runtime import _run_cli

    agent_id = current_subscription_dispatch_provenance_agent_id()
    identity = current_subscription_dispatch_provenance_identity()
    assert agent_id
    command = ["/usr/bin/true", "--model", identity["model"]]
    if identity["runtime"] == "codex":
        command.extend(
            ["-c", f"model_reasoning_effort={identity['reasoning_effort']}"]
        )
    else:
        command.extend(["--effort", identity["reasoning_effort"]])
    command.append(prompt)
    result = _run_cli(
        command,
        runtime=identity["runtime"],
        repo=tmp_path,
        timeout_seconds=5,
        agent_id=agent_id,
    )
    assert result.returncode == 0


def _test_dispatch_budget_scope():
    counter = {"value": 0}
    committed: set[str] = set()

    def before(_runtime, _command):
        counter["value"] += 1
        return BudgetReservation(
            reservation_id=f"reservation:test-{counter['value']}",
            action_id=f"boundary:test-dispatch:{counter['value']}",
            phase="boundary",
            resources={"provider_calls": 1, "agent_turns": 1},
        )

    def after(reservation):
        committed.add(reservation.reservation_id)

    return subscription_dispatch_budget_scope(
        before_dispatch=before,
        after_dispatch=after,
    ), committed


def _context():
    signature = TheorySignature(
        name="UnaryTaskFixture",
        sorts=(SortDecl("S"),),
        operations=(OperationSymbol("step", ("S",), "S"),),
    )
    formula = AxiomFormula(
        "step_idempotent",
        Formula.forall(
            (Binder("x", "S"),),
            Formula.eq(
                Term.app("step", Term.app("step", Term.var("x"))),
                Term.app("step", Term.var("x")),
            ),
        ),
    )
    universe = build_model_universe(
        signature,
        strata=({"sort_sizes": {"S": 2}},),
    )
    return build_formal_theory_context(
        signature=signature,
        formulas=(formula,),
        universe=universe,
    )


def _request(context, *, finite_residual: bool = False) -> dict:
    core = {
        "schema": "leanmill.theory_task_request.v1",
        "context_hash": context.context_hash,
        "context_epoch": 0,
        "presentation_formula_ids": list(context.formula_ids),
        "goal": "Decide the authored universal reconstruction claim by counterexample.",
        "observable": "a formally checked counterexample to that exact universal claim",
        "adjudicator_capability": "governed_formal_counterexample",
        "evidence_refs": ["resume-context:reviewed-source-free-projection"],
        "kill_condition": "the formal statement is unfaithful or lacks attributed kernel evidence",
        "authority": "leaf_request_host_bound",
    }
    if finite_residual:
        core["finite_witness_residual"] = {
            "source_scope": "proved_finite_witness",
            "witness_id": "finite-witness:order-3",
            "claim_id": "reconstruction:unbounded",
            "evidence_refs": ["finite-witness:kernel-checked"],
        }
    return {**core, "request_id": "theory-task-request:" + content_hash(core)}


def _contract(context, *, finite_residual: bool = False) -> TaskDischargeContract:
    request = _request(context, finite_residual=finite_residual)
    lowering = compile_theory_task(
        request=request,
        context=context,
        adapter_config={},
    )
    assert lowering is not None
    return TaskDischargeContract(
        contract_id="theory-task:" + content_hash(
            {"adapter_id": "generic_fol_finite.v1", "request": request, "lowering": lowering}
        ),
        adjudicator_id=str(lowering["adjudicator_id"]),
        lifecycle_scope="campaign:test",
        owner="lineage:test",
        parameters=dict(lowering["parameters"]),
    )


def _governed_attempt(task_id: str) -> dict:
    attribution_core = {
        "schema": "leanmill.matched_consequence_attribution.v1",
        "target_hash": "target:reconstruction-counterexample",
        "proof_digest": "proof:checked",
        "arms": {
            "full": {"status": "proved", "kernel_checked": True},
            "empty": {"status": "unresolved", "kernel_checked": False},
            "without:premise": {"status": "unresolved", "kernel_checked": False},
        },
    }
    attribution = {
        **attribution_core,
        "receipt_sha256": content_hash(attribution_core),
    }
    core = {
        "schema": "leanmill.governed_consequence_attempt.v1",
        "task_id": task_id,
        "status": "proved_attributed",
        "proof_text": "by exact checked_counterexample",
        "solver_result_digest": "solver:provider-free-replay",
        "attribution": attribution,
        "work_receipt": {
            "verdict": "completed",
            "formal_leg": {
                "outcome": "proved_attributed",
                "credit_ready": True,
            },
        },
        "refutation": None,
        "reason": "premise-aware kernel replay",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _boundary(contract: TaskDischargeContract) -> dict:
    target_id = "formal-task:reconstruction-counterexample"
    faithfulness = build_formal_task_faithfulness_receipt(
        contract,
        formal_target_id=target_id,
        formal_statement_sha256="statement:reviewed",
        reviewer_evidence_refs=("independent-review:accepted",),
        authority="independent_formal_statement_reviewer",
    )
    row = build_formal_task_boundary_result(
        contract,
        faithfulness_receipt=faithfulness,
        governed_attempt=_governed_attempt(target_id),
    )
    core = {
        "schema": "leanmill.frontier_boundary_result.v1",
        "context_hash": str(contract.parameters["context_hash"]),
        "query_results": [row],
        "stop_reason": "campaign_finished",
        "next_epoch_proposal": None,
    }
    return {**core, "result_sha256": content_hash(core)}


def test_generic_fol_compiles_only_fresh_formal_counterexample_task() -> None:
    context = _context()
    contract = _contract(context)
    assert contract.adjudicator_id == GOVERNED_FORMAL_COUNTEREXAMPLE_ADJUDICATOR
    assert contract.parameters["claim_scope"] == (
        "task_only_pending_independent_objective_authorization"
    )

    recovery_request = {
        **_request(context),
        "adjudicator_capability": "external_science_recovery_admission",
    }
    recovery_core = {
        key: value for key, value in recovery_request.items() if key != "request_id"
    }
    recovery_request["request_id"] = (
        "theory-task-request:" + content_hash(recovery_core)
    )
    assert compile_theory_task(
        request=recovery_request,
        context=context,
        adapter_config={},
    ) is None


def test_generic_fol_formal_task_has_a_live_workbench_producer() -> None:
    context = _context()
    environment = axiompack_leaf_workbench_action_environment(
        context=context,
        selection_mode="theory_program",
        theory_adapter_id="generic_fol_finite.v1",
        theory_adapter_config={},
        campaign_id="campaign:test",
        lineage_id="lineage:test",
    )
    request = _request(context)
    receipt = environment["action_handlers"]["propose_theory_task"](
        ".",
        {
            "input_refs": {
                "formula_ids": request["presentation_formula_ids"],
                "goal": request["goal"],
                "observable": request["observable"],
                "adjudicator_capability": request["adjudicator_capability"],
                "evidence_refs": request["evidence_refs"],
                "kill_condition": request["kill_condition"],
            }
        },
        None,
        environment["contract"],
    )
    summary = receipt["output_summary"]
    assert summary["status"] == "compiled_theory_task"
    assert summary["missing_capability"] is None
    assert summary["task_contract"]["adjudicator_id"] == (
        GOVERNED_FORMAL_COUNTEREXAMPLE_ADJUDICATOR
    )


def test_formal_task_kernel_replay_requires_positive_axiom_receipt() -> None:
    context = _context()
    contract = _contract(context)
    admission = FormalizationAdmission(
        task_digest="sha256:" + content_hash({
            "contract_sha256": contract.sha256,
            "task_specification": contract.parameters["task_specification"],
        }),
        intent_text="test task",
        context_digest="sha256:" + context.context_hash,
        status="ADMITTED",
        target_name="formal_task_axiom_gate",
        source_text="theorem formal_task_axiom_gate : True := by\n  sorry\n",
        target_signature=": True",
        faithfulness_reason="fixture",
        faithfulness_checks_json=json.dumps({"fixture": True}),
        refine_trace_json="[]",
        advisory_audits_json="{}",
    )
    raw_solver = {
        "results": [{
            "outcome": "closed",
            "proof_text": "by trivial",
            "contract_validation": {
                "credit_ready_at_solver_layer": True,
                "receipts": {
                    "kernel_compile_receipt": {
                        "available": True,
                        "passed": True,
                    },
                    "matched_negative_control_receipt": {
                        "available": True,
                        "passed": True,
                    },
                },
            },
        }],
        "governance": {"status": "ratified"},
        "closure_certificate": "closure:test:missing-axiom-receipt",
    }

    with pytest.raises(
        FormalTaskAttemptDidNotClose,
        match="lacks_ratified_closure_evidence",
    ):
        _kernel_replay_receipt(
            contract,
            admission,
            raw_solver,
            compile_fn=lambda _source: True,
            attempt_id="attempt:missing-axiom-receipt",
            campaign_id=contract.lifecycle_scope,
            context_hash=context.context_hash,
            lean_solver_ref="solver:test",
        )


def test_navigator_schema_accepts_typed_finite_residual_and_rejects_null() -> None:
    context = _context()
    request = _request(context, finite_residual=True)
    decision = {
        "decision": "request",
        "rationale": "test whether the finite witness generalizes",
        "capability_id": "propose_theory_task",
        "input_refs": {
            "formula_ids": request["presentation_formula_ids"],
            "goal": request["goal"],
            "observable": request["observable"],
            "adjudicator_capability": request["adjudicator_capability"],
            "evidence_refs": request["evidence_refs"],
            "kill_condition": request["kill_condition"],
            "finite_witness_residual": request["finite_witness_residual"],
        },
        "formula_ids": None,
        "boundary_target_ids": None,
        "task_contract_ids": None,
    }
    validator = Draft202012Validator(navigator_decision_output_schema())
    assert list(validator.iter_errors(decision)) == []
    decision["input_refs"] = {
        **decision["input_refs"],
        "finite_witness_residual": None,
    }
    assert list(validator.iter_errors(decision))


def test_formal_counterexample_requires_review_and_attributed_kernel_receipts() -> None:
    context = _context()
    contract = _contract(context)
    boundary = _boundary(contract)

    receipt = adjudicate_theory_task(
        contract=contract,
        boundary_result=boundary,
    )
    assert receipt.status == "discharged"
    assert receipt.observed["boundary_status"] == "kernel_verified_attributed"

    tampered = dict(boundary)
    tampered["query_results"] = [dict(boundary["query_results"][0])]
    tampered["query_results"][0]["faithfulness_receipt"] = {
        **tampered["query_results"][0]["faithfulness_receipt"],
        "verdict": "unfaithful",
    }
    tampered_core = {
        key: value for key, value in tampered.items() if key != "result_sha256"
    }
    tampered["result_sha256"] = content_hash(tampered_core)
    try:
        adjudicate_theory_task(contract=contract, boundary_result=tampered)
    except ValueError as exc:
        assert "digest mismatch" in str(exc)
    else:
        raise AssertionError("tampered faithfulness evidence must not discharge")


def test_formal_counterexample_reaches_existing_discharge_consumer(tmp_path) -> None:
    context = _context()
    contract = _contract(context)
    program = TheoryProgram(
        campaign_id="campaign:test",
        lineage_id="lineage:test",
        context_hash=context.context_hash,
        context_epoch=0,
        presentation_formula_ids=context.formula_ids,
        prediction_formula_ids=(),
        selection_receipt_id="selection:test",
        schema=THEORY_PROGRAM_V2,
        task_discharge_contracts=(contract,),
    )
    finalist = {
        "formula_ids": list(context.formula_ids),
        "boundary_target_ids": [],
        "theory_program_id": program.program_id,
        "theory_program": program.to_json(),
    }
    navigation = {"finalists": [finalist]}
    boundary = _boundary(contract)
    bundle = _adjudicate_theory_program_tasks(
        tmp_path,
        adapter_id="generic_fol_finite.v1",
        navigation=navigation,
        boundary_result=boundary,
    )
    assert bundle["explicit_program_status"] == "discharged"

    run = {
        "status": "frontier_candidates_frozen_awaiting_boundary_approval",
        "context_hash": context.context_hash,
        "navigation": {
            **navigation,
            "lineage_synthesis": {
                "route": "proceed_boundary",
                "objective_contract": {
                    "schema": "leanmill.frontier_objective_contract.v1",
                    "instruction": "Adjudicate the authored reconstruction question.",
                },
                "program_ids": [program.program_id],
            },
        },
    }
    run["run_digest"] = content_hash(run)
    consumed = _consume_theory_task_discharge(
        tmp_path,
        run,
        {"boundary_result": boundary, "theory_task_discharge": bundle},
    )
    assert consumed["status"] == "frontier_objective_discharged"
    assert consumed["navigation"]["theory_task_discharge"]["objective_status"] == (
        "discharged"
    )
    disposition = lineage_disposition_from_task_discharge(
        theory_program=program.to_json(),
        discharge_bundle=bundle,
        discharge_consumption=consumed["navigation"]["theory_task_discharge"],
        boundary_result=boundary,
    )
    terminal = assert_campaign_closable(
        context_hash=context.context_hash,
        frozen_lineage_ids=(program.lineage_id,),
        lineage_dispositions=(disposition,),
    )
    assert terminal["ready"] is True


def test_task_only_program_executes_and_replays_through_frontier_boundary(
    tmp_path,
) -> None:
    context, source_blueprint = _context_and_blueprint()
    contract = _contract(context)
    program = TheoryProgram(
        campaign_id="campaign:test",
        lineage_id="lineage:test",
        context_hash=context.context_hash,
        context_epoch=0,
        presentation_formula_ids=context.formula_ids,
        prediction_formula_ids=(),
        selection_receipt_id="selection:test",
        schema=THEORY_PROGRAM_V2,
        task_discharge_contracts=(contract,),
    )
    navigation = {
        "finalists": [
            {
                "candidate_kind": "theory_program",
                "formula_ids": list(program.presentation_formula_ids),
                "boundary_target_ids": [],
                "residual_prediction_formula_ids": [],
                "theory_program_id": program.program_id,
                "theory_program": program.to_json(),
            }
        ]
    }
    blueprint = replace(
        source_blueprint,
        navigator_contract={
            **source_blueprint.navigator_contract,
            "selection_mode": "theory_program",
        },
        query_budget={
            **source_blueprint.query_budget,
            "boundary_queries": 2,
        },
    )
    row = _boundary(contract)["query_results"][0]

    first = run_frontier_boundaries(
        context,
        blueprint,
        navigation,
        TheoryCampaignJournal(tmp_path / "first.events.jsonl"),
        ExplorationBudgetLedger(
            tmp_path / "first.budget.jsonl",
            budget_preset("smoke_20m"),
            attempt_id="attempt:first",
        ),
        attempt_id="attempt:first",
        campaign_id="campaign:test",
        theory_task_executor_fn=lambda *_args, **_kwargs: row,
    ).to_json()
    assert first["query_results"] == [row]

    replay = run_frontier_boundaries(
        context,
        blueprint,
        navigation,
        TheoryCampaignJournal(tmp_path / "replay.events.jsonl"),
        ExplorationBudgetLedger(
            tmp_path / "replay.budget.jsonl",
            budget_preset("smoke_20m"),
            attempt_id="attempt:replay",
        ),
        attempt_id="attempt:replay",
        campaign_id="campaign:test",
        theory_task_executor_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("immutable prior task result must replay")
        ),
        prior_query_results=first["query_results"],
    ).to_json()
    assert replay["query_results"] == [row]


def test_formalization_campaign_factory_first_fires_with_separate_fake_roles(
    tmp_path,
) -> None:
    context, source_blueprint = _context_and_blueprint()
    contract = _contract(context)
    calls = {"formalize": 0, "solve": 0, "compile": 0}

    def admit(intent_text, **kwargs):
        calls["formalize"] += 1
        _test_transport_call(tmp_path, "formalize the frozen task")
        reviewer = role_registry["roles"]["faithfulness_reviewer"]
        from ztare.common.llm_runtime import subscription_reasoning_effort

        reviewer_effort = subscription_reasoning_effort(
            reviewer["config"]["runtime"],
            reviewer["config"]["reasoning_effort"],
            model=reviewer["config"]["model"],
        )
        assert reviewer_effort
        with subscription_dispatch_role_scope(
            role="faithfulness_reviewer",
            agent_id=reviewer["agent_id"],
            run_tag=(
                "attempt:first-fire:theory-task:faithfulness_reviewer:"
                f"{contract.sha256[:16]}"
            ),
            runtime=reviewer["config"]["runtime"],
            model=reviewer["config"]["model"],
            reasoning_effort=reviewer_effort,
            config_sha256=reviewer["config_sha256"],
        ):
            _test_transport_call(tmp_path, "review the frozen formalization")
        return FormalizationAdmission(
            task_digest=kwargs["task_digest"],
            intent_text=intent_text,
            context_digest="sha256:" + "1" * 64,
            status="ADMITTED",
            target_name="campaign_reconstruction_counterexample",
            source_text=(
                "theorem campaign_reconstruction_counterexample : True := by\n"
                "  sorry\n"
            ),
            target_signature=": True",
            faithfulness_reason="independent round trip accepted",
            faithfulness_checks_json=json.dumps(
                {"independent_reviewer": True}, sort_keys=True
            ),
            refine_trace_json="[]",
            advisory_audits_json="{}",
        )

    def solve(target_name, source_text, goal, **_kwargs):
        calls["solve"] += 1
        _test_transport_call(tmp_path, "solve the admitted Lean target")
        assert _kwargs["require_positive_axiom_receipt"] is True
        assert target_name == "campaign_reconstruction_counterexample"
        assert has_sorry(source_text)
        assert goal == ""
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
        }
        validation = finalize_solver_validation({
            "credit_ready_at_solver_layer": True,
            "positive_axiom_receipt_required": True,
            "discriminating_mnc_required": True,
            "axiom_tier": "kernel_pure",
            "receipts": {
                "kernel_compile_receipt": {"available": True, "passed": True},
                "matched_negative_control_receipt": {
                    "available": True,
                    "passed": True,
                },
                "axiom_allowlist_receipt": {"available": True, "passed": True},
            },
        }, governance)
        return {
            "results": [
                {
                    "outcome": "closed",
                    "proof_text": "by trivial",
                    "contract_validation": validation,
                }
            ],
            "governance": governance,
            "closure_certificate": "closure:test:first-fire",
        }

    def compile_source(source_text):
        calls["compile"] += 1
        return not has_sorry(source_text)

    role_models = {
        "formalizer": ("gpt-formalizer", "high"),
        "faithfulness_reviewer": ("gpt-reviewer", "ultra"),
        "lean_solver": ("gpt-solver", "medium"),
    }
    role = lambda name, agent_id: SimpleNamespace(  # noqa: E731
        role=name,
        agent_id=agent_id,
        config=FrontierAgentConfig(
            model=role_models[name][0],
            reasoning_effort=role_models[name][1],
        ),
    )
    role_registry = build_formal_task_role_registry_receipt(
        attempt_id="attempt:first-fire",
        campaign_id="campaign:test",
        formalizer_role=role("formalizer", "axiompack-formalizer"),
        faithfulness_reviewer_role=role(
            "faithfulness_reviewer", "axiompack-faithfulness-reviewer"
        ),
        lean_solver_role=role("lean_solver", "axiompack-lean-solver"),
    )
    executor = make_formalization_campaign_task_executor(
        attempt_id="attempt:first-fire",
        campaign_id="campaign:test",
        sandbox=tmp_path,
        compile_fn=compile_source,
        role_registry_receipt=role_registry,
        formalization_admission_fn=admit,
        admitted_solver_fn=solve,
    )
    program = TheoryProgram(
        campaign_id="campaign:test",
        lineage_id="lineage:test",
        context_hash=context.context_hash,
        context_epoch=0,
        presentation_formula_ids=context.formula_ids,
        prediction_formula_ids=(),
        selection_receipt_id="selection:first-fire",
        schema=THEORY_PROGRAM_V2,
        task_discharge_contracts=(contract,),
    )
    navigation = {
        "finalists": [
            {
                "candidate_kind": "theory_program",
                "formula_ids": list(program.presentation_formula_ids),
                "boundary_target_ids": [],
                "residual_prediction_formula_ids": [],
                "theory_program_id": program.program_id,
                "theory_program": program.to_json(),
            }
        ]
    }
    blueprint = replace(
        source_blueprint,
        navigator_contract={
            **source_blueprint.navigator_contract,
            "selection_mode": "theory_program",
        },
        query_budget={**source_blueprint.query_budget, "boundary_queries": 2},
    )
    dispatch_scope, committed = _test_dispatch_budget_scope()
    with dispatch_scope:
        boundary = run_frontier_boundaries(
            context,
            blueprint,
            navigation,
            TheoryCampaignJournal(tmp_path / "first-fire.events.jsonl"),
            ExplorationBudgetLedger(
                tmp_path / "first-fire.budget.jsonl",
                budget_preset("smoke_20m"),
                attempt_id="attempt:first-fire",
            ),
            attempt_id="attempt:first-fire",
            campaign_id="campaign:test",
            theory_task_executor_fn=executor,
        ).to_json()
    assert len(committed) == 3
    assert calls == {"formalize": 1, "solve": 1, "compile": 1}, json.dumps(
        boundary, indent=2, sort_keys=True
    )
    assert boundary["query_results"][0]["status"] == (
        "kernel_verified_independently_reviewed"
    )
    role_receipt = boundary["query_results"][0]["role_separation_receipt"]
    assert set(role_receipt["role_execution_receipts"]) == {
        "formalizer", "faithfulness_reviewer", "lean_solver"
    }
    assert {
        role_name: descriptor["config"]["model"]
        for role_name, descriptor in role_receipt[
            "role_registry_receipt"
        ]["roles"].items()
    } == {
        "formalizer": "gpt-formalizer",
        "faithfulness_reviewer": "gpt-reviewer",
        "lean_solver": "gpt-solver",
    }
    for role_name, call_receipt in role_receipt[
        "role_execution_receipts"
    ].items():
        assert call_receipt["config_sha256"] == role_receipt[
            "role_registry_receipt"
        ]["roles"][role_name]["config_sha256"]
        assert call_receipt["dispatch_calls"]
        assert all(
            row["charged_reservation"] is True
            and row["agent_id"]
            == role_receipt["role_registry_receipt"]["roles"][role_name][
                "agent_id"
            ]
            for row in call_receipt["dispatch_calls"]
        )
        assert all(
            row["run_tag"] == call_receipt["run_tag"]
            for row in call_receipt["dispatch_calls"]
        )
    assert adjudicate_theory_task(
        contract=contract, boundary_result=boundary
    ).status == "discharged"

    def output_only_admit(intent_text, **kwargs):
        return FormalizationAdmission(
            task_digest=kwargs["task_digest"],
            intent_text=intent_text,
            context_digest="sha256:" + "8" * 64,
            status="ADMITTED",
            target_name="campaign_reconstruction_counterexample",
            source_text=(
                "theorem campaign_reconstruction_counterexample : True := by\n"
                "  sorry\n"
            ),
            target_signature=": True",
            faithfulness_reason="output exists without transport evidence",
            faithfulness_checks_json=json.dumps(
                {"independent_reviewer": True}, sort_keys=True
            ),
            refine_trace_json="[]",
            advisory_audits_json="{}",
        )

    output_only_executor = make_formalization_campaign_task_executor(
        attempt_id="attempt:first-fire",
        campaign_id="campaign:test",
        sandbox=tmp_path,
        compile_fn=compile_source,
        role_registry_receipt=role_registry,
        formalization_admission_fn=output_only_admit,
        admitted_solver_fn=lambda *_args, **_kwargs: {
            "results": [
                {
                    "outcome": "closed",
                    "proof_text": "by trivial",
                    "contract_validation": {
                        "credit_ready_at_solver_layer": True,
                        "positive_axiom_receipt_required": True,
                        "axiom_tier": "kernel_pure",
                        "receipts": {
                            "kernel_compile_receipt": {
                                "available": True,
                                "passed": True,
                            },
                            "matched_negative_control_receipt": {
                                "available": True,
                                "passed": True,
                            },
                            "axiom_allowlist_receipt": {
                                "available": True,
                                "passed": True,
                            },
                        },
                    },
                }
            ],
            "governance": {"status": "ratified"},
            "closure_certificate": "closure:test:output-only",
        },
    )
    with pytest.raises(ValueError, match="without call provenance"):
        output_only_executor(
            contract,
            context=context,
            verification_plan={},
            budget_ledger=None,
        )

    tampered = json.loads(json.dumps(boundary))
    role_row = tampered["query_results"][0]["role_separation_receipt"]
    role_row["role_execution_receipts"].pop("faithfulness_reviewer")
    role_core = {
        key: value for key, value in role_row.items() if key != "receipt_sha256"
    }
    role_row["receipt_sha256"] = content_hash(role_core)
    task_row = tampered["query_results"][0]
    task_core = {
        key: value for key, value in task_row.items() if key != "receipt_sha256"
    }
    task_row["receipt_sha256"] = content_hash(task_core)
    boundary_core = {
        key: value for key, value in tampered.items() if key != "result_sha256"
    }
    tampered["result_sha256"] = content_hash(boundary_core)
    with pytest.raises(ValueError, match="role receipt changed identity"):
        adjudicate_theory_task(contract=contract, boundary_result=tampered)

    wrong_task = json.loads(json.dumps(boundary))
    role_row = wrong_task["query_results"][0]["role_separation_receipt"]
    formalizer_call = role_row["role_execution_receipts"]["formalizer"][
        "dispatch_calls"
    ][0]
    dispatch_artifact = Path(formalizer_call["artifact_path"])
    original_dispatch = json.loads(dispatch_artifact.read_text(encoding="utf-8"))
    borrowed_dispatch = dict(original_dispatch)
    borrowed_dispatch["run_tag"] = (
        "attempt:first-fire:theory-task:formalizer:borrowed-contract"
    )
    borrowed_core = {
        key: value
        for key, value in borrowed_dispatch.items()
        if key != "receipt_sha256"
    }
    borrowed_dispatch["receipt_sha256"] = content_hash(borrowed_core)
    dispatch_artifact.write_text(
        json.dumps(borrowed_dispatch, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    role_row["role_execution_receipts"]["formalizer"]["dispatch_calls"][0] = (
        borrowed_dispatch
    )
    call_row = role_row["role_execution_receipts"]["formalizer"]
    call_row["dispatch_calls_sha256"] = content_hash(call_row["dispatch_calls"])
    call_core = {
        key: value for key, value in call_row.items() if key != "receipt_sha256"
    }
    call_row["receipt_sha256"] = content_hash(call_core)
    role_core = {
        key: value for key, value in role_row.items() if key != "receipt_sha256"
    }
    role_row["receipt_sha256"] = content_hash(role_core)
    task_row = wrong_task["query_results"][0]
    task_core = {
        key: value for key, value in task_row.items() if key != "receipt_sha256"
    }
    task_row["receipt_sha256"] = content_hash(task_core)
    boundary_core = {
        key: value for key, value in wrong_task.items() if key != "result_sha256"
    }
    wrong_task["result_sha256"] = content_hash(boundary_core)
    try:
        with pytest.raises(ValueError, match="role receipt changed identity"):
            adjudicate_theory_task(contract=contract, boundary_result=wrong_task)
    finally:
        dispatch_artifact.write_text(
            json.dumps(original_dispatch, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    dispatch_artifact = Path(
        role_receipt["role_execution_receipts"]["formalizer"][
            "dispatch_calls"
        ][0]["artifact_path"]
    )
    frozen_dispatch = dispatch_artifact.read_text(encoding="utf-8")
    dispatch_artifact.write_text("{}\n", encoding="utf-8")
    try:
        with pytest.raises(
            ValueError, match="dispatch provenance artifact is unavailable|changed identity"
        ):
            adjudicate_theory_task(contract=contract, boundary_result=boundary)
    finally:
        dispatch_artifact.write_text(frozen_dispatch, encoding="utf-8")


def test_formalization_campaign_rejects_recovered_repo_theorem_import(
    tmp_path,
) -> None:
    context = _context()
    contract = _contract(context)
    calls = {"solve": 0, "compile": 0}

    def admit(intent_text, **kwargs):
        return FormalizationAdmission(
            task_digest=kwargs["task_digest"],
            intent_text=intent_text,
            context_digest="sha256:" + "2" * 64,
            status="ADMITTED",
            target_name="renamed_recovered_counterexample",
            source_text=(
                "import ZtareProofs.AxiomPackT2ReconstructionCounterexample\n"
                "theorem renamed_recovered_counterexample : True := by\n"
                "  sorry\n"
            ),
            target_signature=": True",
            faithfulness_reason="reviewer accepted the surface statement",
            faithfulness_checks_json=json.dumps(
                {"independent_reviewer": True}, sort_keys=True
            ),
            refine_trace_json="[]",
            advisory_audits_json="{}",
        )

    def solve(*_args, **_kwargs):
        calls["solve"] += 1
        raise AssertionError("repo-importing source must not reach the solver")

    def compile_source(_source_text):
        calls["compile"] += 1
        return True

    role = lambda name, agent_id: SimpleNamespace(  # noqa: E731
        role=name,
        agent_id=agent_id,
        config=FrontierAgentConfig(),
    )
    registry = build_formal_task_role_registry_receipt(
        attempt_id="attempt:import-firewall",
        campaign_id="campaign:test",
        formalizer_role=role("formalizer", "formalizer:import-firewall"),
        faithfulness_reviewer_role=role(
            "faithfulness_reviewer", "reviewer:import-firewall"
        ),
        lean_solver_role=role("lean_solver", "solver:import-firewall"),
    )
    executor = make_formalization_campaign_task_executor(
        attempt_id="attempt:import-firewall",
        campaign_id="campaign:test",
        sandbox=tmp_path,
        compile_fn=compile_source,
        role_registry_receipt=registry,
        formalization_admission_fn=admit,
        admitted_solver_fn=solve,
    )

    from ztare.formal.repl_compile import (
        get_campaign_substrate,
        set_campaign_substrate,
    )

    prior = str(tmp_path / "recovered_campaign_substrate.lean")
    set_campaign_substrate(prior)
    try:
        with pytest.raises(ValueError, match="outside the Mathlib allowlist"):
            executor(
                contract,
                context=context,
                verification_plan={},
                budget_ledger=None,
            )
        assert get_campaign_substrate() == prior
    finally:
        set_campaign_substrate(None)
    assert calls == {"solve": 0, "compile": 0}
    with pytest.raises(ValueError, match="frozen grammar"):
        _mathlib_only_import_receipt(
            contract,
            (
                "/- disguised command -/ import "
                "ZtareProofs.AxiomPackT2ReconstructionCounterexample\n"
                "theorem renamed : True := by sorry\n"
            ),
            stage="admitted_source",
        )


@pytest.mark.parametrize(
    ("scenario", "expected_status", "expected_stage"),
    (
        ("review_rejected", "formalization_rejected", "faithfulness_review"),
        ("provider_unavailable", "runtime_unavailable", "formalization"),
        ("solver_unclosed", "solver_unclosed", "solver"),
    ),
)
def test_formal_task_negative_attempts_are_typed_feedback_without_credit(
    tmp_path, scenario, expected_status, expected_stage
) -> None:
    context = _context()
    contract = _contract(context)
    role = lambda name: SimpleNamespace(  # noqa: E731
        role=name,
        agent_id=f"{name}:negative:{scenario}",
        config=FrontierAgentConfig(),
    )
    registry = build_formal_task_role_registry_receipt(
        attempt_id=f"attempt:negative:{scenario}",
        campaign_id="campaign:test",
        formalizer_role=role("formalizer"),
        faithfulness_reviewer_role=role("faithfulness_reviewer"),
        lean_solver_role=role("lean_solver"),
    )

    def reviewer_call():
        reviewer = registry["roles"]["faithfulness_reviewer"]
        from ztare.common.llm_runtime import subscription_reasoning_effort

        effort = subscription_reasoning_effort(
            reviewer["config"]["runtime"],
            reviewer["config"]["reasoning_effort"],
            model=reviewer["config"]["model"],
        )
        assert effort
        with subscription_dispatch_role_scope(
            role="faithfulness_reviewer",
            agent_id=reviewer["agent_id"],
            run_tag=(
                f"attempt:negative:{scenario}:theory-task:"
                f"faithfulness_reviewer:{contract.sha256[:16]}"
            ),
            runtime=reviewer["config"]["runtime"],
            model=reviewer["config"]["model"],
            reasoning_effort=effort,
            config_sha256=reviewer["config_sha256"],
        ):
            _test_transport_call(tmp_path, "negative-path faithfulness review")

    def admit(intent_text, **kwargs):
        _test_transport_call(tmp_path, "negative-path formalization")
        if scenario != "provider_unavailable":
            reviewer_call()
        admitted = scenario == "solver_unclosed"
        return FormalizationAdmission(
            task_digest=kwargs["task_digest"],
            intent_text=intent_text,
            context_digest="sha256:" + "7" * 64,
            status=(
                "ADMITTED"
                if admitted
                else "INADMISSIBLE_PROVIDER_DEAD"
                if scenario == "provider_unavailable"
                else "REJECTED"
            ),
            target_name="negative_target" if admitted else "",
            source_text=(
                "theorem negative_target : True := by\n  sorry\n"
                if admitted
                else ""
            ),
            target_signature=": True" if admitted else "",
            faithfulness_reason=scenario,
            faithfulness_checks_json=json.dumps(
                {"independent_reviewer": admitted}, sort_keys=True
            ),
            refine_trace_json="[]",
            advisory_audits_json="{}",
        )

    def solve(*_args, **_kwargs):
        _test_transport_call(tmp_path, "negative-path solver")
        return {
            "schema": "leanmill.solve_adhoc_result.v1",
            "results": [{"outcome": "open", "proof_text": ""}],
        }

    executor = make_formalization_campaign_task_executor(
        attempt_id=f"attempt:negative:{scenario}",
        campaign_id="campaign:test",
        sandbox=tmp_path,
        compile_fn=lambda _source: True,
        role_registry_receipt=registry,
        formalization_admission_fn=admit,
        admitted_solver_fn=solve,
    )
    dispatch_scope, committed = _test_dispatch_budget_scope()
    with dispatch_scope:
        outcome = executor(
            contract,
            context=context,
            verification_plan={},
            budget_ledger=None,
        )
    assert committed
    assert outcome["status"] == expected_status
    assert outcome["stage"] == expected_stage
    boundary_core = {
        "schema": "leanmill.frontier_boundary_result.v1",
        "context_hash": context.context_hash,
        "query_results": [outcome],
    }
    boundary = {
        **boundary_core,
        "result_sha256": content_hash(boundary_core),
    }
    receipt = adjudicate_theory_task(
        contract=contract,
        boundary_result=boundary,
    )
    assert receipt.status == "unavailable"
    assert receipt.observed["boundary_status"] == expected_status


@pytest.mark.parametrize(
    ("failed_role", "expected_stage"),
    (
        ("formalizer", "formalization"),
        ("faithfulness_reviewer", "faithfulness_review"),
        ("lean_solver", "solver"),
    ),
)
def test_formal_task_pre_spawn_failure_is_typed_role_bound_and_replay_checked(
    tmp_path, monkeypatch, failed_role, expected_stage
) -> None:
    import subprocess
    from ztare.common import subscription_agent_runtime as subscription_runtime

    context = _context()
    contract = _contract(context)
    attempt_id = f"attempt:pre-spawn:{failed_role}"
    role = lambda name: SimpleNamespace(  # noqa: E731
        role=name,
        agent_id=f"{name}:pre-spawn:{failed_role}",
        config=FrontierAgentConfig(),
    )
    registry = build_formal_task_role_registry_receipt(
        attempt_id=attempt_id,
        campaign_id="campaign:test",
        formalizer_role=role("formalizer"),
        faithfulness_reviewer_role=role("faithfulness_reviewer"),
        lean_solver_role=role("lean_solver"),
    )
    original_run = subscription_runtime._run_cli_unbudgeted

    def crash_selected(command, **kwargs):
        if command[-1] == f"crash:{failed_role}":
            raise OSError(f"pre-spawn {failed_role} fixture")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(subscription_runtime, "_run_cli_unbudgeted", crash_selected)
    counter = {"value": 0}
    committed: set[str] = set()
    released: set[str] = set()

    def before(_runtime, _command):
        counter["value"] += 1
        return BudgetReservation(
            reservation_id=f"reservation:pre-spawn-{failed_role}-{counter['value']}",
            action_id=f"boundary:pre-spawn:{failed_role}:{counter['value']}",
            phase="boundary",
            resources={"provider_calls": 1, "agent_turns": 1},
        )

    def unused_after(_reservation):
        raise AssertionError("result-aware settlement must own this attempt")

    def settle(reservation, result):
        if result is None:
            released.add(reservation.reservation_id)
            return False
        committed.add(reservation.reservation_id)
        return True

    def dispatch(role_name: str) -> None:
        prompt = (
            f"crash:{failed_role}"
            if role_name == failed_role
            else f"success:{role_name}"
        )
        _test_transport_call(tmp_path, prompt)

    def reviewer_dispatch() -> None:
        reviewer = registry["roles"]["faithfulness_reviewer"]
        from ztare.common.llm_runtime import subscription_reasoning_effort

        effort = subscription_reasoning_effort(
            reviewer["config"]["runtime"],
            reviewer["config"]["reasoning_effort"],
            model=reviewer["config"]["model"],
        )
        assert effort
        with subscription_dispatch_role_scope(
            role="faithfulness_reviewer",
            agent_id=reviewer["agent_id"],
            run_tag=(
                f"{attempt_id}:theory-task:faithfulness_reviewer:"
                f"{contract.sha256[:16]}"
            ),
            runtime=reviewer["config"]["runtime"],
            model=reviewer["config"]["model"],
            reasoning_effort=effort,
            config_sha256=reviewer["config_sha256"],
        ):
            dispatch("faithfulness_reviewer")

    def admit(intent_text, **kwargs):
        dispatch("formalizer")
        reviewer_dispatch()
        return FormalizationAdmission(
            task_digest=kwargs["task_digest"],
            intent_text=intent_text,
            context_digest="sha256:" + "6" * 64,
            status="ADMITTED",
            target_name="pre_spawn_target",
            source_text="theorem pre_spawn_target : True := by\n  sorry\n",
            target_signature=": True",
            faithfulness_reason="reviewed",
            faithfulness_checks_json=json.dumps(
                {"independent_reviewer": True}, sort_keys=True
            ),
            refine_trace_json="[]",
            advisory_audits_json="{}",
        )

    def solve(*_args, **_kwargs):
        dispatch("lean_solver")
        raise AssertionError("a successful solver fixture was not requested")

    executor = make_formalization_campaign_task_executor(
        attempt_id=attempt_id,
        campaign_id="campaign:test",
        sandbox=tmp_path,
        compile_fn=lambda _source: True,
        role_registry_receipt=registry,
        formalization_admission_fn=admit,
        admitted_solver_fn=solve,
    )
    with subscription_dispatch_budget_scope(
        before_dispatch=before,
        after_dispatch=unused_after,
        settle_dispatch=settle,
    ):
        outcome = executor(
            contract,
            context=context,
            verification_plan={},
            budget_ledger=None,
        )
    assert outcome["status"] == "runtime_unavailable"
    assert outcome["stage"] == expected_stage
    failures = [
        row
        for row in outcome["dispatch_calls"]
        if row["schema"] == SUBSCRIPTION_DISPATCH_PRE_SPAWN_FAILURE_SCHEMA
    ]
    assert len(failures) == 1
    failure = failures[0]
    assert failure["role"] == failed_role
    assert failure["reservation_settlement"] == "released"
    assert failure["charged_reservation"] is False
    assert failure["reservation_id"] in released
    assert not (committed & released)
    assert validate_formal_task_attempt_outcome(contract, outcome) == outcome

    boundary_core = {
        "schema": "leanmill.frontier_boundary_result.v1",
        "context_hash": context.context_hash,
        "query_results": [outcome],
    }
    boundary = {
        **boundary_core,
        "result_sha256": content_hash(boundary_core),
    }
    receipt = adjudicate_theory_task(contract=contract, boundary_result=boundary)
    assert receipt.status == "unavailable"
    assert receipt.observed["boundary_status"] == "runtime_unavailable"

    artifact = Path(failure["artifact_path"])
    frozen = artifact.read_text(encoding="utf-8")
    artifact.write_text("{}\n", encoding="utf-8")
    try:
        with pytest.raises(ValueError, match="pre-spawn artifact is unavailable|changed identity"):
            validate_formal_task_attempt_outcome(contract, outcome)
    finally:
        artifact.write_text(frozen, encoding="utf-8")
    replay_contract = replace(contract, contract_id=contract.contract_id + ":replay")
    with pytest.raises(ValueError, match="crossed its contract|changed identity"):
        validate_formal_task_attempt_outcome(replay_contract, outcome)
    monkeypatch.setattr(subscription_runtime, "_run_cli_unbudgeted", original_run)


def test_roundtrip_reviewer_cli_uses_its_frozen_model_and_restores_formalizer(
    monkeypatch,
) -> None:
    from ztare.leanmill.solver import autoformalize

    observed: dict[str, str] = {}

    def fake_cli(_prompt, *, runtime, timeout_s, agent_tag):
        observed.update({
            "runtime": runtime,
            "timeout_s": str(timeout_s),
            "agent_tag": agent_tag,
            "model": __import__("os").environ.get(
                "ZTARE_CODEX_AGENT_MODEL", ""
            ),
            "effort": __import__("os").environ.get(
                "ZTARE_CODEX_AGENT_REASONING_EFFORT", ""
            ),
        })
        return "reviewed"

    monkeypatch.setattr(autoformalize, "_cli_text", fake_cli)
    monkeypatch.setenv("ZTARE_CODEX_AGENT_MODEL", "gpt-formalizer")
    monkeypatch.setenv("ZTARE_CODEX_AGENT_REASONING_EFFORT", "high")
    monkeypatch.setenv(
        "ZTARE_LEANMILL_ROUNDTRIP_AGENT_MODEL", "gpt-reviewer"
    )
    monkeypatch.setenv(
        "ZTARE_LEANMILL_ROUNDTRIP_AGENT_REASONING_EFFORT", "xhigh"
    )

    assert autoformalize._roundtrip_cli_text(
        "judge this statement",
        runtime="codex",
        timeout_s=77,
        label="faithfulness-reviewer:test",
    ) == "reviewed"
    assert observed == {
        "runtime": "codex",
        "timeout_s": "77",
        "agent_tag": "faithfulness-reviewer:test",
        "model": "gpt-reviewer",
        "effort": "xhigh",
    }
    assert __import__("os").environ["ZTARE_CODEX_AGENT_MODEL"] == (
        "gpt-formalizer"
    )
    assert __import__("os").environ[
        "ZTARE_CODEX_AGENT_REASONING_EFFORT"
    ] == "high"


def test_consumption_materializes_declared_finite_residual_and_adjudication(
    tmp_path,
) -> None:
    context = _context()
    contract = _contract(context, finite_residual=True)
    program = TheoryProgram(
        campaign_id="campaign:test",
        lineage_id="lineage:test",
        context_hash=context.context_hash,
        context_epoch=0,
        presentation_formula_ids=context.formula_ids,
        prediction_formula_ids=(),
        selection_receipt_id="selection:finite-residual",
        schema=THEORY_PROGRAM_V2,
        task_discharge_contracts=(contract,),
    )
    navigation = {
        "finalists": [{
            "formula_ids": list(context.formula_ids),
            "boundary_target_ids": [],
            "theory_program_id": program.program_id,
            "theory_program": program.to_json(),
        }],
        "lineage_synthesis": {
            "route": "proceed_boundary",
            "objective_contract": {
                "schema": "leanmill.frontier_objective_contract.v1",
                "instruction": "Adjudicate the finite generalization.",
            },
            "program_ids": [program.program_id],
        },
    }
    boundary = _boundary(contract)
    bundle = _adjudicate_theory_program_tasks(
        tmp_path,
        adapter_id="generic_fol_finite.v1",
        navigation=navigation,
        boundary_result=boundary,
    )
    run_core = {
        "status": "frontier_candidates_frozen_awaiting_boundary_approval",
        "context_hash": context.context_hash,
        "navigation": navigation,
    }
    _consume_theory_task_discharge(
        tmp_path,
        {**run_core, "run_digest": content_hash(run_core)},
        {"boundary_result": boundary, "theory_task_discharge": bundle},
    )

    residuals = list(tmp_path.glob("generalization_residual.*.json"))
    adjudications = list(tmp_path.glob("generalization_adjudication.*.json"))
    assert len(residuals) == len(adjudications) == 1
    residual = json.loads(residuals[0].read_text())
    adjudication = json.loads(adjudications[0].read_text())
    assert residual["source_scope"] == "proved_finite_witness"
    assert adjudication["residual_id"] == residual["residual_id"]
    assert adjudication["terminal_state"] == "refuted_general"


def test_authoritative_terminal_action_refuses_undisposed_frozen_lineage(
    tmp_path,
) -> None:
    context, source_blueprint = _context_and_blueprint()
    contract = _contract(context)
    program = TheoryProgram(
        campaign_id="campaign:test",
        lineage_id="lineage:test",
        context_hash=context.context_hash,
        context_epoch=0,
        presentation_formula_ids=context.formula_ids,
        prediction_formula_ids=(),
        selection_receipt_id="selection:premature-stop",
        schema=THEORY_PROGRAM_V2,
        task_discharge_contracts=(contract,),
    )
    navigation = {
        "finalists": [
            {
                "candidate_kind": "theory_program",
                "formula_ids": list(program.presentation_formula_ids),
                "boundary_target_ids": [],
                "residual_prediction_formula_ids": [],
                "theory_program_id": program.program_id,
                "theory_program": program.to_json(),
            }
        ]
    }
    boundary = _boundary(contract)
    bundle = _adjudicate_theory_program_tasks(
        tmp_path,
        adapter_id="generic_fol_finite.v1",
        navigation=navigation,
        boundary_result=boundary,
    )
    blueprint = replace(
        source_blueprint,
        navigator_contract={
            **source_blueprint.navigator_contract,
            "selection_mode": "theory_program",
        },
        verification_plan={"post_freeze_interpretation": False},
    )
    write_json_atomic(tmp_path / "blueprint.json", blueprint.to_json())
    completion_core = {
        "schema": "leanmill.frontier_boundary_completion.v1",
        "status": "campaign_completed",
        "boundary_result": boundary,
        "theory_task_discharge": bundle,
    }
    write_json_atomic(
        tmp_path / "boundary_completion.json",
        {
            **completion_core,
            "completion_sha256": content_hash(completion_core),
        },
    )
    run_core = {
        "status": "frontier_candidates_frozen_awaiting_boundary_approval",
        "context_hash": context.context_hash,
        "navigation": navigation,
    }
    run = {**run_core, "run_digest": content_hash(run_core)}
    write_json_atomic(tmp_path / "run.json", run)

    assert next_frontier_campaign_action(tmp_path) == (
        "resolve_terminal_obligations"
    )
    gate = __import__("json").loads(
        (tmp_path / "campaign_closure_gate.json").read_text()
    )
    assert gate["missing_lineage_disposition_ids"] == [program.lineage_id]
    updated = _open_terminal_obligation_feedback(tmp_path, run)
    assert updated["status"] == "frontier_objective_unmet"
    assert updated["navigation"]["objective_review_history"][-1]["schema"] == (
        "leanmill.terminal_obligation_feedback.v1"
    )


def test_two_lineage_driver_consumes_leaf_authored_sibling_supersession(
    tmp_path,
    monkeypatch,
) -> None:
    import ztare.leanmill.frontier_campaign_runner as runner

    context, source_blueprint = _context_and_blueprint()
    source_contract = _contract(context)

    def owned_contract(lineage_id: str) -> TaskDischargeContract:
        return TaskDischargeContract(
            contract_id=source_contract.contract_id + ":" + lineage_id,
            adjudicator_id=source_contract.adjudicator_id,
            lifecycle_scope=source_contract.lifecycle_scope,
            owner=lineage_id,
            parameters=source_contract.parameters,
        )

    first_contract = owned_contract("lineage:f0")
    second_contract = owned_contract("lineage:f1")
    first = TheoryProgram(
        campaign_id="campaign:test",
        lineage_id="lineage:f0",
        context_hash=context.context_hash,
        context_epoch=0,
        presentation_formula_ids=context.formula_ids,
        prediction_formula_ids=(),
        selection_receipt_id="selection:f0",
        schema=THEORY_PROGRAM_V2,
        task_discharge_contracts=(first_contract,),
    )
    second = TheoryProgram(
        campaign_id="campaign:test",
        lineage_id="lineage:f1",
        context_hash=context.context_hash,
        context_epoch=0,
        presentation_formula_ids=context.formula_ids,
        prediction_formula_ids=(),
        selection_receipt_id="selection:f1",
        schema=THEORY_PROGRAM_V2,
        task_discharge_contracts=(second_contract,),
    )
    second_disposition = lineage_disposition_from_terminal_transition(
        context_hash=context.context_hash,
        lineage_id=second.lineage_id,
        transition_receipt=_budget_stop_receipt(context.context_hash),
    )
    write_json_atomic(
        tmp_path / "lineage_disposition.f1.json", second_disposition
    )
    environment = axiompack_leaf_workbench_action_environment(
        context=context,
        selection_mode="theory_program",
        theory_adapter_id="generic_fol_finite.v1",
        theory_adapter_config={},
        campaign_id="campaign:test",
        lineage_id=first.lineage_id,
    )
    action_receipt = environment["action_handlers"][
        "propose_lineage_disposition"
    ](
        ".",
        {
            "input_refs": {
                "terminal_state": "superseded",
                "reason": (
                    "the sibling discharged the stronger printed-question "
                    "obstruction after reviewed recurrence evidence"
                ),
                "evidence_refs": [second_disposition["receipt_sha256"]],
            }
        },
        None,
        environment["contract"],
    )
    finalists = [
        {
            "theory_program_id": program.program_id,
            "theory_program": program.to_json(),
            "baseline_evaluator_ref": CHEAP_CONSEQUENCE_EVALUATOR_REF,
            "formula_ids": list(program.presentation_formula_ids),
            "boundary_target_ids": [],
        }
        for program in (first, second)
    ]
    navigation = {
        "finalists": finalists,
        "trace": [{
            "decision": "request",
            "capability_id": "propose_lineage_disposition",
            "receipt": action_receipt,
        }],
    }
    run_core = {
        "status": "frontier_objective_discharged",
        "context_hash": context.context_hash,
        "navigation": navigation,
    }
    write_json_atomic(
        tmp_path / "run.json",
        {**run_core, "run_digest": content_hash(run_core)},
    )
    write_json_atomic(
        tmp_path / "blueprint.json",
        replace(
            source_blueprint,
            verification_plan={"post_freeze_interpretation": False},
        ).to_json(),
    )
    write_json_atomic(tmp_path / "budget.json", {"budget_digest": "budget:test"})
    monkeypatch.setattr(
        runner, "_boundary_completion_covers", lambda *_args, **_kwargs: True
    )
    monkeypatch.setattr(
        runner, "_boundary_search_feedback", lambda *_args, **_kwargs: None
    )

    assert drive_frontier_campaign(tmp_path) == tmp_path
    dispositions = [
        json.loads(path.read_text())
        for path in tmp_path.glob("lineage_disposition.*.json")
    ]
    by_lineage = {row["lineage_id"]: row for row in dispositions}
    assert by_lineage[first.lineage_id]["terminal_state"] == "superseded"
    assert by_lineage[first.lineage_id]["authority"] == (
        "leaf_authored_workbench_disposition_host_validated"
    )
    gate = json.loads((tmp_path / "campaign_closure_gate.json").read_text())
    assert gate["ready"] is True


def test_terminal_gate_ignores_historical_context_dispositions(
    tmp_path,
) -> None:
    context = _context()
    contract = _contract(context)
    program = TheoryProgram(
        campaign_id="campaign:test",
        lineage_id="lineage:current",
        context_hash=context.context_hash,
        context_epoch=2,
        presentation_formula_ids=context.formula_ids,
        prediction_formula_ids=(),
        selection_receipt_id="selection:current",
        schema=THEORY_PROGRAM_V2,
        task_discharge_contracts=(contract,),
    )
    run_core = {
        "status": "budget_stopped",
        "context_hash": context.context_hash,
        "navigation": {
            "finalists": [
                {
                    "candidate_kind": "theory_program",
                    "formula_ids": list(program.presentation_formula_ids),
                    "boundary_target_ids": [],
                    "theory_program_id": program.program_id,
                    "theory_program": program.to_json(),
                }
            ]
        },
    }
    run = {**run_core, "run_digest": content_hash(run_core)}
    write_json_atomic(tmp_path / "run.json", run)
    write_json_atomic(
        tmp_path / "budget_stop_receipt.json",
        _budget_stop_receipt(context.context_hash),
    )
    historical = lineage_disposition_from_terminal_transition(
        context_hash="context:prior",
        lineage_id="lineage:prior",
        transition_receipt=_budget_stop_receipt("context:prior"),
    )
    write_json_atomic(
        tmp_path / "lineage_disposition.historical.json", historical
    )

    assert next_frontier_campaign_action(tmp_path) == "complete"
    gate = json.loads((tmp_path / "campaign_closure_gate.json").read_text())
    assert gate["ready"] is True
    assert gate["frozen_lineage_ids"] == [program.lineage_id]
    assert len(list(tmp_path.glob("lineage_disposition.*.json"))) == 2


def test_budget_reopen_supersedes_same_lineage_stop_disposition(
    tmp_path,
) -> None:
    context_hash = "context:reopened"
    lineage_id = "lineage:reopened"
    budget = budget_preset("smoke_20m")
    ledger = ExplorationBudgetLedger(
        tmp_path / "budget.events.jsonl",
        budget,
        attempt_id=tmp_path.name,
    )
    stop = ledger.stop_receipt(
        "blocked_before_action:smt_calls",
        context_hash=context_hash,
    ).to_json()
    disposition = lineage_disposition_from_terminal_transition(
        context_hash=context_hash,
        lineage_id=lineage_id,
        transition_receipt=stop,
    )
    write_json_atomic(
        tmp_path / "lineage_disposition.stopped.json", disposition
    )
    ledger.extend_resources(
        phase="boundary",
        resources={"smt_calls": 1},
        authority_ref="user:continue:test",
        reason="resume the same frozen lineage",
    )
    extension = json.loads(
        (tmp_path / "budget.events.jsonl").read_text().splitlines()[-1]
    )
    reopen_core = {
        "schema": "leanmill.boundary_budget_extension_reopen.v1",
        "context_hash": context_hash,
        "prior_run_digest": "run:stopped",
        "boundary_completion_sha256": "completion:stopped",
        "superseded_budget_stop_receipt": stop,
        "extension_event_sha256": extension["event_sha256"],
        "authority": "deterministic_campaign_lifecycle",
    }
    write_json_atomic(
        tmp_path / "boundary_budget_extension_reopen.test.json",
        {**reopen_core, "receipt_sha256": content_hash(reopen_core)},
    )

    assert _active_lineage_disposition_rows(
        tmp_path,
        context_hash=context_hash,
        lineage_ids=(lineage_id,),
    ) == ()


def test_stopped_campaign_blocks_on_unadjudicated_finite_generalization(
    tmp_path,
) -> None:
    context = _context()
    contract = _contract(context, finite_residual=True)
    program = TheoryProgram(
        campaign_id="campaign:test",
        lineage_id="lineage:test",
        context_hash=context.context_hash,
        context_epoch=0,
        presentation_formula_ids=context.formula_ids,
        prediction_formula_ids=(),
        selection_receipt_id="selection:stopped-residual",
        schema=THEORY_PROGRAM_V2,
        task_discharge_contracts=(contract,),
    )
    run_core = {
        "status": "budget_stopped",
        "context_hash": context.context_hash,
        "navigation": {
            "finalists": [
                {
                    "candidate_kind": "theory_program",
                    "formula_ids": list(program.presentation_formula_ids),
                    "boundary_target_ids": [],
                    "theory_program_id": program.program_id,
                    "theory_program": program.to_json(),
                }
            ]
        },
    }
    write_json_atomic(
        tmp_path / "run.json",
        {**run_core, "run_digest": content_hash(run_core)},
    )
    write_json_atomic(
        tmp_path / "budget_stop_receipt.json",
        _budget_stop_receipt(context.context_hash),
    )
    assert next_frontier_campaign_action(tmp_path) == (
        "terminal_obligations_blocked"
    )
    residual_paths = list(tmp_path.glob("generalization_residual.*.json"))
    assert len(residual_paths) == 1
    residual = json.loads(residual_paths[0].read_text())
    gate = __import__("json").loads(
        (tmp_path / "campaign_closure_gate.json").read_text()
    )
    assert gate["missing_lineage_disposition_ids"] == []
    assert gate["unadjudicated_generalization_residual_ids"] == [
        residual["residual_id"]
    ]
    assert next_frontier_campaign_action(tmp_path) == (
        "terminal_obligations_blocked"
    )
