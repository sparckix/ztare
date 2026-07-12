"""Rank witnessed disagreements between frozen theory programs."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from ztare.leanmill.theory_context import TheoryLandscapeContext
from ztare.leanmill.theory_interest import profile_theory_program_predictions
from ztare.leanmill.theory_ir import content_hash
from ztare.leanmill.theory_program import (
    TheoryProgram,
    compare_host_isolated_theory_programs,
)
from ztare.leanmill.theory_query_policy import BoundaryQuery, rank_boundary_queries


_HOLDS = {"holds_on_complete_context", "holds_on_observed_context"}


def _validate_isolation(
    receipt: Mapping[str, Any],
    programs: Sequence[TheoryProgram],
) -> None:
    core = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    expected = {(row.context_hash, row.context_epoch) for row in programs}
    receipt_lineages = {str(row) for row in receipt.get("lineage_ids") or ()}
    if (
        receipt.get("schema") != "leanmill.theory_lineage_isolation.v1"
        or receipt.get("receipt_sha256") != content_hash(core)
        or len(expected) != 1
        or (
            receipt.get("context_hash"),
            int(receipt.get("context_epoch", -1)),
        )
        != next(iter(expected))
        or not {row.lineage_id for row in programs} <= receipt_lineages
    ):
        raise ValueError("isolation receipt does not bind the theory committee")


def _chart_value(status: str) -> bool | None:
    if status in _HOLDS:
        return True
    if status == "refuted_in_context":
        return False
    if status == "vacuous_on_empty_extent":
        return None
    raise ValueError(f"unsupported prediction status: {status}")


def plan_theory_program_disagreement_lifts(
    context: TheoryLandscapeContext,
    programs: Sequence[TheoryProgram],
    *,
    isolation_receipt: Mapping[str, Any],
    query_cost_units: Mapping[str, float] | None = None,
    max_queries: int = 1,
) -> dict[str, Any]:
    """Price actual chart disagreements; choose no theory and run no boundary."""

    if type(max_queries) is not int or max_queries < 1:
        raise ValueError("max_queries must be a positive integer")
    committee = tuple(sorted(programs, key=lambda row: row.program_id))
    comparison = compare_host_isolated_theory_programs(committee)
    if any(row.context_hash != context.context_hash for row in committee):
        raise ValueError("theory committee targets another context")
    known = set(context.formula_ids)
    if any(
        (set(row.presentation_formula_ids) | set(row.prediction_formula_ids))
        - known
        for row in committee
    ):
        raise ValueError("theory committee contains unknown formulas")
    _validate_isolation(isolation_receipt, committee)

    program_ids = [row.program_id for row in committee]
    presentations = set().union(
        *(set(row.presentation_formula_ids) for row in committee)
    )
    targets = sorted(
        set().union(*(set(row.prediction_formula_ids) for row in committee))
    )
    evaluations: list[dict[str, Any]] = []
    queries: list[BoundaryQuery] = []
    target_by_query: dict[str, str] = {}
    holding_by_target: dict[str, list[str]] = {}
    profile_refs: dict[tuple[str, str], str] = {}
    costs = dict(query_cost_units or {})

    for target in targets:
        if target in presentations:
            evaluations.append(
                {
                    "target_formula_id": target,
                    "query_status": "excluded_assumed_by_committee_member",
                    "program_outcomes": {},
                }
            )
            continue
        predictions: dict[str, bool] = {}
        outcomes: dict[str, Any] = {}
        vacuous = False
        for program in committee:
            profile = profile_theory_program_predictions(
                context, program.presentation_formula_ids, (target,)
            )
            prediction = profile["predictions"][0]
            status = str(prediction["chart_status"])
            value = _chart_value(status)
            vacuous |= value is None
            if value is not None:
                predictions[program.program_id] = value
            profile_refs[(program.program_id, target)] = profile["receipt_sha256"]
            outcomes[program.program_id] = {
                "lineage_id": program.lineage_id,
                "chart_status": status,
                "counterexample_object_id": prediction.get(
                    "counterexample_object_id"
                ),
                "agent_nominated": target in program.prediction_formula_ids,
            }
        holding = [
            row.program_id
            for row in committee
            if target in row.prediction_formula_ids
            and outcomes[row.program_id]["chart_status"] in _HOLDS
        ]
        status = (
            "excluded_vacuous_program_extent"
            if vacuous
            else "excluded_unanimous_seed_prediction"
            if len(set(predictions.values())) < 2
            else "excluded_no_supported_agent_nomination"
            if not holding
            else "actionable_prediction_disagreement"
        )
        evaluations.append(
            {
                "target_formula_id": target,
                "query_status": status,
                "holding_nominator_program_ids": holding,
                "program_outcomes": outcomes,
            }
        )
        if status != "actionable_prediction_disagreement":
            continue
        query_id = "theory-program-boundary:" + content_hash(
            {
                "context_hash": context.context_hash,
                "target_formula_id": target,
                "predictions": predictions,
            }
        )
        queries.append(
            BoundaryQuery(
                query_id=query_id,
                query_type="theory_program_prediction_disagreement_boundary_lift",
                predictions=predictions,
                cost_units=float(costs.get(target, 1.0)),
                target_mapping=f"replay frozen implications for {target}",
                nearest_confuser="hold versus refute",
                falsifier="boundary countermodel or checked implication refutation",
                verification_artifact="frontier_boundary:full_theory_program_replay",
            )
        )
        target_by_query[query_id] = target
        holding_by_target[target] = holding

    ranked = rank_boundary_queries(
        program_ids,
        queries,
        description_lengths={
            row.program_id: len(row.presentation_formula_ids)
            + len(row.prediction_formula_ids)
            for row in committee
        },
    ) if queries else ()
    selected = ranked[:max_queries]
    by_id = {row.program_id: row for row in committee}
    lifts = []
    for rank, priced in enumerate(selected, start=1):
        target = target_by_query[priced.query.query_id]
        for program_id in holding_by_target[target]:
            program = by_id[program_id]
            lifts.append(
                {
                    "schema": "leanmill.theory_program_boundary_lift_request.v1",
                    "query_id": priced.query.query_id,
                    "query_rank": rank,
                    "priority_target_formula_id": target,
                    "program_id": program_id,
                    "lineage_id": program.lineage_id,
                    "theory_program": program.to_json(),
                    "required_boundary_target_ids": list(
                        program.prediction_formula_ids
                    ),
                    "seed_profile_receipt_sha256": profile_refs[
                        (program_id, target)
                    ],
                    "status": "proposal_only_requires_full_program_boundary_replay",
                }
            )

    core = {
        "schema": "leanmill.theory_program_disagreement_policy.v1",
        "status": (
            "boundary_lifts_proposed"
            if lifts
            else "no_actionable_prediction_disagreement"
        ),
        "campaign_id": committee[0].campaign_id,
        "context_hash": context.context_hash,
        "context_epoch": committee[0].context_epoch,
        "isolation_receipt_sha256": isolation_receipt["receipt_sha256"],
        "program_comparison": comparison,
        "target_evaluations": evaluations,
        "ranked_queries": [
            {
                **row.to_json(),
                "target_formula_id": target_by_query[row.query.query_id],
            }
            for row in ranked
        ],
        "selected_query_ids": [row.query.query_id for row in selected],
        "boundary_lift_requests": lifts,
        "claim_boundary": (
            "proposal-only chart policy; no theory selection or boundary verdict"
        ),
        "authority": "deterministic_proposal_only_policy",
    }
    return {**core, "receipt_sha256": content_hash(core)}


__all__ = ["plan_theory_program_disagreement_lifts"]
