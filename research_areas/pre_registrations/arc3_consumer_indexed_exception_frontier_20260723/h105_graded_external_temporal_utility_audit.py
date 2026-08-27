#!/usr/bin/env python3
"""Audit H105 against the frozen, prospectively collected H95 pairs."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from ztare.common.equivariance import stable_sha256  # noqa: E402
from ztare.common.temporal_decision_credit import (  # noqa: E402
    DecisionChoiceAuthority,
    DecisionEligibilityChain,
    DecisionEligibilityEdge,
    compile_temporal_decision_credit,
)
from ztare.common.temporal_decision_utility import (  # noqa: E402
    ExternalUtilityMeasure,
    TemporalDecisionUtilityArm,
    compile_temporal_decision_utility,
    settle_matched_temporal_utility_pair,
)


BASE = Path(__file__).resolve().parent
H95_PATH = BASE / "h95_response_transport_square/result.json"
RESULT_PATH = BASE / "h105_graded_external_temporal_utility_result.json"
SUMMARY_PATH = BASE / "h105_graded_external_temporal_utility_result.md"


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _lower_h95(result: dict):
    causal = result["intervention_revision_transport"]
    placebo = result["placebo_intervention_revision_transport"]
    causal_family = str(causal["payload_invariant_sha256"])
    placebo_family = str(placebo["payload_invariant_sha256"])
    first_scope = result["pairs"][0]["stratum"]["scope"]
    continuation = stable_sha256({
        "schema": "ztare-h95-continuation-policy-v1",
        "controller_sha256": first_scope["controller_sha256"],
        "model": "gpt-5.6-sol",
        "reasoning_effort": "xhigh",
        "post_prefix_action_budget": result["aggregate"][
            "post_prefix_primitive_action_cost_per_arm"
        ],
        "proposal_inferences_before_action": result["aggregate"][
            "proposal_inferences_before_post_prefix_action"
        ],
    })
    utility_pairs = []
    binary_pairs = []
    for row in result["pairs"]:
        scope = row["stratum"]["scope"]
        authority = DecisionChoiceAuthority(
            task_contract_sha256=str(scope["task_sha256"]),
            decision_namespace="arc3-response-transport-square",
            choice_context_sha256=str(scope["context_sha256"]),
            continuation_context_sha256=continuation,
            available_option_family_sha256s=(
                causal_family,
                placebo_family,
            ),
        )
        measure = ExternalUtilityMeasure(
            task_contract_sha256=authority.task_contract_sha256,
            measure_id="h95-weighted-task-efficiency-v1",
            component_weights=(
                (
                    "efficiency_score",
                    float(row["stratum"]["efficiency_score_weight"]),
                ),
                (
                    "task_score",
                    float(row["stratum"]["task_score_weight"]),
                ),
            ),
        )
        pair_ref = "h95-pair:" + stable_sha256({
            "experiment_sha256": result["experiment_sha256"],
            "pair_index": row["pair_index"],
        })
        utility_arms = []
        binary_arms = []
        for arm_id, option_family, variant in (
            (
                "offer",
                causal_family,
                causal["target_intervention_revision_sha256"],
            ),
            (
                "withhold",
                placebo_family,
                placebo["target_intervention_revision_sha256"],
            ),
        ):
            metrics = row[f"{arm_id}_metrics"]
            outcome = row[f"{arm_id}_outcome"]
            terminal = (
                "attained"
                if float(metrics["task_score"]) > 0.0
                else "open"
            )
            utility_arms.append(TemporalDecisionUtilityArm(
                matched_pair_ref=pair_ref,
                arm_id=arm_id,
                authority=authority,
                chosen_option_family_sha256=option_family,
                chosen_option_variant_sha256=str(variant),
                continuation_policy_sha256=continuation,
                utility_measure=measure,
                component_values=(
                    ("task_score", float(metrics["task_score"])),
                    (
                        "efficiency_score",
                        float(metrics["efficiency_score"]),
                    ),
                ),
                primitive_action_cost=float(
                    outcome["primitive_action_cost"]
                ),
                immediate_task_status="open",
                terminal_task_status=terminal,
                external_value=float(outcome["net_external_value"]),
                external_outcome_ref=str(outcome["external_outcome_ref"]),
            ))
            chain_ref = f"{pair_ref}:{arm_id}"
            binary_arms.append(DecisionEligibilityChain(
                chain_ref=chain_ref,
                matched_pair_ref=pair_ref,
                arm_id=arm_id,
                continuation_policy_sha256=continuation,
                edges=(DecisionEligibilityEdge(
                    chain_ref=chain_ref,
                    edge_index=0,
                    authority=authority,
                    chosen_option_family_sha256=option_family,
                    chosen_option_variant_sha256=str(variant),
                    successor_decision_state_sha256=(
                        "terminal:" + stable_sha256({
                            "pair_ref": pair_ref,
                            "arm_id": arm_id,
                            "terminal": terminal,
                        })
                    ),
                    predicted_information_yield=float(
                        metrics["information_yield"]
                    ),
                    observed_information_yield=float(
                        metrics["information_yield"]
                    ),
                    information_yield_measure_sha256=stable_sha256(
                        metrics["information_yield_measure"]
                    ),
                    primitive_action_cost=float(
                        outcome["primitive_action_cost"]
                    ),
                    immediate_task_status="open",
                    evidence_ref=str(outcome["external_outcome_ref"]),
                ),),
                terminal_task_status=terminal,
                terminal_adjudication_ref=str(
                    outcome["external_outcome_ref"]
                ),
            ))
        utility_pairs.append(tuple(utility_arms))
        binary_pairs.append(tuple(binary_arms))
    return tuple(utility_pairs), tuple(binary_pairs)


def main() -> int:
    h95 = json.loads(H95_PATH.read_text(encoding="utf-8"))
    h95_core = dict(h95)
    h95_embedded_sha = str(h95_core.pop("sha256"))
    if stable_sha256(h95_core) != h95_embedded_sha:
        raise SystemExit("H95 embedded result identity drifted")
    utility_pairs, binary_pairs = _lower_h95(h95)
    graded = compile_temporal_decision_utility(
        utility_pairs,
        minimum_support=2,
    )
    binary = compile_temporal_decision_credit(
        binary_pairs,
        minimum_support=2,
        max_eligibility_delay_steps=0,
    )
    graded_receipt = graded.to_receipt()
    binary_receipt = binary.to_receipt()
    judgments = {
        row.status: row.to_receipt() for row in graded.judgments
    }

    first_left, first_right = utility_pairs[0]
    mismatches = {}
    mismatch_rows = {
        "choice_context": replace(
            first_right,
            authority=replace(
                first_right.authority,
                choice_context_sha256="h96-different-context",
            ),
        ),
        "continuation_policy": replace(
            first_right,
            continuation_policy_sha256="different-policy",
        ),
        "utility_measure": replace(
            first_right,
            utility_measure=ExternalUtilityMeasure(
                task_contract_sha256=(
                    first_right.authority.task_contract_sha256
                ),
                measure_id="different-measure",
                component_weights=(
                    ("efficiency_score", 0.2),
                    ("task_score", 0.8),
                ),
            ),
        ),
        "primitive_cost": replace(
            first_right,
            primitive_action_cost=19.0,
        ),
        "external_evidence": replace(
            first_right,
            external_outcome_ref=first_left.external_outcome_ref,
        ),
    }
    for name, drifted in mismatch_rows.items():
        receipt = settle_matched_temporal_utility_pair(
            first_left,
            drifted,
        )
        mismatches[name] = {
            "status": receipt.status,
            "reason": receipt.reason,
        }
    tie = settle_matched_temporal_utility_pair(
        first_left,
        replace(
            first_right,
            component_values=first_left.component_values,
            terminal_task_status=first_left.terminal_task_status,
            external_value=first_left.external_value,
        ),
    )

    primitive_costs_before = [
        arm.primitive_action_cost
        for pair in utility_pairs
        for arm in pair
    ]
    primitive_costs_after = [
        row.primitive_action_cost_per_arm
        for row in graded.pair_receipts
    ]
    expected_costs_after = [
        pair[0].primitive_action_cost for pair in utility_pairs
    ]
    preferred = judgments.get("utility_preferred", {})
    hazard = judgments.get("utility_hazard", {})
    checks = {
        "h95_identity_verified": True,
        "pair_1_delta_0_89": abs(
            graded.pair_receipts[0].external_value_delta - 0.89
        ) < 1e-12,
        "pair_2_equal_terminal_delta_0_07": (
            utility_pairs[1][0].terminal_task_status
            == utility_pairs[1][1].terminal_task_status
            == "attained"
            and abs(
                graded.pair_receipts[1].external_value_delta - 0.07
            ) < 1e-12
        ),
        "graded_support_two": (
            preferred.get("preferred_support") == 2
            and hazard.get("hazard_support") == 2
        ),
        "mean_delta_matches_h95": abs(
            graded_receipt["mean_settled_external_delta"]
            - h95["aggregate"]["mean_offer_minus_withhold_composite"]
        ) < 1e-12,
        "binary_baseline_undersampled": (
            binary_receipt["settled_pair_count"] == 1
            and {row["status"] for row in binary_receipt["judgments"]}
            == {"undersampled"}
        ),
        "mismatches_refused": all(
            row["status"] == "refused"
            for row in mismatches.values()
        ),
        "tie_uninformative": tie.status == "uninformative",
        "primitive_costs_unchanged": (
            primitive_costs_before == [20.0, 20.0, 20.0, 20.0]
            and primitive_costs_after == expected_costs_after
        ),
        "h96_context_cannot_pool": (
            mismatches["choice_context"]["reason"]
            == "decision_choice_authority_mismatch"
        ),
        "separate_authority_channels": (
            graded_receipt["terminal_task_credit_authorized"] is False
            and graded_receipt["information_yield_authorized"] is False
        ),
    }

    verification_command = [
        str(ROOT / "venv/bin/python"),
        "-m",
        "pytest",
        "tests/common/test_temporal_decision_utility.py",
        "-q",
    ]
    completed = subprocess.run(
        verification_command,
        cwd=ROOT,
        env={
            **dict(__import__("os").environ),
            "PYTHONPATH": "src",
            "MPLCONFIGDIR": "/private/tmp/mplconfig",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    output = {
        "schema": "ztare-h105-graded-external-temporal-utility-audit-v1",
        "hypothesis_id": (
            "H-GPSA-GRADED-EXTERNAL-TEMPORAL-UTILITY-20260807-105"
        ),
        "status": (
            "supported"
            if all(checks.values()) and completed.returncode == 0
            else "failed"
        ),
        "environment_contact": False,
        "evidence_mode": (
            "retrospective_analysis_of_prospectively_collected_h95_pairs"
        ),
        "source": {
            "h95_result_ref": str(H95_PATH.relative_to(ROOT)),
            "h95_file_sha256": _file_sha256(H95_PATH),
            "h95_embedded_sha256": h95_embedded_sha,
        },
        "checks": checks,
        "graded": {
            "settled_pair_count": graded_receipt["settled_pair_count"],
            "pair_deltas": [
                row.external_value_delta for row in graded.pair_receipts
            ],
            "mean_settled_external_delta": (
                graded_receipt["mean_settled_external_delta"]
            ),
            "judgments": [
                row.to_receipt() for row in graded.judgments
            ],
            "sha256": graded.sha256,
        },
        "binary_baseline": {
            "settled_pair_count": binary_receipt["settled_pair_count"],
            "judgments": binary_receipt["judgments"],
            "sha256": binary_receipt["sha256"],
        },
        "negative_controls": {
            "mismatches": mismatches,
            "equal_utility": tie.to_receipt(),
        },
        "verification": {
            "command": verification_command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "stdout_sha256": hashlib.sha256(
                completed.stdout.encode("utf-8")
            ).hexdigest(),
            "stderr_sha256": hashlib.sha256(
                completed.stderr.encode("utf-8")
            ).hexdigest(),
        },
        "claim_boundary": (
            "graded exact-authority analysis of frozen H95 outcomes; "
            "no new environment result or benchmark claim"
        ),
    }
    output["sha256"] = stable_sha256(output)
    RESULT_PATH.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    SUMMARY_PATH.write_text(
        "\n".join((
            "# H105 graded external temporal utility result",
            "",
            f"Status: `{output['status']}`",
            "",
            "The frozen H95 pairs expose a value signal discarded by binary "
            "terminal settlement. Pair 1 contributed `+0.89`; pair 2 "
            "contributed `+0.07` even though both arms attained the task. "
            "Together they produce two exact-authority graded supports and "
            "mean delta `+0.48`.",
            "",
            "The binary attained/open compiler settled only pair 1 and "
            "remained undersampled at support two. Context, controller, "
            "measure, cost, and evidence mismatches refused. Equal external "
            "utility remained uninformative. The compiler preserved all four "
            "primitive costs and granted neither terminal-task nor "
            "information-yield authority.",
            "",
            "This is a retrospective analysis of prospectively collected H95 "
            "evidence. It adds no new environment outcome and does not admit "
            "H96 across its failed transport boundary.",
            "",
            f"Result SHA-256: `{output['sha256']}`",
            "",
        )) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "result_path": str(RESULT_PATH.relative_to(ROOT)),
        "summary_path": str(SUMMARY_PATH.relative_to(ROOT)),
        "status": output["status"],
        "checks": checks,
        "sha256": output["sha256"],
    }, indent=2, sort_keys=True))
    return 0 if output["status"] == "supported" else 1


if __name__ == "__main__":
    raise SystemExit(main())
