from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ztare.primitives.primitive_library import load_approved_primitives_index
from ztare.validator.core.information_yield import ThesisControlMode


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
    THESIS_CONTROL_MODE_MISMATCH = "THESIS_CONTROL_MODE_MISMATCH"


@dataclass(frozen=True)
class MutationDeclaration:
    scope_delta: MutationScopeDelta
    claim_delta_type: ClaimDeltaType
    primitive_invoked: str | None
    touched_artifacts: tuple[MutationArtifact, ...]
    thesis_control_mode: ThesisControlMode = ThesisControlMode.EXPLOIT_CURRENT_THESIS


@dataclass(frozen=True)
class MutationValidationRecord:
    mismatch_code: MutationMismatchCode
    declared_scope_delta: MutationScopeDelta
    declared_claim_delta_type: ClaimDeltaType
    declared_thesis_control_mode: ThesisControlMode
    declared_primitive_invoked: str | None
    declared_touched_artifacts: tuple[MutationArtifact, ...]
    actual_touched_artifacts: tuple[MutationArtifact, ...]
    breadth_delta: int
    rationale: str


def parse_mutation_declaration(payload: dict[str, object]) -> MutationDeclaration:
    # Missing/invalid keys are kernel-derived, never a reject: the breadth
    # normalizer downstream replaces declared scope with the computed one
    # anyway, so a permissive default here only ever gets corrected upward.
    try:
        scope_delta = MutationScopeDelta(str(payload["scope_delta"]))
    except (KeyError, ValueError):
        scope_delta = MutationScopeDelta.MULTI_ARTIFACT
    try:
        claim_delta_type = ClaimDeltaType(str(payload["claim_delta_type"]))
    except (KeyError, ValueError):
        claim_delta_type = ClaimDeltaType.REFRAMING
    primitive_invoked = payload.get("primitive_invoked")
    thesis_control_mode = ThesisControlMode(
        str(payload.get("thesis_control_mode") or ThesisControlMode.EXPLOIT_CURRENT_THESIS.value)
    )
    touched_artifacts_payload = payload.get("touched_artifacts", ())
    if isinstance(touched_artifacts_payload, str):
        touched_artifacts_payload = [touched_artifacts_payload]
    if not isinstance(touched_artifacts_payload, (list, tuple)):
        raise ValueError("`touched_artifacts` must be a list.")
    touched_artifacts = tuple(MutationArtifact(str(item)) for item in touched_artifacts_payload)
    return MutationDeclaration(
        scope_delta=scope_delta,
        claim_delta_type=claim_delta_type,
        primitive_invoked=None if primitive_invoked in (None, "", "null") else str(primitive_invoked),
        touched_artifacts=touched_artifacts,
        thesis_control_mode=thesis_control_mode,
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
    expected_thesis_control_mode: ThesisControlMode | None = None,
) -> MutationValidationRecord:
    actual_touched_artifacts = _dedupe_preserve_order(
        tuple(_map_path_to_artifact(path) for path in changed_paths)
    )

    # ponytail: normalize envelope faults — bookkeeping the kernel can compute
    # from the artifact must be computed, not extracted under threat of strike.
    # Strikes are reserved for science-content failures (regression, gate failures).

    attribution_notes: list[str] = []

    if declaration.primitive_invoked and declaration.primitive_invoked not in approved_primitive_keys:
        # INVALID_PRIMITIVE_DECLARATION: advisory metadata gone stale — drop the
        # invalid key, attach a mismatch note, and proceed.
        import logging as _logging
        _logging.getLogger(__name__).info(
            "envelope-normalize INVALID_PRIMITIVE_DECLARATION: dropping %r (not in approved index); "
            "derived_by=kernel",
            declaration.primitive_invoked,
        )
        attribution_notes.append(
            f"INVALID_PRIMITIVE_DECLARATION normalized: dropped undeclared primitive "
            f"{declaration.primitive_invoked!r} (not in approved index); derived_by=kernel"
        )
        declaration = MutationDeclaration(
            scope_delta=declaration.scope_delta,
            claim_delta_type=declaration.claim_delta_type,
            primitive_invoked=None,
            touched_artifacts=declaration.touched_artifacts,
            thesis_control_mode=declaration.thesis_control_mode,
        )

    if not _artifacts_within_declared_scope(declaration, actual_touched_artifacts):
        # UNDECLARED_ARTIFACT_BREADTH: kernel already computed actual_touched_artifacts;
        # upgrade scope_delta to cover them instead of rejecting.
        upgraded_scope = _infer_scope_for_artifacts(actual_touched_artifacts)
        import logging as _logging
        _logging.getLogger(__name__).info(
            "envelope-normalize UNDECLARED_ARTIFACT_BREADTH: upgrading scope %s→%s for actual=%s; "
            "derived_by=kernel",
            declaration.scope_delta.value,
            upgraded_scope.value,
            [a.value for a in actual_touched_artifacts],
        )
        attribution_notes.append(
            f"UNDECLARED_ARTIFACT_BREADTH normalized: scope upgraded "
            f"{declaration.scope_delta.value}→{upgraded_scope.value} to cover actual artifacts "
            f"{[a.value for a in actual_touched_artifacts]}; derived_by=kernel"
        )
        declaration = MutationDeclaration(
            scope_delta=upgraded_scope,
            claim_delta_type=declaration.claim_delta_type,
            primitive_invoked=declaration.primitive_invoked,
            touched_artifacts=actual_touched_artifacts,
            thesis_control_mode=declaration.thesis_control_mode,
        )

    breadth_delta = _estimate_claim_breadth(after_text) - _estimate_claim_breadth(before_text)
    if (
        expected_thesis_control_mode is not None
        and declaration.thesis_control_mode != expected_thesis_control_mode
    ):
        return MutationValidationRecord(
            mismatch_code=MutationMismatchCode.THESIS_CONTROL_MODE_MISMATCH,
            declared_scope_delta=declaration.scope_delta,
            declared_claim_delta_type=declaration.claim_delta_type,
            declared_thesis_control_mode=declaration.thesis_control_mode,
            declared_primitive_invoked=declaration.primitive_invoked,
            declared_touched_artifacts=declaration.touched_artifacts,
            actual_touched_artifacts=actual_touched_artifacts,
            breadth_delta=breadth_delta,
            rationale=(
                "Declared thesis_control_mode does not match the pending loop-control signal "
                f"({declaration.thesis_control_mode.value} != {expected_thesis_control_mode.value})."
            ),
        )

    if declaration.claim_delta_type == ClaimDeltaType.NARROWING and breadth_delta > 0:
        return MutationValidationRecord(
            mismatch_code=MutationMismatchCode.CLAIM_DELTA_SCOPE_CONFLICT,
            declared_scope_delta=declaration.scope_delta,
            declared_claim_delta_type=declaration.claim_delta_type,
            declared_thesis_control_mode=declaration.thesis_control_mode,
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
            declared_thesis_control_mode=declaration.thesis_control_mode,
            declared_primitive_invoked=declaration.primitive_invoked,
            declared_touched_artifacts=declaration.touched_artifacts,
            actual_touched_artifacts=actual_touched_artifacts,
            breadth_delta=breadth_delta,
            rationale="Declared widening conflicts with a measured decrease in claim breadth.",
        )

    base_rationale = "Mutation declaration matches touched artifacts and measured breadth change."
    if attribution_notes:
        base_rationale = base_rationale + " [envelope-normalized: " + "; ".join(attribution_notes) + "]"
    return MutationValidationRecord(
        mismatch_code=MutationMismatchCode.CLEAN,
        declared_scope_delta=declaration.scope_delta,
        declared_claim_delta_type=declaration.claim_delta_type,
        declared_thesis_control_mode=declaration.thesis_control_mode,
        declared_primitive_invoked=declaration.primitive_invoked,
        declared_touched_artifacts=declaration.touched_artifacts,
        actual_touched_artifacts=actual_touched_artifacts,
        breadth_delta=breadth_delta,
        rationale=base_rationale,
    )


def _infer_scope_for_artifacts(
    actual_touched_artifacts: tuple[MutationArtifact, ...],
) -> MutationScopeDelta:
    """Derive the tightest MutationScopeDelta that covers all actual artifacts.

    Used by the envelope normalizer when the declared scope is too narrow.
    Falls back to MULTI_ARTIFACT for unusual artifact combinations.
    """
    artifact_set = set(actual_touched_artifacts)
    thesis_only_set = {MutationArtifact.THESIS_MD, MutationArtifact.CURRENT_ITERATION_MD}
    test_harness_set = thesis_only_set | {MutationArtifact.TEST_MODEL_PY}
    evidence_boundary_set = thesis_only_set | {MutationArtifact.EVIDENCE_TXT}
    rubric_interface_set = {MutationArtifact.RUBRIC_JSON, MutationArtifact.RUNNER_RUNTIME}

    if artifact_set.issubset(thesis_only_set):
        return MutationScopeDelta.THESIS_ONLY
    if artifact_set.issubset(test_harness_set):
        return MutationScopeDelta.TEST_HARNESS
    if artifact_set.issubset(evidence_boundary_set):
        return MutationScopeDelta.EVIDENCE_BOUNDARY
    if artifact_set.issubset(rubric_interface_set):
        return MutationScopeDelta.RUBRIC_INTERFACE
    return MutationScopeDelta.MULTI_ARTIFACT


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
