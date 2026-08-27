#!/usr/bin/env python3
"""Audit H106 persistence and exact-measure selector consumption."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(BASE))

from h105_graded_external_temporal_utility_audit import (  # noqa: E402
    H95_PATH,
    _lower_h95,
)
from ztare.common.continual_skill_memory import (  # noqa: E402
    MEMORY_SCHEMA,
    compile_persisted_temporal_decision_utility,
    empty_continual_skill_memory,
    judge_combined_decision_option_task_credit,
    load_continual_skill_memory,
    record_temporal_utility_arm,
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
    DecisionEligibilityChain,
    DecisionEligibilityEdge,
    compile_temporal_decision_credit,
)


RESULT_PATH = BASE / "h106_persistent_multichannel_decision_judgment_result.json"
SUMMARY_PATH = BASE / "h106_persistent_multichannel_decision_judgment_result.md"


def _candidate(
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


def _opposing_task_pairs(
    authority,
    continuation_policy_sha256: str,
    causal_family: str,
    placebo_family: str,
):
    pairs = []
    for pair_index in (1, 2):
        arms = []
        for arm_id, option, terminal in (
            ("causal", causal_family, "open"),
            ("placebo", placebo_family, "attained"),
        ):
            chain_ref = f"h106-opposing:{pair_index}:{arm_id}"
            arms.append(DecisionEligibilityChain(
                chain_ref=chain_ref,
                matched_pair_ref=f"h106-opposing:{pair_index}",
                arm_id=arm_id,
                continuation_policy_sha256=continuation_policy_sha256,
                edges=(DecisionEligibilityEdge(
                    chain_ref=chain_ref,
                    edge_index=0,
                    authority=authority,
                    chosen_option_family_sha256=option,
                    chosen_option_variant_sha256=f"{option}:opposing",
                    successor_decision_state_sha256=(
                        f"h106-opposing-terminal:{pair_index}:{arm_id}"
                    ),
                    predicted_information_yield=0.5,
                    observed_information_yield=0.5,
                    information_yield_measure_sha256=(
                        "h106-opposing-yield-measure"
                    ),
                    primitive_action_cost=20.0,
                    immediate_task_status="open",
                    evidence_ref=(
                        f"h106-opposing:{pair_index}:{arm_id}"
                    ),
                ),),
                terminal_task_status=terminal,
                terminal_adjudication_ref=(
                    f"h106-opposing-adjudication:{pair_index}:{arm_id}"
                ),
            ))
        pairs.append(tuple(arms))
    return tuple(pairs)


def main() -> int:
    h95 = json.loads(H95_PATH.read_text(encoding="utf-8"))
    utility_pairs, _binary_pairs = _lower_h95(h95)
    all_arms = tuple(
        arm for pair in utility_pairs for arm in pair
    )
    with tempfile.TemporaryDirectory(prefix="ztare-h106-") as tmp:
        path = Path(tmp) / "continual-skill-memory.json"
        legacy_payload = empty_continual_skill_memory().to_dict()
        legacy_payload["schema"] = "ztare-continual-skill-memory-v2"
        legacy_payload.pop("temporal_utility_arms")
        path.write_text(
            json.dumps(legacy_payload),
            encoding="utf-8",
        )
        migrated = load_continual_skill_memory(path)
        migrated_empty = (
            migrated.schema == MEMORY_SCHEMA
            and migrated.temporal_utility_arms == ()
        )
        memory = migrated
        for arm in all_arms:
            memory = record_temporal_utility_arm(memory, arm)
        before = tuple(
            arm.to_receipt() for arm in memory.temporal_utility_arms
        )
        serialized = memory.to_dict()
        no_derived_preference_serialized = (
            "temporal_utility_judgments" not in serialized
        )
        save_continual_skill_memory(path, memory)
        restored = load_continual_skill_memory(path)
        after = tuple(
            arm.to_receipt() for arm in restored.temporal_utility_arms
        )

    compilation = compile_persisted_temporal_decision_utility(
        restored,
        minimum_support=2,
    )
    compilation_receipt = compilation.to_receipt()
    authority = utility_pairs[0][0].authority
    measure_sha = utility_pairs[0][0].utility_measure.sha256
    causal_family = utility_pairs[0][0].chosen_option_family_sha256
    placebo_family = utility_pairs[0][1].chosen_option_family_sha256

    def query(option: str, **overrides):
        scope = {
            "decision_namespace": authority.decision_namespace,
            "option_family_sha256": option,
            "task_contract_sha256": authority.task_contract_sha256,
            "choice_context_sha256": authority.choice_context_sha256,
            "continuation_context_sha256": (
                authority.continuation_context_sha256
            ),
            "available_option_family_sha256s": (
                authority.available_option_family_sha256s
            ),
            "external_utility_measure_sha256": measure_sha,
            "utility_compilation": compilation,
        }
        scope.update(overrides)
        return judge_combined_decision_option_task_credit(
            restored,
            **scope,
        )

    causal = query(causal_family)
    placebo = query(placebo_family)
    candidates = (
        _candidate(
            "causal",
            preparation=("a", "b"),
            responses=("x", "x", "y"),
        ),
        _candidate(
            "placebo",
            preparation=("d",),
            responses=("x", "y", "z"),
        ),
    )
    weights = ProtocolYieldWeights(1.0, 1.0, 1.0)
    baseline = select_guarded_protocol(candidates, weights=weights)
    reranked = select_guarded_protocol(
        candidates,
        weights=weights,
        task_value_by_protocol_id={
            "causal": causal.preference,
            "placebo": placebo.preference,
        },
    )
    costs_before = {
        row.protocol_id: row.cost.to_receipt()
        for row in baseline.prices
    }
    costs_after = {
        row.protocol_id: row.cost.to_receipt()
        for row in reranked.prices
    }
    mismatch_preferences = {
        "no_measure": query(
            causal_family,
            external_utility_measure_sha256="",
        ).preference,
        "wrong_measure": query(
            causal_family,
            external_utility_measure_sha256="wrong-measure",
        ).preference,
        "wrong_context": query(
            causal_family,
            choice_context_sha256="wrong-context",
        ).preference,
        "wrong_controller": query(
            causal_family,
            continuation_context_sha256="wrong-controller",
        ).preference,
        "wrong_option_set": query(
            causal_family,
            available_option_family_sha256s=(
                causal_family,
                "different-option",
            ),
        ).preference,
        "wrong_task": query(
            causal_family,
            task_contract_sha256="wrong-task",
        ).preference,
    }
    opposing = compile_temporal_decision_credit(
        _opposing_task_pairs(
            authority,
            utility_pairs[0][0].continuation_policy_sha256,
            causal_family,
            placebo_family,
        ),
        minimum_support=2,
        max_eligibility_delay_steps=0,
    )
    conflict = query(
        causal_family,
        temporal_compilation=opposing,
    )
    conflicting_arm_refused = False
    try:
        record_temporal_utility_arm(
            restored,
            replace(
                utility_pairs[0][0],
                external_outcome_ref="h106-conflicting-evidence",
            ),
        )
    except ValueError as error:
        conflicting_arm_refused = "conflicting evidence" in str(error)

    checks = {
        "legacy_v2_migrates_empty": migrated_empty,
        "four_arms_round_trip_exactly": before == after and len(after) == 4,
        "derived_preference_not_serialized": (
            no_derived_preference_serialized
        ),
        "restored_h95_compilation": (
            compilation_receipt["settled_pair_count"] == 2
            and compilation_receipt["mean_settled_external_delta"]
            == h95["aggregate"]["mean_offer_minus_withhold_composite"]
        ),
        "utility_channels_positive_and_negative": (
            causal.immediate_preference == 0
            and causal.temporal_preference == 0
            and causal.utility_preference == 1
            and causal.preference == 1
            and placebo.utility_preference == -1
            and placebo.preference == -1
        ),
        "selector_flips_from_information_baseline": (
            baseline.selected_protocol_id == "placebo"
            and reranked.selected_protocol_id == "causal"
        ),
        "mismatches_are_neutral": not any(
            mismatch_preferences.values()
        ),
        "task_utility_conflict_is_neutral": (
            conflict.temporal_preference == -1
            and conflict.utility_preference == 1
            and conflict.status == "credit_conflict"
            and conflict.preference == 0
        ),
        "protocol_costs_unchanged": costs_before == costs_after,
        "conflicting_pair_arm_refused": conflicting_arm_refused,
        "channel_authorities_explicit": (
            causal.to_receipt()["authority_channels"]
            == {
                "immediate": "matched_external_terminal_adjudication",
                "temporal": "matched_external_terminal_adjudication",
                "utility": "matched_external_utility_adjudication",
                "information_yield": "selection_price_only",
            }
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
            **os.environ,
            "PYTHONPATH": "src",
            "MPLCONFIGDIR": "/private/tmp/mplconfig",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    output = {
        "schema": (
            "ztare-h106-persistent-multichannel-decision-judgment-audit-v1"
        ),
        "hypothesis_id": (
            "H-GPSA-PERSISTENT-MULTICHANNEL-DECISION-JUDGMENT-20260807-106"
        ),
        "status": (
            "supported"
            if all(checks.values()) and completed.returncode == 0
            else "failed"
        ),
        "environment_contact": False,
        "source": {
            "h95_result_ref": str(H95_PATH.relative_to(ROOT)),
            "h105_compilation_sha256": compilation.sha256,
        },
        "checks": checks,
        "memory": {
            "schema": MEMORY_SCHEMA,
            "arm_count": len(after),
            "memory_sha256": restored.memory_sha256,
            "stored_derived_preference": False,
        },
        "selection": {
            "baseline_protocol_id": baseline.selected_protocol_id,
            "reranked_protocol_id": reranked.selected_protocol_id,
            "causal_judgment": causal.to_receipt(),
            "placebo_judgment": placebo.to_receipt(),
            "mismatch_preferences": mismatch_preferences,
            "conflict_judgment": conflict.to_receipt(),
            "costs_before": costs_before,
            "costs_after": costs_after,
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
            "offline persistence and exact-measure selector consumption; "
            "no new ARC environment outcome"
        ),
    }
    from ztare.common.equivariance import stable_sha256

    output["sha256"] = stable_sha256(output)
    RESULT_PATH.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    SUMMARY_PATH.write_text(
        "\n".join((
            "# H106 persistent multichannel decision judgment result",
            "",
            f"Status: `{output['status']}`",
            "",
            "Four H95 external-utility arms survived a v3 continual-memory "
            "round trip. The memory stores arm evidence and rederives the "
            "preference; it does not serialize a derived judgment.",
            "",
            "With the exact H95 utility-measure hash, the causal option "
            "received `+1` and the placebo `-1`, flipping the guarded selector "
            "from the higher-information placebo to the externally better "
            "causal option. Protocol costs were unchanged. Missing or changed "
            "measure/task/context/controller/choice-set identities returned "
            "zero. Opposing terminal-task and utility values returned neutral "
            "conflict.",
            "",
            "This is an offline consumption result over frozen H95 evidence. "
            "It adds no environment outcome.",
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
