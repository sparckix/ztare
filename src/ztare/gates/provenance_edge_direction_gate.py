"""G-PROVENANCE-EDGE-DIRECTION.

General gate for checking that a receipt's source-to-target edge is oriented:
constructive source fields cannot include the object being constructed, derived
conclusions cannot be assumed as sources, and same-witness bounds must bind a
declared witness field to its declared bound field.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-PROVENANCE-EDGE-DIRECTION"

REQUIRED_FIELDS = (
    "edge_id",
    "direction",
    "source_fields",
    "constructed_fields",
    "derived_conclusions",
    "forbidden_assumed_fields",
    "nearest_confuser",
    "confuser_distinction",
)

VALID_DIRECTIONS = {"construct", "reduce", "audit"}
PROVED_STATUSES = {"proved", "verified", "compiled", "daemon_stamped"}


def _present(value: Any) -> bool:
    if isinstance(value, str):
        text = value.strip()
        lowered = text.lower()
        if not text:
            return False
        false_exact_matches = {
            "missing",
            "absent",
            "unknown",
            "todo",
            "owed",
            "unpaid",
            "not supplied",
            "not provided",
            "none",
            "null",
            "false",
            "0",
        }
        return lowered not in false_exact_matches
    return value not in (None, "", [], {}, False)


def _names(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    names: set[str] = set()
    for value in values:
        if isinstance(value, dict):
            name = value.get("name")
        else:
            name = value
        if isinstance(name, str) and name.strip():
            names.add(name.strip())
    return names


def _unproved_source_fields(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    unproved: list[str] = []
    for value in values:
        if not isinstance(value, dict):
            unproved.append(str(value))
            continue
        name = str(value.get("name") or "<unnamed>")
        status = str(value.get("status") or "").strip().lower()
        artifact = value.get("artifact")
        if status not in PROVED_STATUSES or not _present(artifact):
            unproved.append(name)
    return unproved


def _bad_same_witness_bindings(values: Any) -> list[dict[str, Any]]:
    if values is None:
        return []
    if not isinstance(values, list):
        return [{"reason": "same_witness_bindings must be a list"}]
    bad: list[dict[str, Any]] = []
    for value in values:
        if not isinstance(value, dict):
            bad.append({"binding": value, "reason": "binding must be an object"})
            continue
        witness = value.get("witness_field")
        bound = value.get("bound_field")
        if not _present(witness) or not _present(bound):
            bad.append({
                "binding": value,
                "reason": "witness_field and bound_field are required",
            })
    return bad


def run_provenance_edge_direction_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate source-to-target direction for a receipt edge."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "provenance_edge_direction_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "hard_violations_present": ["malformed_receipt"],
            "summary": "malformed provenance edge-direction receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "provenance_edge_direction_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": "edge direction receipts need source, constructed, derived, and confuser fields",
        })

    direction = str(receipt.get("direction") or "").strip().lower()
    if direction and direction not in VALID_DIRECTIONS:
        violations.append({
            "type": "provenance_edge_direction_invalid_direction",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": [direction],
            "reason": f"direction must be one of {sorted(VALID_DIRECTIONS)}",
        })

    source_names = _names(receipt.get("source_fields"))
    constructed = _names(receipt.get("constructed_fields"))
    derived = _names(receipt.get("derived_conclusions"))
    forbidden = _names(receipt.get("forbidden_assumed_fields"))

    constructed_as_source = sorted(source_names & constructed)
    derived_as_source = sorted(source_names & derived)
    forbidden_as_source = sorted(source_names & forbidden)
    unproved_sources = _unproved_source_fields(receipt.get("source_fields"))
    bad_same_witness = _bad_same_witness_bindings(
        receipt.get("same_witness_bindings")
    )
    endpoint_restatement = (
        bool(receipt.get("endpoint_restatement_forbidden")) and
        _present(receipt.get("endpoint_restatement_used"))
    )

    hard_present: list[str] = []
    if constructed_as_source:
        hard_present.append("constructed_field_listed_as_source")
        violations.append({
            "type": "constructed_field_listed_as_source",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": constructed_as_source,
            "reason": "a construct edge cannot assume the field it constructs",
        })
    if derived_as_source:
        hard_present.append("derived_conclusion_listed_as_source")
        violations.append({
            "type": "derived_conclusion_listed_as_source",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": derived_as_source,
            "reason": "a derived conclusion cannot be listed as a source",
        })
    if forbidden_as_source:
        hard_present.append("forbidden_assumed_field_used")
        violations.append({
            "type": "forbidden_assumed_field_used",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": forbidden_as_source,
            "reason": "the receipt used a field it declared forbidden to assume",
        })
    if unproved_sources:
        hard_present.append("unproved_source_field")
        violations.append({
            "type": "unproved_source_field",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": unproved_sources,
            "reason": "source fields need proved status and an artifact",
        })
    if bad_same_witness:
        hard_present.append("same_witness_binding_malformed")
        violations.append({
            "type": "same_witness_binding_malformed",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": bad_same_witness,
            "reason": "same-witness bindings need witness_field and bound_field",
        })
    if endpoint_restatement:
        hard_present.append("endpoint_restatement_used")
        violations.append({
            "type": "endpoint_restatement_used",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": [receipt.get("endpoint_restatement_used")],
            "reason": "endpoint restatement is forbidden on this edge",
        })

    blocking = [v for v in violations if v.get("severity") == "blocking"]
    complete = not missing and not hard_present
    return {
        "gate_id": GATE_ID,
        "passed": not blocking if enforce_block else True,
        "complete": complete,
        "blocking_active": enforce_block,
        "violations": violations,
        "missing_fields": missing,
        "required_fields": list(REQUIRED_FIELDS),
        "hard_violations_present": hard_present,
        "summary": (
            "complete provenance edge-direction receipt"
            if complete else
            "incomplete provenance edge-direction receipt; "
            f"missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    good = run_provenance_edge_direction_gate({
        "edge_id": "edge",
        "direction": "construct",
        "source_fields": [{
            "name": "selector",
            "status": "proved",
            "artifact": "repo/file.lean",
        }],
        "constructed_fields": ["explicit_witness"],
        "derived_conclusions": ["selector_bound_source"],
        "forbidden_assumed_fields": ["explicit_witness"],
        "same_witness_bindings": [{
            "witness_field": "selector",
            "bound_field": "selector_bound",
        }],
        "endpoint_restatement_forbidden": True,
        "nearest_confuser": "subtype witness assumed",
        "confuser_distinction": "selector is source, subtype is constructed",
    }, enforce_block=True)
    assert good["passed"] is True
    assert good["complete"] is True

    bad = run_provenance_edge_direction_gate({
        "edge_id": "edge",
        "direction": "construct",
        "source_fields": [{
            "name": "explicit_witness",
            "status": "proved",
            "artifact": "repo/file.lean",
        }],
        "constructed_fields": ["explicit_witness"],
        "derived_conclusions": [],
        "forbidden_assumed_fields": ["explicit_witness"],
        "nearest_confuser": "self source",
        "confuser_distinction": "none",
    }, enforce_block=True)
    assert bad["passed"] is False
    assert "constructed_field_listed_as_source" in bad["hard_violations_present"]
    assert "forbidden_assumed_field_used" in bad["hard_violations_present"]


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
        description="Validate source-to-target provenance edge direction."
    )
    parser.add_argument("receipt_json", nargs="?", help="Path to receipt JSON, or - for stdin")
    parser.add_argument("--enforce-block", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        _self_test()
        print(json.dumps({"ok": True, "gate_id": GATE_ID}, indent=2, sort_keys=True))
        return 0
    if not args.receipt_json:
        raise SystemExit("receipt_json is required unless --self-test is set")
    result = run_provenance_edge_direction_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
