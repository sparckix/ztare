"""GP-180 numeric-submission contract helpers.

Centralizes logic that was previously inline in autoresearch_loop.py and
mutation_suite_guard.py for detecting which submission contract a mutator
is using and assembling R1-retry prompts that respect each numeric contract.

Three valid numeric submissions for the test_model.py contract:

  Parametric model declaration
      MODEL_PARAMS, PARAMETER_NAMES, INIT_RANGE, PARAMETRIC_FORM, I_model

  Variational/Lagrangian declaration
      MODEL_PARAMS, PARAMETER_NAMES, INIT_RANGE,
      LAGRANGIAN, Q_VARIABLES, BACKGROUND, PREDICTION, I_model
      (apparatus auto-derives PARAMETRIC_FORM via sympy E-L solving)

  Fixed-parameter declaration
      MODEL_PARAMS = {'a': 0.5, ...}, I_model
      (no PARAMETRIC_FORM or LAGRANGIAN; constants are not fit)

This module exposes:
  - detect_submission_contract(python_code) -> {"contract": str, "decls": dict}
  - is_mixed_parametric_variational_submission(python_code, r1_error_msg) -> bool
  - format_r1_retry_skeleton(r1_error, prior_content, max_chars=12000) -> str

Called from:
  - src/ztare/validator/autoresearch_loop.py R1-retry handler
  - src/ztare/fit/mutation_suite_guard.py contract checks
"""
from __future__ import annotations

import ast
from typing import Optional


def requires_i_model_submission(rubric_data: dict | None) -> bool:
    """Return whether the substrate contract requires a scalar ``I_model``.

    Explicit ``require_i_model_in_submission`` remains authoritative.  When it
    is absent, infer only the narrow non-scalar cases that the apparatus can
    identify from rubric metadata: theorem packets and calibration/qualitative
    bounded-discriminator runs with fitting disabled.  Legacy rubrics still
    default to the scalar contract.
    """
    rubric = rubric_data or {}
    if "require_i_model_in_submission" in rubric:
        return bool(rubric.get("require_i_model_in_submission"))

    theorem_required = bool(
        (rubric.get("theorem_packet_contract") or {}).get("required_top_level_functions")
    )
    if theorem_required:
        return False

    rubric_mode = str(rubric.get("rubric_mode") or "").strip().lower()
    falsification_mode = str(rubric.get("falsification_mode") or "").strip().lower()
    fit_score_mode = str(rubric.get("fit_score_mode") or "").strip().lower()
    fit_disabled = (
        rubric.get("enable_fit_primitive") is False
        and not bool(rubric.get("enable_fit_primitive_features", False))
        and fit_score_mode == "none"
    )
    try:
        holdout_budget = int(rubric.get("holdout_budget") or 0)
    except (TypeError, ValueError):
        holdout_budget = 0
    no_holdout = rubric.get("holdout_hard_gate") is False or holdout_budget == 0
    qualitative_gates = (
        bool(rubric.get("disable_evidence_fit_gate", False))
        or bool(rubric.get("disable_uniqueness_gap_gate", False))
    )
    if (
        rubric_mode in {"calibration", "kepler"}
        and falsification_mode == "bounded_discriminator"
        and fit_disabled
        and no_holdout
        and qualitative_gates
    ):
        return False

    return True


def submission_contract_kind(rubric_data: dict | None) -> str:
    """Classify the top-level submission contract for prompt/validator routing."""
    rubric = rubric_data or {}
    if (rubric.get("theorem_packet_contract") or {}).get("required_top_level_functions"):
        return "theorem_packet"
    if requires_i_model_submission(rubric):
        return "numeric_model"
    return "assertion_suite"


# ---------------------------------------------------------------------------
# Contract detection
# ---------------------------------------------------------------------------

def detect_submission_contract(python_code: str) -> dict:
    """Inspect the mutator's test_model.py source and report which submission
    contract is satisfied.

    Returns a dict with keys:
      - "contract": "parametric_model" | "variational_lagrangian" |
        "fixed_parameter_model" | "mixed_parametric_variational" | None
      - "has_parametric_form": bool
      - "has_parameter_names": bool
      - "has_lagrangian": bool
      - "has_prediction": bool
      - "has_q_variables": bool
      - "has_background": bool
      - "has_nonempty_model_params": bool

    Returns dict with contract=None on parse failure.
    """
    has_form = False
    has_pnames = False
    has_lag = False
    has_pred = False
    has_qvars = False
    has_bg = False
    has_nonempty_mp = False
    try:
        tree = ast.parse(python_code or "")
    except SyntaxError:
        return {"contract": None, "has_parametric_form": False, "has_parameter_names": False,
                "has_lagrangian": False, "has_prediction": False, "has_q_variables": False,
                "has_background": False, "has_nonempty_model_params": False}
    for stmt in tree.body:
        if not isinstance(stmt, ast.Assign):
            continue
        for tgt in stmt.targets:
            if not isinstance(tgt, ast.Name):
                continue
            if tgt.id == "PARAMETRIC_FORM":
                has_form = True
            elif tgt.id == "PARAMETER_NAMES":
                has_pnames = True
            elif tgt.id == "LAGRANGIAN":
                has_lag = True
            elif tgt.id == "PREDICTION":
                has_pred = True
            elif tgt.id == "Q_VARIABLES":
                has_qvars = True
            elif tgt.id == "BACKGROUND":
                has_bg = True
            elif tgt.id == "MODEL_PARAMS":
                if isinstance(stmt.value, ast.Dict) and len(stmt.value.keys) > 0:
                    has_nonempty_mp = True

    parametric_model = has_form and has_pnames
    variational_lagrangian = has_lag and has_pred and has_pnames
    fixed_parameter_model = has_nonempty_mp

    if parametric_model and variational_lagrangian:
        contract = "mixed_parametric_variational"
    elif parametric_model:
        contract = "parametric_model"
    elif variational_lagrangian:
        contract = "variational_lagrangian"
    elif fixed_parameter_model:
        contract = "fixed_parameter_model"
    else:
        contract = None

    return {
        "contract": contract,
        "has_parametric_form": has_form,
        "has_parameter_names": has_pnames,
        "has_lagrangian": has_lag,
        "has_prediction": has_pred,
        "has_q_variables": has_qvars,
        "has_background": has_bg,
        "has_nonempty_model_params": has_nonempty_mp,
    }


# ---------------------------------------------------------------------------
# Mixed-contract detection (mutator submitted both parametric-model and
# variational/Lagrangian declarations simultaneously,
# and the R1 error is about the PARAMETRIC_FORM half — telling them to delete
# the broken PARAMETRIC_FORM is cleaner than telling them to fix it).
# ---------------------------------------------------------------------------

def is_mixed_parametric_variational_submission(python_code: str, r1_error_msg: Optional[str]) -> bool:
    """True iff the prior submission mixes parametric and variational declarations
    AND the R1 error mentions PARAMETRIC_FORM. In that case the cleanest
    advice is to delete PARAMETRIC_FORM and rely on the variational/Lagrangian declaration.
    """
    if not r1_error_msg or "PARAMETRIC_FORM" not in r1_error_msg:
        return False
    detect = detect_submission_contract(python_code)
    return detect["contract"] == "mixed_parametric_variational"


# ---------------------------------------------------------------------------
# R1 retry skeleton builder (was inline in autoresearch_loop.py:5946-6020)
# ---------------------------------------------------------------------------

_PARAMETRIC_MODEL_TEMPLATE = """\
──────────────────────────────────────────────────────────────
PARAMETRIC MODEL DECLARATION — PARAMETRIC_FORM
──────────────────────────────────────────────────────────────
```python
import math

# REQUIRED at module scope (NOT inside a function, NOT inside `if __name__`):
MODEL_PARAMS = {}                  # leave empty; scipy fills it
PARAMETER_NAMES = []               # fill only if this project fits params
INIT_RANGE = {}                    # bounds for each named param
PARAMETRIC_FORM = (                # MUST be a string of valid Python expression
    "0.5"
)

def I_model(features, params=None):
    p = params if params is not None else MODEL_PARAMS
    # ... your math here, returning float
    return ...

if __name__ == '__main__':
    pass
```
"""

_VARIATIONAL_LAGRANGIAN_TEMPLATE = """\
──────────────────────────────────────────────────────────────
VARIATIONAL/LAGRANGIAN DECLARATION — LAGRANGIAN + PREDICTION
──────────────────────────────────────────────────────────────
```python
import math

# REQUIRED at module scope:
MODEL_PARAMS = {}
PARAMETER_NAMES = ['m2', 'lam', 'J0']   # your Lagrangian's parameters
INIT_RANGE = {'m2': (0.01, 5.0), 'lam': (0.01, 5.0), 'J0': (0.01, 5.0)}

# Newton-mode declaration: GP-180 will compute Euler-Lagrange,
# solve for steady-state q, substitute into PREDICTION, and emit
# the apparatus-ready PARAMETRIC_FORM automatically.
LAGRANGIAN = (
    "q_dot**2/2 - 0.5*m2*q**2 - 0.25*lam*q**4 + q*(J0/log_d)"
)
Q_VARIABLES = ['q']
BACKGROUND = ['log_d']             # which features the source J uses
PREDICTION = "q"                   # closed-form g_obs in q + features

def I_model(features, params=None):
    # Optional: GP-180 may need this fallback. Manually derive a closed
    # form for q at steady state if you want, OR return 0.5 and let GP-180
    # supersede via its sympy-derived PARAMETRIC_FORM.
    return 0.5

if __name__ == '__main__':
    pass
```
"""

_UNIVERSAL_DONTS = """\
──────────────────────────────────────────────────────────────
Universal don'ts (apply to both numeric contracts):
  - Do NOT import project feature tables (`features`, `FEATURES`,
    `visible_rows`, `holdout_rows`) unless evidence explicitly requires it.
  - Do NOT call I_model(...) at module level (MODEL_PARAMS is {} at import).
  - Do NOT call helper functions inside PARAMETRIC_FORM (whitelist rejects).
  - Do NOT put PARAMETER_NAMES, PARAMETRIC_FORM, or LAGRANGIAN inside a
    function or inside `if __name__`. They MUST be at module scope.
  - Debug prints belong in `if __name__ == '__main__':` ONLY.
──────────────────────────────────────────────────────────────
"""


def _format_theorem_packet_retry_skeleton(
    r1_error: str,
    prior_content: str,
    *,
    rubric_data: dict,
    max_prior_chars: int,
    retry_error_history: list[str] | None = None,
) -> str:
    contract = rubric_data.get("theorem_packet_contract") or {}
    required = list(contract.get("required_top_level_functions") or [])
    fn_lines = "\n".join(f"def {name}():\n    return {{...}}\n" for name in required)
    return (
        "Your prior theorem-packet submission was rejected by the R1 lint check "
        "(NOT a scientific failure — just a contract/import violation). Specific error:\n\n"
        f"  {r1_error}\n\n"
        f"{_format_retry_error_history(retry_error_history)}"
        "This substrate is NOT a scalar PARAMETRIC_FORM/LAGRANGIAN fit. Do not switch "
        "to the generic numeric-declaration template. Preserve the theorem-packet science "
        "and repair the Python/import issue in place.\n\n"
        "Required module-scope API:\n"
        "```python\n"
        f"{fn_lines}"
        "```\n"
        "Rules:\n"
        "  - define every required function at top level\n"
        "  - I_model/PARAMETRIC_FORM/LAGRANGIAN are optional compatibility only, not the main result\n"
        "  - no module-level calls, heavy assertions, or side effects at import\n"
        "  - keep imports stdlib-only unless the evidence explicitly allows more\n\n"
        "RESUBMIT THE COMPLETE SUBMISSION: thesis prose plus test_model.py. "
        "The iteration counter has NOT advanced; this is a free retry.\n\n"
        "Your prior submission was:\n"
        f"```\n{(prior_content or '')[:max_prior_chars]}\n```\n"
    )


def _format_assertion_suite_retry_skeleton(
    r1_error: str,
    prior_content: str,
    *,
    max_prior_chars: int,
    retry_error_history: list[str] | None = None,
) -> str:
    return (
        "Your prior qualitative falsification-suite submission was rejected by "
        "the R1 lint check. Specific error:\n\n"
        f"  {r1_error}\n\n"
        f"{_format_retry_error_history(retry_error_history)}"
        "This substrate is evaluated through thesis prose plus a portable "
        "assertion suite. Do not switch to a scalar numeric-declaration template.\n\n"
        "Required shape:\n"
        "```python\n"
        "import math\n\n"
        "def test_mechanism_is_bounded():\n"
        "    # Encode a small deterministic check against the stated mechanism.\n"
        "    assert True\n\n"
        "def test_named_rival_is_not_equivalent():\n"
        "    # Encode the strongest rival as a distinct condition.\n"
        "    assert True\n\n"
        "if __name__ == '__main__':\n"
        "    test_mechanism_is_bounded()\n"
        "    test_named_rival_is_not_equivalent()\n"
        "```\n\n"
        "Rules:\n"
        "  - use stdlib-only Python and plain assert statements\n"
        "  - no I_model, PARAMETRIC_FORM, LAGRANGIAN, MODEL_PARAMS, "
        "PARAMETER_NAMES, or INIT_RANGE unless the rubric explicitly asks for a "
        "numeric predictor\n"
        "  - no module-level execution except definitions and constants\n"
        "  - keep the thesis prose; repair the Python block in place\n\n"
        "RESUBMIT THE COMPLETE SUBMISSION: thesis prose plus test_model.py. "
        "The iteration counter has NOT advanced; this is a free retry.\n\n"
        "Your prior submission was:\n"
        f"```\n{(prior_content or '')[:max_prior_chars]}\n```\n"
    )


def format_r1_retry_skeleton(
    r1_error: str,
    prior_content: str,
    *,
    max_prior_chars: int = 12000,
    rubric_data: dict | None = None,
    retry_error_history: list[str] | None = None,
) -> str:
    """Assemble the R1 retry prompt for the numeric submission contract.

    Detects the mixed parametric+variational case (mutator submitted both
    declarations and PARAMETRIC_FORM has the bug) and prepends an explicit
    advisory to keep the variational/Lagrangian declaration.

    Args:
      r1_error: the specific R1 lint error message from the apparatus
      prior_content: the mutator's previous response text (truncated)
      max_prior_chars: cap on the included prior_content (default 12000)
      retry_error_history: same-iteration R1 errors seen so far, including
        the current error. Used to avoid repeating an earlier failed repair
        shape when the latest error changes.

    Returns: complete retry prompt as a single string.
    """
    contract_kind = submission_contract_kind(rubric_data)
    if contract_kind == "theorem_packet":
        return _format_theorem_packet_retry_skeleton(
            r1_error,
            prior_content,
            rubric_data=rubric_data,
            max_prior_chars=max_prior_chars,
            retry_error_history=retry_error_history,
        )
    if contract_kind == "assertion_suite":
        return _format_assertion_suite_retry_skeleton(
            r1_error,
            prior_content,
            max_prior_chars=max_prior_chars,
            retry_error_history=retry_error_history,
        )

    mixed_advice = ""
    if is_mixed_parametric_variational_submission(prior_content or "", r1_error or ""):
        mixed_advice = (
            "\nMixed numeric declarations detected: your prior submission contained both\n"
            "LAGRANGIAN and PARAMETRIC_FORM, and the R1 error is about PARAMETRIC_FORM.\n"
            "Delete PARAMETRIC_FORM entirely and keep the variational/Lagrangian declaration\n"
            "(LAGRANGIAN + PREDICTION + PARAMETER_NAMES). GP-180 will derive the\n"
            "apparatus-ready expression via sympy; you do not need both declarations.\n"
        )

    return (
        "Your prior submission was rejected by the R1 lint check (NOT a "
        "scientific failure — just a contract violation). Specific error:\n\n"
        f"  {r1_error}\n\n"
        f"{_format_retry_error_history(retry_error_history)}"
        f"{mixed_advice}"
        "═══════════════════════════════════════════════════════════════\n"
        "MINIMAL VALID NUMERIC DECLARATION — copy ONE contract below\n"
        "═══════════════════════════════════════════════════════════════\n"
        "Two accepted numeric declarations, mutually exclusive — pick one.\n"
        "If your prior submission had a LAGRANGIAN block, prefer the variational/Lagrangian\n"
        "declaration: GP-180 will solve Euler-Lagrange via sympy and emit\n"
        "PARAMETRIC_FORM automatically. The R1 strike that bounced you was a\n"
        "contract violation, not a directive to abandon the Lagrangian.\n\n"
        f"{_PARAMETRIC_MODEL_TEMPLATE}\n"
        f"{_VARIATIONAL_LAGRANGIAN_TEMPLATE}\n"
        "Either declaration is valid. The variational/Lagrangian declaration is preferred for invariant_search\n"
        "rubric mode and for any case where you would otherwise need a cubic-root\n"
        "or special-function call (CubicRealRoot / cbrt / Cardano formula) in\n"
        "PARAMETRIC_FORM — those trigger the AST whitelist rejection. Submit the\n"
        "Lagrangian instead and let the apparatus handle the algebra.\n\n"
        f"{_UNIVERSAL_DONTS}\n"
        "RESUBMIT THE COMPLETE SUBMISSION. Your response MUST contain "
        "BOTH of the following blocks:\n"
        "  1. A thesis prose section (markdown, scientific argument)\n"
        "  2. A Python falsification suite section (test_model.py) — "
        "starting with one numeric declaration above.\n\n"
        "Common contract bugs (this iter has now seen all three — DO NOT repeat):\n"
        "  - PARAMETER_NAMES wrapped in `if __name__ == '__main__':` → must be at module scope\n"
        "  - Module-level I_model(...) call (e.g., for sanity check) → triggers KeyError on empty MODEL_PARAMS\n"
        "  - PARAMETRIC_FORM calls a helper (e.g., _model_expr(...)) → whitelist rejects it; inline the expression\n"
        "  - PARAMETRIC_FORM with unmatched paren → must be valid Python expression string\n\n"
        "Fix the specific contract violation above. Preserve the SCIENCE "
        "from your prior submission (thesis prose, parametric_form math, "
        "param names). The iteration counter has NOT advanced; this is a "
        "free retry.\n\n"
        "Your prior submission was:\n"
        f"```\n{(prior_content or '')[:max_prior_chars]}\n```\n"
    )


def _format_retry_error_history(errors: list[str] | None) -> str:
    if not errors:
        return ""
    cleaned: list[str] = []
    for raw in errors:
        text = " ".join(str(raw or "").split())
        if not text:
            continue
        if cleaned and cleaned[-1] == text:
            continue
        cleaned.append(text)
    if len(cleaned) <= 1:
        return ""
    lines = [
        "Same-iteration R1 strike history:",
    ]
    for idx, err in enumerate(cleaned[-3:], start=max(1, len(cleaned) - 2)):
        tail = err[:500] + ("..." if len(err) > 500 else "")
        lines.append(f"  {idx}. {tail}")
    lines.extend(
        [
            "",
            "The next submission must satisfy the current error without reintroducing",
            "any earlier strike in this list.",
            "",
        ]
    )
    return "\n".join(lines)
