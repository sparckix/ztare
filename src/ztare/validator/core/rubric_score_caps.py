from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _clean_tokens(value: Any) -> list[str]:
    return [
        str(item).strip().lower()
        for item in _as_list(value)
        if str(item).strip()
    ]


def _contains_any(haystack: str, needles: Iterable[str]) -> bool:
    lowered = haystack.lower()
    return any(needle in lowered for needle in needles)


def _gap_matches_rule(gap: Mapping[str, Any], rule: Mapping[str, Any], context: str) -> bool:
    severities = set(_clean_tokens(rule.get("severity_any") or rule.get("severities_any")))
    if severities and str(gap.get("severity", "")).strip().lower() not in severities:
        return False

    gap_types = set(_clean_tokens(rule.get("gap_type_any") or rule.get("gap_types_any")))
    if gap_types and str(gap.get("gap_type", "")).strip().lower() not in gap_types:
        return False

    target = str(gap.get("target", "") or "")
    description = str(gap.get("description", "") or "")
    target_tokens = _clean_tokens(rule.get("target_contains_any") or rule.get("targets_any"))
    if target_tokens and not _contains_any(target, target_tokens):
        return False

    description_tokens = _clean_tokens(
        rule.get("description_contains_any") or rule.get("descriptions_any")
    )
    if description_tokens and not _contains_any(description, description_tokens):
        return False

    text_tokens = _clean_tokens(rule.get("text_contains_any") or rule.get("keywords_any"))
    if text_tokens and not _contains_any("\n".join([target, description, context]), text_tokens):
        return False

    return True


def apply_evidence_gap_score_caps(
    evaluation: dict[str, Any],
    rubric_data: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply rubric-declared score caps driven by judge evidence gaps.

    This is intentionally opt-in. It lets a rubric say that an otherwise useful
    high-quality thesis must remain below a proof-grade score when the judge's
    own structured gaps say the proof object is still missing.
    """

    rules = rubric_data.get("evidence_gap_score_caps")
    if not isinstance(rules, list) or not rules:
        return evaluation

    gaps = evaluation.get("evidence_gaps")
    if not isinstance(gaps, list):
        gaps = []

    context = "\n".join(
        str(evaluation.get(field, "") or "")
        for field in ("weakest_point", "debate_summary", "adversarial_alignment")
    )
    current_score = int(evaluation.get("score") or 0)
    original_score = current_score
    score_contract = evaluation.get("score_contract")
    if not isinstance(score_contract, dict):
        score_contract = {}

    soft_caps = score_contract.get("soft_score_caps")
    if not isinstance(soft_caps, list):
        soft_caps = []

    applied: list[dict[str, Any]] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        try:
            cap = int(rule["cap"])
        except (KeyError, TypeError, ValueError):
            continue
        if current_score <= cap:
            continue
        when_score_at_least = rule.get("when_score_at_least")
        if when_score_at_least is not None:
            try:
                if original_score < int(when_score_at_least):
                    continue
            except (TypeError, ValueError):
                continue

        matched_gap = None
        for gap in gaps:
            if isinstance(gap, dict) and _gap_matches_rule(gap, rule, context):
                matched_gap = gap
                break
        if matched_gap is None and rule.get("match_without_gap_context"):
            text_tokens = _clean_tokens(rule.get("text_contains_any") or rule.get("keywords_any"))
            if text_tokens and _contains_any(context, text_tokens):
                matched_gap = {"target": "context", "severity": "unknown"}
        if matched_gap is None:
            continue

        reason = str(rule.get("reason") or "rubric evidence-gap score cap").strip()
        name = str(rule.get("name") or "evidence_gap_score_cap").strip()
        current_score = min(current_score, cap)
        applied_entry = {
            "name": name,
            "cap": cap,
            "reason": reason,
            "matched_gap_target": str(matched_gap.get("target", "") or ""),
            "matched_gap_severity": str(matched_gap.get("severity", "") or ""),
            "source": "rubric.evidence_gap_score_caps",
        }
        applied.append(applied_entry)
        soft_caps.append(applied_entry)

    if not applied:
        return evaluation

    evaluation["score"] = max(0, min(100, current_score))
    score_contract["soft_score_caps"] = soft_caps
    active_cap = min(applied, key=lambda item: int(item["cap"]))
    score_contract["cap_reason"] = "soft_cap"
    score_contract["cap_reason_detail"] = str(active_cap["reason"])
    score_contract["rubric_evidence_gap_score_caps_applied"] = applied
    evaluation["score_contract"] = score_contract

    previous_cap = evaluation.get("score_cap_applied")
    original_judge_score = original_score
    if isinstance(previous_cap, dict) and previous_cap.get("original_judge_score") is not None:
        try:
            original_judge_score = int(previous_cap["original_judge_score"])
        except (TypeError, ValueError):
            original_judge_score = original_score
    evaluation["score_cap_applied"] = {
        "original_judge_score": original_judge_score,
        "capped_score": evaluation["score"],
        "reason": str(active_cap["reason"]),
        "source": "rubric.evidence_gap_score_caps",
        "applied_caps": applied,
    }
    return evaluation
