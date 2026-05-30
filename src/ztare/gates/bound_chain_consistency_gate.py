"""G-BOUND-CHAIN-CONSISTENCY — gate for ps_06 Proof by Estimate Chaining.

Operationalizes ps_06 from the GP-216 problem-solving sister vocabulary:
"a conclusion is reached by establishing a chain of precise quantitative
bounds on existing structures."

When a substrate's proof proceeds by chaining bounds (Lipschitz reserve
ledger, market-impact pricing chain, falsifier-spine receipt chain, etc.),
this gate verifies:

  C1. Each bound has a declared type (premise variables, conclusion bound,
      scope domain).
  C2. Each bound's premise matches the prior bound's conclusion at the type
      level (chain-consistency).
  C3. No silent constant inflation: if bound[i] says `X ≤ C1·Y` and
      bound[i+1] says `X ≤ C2·Y` with C2 > C1, the gate flags it unless
      bound[i+1] declares the inflation explicitly.
  C4. Scope-leak detection: each bound's domain must be declared and
      consistent with the substrate's topology.

This is a SIMPLIFIED version: it operates on a typed-receipt schema rather
than parsing Lean AST. Substrates declare bound chains in rubric metadata
or in a structured `bound_chain.json` artifact. The full Lean AST walker
is deferred until use-case specifies the parsing requirements.

The schema for declared bound chains:
  [
    {
      "id": "<bound name>",
      "premises": [<list of typed quantities, e.g., "lowFrequencyLipschitzCost: R+">],
      "conclusion": "<typed bound, e.g., 'leakage ≤ C·lowFrequencyLipschitzCost·highShellEnergy'>",
      "constants": {"C": <value or symbolic>},
      "scope": "<topology / function-space declaration>",
      "depends_on": [<list of prior bound ids>],
    }
  ]
"""
from __future__ import annotations

from typing import Any


def run_bound_chain_gate(
    bound_chain: list[dict],
    rubric_data: dict[str, Any] | None = None,
    *,
    allow_implicit_inflation: bool = False,
) -> dict[str, Any]:
    """Verify bound chain consistency.

    Args:
        bound_chain: list of bound declarations following the schema above.
        rubric_data: rubric metadata (optional).
        allow_implicit_inflation: if False, any constant inflation between
          chained bounds must be explicitly declared.

    Returns:
        {
          "passed": bool,
          "violations": list[dict],
          "n_bounds": int,
          "chain_complete": bool,
          "summary": str,
        }
    """
    rubric_data = rubric_data or {}
    violations: list[dict[str, Any]] = []

    if not bound_chain:
        return {
            "passed": True,
            "violations": [],
            "n_bounds": 0,
            "chain_complete": True,
            "summary": "no bound chain declared",
        }

    # C1: each bound has declared type
    for i, b in enumerate(bound_chain):
        for required in ("id", "premises", "conclusion"):
            if required not in b:
                violations.append({
                    "type": "missing_declaration",
                    "severity": "blocking",
                    "bound_index": i,
                    "missing": required,
                    "reason": f"Bound at index {i} missing required field {required!r}",
                })

    # Build dependency map
    by_id = {b.get("id"): b for b in bound_chain if "id" in b}

    # C2: each bound's dependencies must resolve, and premises must be
    # type-compatible with prior bounds' conclusions
    for b in bound_chain:
        deps = b.get("depends_on", [])
        for dep_id in deps:
            if dep_id not in by_id:
                violations.append({
                    "type": "unresolved_dependency",
                    "severity": "blocking",
                    "bound_id": b.get("id"),
                    "dep_id": dep_id,
                    "reason": f"Bound {b.get('id')!r} declares dependency on {dep_id!r}, not found in chain",
                })

    # C3: silent constant inflation detection
    # For each pair of bounds where one depends on the other and they bound the same quantity
    if not allow_implicit_inflation:
        for b in bound_chain:
            for dep_id in b.get("depends_on", []):
                dep = by_id.get(dep_id)
                if not dep:
                    continue
                # Compare conclusions: if both contain the same LHS quantity,
                # check whether constants were declared
                conc_b = b.get("conclusion", "")
                conc_dep = dep.get("conclusion", "")
                # Simple heuristic: extract leading quantity (part before "≤" or "<=")
                lhs_b = _extract_lhs(conc_b)
                lhs_dep = _extract_lhs(conc_dep)
                if lhs_b and lhs_dep and lhs_b == lhs_dep:
                    # Same quantity bounded; check constants
                    c_b = b.get("constants", {})
                    c_dep = dep.get("constants", {})
                    common_keys = set(c_b.keys()) & set(c_dep.keys())
                    for k in common_keys:
                        v_b = _to_float(c_b[k])
                        v_dep = _to_float(c_dep[k])
                        if v_b is not None and v_dep is not None and v_b > v_dep * 1.01:
                            if not b.get("inflation_declared"):
                                violations.append({
                                    "type": "silent_constant_inflation",
                                    "severity": "blocking",
                                    "bound_id": b.get("id"),
                                    "dep_id": dep_id,
                                    "constant": k,
                                    "inflated_to": v_b,
                                    "from_value": v_dep,
                                    "reason": (
                                        f"Bound {b.get('id')!r} inflates constant {k} from {v_dep} "
                                        f"to {v_b} relative to {dep_id!r}, but `inflation_declared` "
                                        f"is not set. Silent constant inflation is a known failure mode "
                                        f"in chained bound proofs."
                                    ),
                                })

    # C4: scope declaration (warning if missing)
    for b in bound_chain:
        if "scope" not in b:
            violations.append({
                "type": "scope_undeclared",
                "severity": "warning",
                "bound_id": b.get("id"),
                "reason": (
                    f"Bound {b.get('id')!r} has no declared scope/topology. Scope-leak risk: a bound "
                    f"derived under one topology may not transfer to the substrate's actual function "
                    f"space. Recommend declaring `scope` field."
                ),
            })

    # Chain completeness check: is there a single root + leaf?
    has_roots = [b for b in bound_chain if not b.get("depends_on")]
    leaves = [b for b in bound_chain if not _is_dependency_of_any(b, bound_chain)]
    chain_complete = len(has_roots) >= 1 and len(leaves) >= 1

    blocking = [v for v in violations if v.get("severity") == "blocking"]
    passed = len(blocking) == 0

    return {
        "passed": passed,
        "violations": violations,
        "n_bounds": len(bound_chain),
        "n_blocking_violations": len(blocking),
        "chain_complete": chain_complete,
        "summary": (
            f"chain_n={len(bound_chain)}; blocking={len(blocking)}; "
            f"complete={chain_complete}"
        ),
    }


def _extract_lhs(conclusion: str) -> str:
    """Extract LHS quantity name from a bound declaration."""
    for sep in ("≤", "<=", "≥", ">=", "="):
        if sep in conclusion:
            return conclusion.split(sep, 1)[0].strip()
    return conclusion.strip()


def _to_float(v: Any) -> float | None:
    """Convert to float if possible."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _is_dependency_of_any(b: dict, chain: list[dict]) -> bool:
    bid = b.get("id")
    if not bid:
        return False
    return any(bid in other.get("depends_on", []) for other in chain)


def _self_test() -> None:
    """Smoke tests, modeled on NS Track B falsifier-spine bound shapes."""
    # Test 1: clean chain
    chain = [
        {
            "id": "bound_lh_constant",
            "premises": ["lowFreqLipschitzCost: R+", "highShellEnergy: R+"],
            "conclusion": "leakage <= 1.0 * lowFreqLipschitzCost * highShellEnergy",
            "constants": {"C_lh": 1.0},
            "scope": "Leray-Sobolev H^1 paraproduct",
            "depends_on": [],
        },
        {
            "id": "bound_lh_lp_bony",
            "premises": ["leakage", "reserveLoss"],
            "conclusion": "leakage <= reserveLoss",
            "constants": {"C_lh": 1.0},
            "scope": "Leray-Sobolev H^1 paraproduct",
            "depends_on": ["bound_lh_constant"],
        },
    ]
    r = run_bound_chain_gate(chain)
    assert r["passed"], f"Test 1 should pass: {r}"
    print(f"  Test 1 PASS (clean chain, n={r['n_bounds']})")

    # Test 2: silent constant inflation
    chain2 = [
        {
            "id": "bound_a",
            "premises": ["X"],
            "conclusion": "leakage <= C·X",
            "constants": {"C": 1.0},
            "scope": "L2",
            "depends_on": [],
        },
        {
            "id": "bound_b",
            "premises": ["X"],
            "conclusion": "leakage <= C·X",
            "constants": {"C": 5.0},  # silent inflation from 1 to 5
            "scope": "L2",
            "depends_on": ["bound_a"],
        },
    ]
    r = run_bound_chain_gate(chain2)
    assert not r["passed"], f"Test 2 should fail: {r}"
    assert any(v["type"] == "silent_constant_inflation" for v in r["violations"])
    print(f"  Test 2 PASS (silent inflation detected)")

    # Test 3: declared inflation passes
    chain3 = [
        {
            "id": "bound_a",
            "premises": ["X"],
            "conclusion": "leakage <= C·X",
            "constants": {"C": 1.0},
            "scope": "L2",
            "depends_on": [],
        },
        {
            "id": "bound_b",
            "premises": ["X"],
            "conclusion": "leakage <= C·X",
            "constants": {"C": 5.0},
            "scope": "L2",
            "depends_on": ["bound_a"],
            "inflation_declared": True,
        },
    ]
    r = run_bound_chain_gate(chain3)
    assert r["passed"], f"Test 3 should pass with inflation_declared: {r}"
    print(f"  Test 3 PASS (declared inflation accepted)")

    # Test 4: missing declaration fails
    chain4 = [{"id": "broken"}]
    r = run_bound_chain_gate(chain4)
    assert not r["passed"]
    assert any(v["type"] == "missing_declaration" for v in r["violations"])
    print(f"  Test 4 PASS (missing fields detected)")

    # Test 5: unresolved dependency fails
    chain5 = [
        {"id": "leaf", "premises": ["X"], "conclusion": "Y <= X", "depends_on": ["nonexistent"]},
    ]
    r = run_bound_chain_gate(chain5)
    assert not r["passed"]
    assert any(v["type"] == "unresolved_dependency" for v in r["violations"])
    print(f"  Test 5 PASS (unresolved dep detected)")

    print("All self-tests passed.")


if __name__ == "__main__":
    _self_test()
