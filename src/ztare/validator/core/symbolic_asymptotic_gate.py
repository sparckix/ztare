from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


DEFAULT_ASYMPTOTIC_PRIORITY = ("B", "N", "K", "n", "k", "M", "A")
DEFAULT_ASYMPTOTIC_SYMBOLS = ("A", "B", "K", "N", "n", "k", "M")
DEFAULT_COEFFICIENT_SYMBOLS = (
    "alpha",
    "beta",
    "C",
    "C0",
    "C1",
    "C2",
    "C3",
    "c0",
    "c1",
    "c2",
    "gamma0",
    "tau0",
    "lambda0",
)


@dataclass(frozen=True)
class TextRejector:
    """A small declarative text veto for domain-specific symbolic gates.

    The generic gate validates the mechanical SymPy burden. Domain projects can
    add rejectors for known semantic traps without forking the parser.
    """

    name: str
    reason: str
    required_any_groups: tuple[tuple[str, ...], ...]
    unless_any: tuple[str, ...] = ()

    def fires(self, text: str) -> bool:
        if self.unless_any and any(token in text for token in self.unless_any):
            return False
        return all(any(token in text for token in group) for group in self.required_any_groups)


def _first_mapping_value(data: Mapping[str, Any], keys: Sequence[str]) -> Any:
    lowered = {str(k).lower(): v for k, v in data.items()}
    for key in keys:
        if key in lowered:
            return lowered[key]
    for actual_key, value in lowered.items():
        if any(key in actual_key for key in keys):
            return value
    return None


def evaluate_asymptotic_terms(
    terms: Mapping[str, Any],
    *,
    rejectors: Sequence[TextRejector] = (),
    gain_keys: Sequence[str] = ("gain_polynomial_or_bound", "gain_polynomial", "mixed_gain_bound"),
    tax_keys: Sequence[str] = (
        "self_tax_polynomial_or_bound",
        "self_tax_polynomial",
        "high_high_bound",
    ),
    asymptotic_priority: Sequence[str] = DEFAULT_ASYMPTOTIC_PRIORITY,
    asymptotic_symbols: Sequence[str] = DEFAULT_ASYMPTOTIC_SYMBOLS,
    coefficient_symbols: Sequence[str] = DEFAULT_COEFFICIENT_SYMBOLS,
    require_sqrt_tax_limit: bool = False,
    sqrt_tax_limit_threshold: float = 1.0,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ran": True,
        "passed": False,
        "reason": "asymptotic_terms_not_checked",
    }

    try:
        import sympy as sp
    except Exception as exc:  # noqa: BLE001
        payload["reason"] = f"sympy_unavailable: {type(exc).__name__}: {exc}"
        return payload

    rendered = json.dumps(terms, default=str).lower()
    if any(token in rendered for token in ("not_yet_derived", "not yet derived", "placeholder", "todo")):
        payload["reason"] = "asymptotic_terms_contains_placeholder"
        return payload

    for rejector in rejectors:
        if rejector.fires(rendered):
            payload["reason"] = f"{rejector.name}: {rejector.reason}"
            return payload

    gain_raw = _first_mapping_value(terms, gain_keys)
    tax_raw = _first_mapping_value(terms, tax_keys)
    if gain_raw is None or tax_raw is None:
        payload["reason"] = "missing_gain_or_self_tax_polynomial"
        return payload

    locals_ns = {
        name: sp.symbols(name, positive=True)
        for name in (*asymptotic_symbols, *coefficient_symbols)
    }
    try:
        gain_text = str(gain_raw).strip()
        tax_text = str(tax_raw).strip()
        for field_name, field_text in (
            ("gain_polynomial_or_bound", gain_text),
            ("self_tax_polynomial_or_bound", tax_text),
        ):
            if "=" in field_text or ";" in field_text:
                raise ValueError(f"{field_name}_must_be_raw_sympy_expression_without_lhs_or_prose")
        gain_expr = sp.sympify(gain_text, locals=locals_ns)
        tax_expr = sp.sympify(tax_text, locals=locals_ns)
    except Exception as exc:  # noqa: BLE001
        payload["reason"] = f"sympify_failed: {type(exc).__name__}: {exc}"
        return payload

    symbols = sorted(gain_expr.free_symbols | tax_expr.free_symbols, key=lambda s: str(s))
    preferred = [
        sym
        for name in asymptotic_priority
        for sym in symbols
        if str(sym) == name
    ]
    if not preferred:
        payload["reason"] = "no_asymptotic_symbol_found"
        return payload
    var = preferred[0]

    def rational_degree(expr: Any) -> int:
        expr = sp.together(expr)
        num, den = expr.as_numer_denom()
        return sp.Poly(num, var).degree() - sp.Poly(den, var).degree()

    try:
        ratio = sp.simplify(gain_expr / tax_expr)
        ratio_limit = sp.limit(ratio, var, sp.oo)
        sqrt_ratio = sp.simplify(gain_expr / sp.sqrt(tax_expr))
        sqrt_ratio_limit = sp.limit(sqrt_ratio, var, sp.oo)
        degree_gain = rational_degree(gain_expr)
        degree_tax = rational_degree(tax_expr)
    except Exception as exc:  # noqa: BLE001
        payload["reason"] = f"asymptotic_limit_failed: {type(exc).__name__}: {exc}"
        return payload

    payload.update(
        {
            "variable": str(var),
            "gain_expr": str(gain_expr),
            "self_tax_expr": str(tax_expr),
            "gain_over_self_tax_limit": str(ratio_limit),
            "gain_over_sqrt_self_tax_limit": str(sqrt_ratio_limit),
            "degree_gain": degree_gain,
            "degree_self_tax": degree_tax,
        }
    )
    try:
        limit_float = float(sp.N(ratio_limit))
    except Exception as exc:  # noqa: BLE001
        payload["reason"] = f"limit_not_numeric: {type(exc).__name__}: {exc}"
        return payload
    if not (0 <= limit_float < 1):
        payload["reason"] = f"gain_over_self_tax_limit_not_subunit: {limit_float}"
        return payload
    if degree_tax < degree_gain:
        payload["reason"] = "self_tax_degree_below_gain_degree"
        return payload
    if require_sqrt_tax_limit:
        try:
            sqrt_limit_float = float(sp.N(sqrt_ratio_limit))
        except Exception as exc:  # noqa: BLE001
            payload["reason"] = f"sqrt_tax_limit_not_numeric: {type(exc).__name__}: {exc}"
            return payload
        if not (0 <= sqrt_limit_float <= sqrt_tax_limit_threshold):
            payload["reason"] = (
                "gain_over_sqrt_self_tax_limit_above_threshold: "
                f"{sqrt_limit_float} > {sqrt_tax_limit_threshold}"
            )
            return payload

    payload["passed"] = True
    payload["reason"] = "sympy_asymptotic_check_passed"
    return payload


def run_candidate_asymptotic_check(
    candidate_path: str | Path | None,
    *,
    rejectors: Sequence[TextRejector] = (),
    require_sqrt_tax_limit: bool = False,
    sqrt_tax_limit_threshold: float = 1.0,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ran": False,
        "passed": False,
        "reason": "asymptotic_terms_not_executed",
    }
    if candidate_path is None:
        payload["reason"] = "candidate_path_missing"
        return payload

    path = Path(candidate_path)
    try:
        module_name = f"_ztare_asymptotic_candidate_{uuid.uuid4().hex}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            payload["reason"] = "candidate_import_spec_failed"
            return payload
        module = importlib.util.module_from_spec(spec)
        old_path = list(sys.path)
        sys.path.insert(0, str(path.parent))
        try:
            spec.loader.exec_module(module)
        finally:
            sys.path[:] = old_path
        fn = getattr(module, "asymptotic_terms", None)
        if not callable(fn):
            payload["reason"] = "asymptotic_terms_not_callable"
            return payload
        terms = fn()
        if not isinstance(terms, Mapping):
            payload["ran"] = True
            payload["reason"] = "asymptotic_terms_returned_non_mapping"
            return payload
        return evaluate_asymptotic_terms(
            terms,
            rejectors=rejectors,
            require_sqrt_tax_limit=require_sqrt_tax_limit,
            sqrt_tax_limit_threshold=sqrt_tax_limit_threshold,
        )
    except Exception as exc:  # noqa: BLE001
        payload["ran"] = True
        payload["reason"] = f"candidate_runtime_error: {type(exc).__name__}: {exc}"
        return payload
