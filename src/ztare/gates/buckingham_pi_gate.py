"""G-BUCKINGHAM-PI — dimensional analysis gate for PARAMETRIC_FORM.

Enforces that arguments to transcendental functions (exp, log, tanh, sin,
cos, asinh, atan, sigmoid, erf, softplus, etc.) are dimensionless. This is
the Buckingham π theorem operationalized as a structural prune: the universe
does not call `tanh()` on a dimensional quantity, so neither should the
mutator.

Apparatus-general design: the gate consumes a per-substrate
`dimensional_features` dict from rubric_data when present; falls back to a
heuristic that treats every `*_log10`, `*_dex`, `*_ratio`, `gas_fraction`,
`*_count` key as dimensionless and `x` / `sigma` (the canonical g_bar and
its uncertainty) as dimensionful.

Detection rule for a transcendental call `T(arg)`:
  - If `arg` references ANY dimensionful feature/expression unmediated by a
    dividing dimensional constant, fail with "raw dimensional quantity
    inside <T>" — e.g., `exp(features['x'])` is rejected.
  - If `arg` references only dimensionless features and bare params, pass.
  - If `arg` is `features['x'] / divisor` or `features['x'] * params['log_*']
    (in log-space)` style, pass — these are the canonical dimensionless ratio
    patterns.

The gate does NOT validate parameter dimensions (params are
mutator-declared; we trust the naming convention via `log_*` / `raw_*` /
amp_*` etc.). It catches the decision-critical violation: dimensionful feature
quantities used directly inside transcendentals.

Usage
-----
  from src.ztare.gates.buckingham_pi_gate import run_buckingham_pi_gate
  result = run_buckingham_pi_gate(parametric_form, rubric_data=rubric)
  if not result["passed"]:
      # treat as R1 strike with structural feedback
      ...

Returns:
  {
    "passed": bool,
    "violations": list[{"function": str, "arg": str, "reason": str, ...}],
    "features_used": list[str],
    "scanned_calls": int,
    "gate_id": "G-BUCKINGHAM-PI",
  }
"""
from __future__ import annotations

import ast
from typing import Any, Optional

GATE_ID = "G-BUCKINGHAM-PI"
GATE_NAME = "buckingham_pi_gate"

# Functions whose argument MUST be dimensionless. The output is naturally
# dimensionless or — for log/log10 — has dimensionless argument.
TRANSCENDENTAL_FUNCS: frozenset[str] = frozenset({
    "exp", "log", "log10", "log2", "ln",
    "sin", "cos", "tan",
    "asin", "acos", "atan", "arctan",
    "sinh", "cosh", "tanh",
    "asinh", "acosh", "atanh",
    "sigmoid", "softplus", "erf", "erfc",
})

# Default per-substrate feature classification. Overridable via
# rubric_data["dimensional_features"] = {"x": "acceleration", "sigma": "acceleration", ...}
# Any feature key NOT in dimensional_features is assumed dimensionless.
_DEFAULT_DIMENSIONFUL_FEATURES: frozenset[str] = frozenset({"x", "sigma"})


def _classify_feature(key: str, dimensional_features: dict[str, str]) -> str:
    """Return 'dimensionless' or the named dimension."""
    if key in dimensional_features:
        return dimensional_features[key]
    # Heuristic fallback: log10/dex/ratio/fraction/uncertainty keys are dimensionless.
    kl = key.lower()
    for tag in ("_log10", "_dex", "_ratio", "_fraction", "_count", "_uncertainty"):
        if tag in kl:
            return "dimensionless"
    if kl in {"id", "system_class", "system_id", "row_id"}:
        return "dimensionless"
    if kl.endswith("_source") or kl.endswith("_tag"):
        return "dimensionless"
    if kl in {"x", "y", "g_bar", "g_obs", "sigma", "mass", "radius", "velocity"}:
        return "acceleration" if kl in {"x", "y", "g_bar", "g_obs", "sigma"} else "unknown"
    return "dimensionless"  # default lenient: unknown keys treated as dimensionless


# Logarithm-family functions that ABSORB dimensions in physics convention:
# `log10(x_meters)` is shorthand for `log10(x_meters / 1m)`. We treat
# features appearing inside log/log10/ln as dimension-stripped for the
# purposes of the upstream transcendental's argument check. (Without this
# exemption, the gate falsely flags every multi-decade logarithmic feature
# as a dimensional violation — see audit H1/H2, 2026-04-28.)
_LOG_FUNCS_DIMENSION_STRIPPING: frozenset[str] = frozenset({"log", "log10", "log2", "ln"})


def _is_inside_log(node: ast.AST, parents: dict[int, ast.AST]) -> bool:
    """Walk parents to check if `node` lives inside a log/log10/ln call."""
    cur = node
    while True:
        par = parents.get(id(cur))
        if par is None:
            return False
        if isinstance(par, ast.Call):
            fn = None
            if isinstance(par.func, ast.Name):
                fn = par.func.id
            elif isinstance(par.func, ast.Attribute):
                fn = par.func.attr
            if fn and fn.lower() in _LOG_FUNCS_DIMENSION_STRIPPING:
                return True
        cur = par


def _collect_features_in_subtree(node: ast.AST, *, exempt_inside_log: bool = False) -> list[str]:
    """Return feature keys (`features['<key>']`) referenced in subtree.

    When `exempt_inside_log=True`, features that appear inside a
    log/log10/ln call are filtered out — they've been dimension-stripped
    by the log convention and don't count for the upstream transcendental's
    argument check.
    """
    if exempt_inside_log:
        # Build parent map for log-ancestry lookup
        parents: dict[int, ast.AST] = {}
        for parent in ast.walk(node):
            for child in ast.iter_child_nodes(parent):
                parents[id(child)] = parent
        out: list[str] = []
        for sub in ast.walk(node):
            if isinstance(sub, ast.Subscript):
                value = sub.value
                sl = sub.slice
                if isinstance(value, ast.Name) and value.id == "features":
                    if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                        if not _is_inside_log(sub, parents):
                            out.append(sl.value)
        return out
    out: list[str] = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Subscript):
            value = sub.value
            sl = sub.slice
            if isinstance(value, ast.Name) and value.id == "features":
                if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                    out.append(sl.value)
    return out


def _arg_is_dimensionally_safe(
    arg: ast.AST,
    dimensional_features: dict[str, str],
) -> tuple[bool, str]:
    """Check whether arg is dimensionless.

    Strategy: collect all features referenced in the subtree. If ALL are
    dimensionless, pass. If ANY are dimensional, the arg must contain a
    BinOp(Div) node where the dimensional feature appears in the numerator
    AND a balancing dimensional quantity (typically `exp(params['log_*'])`
    or another reference to the same dimensional feature) appears in the
    denominator. We approximate this by requiring: for each dimensional
    feature reference, there is at least one Div operation in the AST whose
    numerator chain contains that feature. This is heuristic but catches
    the obvious violation `exp(features['x'])` while permitting the
    canonical `exp(features['x'] / exp(params['log_c']))` pattern.

    Returns (safe, reason).
    """
    # Audit-fix H1/H2 (2026-04-28): features inside log/log10/ln are
    # dimension-stripped by the log convention. Skip them when collecting
    # dimensional refs in the upstream transcendental's arg.
    refs = _collect_features_in_subtree(arg, exempt_inside_log=True)
    if not refs:
        return True, "arg is parameter-only (no feature references)"

    dimensional_refs = [
        r for r in refs
        if _classify_feature(r, dimensional_features) != "dimensionless"
    ]
    if not dimensional_refs:
        return True, "all features in arg are dimensionless"

    # If we hit a dimensional feature, look for a Div node containing it in
    # the numerator. This is a conservative check — it permits any Div as
    # long as the dimensional ref lives in the left side of a Div somewhere.
    div_satisfies: dict[str, bool] = {r: False for r in dimensional_refs}
    for sub in ast.walk(arg):
        if isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.Div):
            num_refs = _collect_features_in_subtree(sub.left)
            for r in dimensional_refs:
                if r in num_refs:
                    div_satisfies[r] = True

    unbalanced = [r for r, ok in div_satisfies.items() if not ok]
    if unbalanced:
        return False, (
            f"dimensional feature(s) {unbalanced} appear inside transcendental "
            f"arg without being divided by a dimension-balancing quantity. "
            f"Buckingham π: transcendentals require dimensionless args."
        )
    return True, "dimensional refs are balanced by Div operation"


def run_buckingham_pi_gate(
    parametric_form: str,
    rubric_data: Optional[dict] = None,
) -> dict[str, Any]:
    """Scan PARAMETRIC_FORM for transcendentals with dimensional arguments.

    Returns a result dict; passed=False on any violation.
    """
    rubric_data = rubric_data or {}
    dim_feats: dict[str, str] = dict(rubric_data.get("dimensional_features") or {})
    # Merge with defaults (rubric overrides defaults).
    for k in _DEFAULT_DIMENSIONFUL_FEATURES:
        dim_feats.setdefault(k, "acceleration")

    if not isinstance(parametric_form, str) or not parametric_form.strip():
        return {
            "passed": True,
            "violations": [],
            "features_used": [],
            "scanned_calls": 0,
            "gate_id": GATE_ID,
            "skipped_reason": "empty_form",
        }

    try:
        tree = ast.parse(parametric_form, mode="eval")
    except SyntaxError as exc:
        return {
            "passed": True,  # parser failure is R1's job, not Buckingham's
            "violations": [],
            "features_used": [],
            "scanned_calls": 0,
            "gate_id": GATE_ID,
            "skipped_reason": f"unparseable: {exc}",
        }

    violations: list[dict[str, Any]] = []
    scanned = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn_name: Optional[str] = None
        if isinstance(node.func, ast.Name):
            fn_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            fn_name = node.func.attr
        if fn_name is None or fn_name.lower() not in TRANSCENDENTAL_FUNCS:
            continue
        # Audit-fix H1 (2026-04-28): log/log10/ln implicitly normalize by
        # a unit constant in physics convention. Don't enforce dimensionless
        # arg on these specific transcendentals.
        if fn_name.lower() in _LOG_FUNCS_DIMENSION_STRIPPING:
            continue
        scanned += 1
        # Most transcendentals take a single positional arg. sigmoid in
        # the local primitive vocabulary takes (x, center=0, width=1).
        # We only check the first arg; centers/widths are bare params.
        if not node.args:
            continue
        arg = node.args[0]
        ok, reason = _arg_is_dimensionally_safe(arg, dim_feats)
        if not ok:
            try:
                arg_src = ast.unparse(arg)
            except Exception:                       # noqa: BLE001
                arg_src = "<unparse_failed>"
            violations.append({
                "function": fn_name,
                "arg": arg_src[:200],
                "reason": reason,
            })

    return {
        "passed": len(violations) == 0,
        "violations": violations,
        "features_used": _collect_features_in_subtree(tree),
        "scanned_calls": scanned,
        "gate_id": GATE_ID,
    }


def format_violation_feedback(result: dict[str, Any]) -> str:
    """Mutator-facing rejection message when the gate fails."""
    if result.get("passed"):
        return ""
    lines = [
        "🛑 Buckingham π violation — your PARAMETRIC_FORM applies a transcendental",
        "function to a dimensional quantity.",
        "",
        "The universe does not compute exp(meters) or tanh(kg). Every transcendental",
        "function in physics takes a DIMENSIONLESS argument — typically a ratio of",
        "two quantities with the same units (e.g., g_bar/a₀, r/r_0).",
        "",
        "Violations detected:",
    ]
    for v in result.get("violations", []):
        lines.append(f"  - {v['function']}({v['arg']})")
        lines.append(f"      reason: {v['reason']}")
    lines.append("")
    lines.append("Fix: divide every dimensional feature by a same-unit constant before")
    lines.append("passing it through a transcendental. Example transformation:")
    lines.append("  ❌ exp(features['x'])")
    lines.append("  ✓ exp(features['x'] / exp(params['log_a0']))   # log_a0 in log-acceleration")
    lines.append("  ✓ tanh(features['radius_log10'] - params['r0_log10'])  # both dimensionless")
    return "\n".join(lines)
