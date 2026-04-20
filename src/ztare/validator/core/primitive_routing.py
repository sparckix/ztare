from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Iterable


class ExploitFamilyTag(str, Enum):
    SELF_REFERENCE_FUTURE_PREDICTION = "SELF_REFERENCE_FUTURE_PREDICTION"
    LOCAL_SAFE_HARBOR = "LOCAL_SAFE_HARBOR"
    WHOLE_SYSTEM_OVERCLAIM = "WHOLE_SYSTEM_OVERCLAIM"
    UNKNOWN = "UNKNOWN"


class PrimitiveRoutingPolicy(str, Enum):
    SELF_REFERENCE_PRESSURE = "SELF_REFERENCE_PRESSURE"
    SAFE_HARBOR_LOCAL = "SAFE_HARBOR_LOCAL"
    OVERCLAIM_SCOPE_DISCIPLINE = "OVERCLAIM_SCOPE_DISCIPLINE"
    MANUAL_REVIEW = "MANUAL_REVIEW"


POLICY_TO_PRIMITIVE_KEYS: dict[PrimitiveRoutingPolicy, tuple[str, ...]] = {
    PrimitiveRoutingPolicy.SELF_REFERENCE_PRESSURE: (
        "self_referential_falsification",
        "cooked_books",
        "float_masking",
        "perfect_mirroring_simulation",
        "unidirectional_decay",
    ),
    PrimitiveRoutingPolicy.SAFE_HARBOR_LOCAL: (
        "missing_falsification_suite",
    ),
    PrimitiveRoutingPolicy.OVERCLAIM_SCOPE_DISCIPLINE: (
        "domain_leakage",
        "dimensional_error",
    ),
    PrimitiveRoutingPolicy.MANUAL_REVIEW: (),
}


@dataclass(frozen=True)
class PrimitiveRoutingDecision:
    family_tag: ExploitFamilyTag
    policy: PrimitiveRoutingPolicy
    primitive_keys: tuple[str, ...]
    punitive_primitives_allowed: bool
    requires_manual_review: bool
    rationale: str


def _contains_any(text: str, patterns: Iterable[str]) -> bool:
    return any(pattern in text for pattern in patterns)


def _has_bounded_component_disclaimer(text: str) -> bool:
    return _contains_any(
        text,
        [
            "local component",
            "bounded local",
            "scope-limited",
            "scope limited",
            "local deterministic mapping",
            "does not claim to solve upstream",
            "does not verify upstream",
            "does not guarantee upstream",
            "opaque inputs",
            "opaque risk label",
            "received status tokens",
        ],
    )


def _has_upstream_truth_disclaimer(text: str) -> bool:
    return _contains_any(
        text,
        [
            "does not claim to solve whether the upstream evaluator is honest",
            "does not claim that the upstream label is truthful or complete",
            "does not claim that upstream labels are truthful or complete",
            "does not claim to prove that upstream labels are correct or sufficient",
            "does not verify the truthfulness",
            "does not verify upstream truthfulness",
            "does not claim upstream truthfulness",
            "opaque inputs",
            "opaque upstream",
            "not trusted truths",
            "disclaims responsibility for upstream",
            "does not solve upstream semantic correctness",
            "received status tokens",
        ],
    )


def _has_negated_whole_system_disclaimer(text: str) -> bool:
    patterns = [
        r"does\s+not\s+claim.*whole-system",
        r"does\s+not\s+claim.*whole system",
        r"does\s+not\s+claim.*end-to-end",
        r"does\s+not\s+claim.*end to end",
        r"not\s+claim.*whole-system",
        r"not\s+claim.*whole system",
        r"does\s+not\s+claim.*whole-system validity",
        r"does\s+not\s+claim.*whole system validity",
        r"does\s+not\s+claim.*whole-system safety",
        r"does\s+not\s+claim.*whole system safety",
        r"does\s+not\s+claim.*completeness",
        r"does\s+not\s+claim.*exploit detection",
        r"does\s+not\s+guarantee.*whole-system",
        r"does\s+not\s+guarantee.*whole system",
        r"does\s+not\s+claim\s+that.*whole-system",
        r"does\s+not\s+claim\s+that.*whole system",
        r"does\s+not\s+claim\s+to\s+guarantee.*whole-system",
        r"does\s+not\s+claim\s+to\s+guarantee.*whole system",
        r"does\s+not\s+claim\s+to\s+guarantee.*end-to-end",
        r"does\s+not\s+claim\s+to\s+guarantee.*end to end",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def _has_affirmative_whole_system_claim(text: str) -> bool:
    future_claim = _contains_any(
        text,
        [
            "future prediction",
            "future distress",
            "solvency",
            "collapse",
            "distress",
            "by q1 2026",
            "by the end of q4",
        ],
    )
    explicit_guarantee = _contains_any(
        text,
        [
            "ensures",
            "prevents",
            "cannot quietly pass",
            "every potential failure",
            "system-level protection",
            "whole-system protection",
            "end-to-end protection",
        ],
    )
    plain_scope_terms = _contains_any(
        text,
        [
            "whole-system",
            "whole system",
            "end-to-end",
            "end to end",
            "global security",
            "system-level",
            "system level",
            "overall ai safety",
        ],
    ) and not _has_negated_whole_system_disclaimer(text)
    return future_claim or explicit_guarantee or plain_scope_terms


def _has_straw_man_mismatch(text: str) -> bool:
    direct = _contains_any(
        text,
        [
            "straw man",
            "straw-man",
            "tautological verification",
            "self-authored threshold",
            "self authored threshold",
            "tests downstream arithmetic",
            "not an external kill test",
            "trivially passable",
            "weakened version of the claim",
            "claim-test mismatch",
            "claim test mismatch",
        ],
    )
    comparative_design_rubric = _contains_any(
        text,
        [
            "simulation requirement",
            "compare at least two design alternatives",
            "design alternatives",
            "morning café club",
            "seasonal table",
            "critic's cut",
            "55+ demographic",
            "host-ambassador",
            "hyperlocal host-ambassador operational blueprint",
        ],
    )
    falsification_threshold_pack = (
        _contains_any(text, ["falsification condition", "load-bearing variables", "arithmetic transparency", "symbolic mapping"])
        and _contains_any(text, ["gross profit", "breakeven point", "operational cost per active host"])
    )
    return direct or (comparative_design_rubric and falsification_threshold_pack)


def _has_decisive_self_authored_future_variable(text: str) -> bool:
    future_state = _contains_any(
        text,
        [
            "future prediction",
            "future distress",
            "solvency",
            "collapse",
            "distress",
            "by q1 2026",
            "by the end of q4",
            "future-state",
            "future state",
        ],
    )
    self_authored_decisive = _contains_any(
        text,
        [
            "thesis-authored",
            "thesis authored",
            "self-authored threshold",
            "self authored threshold",
            "future threshold",
            "predicted future price",
            "internal price floor",
            "distress threshold",
            "load-bearing variable",
            "asserted variable origin",
        ],
    )
    return future_state and self_authored_decisive


def _stage2_safe_harbor_guard(text: str) -> bool:
    return (
        _has_bounded_component_disclaimer(text)
        and _has_upstream_truth_disclaimer(text)
        and not _has_affirmative_whole_system_claim(text)
    )


def derive_exploit_family_tag(
    thesis_text: str,
    evidence_text: str = "",
    critiques_text: str = "",
) -> tuple[ExploitFamilyTag, str]:
    haystack = (
        "\n".join([thesis_text, evidence_text, critiques_text])
        .lower()
        .replace("*", "")
        .replace("`", "")
    )

    local_scope = _has_bounded_component_disclaimer(haystack)
    whole_system = _has_affirmative_whole_system_claim(haystack)
    self_reference = _contains_any(
        haystack,
        [
            "thesis-authored",
            "thesis authored",
            "self-referential",
            "self referential",
            "predicted future price",
            "future threshold",
            "future-state",
            "future state",
        ],
    )
    if _has_straw_man_mismatch(haystack):
        return (
            ExploitFamilyTag.UNKNOWN,
            "Claim-test mismatch / Straw Man behavior detected; current stage-3 taxonomy routes this to manual review.",
        )
    if _has_decisive_self_authored_future_variable(haystack):
        return (
            ExploitFamilyTag.SELF_REFERENCE_FUTURE_PREDICTION,
            "Thesis-authored decisive future variable/threshold takes priority over overclaim language.",
        )
    if _stage2_safe_harbor_guard(haystack):
        return (
            ExploitFamilyTag.LOCAL_SAFE_HARBOR,
            "Stage-2-style safe-harbor guard passed: bounded local mapping, upstream-truth disclaimer, no whole-system guarantee.",
        )

    if local_scope and whole_system:
        return (
            ExploitFamilyTag.WHOLE_SYSTEM_OVERCLAIM,
            "Local-scope language coexists with whole-system or end-to-end claims.",
        )
    if self_reference or whole_system:
        return (
            ExploitFamilyTag.SELF_REFERENCE_FUTURE_PREDICTION,
            "Whole-system predictive or self-referential language dominates the claim.",
        )
    if local_scope:
        return (
            ExploitFamilyTag.LOCAL_SAFE_HARBOR,
            "Claim is explicitly scoped to a bounded local component without whole-system guarantees.",
        )
    return (
        ExploitFamilyTag.UNKNOWN,
        "No stable family tag could be derived from the available text; fail closed to manual review.",
    )


def route_primitives_for_v4(
    thesis_text: str,
    evidence_text: str = "",
    critiques_text: str = "",
) -> PrimitiveRoutingDecision:
    family_tag, rationale = derive_exploit_family_tag(
        thesis_text=thesis_text,
        evidence_text=evidence_text,
        critiques_text=critiques_text,
    )

    if family_tag == ExploitFamilyTag.SELF_REFERENCE_FUTURE_PREDICTION:
        policy = PrimitiveRoutingPolicy.SELF_REFERENCE_PRESSURE
        punitive = True
        manual_review = False
    elif family_tag == ExploitFamilyTag.LOCAL_SAFE_HARBOR:
        policy = PrimitiveRoutingPolicy.SAFE_HARBOR_LOCAL
        punitive = False
        manual_review = False
    elif family_tag == ExploitFamilyTag.WHOLE_SYSTEM_OVERCLAIM:
        policy = PrimitiveRoutingPolicy.OVERCLAIM_SCOPE_DISCIPLINE
        punitive = True
        manual_review = False
    else:
        policy = PrimitiveRoutingPolicy.MANUAL_REVIEW
        punitive = False
        manual_review = True

    return PrimitiveRoutingDecision(
        family_tag=family_tag,
        policy=policy,
        primitive_keys=POLICY_TO_PRIMITIVE_KEYS[policy],
        punitive_primitives_allowed=punitive,
        requires_manual_review=manual_review,
        rationale=rationale,
    )
