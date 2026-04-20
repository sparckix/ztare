from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.ztare.validator.core.hinge_handoff import (
    ArtifactType,
    HingeAlignmentStatus,
    HingeGroundingPointer,
    HingeObject,
    HingeScopeLevel,
    Stage2Handoff,
    derive_hinge_object,
    evaluate_hinge_grounding,
)
from src.ztare.validator.core.primitive_routing import ExploitFamilyTag, derive_exploit_family_tag


class BridgeMismatchClass(str, Enum):
    CLEAN = "CLEAN"
    FAMILY_TAG_UNDERSPECIFIED = "FAMILY_TAG_UNDERSPECIFIED"
    GROUNDING_POINTER_ABSENT = "GROUNDING_POINTER_ABSENT"
    SCOPE_BOUNDARY_CONTRADICTED = "SCOPE_BOUNDARY_CONTRADICTED"
    BRIDGE_UNRESOLVED = "BRIDGE_UNRESOLVED"


class BridgeResolutionStatus(str, Enum):
    CLEAN_HANDOFF = "CLEAN_HANDOFF"
    FAIL_CLOSED_UNRESOLVED = "FAIL_CLOSED_UNRESOLVED"


@dataclass(frozen=True)
class BridgeRecord:
    family_tag: ExploitFamilyTag
    mismatch_class: BridgeMismatchClass
    resolution_status: BridgeResolutionStatus
    derived_handoff: Optional[Stage2Handoff]
    downstream_handoff: Stage2Handoff
    source_signals: tuple[str, ...]


def build_stage24_bridge_record(
    thesis_text: str,
    evidence_text: str,
    test_model_text: str = "",
    critiques_text: str = "",
) -> BridgeRecord:
    family_tag, family_rationale = derive_exploit_family_tag(
        thesis_text=thesis_text,
        evidence_text=evidence_text,
        critiques_text=critiques_text,
    )
    hinge = derive_hinge_object(
        family_tag=family_tag,
        thesis_text=thesis_text,
        evidence_text=evidence_text,
        test_model_text=test_model_text,
    )
    alignment_status = evaluate_hinge_grounding(hinge)
    derived_handoff = Stage2Handoff(
        family_tag=family_tag,
        hinge=hinge,
        alignment_status=alignment_status,
        provenance_verified=alignment_status != HingeAlignmentStatus.UNRESOLVED_UNGROUNDED,
        rationale=f"{family_rationale} | Stage-2 handoff derived as {alignment_status.value}.",
    )

    mismatch_class, source_signals = _classify_bridge_mismatch(
        family_tag=family_tag,
        hinge=hinge,
        alignment_status=alignment_status,
        thesis_text=thesis_text,
        evidence_text=evidence_text,
        test_model_text=test_model_text,
    )
    if mismatch_class == BridgeMismatchClass.CLEAN:
        return BridgeRecord(
            family_tag=family_tag,
            mismatch_class=mismatch_class,
            resolution_status=BridgeResolutionStatus.CLEAN_HANDOFF,
            derived_handoff=derived_handoff,
            downstream_handoff=derived_handoff,
            source_signals=source_signals,
        )

    return BridgeRecord(
        family_tag=family_tag,
        mismatch_class=mismatch_class,
        resolution_status=BridgeResolutionStatus.FAIL_CLOSED_UNRESOLVED,
        derived_handoff=derived_handoff,
        downstream_handoff=_fail_closed_handoff(derived_handoff, mismatch_class),
        source_signals=source_signals,
    )


def _classify_bridge_mismatch(
    *,
    family_tag: ExploitFamilyTag,
    hinge: HingeObject,
    alignment_status: HingeAlignmentStatus,
    thesis_text: str,
    evidence_text: str,
    test_model_text: str,
) -> tuple[BridgeMismatchClass, tuple[str, ...]]:
    normalized = _normalize_text("\n".join(part for part in (thesis_text, evidence_text) if part))
    signals: list[str] = []

    if _has_scope_boundary_contradiction(normalized):
        signals.append("local-scope disclaimer coexists with whole-system guarantee language")
        return BridgeMismatchClass.SCOPE_BOUNDARY_CONTRADICTED, tuple(signals)

    recovered_family = _recover_family_from_bridge_surface(normalized, test_model_text)
    if recovered_family is not ExploitFamilyTag.UNKNOWN and recovered_family != family_tag:
        signals.append(
            f"family recoverable from bridge surface as {recovered_family.value}, "
            f"but derivation produced {family_tag.value}"
        )
        return BridgeMismatchClass.FAMILY_TAG_UNDERSPECIFIED, tuple(signals)

    if _is_explicitly_exploratory_bridge(normalized):
        signals.append("text stays exploratory/non-committal and does not justify a confident bridge handoff")
        return BridgeMismatchClass.BRIDGE_UNRESOLVED, tuple(signals)

    grounding_signal = _grounding_pointer_absent_or_insufficient(
        family_tag=family_tag,
        hinge=hinge,
        normalized_text=normalized,
        test_model_text=test_model_text,
    )
    if grounding_signal is not None:
        signals.append(grounding_signal)
        return BridgeMismatchClass.GROUNDING_POINTER_ABSENT, tuple(signals)

    if alignment_status == HingeAlignmentStatus.UNRESOLVED_UNGROUNDED:
        signals.append("bridge derivation could not produce a grounded non-clean handoff")
        return BridgeMismatchClass.BRIDGE_UNRESOLVED, tuple(signals)

    signals.append("bridge derivation is internally coherent")
    return BridgeMismatchClass.CLEAN, tuple(signals)


def _recover_family_from_bridge_surface(normalized_text: str, test_model_text: str) -> ExploitFamilyTag:
    if _is_explicitly_exploratory_bridge(normalized_text):
        return ExploitFamilyTag.UNKNOWN

    has_local_parser_surface = any(
        token in normalized_text
        for token in (
            "exactly two-character hexadecimal token",
            "parser over a fixed input alphabet",
            "rejects everything else",
            "bounded local component",
            "one narrow problem",
            "opaque symbols, not trusted truths",
        )
    )
    has_local_executable_locus = bool(test_model_text.strip()) and (
        "assert " in test_model_text or "def " in test_model_text or "class " in test_model_text
    )
    if has_local_parser_surface and has_local_executable_locus and not _has_affirmative_whole_system_claim(
        normalized_text
    ):
        return ExploitFamilyTag.LOCAL_SAFE_HARBOR

    if _contains_any(
        normalized_text,
        ("future distress", "future prediction", "progression risk", "six-month progression", "by q4", "by q1"),
    ) and _contains_any(
        normalized_text,
        ("threshold", "cutoff", "thesis-authored", "thesis authored", "progression cutoff"),
    ):
        return ExploitFamilyTag.SELF_REFERENCE_FUTURE_PREDICTION

    return ExploitFamilyTag.UNKNOWN


def _has_scope_boundary_contradiction(text: str) -> bool:
    local_scope = _has_affirmative_local_scope(text)
    whole_system = _has_affirmative_whole_system_claim(text)
    return local_scope and whole_system


def _has_affirmative_local_scope(text: str) -> bool:
    if _contains_any(
        text,
        (
            "not a local component claim",
            "not a local component",
            "does not claim to be a local component",
        ),
    ):
        return False
    return _contains_any(
        text,
        (
            "this is a bounded local component",
            "bounded local component",
            "one narrow problem",
            "local deterministic mapping",
            "local token-to-decision mapping",
            "scope discipline",
            "local component",
        ),
    )


def _has_affirmative_whole_system_claim(text: str) -> bool:
    if _contains_any(
        text,
        (
            "does not claim whole-system",
            "does not claim whole system",
            "does not claim to guarantee whole-system",
            "does not claim to guarantee whole system",
            "not as a whole-system guarantee",
            "not as a whole system guarantee",
            "does not claim to guarantee end-to-end",
            "does not claim to guarantee end to end",
            "not a local component claim",
        ),
    ):
        negated_terms = True
    else:
        negated_terms = False

    future_claim = _contains_any(
        text,
        (
            "future distress",
            "future prediction",
            "six-month progression",
            "by q4",
            "by q1",
        ),
    )
    explicit_guarantee = _contains_any(
        text,
        (
            "ensures",
            "cannot ever pass through the evaluation stack",
            "cannot pass through the evaluation system",
            "whole-system protection",
            "whole system protection",
            "end-to-end protection",
            "end to end protection",
            "system-level protection",
        ),
    )
    plain_terms = _contains_any(
        text,
        (
            "whole-system",
            "whole system",
            "end-to-end",
            "end to end",
            "system-level",
            "system level",
        ),
    )
    return future_claim or explicit_guarantee or (plain_terms and not negated_terms)


def _grounding_pointer_absent_or_insufficient(
    *,
    family_tag: ExploitFamilyTag,
    hinge: HingeObject,
    normalized_text: str,
    test_model_text: str,
) -> str | None:
    if _grounding_pointer_missing_for_local_claim(hinge):
        return "bridge lacks a usable executable grounding pointer for the claimed local/generic mechanism"

    if _has_self_certifying_metric_surface(normalized_text, test_model_text):
        return "claim relies on a self-certifying internal metric rather than an independently falsifiable grounding locus"

    if _has_broad_claim_with_thin_falsification(normalized_text, test_model_text):
        return "broad claim has only thin or trivial executable falsification coverage"

    if (
        family_tag in (ExploitFamilyTag.LOCAL_SAFE_HARBOR, ExploitFamilyTag.UNKNOWN)
        and _assert_count(test_model_text) <= 1
        and _contains_any(
            normalized_text,
            (
                "all edge cases",
                "any list",
                "any input",
                "all critical operations",
                "all nodes",
                "universal",
            ),
        )
    ):
        return "bridge presents a broad universal claim with only one executable check"

    return None


def _grounding_pointer_missing_for_local_claim(hinge: HingeObject) -> bool:
    if hinge.scope_level not in (HingeScopeLevel.LOCAL_COMPONENT, HingeScopeLevel.GENERIC_WEAKEST_POINT):
        return False
    if hinge.grounding_pointer is None:
        return True
    if hinge.grounding_pointer.artifact_type == ArtifactType.THESIS_PROSE:
        return True
    return hinge.grounding_pointer.artifact_locus.strip() == ""


def _has_self_certifying_metric_surface(text: str, test_model_text: str) -> bool:
    disclaimer_surface = _contains_any(
        text,
        (
            "metric is defined exclusively by the system's internal",
            "metric is defined exclusively by the systems internal",
            "hardcoded to always report 100% availability",
            "hardcoded to always report 100% reliability",
            "hardcoded to always report",
            "external validation or user-perceived downtime is explicitly excluded",
            "external validation or user perceived downtime is explicitly excluded",
            "internal uptime counter",
            "user-perceived downtime is explicitly excluded",
            "user perceived downtime is explicitly excluded",
        ),
    )
    hardcoded_metric_surface = _contains_any(
        _normalize_text(test_model_text),
        (
            "return 1.0",
            "return 100.0",
            "return 100",
            "always report 100% availability",
            "always report 100% reliability",
            "get_system_reliability_metric",
            "uptime counter",
        ),
    )
    whole_system_surface = _has_affirmative_whole_system_claim(text)
    return whole_system_surface and (disclaimer_surface or hardcoded_metric_surface)


def _has_broad_claim_with_thin_falsification(text: str, test_model_text: str) -> bool:
    broad_claim = _contains_any(
        text,
        (
            "any list",
            "all edge cases",
            "single-element lists",
            "single element lists",
            "lists with duplicates",
            "lists with negative numbers",
            "all critical operations",
            "all nodes",
            "any input",
            "universal",
        ),
    )
    if not broad_claim:
        return False
    return _assert_count(test_model_text) <= 1


def _is_explicitly_exploratory_bridge(text: str) -> bool:
    return _contains_any(
        text,
        (
            "does not assert",
            "exploratory and intentionally non-committal",
            "exploratory and intentionally non committal",
            "generic weakest-point thesis",
            "generic weakest point thesis",
        ),
    )


def _fail_closed_handoff(derived_handoff: Stage2Handoff, mismatch_class: BridgeMismatchClass) -> Stage2Handoff:
    unresolved_hinge = HingeObject(
        hinge_claim_summary=f"Bridge fail-closed due to {mismatch_class.value}.",
        decisive_variable=derived_handoff.hinge.decisive_variable,
        decisive_variable_origin=derived_handoff.hinge.decisive_variable_origin,
        scope_level=derived_handoff.hinge.scope_level,
        grounding_pointer=HingeGroundingPointer(ArtifactType.THESIS_PROSE, mismatch_class.value),
        direct_test_present=derived_handoff.hinge.direct_test_present,
        whole_system_claim_present=derived_handoff.hinge.whole_system_claim_present,
    )
    return Stage2Handoff(
        family_tag=derived_handoff.family_tag,
        hinge=unresolved_hinge,
        alignment_status=HingeAlignmentStatus.UNRESOLVED_UNGROUNDED,
        provenance_verified=False,
        rationale=(
            f"Bridge mismatch {mismatch_class.value} triggered fail-closed reconciliation to "
            "UNRESOLVED_UNGROUNDED."
        ),
    )


def _normalize_text(text: str) -> str:
    return text.lower().replace("**", "").replace("`", "")


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)


def _assert_count(text: str) -> int:
    return _normalize_text(text).count("assert ")
