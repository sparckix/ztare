"""G-NOETHER-NONDEGENERACY — reject trivial invariants before they
contaminate the Noether-variance loss.

The Noether-variance loss term `λ · CV²(Π)` rewards Π that is constant
across the substrate. A real conservation law has CV²(Π) → 0 by
physics. A *trivially* constant expression (e.g., `Π = x - x = 0`,
`Π = features['x'] / features['x'] = 1`, `Π = x**0 = 1`) also has
CV²(Π) = 0 — but for purely structural reasons, with no physics
content. Without this gate, the mutator can submit any Lagrangian
whose Noether invariant happens to reduce to a constant and collect
the Noether penalty's full reward (λ · 0 = 0 contribution to loss)
while contributing zero physics.

This gate runs at GP-180 derivation time, AFTER `_substitute_callable`
has translated bare symbols to `features['k']` / `params['p']`. It
walks the AST and rejects four trivial-constant patterns plus three
"too weak" patterns:

  TRIVIAL (always-constant by AST):
    1. Subtraction of identical sub-expressions:  X - X
    2. Division of identical sub-expressions:     X / X
    3. Multiplication by literal zero:            X * 0  or  0 * X
    4. Power with literal-zero exponent:          X ** 0

  TOO WEAK (technically variable, but no physics signal):
    5. References zero distinct features.  Π depends only on params,
       which are constant per fit → CV²(Π) = 0 always. Contributes
       nothing to the loss but is also unfalsifiable. Pass-through:
       does not block the fit, but the gate flags it so the briefing
       knows the Noether term will never fire.
    6. References exactly one distinct feature with linear degree.
       (Reserved; not currently rejected.)
    7. Functionally constant via sympy `simplify` reduction.
       (Reserved; sympy round-trip is expensive.)

The gate's verdict has three levels:
  - "ok"        — invariant is non-degenerate; use in loss.
  - "weak"      — references no features; loss term is silently zero.
                  Allowed but flagged.
  - "degenerate"— AST-trivially constant; reject from loss.

Caller should drop "degenerate" invariants before passing to the fit
and may surface them to the mutator briefing as structural feedback.
"""
from __future__ import annotations

import ast
from typing import Literal

GATE_ID = "G-NOETHER-NONDEGENERACY"

Verdict = Literal["ok", "weak", "degenerate"]


def _ast_equal(a: ast.AST, b: ast.AST) -> bool:
    """Structural equality of two ASTs by dump."""
    try:
        return ast.dump(a) == ast.dump(b)
    except Exception:                                                   # noqa: BLE001
        return False


def _is_literal_zero(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value) == 0.0
    # `-0`, `+0` after ast.parse become UnaryOp; cover that too
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        return _is_literal_zero(node.operand)
    return False


def _collect_feature_keys(tree: ast.AST) -> set[str]:
    keys: set[str] = set()
    for n in ast.walk(tree):
        if not isinstance(n, ast.Subscript):
            continue
        if not isinstance(n.value, ast.Name) or n.value.id != "features":
            continue
        sl = n.slice
        # Py3.9+: Subscript.slice is the index expression directly.
        if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
            keys.add(sl.value)
    return keys


def _has_trivial_pattern(tree: ast.AST) -> str | None:
    """Return a human-readable reason if an AST-trivial constant pattern
    is found; else None."""
    for n in ast.walk(tree):
        # X - X
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Sub):
            if _ast_equal(n.left, n.right):
                return "subtraction of identical sub-expressions (X - X = 0)"
        # X / X
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div):
            if _ast_equal(n.left, n.right):
                return "division of identical sub-expressions (X / X = 1)"
        # X * 0  or  0 * X
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mult):
            if _is_literal_zero(n.left) or _is_literal_zero(n.right):
                return "multiplication by literal zero (X * 0 = 0)"
        # X ** 0
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Pow):
            if _is_literal_zero(n.right):
                return "power with literal-zero exponent (X ** 0 = 1)"
    return None


def evaluate_noether_invariant(invariant_str: str) -> dict:
    """Return a verdict dict for one Noether-invariant string.

    Result schema:
        {
          "gate_id": "G-NOETHER-NONDEGENERACY",
          "verdict": "ok" | "weak" | "degenerate",
          "reason": str,
          "feature_keys": list[str],
          "compile_ok": bool,
        }
    """
    if not isinstance(invariant_str, str) or not invariant_str.strip():
        return {
            "gate_id": GATE_ID, "verdict": "degenerate",
            "reason": "empty or non-string invariant", "feature_keys": [],
            "compile_ok": False,
        }
    # Strip the synthetic q_dot=0 substitution that fit_primitive_features
    # applies before compiling — we want to evaluate the same AST the
    # fit will see.
    sanitized = invariant_str.replace("q_dot", "0")
    try:
        tree = ast.parse(sanitized, mode="eval")
    except SyntaxError as exc:
        return {
            "gate_id": GATE_ID, "verdict": "degenerate",
            "reason": f"unparseable: {exc}",
            "feature_keys": [], "compile_ok": False,
        }
    trivial = _has_trivial_pattern(tree)
    if trivial is not None:
        return {
            "gate_id": GATE_ID, "verdict": "degenerate",
            "reason": trivial, "feature_keys": [], "compile_ok": True,
        }
    feature_keys = sorted(_collect_feature_keys(tree))
    if len(feature_keys) == 0:
        return {
            "gate_id": GATE_ID, "verdict": "weak",
            "reason": (
                "invariant references zero features (params-only). "
                "CV²(Π) is zero by construction; loss term contributes "
                "nothing."
            ),
            "feature_keys": [], "compile_ok": True,
        }
    return {
        "gate_id": GATE_ID, "verdict": "ok",
        "reason": f"invariant references {len(feature_keys)} distinct feature(s)",
        "feature_keys": feature_keys, "compile_ok": True,
    }


def filter_invariants(noether: dict[str, str]) -> tuple[dict[str, str], list[dict]]:
    """Split a `{symmetry: invariant_str}` dict into kept + flagged.

    Returns:
      (kept, audit) where:
        kept  = subset that passed (verdict in {"ok", "weak"})
        audit = list of per-invariant verdict dicts including drops

    "weak" invariants are kept (the loss is silently zero) but appear
    in the audit so the mutator briefing can mention them.
    "degenerate" invariants are dropped.
    """
    kept: dict[str, str] = {}
    audit: list[dict] = []
    for sym, inv in noether.items():
        v = evaluate_noether_invariant(inv)
        v["symmetry"] = sym
        v["invariant"] = inv
        audit.append(v)
        if v["verdict"] != "degenerate":
            kept[sym] = inv
    return kept, audit
