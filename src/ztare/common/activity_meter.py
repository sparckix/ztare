from __future__ import annotations

from collections import Counter
from typing import Any


ACTIVITY_CLASSES = ("preflight_repair", "probe_query", "mining", "candidate_authoring", "scoring")

_ACTION_CLASS_MAP = {
    "check_receipt_compatibility": "preflight_repair",
    "check_worldmodel_carrier_contract": "preflight_repair",
    "check-receipt": "preflight_repair",
    "run_visible_json_probe": "probe_query",
    "probe-json": "probe_query",
    "score_worldmodel_candidate_delta": "scoring",
    "score-worldmodel-candidate": "scoring",
    "run_action": "candidate_authoring",
    "route_action": "candidate_authoring",
    "rank_next_morphisms": "mining",
    "mine_worldmodel_separating_features": "mining",
    "mine_worldmodel_lowerable_selectors": "mining",
    "mine_worldmodel_global_carrier_selectors_from_observable_context": "mining",
    "cell_local_lowerable_carrier_selector_miner": "mining",
}


def classify_activity(action_name: str, payload: dict[str, Any] | None = None) -> str:
    name = str(action_name or "").strip()
    if name in _ACTION_CLASS_MAP:
        return _ACTION_CLASS_MAP[name]
    if name in {"LEAF_WORKBENCH_ACTION_REQUEST", "LEAF_WORKBENCH_RECEIPT"}:
        return "candidate_authoring"
    payload = payload or {}
    if isinstance(payload.get("proposed_change"), (str, dict)):
        return "candidate_authoring"
    if str(payload.get("kind") or "").strip().endswith("probe"):
        return "probe_query"
    return "mining"


def summarize_activity_spend(actions: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter({name: 0 for name in ACTIVITY_CLASSES})
    rows: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        activity = classify_activity(str(action.get("action") or action.get("capability_id") or action.get("command") or ""), action)
        counts[activity] += 1
        rows.append({
            "action": str(action.get("action") or action.get("capability_id") or action.get("command") or ""),
            "activity_class": activity,
        })
    return {"activity_classes": dict(counts), "action_rows": rows}
