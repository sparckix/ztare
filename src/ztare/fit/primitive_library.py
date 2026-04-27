"""GP-127: Cross-Substrate Primitive Library.

After each successful compression, the winning template is saved to a shared
library. On new substrates, the library templates are tried FIRST (before the
fixed grammar). This gives the engine a growing vocabulary learned from its
own successful compressions.

Ramanujan's genius was cross-domain pattern recognition. This approximates it:
if sqrt(n/log(n)) worked on prime partitions AND abundant density, it probably
encodes something structural — try it on the next substrate too.

Usage:
    from src.ztare.fit.primitive_library import load_library, save_to_library

    # After successful compression:
    save_to_library(expression, params, substrate_name, bic)

    # Before compression on new substrate:
    learned_templates = load_library()
"""

from __future__ import annotations

import json
from pathlib import Path

LIBRARY_PATH = Path(__file__).parent.parent.parent.parent / "config" / "primitive_library.json"


def load_library() -> list[tuple[str, str, list[str]]]:
    """Load learned templates from the shared library.

    Returns list of (name, expression_str, param_names) tuples,
    same format as _build_templates_1d().
    """
    if not LIBRARY_PATH.exists():
        return []

    data = json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))
    templates = []
    seen_exprs = set()

    for entry in data:
        expr = entry["expression"]
        # Deduplicate by expression (ignore parameter values)
        if expr in seen_exprs:
            continue
        seen_exprs.add(expr)

        name = f"LIB_{entry.get('name', 'learned')}_{entry.get('source', 'unknown')}"
        param_names = list(entry.get("params", {}).keys())
        templates.append((name, expr, param_names))

    return templates


def save_to_library(
    name: str,
    expression: str,
    params: dict[str, float],
    source_substrate: str,
    bic: float,
    max_residual: float | None = None,
) -> None:
    """Save a gate-passing compressed form to the shared library.

    Only saves if the expression isn't already in the library.
    """
    LIBRARY_PATH.parent.mkdir(parents=True, exist_ok=True)

    if LIBRARY_PATH.exists():
        data = json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))
    else:
        data = []

    # Check for duplicate expression
    existing_exprs = {entry["expression"] for entry in data}
    if expression in existing_exprs:
        return

    data.append({
        "name": name,
        "expression": expression,
        "params": params,
        "source": source_substrate,
        "bic": bic,
        "max_residual": max_residual,
    })

    LIBRARY_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def generalize_expression(expression: str, source_var: str = "n") -> str:
    """Strip fitted parameter values from an expression, keeping structure.

    The expression from one substrate uses variable 'n' — when trying on a
    new substrate with variable 't', we need to substitute.
    This function returns the expression with the source variable,
    ready for substitution at use time.
    """
    return expression
