"""G-PI-GROUP-FORCING — dimensional-monomial forcing / π-group analysis.

ORTHOGONAL to `buckingham_pi_gate` (which only enforces that arguments to
transcendental functions are dimensionless via an AST prune). This gate
answers a different, recurring question:

    Given a target quantity Q with a known dimension vector, and a chosen
    subset S of dimensionful constants, is Q dimensionally FORCED to a
    unique monomial of S, or does it require an independent additional
    dimensionful constant?

Canonical use (the recurring NS anti-laundering check): is a candidate
length ℓ necessarily the heat length √(νt) (forced by S={ν,t}), or is it
an independent dimensionful scale L_* not derivable from (ν,t)? Done by
hand many times; this mechanizes it, general to any scaling/criticality
argument, in-loop and out-of-loop.

Mathematical contract (MF5-corrected rank comparison)
-----------------------------------------------------
Let A be the matrix whose columns are the dimension vectors of the S
constants (rows = base dimensions), and b the dimension vector of Q.
Solve A x = b over the rationals:

  * b ∉ col(A)              (rank(A) < rank([A|b]))
        → forced=False, needs_independent_constant=True
        Q cannot be built from S at all; an independent dimensionful
        constant outside S is required.

  * b ∈ col(A) and A has TRIVIAL null space (full column rank)
        → forced=True, exponents = the unique rational solution x
        Q ≡ const · Π Sᵢ^{xᵢ} is the only dimensionally admissible monomial.

  * b ∈ col(A) and A has a NON-TRIVIAL null space
        → forced=False, needs_independent_constant=False, ambiguous=True
        Q is representable but NOT uniquely (a free π-group among S
        elements). The monomial is under-determined; an extra physical
        constraint — not a new constant — would pin it.

Exact rational arithmetic throughout (sympy). Rational exponents are
supported and returned as such (e.g. ℓ = ν^(1/2) t^(1/2)).

Usage
-----
  from ztare.gates.pi_group_forcing import run_pi_group_forcing
  res = run_pi_group_forcing(
      quantity_dim={"L": 1},                       # a length
      subset_dims={"nu": {"L": 2, "T": -1},        # kinematic viscosity
                   "t":  {"T": 1}},                # time
  )
  # res["forced"] is True, res["exponents"] == {"nu": 1/2, "t": 1/2}

Returns
-------
  {
    "gate_id": "G-PI-GROUP-FORCING",
    "forced": bool,
    "needs_independent_constant": bool,
    "ambiguous": bool,
    "exponents": dict[str, str] | None,   # constant -> rational exponent
    "monomial": str | None,               # e.g. "nu**(1/2)*t**(1/2)"
    "base_dimensions": list[str],
    "reason": str,
  }
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Mapping, Optional

GATE_ID = "G-PI-GROUP-FORCING"
GATE_NAME = "pi_group_forcing"


def _normalize_subset_dims(
    subset_dims: Mapping[str, Mapping[str, Any]] | Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    if isinstance(subset_dims, Mapping):
        return dict(subset_dims)
    if isinstance(subset_dims, Sequence) and not isinstance(subset_dims, (str, bytes)):
        return {f"x{i}": vec for i, vec in enumerate(subset_dims)}
    return {}


def _base_dims(
    quantity_dim: Mapping[str, Any],
    subset_dims: Mapping[str, Mapping[str, Any]] | Sequence[Mapping[str, Any]],
) -> list[str]:
    normalized = _normalize_subset_dims(subset_dims)
    seen: list[str] = []
    for d in quantity_dim:
        if d not in seen:
            seen.append(d)
    for vec in normalized.values():
        for d in vec:
            if d not in seen:
                seen.append(d)
    return seen


def run_pi_group_forcing(
    quantity_dim: Mapping[str, Any],
    subset_dims: Mapping[str, Mapping[str, Any]] | Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Decide whether `quantity_dim` is a forced monomial of `subset_dims`.

    `quantity_dim` / each value of `subset_dims` is a {base_dim: exponent}
    map; missing base dims are exponent 0. Exponents may be ints, floats,
    or anything `sympy.Rational`/`sympify` accepts (e.g. "1/2").
    """
    try:
        from sympy import Matrix, Rational, nsimplify, sympify
    except Exception as exc:  # pragma: no cover - env guard
        return {
            "gate_id": GATE_ID,
            "forced": False,
            "needs_independent_constant": False,
            "ambiguous": False,
            "exponents": None,
            "monomial": None,
            "base_dimensions": [],
            "reason": f"skipped: sympy unavailable ({exc})",
        }

    subset_dims = _normalize_subset_dims(subset_dims)

    if not subset_dims:
        return {
            "gate_id": GATE_ID,
            "forced": False,
            "needs_independent_constant": True,
            "ambiguous": False,
            "exponents": None,
            "monomial": None,
            "base_dimensions": _base_dims(quantity_dim, subset_dims),
            "reason": "empty subset S — nothing to force a monomial from; "
                      "an independent dimensionful constant is required",
        }

    def _r(v: Any):
        try:
            return Rational(v)
        except Exception:
            return nsimplify(sympify(v), rational=True)

    base = _base_dims(quantity_dim, subset_dims)
    names = list(subset_dims.keys())

    if not base:
        return {
            "gate_id": GATE_ID,
            "forced": False,
            "needs_independent_constant": False,
            "ambiguous": True,
            "exponents": None,
            "monomial": None,
            "base_dimensions": [],
            "reason": (
                f"target and {names} are all dimensionless. Dimensional "
                "analysis cannot force a unique monomial; a physical bound "
                "or normalization must control the dimensionless parameter"
            ),
        }

    # A: rows = base dims, cols = S constants. b: target quantity.
    A = Matrix(
        [[_r(subset_dims[n].get(d, 0)) for n in names] for d in base]
    )
    b = Matrix([[_r(quantity_dim.get(d, 0))] for d in base])

    rank_A = A.rank()
    rank_Ab = A.row_join(b).rank()

    if rank_A < rank_Ab:
        return {
            "gate_id": GATE_ID,
            "forced": False,
            "needs_independent_constant": True,
            "ambiguous": False,
            "exponents": None,
            "monomial": None,
            "base_dimensions": base,
            "reason": (
                f"target dimension is not in the column space of S "
                f"(rank A={rank_A} < rank [A|b]={rank_Ab}); it cannot be "
                f"built from {names} — an independent dimensionful "
                f"constant outside S is required"
            ),
        }

    # b ∈ col(A). Particular solution + null space of A.
    null = A.nullspace()
    if null:
        return {
            "gate_id": GATE_ID,
            "forced": False,
            "needs_independent_constant": False,
            "ambiguous": True,
            "exponents": None,
            "monomial": None,
            "base_dimensions": base,
            "reason": (
                f"target is representable from {names} but NOT uniquely: "
                f"A has a non-trivial null space (dim {len(null)}) — a free "
                f"π-group among S. The monomial is under-determined; an "
                f"extra physical constraint (not a new constant) pins it"
            ),
        }

    # Full column rank ⇒ unique solution. Use least-squares-free exact solve.
    sol = A.solve(b)  # exact; A has full column rank and b ∈ col(A)
    exponents = {names[i]: sol[i, 0] for i in range(len(names))}
    monomial = "*".join(
        f"{n}**({exponents[n]})" for n in names if exponents[n] != 0
    ) or "1"
    return {
        "gate_id": GATE_ID,
        "forced": True,
        "needs_independent_constant": False,
        "ambiguous": False,
        "exponents": {n: str(exponents[n]) for n in names},
        "monomial": monomial,
        "base_dimensions": base,
        "reason": (
            f"target dimension is uniquely forced: it is the only "
            f"dimensionally admissible monomial of {names} "
            f"(A full column rank, b ∈ col(A))"
        ),
    }


def format_forcing_report(result: dict[str, Any]) -> str:
    """Human/agent-facing one-screen verdict."""
    if result.get("reason", "").startswith("skipped:"):
        return f"π-group forcing skipped — {result['reason']}"
    if result.get("forced"):
        return (
            "✓ DIMENSIONALLY FORCED — the target is the unique admissible "
            f"monomial: {result['monomial']}. Exponents: "
            f"{result['exponents']}. A candidate of this dimension built "
            "only from S carries NO independent content (anti-laundering: "
            "it is that monomial in disguise)."
        )
    if result.get("needs_independent_constant"):
        return (
            "✗ NOT FORCED — needs an independent dimensionful constant. "
            f"{result['reason']}. A quantity of this dimension is a genuine "
            "new scale, not derivable from S."
        )
    return (
        "~ AMBIGUOUS — representable but not unique (free π-group). "
        f"{result['reason']}."
    )
