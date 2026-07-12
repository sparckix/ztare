"""No-provider compact-pack control for an exact finite theory context."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any

from ztare.common.leaf_workbench_environment import resolve_leaf_workbench_environment
from ztare.leanmill.finite_theory_context import SemanticTheoryNode
from ztare.leanmill.theory_context import TheoryLandscapeContext
from ztare.leanmill.theory_campaign_journal import TheoryCampaignEvent, TheoryCampaignJournal
from ztare.leanmill.theory_interest import (
    TheoryResidualYield,
    theory_residual_information_yield,
)
from ztare.leanmill.theory_query_policy import BoundaryQuery, rank_boundary_queries
from ztare.leanmill.theory_navigator import _receipted_reject_all


@dataclass(frozen=True)
class DeterministicCampaignResult:
    context_hash: str
    finalist_node_ids: tuple[str, ...]
    finalists: tuple[dict[str, Any], ...]
    ranked_queries: tuple[dict[str, Any], ...]
    workbench_receipts: tuple[dict[str, Any], ...]
    reject_all_receipt: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "leanmill.deterministic_frontier_campaign.v1",
            "context_hash": self.context_hash,
            "finalist_node_ids": list(self.finalist_node_ids),
            "finalists": list(self.finalists),
            "ranked_queries": list(self.ranked_queries),
            "workbench_receipts": list(self.workbench_receipts),
            "reject_all_receipt": self.reject_all_receipt,
            "provider_calls": 0,
        }


def _jaccard_distance(left: int, right: int) -> float:
    union = (left | right).bit_count()
    return 0.0 if union == 0 else 1.0 - (left & right).bit_count() / union


def _eligible_presentations(
    context: TheoryLandscapeContext,
    node: SemanticTheoryNode,
    *,
    minimum_presentation_size: int,
    maximum_presentation_size: int,
) -> tuple[tuple[tuple[str, ...], TheoryResidualYield], ...]:
    if node.extent_bits.bit_count() < 2:
        return ()
    eligible: list[tuple[tuple[str, ...], TheoryResidualYield]] = []
    for presentation in node.minimal_generators:
        if not minimum_presentation_size <= len(presentation) <= maximum_presentation_size:
            continue
        signal = theory_residual_information_yield(context, presentation)
        if (
            signal.residual_consequence_ids
            and signal.coordinates.identification_bits > 0
            and all(
                context.independence_witness(presentation, formula) is not None
                for formula in presentation
            )
        ):
            eligible.append((presentation, signal))
    return tuple(eligible)


def select_diverse_theory_nodes(
    context: TheoryLandscapeContext,
    *,
    max_finalists: int,
    minimum_presentation_size: int = 2,
    maximum_presentation_size: int = 2,
) -> tuple[SemanticTheoryNode, ...]:
    if max_finalists < 1:
        raise ValueError("max_finalists must be positive")
    candidate_presentations: dict[
        str, tuple[tuple[tuple[str, ...], TheoryResidualYield], ...]
    ] = {}
    candidates: list[SemanticTheoryNode] = []
    if not 1 <= minimum_presentation_size <= maximum_presentation_size:
        raise ValueError("invalid deterministic presentation-size bounds")
    for node in context.generated_theory_nodes(
        max_presentation_size=maximum_presentation_size
    ):
        eligible = _eligible_presentations(
            context,
            node,
            minimum_presentation_size=minimum_presentation_size,
            maximum_presentation_size=maximum_presentation_size,
        )
        if eligible:
            candidates.append(node)
            candidate_presentations[node.node_id] = eligible
    candidates.sort(
        key=lambda row: (
            -max(
                len(signal.residual_consequence_ids)
                * min(row.extent_bits.bit_count(), 32)
                for _presentation, signal in candidate_presentations[row.node_id]
            ),
            -row.extent_bits.bit_count(),
            row.node_id,
        )
    )
    selected: list[SemanticTheoryNode] = []
    while candidates and len(selected) < max_finalists:
        if not selected:
            chosen = candidates.pop(0)
        else:
            chosen = max(
                candidates,
                key=lambda row: (
                    min(_jaccard_distance(row.extent_bits, old.extent_bits) for old in selected),
                    row.closure_bits.bit_count(),
                    row.node_id,
                ),
            )
            candidates.remove(chosen)
        selected.append(chosen)
    return tuple(selected)


def run_deterministic_frontier_campaign(
    context: TheoryLandscapeContext,
    *,
    campaign_id: str,
    attempt_id: str,
    journal: TheoryCampaignJournal,
    max_finalists: int = 8,
    max_ranked_queries: int = 32,
    boundary_query_type: str = "conditional_lean_consequence",
    minimum_presentation_size: int = 2,
    maximum_presentation_size: int = 2,
    selection_mode: str = "compact_axiom_pack",
    epoch: int = 0,
) -> DeterministicCampaignResult:
    if selection_mode != "compact_axiom_pack":
        raise ValueError(
            "the deterministic control implements only compact_axiom_pack; "
            "theory_program requires an agent navigator"
        )
    environment = resolve_leaf_workbench_environment(
        "axiompack",
        context=context,
        selection_mode=selection_mode,
        max_presentation_size=maximum_presentation_size,
    )
    finalists = select_diverse_theory_nodes(
        context,
        max_finalists=max_finalists,
        minimum_presentation_size=minimum_presentation_size,
        maximum_presentation_size=maximum_presentation_size,
    )
    if not finalists:
        select = environment["action_handlers"]["select_theory_presentation"]
        rejected: list[dict[str, Any]] = []
        receipts: list[dict[str, Any]] = []
        for size in range(minimum_presentation_size, maximum_presentation_size + 1):
            for presentation in combinations(context.formula_ids, size):
                receipt = select(
                    ".",
                    {"input_refs": {"formula_ids": list(presentation)}},
                    None,
                    environment["contract"],
                )
                summary = dict(receipt["output_summary"])
                residual = dict(summary.get("residual_yield") or {})
                if (
                    float(residual.get("identification_bits", -1.0)) != 0.0
                    or residual.get("residual_ids")
                    or summary.get("residual_synergy_formula_ids")
                ):
                    continue
                receipts.append(receipt)
                rejected.append(
                    {
                        "formula_ids": list(presentation),
                        "node_id": summary["node_id"],
                        "reason": "zero_residual_information",
                        "selection_receipt_id": receipt["receipt_id"],
                        "residual_yield": residual,
                        "cheap_baseline_formula_ids": list(
                            summary.get("cheap_baseline_formula_ids") or ()
                        ),
                        "structural_baseline": summary.get("structural_baseline"),
                        "residual_synergy_formula_ids": [],
                    }
                )
                if len(rejected) >= 3:
                    break
            if len(rejected) >= 3:
                break
        reject_all = _receipted_reject_all(
            context,
            rejected,
            reason="exact_context_has_no_eligible_residual_pair",
        )
        journal.append(
            TheoryCampaignEvent(
                attempt_id=attempt_id,
                campaign_id=campaign_id,
                epoch=epoch,
                context_hash=context.context_hash,
                event_type="navigator_reject_all",
                subject_ids=(str(reject_all["receipt_id"]),),
                input_refs=tuple(
                    str(row["selection_receipt_id"]) for row in rejected
                ),
                output_refs=(str(reject_all["receipt_id"]),),
                evidence_status="witnessed",
                authority="deterministic_information_control",
            )
        )
        return DeterministicCampaignResult(
            context_hash=context.context_hash,
            finalist_node_ids=(),
            finalists=(),
            ranked_queries=(),
            workbench_receipts=tuple(receipts),
            reject_all_receipt=reject_all,
        )
    receipts: list[dict[str, Any]] = []
    finalist_rows: list[dict[str, Any]] = []
    target_formula_ids: set[str] = set()
    for node in finalists:
        presentation, residual = min(
            _eligible_presentations(
                context,
                node,
                minimum_presentation_size=minimum_presentation_size,
                maximum_presentation_size=maximum_presentation_size,
            ),
            key=lambda row: (
                -row[1].coordinates.identification_bits,
                -len(row[1].residual_consequence_ids),
                row[0],
            ),
        )
        synergy_ids = residual.joint_only_consequence_ids
        target_formula_ids.update(residual.residual_consequence_ids)
        finalist_rows.append(
            {
                "node_id": node.node_id,
                "formula_ids": list(presentation),
                "joint_only_consequence_ids": list(synergy_ids),
                "cheap_baseline_consequence_ids": list(
                    residual.cheap_baseline_consequence_ids
                ),
                "residual_joint_only_consequence_ids": list(
                    residual.residual_consequence_ids
                ),
                "residual_information_yield": residual.coordinates.to_json(),
                "structural_baseline": residual.structural_baseline,
                "extent_size": node.extent_bits.bit_count(),
                "closure_size": node.closure_bits.bit_count(),
            }
        )
        receipt = environment["action_handlers"]["inspect_theory_node"](
            ".", {"input_refs": {"node_id": node.node_id}}, None, environment["contract"]
        )
        receipts.append(receipt)
        journal.append(
            TheoryCampaignEvent(
                attempt_id=attempt_id,
                campaign_id=campaign_id,
                epoch=epoch,
                context_hash=context.context_hash,
                event_type="finalist_frozen",
                subject_ids=(node.node_id,),
                input_refs=tuple(presentation),
                output_refs=(receipt["receipt_id"],),
                evidence_status="frozen",
                authority="deterministic_information_control",
            )
        )

    formula_ids = context.formula_ids
    queries: list[BoundaryQuery] = []
    for formula_index, formula_id in enumerate(formula_ids):
        if formula_id not in target_formula_ids:
            continue
        predictions = {
            node.node_id: bool(node.closure_bits & (1 << formula_index)) for node in finalists
        }
        if len(set(predictions.values())) < 2:
            continue
        true_nodes = sorted(node_id for node_id, prediction in predictions.items() if prediction)
        false_nodes = sorted(node_id for node_id, prediction in predictions.items() if not prediction)
        queries.append(
            BoundaryQuery(
                query_id=("lean-boundary:" if boundary_query_type == "conditional_lean_consequence" else "raw-boundary:") + formula_id,
                query_type=boundary_query_type,
                predictions=predictions,
                cost_units=1.0,
                target_mapping=f"test conditional consequence {formula_id} for the frozen presentations",
                nearest_confuser=f"{true_nodes[0]} versus {false_nodes[0]}",
                falsifier="a replayed finite countermodel or kernel-checked refutation",
                verification_artifact=(
                    "conditional-lean-task:" if boundary_query_type == "conditional_lean_consequence"
                    else "raw-boundary-task:"
                ) + formula_id,
            )
        )
    ranked = rank_boundary_queries(
        [row.node_id for row in finalists],
        queries,
        description_lengths={
            row.node_id: min(map(len, row.minimal_generators)) for row in finalists
        },
    ) if queries else ()
    return DeterministicCampaignResult(
        context_hash=context.context_hash,
        finalist_node_ids=tuple(row.node_id for row in finalists),
        finalists=tuple(finalist_rows),
        ranked_queries=tuple(row.to_json() for row in ranked[:max_ranked_queries]),
        workbench_receipts=tuple(receipts),
    )


__all__ = [
    "DeterministicCampaignResult", "run_deterministic_frontier_campaign",
    "select_diverse_theory_nodes",
]
