"""G-PROVENANCE-ACYCLIC-EDGE.

General provenance gate for source-to-target family dependencies.  It blocks
edges whose source families include the target family, a constructed family, or
an explicitly forbidden downstream family, and cycle-detects the supplied
dependency edge list.
"""
from __future__ import annotations

from typing import Any


GATE_ID = "G-PROVENANCE-ACYCLIC-EDGE"

REQUIRED_FIELDS = (
    "edge_id",
    "target_family",
    "source_families",
    "constructed_families",
    "forbidden_source_families",
    "dependency_edges",
    "nearest_confuser",
    "confuser_distinction",
)


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
    if isinstance(values, str):
        return {values.strip()} if values.strip() else set()
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


def _edge_pair(value: Any) -> tuple[str, str] | None:
    if not isinstance(value, dict):
        return None
    src = value.get("from")
    dst = value.get("to")
    if not isinstance(src, str) or not isinstance(dst, str):
        return None
    src = src.strip()
    dst = dst.strip()
    if not src or not dst:
        return None
    return src, dst


def _find_cycle(edges: Any) -> list[str] | None:
    if not isinstance(edges, list):
        return None
    adjacency: dict[str, list[str]] = {}
    for value in edges:
        pair = _edge_pair(value)
        if pair is None:
            continue
        src, dst = pair
        adjacency.setdefault(src, []).append(dst)
        adjacency.setdefault(dst, [])

    color = {node: 0 for node in adjacency}
    parent: dict[str, str | None] = {node: None for node in adjacency}

    def reconstruct(start: str, end: str) -> list[str]:
        if start == end:
            return [start, end]
        chain = [end]
        cursor = parent.get(end)
        while cursor is not None and cursor != start:
            chain.append(cursor)
            cursor = parent.get(cursor)
        chain.append(start)
        chain.reverse()
        chain.append(start)
        return chain

    for root in list(adjacency):
        if color[root] != 0:
            continue
        stack: list[tuple[str, int]] = [(root, 0)]
        color[root] = 1
        while stack:
            node, idx = stack[-1]
            neighbors = adjacency.get(node, [])
            if idx >= len(neighbors):
                color[node] = 2
                stack.pop()
                continue
            stack[-1] = (node, idx + 1)
            neighbor = neighbors[idx]
            if color[neighbor] == 1:
                return reconstruct(neighbor, node)
            if color[neighbor] == 0:
                color[neighbor] = 1
                parent[neighbor] = node
                stack.append((neighbor, 0))
    return None


def _malformed_edges(edges: Any) -> list[Any]:
    if edges is None:
        return []
    if not isinstance(edges, list):
        return [edges]
    return [value for value in edges if _edge_pair(value) is None]


def run_provenance_acyclic_edge_gate(
    receipt: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Validate that a provenance edge has no declared family cycle."""
    receipt = receipt or {}
    violations: list[dict[str, Any]] = []

    if not isinstance(receipt, dict):
        return {
            "gate_id": GATE_ID,
            "passed": not enforce_block,
            "complete": False,
            "blocking_active": enforce_block,
            "violations": [{
                "type": "provenance_acyclic_edge_receipt_malformed",
                "severity": "blocking" if enforce_block else "advisory",
                "reason": "receipt must be a JSON object",
            }],
            "missing_fields": list(REQUIRED_FIELDS),
            "required_fields": list(REQUIRED_FIELDS),
            "hard_violations_present": ["malformed_receipt"],
            "cycle": None,
            "summary": "malformed provenance acyclic-edge receipt",
        }

    missing = [field for field in REQUIRED_FIELDS if not _present(receipt.get(field))]
    if missing:
        violations.append({
            "type": "provenance_acyclic_edge_receipt_incomplete",
            "severity": "blocking" if enforce_block else "advisory",
            "missing_fields": missing,
            "reason": "acyclic provenance receipts need families, forbidden sources, and dependency edges",
        })

    target = str(receipt.get("target_family") or "").strip()
    sources = _names(receipt.get("source_families"))
    constructed = _names(receipt.get("constructed_families"))
    forbidden = _names(receipt.get("forbidden_source_families"))
    malformed_edges = _malformed_edges(receipt.get("dependency_edges"))
    cycle = _find_cycle(receipt.get("dependency_edges"))

    hard_present: list[str] = []
    if target and target in sources:
        hard_present.append("target_family_listed_as_source")
        violations.append({
            "type": "target_family_listed_as_source",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": [target],
            "reason": "a target family cannot be a source for its own construction",
        })

    constructed_as_source = sorted(sources & constructed)
    if constructed_as_source:
        hard_present.append("constructed_family_listed_as_source")
        violations.append({
            "type": "constructed_family_listed_as_source",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": constructed_as_source,
            "reason": "constructed families cannot be listed as sources",
        })

    forbidden_as_source = sorted(sources & forbidden)
    if forbidden_as_source:
        hard_present.append("forbidden_downstream_family_used")
        violations.append({
            "type": "forbidden_downstream_family_used",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": forbidden_as_source,
            "reason": "receipt uses a downstream or confuser family declared forbidden",
        })

    if malformed_edges:
        hard_present.append("malformed_dependency_edge")
        violations.append({
            "type": "malformed_dependency_edge",
            "severity": "blocking" if enforce_block else "advisory",
            "fields": malformed_edges,
            "reason": "dependency_edges entries must have string from/to fields",
        })

    if cycle:
        hard_present.append("dependency_cycle")
        violations.append({
            "type": "dependency_cycle",
            "severity": "blocking" if enforce_block else "advisory",
            "cycle": cycle,
            "reason": "declared provenance dependency graph contains a directed cycle",
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
        "cycle": cycle,
        "summary": (
            "complete provenance acyclic-edge receipt"
            if complete else
            "incomplete provenance acyclic-edge receipt; "
            f"missing {len(missing)} field(s)"
        ),
    }


def _self_test() -> None:
    good = run_provenance_acyclic_edge_gate({
        "edge_id": "edge",
        "target_family": "Target",
        "source_families": ["Coverage", "Incidence"],
        "constructed_families": ["Target"],
        "forbidden_source_families": ["DownstreamTargetAdapter"],
        "dependency_edges": [
            {"from": "Coverage", "to": "Target"},
            {"from": "Incidence", "to": "Target"},
        ],
        "nearest_confuser": "DownstreamTargetAdapter",
        "confuser_distinction": "sources precede Target and do not consume Target adapters",
    }, enforce_block=True)
    assert good["passed"] is True
    assert good["complete"] is True

    bad = run_provenance_acyclic_edge_gate({
        "edge_id": "edge",
        "target_family": "Target",
        "source_families": ["DownstreamTargetAdapter"],
        "constructed_families": ["Target"],
        "forbidden_source_families": ["DownstreamTargetAdapter"],
        "dependency_edges": [
            {"from": "Target", "to": "DownstreamTargetAdapter"},
            {"from": "DownstreamTargetAdapter", "to": "Target"},
        ],
        "nearest_confuser": "DownstreamTargetAdapter",
        "confuser_distinction": "none",
    }, enforce_block=True)
    assert bad["passed"] is False
    assert "forbidden_downstream_family_used" in bad["hard_violations_present"]
    assert "dependency_cycle" in bad["hard_violations_present"]


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
        description="Validate that a provenance family edge is acyclic."
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
    result = run_provenance_acyclic_edge_gate(
        _read_json(args.receipt_json),
        enforce_block=args.enforce_block,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
