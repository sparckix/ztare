from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

from ztare.common.science_output_policy import SCIENCE_OUTPUT_POLICY


CandidateFirstContractId = Literal["worldmodel-candidate-first-v1"]
NonCandidateReason = Literal[
    "registered_workbench_action",
    "lowerability_blocked",
    "investigated",
]

CANDIDATE_FIRST_CONTRACT_ID: CandidateFirstContractId = "worldmodel-candidate-first-v1"

REGISTERED_ACTION_RECEIPT = "LEAF_WORKBENCH_ACTION_REQUEST"
CAPABILITY_PROPOSAL_RECEIPT = "LEAF_WORKBENCH_CAPABILITY_PROPOSAL"
LOWERABILITY_BLOCKED_RECEIPT = "LOWERABILITY_BLOCKED"
INVESTIGATED_RECEIPT = "INVESTIGATED"


@dataclass(frozen=True)
class CandidateFirstDecision:
    may_omit_candidate: bool
    reasons: tuple[NonCandidateReason, ...] = ()


def candidate_first_empty_candidate_decision(
    receipt_types: Iterable[str],
    *,
    lowerability_blocked: bool = False,
) -> CandidateFirstDecision:
    """Classify whether a candidate-first contract may omit executable code.

    This is a syntax-independent policy. Validators still check each receipt's
    payload shape and authority. The policy only decides whether an otherwise
    candidate-bearing response is allowed to be control-only.
    """

    seen = {str(receipt_type or "").strip() for receipt_type in receipt_types}
    reasons: list[NonCandidateReason] = []
    if REGISTERED_ACTION_RECEIPT in seen:
        reasons.append("registered_workbench_action")
    if LOWERABILITY_BLOCKED_RECEIPT in seen or lowerability_blocked:
        reasons.append("lowerability_blocked")
    if INVESTIGATED_RECEIPT in seen:
        # INVESTIGATED is a first-class honest-null outcome: the contract
        # tells the leaf to leave test_model_py empty for it — the policy
        # must not strike what the contract instructs.
        reasons.append("investigated")
    return CandidateFirstDecision(
        may_omit_candidate=bool(reasons),
        reasons=tuple(reasons),
    )


def candidate_first_policy_text() -> str:
    return (
        "Candidate-first policy: produce a transportable executable law whenever "
        "visible evidence permits. Empty `test_model_py` is admissible only for "
        "`LEAF_WORKBENCH_ACTION_REQUEST` to a registered workbench action, "
        "`LOWERABILITY_BLOCKED` carrying evidence that no gamma-lowerable "
        "candidate is currently justified after visible tools/candidate family "
        "were attempted, or `INVESTIGATED` carrying a credited elimination "
        "(eliminated hypothesis + witness + evidence refs) — an honest null "
        "that prunes the search is a valid science turn. A scored candidate "
        "regression may support continued "
        "local scratch work or a blocker when paired with an evidence-backed "
        "obstruction; the harness must not impose a fixed morphism checklist. "
        f"{SCIENCE_OUTPUT_POLICY.tool_gap_text()}"
    )
