"""Source-static row to repair-family routing contract.

This contract sits between source mining and expensive C-supply conversion.
It does not grant C credit; it only decides whether a lexical/static family
match is strong enough to spend template/probe budget downstream.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DEFAULT_ALLOWED_STATUSES = ("candidate_family", "active", "validated")


@dataclass(frozen=True)
class SourceFamilyMatchPolicy:
    min_hit_count: int = 2
    min_confidence: float = 0.75
    allowed_statuses: tuple[str, ...] = DEFAULT_ALLOWED_STATUSES
    require_negative_controls: bool = True

    def as_receipt(self) -> dict[str, Any]:
        return {
            "schema": "leanmill-source-family-match-policy-v1",
            "min_hit_count": self.min_hit_count,
            "min_confidence": self.min_confidence,
            "allowed_statuses": list(self.allowed_statuses),
            "require_negative_controls": self.require_negative_controls,
            "ordering_rule": "Eligible matches are sorted by confidence DESC, hit_count DESC, family ASC.",
            "credit_boundary": "Source-family matching routes C-supply spend only; it never grants proof, governance, benchmark, or C credit.",
        }


def _as_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lower = value.strip().lower()
        if lower in {"1", "true", "yes", "on"}:
            return True
        if lower in {"0", "false", "no", "off"}:
            return False
    return default


def _as_statuses(value: Any, default: tuple[str, ...] = DEFAULT_ALLOWED_STATUSES) -> tuple[str, ...]:
    raw: list[Any]
    if isinstance(value, str):
        raw = [part.strip() for part in value.split(",")]
    elif isinstance(value, list):
        raw = value
    elif isinstance(value, tuple):
        raw = list(value)
    else:
        raw = list(default)
    statuses = tuple(str(item).strip() for item in raw if str(item).strip())
    return statuses or default


def _profile_section(policy: dict[str, Any], profile: str) -> dict[str, Any]:
    profiles = policy.get("profiles") if isinstance(policy.get("profiles"), dict) else {}
    section = profiles.get(profile) if profile and isinstance(profiles.get(profile), dict) else {}
    growth = section.get("c_supply_growth_controller") if isinstance(section.get("c_supply_growth_controller"), dict) else {}
    return growth


def policy_from_mapping(mapping: dict[str, Any] | None = None, *, fallback_min_hit_count: int = 2) -> SourceFamilyMatchPolicy:
    mapping = mapping if isinstance(mapping, dict) else {}
    min_hit = mapping.get("source_template_min_hit_count", mapping.get("min_hit_count", fallback_min_hit_count))
    min_conf = mapping.get("source_template_min_confidence", mapping.get("min_confidence", 0.75))
    try:
        min_hit_count = max(1, int(min_hit))
    except (TypeError, ValueError):
        min_hit_count = max(1, int(fallback_min_hit_count))
    try:
        min_confidence = max(0.0, min(1.0, float(min_conf)))
    except (TypeError, ValueError):
        min_confidence = 0.75
    return SourceFamilyMatchPolicy(
        min_hit_count=min_hit_count,
        min_confidence=min_confidence,
        allowed_statuses=_as_statuses(
            mapping.get("source_template_allowed_statuses", mapping.get("allowed_statuses")),
        ),
        require_negative_controls=_as_bool(
            mapping.get("source_template_require_negative_controls", mapping.get("require_negative_controls")),
            True,
        ),
    )


def policy_from_factory_policy(policy: dict[str, Any] | None, *, profile: str = "", fallback_min_hit_count: int = 2) -> SourceFamilyMatchPolicy:
    policy = policy if isinstance(policy, dict) else {}
    operations = policy.get("operations") if isinstance(policy.get("operations"), dict) else {}
    base = operations.get("source_static_family_match_policy") if isinstance(operations.get("source_static_family_match_policy"), dict) else {}
    merged = dict(base)
    merged.update(_profile_section(policy, profile))
    return policy_from_mapping(merged, fallback_min_hit_count=fallback_min_hit_count)


def eligibility(match: dict[str, Any], policy: SourceFamilyMatchPolicy) -> dict[str, Any]:
    family = str(match.get("family") or "")
    status = str(match.get("status") or "")
    try:
        hit_count = int(match.get("hit_count") or 0)
    except (TypeError, ValueError):
        hit_count = 0
    try:
        confidence = float(match.get("confidence") or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    failures: list[str] = []
    if not family:
        failures.append("missing_family")
    if policy.require_negative_controls and not bool(match.get("has_negative_controls")):
        failures.append("missing_negative_controls")
    if hit_count < policy.min_hit_count:
        failures.append("hit_count_below_policy")
    if confidence < policy.min_confidence:
        failures.append("confidence_below_policy")
    if status not in set(policy.allowed_statuses):
        failures.append("family_status_not_conversion_eligible")
    return {
        "eligible": not failures,
        "failures": failures,
        "family": family,
        "status": status,
        "hit_count": hit_count,
        "confidence": confidence,
        "policy": policy.as_receipt(),
    }


def eligible_matches(matches: Any, policy: SourceFamilyMatchPolicy) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for match in matches or []:
        if not isinstance(match, dict):
            continue
        receipt = eligibility(match, policy)
        if not receipt["eligible"]:
            continue
        out.append(dict(match))
    out.sort(key=lambda item: (-float(item.get("confidence") or 0.0), -int(item.get("hit_count") or 0), str(item.get("family") or "")))
    return out


def best_match(matches: Any, policy: SourceFamilyMatchPolicy) -> dict[str, Any] | None:
    filtered = eligible_matches(matches, policy)
    return filtered[0] if filtered else None


def rejection_summary(matches: Any, policy: SourceFamilyMatchPolicy) -> dict[str, Any]:
    counts: dict[str, int] = {}
    total = 0
    for match in matches or []:
        if not isinstance(match, dict):
            continue
        total += 1
        receipt = eligibility(match, policy)
        if receipt["eligible"]:
            counts["eligible"] = counts.get("eligible", 0) + 1
        for failure in receipt["failures"]:
            counts[failure] = counts.get(failure, 0) + 1
    return {
        "schema": "leanmill-source-family-match-rejection-summary-v1",
        "total": total,
        "counts": dict(sorted(counts.items())),
        "policy": policy.as_receipt(),
    }


def _self_test() -> None:
    policy = SourceFamilyMatchPolicy(min_hit_count=2, min_confidence=0.75, allowed_statuses=("candidate_family",))
    matches = [
        {"family": "seed", "status": "seed_only", "hit_count": 5, "confidence": 0.95, "has_negative_controls": True},
        {"family": "weak", "status": "candidate_family", "hit_count": 1, "confidence": 0.9, "has_negative_controls": True},
        {"family": "ok", "status": "candidate_family", "hit_count": 2, "confidence": 0.8, "has_negative_controls": True},
    ]
    assert (best_match(matches, policy) or {}).get("family") == "ok"
    summary = rejection_summary(matches, policy)
    assert summary["counts"]["family_status_not_conversion_eligible"] == 1
    assert summary["counts"]["hit_count_below_policy"] == 1


if __name__ == "__main__":
    _self_test()
    print("source_family_match self-test PASS")
