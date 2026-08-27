#!/usr/bin/env python3
"""Audit H99 persistent temporal judgment against its frozen criteria."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory


FIXTURES = Path(__file__).resolve().parent
ROOT = FIXTURES.parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ztare.common.continual_skill_memory import (  # noqa: E402
    decision_option_family_sha256,
    empty_continual_skill_memory,
    judge_combined_decision_option_task_credit,
    judge_decision_option_task_credit,
    load_continual_skill_memory,
    record_task_decision_experience,
    record_temporal_decision_chain,
    save_continual_skill_memory,
)
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
)


NAMESPACE = "persistent-protocol-choice"
TASK = "persistent-external-task"
SOURCE = "persistent-shared-source"
CONTROLLER = "persistent-controller-v1"
MEASURE = "heldout-version-space-reduction-v1"
FAMILIES = {
    protocol_id: decision_option_family_sha256(NAMESPACE, protocol_id)
    for protocol_id in ("advance", "detour")
}
AVAILABLE = tuple(sorted(FAMILIES.values()))


def chain(
    pair: int,
    *,
    first_protocol: str,
    terminal: str,
    predicted: float,
    observed: float,
) -> DecisionEligibilityChain:
    chain_ref = f"persistent-pair-{pair}:{first_protocol}"
    successor = f"{chain_ref}:successor"
    authority = DecisionChoiceAuthority(
        task_contract_sha256=TASK,
        decision_namespace=NAMESPACE,
        choice_context_sha256=SOURCE,
        continuation_context_sha256=CONTROLLER,
        available_option_family_sha256s=AVAILABLE,
    )
    later = DecisionChoiceAuthority(
        task_contract_sha256=TASK,
        decision_namespace=NAMESPACE,
        choice_context_sha256=successor,
        continuation_context_sha256=CONTROLLER,
        available_option_family_sha256s=("finish", "wait"),
    )
    return DecisionEligibilityChain(
        chain_ref=chain_ref,
        matched_pair_ref=f"persistent-pair-{pair}",
        arm_id=first_protocol,
        continuation_policy_sha256="persistent-policy",
        edges=(
            DecisionEligibilityEdge(
                chain_ref=chain_ref,
                edge_index=0,
                authority=authority,
                chosen_option_family_sha256=FAMILIES[first_protocol],
                chosen_option_variant_sha256=first_protocol + "-variant",
                successor_decision_state_sha256=successor,
                predicted_information_yield=predicted,
                observed_information_yield=observed,
                information_yield_measure_sha256=MEASURE,
                primitive_action_cost=1.0,
                immediate_task_status="open",
                evidence_ref=f"edge:{chain_ref}:0",
            ),
            DecisionEligibilityEdge(
                chain_ref=chain_ref,
                edge_index=1,
                authority=later,
                chosen_option_family_sha256=(
                    "finish" if terminal == "attained" else "wait"
                ),
                chosen_option_variant_sha256=terminal + "-variant",
                successor_decision_state_sha256=f"{chain_ref}:terminal",
                predicted_information_yield=0.2,
                observed_information_yield=0.2,
                information_yield_measure_sha256=MEASURE,
                primitive_action_cost=1.0,
                immediate_task_status=terminal,
                evidence_ref=f"edge:{chain_ref}:1",
            ),
        ),
        terminal_task_status=terminal,
        terminal_adjudication_ref=f"adjudication:{chain_ref}:{terminal}",
    )


def candidate(
    protocol_id: str,
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


def immediate_scope() -> dict:
    return {
        "task_contract_sha256": TASK,
        "decision_namespace": NAMESPACE,
        "choice_context_sha256": SOURCE,
        "continuation_context_sha256": CONTROLLER,
        "available_option_family_sha256s": AVAILABLE,
    }


def run_audit() -> dict:
    legacy = empty_continual_skill_memory()
    for trace_ref, protocol_id in (
        ("legacy-open-advance", "advance"),
        ("legacy-open-detour", "detour"),
    ):
        legacy = record_task_decision_experience(
            legacy,
            **immediate_scope(),
            trace_ref=trace_ref,
            choice_index=0,
            outcome="open",
            chosen_option_family_sha256=FAMILIES[protocol_id],
            chosen_option_variant_sha256=protocol_id + "-legacy",
            evidence_ref="legacy:" + trace_ref,
        )
    legacy_payload = legacy.to_dict()
    legacy_payload["schema"] = "ztare-continual-skill-memory-v1"
    legacy_payload.pop("temporal_decision_chains")
    legacy_payload.pop("decision_yield_calibrations")

    with TemporaryDirectory(prefix="ztare-h99-") as directory:
        path = Path(directory) / "memory.json"
        path.write_text(json.dumps(legacy_payload), encoding="utf-8")
        migrated = load_continual_skill_memory(path)
        legacy_preferences = {
            protocol_id: judge_decision_option_task_credit(
                migrated,
                **immediate_scope(),
                option_family_sha256=family,
            ).preference
            for protocol_id, family in FAMILIES.items()
        }
        memory = migrated
        chains = tuple(
            row
            for pair, advance_observed, detour_observed in (
                (1, 0.4, 0.15),
                (2, 0.6, 0.10),
            )
            for row in (
                chain(
                    pair,
                    first_protocol="advance",
                    terminal="attained",
                    predicted=0.8,
                    observed=advance_observed,
                ),
                chain(
                    pair,
                    first_protocol="detour",
                    terminal="open",
                    predicted=1.2,
                    observed=detour_observed,
                ),
            )
        )
        for row in chains:
            memory = record_temporal_decision_chain(memory, row)
        chain_hashes_before = tuple(
            row.sha256 for row in memory.temporal_decision_chains
        )
        calibrations_before = tuple(
            row.to_receipt()
            for row in memory.decision_yield_calibrations
        )
        save_continual_skill_memory(path, memory)
        restored = load_continual_skill_memory(path)
        chain_hashes_after = tuple(
            row.sha256 for row in restored.temporal_decision_chains
        )
        calibrations_after = tuple(
            row.to_receipt()
            for row in restored.decision_yield_calibrations
        )

        judgments = {
            protocol_id: judge_combined_decision_option_task_credit(
                restored,
                **immediate_scope(),
                option_family_sha256=family,
                max_eligibility_delay_steps=1,
            )
            for protocol_id, family in FAMILIES.items()
        }
        mismatched_controller = {
            protocol_id: judge_combined_decision_option_task_credit(
                restored,
                **{
                    **immediate_scope(),
                    "continuation_context_sha256": "different-controller",
                },
                option_family_sha256=family,
            ).preference
            for protocol_id, family in FAMILIES.items()
        }
        mismatched_choice_set = {
            protocol_id: judge_combined_decision_option_task_credit(
                restored,
                **{
                    **immediate_scope(),
                    "available_option_family_sha256s": tuple(sorted((
                        *AVAILABLE,
                        "third-family",
                    ))),
                },
                option_family_sha256=family,
            ).preference
            for protocol_id, family in FAMILIES.items()
        }

        candidates = (
            candidate("advance", ("a", "b"), ("x", "x", "y")),
            candidate("detour", ("d",), ("x", "y", "z")),
        )
        weights = ProtocolYieldWeights(1.0, 1.0, 1.0)
        baseline = select_guarded_protocol(candidates, weights=weights)
        reranked = select_guarded_protocol(
            candidates,
            weights=weights,
            task_value_by_protocol_id={
                protocol_id: judgment.preference
                for protocol_id, judgment in judgments.items()
            },
        )
        baseline_costs = {
            row.protocol_id: row.cost.to_receipt()
            for row in baseline.prices
        }
        reranked_costs = {
            row.protocol_id: row.cost.to_receipt()
            for row in reranked.prices
        }

        conflicting = restored
        for trace_ref, protocol_id, outcome in (
            ("immediate-positive-detour", "detour", "attained"),
            ("immediate-contrast-advance", "advance", "open"),
        ):
            conflicting = record_task_decision_experience(
                conflicting,
                **immediate_scope(),
                trace_ref=trace_ref,
                choice_index=0,
                outcome=outcome,
                chosen_option_family_sha256=FAMILIES[protocol_id],
                chosen_option_variant_sha256=protocol_id + "-conflict",
                evidence_ref="conflict:" + trace_ref,
            )
        conflicts = {
            protocol_id: judge_combined_decision_option_task_credit(
                conflicting,
                **immediate_scope(),
                option_family_sha256=family,
                max_eligibility_delay_steps=1,
            ).to_receipt()
            for protocol_id, family in FAMILIES.items()
        }

        tampered = json.loads(path.read_text(encoding="utf-8"))
        tampered["decision_yield_calibrations"][0]["mean_error"] = 9.0
        path.write_text(json.dumps(tampered), encoding="utf-8")
        drift_rejected = False
        drift_error = ""
        try:
            load_continual_skill_memory(path)
        except ValueError as error:
            drift_rejected = True
            drift_error = str(error)

    checks = {
        "legacy_open_open_remained_uncredited": (
            legacy_preferences == {"advance": 0, "detour": 0}
        ),
        "memory_migrated_to_v2": (
            migrated.schema == "ztare-continual-skill-memory-v2"
        ),
        "chain_hashes_round_tripped": (
            chain_hashes_before == chain_hashes_after
        ),
        "yield_calibrations_round_tripped": (
            calibrations_before == calibrations_after
        ),
        "yield_calibration_has_no_task_authority": all(
            not row["task_credit_authorized"]
            for row in calibrations_after
        ),
        "distal_preferences_reconstructed": (
            judgments["advance"].preference == 1
            and judgments["detour"].preference == -1
        ),
        "exact_scope_selection_flipped": (
            baseline.selected_protocol_id == "detour"
            and reranked.selected_protocol_id == "advance"
        ),
        "protocol_costs_unchanged": baseline_costs == reranked_costs,
        "controller_mismatch_uncredited": (
            mismatched_controller == {"advance": 0, "detour": 0}
        ),
        "choice_set_mismatch_uncredited": (
            mismatched_choice_set == {"advance": 0, "detour": 0}
        ),
        "immediate_distal_conflict_neutral": all(
            row["status"] == "credit_conflict"
            and row["preference"] == 0
            for row in conflicts.values()
        ),
        "calibration_drift_rejected": drift_rejected,
    }
    return {
        "schema": "ztare-h99-persistent-temporal-judgment-audit-v1",
        "hypothesis_id": (
            "H-GPSA-PERSISTENT-TEMPORAL-JUDGMENT-20260805-99"
        ),
        "status": (
            "supported" if all(checks.values()) else "refuted"
        ),
        "environment_contact": False,
        "checks": checks,
        "legacy": {
            "source_schema": "ztare-continual-skill-memory-v1",
            "restored_schema": migrated.schema,
            "immediate_preferences": legacy_preferences,
        },
        "persistence": {
            "chain_count": len(chain_hashes_after),
            "chain_sha256s": list(chain_hashes_after),
            "calibration_count": len(calibrations_after),
            "calibrations": list(calibrations_after),
            "drift_error": drift_error,
        },
        "judgments": {
            key: value.to_receipt()
            for key, value in judgments.items()
        },
        "selection": {
            "baseline": baseline.to_receipt(),
            "reranked": reranked.to_receipt(),
            "costs_unchanged": baseline_costs == reranked_costs,
        },
        "mismatch_preferences": {
            "controller": mismatched_controller,
            "choice_set": mismatched_choice_set,
        },
        "conflicts": conflicts,
        "claim_boundary": (
            "controller-neutral offline persistence and selector integration; "
            "no ARC score or automatic play-loop chain collection claim"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=FIXTURES / (
            "h99_persistent_temporal_judgment_result.json"
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
        "status": result["status"],
        "checks": result["checks"],
    }, indent=2, sort_keys=True))
    if result["status"] != "supported":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
