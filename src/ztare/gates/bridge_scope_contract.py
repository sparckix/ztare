from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.ztare.validator.mutation_contract import (
    MutationArtifact,
    MutationDeclaration,
    MutationScopeDelta,
)


class BridgeScopeMismatchCode(str, Enum):
    CLEAN = "CLEAN"
    INVALID_SCOPE_DELTA = "INVALID_SCOPE_DELTA"
    INVALID_ARTIFACT_SET = "INVALID_ARTIFACT_SET"
    NON_BRIDGE_MECHANISM = "NON_BRIDGE_MECHANISM"


@dataclass(frozen=True)
class BridgeScopeValidationRecord:
    mismatch_code: BridgeScopeMismatchCode
    rationale: str
    scope_signals: tuple[str, ...]


ALLOWED_SCOPE_DELTAS = {
    MutationScopeDelta.THESIS_ONLY,
    MutationScopeDelta.TEST_HARNESS,
    MutationScopeDelta.EVIDENCE_BOUNDARY,
    MutationScopeDelta.MULTI_ARTIFACT,
}

ALLOWED_ARTIFACTS = {
    MutationArtifact.THESIS_MD,
    MutationArtifact.CURRENT_ITERATION_MD,
    MutationArtifact.TEST_MODEL_PY,
    MutationArtifact.EVIDENCE_TXT,
}

FORBIDDEN_BRIDGE_MARKERS = (
    "groundingsignalreport",
    "derive_grounding_signals",
    "falsificationcontract",
    "semantic gate flip rate",
    "stable bad-case retention",
    "good-control false-reject behavior",
    "good control false reject behavior",
)


def evaluate_bridge_scope(
    declaration: MutationDeclaration,
    *,
    thesis_text: str,
    python_code: str,
) -> BridgeScopeValidationRecord:
    if declaration.scope_delta not in ALLOWED_SCOPE_DELTAS:
        return BridgeScopeValidationRecord(
            mismatch_code=BridgeScopeMismatchCode.INVALID_SCOPE_DELTA,
            rationale="Bridge discovery only allows thesis, harness, evidence, or bounded multi-artifact mutations.",
            scope_signals=(declaration.scope_delta.value,),
        )

    touched = set(declaration.touched_artifacts)
    if not touched.issubset(ALLOWED_ARTIFACTS):
        invalid = sorted(item.value for item in touched - ALLOWED_ARTIFACTS)
        return BridgeScopeValidationRecord(
            mismatch_code=BridgeScopeMismatchCode.INVALID_ARTIFACT_SET,
            rationale="Bridge discovery touched artifacts outside the bridge contract surface.",
            scope_signals=tuple(invalid),
        )

    combined = f"{thesis_text}\n{python_code}".lower()
    found = tuple(marker for marker in FORBIDDEN_BRIDGE_MARKERS if marker in combined)
    if found:
        return BridgeScopeValidationRecord(
            mismatch_code=BridgeScopeMismatchCode.NON_BRIDGE_MECHANISM,
            rationale="Candidate introduces a non-bridge mechanism instead of mutating the audited bridge contract.",
            scope_signals=found,
        )

    return BridgeScopeValidationRecord(
        mismatch_code=BridgeScopeMismatchCode.CLEAN,
        rationale="Candidate remains within the bounded bridge contract surface.",
        scope_signals=(),
    )
