"""Deterministic gate for PDE execution-mode outputs.

The gate checks whether an RD agent produced the required artifacts before
ending with an open-gap verdict. It does not judge mathematical truth.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from ztare.research_director.pde_estimate_craft_ops import (
    BASE_WORK_UNIT_TEMPLATES,
)


TERMINAL_GAP_VERDICTS = {
    "MISSING_HYPOTHESIS",
    "OPEN",
    "NO_CLOSE",
    "THEOREM_OR_DOMAIN_GAP",
    "NEW_PDE_WORK_NEEDED",
}


CONSTRUCTIVE_TURN_SIGNAL_FIELDS = {
    "conditional_source_law",
    "conditional_theorem",
    "conditional_theorem_exists",
    "source_law",
    "source_contract",
}

CONSTRUCTIVE_TURN_CARRIER_FIELDS = {
    "target_carrier",
    "source_carrier",
    "bounded_or_selectable_variable",
    "bounded_share_variable",
    "bounded_variable",
    "selectable_variable",
}

CONSTRUCTIVE_TURN_BLOCKERS = {
    "immediate_packet_kill",
    "known_contradiction",
    "source_law_refuted",
    "no_selectable_carrier",
}


def _norm(value: Any) -> str:
    return str(value or "").strip().upper().replace("-", "_").replace(" ", "_")


def _work_unit_type(unit: dict[str, Any]) -> str:
    return str(unit.get("type") or unit.get("unit_type") or "").strip()


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in {"", "false", "0", "no", "none", "null"}
    return bool(value)


def _has_truthy(payload: dict[str, Any], fields: set[str]) -> bool:
    return any(_truthy(payload.get(field)) for field in fields)


def _flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(v) for v in value)
    return str(value or "")


def _work_units_imply_constructive_turn(payload: dict[str, Any]) -> bool:
    units = payload.get("work_units") or payload.get("pde_work_units") or []
    if not isinstance(units, list):
        return False
    text = _flatten_text(units).lower().replace("-", " ").replace("_", " ")
    source_signal = (
        "conditional source" in text
        or "conditional law" in text
        or "source fixed" in text
        or "source law" in text
    )
    carrier_signal = (
        "bounded share" in text
        or "bounded variable" in text
        or "selectable" in text
        or "selected event" in text
        or "target carrier" in text
    )
    constructor_signal = (
        "positive conditional constructor" in text
        or "positive constructor" in text
        or "producing a restricted" in text
        or "produces a restricted" in text
        or "directly inhabits" in text
    )
    return source_signal and carrier_signal and constructor_signal


def constructive_turn_due(payload: dict[str, Any]) -> bool:
    """Return whether a positive-constructor attempt is action-order due.

    This is an action-sequencing check, not a mathematical truth check. It
    fires when a source law and bounded/selectable carrier are both visible
    and no caller-declared blocker has already killed the construction lane.
    """
    explicit = payload.get("constructive_turn_due")
    if explicit is not None:
        return _truthy(explicit)
    signals = payload.get("constructive_turn_signals")
    if isinstance(signals, dict):
        merged = {**payload, **signals}
    else:
        merged = payload
    if _has_truthy(merged, CONSTRUCTIVE_TURN_BLOCKERS):
        return False
    explicit_context_due = (
        _has_truthy(merged, CONSTRUCTIVE_TURN_SIGNAL_FIELDS)
        and _has_truthy(merged, CONSTRUCTIVE_TURN_CARRIER_FIELDS)
    )
    return explicit_context_due or _work_units_imply_constructive_turn(payload)


def validate_pde_work_units(
    payload: dict[str, Any],
    *,
    estimate_derivation_min: int = 2,
    falsifier_packet_min: int = 1,
) -> dict[str, Any]:
    """Return a pass/fail report for PDE work-unit sufficiency."""
    verdict = _norm(
        payload.get("terminal_verdict")
        or payload.get("verdict")
        or payload.get("status")
    )
    units = payload.get("work_units") or payload.get("pde_work_units") or []
    if not isinstance(units, list):
        return {
            "passed": False,
            "verdict": verdict,
            "violations": [{
                "type": "work_units_not_list",
                "message": "work_units must be a list",
            }],
            "counts": {},
        }

    counts = Counter(_work_unit_type(unit) for unit in units if isinstance(unit, dict))
    violations: list[dict[str, Any]] = []
    for index, unit in enumerate(units):
        if not isinstance(unit, dict):
            violations.append({
                "type": "work_unit_not_object",
                "index": index,
            })
            continue
        unit_type = _work_unit_type(unit)
        template = BASE_WORK_UNIT_TEMPLATES.get(unit_type)
        if template is None:
            violations.append({
                "type": "unknown_work_unit_type",
                "index": index,
                "unit_type": unit_type,
            })
            continue
        missing = [
            field for field in template.required_fields
            if field not in unit or unit.get(field) in (None, "", [])
        ]
        if missing:
            violations.append({
                "type": "work_unit_missing_fields",
                "index": index,
                "unit_type": unit_type,
                "missing_fields": missing,
            })

    constructive_requires_attempt = constructive_turn_due(payload)
    if (
        constructive_requires_attempt
        and counts.get("positive_constructor_attempt", 0) == 0
    ):
        violations.append({
            "type": "missing_positive_constructor_attempt",
            "message": (
                "source law plus bounded/selectable carrier is visible; "
                "attempt a positive constructor before adding obstruction-only work"
            ),
            "requires_one_of": ["positive_constructor_attempt"],
        })

    terminal_requires_work = verdict in TERMINAL_GAP_VERDICTS
    if terminal_requires_work:
        if counts.get("estimate_derivation", 0) < estimate_derivation_min:
            violations.append({
                "type": "too_few_estimate_derivations",
                "required": estimate_derivation_min,
                "actual": counts.get("estimate_derivation", 0),
            })
        if counts.get("falsifier_packet", 0) < falsifier_packet_min:
            violations.append({
                "type": "too_few_falsifier_packets",
                "required": falsifier_packet_min,
                "actual": counts.get("falsifier_packet", 0),
            })
        if (
            counts.get("smaller_theorem", 0) == 0
            and counts.get("literature_match", 0) == 0
        ):
            violations.append({
                "type": "missing_shrink_or_literature_match",
                "requires_one_of": ["smaller_theorem", "literature_match"],
            })

    return {
        "passed": not violations,
        "verdict": verdict,
        "terminal_requires_work": terminal_requires_work,
        "constructive_turn_due": constructive_requires_attempt,
        "counts": dict(counts),
        "violations": violations,
    }



def _read_json(path: str) -> dict[str, Any]:
    import json
    import sys

    if path == "-":
        return json.loads(sys.stdin.read())
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Validate PDE execution-mode work units."
    )
    parser.add_argument("payload_json", help="Path to payload JSON, or - for stdin")
    parser.add_argument("--estimate-derivation-min", type=int, default=2)
    parser.add_argument("--falsifier-packet-min", type=int, default=1)
    args = parser.parse_args(argv)

    result = validate_pde_work_units(
        _read_json(args.payload_json),
        estimate_derivation_min=args.estimate_derivation_min,
        falsifier_packet_min=args.falsifier_packet_min,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
