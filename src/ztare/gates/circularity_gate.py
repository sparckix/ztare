"""G-CIRC — deterministic circularity detector.

Detects structural circularity in a thesis by cycle-detecting the claim
dependency graph emitted as `probability_dag.json`. A cycle in a directed
argument graph means the thesis's conclusion is presupposed in its own
premise — the canonical definition of circularity per the ZTARE
anti-pattern catalog Part 1 (structural blocker SB-1).

Deterministic Python replacement for the LLM-taxonomy-based `circularity`
class injection via `inject_antipattern_catalog: "hardkill"`. Once this
gate is live in the loop, the hardkill injection can be retired for
circularity (cf. unfalsifiable_claim, which needs G-FALSIFY separately).

DAG format (from autoresearch_loop champion promotion):
  {
    "outcome": {"label": str, "probability": float},
    "nodes":   [{"id": str, "label": str, "probability": float,
                 "watch_signal": str}, ...],
    "edges":   [{"from": str, "to": str, "weight": float}, ...]
  }

Scope
-----
- Catches DIRECTED CYCLES in the claim graph (including self-loops).
- Does NOT catch semantic circularity that's hidden in natural-language
  definitions (X defined in terms of Y where Y is the thing being proven).
  That requires either a semantic-gate or the LLM judge. The DAG-level
  detector is permissive-but-exact: zero false positives (if the DAG
  claims acyclicity and it isn't, the thesis is structurally broken).

Usage
-----
  from ztare.gates.circularity_gate import run_circularity_gate
  result = run_circularity_gate(Path("projects/foo/champion_probability_dag.json"))
  if not result["passed"]:
      # Dispatch as structural blocker; score → 0
      ...

Not currently wired into autoresearch_loop.py. Wiring is the last step
of the hardkill-retirement program (only after G-FALSIFY is also live).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


GATE_ID = "G-CIRC"
GATE_NAME = "circularity_gate"


def _build_adjacency(dag: dict[str, Any]) -> dict[str, list[str]]:
    """Build adjacency list from DAG. Includes the synthetic 'outcome' node
    as a target only (no outgoing edges). Nodes are keyed by id; 'outcome'
    is keyed literally. Unknown edge endpoints are silently dropped (safe
    degradation for malformed JSON).
    """
    adj: dict[str, list[str]] = {}
    for node in dag.get("nodes", []) or []:
        nid = node.get("id")
        if nid:
            adj.setdefault(nid, [])
    # outcome always exists as a sink
    if dag.get("outcome") is not None:
        adj.setdefault("outcome", [])
    for edge in dag.get("edges", []) or []:
        src = edge.get("from")
        dst = edge.get("to")
        if not src or not dst:
            continue
        # If source not declared as node, auto-register (lenient)
        adj.setdefault(src, [])
        adj.setdefault(dst, [])
        adj[src].append(dst)
    return adj


def _find_cycle(adj: dict[str, list[str]]) -> list[str] | None:
    """DFS cycle detection. Returns the cycle path (list of node ids starting
    and ending with the same node) if any cycle exists; None otherwise.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in adj}
    parent: dict[str, str | None] = {n: None for n in adj}

    def _reconstruct(start: str, end: str) -> list[str]:
        # Self-loop special case
        if start == end:
            return [start, end]
        # Walk parent chain from 'end' back to 'start', then close the loop
        chain = [end]
        cursor = parent.get(end)
        while cursor is not None and cursor != start:
            chain.append(cursor)
            cursor = parent.get(cursor)
        chain.append(start)
        chain.reverse()
        chain.append(start)  # close the cycle back to the ancestor
        return chain

    for root in list(adj.keys()):
        if color[root] != WHITE:
            continue
        stack: list[tuple[str, int]] = [(root, 0)]
        parent[root] = None
        color[root] = GRAY
        while stack:
            node, idx = stack[-1]
            neighbors = adj.get(node, [])
            if idx >= len(neighbors):
                color[node] = BLACK
                stack.pop()
                continue
            stack[-1] = (node, idx + 1)
            nbr = neighbors[idx]
            if nbr not in color:
                continue  # external reference
            if color[nbr] == GRAY:
                # Found cycle: nbr is ancestor of node
                return _reconstruct(nbr, node)
            if color[nbr] == WHITE:
                color[nbr] = GRAY
                parent[nbr] = node
                stack.append((nbr, 0))
    return None


def run_circularity_gate(
    probability_dag_path: Path | str,
) -> dict[str, Any]:
    """Run the circularity gate on a probability_dag.json file.

    Parameters
    ----------
    probability_dag_path : Path or str
        Path to the DAG JSON. Both champion_probability_dag.json and
        latest_probability_dag.json formats are supported (they share
        the same schema).

    Returns
    -------
    dict with keys:
        gate_id:   "G-CIRC"
        passed:    bool
        cycle:     list[str] or None
        node_count: int
        edge_count: int
        rationale: str
        error:     str or absent
    """
    p = Path(probability_dag_path)
    result: dict[str, Any] = {
        "gate_id": GATE_ID,
        "passed": False,
        "cycle": None,
        "node_count": 0,
        "edge_count": 0,
        "rationale": "",
    }
    if not p.is_file():
        result["rationale"] = f"DAG file not found: {p}"
        result["error"] = "FileNotFoundError"
        return result
    try:
        dag = json.loads(p.read_text())
    except json.JSONDecodeError as exc:
        result["rationale"] = f"DAG JSON invalid: {exc}"
        result["error"] = "JSONDecodeError"
        return result

    adj = _build_adjacency(dag)
    result["node_count"] = len(adj)
    result["edge_count"] = sum(len(v) for v in adj.values())

    cycle = _find_cycle(adj)
    if cycle is None:
        result["passed"] = True
        result["rationale"] = (
            f"DAG acyclic ({result['node_count']} nodes, "
            f"{result['edge_count']} edges)."
        )
    else:
        result["passed"] = False
        result["cycle"] = cycle
        result["rationale"] = (
            f"DAG contains directed cycle {' -> '.join(cycle)}. "
            f"Thesis conclusion depends on itself (SB-1 circularity)."
        )
    return result


def _self_test() -> int:
    """Unit tests on in-memory DAG fixtures.

    Runs as __main__; returns 0 on pass, 1 on fail.
    """
    import tempfile

    def _write(dag: dict) -> Path:
        fh = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        fh.write(json.dumps(dag))
        fh.close()
        return Path(fh.name)

    # Case 1: acyclic (gp150 real champion shape)
    dag_good = {
        "outcome": {"label": "T", "probability": 0.58},
        "nodes": [{"id": "A"}, {"id": "B"}, {"id": "C"}, {"id": "D"}],
        "edges": [
            {"from": "A", "to": "D"}, {"from": "B", "to": "D"},
            {"from": "B", "to": "C"}, {"from": "C", "to": "outcome"},
            {"from": "D", "to": "outcome"},
        ],
    }
    r = run_circularity_gate(_write(dag_good))
    assert r["passed"], f"acyclic case failed: {r}"
    print(f"  acyclic DAG: PASS (nodes={r['node_count']})")

    # Case 2: self-loop
    dag_self = {
        "outcome": {"label": "T"},
        "nodes": [{"id": "A"}, {"id": "B"}],
        "edges": [{"from": "A", "to": "A"}, {"from": "A", "to": "outcome"}],
    }
    r = run_circularity_gate(_write(dag_self))
    assert not r["passed"], "self-loop should have failed"
    assert r["cycle"] == ["A", "A"], f"self-loop cycle mismatch: {r['cycle']}"
    print(f"  self-loop: FAIL-as-expected (cycle={r['cycle']})")

    # Case 3: 3-node cycle
    dag_cycle = {
        "outcome": {"label": "T"},
        "nodes": [{"id": "A"}, {"id": "B"}, {"id": "C"}],
        "edges": [
            {"from": "A", "to": "B"}, {"from": "B", "to": "C"},
            {"from": "C", "to": "A"}, {"from": "A", "to": "outcome"},
        ],
    }
    r = run_circularity_gate(_write(dag_cycle))
    assert not r["passed"], "3-cycle should have failed"
    assert r["cycle"] == ["A", "B", "C", "A"], f"3-cycle mismatch: {r['cycle']}"
    print(f"  3-cycle: FAIL-as-expected (cycle={r['cycle']})")

    # Case 4: malformed JSON
    fh = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    fh.write("{not json")
    fh.close()
    r = run_circularity_gate(Path(fh.name))
    assert not r["passed"]
    assert r.get("error") == "JSONDecodeError"
    print(f"  malformed JSON: FAIL-safe")

    # Case 5: missing file
    r = run_circularity_gate(Path("/nonexistent/dag.json"))
    assert not r["passed"]
    assert r.get("error") == "FileNotFoundError"
    print(f"  missing file: FAIL-safe")

    # Case 6: empty DAG (no nodes, no edges) — vacuously acyclic
    r = run_circularity_gate(_write({"outcome": {}, "nodes": [], "edges": []}))
    assert r["passed"], "empty DAG should pass (vacuously acyclic)"
    print(f"  empty DAG: PASS (vacuous)")

    print("\n6/6 circularity_gate self-tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_self_test())
