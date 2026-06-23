"""G-AUXILIARY-OBJECT-DECLARATION — gate for GP-219 proto-op A (advisory v0.1).

Operationalizes proto-op A ("Auxiliary Comparison Object Construction") from
the GP-219 PDE / estimate-craft sister vocabulary: a closure attempt should
declare any engineered auxiliary objects (barriers, intertwiners, certificates,
test functions, charged observables, dichotomy lemmas, normal-form reductions,
structural lemmas) up front, with their engineered properties named.

# Status: ADVISORY v0.1 (2026-05-05)

Ships in advisory mode (returns passed=True with warnings) until NS Track B
field-test data confirms gate semantics. Flip to promote-blocking by setting
`enforce_block=True` once 5 closure-attempt observations validate the gate.

# What this gate verifies (when active)

  M1. Rubric declares ≥1 auxiliary object under `auxiliary_objects` (key list)
      OR closure attempt explicitly states "no auxiliary object needed"
  M2. Each declared object has: name, engineered_properties, comparison_target
  M3. Engineered_properties is non-empty (object must have NAMED properties,
      not just "some function")

# Usage

    from ztare.gates.auxiliary_object_declaration_gate import run_auxiliary_object_gate
    result = run_auxiliary_object_gate(rubric_data=rubric)
    # advisory: result["advisory_warnings"] reports issues; result["passed"] is True by default
    # blocking: pass enforce_block=True; result["passed"] reflects M1-M3
"""
from __future__ import annotations

from typing import Any


def run_auxiliary_object_gate(
    rubric_data: dict[str, Any] | None = None,
    *,
    enforce_block: bool = False,
) -> dict[str, Any]:
    """Verify proto-op A auxiliary-object declarations in a closure-attempt rubric.

    Args:
        rubric_data: rubric metadata. Looks for:
          - `auxiliary_objects`: list of {name, engineered_properties, comparison_target}
          - OR `no_auxiliary_object`: bool (explicit declaration that none is needed)
        enforce_block: if True, return passed=False on violations (promote-blocking).
            If False (default), return passed=True with advisory warnings.

    Returns:
        {
          "passed": bool,                    # always True in advisory mode
          "blocking_active": bool,
          "violations": list[dict],          # populated regardless of mode
          "advisory_warnings": list[str],    # human-readable
          "n_objects_declared": int,
          "summary": str,
        }
    """
    rubric_data = rubric_data or {}
    aux_objects = rubric_data.get("auxiliary_objects")
    no_aux = bool(rubric_data.get("no_auxiliary_object"))

    violations: list[dict[str, Any]] = []
    warnings: list[str] = []

    # M1: declaration required (either list or explicit "none")
    if not aux_objects and not no_aux:
        violations.append({
            "type": "auxiliary_object_not_declared",
            "severity": "advisory" if not enforce_block else "blocking",
            "reason": (
                "GP-219 proto-op A requires explicit declaration of any engineered auxiliary "
                "objects (barriers, intertwiners, certificates, dichotomy lemmas, normal-form "
                "reductions, structural lemmas) used by this closure attempt. Add `auxiliary_objects` "
                "to rubric (list of {name, engineered_properties, comparison_target}) OR set "
                "`no_auxiliary_object: true` if this attempt genuinely has none."
            ),
        })
        warnings.append("auxiliary_objects field absent; proto-op A discipline not declared")

    n_objects = 0
    if aux_objects and isinstance(aux_objects, list):
        for i, obj in enumerate(aux_objects):
            n_objects += 1
            if not isinstance(obj, dict):
                violations.append({
                    "type": "auxiliary_object_malformed",
                    "severity": "advisory" if not enforce_block else "blocking",
                    "object_index": i,
                    "reason": "auxiliary_objects[%d] is not a dict; expected {name, engineered_properties, comparison_target}" % i,
                })
                continue
            # M2: structural fields required
            missing_fields = [f for f in ("name", "engineered_properties", "comparison_target") if not obj.get(f)]
            if missing_fields:
                violations.append({
                    "type": "auxiliary_object_incomplete",
                    "severity": "advisory" if not enforce_block else "blocking",
                    "object_index": i,
                    "object_name": obj.get("name", "<unnamed>"),
                    "missing_fields": missing_fields,
                    "reason": (
                        "auxiliary_objects[%d] missing: %s. Each engineered object must declare "
                        "(a) a name, (b) the engineered analytic/structural properties (decay rate, "
                        "sign, PSD-ness, dichotomy outcome, normal form), (c) what it is being "
                        "compared against / what argument it drives." % (i, ", ".join(missing_fields))
                    ),
                })
                warnings.append(f"auxiliary_objects[{i}] ({obj.get('name', '<unnamed>')}) missing: {missing_fields}")

            # M3: engineered_properties must be non-empty
            props = obj.get("engineered_properties")
            if props is not None and not props:
                violations.append({
                    "type": "engineered_properties_empty",
                    "severity": "advisory" if not enforce_block else "blocking",
                    "object_index": i,
                    "object_name": obj.get("name", "<unnamed>"),
                    "reason": (
                        "auxiliary_objects[%d] has empty engineered_properties; this is a generic "
                        "object, not an engineered one. Either declare specific structural/analytic "
                        "properties (e.g., 'cosh-bounded', 'PSD on a fixed cone', 'monotone in shell-index') "
                        "or remove from auxiliary_objects." % i
                    ),
                })

    blocking_violations = [v for v in violations if v.get("severity") == "blocking"]
    passed = (not blocking_violations) if enforce_block else True

    summary_parts = []
    if no_aux:
        summary_parts.append("no_auxiliary_object: explicitly declared none")
    elif n_objects:
        summary_parts.append(f"{n_objects} auxiliary object(s) declared")
    else:
        summary_parts.append("no auxiliary objects declared")
    if violations:
        summary_parts.append(f"{len(violations)} violation(s)")
    if not enforce_block:
        summary_parts.append("ADVISORY mode (not promote-blocking)")

    return {
        "passed": passed,
        "blocking_active": enforce_block,
        "violations": violations,
        "advisory_warnings": warnings,
        "n_objects_declared": n_objects,
        "summary": "; ".join(summary_parts),
    }


# ── Self-tests ──────────────────────────────────────────────────────────


def _self_test() -> None:
    # T1: missing declaration → violation in advisory; passed still True
    r = run_auxiliary_object_gate(rubric_data={})
    assert r["passed"] is True, "advisory mode: passed should be True"
    assert any(v["type"] == "auxiliary_object_not_declared" for v in r["violations"])
    assert r["n_objects_declared"] == 0

    # T2: same in blocking mode → passed=False
    r = run_auxiliary_object_gate(rubric_data={}, enforce_block=True)
    assert r["passed"] is False
    assert r["blocking_active"] is True

    # T3: explicit no_auxiliary_object: True → no violation
    r = run_auxiliary_object_gate(rubric_data={"no_auxiliary_object": True})
    assert r["passed"] is True
    assert not any(v["type"] == "auxiliary_object_not_declared" for v in r["violations"])

    # T4: well-formed object passes
    r = run_auxiliary_object_gate(rubric_data={
        "auxiliary_objects": [
            {
                "name": "carleman_weight_phi_eps",
                "engineered_properties": ["smooth", "exponentially-bounded", "vanishing on annular boundary"],
                "comparison_target": "u_eps in regularized parabolic equation",
            },
        ],
    })
    assert r["passed"] is True
    assert not r["violations"]
    assert r["n_objects_declared"] == 1

    # T5: incomplete object → advisory violation
    r = run_auxiliary_object_gate(rubric_data={
        "auxiliary_objects": [{"name": "anonymous", "engineered_properties": [], "comparison_target": ""}],
    })
    assert any(v["type"] == "auxiliary_object_incomplete" for v in r["violations"])
    assert any(v["type"] == "engineered_properties_empty" for v in r["violations"])

    # T6: blocking mode with valid declaration passes
    r = run_auxiliary_object_gate(
        rubric_data={
            "auxiliary_objects": [
                {
                    "name": "matrix_intertwiner_psi",
                    "engineered_properties": ["bounded operator-norm", "Leray-neutral on shell"],
                    "comparison_target": "leakage tensor",
                },
            ],
        },
        enforce_block=True,
    )
    assert r["passed"] is True

    print("ALL TESTS PASSED")


if __name__ == "__main__":
    _self_test()
