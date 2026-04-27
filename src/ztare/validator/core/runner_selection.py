from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re

from src.ztare.validator.core.mutation_contract import (
    MutationMismatchCode,
    MutationValidationRecord,
)


class CandidateScopeVerdict(str, Enum):
    IN_SCOPE = "IN_SCOPE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


@dataclass(frozen=True)
class CandidateSelectionRecord:
    scope_verdict: CandidateScopeVerdict
    candidate_admissible: bool
    minority_attack_preserved: bool
    keep_best_in_scope: bool
    selected_as_best: bool
    candidate_score: int
    best_score_before: int
    scope_signals: tuple[str, ...]
    attacker_headers_seen: tuple[str, ...]
    rationale: str


def evaluate_candidate_selection(
    *,
    candidate_score: int,
    best_score_before: int,
    mutation_validation: MutationValidationRecord | None,
    scope_verdict: CandidateScopeVerdict,
    scope_signals: tuple[str, ...] = (),
    dynamic: bool,
    debate_log_text: str,
) -> CandidateSelectionRecord:
    attacker_headers_seen = _extract_attacker_headers(debate_log_text)
    # GP-135 fix (2026-04-23): count TOTAL attacker sections, not unique names.
    # Under dynamic mode the committee can emit multiple attackers labeled
    # with a generic persona string ("## Attacker: Attacker"); deduplicating
    # by name then failed R3 even when two full attacker sections ran. The
    # check's intent is "dynamic minority attacker preserved in the log",
    # which is satisfied by section count, not name uniqueness.
    attacker_section_count = _count_attacker_sections(debate_log_text)
    minority_attack_preserved = (not dynamic) or attacker_section_count >= 2

    admissible = True
    reasons: list[str] = []

    if mutation_validation is not None and mutation_validation.mismatch_code != MutationMismatchCode.CLEAN:
        admissible = False
        reasons.append(
            f"R1 mismatch {mutation_validation.mismatch_code.value}: {mutation_validation.rationale}"
        )

    if scope_verdict == CandidateScopeVerdict.OUT_OF_SCOPE:
        admissible = False
        reasons.append("Candidate introduces off-scope mechanisms for the active project contract.")

    if not minority_attack_preserved:
        admissible = False
        reasons.append("Dynamic run did not preserve both attacker outputs in the debate log.")

    keep_best_in_scope = (not admissible) or candidate_score <= best_score_before
    selected_as_best = admissible and candidate_score > best_score_before

    if admissible and selected_as_best:
        reasons.append("Candidate is admissible, in-scope, and improves score.")
    elif admissible and keep_best_in_scope:
        reasons.append("Candidate is admissible but does not beat the current best score.")

    return CandidateSelectionRecord(
        scope_verdict=scope_verdict,
        candidate_admissible=admissible,
        minority_attack_preserved=minority_attack_preserved,
        keep_best_in_scope=keep_best_in_scope,
        selected_as_best=selected_as_best,
        candidate_score=candidate_score,
        best_score_before=best_score_before,
        scope_signals=scope_signals,
        attacker_headers_seen=attacker_headers_seen,
        rationale=" ".join(reasons).strip(),
    )


def _extract_attacker_headers(debate_log_text: str) -> tuple[str, ...]:
    headers = re.findall(r"^## Attacker:\s*(.+?)\s*$", debate_log_text, flags=re.MULTILINE)
    deduped: list[str] = []
    for header in headers:
        if header not in deduped:
            deduped.append(header)
    return tuple(deduped)


def _count_attacker_sections(debate_log_text: str) -> int:
    """Count TOTAL '## Attacker:' sections (no deduplication).

    Used by R3 to decide whether the dynamic minority attacker was
    preserved. Section count is the right proxy for "both attackers ran";
    name uniqueness is irrelevant when the committee emits generic
    persona labels.
    """
    return len(re.findall(r"^## Attacker:\s*.+$", debate_log_text, flags=re.MULTILINE))
