"""Projection receipts for mutator briefing renders.

The mutator prompt is an abstraction of concrete repository/workspace state.
This receipt checks whether higher-authority structured records survived that
projection into the rendered prompt, and whether lower-authority baseline
markers were also emitted.
"""
from __future__ import annotations

import hashlib
from typing import Any

SCHEMA = "ztare-mutator-briefing-projection-receipt-v1"

_AUTHORITY_SOURCE_TYPES = {
    "full_survivor": 100,
    "gate_pass": 96,
    "deterministic_receipt": 94,
    "compiled_proof_artifact": 92,
    "strategy_experiment": 88,
}

_DEMOTION_MARKERS = (
    "Mandatory Patch Base",
)


def build_projection_receipt(
    *,
    body: str,
    records: list[dict[str, Any]],
    iter_index: int | None = None,
) -> dict[str, Any]:
    """Return a compact abstraction-soundness receipt for one briefing body."""
    text = str(body or "")
    authority_records = [
        _authority_entry(rec)
        for rec in records
        if isinstance(rec, dict) and _authority_score(rec) > 0
    ]
    authority_records = [entry for entry in authority_records if entry is not None]
    preserved = []
    missing = []
    for entry in authority_records:
        if any(anchor and anchor in text for anchor in entry["anchors"]):
            preserved.append(_entry_public(entry))
        else:
            missing.append(_entry_public(entry))
    demotions = [marker for marker in _DEMOTION_MARKERS if marker in text]
    failures = []
    if missing:
        failures.append("authority_artifact_missing")
    if authority_records and demotions:
        failures.append("lower_authority_baseline_marker_present")
    return {
        "schema": SCHEMA,
        "iter_index": iter_index,
        "prompt_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "authority_records": len(authority_records),
        "preserved": preserved,
        "missing": missing,
        "demotion_markers": demotions,
        "status": "fail" if failures else "pass",
        "failures": failures,
    }


def _authority_score(rec: dict[str, Any]) -> int:
    return int(_AUTHORITY_SOURCE_TYPES.get(str(rec.get("source_type") or ""), 0))


def _authority_entry(rec: dict[str, Any]) -> dict[str, Any] | None:
    anchors = [
        str(rec.get("sha") or ""),
        str(rec.get("failure_family_sha") or ""),
        str(rec.get("source_ref") or rec.get("submission") or rec.get("path") or ""),
        str(rec.get("summary") or "")[:80],
    ]
    anchors = [a for a in anchors if a]
    if not anchors:
        return None
    return {
        "provider": str(rec.get("provider") or ""),
        "source_type": str(rec.get("source_type") or ""),
        "source_ref": str(rec.get("source_ref") or rec.get("submission") or rec.get("path") or ""),
        "sha": str(rec.get("sha") or ""),
        "failure_family_sha": str(rec.get("failure_family_sha") or ""),
        "authority_score": _authority_score(rec),
        "anchors": anchors,
    }


def _entry_public(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider": entry["provider"],
        "source_type": entry["source_type"],
        "source_ref": entry["source_ref"],
        "sha": entry["sha"],
        "authority_score": entry["authority_score"],
    }
