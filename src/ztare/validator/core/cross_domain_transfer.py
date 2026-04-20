from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TransferDecision(str, Enum):
    ALLOW = "ALLOW"
    SUPPRESS = "SUPPRESS"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class TransferRequirement(str, Enum):
    TARGET_LANGUAGE_RESTATEMENT = "mechanism_restated_in_target_language"
    TARGET_VARIABLES_IDENTIFIED = "target_domain_variables_identified"
    EXPLICIT_BREAK_CASE = "explicit_break_case_provided"
    TARGET_FALSIFICATION_CHECK = "target_domain_falsification_check_present"


class TransferReasonCode(str, Enum):
    ALLOW_ALL_REQUIREMENTS_MET = "ALLOW_ALL_REQUIREMENTS_MET"
    SUPPRESS_MISSING_REQUIREMENTS = "SUPPRESS_MISSING_REQUIREMENTS"
    MANUAL_REVIEW_STAGE24_BRIDGE = "MANUAL_REVIEW_STAGE24_BRIDGE"


@dataclass(frozen=True)
class TransferRequest:
    source_domain: str
    target_domain: str
    mechanism_restated_in_target_language: bool
    target_domain_variables_identified: bool
    explicit_break_case_provided: bool
    target_domain_falsification_check_present: bool
    requires_stage24_bridge: bool = False
    stage24_bridge_hardened: bool = False


@dataclass(frozen=True)
class TransferDecisionRecord:
    decision: TransferDecision
    reason_code: TransferReasonCode
    source_domain: str
    target_domain: str
    missing_requirements: tuple[TransferRequirement, ...]
    requires_stage24_bridge: bool
    stage24_bridge_hardened: bool


def evaluate_transfer_request(request: TransferRequest) -> TransferDecisionRecord:
    if request.requires_stage24_bridge and not request.stage24_bridge_hardened:
        return TransferDecisionRecord(
            decision=TransferDecision.MANUAL_REVIEW,
            reason_code=TransferReasonCode.MANUAL_REVIEW_STAGE24_BRIDGE,
            source_domain=request.source_domain,
            target_domain=request.target_domain,
            missing_requirements=(),
            requires_stage24_bridge=request.requires_stage24_bridge,
            stage24_bridge_hardened=request.stage24_bridge_hardened,
        )

    missing_requirements: list[TransferRequirement] = []
    if not request.mechanism_restated_in_target_language:
        missing_requirements.append(TransferRequirement.TARGET_LANGUAGE_RESTATEMENT)
    if not request.target_domain_variables_identified:
        missing_requirements.append(TransferRequirement.TARGET_VARIABLES_IDENTIFIED)
    if not request.explicit_break_case_provided:
        missing_requirements.append(TransferRequirement.EXPLICIT_BREAK_CASE)
    if not request.target_domain_falsification_check_present:
        missing_requirements.append(TransferRequirement.TARGET_FALSIFICATION_CHECK)

    if missing_requirements:
        return TransferDecisionRecord(
            decision=TransferDecision.SUPPRESS,
            reason_code=TransferReasonCode.SUPPRESS_MISSING_REQUIREMENTS,
            source_domain=request.source_domain,
            target_domain=request.target_domain,
            missing_requirements=tuple(missing_requirements),
            requires_stage24_bridge=request.requires_stage24_bridge,
            stage24_bridge_hardened=request.stage24_bridge_hardened,
        )

    return TransferDecisionRecord(
        decision=TransferDecision.ALLOW,
        reason_code=TransferReasonCode.ALLOW_ALL_REQUIREMENTS_MET,
        source_domain=request.source_domain,
        target_domain=request.target_domain,
        missing_requirements=(),
        requires_stage24_bridge=request.requires_stage24_bridge,
        stage24_bridge_hardened=request.stage24_bridge_hardened,
    )
