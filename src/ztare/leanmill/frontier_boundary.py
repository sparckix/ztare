"""Budgeted boundary execution for frozen frontier-theory finalists."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from ztare.leanmill.exploration_budget import BudgetExceeded, ExplorationBudgetLedger
from ztare.leanmill.context_epoch import propose_context_epoch
from ztare.leanmill.frontier_blueprint import FrontierTheoryBlueprint
from ztare.leanmill.lean_consequence_bridge import LeanConsequenceTask, render_lean_consequence_task
from ztare.leanmill.theory_campaign_journal import TheoryCampaignEvent, TheoryCampaignJournal
from ztare.leanmill.theory_conflict_ledger import (
    TheoryConflictLedger,
    finite_countermodel_conflict_receipt,
    theory_implication_signature,
)
from ztare.leanmill.theory_context import TheoryLandscapeContext
from ztare.leanmill.theory_interest import profile_theory_program_predictions
from ztare.leanmill.theory_ir import AxiomFormula, TheorySignature, content_hash
from ztare.leanmill.theory_program import TheoryProgram


LeanExecutorFn = Callable[..., Mapping[str, Any]]
IsabelleExecutorFn = Callable[..., Mapping[str, Any]]
RawBoundaryFn = Callable[
    [TheoryLandscapeContext, tuple[str, ...], str, Mapping[str, Any]],
    Mapping[str, Any],
]
CountermodelFn = Callable[..., Any]
SinglePremiseAuditFn = Callable[[tuple[str, ...], str], Mapping[str, Any]]


@dataclass(frozen=True)
class FrontierBoundaryResult:
    context_hash: str
    query_results: tuple[Mapping[str, Any], ...]
    stop_reason: str
    next_epoch_proposal: Mapping[str, Any] | None = None
    schema: str = "leanmill.frontier_boundary_result.v1"

    def to_json(self) -> dict[str, Any]:
        core = {
            "schema": self.schema,
            "context_hash": self.context_hash,
            "query_results": [dict(row) for row in self.query_results],
            "stop_reason": self.stop_reason,
            "next_epoch_proposal": (
                dict(self.next_epoch_proposal)
                if self.next_epoch_proposal is not None else None
            ),
        }
        return {**core, "result_sha256": content_hash(core)}


def _journal(
    journal: TheoryCampaignJournal,
    *,
    attempt_id: str,
    campaign_id: str,
    epoch: int,
    context_hash: str,
    event_type: str,
    subject_id: str,
    input_refs: Sequence[str],
    output_ref: str,
    evidence_status: str,
    authority: str,
) -> None:
    journal.append(
        TheoryCampaignEvent(
            attempt_id=attempt_id,
            campaign_id=campaign_id,
            epoch=epoch,
            context_hash=context_hash,
            event_type=event_type,
            subject_ids=(subject_id,),
            input_refs=tuple(input_refs),
            output_refs=(output_ref,),
            evidence_status=evidence_status,
            authority=authority,
        )
    )


def _larger_model_strata(
    signature: TheorySignature, plan: Mapping[str, Any]
) -> tuple[tuple[tuple[str, int], ...], ...]:
    declared = plan.get("larger_model_strata")
    if declared is not None:
        if not isinstance(declared, list):
            raise ValueError("larger_model_strata must be a list")
        rows = []
        for row in declared:
            if not isinstance(row, Mapping) or set(row) != {"sort_sizes"}:
                raise ValueError("larger model strata require one sort_sizes object")
            raw = row["sort_sizes"]
            if not isinstance(raw, Mapping):
                raise ValueError("larger model sort_sizes must be an object")
            sizes = tuple(sorted((str(key), value) for key, value in raw.items()))
            if (
                {key for key, _value in sizes} != set(signature.sort_map)
                or any(type(value) is not int or value < 1 for _key, value in sizes)
            ):
                raise ValueError("larger model stratum must size every signature sort")
            rows.append(sizes)
        return tuple(rows)
    carriers = plan.get("larger_carriers") or ()
    if not carriers:
        return ()
    if len(signature.sorts) != 1:
        raise ValueError("larger_carriers shorthand requires a one-sort signature")
    sort = signature.sorts[0].name
    if any(type(size) is not int or size < 1 for size in carriers):
        raise ValueError("larger_carriers must contain positive integers")
    return tuple(((sort, size),) for size in carriers)


def run_frontier_boundaries(
    context: TheoryLandscapeContext,
    blueprint: FrontierTheoryBlueprint,
    navigation: Mapping[str, Any],
    journal: TheoryCampaignJournal,
    budget_ledger: ExplorationBudgetLedger,
    *,
    attempt_id: str,
    campaign_id: str,
    lean_executor_fn: LeanExecutorFn | None = None,
    isabelle_executor_fn: IsabelleExecutorFn | None = None,
    raw_boundary_fn: RawBoundaryFn | None = None,
    countermodel_fn: CountermodelFn | None = None,
    single_premise_audit_fn: SinglePremiseAuditFn | None = None,
    conflict_ledger: TheoryConflictLedger | None = None,
) -> FrontierBoundaryResult:
    """Execute navigator-selected residual predictions under the campaign budget."""
    finalists = tuple(navigation.get("finalists") or ())
    query_limit = int(
        blueprint.query_budget.get(
            "larger_model_queries",
            blueprint.query_budget.get("boundary_queries", len(finalists) * 2 or 1),
        )
    )
    plan = dict(blueprint.verification_plan)
    results: list[dict[str, Any]] = []
    stop_reason = "campaign_finished"
    seen: set[tuple[tuple[str, ...], str]] = set()
    epoch_evidence_refs: list[str] = []
    epoch_additions: list[dict[str, Any]] = []
    boundary_queries_used = 0
    context_epoch = max(
        (
            event.epoch
            for event in journal.replay()
            if event.context_hash == context.context_hash
        ),
        default=0,
    )

    axiom_map = {
        row.formula_id: row.axiom
        for row in getattr(context, "formula_profiles", ())
        if hasattr(row, "axiom")
    }
    larger_strata = _larger_model_strata(context.signature, plan)
    if larger_strata and countermodel_fn is None:
        from ztare.leanmill.theory_adapter_registry import (
            materialize_theory_adapter_capability,
        )

        countermodel_fn = materialize_theory_adapter_capability(
            blueprint.adapter_id,
            "fixed_size_countermodel_finder",
            signature=context.signature,
            adapter_config=blueprint.adapter_config,
        )

    for finalist in finalists:
        premises = tuple(sorted(str(row) for row in finalist.get("formula_ids") or ()))
        candidate_kind = str(
            finalist.get("candidate_kind") or "compact_axiom_pack"
        )
        residual_targets = tuple(
            str(row)
            for row in (
                finalist.get("residual_prediction_formula_ids")
                if candidate_kind == "theory_program"
                else finalist.get("residual_joint_only_consequence_ids")
                or finalist.get("joint_only_consequence_ids")
                or ()
            )
        )
        nominated_targets = finalist.get("boundary_target_ids")
        if candidate_kind == "theory_program":
            program = TheoryProgram.from_json(finalist.get("theory_program"))
            targets = tuple(str(row) for row in nominated_targets or ())
            if (
                not targets
                or len(set(targets)) != len(targets)
                or targets != program.prediction_formula_ids
                or program.presentation_formula_ids != premises
                or program.context_hash != context.context_hash
            ):
                raise ValueError(
                    "theory-program boundary targets must match its frozen predictions"
                )
            prediction_profile = profile_theory_program_predictions(
                context, premises, targets
            )
            supplied_profile = finalist.get("prediction_profile")
            if isinstance(supplied_profile, Mapping) and (
                supplied_profile.get("receipt_sha256")
                != prediction_profile["receipt_sha256"]
            ):
                raise ValueError("theory-program prediction profile no longer replays")
            seed_prediction_rows = {
                str(row["prediction_formula_id"]): dict(row)
                for row in prediction_profile["predictions"]
            }
        elif nominated_targets:
            targets = tuple(str(row) for row in nominated_targets)
            if len(set(targets)) != len(targets) or any(
                row not in residual_targets for row in targets
            ):
                raise ValueError(
                    "compact-pack boundary targets must be distinct residual consequences"
                )
            seed_prediction_rows = {}
        else:
            targets = tuple(sorted(residual_targets))
            seed_prediction_rows = {}
        for target_id in targets:
            key = (premises, target_id)
            if key in seen or boundary_queries_used >= query_limit:
                continue
            seen.add(key)
            soft_stop = budget_ledger.soft_stop_reason(
                allow_coverage_target=False
            )
            if soft_stop is not None:
                stop_reason = soft_stop
                break
            pack_dependency_candidate = target_id in {
                str(value)
                for value in (
                    finalist.get("joint_only_consequence_ids")
                    or finalist.get("residual_joint_only_consequence_ids")
                    or ()
                )
            }
            row: dict[str, Any] = {
                "premise_formula_ids": list(premises),
                "target_formula_id": target_id,
                "candidate_kind": candidate_kind,
                "logical_premise_ablation": {"status": "not_configured"},
                "pack_synergy_status": (
                    "unresolved"
                    if pack_dependency_candidate
                    else "not_claimed_theory_program"
                ),
                "program_prediction_status": "pending",
                "seed_context_prediction": seed_prediction_rows.get(target_id),
                "countermodel_searches": [],
                "isabelle": {"status": "not_requested"},
                "lean": {"status": "not_requested"},
                "formal_consensus": {"status": "not_requested"},
            }
            seed_prediction = seed_prediction_rows.get(target_id)
            if (
                isinstance(seed_prediction, Mapping)
                and seed_prediction.get("chart_status") == "refuted_in_context"
            ):
                witness_id = str(seed_prediction.get("counterexample_object_id") or "")
                if not witness_id:
                    raise ValueError("seed-context refutation lacks its witness identity")
                seed_core = {
                    "schema": "leanmill.seed_context_prediction_refutation.v1",
                    "context_hash": context.context_hash,
                    "premise_formula_ids": list(premises),
                    "target_formula_id": target_id,
                    "witness_object_id": witness_id,
                    "witness": dict(context.anonymous_object_profile(witness_id)),
                    "claim_boundary": str(prediction_profile["claim_boundary"]),
                    "authority": "host_context_replay",
                }
                seed_receipt = {
                    **seed_core,
                    "receipt_sha256": content_hash(seed_core),
                }
                row["program_prediction_status"] = "refuted_in_seed_context"
                row["countermodel_searches"] = [seed_receipt]
                row["logical_premise_ablation"] = {
                    "status": "skipped_seed_context_counterexample"
                }
                row["isabelle"] = {"status": "skipped_seed_context_counterexample"}
                row["lean"] = {"status": "skipped_seed_context_counterexample"}
                _journal(
                    journal,
                    attempt_id=attempt_id,
                    campaign_id=campaign_id,
                    epoch=context_epoch,
                    context_hash=context.context_hash,
                    event_type="countermodel_found",
                    subject_id=target_id,
                    input_refs=premises,
                    output_ref=str(seed_receipt["receipt_sha256"]),
                    evidence_status="witnessed",
                    authority="host_context_replay",
                )
                budget_ledger.observe_information(
                    action_id=f"boundary:{target_id}:seed-context",
                    marginal_information_per_cost_ppm=1_000_000,
                    coverage_ppm=min(
                        1_000_000,
                        len(results + [row]) * 1_000_000 // max(1, query_limit),
                    ),
                    evidence_refs=(str(seed_receipt["receipt_sha256"]),),
                )
                results.append(row)
                continue
            conflict_signature = theory_implication_signature(
                context.signature.content_hash, premises, target_id
            )
            prior_conflict = (
                conflict_ledger.blocks(conflict_signature)
                if conflict_ledger is not None
                else None
            )
            if prior_conflict is not None:
                provenance = (
                    dict(prior_conflict.provenance)
                    if isinstance(prior_conflict.provenance, Mapping)
                    else {}
                )
                if provenance.get("conflict_kind") != "finite_countermodel":
                    raise ValueError("theory implication memory has an incompatible conflict kind")
                replay_core = {
                    "schema": "leanmill.replayed_theory_conflict.v1",
                    "candidate_signature": conflict_signature,
                    "context_hash": context.context_hash,
                    "source_context_hash": str(
                        provenance.get("source_context_hash") or ""
                    ),
                    "witness_ref": str(provenance.get("witness_ref") or ""),
                    "witness_summary": prior_conflict.witness_summary,
                    "authority": "host_witness_replay",
                }
                replay = {**replay_core, "receipt_sha256": content_hash(replay_core)}
                row["logical_premise_ablation"] = {
                    "status": "skipped_replayed_countermodel"
                }
                if pack_dependency_candidate:
                    row["pack_synergy_status"] = "refuted_by_replayed_countermodel"
                row["program_prediction_status"] = "refuted_by_replayed_countermodel"
                row["countermodel_searches"] = [replay]
                row["isabelle"] = {"status": "skipped_replayed_countermodel"}
                row["lean"] = {"status": "skipped_replayed_countermodel"}
                _journal(
                    journal,
                    attempt_id=attempt_id,
                    campaign_id=campaign_id,
                    epoch=context_epoch,
                    context_hash=context.context_hash,
                    event_type="countermodel_found",
                    subject_id=target_id,
                    input_refs=premises,
                    output_ref=str(replay["receipt_sha256"]),
                    evidence_status="witnessed",
                    authority="replayed_theory_conflict",
                )
                results.append(row)
                continue
            if single_premise_audit_fn is not None:
                audit = dict(single_premise_audit_fn(premises, target_id))
                if audit.get("schema") not in {
                    "leanmill.source_single_premise_ablation.v1",
                    "leanmill.finite_context_single_premise_ablation.v1",
                }:
                    raise ValueError("single-premise oracle returned an unknown contract")
                if tuple(audit.get("premise_formula_ids") or ()) != premises:
                    raise ValueError("single-premise oracle returned another premise pack")
                if audit.get("target_formula_id") != target_id:
                    raise ValueError("single-premise oracle returned another target")
                audit_core = {
                    key: value for key, value in audit.items() if key != "receipt_sha256"
                }
                if audit.get("receipt_sha256") != content_hash(audit_core):
                    raise ValueError("single-premise oracle receipt digest mismatch")
                row["logical_premise_ablation"] = audit
                if audit.get("status") == "refuted_by_known_single_premise":
                    if pack_dependency_candidate:
                        row["pack_synergy_status"] = "refuted_known_single_premise"
                    row["program_prediction_status"] = (
                        "source_known_single_premise_consequence"
                    )
                    row["isabelle"] = {"status": "skipped_known_single_premise"}
                    row["lean"] = {"status": "skipped_known_single_premise"}
                    receipt_ref = str(audit["receipt_sha256"])
                    _journal(
                        journal,
                        attempt_id=attempt_id,
                        campaign_id=campaign_id,
                        epoch=context_epoch,
                        context_hash=context.context_hash,
                        event_type="boundary_query_completed",
                        subject_id=target_id,
                        input_refs=premises,
                        output_ref=receipt_ref,
                        evidence_status="witnessed",
                        authority="source_bound_single_premise_oracle",
                    )
                    results.append(row)
                    continue
            try:
                query_reservation = budget_ledger.reserve(
                    f"boundary:{target_id}",
                    "boundary",
                    {"boundary_queries": 1},
                )
            except BudgetExceeded as exc:
                stop_reason = exc.reason
                break
            budget_ledger.commit(query_reservation)
            boundary_queries_used += 1

            if blueprint.mode == "evidence_induced":
                if raw_boundary_fn is None:
                    raw = {
                        "schema": "leanmill.raw_boundary_check.v1",
                        "status": "unresolved",
                        "reason": "raw_boundary_checker_not_injected",
                    }
                else:
                    raw = dict(raw_boundary_fn(context, premises, target_id, plan))
                row["raw_boundary"] = raw
                raw_ref = str(raw.get("receipt_sha256") or content_hash(raw))
                status = str(raw.get("status") or "unresolved")
                if status in {"counterexample_found", "refuted"}:
                    epoch_evidence_refs.append(raw_ref)
                    epoch_additions.append(
                        {
                            "kind": "raw_counterexample",
                            "target_formula_id": target_id,
                            "premise_formula_ids": list(premises),
                            "witness_receipt_ref": raw_ref,
                        }
                    )
                _journal(
                    journal,
                    attempt_id=attempt_id,
                    campaign_id=campaign_id,
                    epoch=context_epoch,
                    context_hash=context.context_hash,
                    event_type=(
                        "countermodel_found" if status in {"counterexample_found", "refuted"}
                        else "boundary_query_completed"
                    ),
                    subject_id=target_id,
                    input_refs=premises,
                    output_ref=raw_ref,
                    evidence_status="witnessed" if status != "unresolved" else "unresolved",
                    authority="raw_boundary_checker",
                )
                information = 1_000_000 if status in {"counterexample_found", "refuted", "verified"} else 0
                budget_ledger.observe_information(
                    action_id=f"boundary:{target_id}:raw",
                    marginal_information_per_cost_ppm=information,
                    coverage_ppm=min(1_000_000, len(results + [row]) * 1_000_000 // max(1, query_limit)),
                    evidence_refs=(raw_ref,),
                )
                results.append(row)
                continue

            refuted = False
            if (
                countermodel_fn is not None
                and larger_strata
                and target_id in axiom_map
                and all(item in axiom_map for item in premises)
            ):
                timeout_ms = int(plan.get("smt_timeout_ms", 30_000))
                for size_vector in larger_strata:
                    sizes = dict(size_vector)
                    stratum_ref = content_hash({"sort_sizes": sizes})[:16]
                    try:
                        smt_reservation = budget_ledger.reserve(
                            f"boundary:{target_id}:smt:{stratum_ref}",
                            "boundary",
                            {"smt_calls": 1, "smt_millis": timeout_ms},
                        )
                    except BudgetExceeded as exc:
                        stop_reason = exc.reason
                        break
                    try:
                        receipt = countermodel_fn(
                            tuple(axiom_map[item] for item in premises),
                            axiom_map[target_id],
                            sort_sizes=sizes,
                            base_axioms=tuple(context.base_axioms),
                            timeout_ms=timeout_ms,
                        )
                    finally:
                        budget_ledger.commit(smt_reservation)
                    receipt_json = receipt.to_json()
                    row["countermodel_searches"].append(receipt_json)
                    receipt_ref = str(receipt_json["receipt_sha256"])
                    if receipt.status == "countermodel_found":
                        refuted = True
                        if pack_dependency_candidate:
                            row["pack_synergy_status"] = "refuted_by_larger_model"
                        row["program_prediction_status"] = "refuted_by_larger_model"
                        epoch_evidence_refs.append(receipt_ref)
                        epoch_additions.append(
                            {
                                "kind": "finite_countermodel",
                                "target_formula_id": target_id,
                                "premise_formula_ids": list(premises),
                                "sort_sizes": sizes,
                                "witness_receipt_ref": receipt_ref,
                            }
                        )
                        _journal(
                            journal,
                            attempt_id=attempt_id,
                            campaign_id=campaign_id,
                            epoch=context_epoch,
                            context_hash=context.context_hash,
                            event_type="countermodel_found",
                            subject_id=target_id,
                            input_refs=premises,
                            output_ref=receipt_ref,
                            evidence_status="witnessed",
                            authority="finite_smt_plus_host_replay",
                        )
                        budget_ledger.observe_information(
                            action_id=f"boundary:{target_id}:smt:{stratum_ref}",
                            marginal_information_per_cost_ppm=1_000_000,
                            coverage_ppm=min(1_000_000, len(results + [row]) * 1_000_000 // max(1, query_limit)),
                            evidence_refs=(receipt_ref,),
                        )
                        if conflict_ledger is not None:
                            conflict_receipt = finite_countermodel_conflict_receipt(
                                context, premises, target_id, receipt_json
                            )
                            clause = conflict_ledger.learn(conflict_receipt)
                            _journal(
                                journal,
                                attempt_id=attempt_id,
                                campaign_id=campaign_id,
                                epoch=context_epoch,
                                context_hash=context.context_hash,
                                event_type="conflict_learned",
                                subject_id=clause.signature,
                                input_refs=(*premises, target_id),
                                output_ref=receipt_ref,
                                evidence_status="witnessed",
                                authority="finite_countermodel_host_replay",
                            )
                        break
                if stop_reason.startswith("blocked_before_action"):
                    results.append(row)
                    break

            if (
                not refuted
                and plan.get("conditional_isabelle") is True
                and target_id in axiom_map
                and all(item in axiom_map for item in premises)
            ):
                from ztare.leanmill.solver.sledgehammer import (
                    render_theory_implication_to_isabelle,
                )

                isabelle_task = render_theory_implication_to_isabelle(
                    context.signature,
                    tuple(axiom_map[item] for item in premises),
                    axiom_map[target_id],
                    base_axioms=tuple(context.base_axioms),
                )
                row["isabelle"] = {
                    "status": "task_rendered",
                    "task": isabelle_task.to_json(),
                }
                peer_timeout_ms = int(plan.get("isabelle_timeout_ms", 120_000))
                if isabelle_executor_fn is not None and (
                    budget_ledger.remaining_capacity(
                        "boundary", "formal_peer_attempts"
                    )
                    < 1
                    or budget_ledger.remaining_capacity(
                        "boundary", "formal_peer_millis"
                    )
                    < peer_timeout_ms
                ):
                    row["isabelle"] = {
                        "status": "skipped_budget_exhausted",
                        "task_id": isabelle_task.task_id,
                    }
                elif isabelle_executor_fn is not None:
                    try:
                        peer_reservation = budget_ledger.reserve(
                            f"boundary:{target_id}:formal-peer:isabelle",
                            "boundary",
                            {
                                "formal_peer_attempts": 1,
                                "formal_peer_millis": peer_timeout_ms,
                            },
                        )
                    except BudgetExceeded as exc:
                        stop_reason = exc.reason
                        results.append(row)
                        break
                    peer_attempt: dict[str, Any] | None = None
                    try:
                        peer_attempt = dict(
                            isabelle_executor_fn(
                                isabelle_task,
                                timeout_s=max(1, peer_timeout_ms // 1_000),
                            )
                        )
                        if peer_attempt.get("schema") != "leanmill.isabelle_theory_attempt.v1":
                            raise ValueError(
                                "Isabelle boundary executor returned an unknown contract"
                            )
                        if peer_attempt.get("task_id") != isabelle_task.task_id:
                            raise ValueError("Isabelle boundary executor returned another task")
                        peer_core = {
                            key: value
                            for key, value in peer_attempt.items()
                            if key != "receipt_sha256"
                        }
                        if peer_attempt.get("receipt_sha256") != content_hash(peer_core):
                            raise ValueError(
                                "Isabelle boundary executor receipt digest mismatch"
                            )
                    except Exception:
                        budget_ledger.release(
                            peer_reservation,
                            reason="formal_peer_executor_or_contract_failure",
                        )
                        raise
                    assert peer_attempt is not None
                    budget_ledger.commit(
                        peer_reservation,
                        actual_resources=(
                            {
                                "formal_peer_attempts": 1,
                                "formal_peer_millis": peer_timeout_ms,
                            }
                            if int(peer_attempt.get("transport_calls", 0)) > 0
                            else {}
                        ),
                    )
                    peer_status = str(peer_attempt.get("status") or "unresolved")
                    row["isabelle"] = {
                        "status": peer_status,
                        "task_id": isabelle_task.task_id,
                        "attempt": peer_attempt,
                    }
                    _journal(
                        journal,
                        attempt_id=attempt_id,
                        campaign_id=campaign_id,
                        epoch=context_epoch,
                        context_hash=context.context_hash,
                        event_type=(
                            "conditional_consequence_proved"
                            if peer_status == "proved"
                            else "proof_attempt_unresolved"
                        ),
                        subject_id=target_id,
                        input_refs=premises,
                        output_ref=str(peer_attempt["receipt_sha256"]),
                        evidence_status=(
                            "proved" if peer_status == "proved" else "unresolved"
                        ),
                        authority=(
                            "isabelle_kernel"
                            if peer_status == "proved"
                            else "isabelle_peer_attempt"
                        ),
                    )

            if (
                not refuted
                and plan.get("conditional_lean") is True
                and target_id in axiom_map
                and all(item in axiom_map for item in premises)
            ):
                task = render_lean_consequence_task(
                    context.signature,
                    tuple(axiom_map[item] for item in premises),
                    axiom_map[target_id],
                    base_axioms=tuple(context.base_axioms),
                )
                row["lean"] = {"status": "task_rendered", "task": task.to_json()}
                lean_timeout_ms = int(plan.get("lean_timeout_ms", 180_000))
                if lean_executor_fn is not None and (
                    budget_ledger.remaining_capacity("boundary", "lean_attempts")
                    < 1
                    or budget_ledger.remaining_capacity("boundary", "lean_millis")
                    < lean_timeout_ms
                ):
                    row["lean"] = {
                        "status": "skipped_budget_exhausted",
                        "task_id": task.task_id,
                    }
                elif lean_executor_fn is not None:
                    try:
                        lean_reservation = budget_ledger.reserve(
                            f"boundary:{target_id}:lean",
                            "boundary",
                            {
                                "lean_attempts": 1,
                                "lean_millis": lean_timeout_ms,
                            },
                        )
                    except BudgetExceeded as exc:
                        stop_reason = exc.reason
                        results.append(row)
                        break
                    try:
                        governed = dict(
                            lean_executor_fn(task, budget_ledger=budget_ledger)
                        )
                    finally:
                        budget_ledger.commit(lean_reservation)
                    if governed.get("schema") != "leanmill.governed_consequence_attempt.v1":
                        raise ValueError("Lean boundary executor returned an unknown contract")
                    if governed.get("task_id") != task.task_id:
                        raise ValueError("Lean boundary executor returned another task")
                    governed_core = {
                        key: value for key, value in governed.items() if key != "receipt_sha256"
                    }
                    if governed.get("receipt_sha256") != content_hash(governed_core):
                        raise ValueError("Lean boundary executor receipt digest mismatch")
                    status = str(governed.get("status") or "unresolved")
                    row["lean"] = {
                        "status": status,
                        "task_id": task.task_id,
                        "governed_attempt": governed,
                    }
                    attributed = status == "proved_attributed"
                    if attributed:
                        singletons_excluded = (
                            row["logical_premise_ablation"].get("status")
                            == "certified_single_premise_nonimplication"
                        )
                        if pack_dependency_candidate:
                            row["pack_synergy_status"] = (
                                "proved_exact_two_synergy"
                                if singletons_excluded and len(premises) == 2
                                else (
                                    "proved_no_singleton_suffices"
                                    if singletons_excluded
                                    else "proved_proof_attributed_only"
                                )
                            )
                        row["program_prediction_status"] = "kernel_verified_attributed"
                    else:
                        row["program_prediction_status"] = "unresolved"
                    event_type = "conditional_consequence_proved" if attributed else "proof_attempt_unresolved"
                    _journal(
                        journal,
                        attempt_id=attempt_id,
                        campaign_id=campaign_id,
                        epoch=context_epoch,
                        context_hash=context.context_hash,
                        event_type=event_type,
                        subject_id=target_id,
                        input_refs=premises,
                        output_ref=str(governed["receipt_sha256"]),
                        evidence_status="proved" if attributed else "unresolved",
                        authority="lean_kernel_matched_attribution",
                    )
                    budget_ledger.observe_information(
                        action_id=f"boundary:{target_id}:lean",
                        marginal_information_per_cost_ppm=1_000_000 if attributed else 0,
                        coverage_ppm=min(1_000_000, len(results + [row]) * 1_000_000 // max(1, query_limit)),
                        evidence_refs=(str(governed["receipt_sha256"]),),
                    )
            if row["isabelle"].get("status") == "proved":
                from ztare.common.cross_substrate_consensus import (
                    SubstrateVerdict,
                    cross_substrate_consensus,
                )
                from ztare.common.governed_verification import CheckResult

                peer_attempt = dict(row["isabelle"].get("attempt") or {})
                verdicts = [
                    SubstrateVerdict(
                        "isabelle",
                        CheckResult(
                            True,
                            str(peer_attempt.get("diagnostics") or "isabelle accepted"),
                            "isabelle",
                        ),
                        translation_digest=content_hash(
                            {"task_id": row["isabelle"].get("task_id")}
                        ),
                    )
                ]
                lean_status = str(row["lean"].get("status") or "")
                if lean_status in {"proved_attributed", "refuted_by_kernel"}:
                    verdicts.append(
                        SubstrateVerdict(
                            "lean",
                            CheckResult(
                                lean_status == "proved_attributed",
                                str(
                                    dict(row["lean"].get("governed_attempt") or {}).get(
                                        "reason"
                                    )
                                    or lean_status
                                ),
                                "lean",
                            ),
                            translation_digest=content_hash(
                                {"task_id": row["lean"].get("task_id")}
                            ),
                        )
                    )
                row["formal_consensus"] = cross_substrate_consensus(
                    f"{'+'.join(premises)} implies {target_id}",
                    verdicts,
                ).to_dict()
            if not refuted and row["lean"]["status"] in {"not_requested", "task_rendered"}:
                evidence_ref = content_hash(row)
                _journal(
                    journal,
                    attempt_id=attempt_id,
                    campaign_id=campaign_id,
                    epoch=context_epoch,
                    context_hash=context.context_hash,
                    event_type="boundary_query_completed",
                    subject_id=target_id,
                    input_refs=premises,
                    output_ref=evidence_ref,
                    evidence_status="unresolved",
                    authority="frontier_boundary_orchestrator",
                )
            results.append(row)
        if stop_reason != "campaign_finished":
            break

    proposal = propose_context_epoch(
        journal,
        attempt_id=attempt_id,
        campaign_id=campaign_id,
        context_hash=context.context_hash,
        evidence_refs=epoch_evidence_refs,
        proposed_additions=epoch_additions,
    )
    return FrontierBoundaryResult(
        context_hash=context.context_hash,
        query_results=tuple(results),
        stop_reason=stop_reason,
        next_epoch_proposal=proposal.to_json() if proposal is not None else None,
    )


__all__ = ["FrontierBoundaryResult", "run_frontier_boundaries"]
