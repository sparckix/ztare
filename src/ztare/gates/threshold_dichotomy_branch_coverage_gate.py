"""G-THRESHOLD-DICHOTOMY-BRANCH-COVERAGE — gate for GP-219 proto-op C (advisory v0.1).

Operationalizes proto-op C ("Quantitative Threshold Dichotomy") from the GP-219
PDE / estimate-craft sister vocabulary: a closure attempt should declare any
threshold-dichotomy claims as a binary — "exceed threshold T OR force degeneracy
D" — with BOTH branches explicitly proven, not just one.

This is the structural shape of state-pricing arguments: every "no survivor
above wall" claim is a threshold dichotomy. The failure mode this gate catches:
proving only the "exceed threshold" branch, leaving "force degeneracy" implicit
or hand-waved.

# Status: ADVISORY v0.1 (2026-05-05)

Ships in advisory mode (returns passed=True with warnings) until NS Track B
field-test confirms gate semantics. Flip to promote-blocking with `enforce_block=True`.

# What this gate verifies (when active)

  M1. Rubric declares ≥0 threshold dichotomies under `threshold_dichotomies`
  M2. Each dichotomy has: name, threshold_T, degeneracy_D, branch_proofs
  M3. branch_proofs is a dict with both `exceeds_threshold_proof` and
      `forces_degeneracy_proof` keys, each non-empty
  M4. If a closure attempt has no dichotomies declared, fire advisory note
      (proto-op C is the structural shape of state-pricing — most closure
      attempts on Track B-shaped problems have at least one)

# Usage

    from src.ztare.gates.threshold_dichotomy_branch_coverage_gate import run_threshold_dichotomy_gate
    result = run_threshold_dichotomy_gate(rubric_data=rubric)
"""
from __future__ import annotations

from typing import Any


def run_threshold_dichotomy_gate(
    rubric_data: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
    expect_dichotomy: bool = False,
) -> dict[str, Any]:
    """Verify proto-op C threshold-dichotomy declarations.

    Args:
        rubric_data: rubric metadata. Looks for `threshold_dichotomies`: list of
          {name, threshold_T, degeneracy_D, branch_proofs: {exceeds_threshold_proof, forces_degeneracy_proof}}
        enforce_block: if True, return passed=False on violations.
        expect_dichotomy: if True, fire advisory when zero dichotomies declared
          (Track B-shaped closure attempts usually need at least one).

    Returns:
        {"passed": bool, "blocking_active": bool, "violations": list[dict],
         "advisory_warnings": list[str], "n_dichotomies_declared": int,
         "n_complete_dichotomies": int, "summary": str}
    """
    rubric_data = rubric_data or {}
    dichotomies = rubric_data.get("threshold_dichotomies") or []
    violations: list[dict[str, Any]] = []
    warnings: list[str] = []

    if not isinstance(dichotomies, list):
        violations.append({
            "type": "threshold_dichotomies_malformed",
            "severity": "advisory" if not enforce_block else "blocking",
            "reason": "threshold_dichotomies must be a list of dichotomy dicts",
        })
        dichotomies = []

    n_complete = 0
    for i, d in enumerate(dichotomies):
        if not isinstance(d, dict):
            violations.append({
                "type": "dichotomy_malformed", "dichotomy_index": i,
                "severity": "advisory" if not enforce_block else "blocking",
                "reason": "threshold_dichotomies[%d] is not a dict" % i,
            })
            continue
        # M2: structural fields
        missing = [f for f in ("name", "threshold_T", "degeneracy_D", "branch_proofs") if f not in d or d[f] in (None, "", [])]
        if missing:
            violations.append({
                "type": "dichotomy_incomplete", "dichotomy_index": i,
                "dichotomy_name": d.get("name", "<unnamed>"),
                "severity": "advisory" if not enforce_block else "blocking",
                "missing_fields": missing,
                "reason": (
                    "threshold_dichotomies[%d] missing %s. Each dichotomy must declare: name, "
                    "threshold_T (the fixed positive threshold), degeneracy_D (the structural-degeneracy "
                    "alternative), and branch_proofs with both exceeds_threshold_proof and forces_degeneracy_proof."
                    % (i, ", ".join(missing))
                ),
            })
            warnings.append(f"dichotomy[{i}] ({d.get('name', '<unnamed>')}) missing: {missing}")
            continue
        # M3: both branches
        bp = d.get("branch_proofs") or {}
        if not isinstance(bp, dict):
            violations.append({
                "type": "branch_proofs_malformed", "dichotomy_index": i,
                "dichotomy_name": d.get("name", "<unnamed>"),
                "severity": "advisory" if not enforce_block else "blocking",
                "reason": "branch_proofs must be a dict with exceeds_threshold_proof + forces_degeneracy_proof keys",
            })
            continue
        missing_branches = [b for b in ("exceeds_threshold_proof", "forces_degeneracy_proof") if not bp.get(b)]
        if missing_branches:
            violations.append({
                "type": "missing_branch_proof", "dichotomy_index": i,
                "dichotomy_name": d.get("name", "<unnamed>"),
                "severity": "advisory" if not enforce_block else "blocking",
                "missing_branches": missing_branches,
                "reason": (
                    "dichotomy[%d] (%s) is missing %s. Proto-op C requires BOTH branches proven: "
                    "the local quantity exceeds threshold T, OR forces degeneracy D. "
                    "Most failure modes prove only the threshold branch and leave degeneracy hand-waved."
                    % (i, d.get("name", "<unnamed>"), ", ".join(missing_branches))
                ),
            })
            warnings.append(f"dichotomy[{i}] ({d.get('name', '<unnamed>')}) missing branches: {missing_branches}")
            continue
        n_complete += 1

    # M4: zero dichotomies on a context where one is expected
    if not dichotomies and expect_dichotomy:
        violations.append({
            "type": "no_dichotomies_declared_in_track_b_context",
            "severity": "advisory",  # never blocking for this M4 check
            "reason": (
                "No threshold_dichotomies declared. For Track B-shaped state-pricing closure attempts, "
                "proto-op C is the structural shape of the entire argument; most attempts have ≥1 "
                "dichotomy. If this is genuinely an exception, set `expect_dichotomy: false` in caller."
            ),
        })
        warnings.append("zero threshold dichotomies in expected-dichotomy context")

    blocking_violations = [v for v in violations if v.get("severity") == "blocking"]
    passed = (not blocking_violations) if enforce_block else True

    summary_parts = [f"{len(dichotomies)} dichotomy/ies declared", f"{n_complete} complete"]
    if violations:
        summary_parts.append(f"{len(violations)} violation(s)")
    if not enforce_block:
        summary_parts.append("ADVISORY mode")

    return {
        "passed": passed,
        "blocking_active": enforce_block,
        "violations": violations,
        "advisory_warnings": warnings,
        "n_dichotomies_declared": len(dichotomies),
        "n_complete_dichotomies": n_complete,
        "summary": "; ".join(summary_parts),
    }


# ── Self-tests ──────────────────────────────────────────────────────────


def _self_test() -> None:
    # T1: empty rubric, no expectation → no violations, passed True
    r = run_threshold_dichotomy_gate(rubric_data={})
    assert r["passed"] is True
    assert r["n_dichotomies_declared"] == 0
    assert r["n_complete_dichotomies"] == 0

    # T2: empty + expect_dichotomy=True → advisory violation
    r = run_threshold_dichotomy_gate(rubric_data={}, expect_dichotomy=True)
    assert any(v["type"] == "no_dichotomies_declared_in_track_b_context" for v in r["violations"])

    # T3: incomplete dichotomy (missing branch proof) → violation
    r = run_threshold_dichotomy_gate(rubric_data={
        "threshold_dichotomies": [
            {
                "name": "lipschitz_reserve_wall",
                "threshold_T": 0.667,
                "degeneracy_D": "collapse to one-route null",
                "branch_proofs": {"exceeds_threshold_proof": "phase5fk_proof.lean"},
            },
        ],
    })
    assert any(v["type"] == "missing_branch_proof" for v in r["violations"])

    # T4: complete dichotomy → no violation
    r = run_threshold_dichotomy_gate(rubric_data={
        "threshold_dichotomies": [
            {
                "name": "lipschitz_reserve_wall",
                "threshold_T": 0.667,
                "degeneracy_D": "collapse to one-route null",
                "branch_proofs": {
                    "exceeds_threshold_proof": "phase5fk_proof.lean",
                    "forces_degeneracy_proof": "phase5fc_no_survivor.lean",
                },
            },
        ],
    })
    assert r["passed"] is True
    assert r["n_complete_dichotomies"] == 1
    assert not any(v.get("severity") == "blocking" for v in r["violations"])

    # T5: blocking mode with incomplete → passed=False
    r = run_threshold_dichotomy_gate(
        rubric_data={
            "threshold_dichotomies": [{"name": "x", "threshold_T": 1.0, "degeneracy_D": "y",
                                       "branch_proofs": {"exceeds_threshold_proof": "p"}}],
        },
        enforce_block=True,
    )
    assert r["passed"] is False
    assert any(v.get("severity") == "blocking" for v in r["violations"])

    print("ALL TESTS PASSED")


if __name__ == "__main__":
    _self_test()
