from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from src.ztare.primitives.primitive_library import load_approved_primitives_index


class MutationScopeDelta(str, Enum):
    THESIS_ONLY = "THESIS_ONLY"
    TEST_HARNESS = "TEST_HARNESS"
    EVIDENCE_BOUNDARY = "EVIDENCE_BOUNDARY"
    RUBRIC_INTERFACE = "RUBRIC_INTERFACE"
    MULTI_ARTIFACT = "MULTI_ARTIFACT"


class ClaimDeltaType(str, Enum):
    NARROWING = "NARROWING"
    WIDENING = "WIDENING"
    REFRAMING = "REFRAMING"


class MutationArtifact(str, Enum):
    THESIS_MD = "thesis.md"
    CURRENT_ITERATION_MD = "current_iteration.md"
    TEST_MODEL_PY = "test_model.py"
    EVIDENCE_TXT = "evidence.txt"
    RUBRIC_JSON = "rubric.json"
    RUNNER_RUNTIME = "runner_runtime"
    OTHER = "other"


class MutationMismatchCode(str, Enum):
    CLEAN = "CLEAN"
    UNDECLARED_ARTIFACT_BREADTH = "UNDECLARED_ARTIFACT_BREADTH"
    INVALID_PRIMITIVE_DECLARATION = "INVALID_PRIMITIVE_DECLARATION"
    CLAIM_DELTA_SCOPE_CONFLICT = "CLAIM_DELTA_SCOPE_CONFLICT"


@dataclass(frozen=True)
class MutationDeclaration:
    scope_delta: MutationScopeDelta
    claim_delta_type: ClaimDeltaType
    primitive_invoked: str | None
    touched_artifacts: tuple[MutationArtifact, ...]


@dataclass(frozen=True)
class MutationValidationRecord:
    mismatch_code: MutationMismatchCode
    declared_scope_delta: MutationScopeDelta
    declared_claim_delta_type: ClaimDeltaType
    declared_primitive_invoked: str | None
    declared_touched_artifacts: tuple[MutationArtifact, ...]
    actual_touched_artifacts: tuple[MutationArtifact, ...]
    breadth_delta: int
    rationale: str


def parse_mutation_declaration(payload: dict[str, object]) -> MutationDeclaration:
    scope_delta = MutationScopeDelta(str(payload["scope_delta"]))
    claim_delta_type = ClaimDeltaType(str(payload["claim_delta_type"]))
    primitive_invoked = payload.get("primitive_invoked")
    touched_artifacts_payload = payload.get("touched_artifacts", ())
    if not isinstance(touched_artifacts_payload, (list, tuple)):
        raise ValueError("`touched_artifacts` must be a list.")
    touched_artifacts = tuple(MutationArtifact(str(item)) for item in touched_artifacts_payload)
    return MutationDeclaration(
        scope_delta=scope_delta,
        claim_delta_type=claim_delta_type,
        primitive_invoked=None if primitive_invoked in (None, "", "null") else str(primitive_invoked),
        touched_artifacts=touched_artifacts,
    )


def approved_primitive_keys() -> tuple[str, ...]:
    return tuple(sorted(load_approved_primitives_index().keys()))


def evaluate_mutation_declaration(
    declaration: MutationDeclaration,
    changed_paths: tuple[str, ...],
    *,
    before_text: str = "",
    after_text: str = "",
    approved_primitive_keys: tuple[str, ...] = (),
) -> MutationValidationRecord:
    actual_touched_artifacts = _dedupe_preserve_order(
        tuple(_map_path_to_artifact(path) for path in changed_paths)
    )

    if declaration.primitive_invoked and declaration.primitive_invoked not in approved_primitive_keys:
        return MutationValidationRecord(
            mismatch_code=MutationMismatchCode.INVALID_PRIMITIVE_DECLARATION,
            declared_scope_delta=declaration.scope_delta,
            declared_claim_delta_type=declaration.claim_delta_type,
            declared_primitive_invoked=declaration.primitive_invoked,
            declared_touched_artifacts=declaration.touched_artifacts,
            actual_touched_artifacts=actual_touched_artifacts,
            breadth_delta=_estimate_claim_breadth(after_text) - _estimate_claim_breadth(before_text),
            rationale="Declared primitive key is not in the approved primitive index.",
        )

    if not _artifacts_within_declared_scope(declaration, actual_touched_artifacts):
        return MutationValidationRecord(
            mismatch_code=MutationMismatchCode.UNDECLARED_ARTIFACT_BREADTH,
            declared_scope_delta=declaration.scope_delta,
            declared_claim_delta_type=declaration.claim_delta_type,
            declared_primitive_invoked=declaration.primitive_invoked,
            declared_touched_artifacts=declaration.touched_artifacts,
            actual_touched_artifacts=actual_touched_artifacts,
            breadth_delta=_estimate_claim_breadth(after_text) - _estimate_claim_breadth(before_text),
            rationale="Actual touched artifacts exceed the declared mutation scope.",
        )

    breadth_delta = _estimate_claim_breadth(after_text) - _estimate_claim_breadth(before_text)
    if declaration.claim_delta_type == ClaimDeltaType.NARROWING and breadth_delta > 0:
        return MutationValidationRecord(
            mismatch_code=MutationMismatchCode.CLAIM_DELTA_SCOPE_CONFLICT,
            declared_scope_delta=declaration.scope_delta,
            declared_claim_delta_type=declaration.claim_delta_type,
            declared_primitive_invoked=declaration.primitive_invoked,
            declared_touched_artifacts=declaration.touched_artifacts,
            actual_touched_artifacts=actual_touched_artifacts,
            breadth_delta=breadth_delta,
            rationale="Declared narrowing conflicts with a measured increase in claim breadth.",
        )
    if declaration.claim_delta_type == ClaimDeltaType.WIDENING and breadth_delta < 0:
        return MutationValidationRecord(
            mismatch_code=MutationMismatchCode.CLAIM_DELTA_SCOPE_CONFLICT,
            declared_scope_delta=declaration.scope_delta,
            declared_claim_delta_type=declaration.claim_delta_type,
            declared_primitive_invoked=declaration.primitive_invoked,
            declared_touched_artifacts=declaration.touched_artifacts,
            actual_touched_artifacts=actual_touched_artifacts,
            breadth_delta=breadth_delta,
            rationale="Declared widening conflicts with a measured decrease in claim breadth.",
        )

    return MutationValidationRecord(
        mismatch_code=MutationMismatchCode.CLEAN,
        declared_scope_delta=declaration.scope_delta,
        declared_claim_delta_type=declaration.claim_delta_type,
        declared_primitive_invoked=declaration.primitive_invoked,
        declared_touched_artifacts=declaration.touched_artifacts,
        actual_touched_artifacts=actual_touched_artifacts,
        breadth_delta=breadth_delta,
        rationale="Mutation declaration matches touched artifacts and measured breadth change.",
    )


def _artifacts_within_declared_scope(
    declaration: MutationDeclaration,
    actual_touched_artifacts: tuple[MutationArtifact, ...],
) -> bool:
    if declaration.scope_delta == MutationScopeDelta.MULTI_ARTIFACT:
        return True

    allowed = set(declaration.touched_artifacts)
    if declaration.scope_delta == MutationScopeDelta.THESIS_ONLY:
        allowed |= {MutationArtifact.THESIS_MD, MutationArtifact.CURRENT_ITERATION_MD}
    elif declaration.scope_delta == MutationScopeDelta.TEST_HARNESS:
        allowed |= {
            MutationArtifact.THESIS_MD,
            MutationArtifact.CURRENT_ITERATION_MD,
            MutationArtifact.TEST_MODEL_PY,
        }
    elif declaration.scope_delta == MutationScopeDelta.EVIDENCE_BOUNDARY:
        allowed |= {
            MutationArtifact.THESIS_MD,
            MutationArtifact.CURRENT_ITERATION_MD,
            MutationArtifact.EVIDENCE_TXT,
        }
    elif declaration.scope_delta == MutationScopeDelta.RUBRIC_INTERFACE:
        allowed |= {
            MutationArtifact.RUBRIC_JSON,
            MutationArtifact.RUNNER_RUNTIME,
        }

    return set(actual_touched_artifacts).issubset(allowed)


def _map_path_to_artifact(path: str) -> MutationArtifact:
    name = Path(path).name
    if name == "thesis.md":
        return MutationArtifact.THESIS_MD
    if name == "current_iteration.md":
        return MutationArtifact.CURRENT_ITERATION_MD
    if name == "test_model.py":
        return MutationArtifact.TEST_MODEL_PY
    if name == "evidence.txt":
        return MutationArtifact.EVIDENCE_TXT
    if name.endswith(".json") and "rubric" in name:
        return MutationArtifact.RUBRIC_JSON
    if path.startswith("src/ztare/validator/") or path.startswith("rubrics/"):
        return MutationArtifact.RUNNER_RUNTIME
    return MutationArtifact.OTHER


def _estimate_claim_breadth(text: str) -> int:
    normalized = text.lower().replace("**", "").replace("`", "")
    breadth_tokens = (
        "whole-system",
        "whole system",
        "end-to-end",
        "end to end",
        "system-level",
        "system level",
        "stable adversarial coverage",
        "systemic trust repair",
        "cannot ever pass",
        "guarantee",
        "completeness",
    )
    return sum(normalized.count(token) for token in breadth_tokens)


def _dedupe_preserve_order(items: tuple[MutationArtifact, ...]) -> tuple[MutationArtifact, ...]:
    ordered: list[MutationArtifact] = []
    for item in items:
        if item not in ordered:
            ordered.append(item)
    return tuple(ordered)
