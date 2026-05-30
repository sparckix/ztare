"""G-LAGRANGIAN-NONTRIVIAL — reject Lagrangians whose static
Euler-Lagrange equation collapses to `q = single_background_var`.

Catches the iter-2 false-positive class (run 1777381378, 2026-04-28):
the mutator declared a free harmonic oscillator centered at a
background variable (e.g., `L = (1/2)q̇² − (1/2)(q − rho_local_log10)²`)
whose static E-L is `q = rho_local_log10` — a no-op substitution. The
PREDICTION expression contains all the structural physics, written by
the LLM. There is no derivation content; the Lagrangian is cosmetic.

A real chameleon Lagrangian has a *non-trivial potential* V(φ) (e.g.,
Ratra-Peebles M⁵/φ, exponential V(φ) = M⁴·exp(−βφ/M_Pl), polynomial
(1/2)m²φ² + (1/4)λφ⁴) so the static E-L has a real algebraic solution
that is NOT a single-background substitution. This gate enforces that
distinction structurally.

GP-183 Phase B1.

Verdict semantics:
  - "ok"          steady state references ≥2 background symbols, OR
                  references one background through a non-identity
                  function (sqrt, exp, log, polynomial, ratio, ...).
  - "trivial"     steady state is exactly `q = single_background_var`
                  with no transformation. The Lagrangian provides no
                  derivation content beyond syntactic substitution.
  - "params_only" steady state is a function of params only (no
                  features) — derivation didn't engage with the
                  substrate; treat as informational, not a hard fail.

Caller behavior:
  - "ok"          pass
  - "trivial"     cap at rubric.cap_for_trivial_lagrangian (default 60)
                  with reason `lagrangian_trivially_substituted`
  - "params_only" cap at rubric.cap_for_params_only_lagrangian (default
                  none — informational only, surfaced to briefing)
"""
from __future__ import annotations

import ast
import re
from typing import Any

GATE_ID = "G-LAGRANGIAN-NONTRIVIAL"


def _parse_steady_state_rhs(rhs_str: str) -> ast.AST | None:
    """Parse the steady-state RHS into an AST. Returns None on failure."""
    if not isinstance(rhs_str, str) or not rhs_str.strip():
        return None
    try:
        return ast.parse(rhs_str, mode="eval").body
    except SyntaxError:
        return None


def _is_single_bare_name(node: ast.AST) -> str | None:
    """If `node` is a single `ast.Name`, return that name; else None.

    `q = rho_local_log10` parses to ast.Name(id='rho_local_log10').
    `q = sqrt(rho_local_log10)` parses to ast.Call (NOT a single name).
    `q = features['rho']` parses to ast.Subscript (NOT a single name).
    """
    if isinstance(node, ast.Name):
        return node.id
    return None


def _collect_referenced_names(node: ast.AST) -> set[str]:
    """Walk the AST and return the set of bare-name references (not
    function names, not param subscripts). Used to count distinct
    background variables in compositional steady states."""
    out: set[str] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name):
            out.add(sub.id)
        elif isinstance(sub, ast.Subscript):
            # Skip features['k'] / params['k'] subscript heads
            continue
    return out


def evaluate_lagrangian_nontriviality(
    steady_state: dict[str, str] | None,
    *,
    background_symbols: list[str] | None = None,
    param_symbols: list[str] | None = None,
) -> dict:
    """Inspect the steady-state output of GP-180 and classify the
    Lagrangian's derivation content.

    Args:
      steady_state: the dict GP-180 returns under `steady_state`,
        e.g. `{"q": "rho_local_log10"}` or `{"q": "L_ang**2/(G*M)"}`.
      background_symbols: optional list of declared background names
        (used for "params_only" detection).
      param_symbols: optional list of declared param names.

    Returns:
      {
        "gate_id": "G-LAGRANGIAN-NONTRIVIAL",
        "verdict": "ok" | "trivial" | "params_only" | "unparseable" | "no_steady_state",
        "reason": <human-readable diagnosis>,
        "steady_state_rhs": <input string, for audit>,
        "referenced_names": [<bare names found>],
      }
    """
    if not steady_state:
        return {
            "gate_id": GATE_ID, "verdict": "no_steady_state",
            "reason": "GP-180 produced no steady-state result; cannot classify.",
            "steady_state_rhs": None, "referenced_names": [],
        }

    background_symbols = background_symbols or []
    param_symbols = param_symbols or []

    # The MVP supports a single dynamical field `q`. Take its RHS.
    if "q" in steady_state:
        rhs_str = steady_state["q"]
    else:
        rhs_str = next(iter(steady_state.values()))

    # Strip artifact prefixes the substitution helper might emit
    # (e.g., `features['x']`-style subscripts). Steady state from
    # sympy is typically bare-name math.
    tree = _parse_steady_state_rhs(str(rhs_str))
    if tree is None:
        return {
            "gate_id": GATE_ID, "verdict": "unparseable",
            "reason": f"steady-state RHS could not be parsed: {rhs_str!r}",
            "steady_state_rhs": str(rhs_str), "referenced_names": [],
        }

    # Hard rejection: bare single-name RHS that matches a background symbol.
    sole_name = _is_single_bare_name(tree)
    if sole_name is not None:
        if sole_name in background_symbols or _looks_like_substrate_feature(sole_name):
            return {
                "gate_id": GATE_ID, "verdict": "trivial",
                "reason": (
                    f"steady-state q = {sole_name!r} is a single-background "
                    f"substitution. The declared Lagrangian collapses to "
                    f"q = feature; the derivation is cosmetic and provides "
                    f"no structural content beyond what PREDICTION already "
                    f"contains. A real Lagrangian must have a non-trivial "
                    f"potential V(φ) (Ratra-Peebles M⁵/φ, exponential "
                    f"V(φ)=M⁴·exp(-βφ/M_Pl), polynomial (1/2)m²φ²+(1/4)λφ⁴) "
                    f"so the static E-L has a real algebraic solution that "
                    f"is NOT a single-background substitution."
                ),
                "steady_state_rhs": str(rhs_str), "referenced_names": [sole_name],
            }

    # Walk the AST, count distinct background references.
    refs = _collect_referenced_names(tree)
    bg_refs = {n for n in refs if n in background_symbols or _looks_like_substrate_feature(n)}
    param_refs = {n for n in refs if n in param_symbols}

    # If the RHS references only params (no features), the derivation
    # didn't engage with the substrate. Informational, not a hard fail.
    if not bg_refs and param_refs:
        return {
            "gate_id": GATE_ID, "verdict": "params_only",
            "reason": (
                f"steady-state q = f({sorted(param_refs)}) references only "
                f"declared params, no substrate features. The Lagrangian "
                f"derivation produces a parameter-only equilibrium that "
                f"does not couple to substrate variables. Often happens "
                f"when the L is fully self-contained (e.g. simple harmonic "
                f"oscillator with no source term)."
            ),
            "steady_state_rhs": str(rhs_str), "referenced_names": sorted(refs),
        }

    # If the RHS is a non-trivial composition of one or more features
    # (with or without params), the Lagrangian has derivation content.
    return {
        "gate_id": GATE_ID, "verdict": "ok",
        "reason": (
            f"steady-state q is a non-trivial function of {len(bg_refs)} "
            f"background feature(s) {sorted(bg_refs)}"
            + (f" and {len(param_refs)} param(s) {sorted(param_refs)}" if param_refs else "")
            + ". The Lagrangian's static E-L produces real algebraic "
            "structure beyond single-symbol substitution."
        ),
        "steady_state_rhs": str(rhs_str), "referenced_names": sorted(refs),
    }


# Heuristic for substrate-feature names: the gate may receive a
# steady_state that came from a sympy derivation where background
# symbols were declared inline (e.g., `rho_local_log10`, `mass_log10`).
# These look like substrate-canonical feature keys.
_FEATURE_NAME_HEURISTIC = re.compile(
    r"^(x|y|sigma|mass(_log10)?|radius(_log10)?|rho(_local)?(_log10)?|"
    r"M(_gas)?(_log10)?|gas_fraction|SBdisk(_log10)?|temperature|velocity|"
    r"redshift|distance|luminosity|metallicity)$"
)


def _looks_like_substrate_feature(name: str) -> bool:
    """Heuristic for whether a bare name is a substrate feature."""
    return bool(_FEATURE_NAME_HEURISTIC.match(name))
