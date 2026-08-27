"""Verified current zero-weight paper-watch identities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ztare.common.equivariance import stable_sha256


PAPER_WATCH_SCHEMAS = {
    "jaggedthoughts-public-equity-paper-decision-v1": "public_equity",
    "jaggedthoughts-public-fund-paper-decision-v1": "public_fund",
}
_PAPER_WATCH_CACHE: dict[
    tuple[str, bool], tuple[tuple[tuple[str, int, int], ...], tuple[dict[str, Any], ...]]
] = {}


def verify_paper_watch_decision(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Verify one active, cash-only watch without widening its authority."""
    row = dict(raw)
    kind = PAPER_WATCH_SCHEMAS.get(str(row.get("schema") or ""))
    claimed = str(row.pop("decision_sha256", ""))
    row.pop("transition", None)
    if not kind or not claimed or stable_sha256(row) != claimed:
        raise ValueError("paper-watch decision identity is invalid")
    entity = dict(row.get("entity") or {})
    lifecycle = dict(row.get("lifecycle") or {})
    policy = dict(row.get("paper_policy") or {})
    evidence = dict(row.get("evidence") or {})
    if (
        entity.get("entity_kind") != kind
        or lifecycle.get("data_class") != "operator"
        or lifecycle.get("stage") != "active"
        or float(policy.get("target_weight", -1)) != 0.0
        or policy.get("cash_default") is not True
        or policy.get("allocation_allowed") is not False
        or policy.get("order_routing_allowed") is not False
        or row.get("capital_authority") is not False
        or row.get("brokerage_authority") is not False
        or not str(evidence.get("candidate_leaf") or "")
        or not str(evidence.get("candidate_sha256") or "")
    ):
        raise ValueError("paper-watch decision is not an active zero-weight watch")
    return {**row, "decision_sha256": claimed}


def paper_watch_decisions(
    root: Path, *, current_candidate_only: bool = True,
) -> tuple[dict[str, Any], ...]:
    """Select the latest verified operator watch per current candidate and entity."""
    root = root.expanduser().resolve()
    discovery_path = root / "discovery" / "latest.json"
    paths = tuple(sorted((root / "paper_decisions").glob("*/*.json")))
    tracked_paths = (*paths, *((discovery_path,) if current_candidate_only else ()))
    signature = tuple(
        (str(path), stat.st_mtime_ns, stat.st_size)
        for path in tracked_paths if path.is_file() and (stat := path.stat())
    )
    cache_key = (str(root), current_candidate_only)
    cached = _PAPER_WATCH_CACHE.get(cache_key)
    if cached and cached[0] == signature:
        return tuple(dict(row) for row in cached[1])
    current_by_entity: dict[str, str] = {}
    if current_candidate_only and discovery_path.is_file():
        try:
            discovery = json.loads(discovery_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            discovery = {}
        current_by_entity = {
            str(row.get("entity_id") or "").upper(): str(row.get("candidate_sha256") or "")
            for row in discovery.get("candidates") or ()
            if (
                isinstance(row, Mapping) and row.get("entity_id")
                and row.get("candidate_sha256") and row.get("screen_status") == "qualified"
            )
        }
    latest: dict[str, dict[str, Any]] = {}
    for path in paths:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(raw, Mapping) or raw.get("schema") not in PAPER_WATCH_SCHEMAS:
            continue
        row = verify_paper_watch_decision(raw)
        entity_id = str((row.get("entity") or {}).get("entity_id") or "").upper()
        if not entity_id:
            raise ValueError("paper-watch decision requires entity_id")
        current_sha = current_by_entity.get(entity_id)
        if current_by_entity and (
            not current_sha
            or str((row.get("evidence") or {}).get("candidate_sha256") or "") != current_sha
        ):
            continue
        candidate = {**row, "decision_path": path.relative_to(root).as_posix()}
        current = latest.get(entity_id)
        if current is None or (
            str(candidate.get("activated_at") or ""), str(candidate["decision_id"])
        ) > (str(current.get("activated_at") or ""), str(current["decision_id"])):
            latest[entity_id] = candidate
    result = tuple(latest[key] for key in sorted(latest))
    _PAPER_WATCH_CACHE[cache_key] = (signature, result)
    return tuple(dict(row) for row in result)


def paper_watch_decision(root: Path, decision_id: str) -> tuple[Path, dict[str, Any]]:
    """Resolve one exact paper-watch decision by its immutable identity."""
    matches = []
    for path in sorted((root / "paper_decisions").glob("*/*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(raw, Mapping) and raw.get("decision_id") == decision_id:
            matches.append((path, verify_paper_watch_decision(raw)))
    if len(matches) != 1:
        raise KeyError(f"paper-watch decision absent or ambiguous: {decision_id}")
    return matches[0]


__all__ = [
    "PAPER_WATCH_SCHEMAS", "paper_watch_decision", "paper_watch_decisions",
    "verify_paper_watch_decision",
]
