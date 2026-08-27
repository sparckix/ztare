#!/usr/bin/env python3
"""Close the anonymous H98 matched temporal-credit experiment."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


FIXTURES = Path(__file__).resolve().parent
ROOT = FIXTURES.parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ztare.common.guarded_experiment_protocol import (  # noqa: E402
    GuardedExperimentProtocol,
    GuardedProtocolCandidate,
    ProtocolCost,
    ProtocolResponseHypothesis,
    ProtocolYieldWeights,
    select_guarded_protocol,
)
from ztare.common.temporal_decision_credit import (  # noqa: E402
    DecisionChoiceAuthority,
    DecisionEligibilityChain,
    DecisionEligibilityEdge,
    compile_decision_yield_calibration,
    compile_temporal_decision_credit,
    settle_matched_temporal_pair,
    task_values_for_authority,
)


ADVANCE = "advance-family"
DETOUR = "detour-family"
FINISH = "finish-family"
WAIT = "wait-family"
MEASURE = "heldout-version-space-reduction-v1"


def source_authority(
    *,
    continuation: str = "controller-v1",
    available: tuple[str, ...] = (ADVANCE, DETOUR),
) -> DecisionChoiceAuthority:
    return DecisionChoiceAuthority(
        task_contract_sha256="external-task",
        decision_namespace="anonymous-protocol-choice",
        choice_context_sha256="shared-source-state",
        continuation_context_sha256=continuation,
        available_option_family_sha256s=available,
    )


def later_authority(
    context: str,
    *,
    continuation: str = "controller-v1",
) -> DecisionChoiceAuthority:
    return DecisionChoiceAuthority(
        task_contract_sha256="external-task",
        decision_namespace="anonymous-protocol-choice",
        choice_context_sha256=context,
        continuation_context_sha256=continuation,
        available_option_family_sha256s=(FINISH, WAIT),
    )


def chain(
    pair: int,
    *,
    first_option: str,
    terminal: str,
    observed_yield: float,
    predicted_yield: float,
    continuation: str = "controller-v1",
    available: tuple[str, ...] = (ADVANCE, DETOUR),
    extra_edges: int = 0,
) -> DecisionEligibilityChain:
    arm = first_option.split("-", 1)[0]
    chain_ref = f"pair-{pair}:{arm}"
    successor = f"pair-{pair}:{arm}:state-1"
    edges = [DecisionEligibilityEdge(
        chain_ref=chain_ref,
        edge_index=0,
        authority=source_authority(
            continuation=continuation,
            available=available,
        ),
        chosen_option_family_sha256=first_option,
        chosen_option_variant_sha256=first_option + "-variant",
        successor_decision_state_sha256=successor,
        predicted_information_yield=predicted_yield,
        observed_information_yield=observed_yield,
        information_yield_measure_sha256=MEASURE,
        primitive_action_cost=1.0,
        immediate_task_status="open",
        evidence_ref=f"edge:{chain_ref}:0",
    )]
    current = successor
    for index in range(1, 2 + extra_edges):
        next_state = f"pair-{pair}:{arm}:state-{index + 1}"
        edges.append(DecisionEligibilityEdge(
            chain_ref=chain_ref,
            edge_index=index,
            authority=later_authority(
                current,
                continuation=continuation,
            ),
            chosen_option_family_sha256=(
                FINISH if terminal == "attained" else WAIT
            ),
            chosen_option_variant_sha256=f"terminal-{terminal}",
            successor_decision_state_sha256=next_state,
            predicted_information_yield=0.2,
            observed_information_yield=0.2,
            information_yield_measure_sha256=MEASURE,
            primitive_action_cost=1.0,
            immediate_task_status=(
                terminal if index == 1 + extra_edges else "open"
            ),
            evidence_ref=f"edge:{chain_ref}:{index}",
        ))
        current = next_state
    return DecisionEligibilityChain(
        chain_ref=chain_ref,
        matched_pair_ref=f"pair-{pair}",
        arm_id=f"arm-{arm}",
        continuation_policy_sha256="shared-downstream-policy",
        edges=tuple(edges),
        terminal_task_status=terminal,
        terminal_adjudication_ref=f"adjudication:{chain_ref}:{terminal}",
    )


def candidate(
    protocol_id: str,
    *,
    preparation: tuple[str, ...],
    responses: tuple[str, ...],
) -> GuardedProtocolCandidate:
    return GuardedProtocolCandidate(
        protocol=GuardedExperimentProtocol(
            protocol_id=protocol_id,
            preparation=preparation,
            probe="probe",
            target_key=protocol_id + "-target",
            cost=ProtocolCost(
                preparation_execution_units=len(preparation),
                probe_execution_units=1,
                control_units=1,
            ),
            novel_context=True,
        ),
        committee=tuple(
            ProtocolResponseHypothesis(
                hypothesis_id=f"h{index}",
                response=response,
            )
            for index, response in enumerate(responses)
        ),
    )


def run_audit() -> dict:
    pairs = tuple(
        (
            chain(
                pair,
                first_option=ADVANCE,
                terminal="attained",
                predicted_yield=0.8,
                observed_yield=observed,
            ),
            chain(
                pair,
                first_option=DETOUR,
                terminal="open",
                predicted_yield=1.2,
                observed_yield=0.15 - 0.05 * (pair - 1),
            ),
        )
        for pair, observed in ((1, 0.4), (2, 0.6))
    )
    compilation = compile_temporal_decision_credit(
        pairs,
        minimum_support=2,
        max_eligibility_delay_steps=1,
    )
    judgments = {
        row.option_family_sha256: row
        for row in compilation.judgments
    }
    calibration = compile_decision_yield_calibration(
        tuple(chain_row for pair in pairs for chain_row in pair)
    )
    calibration_by_option = {
        row.option_family_sha256: row
        for row in calibration
        if row.authority == source_authority()
    }

    advance = candidate(
        ADVANCE,
        preparation=("a", "b"),
        responses=("x", "x", "y"),
    )
    detour = candidate(
        DETOUR,
        preparation=("d",),
        responses=("x", "y", "z"),
    )
    weights = ProtocolYieldWeights(1.0, 1.0, 1.0)
    baseline = select_guarded_protocol(
        (advance, detour),
        weights=weights,
    )
    reranked = select_guarded_protocol(
        (advance, detour),
        weights=weights,
        task_value_by_protocol_id=task_values_for_authority(
            compilation,
            source_authority(),
        ),
    )
    baseline_costs = {
        row.protocol_id: row.cost.to_receipt()
        for row in baseline.prices
    }
    reranked_costs = {
        row.protocol_id: row.cost.to_receipt()
        for row in reranked.prices
    }

    open_pairs = tuple(
        (
            chain(
                pair,
                first_option=ADVANCE,
                terminal="open",
                predicted_yield=0.8,
                observed_yield=observed,
            ),
            chain(
                pair,
                first_option=DETOUR,
                terminal="open",
                predicted_yield=1.2,
                observed_yield=detour_observed,
            ),
        )
        for pair, observed, detour_observed in (
            (11, 0.9, 0.15),
            (12, 1.0, 0.1),
        )
    )
    open_only = compile_temporal_decision_credit(
        open_pairs,
        minimum_support=2,
        max_eligibility_delay_steps=1,
    )
    wrong_controller = settle_matched_temporal_pair(
        chain(
            21,
            first_option=ADVANCE,
            terminal="attained",
            predicted_yield=0.8,
            observed_yield=0.4,
        ),
        chain(
            21,
            first_option=DETOUR,
            terminal="open",
            predicted_yield=1.2,
            observed_yield=0.1,
            continuation="controller-v2",
        ),
        max_eligibility_delay_steps=1,
    )
    wrong_choice_set = settle_matched_temporal_pair(
        chain(
            22,
            first_option=ADVANCE,
            terminal="attained",
            predicted_yield=0.8,
            observed_yield=0.4,
        ),
        chain(
            22,
            first_option=DETOUR,
            terminal="open",
            predicted_yield=1.2,
            observed_yield=0.1,
            available=(ADVANCE, DETOUR, "third-family"),
        ),
        max_eligibility_delay_steps=1,
    )
    expired = settle_matched_temporal_pair(
        chain(
            23,
            first_option=ADVANCE,
            terminal="attained",
            predicted_yield=0.8,
            observed_yield=0.4,
            extra_edges=2,
        ),
        chain(
            23,
            first_option=DETOUR,
            terminal="open",
            predicted_yield=1.2,
            observed_yield=0.1,
            extra_edges=2,
        ),
        max_eligibility_delay_steps=1,
    )
    checks = {
        "advance_distal_credit_support_two": (
            judgments[ADVANCE].status == "task_credited"
            and judgments[ADVANCE].enable_support == 2
        ),
        "detour_distal_hazard_support_two": (
            judgments[DETOUR].status == "task_hazard"
            and judgments[DETOUR].hazard_support == 2
        ),
        "credited_first_decisions_nonterminal": all(
            row.edges[0].immediate_task_status == "open"
            for pair in pairs
            for row in pair
        ),
        "open_open_information_does_not_credit": (
            not open_only.judgments
            and all(
                row.status == "uninformative"
                for row in open_only.pair_receipts
            )
        ),
        "controller_mismatch_refused": (
            wrong_controller.reason == "first_choice_authority_mismatch"
        ),
        "choice_set_mismatch_refused": (
            wrong_choice_set.reason == "first_choice_authority_mismatch"
        ),
        "expired_trace_refused": (
            expired.reason == "eligibility_trace_expired"
        ),
        "yield_calibration_separate": (
            calibration_by_option[ADVANCE].status == "calibrated"
            and calibration_by_option[ADVANCE].mean_error
            == -0.30000000000000004
            and calibration_by_option[DETOUR].mean_observed_yield
            == 0.125
        ),
        "selection_flipped": (
            baseline.selected_protocol_id == DETOUR
            and reranked.selected_protocol_id == ADVANCE
        ),
        "protocol_costs_unchanged": baseline_costs == reranked_costs,
    }
    return {
        "schema": "ztare-h98-matched-temporal-decision-credit-audit-v1",
        "status": "offline_complete",
        "environment_contact": False,
        "hypothesis_ref": (
            "research_areas/pre_registrations/"
            "arc3_consumer_indexed_exception_frontier_20260723/"
            "h98_matched_temporal_decision_credit_hypothesis.md"
        ),
        "temporal_credit": compilation.to_receipt(),
        "yield_calibration": [
            row.to_receipt() for row in calibration
        ],
        "negative_controls": {
            "open_open": open_only.to_receipt(),
            "controller_mismatch": wrong_controller.to_receipt(),
            "choice_set_mismatch": wrong_choice_set.to_receipt(),
            "expired_trace": expired.to_receipt(),
        },
        "selection": {
            "baseline": baseline.to_receipt(),
            "distal_credit_reranked": reranked.to_receipt(),
            "baseline_costs": baseline_costs,
            "reranked_costs": reranked_costs,
        },
        "checks": checks,
        "verdict": "supported" if all(checks.values()) else "rejected",
        "claim_boundary": (
            "Anonymous synthetic one-step delayed credit and yield-error "
            "receipts only; no ARC or H97 outcome."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            FIXTURES
            / "h98_matched_temporal_decision_credit_result.json"
        ),
    )
    args = parser.parse_args()
    result = run_audit()
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(args.output),
        "verdict": result["verdict"],
        "checks": result["checks"],
    }, indent=2, sort_keys=True))
    return 0 if result["verdict"] == "supported" else 1


if __name__ == "__main__":
    raise SystemExit(main())
