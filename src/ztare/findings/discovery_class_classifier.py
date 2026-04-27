"""GP-133 Round 4: discovery-class auto-classifier.

For py_exec runs against known-OEIS targets, automatically classify the
mutator's final expression as one of:

    recognition           — syntactically or mathematically equivalent to
                            a formula already in the target's OEIS comment
                            field or linked references
    synthesis             — expression absent from known literature AND
                            shorter description-length than published
                            version (candidate; needs domain-expert review)
    synthesis_incompressible — synthesis-class but expression cannot be
                            reduced to standard primitives
    derivation            — expression accompanied by a stated axiom-to-
                            consequent chain (operationalized via a
                            companion `derivation.lean` or `derivation.md`)
    calibration           — apparatus-shakedown run; not a discovery claim

The classifier is INPUT-DRIVEN. It does not crawl OEIS — the principal or
prior session must supply the known formula in `target_known_formula`.
This keeps the discriminator honest: classification only fires when the
ground truth is known, and the result is a binary-equivalent + secondary
heuristic.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Literal, Optional

log = logging.getLogger(__name__)

DiscoveryClass = Literal[
    "recognition", "synthesis", "synthesis_incompressible",
    "derivation", "calibration",
]


@dataclass(frozen=True)
class ClassificationResult:
    discovery_class: DiscoveryClass
    method: str               # how the classifier reached this verdict
    detail: str               # human-readable rationale
    expression_length: int
    known_formula_length: Optional[int]


def _strip_whitespace(s: str) -> str:
    return re.sub(r"\s+", "", s)


def _try_symbolic_equivalence(
    candidate_expr: str, known_expr: str, var: str = "n"
) -> Optional[bool]:
    """Use SymPy to test mathematical equivalence. Returns None if SymPy
    cannot parse one of the inputs (e.g. py_exec generators / list comps
    that aren't pure mathematical expressions)."""
    try:
        import sympy
        n = sympy.Symbol(var)
        # Limited safe-eval: only allow standard math functions
        safe_globals = {
            "n": n,
            "log": sympy.log, "exp": sympy.exp, "sqrt": sympy.sqrt,
            "sin": sympy.sin, "cos": sympy.cos, "pi": sympy.pi,
            "Sum": sympy.Sum, "Symbol": sympy.Symbol,
        }
        cand = sympy.sympify(candidate_expr, locals=safe_globals, evaluate=True)
        known = sympy.sympify(known_expr, locals=safe_globals, evaluate=True)
        diff = sympy.simplify(cand - known)
        return diff == 0
    except Exception:
        return None


def classify(
    *,
    expression: str,
    target_known_formula: Optional[str] = None,
    has_derivation_artifact: bool = False,
    is_calibration_run: bool = False,
) -> ClassificationResult:
    """Classify a final mutator expression.

    Parameters
    ----------
    expression : str
        The mutator's final expression for the target (e.g. for sigma:
        "sum(d for d in range(1, n+1) if n % d == 0)").
    target_known_formula : str, optional
        The published formula for the target if known (e.g. from OEIS
        comment field). If None, classifier defaults to "synthesis" with
        a low-confidence note (cannot prove novelty without a baseline).
    has_derivation_artifact : bool
        True if a companion derivation file exists (e.g. derivation.lean
        or derivation.md with stated axiom-to-consequent chain). Promotes
        from synthesis → derivation.
    is_calibration_run : bool
        True if the run is explicitly a calibration / instrument-shakedown
        run rather than a discovery claim.

    Returns
    -------
    ClassificationResult with discovery_class + method + detail.
    """
    expr_len = len(expression.strip())

    if is_calibration_run:
        return ClassificationResult(
            discovery_class="calibration",
            method="explicit_calibration_flag",
            detail="Run was declared calibration / instrument-shakedown.",
            expression_length=expr_len,
            known_formula_length=None,
        )

    if target_known_formula is None or not target_known_formula.strip():
        # No baseline to compare against. Default conservative: synthesis-candidate
        # but flagged for domain-expert review.
        return ClassificationResult(
            discovery_class="synthesis",
            method="no_baseline_default_synthesis",
            detail=(
                "No published baseline formula provided. Defaulting to "
                "synthesis-candidate; domain-expert review REQUIRED before "
                "any external citation. Provide target_known_formula when "
                "the target is a known-OEIS sequence to enable auto-classification."
            ),
            expression_length=expr_len,
            known_formula_length=None,
        )

    known_len = len(target_known_formula.strip())

    # Test 1: syntactic identity (after whitespace normalization)
    if _strip_whitespace(expression) == _strip_whitespace(target_known_formula):
        return ClassificationResult(
            discovery_class="recognition",
            method="syntactic_identity",
            detail="Expression is character-identical (modulo whitespace) to known formula.",
            expression_length=expr_len,
            known_formula_length=known_len,
        )

    # Test 2: SymPy mathematical equivalence
    sym_eq = _try_symbolic_equivalence(expression, target_known_formula)
    if sym_eq is True:
        return ClassificationResult(
            discovery_class="recognition",
            method="sympy_mathematical_equivalence",
            detail=(
                "Expression and known formula reduce to the same SymPy "
                "expression. Mathematically equivalent rephrasing — "
                "still recognition."
            ),
            expression_length=expr_len,
            known_formula_length=known_len,
        )
    elif sym_eq is False:
        # Not equivalent. Possible synthesis. Check description-length.
        if expr_len < known_len:
            base_class: DiscoveryClass = "synthesis"
            detail = (
                f"Expression NOT equivalent to known formula (SymPy diff != 0); "
                f"candidate is shorter than published version "
                f"({expr_len} vs {known_len} chars). Synthesis candidate; "
                f"domain-expert review required."
            )
        else:
            base_class = "synthesis_incompressible"
            detail = (
                f"Expression NOT equivalent to known formula and is NOT "
                f"shorter than the published version ({expr_len} vs "
                f"{known_len} chars). Discovery that does not compress — "
                f"may be Eurisko-Traveller-class 'looks-like-gibberish' "
                f"finding, or may be incorrect. Domain-expert review required."
            )
        if has_derivation_artifact:
            return ClassificationResult(
                discovery_class="derivation",
                method="non_equivalent_with_derivation_artifact",
                detail=detail + " Derivation artifact present — promoted to derivation-class.",
                expression_length=expr_len,
                known_formula_length=known_len,
            )
        return ClassificationResult(
            discovery_class=base_class,
            method="non_equivalent_no_derivation",
            detail=detail,
            expression_length=expr_len,
            known_formula_length=known_len,
        )
    else:
        # SymPy could not parse. Fall back to syntactic / length-based heuristic.
        return ClassificationResult(
            discovery_class="synthesis",
            method="sympy_unparseable_fallback",
            detail=(
                "Could not symbolically compare (one of the expressions is "
                "not a pure SymPy expression — e.g. uses list comprehensions "
                "or sieves). Defaulting to synthesis-candidate; domain-expert "
                "review required to determine recognition vs synthesis."
            ),
            expression_length=expr_len,
            known_formula_length=known_len,
        )
