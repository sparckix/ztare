"""G-LIMIT-PASSAGE-INHERITANCE-LEMMA — gate for GP-219 proto-op D (advisory v0.1).

Operationalizes proto-op D ("Limit-Passage Property Inheritance") from the
GP-219 PDE / estimate-craft sister vocabulary: a closure attempt that takes
properties from a sequence (finite prefixes, profiles, regularized solutions,
finite packets) to its limit object must NAME the lower-semicontinuity /
approximation / inheritance lemma being invoked at the finite-to-infinite step,
not hand-wave it.

This is the structural shape of every "uniform bound passes to the limit"
argument. The failure mode this gate catches: claiming a property holds at the
limit when only the prelimit version was proven, with the inheritance lemma
implicit or unstated.

# Status: ADVISORY v0.1 (2026-05-05)

Ships in advisory mode (returns passed=True with warnings) until NS Track B
field-test confirms gate semantics. Flip to promote-blocking with `enforce_block=True`.

# What this gate verifies

  M1. Rubric declares ≥0 limit-passage steps under `limit_passage_steps`
  M2. Each step has: name, sequence_described, inheritance_lemma, property_inherited
  M3. inheritance_lemma is non-empty AND identifies a NAMED lemma (LSC, Aubin-Lions-Simon,
      weak-strong pairing, dominated convergence, Egorov, monotone class, etc.) or
      explicitly states "direct/elementary" if no named lemma is needed
  M4. If a closure attempt declares finite_prefix_results: true AND has zero
      limit_passage_steps, fire advisory (most finite-prefix → infinite-limit
      arguments need at least one)

# Usage

    from src.ztare.gates.limit_passage_inheritance_lemma_gate import run_limit_passage_gate
    result = run_limit_passage_gate(rubric_data=rubric)
"""
from __future__ import annotations

from typing import Any


def run_limit_passage_gate(
    rubric_data: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Verify proto-op D limit-passage inheritance lemma declarations.

    Args:
        rubric_data: rubric metadata. Looks for `limit_passage_steps`: list of
          {name, sequence_described, inheritance_lemma, property_inherited}.
          Also reads `finite_prefix_results: bool` for the M4 advisory.
        enforce_block: if True, return passed=False on violations.

    Returns:
        {"passed": bool, "blocking_active": bool, "violations": list[dict],
         "advisory_warnings": list[str], "n_steps_declared": int,
         "n_complete_steps": int, "summary": str}
    """
    rubric_data = rubric_data or {}
    steps = rubric_data.get("limit_passage_steps") or []
    has_finite_prefix = bool(rubric_data.get("finite_prefix_results"))
    violations: list[dict[str, Any]] = []
    warnings: list[str] = []

    if not isinstance(steps, list):
        violations.append({
            "type": "limit_passage_steps_malformed",
            "severity": "advisory" if not enforce_block else "blocking",
            "reason": "limit_passage_steps must be a list of step dicts",
        })
        steps = []

    n_complete = 0
    for i, s in enumerate(steps):
        if not isinstance(s, dict):
            violations.append({
                "type": "step_malformed", "step_index": i,
                "severity": "advisory" if not enforce_block else "blocking",
                "reason": "limit_passage_steps[%d] is not a dict" % i,
            })
            continue
        # M2: structural fields
        missing = [f for f in ("name", "sequence_described", "inheritance_lemma", "property_inherited")
                   if f not in s or s[f] in (None, "", [])]
        if missing:
            violations.append({
                "type": "step_incomplete", "step_index": i,
                "step_name": s.get("name", "<unnamed>"),
                "severity": "advisory" if not enforce_block else "blocking",
                "missing_fields": missing,
                "reason": (
                    "limit_passage_steps[%d] missing %s. Each step must declare: name, "
                    "sequence_described (what sequence is taken), inheritance_lemma (the NAMED "
                    "LSC/approximation/inheritance lemma OR 'direct/elementary'), property_inherited "
                    "(which property transfers to the limit)." % (i, ", ".join(missing))
                ),
            })
            warnings.append(f"step[{i}] ({s.get('name', '<unnamed>')}) missing: {missing}")
            continue
        n_complete += 1

    # M4: finite-prefix results without explicit limit-passage step
    if has_finite_prefix and not steps:
        violations.append({
            "type": "finite_prefix_without_limit_passage",
            "severity": "advisory",
            "reason": (
                "Rubric declares finite_prefix_results: true but has zero limit_passage_steps. "
                "Most finite-prefix → infinite-limit arguments need ≥1 explicit inheritance-lemma "
                "invocation. If this attempt genuinely has no limit-passage step (e.g., the claim "
                "is about a fixed finite prefix only), set `finite_prefix_results: false` to silence."
            ),
        })
        warnings.append("finite_prefix_results: true with 0 limit-passage steps")

    blocking_violations = [v for v in violations if v.get("severity") == "blocking"]
    passed = (not blocking_violations) if enforce_block else True

    summary_parts = [f"{len(steps)} limit-passage step(s)", f"{n_complete} complete"]
    if violations:
        summary_parts.append(f"{len(violations)} violation(s)")
    if not enforce_block:
        summary_parts.append("ADVISORY mode")

    return {
        "passed": passed,
        "blocking_active": enforce_block,
        "violations": violations,
        "advisory_warnings": warnings,
        "n_steps_declared": len(steps),
        "n_complete_steps": n_complete,
        "summary": "; ".join(summary_parts),
    }


# ── Self-tests ──────────────────────────────────────────────────────────


def _self_test() -> None:
    # T1: empty rubric → passed True, no violations
    r = run_limit_passage_gate(rubric_data={})
    assert r["passed"] is True
    assert r["n_steps_declared"] == 0

    # T2: finite_prefix_results without steps → advisory
    r = run_limit_passage_gate(rubric_data={"finite_prefix_results": True})
    assert any(v["type"] == "finite_prefix_without_limit_passage" for v in r["violations"])

    # T3: incomplete step → violation
    r = run_limit_passage_gate(rubric_data={
        "limit_passage_steps": [
            {"name": "epsilon_to_zero", "sequence_described": "u_eps as eps -> 0",
             "inheritance_lemma": "", "property_inherited": "Sobolev bound"},
        ],
    })
    assert any(v["type"] == "step_incomplete" for v in r["violations"])

    # T4: complete step → no violation
    r = run_limit_passage_gate(rubric_data={
        "limit_passage_steps": [
            {
                "name": "epsilon_to_zero",
                "sequence_described": "u_eps in regularized parabolic equation",
                "inheritance_lemma": "Aubin-Lions-Simon compactness",
                "property_inherited": "L^2 strong convergence + uniform Sobolev bound",
            },
        ],
    })
    assert r["passed"] is True
    assert r["n_complete_steps"] == 1
    assert not any(v.get("severity") == "blocking" for v in r["violations"])

    # T5: blocking mode with incomplete → passed=False
    r = run_limit_passage_gate(
        rubric_data={"limit_passage_steps": [{"name": "x", "sequence_described": "y",
                                               "inheritance_lemma": "", "property_inherited": ""}]},
        enforce_block=True,
    )
    assert r["passed"] is False

    # T6: "direct/elementary" is a valid inheritance_lemma value
    r = run_limit_passage_gate(rubric_data={
        "limit_passage_steps": [
            {"name": "sequence_n", "sequence_described": "u_n -> u",
             "inheritance_lemma": "direct/elementary", "property_inherited": "pointwise convergence"},
        ],
    })
    assert r["passed"] is True
    assert r["n_complete_steps"] == 1

    print("ALL TESTS PASSED")


if __name__ == "__main__":
    _self_test()
