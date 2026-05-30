"""GP-180 Path A / Path B submission helpers.

Centralizes logic that was previously inline in autoresearch_loop.py and
mutation_suite_guard.py for detecting which submission contract a mutator
is using and assembling R1-retry prompts that respect both paths.

Three valid submission paths for the test_model.py contract:

  PATH A (legacy / hand-derived closed form)
      MODEL_PARAMS, PARAMETER_NAMES, INIT_RANGE, PARAMETRIC_FORM, I_model

  PATH B (Newton-mode / GP-180 sympy auto-derivation)
      MODEL_PARAMS, PARAMETER_NAMES, INIT_RANGE,
      LAGRANGIAN, Q_VARIABLES, BACKGROUND, PREDICTION, I_model
      (apparatus auto-derives PARAMETRIC_FORM via sympy E-L solving)

  PATH H (theory-pinned hardcoded constants — only when constants are known)
      MODEL_PARAMS = {'a': 0.5, ...}, I_model
      (no PARAMETRIC_FORM or LAGRANGIAN; constants are not fit)

This module exposes:
  - detect_submission_path(python_code) -> {"path": str, "decls": dict}
  - is_hedge_submission(python_code, r1_error_msg) -> bool
  - format_r1_retry_skeleton(r1_error, prior_content, max_chars=12000) -> str

Called from:
  - src/ztare/validator/autoresearch_loop.py R1-retry handler
  - src/ztare/fit/mutation_suite_guard.py contract checks
"""
from __future__ import annotations

import ast
from typing import Optional


# ---------------------------------------------------------------------------
# Path detection
# ---------------------------------------------------------------------------

def detect_submission_path(python_code: str) -> dict:
    """Inspect the mutator's test_model.py source and report which submission
    path is satisfied.

    Returns a dict with keys:
      - "path": "A" | "B" | "H" | "A+B" (hedge) | None (no path)
      - "has_parametric_form": bool
      - "has_parameter_names": bool
      - "has_lagrangian": bool
      - "has_prediction": bool
      - "has_q_variables": bool
      - "has_background": bool
      - "has_nonempty_model_params": bool

    Returns dict with path=None on parse failure.
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
        return {"path": None, "has_parametric_form": False, "has_parameter_names": False,
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

    path_a = has_form and has_pnames
    path_b = has_lag and has_pred and has_pnames
    path_h = has_nonempty_mp

    if path_a and path_b:
        path = "A+B"
    elif path_a:
        path = "A"
    elif path_b:
        path = "B"
    elif path_h:
        path = "H"
    else:
        path = None

    return {
        "path": path,
        "has_parametric_form": has_form,
        "has_parameter_names": has_pnames,
        "has_lagrangian": has_lag,
        "has_prediction": has_pred,
        "has_q_variables": has_qvars,
        "has_background": has_bg,
        "has_nonempty_model_params": has_nonempty_mp,
    }


# ---------------------------------------------------------------------------
# Hedge detection (mutator submitted both Path A and Path B simultaneously,
# and the R1 error is about the PARAMETRIC_FORM half — telling them to delete
# the broken PARAMETRIC_FORM is cleaner than telling them to fix it).
# ---------------------------------------------------------------------------

def is_hedge_submission(python_code: str, r1_error_msg: Optional[str]) -> bool:
    """True iff the prior submission has BOTH Path A and Path B declared
    AND the R1 error mentions PARAMETRIC_FORM. In that case the cleanest
    advice is "delete the PARAMETRIC_FORM and rely on Path B."
    """
    if not r1_error_msg or "PARAMETRIC_FORM" not in r1_error_msg:
        return False
    detect = detect_submission_path(python_code)
    return detect["path"] == "A+B"


# ---------------------------------------------------------------------------
# R1 retry skeleton builder (was inline in autoresearch_loop.py:5946-6020)
# ---------------------------------------------------------------------------

_PATH_A_SKELETON = """\
──────────────────────────────────────────────────────────────
PATH A — PARAMETRIC_FORM (legacy / hand-derived closed form)
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

_PATH_B_SKELETON = """\
──────────────────────────────────────────────────────────────
PATH B — LAGRANGIAN + PREDICTION (Newton-mode, GP-180 auto-derives)
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
Universal don'ts (apply to both paths):
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
) -> str:
    contract = rubric_data.get("theorem_packet_contract") or {}
    required = list(contract.get("required_top_level_functions") or [])
    fn_lines = "\n".join(f"def {name}():\n    return {{...}}\n" for name in required)
    return (
        "Your prior theorem-packet submission was rejected by the R1 lint check "
        "(NOT a scientific failure — just a contract/import violation). Specific error:\n\n"
        f"  {r1_error}\n\n"
        "This substrate is NOT a scalar PARAMETRIC_FORM/LAGRANGIAN fit. Do not switch "
        "to the generic Path A/Path B scaffold. Preserve the theorem-packet science "
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


def format_r1_retry_skeleton(
    r1_error: str,
    prior_content: str,
    *,
    max_prior_chars: int = 12000,
    rubric_data: dict | None = None,
) -> str:
    """Assemble the R1 retry prompt that offers BOTH Path A and Path B
    skeletons. Detects the hedge case (mutator submitted both paths and
    PARAMETRIC_FORM has the bug) and prepends an explicit "delete the
    PARAMETRIC_FORM, keep the LAGRANGIAN" advisory.

    Args:
      r1_error: the specific R1 lint error message from the apparatus
      prior_content: the mutator's previous response text (truncated)
      max_prior_chars: cap on the included prior_content (default 12000)

    Returns: complete retry prompt as a single string.
    """
    if rubric_data and (rubric_data.get("theorem_packet_contract") or {}).get(
        "required_top_level_functions"
    ):
        return _format_theorem_packet_retry_skeleton(
            r1_error,
            prior_content,
            rubric_data=rubric_data,
            max_prior_chars=max_prior_chars,
        )

    hedge_advice = ""
    if is_hedge_submission(prior_content or "", r1_error or ""):
        hedge_advice = (
            "\n⚠️  HEDGE DETECTED: your prior submission contained both LAGRANGIAN\n"
            "and PARAMETRIC_FORM, and the R1 error is about the PARAMETRIC_FORM.\n"
            "DELETE the PARAMETRIC_FORM entirely. Path B (LAGRANGIAN + PREDICTION +\n"
            "PARAMETER_NAMES) is sufficient on its own — GP-180 will auto-derive\n"
            "the apparatus-ready PARAMETRIC_FORM via sympy. Stop trying to fix\n"
            "the broken PARAMETRIC_FORM; just remove it. You DO NOT need both.\n"
        )

    return (
        "Your prior submission was rejected by the R1 lint check (NOT a "
        "scientific failure — just a contract violation). Specific error:\n\n"
        f"  {r1_error}\n\n"
        f"{hedge_advice}"
        "═══════════════════════════════════════════════════════════════\n"
        "MINIMAL VALID SKELETON — copy ONE of the two paths below\n"
        "═══════════════════════════════════════════════════════════════\n"
        "Two equally-acceptable submission paths, MUTUALLY EXCLUSIVE — pick ONE,\n"
        "do NOT submit both. If your prior submission had a LAGRANGIAN block,\n"
        "prefer PATH B (the GP-180 lagrangian_derivation primitive will solve\n"
        "Euler-Lagrange via sympy and emit PARAMETRIC_FORM automatically — you\n"
        "do NOT need to manually invert the cubic). The R1 strike that bounced\n"
        "you was a contract violation, not a directive to abandon the Lagrangian.\n\n"
        f"{_PATH_A_SKELETON}\n"
        f"{_PATH_B_SKELETON}\n"
        "Either skeleton is valid. Path B is preferred for invariant_search\n"
        "rubric mode and for any case where you would otherwise need a cubic-root\n"
        "or special-function call (CubicRealRoot / cbrt / Cardano formula) in\n"
        "PARAMETRIC_FORM — those trigger the AST whitelist rejection. Submit the\n"
        "Lagrangian instead and let the apparatus handle the algebra.\n\n"
        f"{_UNIVERSAL_DONTS}\n"
        "RESUBMIT THE COMPLETE SUBMISSION. Your response MUST contain "
        "BOTH of the following blocks:\n"
        "  1. A thesis prose section (markdown, scientific argument)\n"
        "  2. A Python falsification suite section (test_model.py) — "
        "starting with PATH A or PATH B above.\n\n"
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
