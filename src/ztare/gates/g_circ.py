"""G-CIRC structural — 3-part Lagrangian-smuggling detector.

Upgrades the legacy `circularity_gate.py` (DAG-cycle detector) with three
structural checks against the *adversarial Lagrangian smuggling* class
the SR-skeptic panel surfaced on gp163d.

Threat model
------------
A mutator that has seen a verified Sacred-DNA bridge form (e.g. the
gp163d Galaxy-Cluster Bridge with its sigmoid centers 11.43 / 1.83 / 0.62
and its (log_c0, log_eta) parameters) can satisfy the
`successor_lock` requirement *and* claim a "first-principles derivation"
by:

  1. Declaring an auxiliary scalar field φ via a Lagrangian L(φ, ∂φ).
  2. Choosing V(φ) so that the Euler-Lagrange (EL) equation has an
     algebraic solution φ(M, r) which, substituted into the proposed
     PARAMETRIC_FORM, reproduces the bridge form.
  3. Citing the EL substitution as "derivation in three steps" with no
     numeric leakage that the legacy string-match G-CIRC would catch.

The legacy gate at `src/ztare/gates/circularity_gate.py` only catches
DAG-level circularity (cycles in the claim graph). It cannot see the
Lagrangian smuggle because (a) numeric constants are renamed, (b) the
target function name (`c_eff`, `bridge`, etc.) is replaced by `V`, and
(c) the prose graph is genuinely acyclic — the circularity is in the
algebra, not the argument structure.

This module implements three structural checks; any one rejects the
candidate.

Check 1 — AST function-symbol scan
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Parse PARAMETRIC_FORM with sympy.sympify (using the
`extract_parametric_form_from_source` helper from
`src/ztare/orchestrator/forced_reframe.py` to pull the literal first).
Reject if any free `Function` symbol — or any sympy `Symbol` introduced
via Lagrangian declaration — has a name matching a verified-axiom target
(e.g. `c_eff`, `bridge`, `g_dagger`).

Check 2 — Numeric-literal vs Sacred-DNA scan
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Pull every numeric literal from the candidate's PARAMETRIC_FORM via AST.
Read `<project_dir>/verified_axioms.json` for axioms with
`successor_lock.active=True`. Build a Sacred-DNA constant table from each
axiom's `parameters` block plus any numeric literals visible inside the
`parametric_form` string. Reject if any candidate literal matches a
Sacred-DNA constant within 1% relative tolerance (or within 1e-6 absolute
when the constant is near zero).

Check 3 — On-shell substitution audit  (load-bearing)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
When the candidate declares an auxiliary field φ via a Lagrangian-style
proposal, solve the EL equation for φ symbolically (or accept the
mutator's claimed ON_SHELL_PHI_SOLUTION block), then substitute back
into the proposed PARAMETRIC_FORM. If the resulting expression has the
SAME AST bucket as the Sacred-DNA bridge form (per
`parametric_form_ast_bucket` in `forced_reframe.py`), the auxiliary
field has no nontrivial dynamics and the "derivation" is tautological.
Reject.

Engagement / opt-in
-------------------
The module exports a `can_handle` predicate that is True when
`rubric.enable_g_circ_structural=True`. Default is False, in which case
this gate is a no-op and the legacy DAG-cycle G-CIRC continues to do its
job. `gp163d`'s rubric will opt in once the SR-skeptic panel signs off.

Verdict shape
-------------
Returns the same dict shape as existing gates::

    {
        "name": "g_circ_structural",
        "flagged": bool,         # True iff any of the 3 checks rejects
        "passed": bool,          # negation of flagged for legacy consumers
        "rule": "ast_symbol" | "sacred_dna_literal" |
                "onshell_tautology" | "no_axioms" | "ok",
        "evidence": {...},
        "severity": "hard_fail" | "soft_warn",
        "source": "g_circ_structural",
    }

Substrate-agnostic
------------------
No gp163d-specific axiom IDs are hardcoded. Every Sacred-DNA constant is
read at runtime from `verified_axioms.json`. Missing file ⇒ no-op (not a
hard fail) — preserves backward compat for substrates that have not yet
verified an axiom.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any, Optional

from src.ztare.orchestrator.forced_reframe import (
    extract_parametric_form_from_source,
    parametric_form_ast_bucket,
)


GATE_ID = "g_circ_structural"
RUBRIC_FLAG = "enable_g_circ_structural"
SACRED_DNA_REL_TOL = 0.01      # 1% relative tolerance
SACRED_DNA_ABS_TOL = 1e-6      # absolute tolerance for near-zero
NUMERIC_LITERAL_FLOOR = 1e-12  # ignore literals smaller than this (e.g. 1e-300 epsilons)

# Structural / banal constants that appear in countless legitimate forms
# and therefore must NOT be treated as Sacred-DNA leakage even when the
# axiom's parametric_form happens to contain them. These are skeletal
# exponents (0.5, 2.0, the bridge's (1+...)^(1/eta) scaffold) and not
# load-bearing fitted parameters. Distinguish by source: only the values
# in the axiom's `parameters` block plus the SIGMOID_CENTERS heuristic
# (any literal not in this set with magnitude > 1.0) are load-bearing.
BANAL_CONSTANTS: frozenset[float] = frozenset({
    0.0, 1.0, -1.0, 0.5, -0.5, 2.0, -2.0, 1e-300,
})


# Names that indicate the mutator is naming the verified-axiom target
# directly (Check 1). Any of these as a sympy Function symbol or as a
# free Name bound by the Lagrangian declaration is a hard reject.
SACRED_TARGET_NAMES: frozenset[str] = frozenset({
    "bridge", "Bridge",
    "c_eff", "ceff", "C_eff",
    "g_dagger", "gdagger", "g_dag", "gDagger",
    "a0", "a_0",
    "M_dyn_over_M_bar", "Mdyn_over_Mbar",
})


# ---------------------------------------------------------------------------
# Check helpers
# ---------------------------------------------------------------------------


def _load_active_axioms(project_dir: Path) -> list[dict[str, Any]]:
    """Read project_dir/verified_axioms.json and return axioms whose
    successor_lock.active is True. Missing / malformed file → []."""
    path = project_dir / "verified_axioms.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    axioms = data.get("axioms", []) or []
    active: list[dict[str, Any]] = []
    for ax in axioms:
        if not isinstance(ax, dict):
            continue
        lock = ax.get("successor_lock") or {}
        if isinstance(lock, dict) and lock.get("active") is True:
            active.append(ax)
    return active


def _extract_numeric_literals(form_str: str) -> list[float]:
    """Walk the AST of a PARAMETRIC_FORM expression and return every
    numeric literal (int / float). Negative literals are captured via
    UnaryOp(USub, Constant). Booleans are skipped."""
    if not form_str:
        return []
    # Wrap in a parenthesised expression so multi-line concatenation works
    try:
        tree = ast.parse(form_str, mode="eval")
    except SyntaxError:
        return []
    literals: list[float] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
                and not isinstance(node.value, bool):
            literals.append(float(node.value))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) \
                and isinstance(node.operand, ast.Constant) \
                and isinstance(node.operand.value, (int, float)) \
                and not isinstance(node.operand.value, bool):
            literals.append(-float(node.operand.value))
    return literals


_NUM_PATTERN = re.compile(
    r"-?\d+\.\d+(?:[eE][-+]?\d+)?|-?\d+(?:[eE][-+]?\d+)?"
)


def _extract_numeric_literals_from_text(text: str) -> list[float]:
    """Best-effort numeric scan of an arbitrary text blob (for sweeping
    literals out of a verified-axiom `parametric_form` string)."""
    out: list[float] = []
    if not text:
        return out
    for m in _NUM_PATTERN.findall(text):
        try:
            v = float(m)
        except ValueError:
            continue
        if abs(v) >= NUMERIC_LITERAL_FLOOR:
            out.append(v)
    return out


def _build_sacred_dna_constants(axioms: list[dict[str, Any]]) -> list[tuple[float, str]]:
    """Build a flat list of (value, provenance_string) Sacred-DNA constants
    from the active axioms. Pulls from each axiom's `parameters` dict and
    from numeric literals that appear inside `parametric_form` (the
    sigmoid centers etc.).
    """
    out: list[tuple[float, str]] = []
    for ax in axioms:
        ax_id = ax.get("axiom_id", "?")
        params = ax.get("parameters") or {}
        if isinstance(params, dict):
            for k, v in params.items():
                try:
                    fv = float(v)
                except (TypeError, ValueError):
                    continue
                if abs(fv) >= NUMERIC_LITERAL_FLOOR:
                    out.append((fv, f"{ax_id}.parameters.{k}"))
        pf = ax.get("parametric_form") or ""
        for lit in _extract_numeric_literals_from_text(pf):
            out.append((lit, f"{ax_id}.parametric_form_literal"))
    return out


def _matches_sacred_dna(
    candidate_lit: float,
    sacred: list[tuple[float, str]],
) -> Optional[tuple[float, str]]:
    """Return the first Sacred-DNA constant the candidate literal matches
    (within 1% relative or 1e-6 absolute), or None."""
    for value, prov in sacred:
        if abs(value) < SACRED_DNA_ABS_TOL:
            if abs(candidate_lit - value) <= SACRED_DNA_ABS_TOL:
                return value, prov
        else:
            rel = abs(candidate_lit - value) / abs(value)
            if rel <= SACRED_DNA_REL_TOL:
                return value, prov
    return None


def _scan_ast_function_symbols(form_str: str) -> list[str]:
    """Return AST `Name` identifiers used as call targets (i.e.
    `name(...)` — the function-symbol surface) plus any free `Name` use
    in the expression. We collect both because a Lagrangian-style
    declaration may bind `c_eff` as a *symbol* (free name) rather than
    a callable."""
    if not form_str:
        return []
    try:
        tree = ast.parse(form_str, mode="eval")
    except SyntaxError:
        return []
    seen: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                seen.add(f.id)
            elif isinstance(f, ast.Attribute):
                seen.add(f.attr)
        elif isinstance(node, ast.Name):
            seen.add(node.id)
    return sorted(seen)


# ---------------------------------------------------------------------------
# Check 3: on-shell substitution
# ---------------------------------------------------------------------------


def _maybe_solve_euler_lagrange(
    lagrangian_text: str,
    aux_field_name: str = "phi",
) -> Optional[str]:
    """Best-effort: solve the EL equation ∂L/∂φ = 0 for the aux field.

    For algebraic Lagrangians (no derivative terms), EL reduces to
    ∂L/∂φ = 0 — a closed-form algebraic solution exists. For Lagrangians
    with a kinetic term, EL is a differential equation; we don't attempt
    to solve those here. The mutator may also pre-supply the solution
    via an `ON_SHELL_PHI_SOLUTION` literal which the caller passes
    directly to `_substitute_phi`.

    Returns the solution as a sympy expression string, or None if EL
    is non-trivial / unsolvable in closed form.
    """
    if not lagrangian_text:
        return None
    try:
        import sympy as sp
    except ImportError:
        return None
    # Reject anything with a derivative — kinetic terms make EL a PDE
    # which we will not solve algebraically.
    if "Derivative" in lagrangian_text or "diff(" in lagrangian_text:
        return None
    try:
        # Parse with the aux field as a Symbol
        local_dict: dict[str, Any] = {aux_field_name: sp.Symbol(aux_field_name)}
        L = sp.sympify(lagrangian_text, locals=local_dict)
        phi = local_dict[aux_field_name]
        eq = sp.diff(L, phi)
        sols = sp.solve(eq, phi)
    except Exception:
        return None
    if not sols:
        return None
    # Pick the first real-valued solution
    for s in sols:
        if not s.has(sp.I):
            return str(s)
    return str(sols[0])


def _substitute_phi(
    parametric_form: str,
    phi_solution: str,
    aux_field_name: str = "phi",
) -> Optional[str]:
    """Substitute the on-shell φ into the parametric form. Returns the
    simplified expression as a string, or None on failure."""
    if not parametric_form or not phi_solution:
        return None
    try:
        import sympy as sp
    except ImportError:
        return None
    try:
        sym = sp.Symbol(aux_field_name)
        sol = sp.sympify(phi_solution)
        # PARAMETRIC_FORM uses subscripted features['x'] etc — sympify
        # cannot parse subscripts. Fall back to a naive textual substitute.
        if "[" in parametric_form:
            substituted = parametric_form.replace(aux_field_name, f"({phi_solution})")
            return substituted
        expr = sp.sympify(parametric_form, locals={aux_field_name: sym})
        sub = sp.simplify(expr.subs(sym, sol))
        return str(sub)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def evaluate_g_circ_structural(
    *,
    project_dir: Path | str,
    parametric_form: Optional[str] = None,
    submission_source: Optional[str] = None,
    lagrangian_text: Optional[str] = None,
    on_shell_phi_solution: Optional[str] = None,
    aux_field_name: str = "phi",
    rubric_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Run the 3-part structural G-CIRC check.

    Parameters
    ----------
    project_dir : Path | str
        Project directory (where `verified_axioms.json` lives).
    parametric_form : str, optional
        The candidate's PARAMETRIC_FORM string. If None, falls back to
        extracting from `submission_source` via
        `extract_parametric_form_from_source`.
    submission_source : str, optional
        Raw test_model.py source. Used to extract PARAMETRIC_FORM when
        the caller did not pre-extract.
    lagrangian_text : str, optional
        The candidate's auxiliary-field Lagrangian (algebraic part). If
        present and parseable, Check 3 attempts EL→solve→substitute.
    on_shell_phi_solution : str, optional
        Mutator-supplied closed-form φ(M, r). Bypasses _maybe_solve_EL.
    aux_field_name : str
        The auxiliary field's symbol name in the Lagrangian. Default
        "phi".
    rubric_data : dict, optional
        The rubric. Used only to read `enable_g_circ_structural`. If
        the flag is False/absent, the gate is a no-op (legacy behavior).

    Returns
    -------
    dict
        Verdict shape consistent with existing gates.
    """
    pdir = Path(project_dir)
    rubric_data = rubric_data or {}

    # Backward compat: opt-in flag. Default False ⇒ legacy behavior
    # (legacy DAG-cycle G-CIRC continues to fire from circularity_gate.py).
    if not bool(rubric_data.get(RUBRIC_FLAG, False)):
        return _verdict(
            flagged=False,
            rule="disabled",
            evidence={"reason": f"rubric.{RUBRIC_FLAG} not set; structural G-CIRC is a no-op"},
            severity="soft_warn",
        )

    # Resolve PARAMETRIC_FORM
    if not parametric_form and submission_source:
        parametric_form = extract_parametric_form_from_source(submission_source) or ""
    parametric_form = parametric_form or ""

    # Load active axioms
    axioms = _load_active_axioms(pdir)
    if not axioms:
        return _verdict(
            flagged=False,
            rule="no_axioms",
            evidence={
                "reason": "no verified_axioms.json with successor_lock.active=True; "
                          "structural G-CIRC has no Sacred-DNA to compare against",
                "project_dir": str(pdir),
            },
            severity="soft_warn",
        )

    # ── Check 1: AST function-symbol scan ────────────────────────────
    symbols = _scan_ast_function_symbols(parametric_form)
    # Also scan the Lagrangian text if the mutator declared one — the
    # smuggle target may live there even when it does not appear in the
    # final PARAMETRIC_FORM.
    lag_symbols = _scan_ast_function_symbols(lagrangian_text or "")
    all_symbols = set(symbols) | set(lag_symbols)
    matches = sorted(all_symbols & SACRED_TARGET_NAMES)
    if matches:
        return _verdict(
            flagged=True,
            rule="ast_symbol",
            evidence={
                "matched_symbols": matches,
                "scanned_form_symbols": symbols,
                "scanned_lagrangian_symbols": lag_symbols,
                "sacred_target_set": sorted(SACRED_TARGET_NAMES),
                "explanation": (
                    "Candidate PARAMETRIC_FORM (or auxiliary Lagrangian) names "
                    "the verified-axiom target directly. Independent derivation "
                    "must not refer to the target by its Sacred-DNA name."
                ),
            },
            severity="hard_fail",
        )

    # ── Check 2: Sacred-DNA literal scan ─────────────────────────────
    candidate_lits = _extract_numeric_literals(parametric_form)
    sacred = _build_sacred_dna_constants(axioms)
    leaks: list[dict[str, Any]] = []
    for lit in candidate_lits:
        if abs(lit) < NUMERIC_LITERAL_FLOOR:
            continue
        # Skip banal structural constants (0, ±1, ±½, ±2) — they appear
        # in countless legitimate forms and the axiom's bridge form
        # contains them as skeletal scaffolding, not load-bearing fits.
        if any(abs(lit - bc) < 1e-9 for bc in BANAL_CONSTANTS):
            continue
        # Skip the universal log10-conversion ln(10) ≈ 2.3026 — it
        # appears in both the bridge form and many independent forms.
        if abs(lit - 2.302585092994046) < 1e-6:
            continue
        match = _matches_sacred_dna(lit, sacred)
        if match is not None:
            value, prov = match
            # Likewise filter out matches against banal-valued sacred
            # entries — even if the axiom's parameters dict happens to
            # contain a 1.0 or 0.5, that is not load-bearing leakage.
            if any(abs(value - bc) < 1e-9 for bc in BANAL_CONSTANTS):
                continue
            leaks.append({
                "candidate_literal": lit,
                "sacred_dna_value": value,
                "provenance": prov,
                "rel_tol_used": SACRED_DNA_REL_TOL,
            })
    if leaks:
        return _verdict(
            flagged=True,
            rule="sacred_dna_literal",
            evidence={
                "leaks": leaks,
                "explanation": (
                    "Candidate PARAMETRIC_FORM contains numeric literal(s) within "
                    "1% relative tolerance of a Sacred-DNA constant from the "
                    "verified-axiom block. This is the canonical 'smuggle the "
                    "sigmoid centers via V(φ)' pattern."
                ),
            },
            severity="hard_fail",
        )

    # ── Check 3: on-shell substitution audit ─────────────────────────
    if lagrangian_text or on_shell_phi_solution:
        phi_sol = on_shell_phi_solution or _maybe_solve_euler_lagrange(
            lagrangian_text or "", aux_field_name=aux_field_name,
        )
        if phi_sol is not None and parametric_form:
            substituted = _substitute_phi(
                parametric_form, phi_sol, aux_field_name=aux_field_name,
            )
            if substituted is not None:
                # Compare AST bucket of substituted form vs each axiom's form
                cand_bucket = parametric_form_ast_bucket(substituted)
                for ax in axioms:
                    ax_form = ax.get("parametric_form") or ""
                    if not ax_form:
                        continue
                    sacred_bucket = parametric_form_ast_bucket(ax_form)
                    if cand_bucket == sacred_bucket and cand_bucket not in (
                            "empty", "syntax_error"):
                        return _verdict(
                            flagged=True,
                            rule="onshell_tautology",
                            evidence={
                                "substituted_form_preview": substituted[:240],
                                "candidate_ast_bucket": cand_bucket,
                                "sacred_ast_bucket": sacred_bucket,
                                "axiom_id": ax.get("axiom_id"),
                                "phi_solution": phi_sol,
                                "explanation": (
                                    "After substituting the on-shell φ into the "
                                    "candidate PARAMETRIC_FORM, the resulting "
                                    "expression has the same AST shape as the "
                                    "Sacred-DNA bridge form. The auxiliary field "
                                    "has no nontrivial dynamics; the 'derivation' "
                                    "is tautological."
                                ),
                            },
                            severity="hard_fail",
                        )

    # ── All three checks passed ──────────────────────────────────────
    return _verdict(
        flagged=False,
        rule="ok",
        evidence={
            "scanned_form_symbols": symbols,
            "candidate_literal_count": len(candidate_lits),
            "sacred_dna_constants_checked": len(sacred),
            "checks_run": [
                "ast_symbol",
                "sacred_dna_literal",
                "onshell_tautology" if (lagrangian_text or on_shell_phi_solution) else "onshell_skipped",
            ],
        },
        severity="soft_warn",
    )


def _verdict(
    *,
    flagged: bool,
    rule: str,
    evidence: dict[str, Any],
    severity: str,
) -> dict[str, Any]:
    return {
        "name": GATE_ID,
        "flagged": bool(flagged),
        "passed": not bool(flagged),
        "rule": rule,
        "evidence": evidence,
        "severity": severity,
        "source": GATE_ID,
    }


# ---------------------------------------------------------------------------
# Cage adapter (engagement predicate + run callback)
# ---------------------------------------------------------------------------


def can_handle(substrate: Any, candidate: Any) -> tuple[bool, str]:
    """Cage `can_handle` predicate.

    Engages when the rubric flag `enable_g_circ_structural` is True.
    The flag is read from `substrate.rubric_data` if present, else from
    `candidate.rubric_data`. Default False ⇒ disengage so the legacy
    DAG-cycle G-CIRC remains the sole circularity defense.
    """
    rubric_data = (
        getattr(substrate, "rubric_data", None)
        or getattr(candidate, "rubric_data", None)
        or {}
    )
    if not isinstance(rubric_data, dict):
        return False, "rubric_data not a dict; structural G-CIRC disengaged"
    if bool(rubric_data.get(RUBRIC_FLAG, False)):
        return True, f"rubric.{RUBRIC_FLAG}=True"
    return False, f"rubric.{RUBRIC_FLAG} not set; structural G-CIRC disengaged (legacy DAG G-CIRC still fires)"


def run_gate(substrate: Any, candidate: Any) -> dict[str, Any]:
    """Cage `run` callback.

    Pulls project_dir, parametric_form, lagrangian_text, and
    on_shell_phi_solution off the substrate / candidate objects when
    available, then delegates to `evaluate_g_circ_structural`.
    """
    project_dir = (
        getattr(candidate, "project_dir", None)
        or getattr(substrate, "project_dir", None)
        or Path(".")
    )
    parametric_form = getattr(candidate, "parametric_form", None)
    submission_source = getattr(candidate, "submission_source", None)
    lagrangian_text = getattr(candidate, "lagrangian_text", None)
    on_shell_phi_solution = getattr(candidate, "on_shell_phi_solution", None)
    rubric_data = (
        getattr(substrate, "rubric_data", None)
        or getattr(candidate, "rubric_data", None)
        or {}
    )
    return evaluate_g_circ_structural(
        project_dir=project_dir,
        parametric_form=parametric_form,
        submission_source=submission_source,
        lagrangian_text=lagrangian_text,
        on_shell_phi_solution=on_shell_phi_solution,
        rubric_data=rubric_data,
    )
