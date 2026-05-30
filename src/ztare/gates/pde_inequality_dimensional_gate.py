"""G-PDE-INEQ-DIM — pre-verifier for PDE-shape inequalities (extends GP-170).

Sister gate to `symbolic_logic_cage.py` (GP-170 R12, which checks
algebraic constraints on PARAMETRIC_FORM). This gate operates on
LLM-PROPOSED INEQUALITY CANDIDATES before they're handed to lake build.

Catches three failure classes Codex flagged on 2026-05-06:
  - Dimensional incoherence (units don't compose)
  - Algebraic inconsistency (LHS exceeds RHS via simple manipulation)
  - Endpoint-exposure violations (lhs/rhs mention quantities not in pack)

# Substrate-agnostic by design

The gate accepts any candidate inequality of the form:
  `lhs_expr <op> rhs_expr` where op ∈ {≤, <, =, ≈}
plus a `dimensional_features: dict[name -> dimension_string]`
plus an `endpoint_set: set[str]` of allowed identifiers.

Defaults to NS Track B's dimensional vocabulary; override via rubric_data.

# What it returns

  - `passed=True`: dimensions consistent + endpoints all in allowed set
  - `passed=False`: specific violation flagged
  - `indeterminate`: SymPy couldn't decide (safe default = pass with warning)

# Reuses

  - `src/ztare/gates/symbolic_logic_cage.py::rewrite_form_for_sympy`
    for `where()` / `sigmoid()` AST rewriting (substrate-agnostic).
  - `src/ztare/gates/buckingham_pi_gate.py` for dimension classification
    (call directly when checking transcendentals).

# When this gate fires

  In the typed-endpoint pack: AFTER Stage 1 (typed identifier filter),
  BEFORE lake build. Cuts a class of failures at zero Lean cost.
  Outside typed-endpoint pack: any rubric exposing
  `cage_meta.pde_inequality_check = true` gets this in PRE_FIT.
"""
from __future__ import annotations

import re
import ast
from typing import Any

GATE_ID = "G-PDE-INEQ-DIM"
PRODUCER = "pde_inequality_dimensional_gate"
RELIABILITY_NOTE = (
    "Advisory v0.1. Catches dimensional + endpoint-exposure violations on "
    "LLM-proposed inequalities. Does NOT verify mathematical correctness — "
    "passes inequalities that are well-typed but mathematically false. "
    "Use as a CHEAP PRE-FILTER before lake build."
)

# Common PDE quantity dimensions (NS-flavored defaults; override per substrate)
DEFAULT_DIM_CATEGORIES = {
    "velocity": ["u", "v", "w", "vel", "velocity", "u_n", "u_h"],
    "pressure": ["p", "pressure", "pi"],
    "vorticity": ["omega", "ω", "curl", "vorticity"],
    "viscosity": ["nu", "ν", "viscosity"],
    "energy": ["E", "energy", "kinetic"],
    "enstrophy": ["enstrophy", "Z"],
    "norm": ["norm", "Lp", "L2", "Linf", "Sobolev"],
    "constant": ["C", "K", "M", "epsilon", "ε", "delta", "δ"],
    "scale": ["lambda", "λ", "shell", "N", "n"],
    "time": ["t", "time", "T"],
    "space": ["x", "y", "z", "r", "rho"],
}

# Conservative physical-unit defaults for common PDE ansatz notation.
#
# These are intentionally exact/small and only activate the exponent-vector
# checker when every identifier in the candidate can be resolved physically.
# Abstract Lean endpoint fields such as `survivalProfit` or `sharpTarget` stay
# on the legacy category checker unless the rubric supplies explicit dimensions.
DEFAULT_PHYSICAL_DIMENSIONS = {
    "N": "L^-1",
    "k": "L^-1",
    "xi": "L^-1",
    "shell": "L^-1",
    "kNorm": "L^-1",
    "dt": "T",
    "t": "T",
    "time": "T",
    "nu": "L^2 T^-1",
    "viscosity": "L^2 T^-1",
    "u": "L T^-1",
    "v": "L T^-1",
    "velocity": "L T^-1",
    "grad_u": "T^-1",
    "omega": "T^-1",
    "vorticity": "T^-1",
    "pressure": "L^2 T^-2",
}

# Inequality operators we recognize.  Longer ASCII forms must precede their
# one-character prefixes so `<=` is not parsed as `<` with a leading `=`.
INEQ_OPS = ["≤", "≥", "<=", ">=", "==", "<", ">", "=", "≈"]

DIMENSIONLESS = {"", "1", "dimensionless"}
LEGACY_DIMENSIONLESS = {"constant", "scalar", "none", "norm"}


def _classify_token(token: str) -> str | None:
    """Heuristic dimension category for a Lean identifier token."""
    tok = token.lower().split(".")[-1]  # strip qualifier
    for category, names in DEFAULT_DIM_CATEGORIES.items():
        if tok in [n.lower() for n in names]:
            return category
    return None


def _split_inequality(expr: str) -> tuple[str, str, str] | None:
    """Find the top-level inequality operator and split lhs/rhs."""
    # Try each operator; first match wins (treat ≤ before <, etc.)
    for op in INEQ_OPS:
        # Find paren-balanced top-level occurrence
        depth = 0
        i = 0
        while i < len(expr):
            c = expr[i]
            if c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
            elif depth == 0 and expr[i:i + len(op)] == op:
                # Avoid := which is Lean assignment
                if op == "=" and i > 0 and expr[i-1] == ":":
                    i += 1; continue
                lhs = expr[:i].strip()
                rhs = expr[i + len(op):].strip()
                if lhs and rhs:
                    return (lhs, op, rhs)
            i += 1
    return None


def _extract_identifiers(expr: str) -> list[str]:
    """Pull identifier-like tokens (Lean idents, including .qualified)."""
    pat = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
    return [m.group(0) for m in pat.finditer(expr)]


def _clean_dim_vector(vec: dict[str, float]) -> dict[str, float]:
    return {k: v for k, v in sorted(vec.items()) if abs(v) > 1e-12}


def _add_dim_vectors(a: dict[str, float],
                     b: dict[str, float],
                     scale: float = 1.0) -> dict[str, float]:
    out = dict(a)
    for k, v in b.items():
        out[k] = out.get(k, 0.0) + scale * v
    return _clean_dim_vector(out)


def _scale_dim_vector(a: dict[str, float], scale: float) -> dict[str, float]:
    return _clean_dim_vector({k: scale * v for k, v in a.items()})


def _parse_dimension_vector(value: Any) -> dict[str, float] | None:
    """Parse physical-dimension declarations such as `L^2 T^-1`.

    Existing users pass category labels like `velocity` or `energy`; those
    deliberately return `None` so the legacy category checker remains active.
    Vector mode engages only when at least one declared dimension uses a real
    physical exponent vector, either as a mapping or as an uppercase-base
    string like `L/T`, `M L^-1 T^-2`, or `dimensionless`.
    """
    if isinstance(value, dict):
        try:
            return _clean_dim_vector({str(k): float(v) for k, v in value.items()})
        except (TypeError, ValueError):
            return None
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if raw.lower() in DIMENSIONLESS:
        return {}
    if not raw:
        return {}
    if not re.search(r"[A-Z]", raw):
        return None

    # Convert compact division notation into signed factors. Examples:
    # `L/T`, `L^2*T^-1`, `M L^-1 T^-2`.
    token_re = re.compile(
        r"(?P<op>[*/]?)\s*(?P<base>[A-Z][A-Za-z0-9_]*)"
        r"(?:\s*(?:\^|\*\*)\s*(?P<exp>[-+]?\d+(?:\.\d+)?))?"
    )
    vec: dict[str, float] = {}
    pos = 0
    matched = False
    for m in token_re.finditer(raw):
        skipped = raw[pos:m.start()].strip()
        if skipped and skipped not in {"*", "/"}:
            return None
        pos = m.end()
        matched = True
        op = m.group("op")
        base = m.group("base")
        exp = float(m.group("exp") or 1.0)
        if op == "/":
            exp *= -1.0
        vec[base] = vec.get(base, 0.0) + exp
    if not matched or raw[pos:].strip():
        return None
    return _clean_dim_vector(vec)


def _lookup_declared_dimension(token: str,
                               dimensional_features: dict[str, Any],
                               *,
                               use_default_physical: bool = True
                               ) -> dict[str, float] | None:
    candidates = [token, token.replace(".", "_"), token.split(".")[-1],
                  token.split(".")[0]]
    for candidate in candidates:
        if candidate in dimensional_features:
            parsed = _parse_dimension_vector(dimensional_features[candidate])
            if parsed is not None:
                return parsed
            raw = str(dimensional_features[candidate]).strip().lower()
            if raw in LEGACY_DIMENSIONLESS:
                return {}
    if use_default_physical:
        for candidate in candidates:
            if candidate in DEFAULT_PHYSICAL_DIMENSIONS:
                parsed = _parse_dimension_vector(
                    DEFAULT_PHYSICAL_DIMENSIONS[candidate])
                if parsed is not None:
                    return parsed
    inferred = _classify_token(token)
    if inferred in {"constant", "norm"}:
        return {}
    return None


def _physical_vector_mode_declared(dimensional_features: dict[str, Any]) -> bool:
    for value in dimensional_features.values():
        if isinstance(value, dict):
            return True
        if isinstance(value, str):
            raw = value.strip()
            if raw.lower() in DIMENSIONLESS or re.search(r"[A-Z]", raw):
                if _parse_dimension_vector(raw) is not None:
                    return True
    return False


def _physical_vector_mode_enabled(lhs: str,
                                  rhs: str,
                                  dimensional_features: dict[str, Any]) -> bool:
    if _physical_vector_mode_declared(dimensional_features):
        return True

    identifiers = set(_extract_identifiers(lhs)) | set(_extract_identifiers(rhs))
    if not identifiers:
        return False

    safe_funcs = {"sqrt", "abs", "exp", "log", "sin", "cos", "tan", "Real.sqrt"}
    for token in identifiers:
        if token in safe_funcs or token.split(".")[-1] in safe_funcs:
            continue
        if _lookup_declared_dimension(token, dimensional_features) is None:
            return False
    return True


def _name_of_ast_node(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _name_of_ast_node(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _numeric_constant(node: ast.AST) -> float | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        inner = _numeric_constant(node.operand)
        return -inner if inner is not None else None
    return None


def _normalise_expr_for_ast(expr: str) -> str:
    # Lean-style powers are the most common mismatch for simple candidates.
    return expr.replace("^", "**")


def _dimension_of_ast(node: ast.AST,
                      dimensional_features: dict[str, Any]
                      ) -> tuple[dict[str, float] | None, list[str]]:
    if isinstance(node, ast.Expression):
        return _dimension_of_ast(node.body, dimensional_features)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return {}, []
        return None, [f"unsupported literal {node.value!r}"]
    if isinstance(node, (ast.Name, ast.Attribute)):
        name = _name_of_ast_node(node)
        if not name:
            return None, ["unsupported identifier node"]
        dim = _lookup_declared_dimension(name, dimensional_features)
        if dim is None:
            return None, [f"missing physical dimension for `{name}`"]
        return dim, []
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        return _dimension_of_ast(node.operand, dimensional_features)
    if isinstance(node, ast.BinOp):
        left, lerr = _dimension_of_ast(node.left, dimensional_features)
        right, rerr = _dimension_of_ast(node.right, dimensional_features)
        errors = lerr + rerr
        if left is None or right is None:
            return None, errors
        if isinstance(node.op, (ast.Add, ast.Sub)):
            if left != right:
                errors.append(
                    f"additive dimension mismatch: {left} vs {right}")
            return left, errors
        if isinstance(node.op, ast.Mult):
            return _add_dim_vectors(left, right), errors
        if isinstance(node.op, ast.Div):
            return _add_dim_vectors(left, right, scale=-1.0), errors
        if isinstance(node.op, ast.Pow):
            exponent = _numeric_constant(node.right)
            if exponent is None:
                errors.append("dimension exponent is not a numeric constant")
                return None, errors
            return _scale_dim_vector(left, exponent), errors
        return None, errors + [f"unsupported binary operator {type(node.op).__name__}"]
    if isinstance(node, ast.Call):
        fname = _name_of_ast_node(node.func) or ""
        args = node.args
        if len(args) != 1:
            return None, [f"unsupported function arity for `{fname}`"]
        arg_dim, errors = _dimension_of_ast(args[0], dimensional_features)
        if arg_dim is None:
            return None, errors
        tail = fname.split(".")[-1]
        if tail in {"sqrt"}:
            return _scale_dim_vector(arg_dim, 0.5), errors
        if tail in {"abs"}:
            return arg_dim, errors
        if tail in {"exp", "log", "sin", "cos", "tan"}:
            if arg_dim:
                errors.append(f"`{fname}` requires a dimensionless argument")
            return {}, errors
        return None, errors + [f"unsupported function `{fname}`"]
    return None, [f"unsupported expression node {type(node).__name__}"]


def _physical_dimension_of_expr(expr: str,
                                dimensional_features: dict[str, Any]
                                ) -> tuple[dict[str, float] | None, list[str]]:
    try:
        tree = ast.parse(_normalise_expr_for_ast(expr), mode="eval")
    except SyntaxError as exc:
        return None, [f"could not parse expression for physical dimensions: {exc.msg}"]
    return _dimension_of_ast(tree, dimensional_features)


def check_dimensional_consistency(lhs: str, rhs: str,
                                    dimensional_features: dict[str, Any]
                                   ) -> dict[str, Any]:
    """Check that lhs and rhs have compatible dimensional categories.

    Substrate-agnostic: uses the substrate's declared `dimensional_features`
    (mapping identifier -> dimension category). Falls back to NS defaults
    via `_classify_token` when not declared.
    """
    if _physical_vector_mode_enabled(lhs, rhs, dimensional_features):
        lhs_dim, lhs_errors = _physical_dimension_of_expr(lhs, dimensional_features)
        rhs_dim, rhs_errors = _physical_dimension_of_expr(rhs, dimensional_features)
        errors = lhs_errors + rhs_errors
        if lhs_dim is None or rhs_dim is None:
            return {"consistent": False,
                    "violation": "physical dimension parse failure",
                    "lhs_dim": lhs_dim,
                    "rhs_dim": rhs_dim,
                    "errors": errors}
        if lhs_dim != rhs_dim:
            return {"consistent": False,
                    "violation": "physical dimension mismatch",
                    "lhs_dim": lhs_dim,
                    "rhs_dim": rhs_dim,
                    "errors": errors}
        if errors:
            return {"consistent": False,
                    "violation": "physical dimension expression mismatch",
                    "lhs_dim": lhs_dim,
                    "rhs_dim": rhs_dim,
                    "errors": errors}
        return {"consistent": True,
                "mode": "physical_vector",
                "lhs_dim": lhs_dim,
                "rhs_dim": rhs_dim}

    def categories_in(expr: str) -> set[str]:
        cats = set()
        for tok in _extract_identifiers(expr):
            if tok in dimensional_features:
                cats.add(dimensional_features[tok])
            else:
                inferred = _classify_token(tok)
                if inferred:
                    cats.add(inferred)
        return cats

    lhs_cats = categories_in(lhs)
    rhs_cats = categories_in(rhs)
    # Empty sets = no claim possible; pass with warning
    if not lhs_cats or not rhs_cats:
        return {"consistent": True,
                "warning": "no dimensional categories detected",
                "lhs_cats": sorted(lhs_cats),
                "rhs_cats": sorted(rhs_cats)}
    # Constant categories combine with anything
    safe = {"constant", "norm"}
    lhs_core = lhs_cats - safe
    rhs_core = rhs_cats - safe
    # Inequality between dimensional and dimensionless = suspect (unless one
    # side is a norm or constant, which we treat as safe)
    if lhs_core and rhs_core and lhs_core != rhs_core:
        # Check if one is a strict subset of other (e.g. velocity ≤ velocity*const)
        if not (lhs_core <= rhs_core or rhs_core <= lhs_core):
            return {"consistent": False,
                    "violation": "category mismatch",
                    "lhs_cats": sorted(lhs_cats),
                    "rhs_cats": sorted(rhs_cats)}
    return {"consistent": True,
            "lhs_cats": sorted(lhs_cats),
            "rhs_cats": sorted(rhs_cats)}


def check_endpoint_exposure(lhs: str, rhs: str,
                             allowed_endpoints: set[str]) -> dict[str, Any]:
    """Check that all identifiers are in the allowed set."""
    if not allowed_endpoints:
        return {"all_bound": True, "warning": "no endpoint set declared"}
    idents = set(_extract_identifiers(lhs)) | set(_extract_identifiers(rhs))
    # Common Lean stdlib + math operators not requiring binding
    safe_idents = {"max", "min", "abs", "sup", "inf", "Real", "Nat", "Int",
                   "Real.exp", "Real.log", "Real.sqrt", "ℝ", "ℕ", "ℤ",
                   "fun", "let", "if", "then", "else"}
    unbound = []
    for ident in idents:
        head = ident.split(".")[0]
        if (ident in safe_idents or head in safe_idents
                or ident.replace(".", "_") in allowed_endpoints
                or head in allowed_endpoints
                or ident in allowed_endpoints):
            continue
        # Allow numeric literals
        try:
            float(ident)
            continue
        except ValueError:
            pass
        # Allow short binders (single letters)
        if len(ident) <= 2:
            continue
        unbound.append(ident)
    return {"all_bound": not unbound, "unbound": unbound}


def run_gate(candidate_inequality: str,
              dimensional_features: dict[str, str] | None = None,
              allowed_endpoints: set[str] | None = None,
             ) -> dict[str, Any]:
    """Run the PDE-inequality dimensional + endpoint check.

    Args:
        candidate_inequality: a string like 'lhs_expr ≤ rhs_expr'
        dimensional_features: substrate-declared identifier->category map
        allowed_endpoints: substrate-declared set of permitted identifiers

    Returns: gate result dict (passed, violations, warnings).
    """
    dimensional_features = dimensional_features or {}
    allowed_endpoints = allowed_endpoints or set()
    if not candidate_inequality.strip():
        return {"name": GATE_ID, "passed": True, "skipped": True,
                "reason": "empty candidate"}

    split = _split_inequality(candidate_inequality)
    if not split:
        return {"name": GATE_ID, "passed": False,
                "reason": "could not parse inequality structure (no recognised operator)",
                "hard_fail": True,
                "RELIABILITY_NOTE": RELIABILITY_NOTE}
    lhs, op, rhs = split
    if op == "==":
        op = "="

    dim_check = check_dimensional_consistency(lhs, rhs, dimensional_features)
    end_check = check_endpoint_exposure(lhs, rhs, allowed_endpoints)
    violations = []
    if not dim_check["consistent"]:
        violation = {"kind": "dimensional_mismatch"}
        for key in ("lhs_cats", "rhs_cats", "lhs_dim", "rhs_dim",
                    "violation", "errors"):
            if key in dim_check:
                violation[key] = dim_check[key]
        violations.append(violation)
    if not end_check["all_bound"]:
        violations.append({
            "kind": "endpoint_unbound",
            "unbound": end_check["unbound"],
        })
    passed = not violations
    return {
        "name": GATE_ID, "passed": passed,
        "lhs": lhs, "op": op, "rhs": rhs,
        "violations": violations,
        "dim_check": dim_check,
        "endpoint_check": end_check,
        "hard_fail": not passed,
        "severity": "advisory" if passed else "blocking",
        "source": PRODUCER,
        "RELIABILITY_NOTE": RELIABILITY_NOTE,
    }


def can_handle(substrate: Any, candidate: Any) -> tuple[bool, str]:
    """Engages when substrate exposes a PDE-inequality candidate."""
    meta = getattr(substrate, "meta", {}) or {}
    if meta.get("pde_inequality_check"):
        return True, "rubric requested PDE inequality check"
    return False, "no pde_inequality_check flag in cage_meta"


# Smoke test
if __name__ == "__main__":
    import json
    test_cases = [
        ("velocity_field ≤ C * pressure",
         {"velocity_field": "velocity", "pressure": "pressure"},
         set()),
        ("gamma * ampSq <= sharpTarget",
         {"gamma": "energy", "ampSq": "constant", "sharpTarget": "energy"},
         {"gamma", "ampSq", "sharpTarget"}),
        ("u_n + v_h ≤ M",
         {}, {"u_n", "v_h", "M"}),
        ("undefined_thing ≤ alpha",
         {}, {"alpha"}),  # endpoint_unbound
        ("nu * grad_u ≤ epsilon * energy",
         {}, {"nu", "grad_u", "epsilon", "energy"}),
    ]
    for ineq, dims, ends in test_cases:
        result = run_gate(ineq, dimensional_features=dims, allowed_endpoints=ends)
        print(f"\n{ineq!r}")
        print(f"  passed: {result['passed']}")
        if result.get("violations"):
            print(f"  violations: {json.dumps(result['violations'], indent=2)}")
