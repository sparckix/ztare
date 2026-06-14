from __future__ import annotations

import ast
import sys
import traceback
from io import StringIO
from pathlib import Path
from typing import Optional


NO_SUITE_SENTINEL = "assert False, 'AI failed to provide a testable falsification suite.'"


def validate_python_suite_candidate(python_code: str | None) -> None:
    stripped = (python_code or "").strip()
    if not stripped:
        raise ValueError(
            "Missing required Python falsification suite block; reject candidate before evaluation."
        )
    if stripped == NO_SUITE_SENTINEL:
        raise ValueError(
            "Mutator emitted the no-suite sentinel falsification block; reject candidate before evaluation."
        )


def _ast_check_params_contract(python_code: str) -> Optional[str]:
    """GP-156 Bug #14 (2026-04-25): the apparatus-fits-params contract
    is voluntary opt-in. The mutator can write
    ``def I_model(features, params): return params['a'] * ...`` and
    silently NOT declare PARAMETRIC_FORM / PARAMETER_NAMES at module
    level. The apparatus then correctly skips fit_primitive_features and
    MODEL_PARAMS stays {}. At gate time I_model raises KeyError on the
    first ``params['a']`` access — the iter is consumed for a contract
    miss.

    Rule: if any function body in the module references ``params[...]``
    OR ``params.get(...)``, then EITHER
      (a) PARAMETRIC_FORM (str) AND PARAMETER_NAMES (list) are declared
          at module level (apparatus will fit), OR
      (b) MODEL_PARAMS is declared as a NON-EMPTY dict at module level
          (mutator hardcoded the constants).
    Otherwise: R1 reject with sharp diagnostic.
    """
    try:
        tree = ast.parse(python_code)
    except SyntaxError:
        return None
    uses_params = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            v = node.value
            if isinstance(v, ast.Name) and v.id == "params":
                uses_params = True
                break
        if isinstance(node, ast.Attribute):
            v = node.value
            if isinstance(v, ast.Name) and v.id == "params" and node.attr in ("get", "setdefault"):
                uses_params = True
                break
    if not uses_params:
        return None
    has_form = False
    has_names = False
    has_lagrangian = False
    has_prediction = False
    has_nonempty_model_params = False
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            for tgt in stmt.targets:
                if isinstance(tgt, ast.Name):
                    if tgt.id == "PARAMETRIC_FORM":
                        has_form = True
                    elif tgt.id == "PARAMETER_NAMES":
                        has_names = True
                    elif tgt.id == "LAGRANGIAN":
                        has_lagrangian = True
                    elif tgt.id == "PREDICTION":
                        has_prediction = True
                    elif tgt.id == "MODEL_PARAMS":
                        if isinstance(stmt.value, ast.Dict) and len(stmt.value.keys) > 0:
                            has_nonempty_model_params = True
    # Three valid contracts:
    #   Parametric model: PARAMETRIC_FORM + PARAMETER_NAMES
    #   Variational/Lagrangian model: LAGRANGIAN + PREDICTION + PARAMETER_NAMES
    #     (lagrangian_derivation auto-derives the apparatus-ready PARAMETRIC_FORM)
    #   Fixed-parameter model: MODEL_PARAMS non-empty
    parametric_model_ok = has_form and has_names
    variational_lagrangian_ok = has_lagrangian and has_prediction and has_names
    fixed_parameter_model_ok = has_nonempty_model_params
    if parametric_model_ok or variational_lagrangian_ok or fixed_parameter_model_ok:
        return None
    return (
        "Contract violation: I_model body references `params[...]` but "
        "none of the three valid numeric contracts is satisfied. At gate "
        "time MODEL_PARAMS={} so I_model will KeyError on the first "
        "`params['x']` access. Choose ONE:\n"
        "  Parametric model declaration — apparatus scipy-fits PARAMETRIC_FORM:\n"
        "      PARAMETRIC_FORM = \"params['a'] * features['x'] + params['b']\"\n"
        "      PARAMETER_NAMES = ['a', 'b']\n"
        "      MODEL_PARAMS = {}      # apparatus fills with fitted values\n"
        "  Variational/Lagrangian declaration — GP-180 lagrangian_derivation auto-derives:\n"
        "      LAGRANGIAN = \"q_dot**2/2 - 0.5*m2*q**2 - 0.25*lam*q**4 + q*(J0/log_d)\"\n"
        "      PREDICTION = \"q\"\n"
        "      PARAMETER_NAMES = ['m2', 'lam', 'J0']\n"
        "      Q_VARIABLES = ['q'];  BACKGROUND = ['log_d']\n"
        "      MODEL_PARAMS = {}      # GP-180 + apparatus fill via sympy + scipy\n"
        "  Fixed-parameter model — only when constants are pinned by theory:\n"
        "      MODEL_PARAMS = {'a': 0.5, 'b': 1.0}\n"
        "Reference: GP-156 Proposal 3 + GP-180 Lagrangian primitive."
    )


def _ast_check_no_module_level_i_model_call(python_code: str) -> Optional[str]:
    """GP-157 programmatic enforcement (2026-04-25): reject module-level
    `I_model(...)` calls at AST stage, BEFORE R1 import-time exec.

    Background: prose-based prompt warnings ("DO NOT call I_model at
    module level") are advisory — the mutator (especially gpt-4.1) keeps
    ignoring them. Each violation costs an API call + harness defect
    classification. The fix: enforce the contract MECHANICALLY in the
    AST, not in the prompt. Same pattern as `_safe_compile_form`'s
    AST whitelist (which is enforcing): code-as-contract beats
    prose-as-contract.

    Returns None if no violation; returns diagnostic string if violation
    found. Caller raises ValueError with that diagnostic.

    Detection rules (only flags TRUE module-level calls):
      - I_model(...) at module top level (NOT inside a FunctionDef,
        ClassDef, or Lambda)
      - Including `assert I_model(...) > 0` and `_x = I_model(...)`
      - NOT flagging I_model() calls inside helper functions —
        those don't crash import. (Note: the apparatus does NOT
        invoke private helpers, so deferring asserts there leaves
        I_model unverified; orchestrator/contract_adherence.py
        catches that pattern as `deferred_assert_helper`.)

    Returns None if no module-level call found.
    """
    try:
        tree = ast.parse(python_code)
    except SyntaxError:
        return None  # let downstream syntax check handle this

    def _is_main_guard(n: ast.AST) -> bool:
        """True if `n` is `if __name__ == "__main__":` (or inverse)."""
        if not isinstance(n, ast.If):
            return False
        test = n.test
        if not isinstance(test, ast.Compare) or len(test.ops) != 1:
            return False
        if not isinstance(test.ops[0], ast.Eq):
            return False
        # Either side: __name__ == "__main__"
        sides = [test.left] + list(test.comparators)
        names = [s.id for s in sides if isinstance(s, ast.Name)]
        consts = [s.value for s in sides if isinstance(s, ast.Constant)]
        return ("__name__" in names) and ("__main__" in consts)

    violations: list[tuple[int, str]] = []
    for node in tree.body:  # ONLY module-level statements
        # Skip the `if __name__ == "__main__":` block — its body only
        # runs when the module is executed directly, never at import.
        # The apparatus IMPORTS test_model.py, so this block is dead at
        # gate time. Allow I_model() debug calls here per Contract C hint.
        if _is_main_guard(node):
            continue
        for sub in ast.walk(node):
            # Skip if we're inside a function or class definition
            if sub is not node and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                # Don't recurse into function bodies — those calls only
                # fire when the function is called, not at module load.
                # ast.walk gives us all descendants; we filter by
                # checking the TOP-LEVEL container.
                break
            if isinstance(sub, ast.Call):
                func = sub.func
                if isinstance(func, ast.Name) and func.id == "I_model":
                    violations.append((sub.lineno, "I_model(...)"))
    if not violations:
        return None
    line_numbers = ", ".join(f"line {ln}" for ln, _ in violations)
    return (
        f"Module-level I_model(...) call detected at {line_numbers}. "
        f"POLICY: no I_model(...) calls at module scope are permitted, "
        f"regardless of what params dict you pass to them. This rule "
        f"applies even if you build a complete probe dict (e.g., "
        f"`I_model(_row, _probe_params)`) — the call is rejected on "
        f"grammar, not on whether it would happen to succeed at import. "
        f"Reasons: (1) module-level calls slow import; (2) the apparatus's "
        f"gate harness already calls I_model on every VISIBLE_SET row and "
        f"checks finite-float + MRE, so any module-level sanity assert is "
        f"redundant; (3) when MODEL_PARAMS={{}} (the pre-fit state), "
        f"calls reading `params['key']` directly raise KeyError and break "
        f"module import entirely. "
        f"FIX: move every I_model(...) call into the `if __name__ == "
        f"\"__main__\":` block (the apparatus does not run that block, "
        f"so it cannot break import). For the I_model definition itself, "
        f"make import-safety OUTSIDE PARAMETRIC_FORM: build a local dict "
        f"`p = dict(DEFAULT_PARAMS); p.update(params or {{}})` and then "
        f"evaluate/calculate with `p`. PARAMETRIC_FORM should reference "
        f"`params['key']` only. Do NOT write numeric defaults inside "
        f"PARAMETRIC_FORM as `params.get('key', 0.34)`: those defaults "
        f"become hidden decision-critical constants and trigger R20/R21 "
        f"effective-K laundering. "
        f"Do NOT hide module-level calls in private helpers like "
        f"`_post_fit_sanity()` — the apparatus does not invoke them, so "
        f"that path leaves I_model untested AND triggers this same R1 "
        f"strike at the helper's call site."
    )


def _ast_check_lagrangian_source_asymptote(python_code: str) -> Optional[str]:
    """GP-180 variational/Lagrangian asymptotic-divergence guard (2026-05-02).

    For substrates with the inversion-limit axiom (α(d → ∞) → 0), a Lagrangian
    whose source J contains divergent-with-d terms — e.g. `log_d`, `log(d)`,
    `log10_d`, or polynomials in d — produces a steady-state q that grows
    without bound, violating the ambient gate by construction. The mutator's
    iter-1 quartic-Lagrangian failure (J ∝ β·log_d → q diverges → α=0.49 at
    d=1e6 vs observed 0.0015, 326× violation) is the canonical case.

    This guard scans the LAGRANGIAN string for forbidden source-divergence
    patterns when a variational/Lagrangian declaration is detected. Returns None if it is not used or
    the source is asymptotically clean; returns diagnostic string if a
    forbidden pattern is found.

    Forbidden patterns (in the LAGRANGIAN expression):
      - log_d, log10_d, ln_d (raw-name references to log-of-d features)
      - log(d), log10(d), ln(d) (function-call form)
      - d**k or d^k for positive k (polynomial-in-d divergence)
      - explicit d * (anything) at top level of source coupling

    Returns: None if guard is satisfied or the Lagrangian contract is not used; diagnostic str
    if a forbidden divergent term is found.
    """
    import re
    try:
        tree = ast.parse(python_code)
    except SyntaxError:
        return None  # let other checks handle syntax

    lagrangian_str: Optional[str] = None
    has_prediction = False
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            for tgt in stmt.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "LAGRANGIAN":
                    if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                        lagrangian_str = stmt.value.value
                    elif isinstance(stmt.value, ast.JoinedStr):
                        # f-string: concatenate the constant parts
                        parts = []
                        for v in stmt.value.values:
                            if isinstance(v, ast.Constant):
                                parts.append(str(v.value))
                        lagrangian_str = "".join(parts) if parts else None
                elif isinstance(tgt, ast.Name) and tgt.id == "PREDICTION":
                    has_prediction = True

    if lagrangian_str is None or not has_prediction:
        return None  # not a variational/Lagrangian declaration; defer to other guards

    # Forbidden patterns in the LAGRANGIAN string. We're looking for these
    # appearing as identifiers or function calls in the action expression.
    forbidden = []
    L = lagrangian_str
    # log-of-d feature references (bare identifier names)
    for pat in (r"\blog_d\b", r"\blog10_d\b", r"\bln_d\b"):
        if re.search(pat, L):
            forbidden.append(re.search(pat, L).group(0))
    # log-call form: log(d), log10(d), ln(d) where d is the bare arg
    for pat in (r"\blog\s*\(\s*d\s*\)", r"\blog10\s*\(\s*d\s*\)",
                r"\bln\s*\(\s*d\s*\)"):
        m = re.search(pat, L)
        if m:
            forbidden.append(m.group(0))
    # Polynomial-in-d: d**k or d^k for positive k. Detect d** with positive
    # numeric exponent. Also bare `d` multiplied by params at top level.
    for m in re.finditer(r"\bd\s*\*\*\s*([0-9.]+)", L):
        try:
            k = float(m.group(1))
            if k > 0:
                forbidden.append(f"d**{k}")
        except ValueError:
            pass
    # bare 'd*' (not 'd**' or '_d') at start of a multiplicative chunk
    # — this catches J ∝ d * something. Conservative: only flag if 'd' appears
    # as a TERM in the source-coupling part (after the q* sign).
    # Heuristic: look for ' d *' or ' d+' etc. as a standalone term.
    # We skip this heuristic for false-positive risk; the named-feature checks
    # above cover the most common substrate shapes.

    if not forbidden:
        return None

    forbidden_uniq = sorted(set(forbidden))
    return (
        f"LAGRANGIAN asymptotic-divergence guard: the LAGRANGIAN "
        f"expression contains divergent-with-d term(s) {forbidden_uniq}. "
        f"Per evidence.txt 'HARD STRUCTURAL CONSTRAINT 2 — Asymptotic "
        f"inversion limit', any candidate must satisfy α(d → ∞) → 0. A "
        f"Lagrangian source J that grows with d (log d, d^k for k > 0) "
        f"forces the steady-state field q to grow with d, violating the "
        f"ambient-gate axiom by construction.\n\n"
        f"FIX: replace the divergent term in the source J. Allowed examples:\n"
        f"  J ∝ 1/d, 1/d^k for k > 0, 1/log(d), exp(-β·d), q/d, q·d^(-k)\n"
        f"Forbidden (auto-rejected): log(d), log_d, log10_d, d^k for k > 0, "
        f"polynomials in d.\n"
        f"This guard fires before scipy.optimize burns compute on a form "
        f"that cannot pass the d=1e6 ambient gate. Reference: substrate "
        f"evidence.txt HARD STRUCTURAL CONSTRAINT 2 + iter-1 quartic-"
        f"Lagrangian failure (predicted q=0.49 at d=1e6 vs observed 0.0015, "
        f"326× ambient-gate violation)."
    )


def validate_python_suite_imports(
    python_code: str,
    *,
    project_dir: Optional[str] = None,
    timeout_seconds: float = 5.0,
    require_i_model: bool = True,
    require_parametric_form: bool = False,
    rubric_data: Optional[dict] = None,
) -> None:
    """Dry-run module-level execution to catch import-time crashes.

    Specifically catches the iter-3 / gp155-iter-1 failure mode where the
    mutator emits a thesis whose top-level code (function defs, top-level
    asserts, top-level fit-param construction) raises TypeError /
    AttributeError / NameError / ImportError on module load. The harness
    would otherwise discover this only when gate_harness.py tries to
    import test_model.py — wasting an iteration on a contract failure.

    Two-stage check:
      1. Syntax check via ``compile`` — catches SyntaxError early.
      2. Sandboxed exec in a fresh namespace with PROJECT_DIR on
         sys.path so legitimate imports (e.g. ``from features import
         FEATURES``) resolve. Module-level top-level asserts that
         pass — fine. Anything that raises — surface as a diagnostic
         ValueError so the mutator gets clean feedback.

    Raises ValueError with a sharp diagnostic if the candidate cannot
    be loaded. Returns None on success.
    """
    code = (python_code or "").strip()
    if not code:
        return  # already covered by validate_python_suite_candidate

    # Stage 1: syntax check
    try:
        compiled = compile(code, "<mutator_test_model>", "exec")
    except SyntaxError as exc:
        raise ValueError(
            f"Python suite has a SyntaxError at line {exc.lineno}: {exc.msg}. "
            f"Fix syntax before resubmission."
        ) from exc

    # Stage 1b: GP-157 programmatic contract enforcement.
    # AST pre-flight rejects module-level I_model calls BEFORE the exec
    # sandbox runs. Faster diagnostic than waiting for R1 KeyError, AND
    # closes the prompt-ignored-by-mutator gap (gpt-4.1 sometimes ignores
    # prose warnings; AST contracts cannot be ignored).
    _violation = _ast_check_no_module_level_i_model_call(code)
    if _violation is not None:
        raise ValueError(_violation)

    # Stage 1c: GP-156 Bug #14 — params[...] requires either fit-contract
    # opt-in (PARAMETRIC_FORM + PARAMETER_NAMES) OR hardcoded MODEL_PARAMS.
    _violation_params = _ast_check_params_contract(code)
    if _violation_params is not None:
        raise ValueError(_violation_params)

    # Stage 1c.5: GP-180 variational/Lagrangian asymptotic-divergence guard (2026-05-02).
    # Catches LAGRANGIAN whose source J contains divergent-with-d terms
    # (log_d, polynomials in d) that violate the inversion-limit axiom by
    # construction. RUBRIC-GATED: only enabled when the substrate's rubric
    # opts in via `enable_lagrangian_inversion_limit_guard: true`. This
    # avoids overfitting the apparatus to substrates that require α(d → ∞)
    # → 0 (gp154-style); substrates with growing-with-d forms (or no
    # asymptotic-axiom requirement) keep the legacy path. Default OFF.
    if rubric_data is not None and bool(
        rubric_data.get("enable_lagrangian_inversion_limit_guard", False)
    ):
        _violation_lag = _ast_check_lagrangian_source_asymptote(code)
        if _violation_lag is not None:
            raise ValueError(_violation_lag)

    # Stage 1d: GP-156 force-opt-in (2026-04-25). When the rubric flag
    # `enable_fit_primitive_features=true`, the substrate was explicitly
    # designed for the apparatus to fit constants — opting out by writing
    # hardcoded constants is gaming the contract, not solving the task.
    # gpt-4.1 was observed retreating to "no PARAMETRIC_FORM at all" after
    # K_law-budget rejections; this stage closes that escape route.
    if require_parametric_form:
        try:
            _tree_pf = ast.parse(code)
        except SyntaxError:
            _tree_pf = None
        _has_form = False
        _has_names = False
        # GP-180 variational/Lagrangian declaration (2026-05-02): the mutator may submit
        #   LAGRANGIAN + PREDICTION + Q_VARIABLES + BACKGROUND
        # instead of PARAMETRIC_FORM. The lagrangian_derivation primitive
        # solves Euler-Lagrange via sympy and emits PARAMETRIC_FORM
        # automatically downstream. Accept this contract here so the guard
        # does not auto-reject the Lagrangian before the apparatus can derive.
        _has_lagrangian = False
        _has_prediction = False
        if _tree_pf is not None:
            for stmt in _tree_pf.body:
                if isinstance(stmt, ast.Assign):
                    for tgt in stmt.targets:
                        if isinstance(tgt, ast.Name):
                            if tgt.id == "PARAMETRIC_FORM":
                                _has_form = True
                            elif tgt.id == "PARAMETER_NAMES":
                                _has_names = True
                            elif tgt.id == "LAGRANGIAN":
                                _has_lagrangian = True
                            elif tgt.id == "PREDICTION":
                                _has_prediction = True
        # Parametric model satisfied: PARAMETRIC_FORM + PARAMETER_NAMES at module scope.
        # Variational/Lagrangian model satisfied: LAGRANGIAN + PREDICTION + PARAMETER_NAMES at module scope.
        parametric_model_ok = _has_form and _has_names
        variational_lagrangian_ok = _has_lagrangian and _has_prediction and _has_names
        if not (parametric_model_ok or variational_lagrangian_ok):
            raise ValueError(
                "Force-opt-in (rubric flag enable_fit_primitive_features=true): "
                "this substrate was designed for the apparatus to fit "
                "constants via scipy.optimize. You MUST declare ONE OF the "
                "following two contracts at module level:\n\n"
                "  Parametric model declaration: PARAMETRIC_FORM (str) AND PARAMETER_NAMES (list[str]).\n"
                "  Variational/Lagrangian declaration: LAGRANGIAN (str) AND PREDICTION (str) "
                "AND PARAMETER_NAMES (list[str]); Q_VARIABLES + BACKGROUND are recommended. "
                "GP-180 lagrangian_derivation will compute Euler-Lagrange via sympy and "
                "emit the apparatus-ready PARAMETRIC_FORM for you.\n\n"
                "Hardcoded constants will reliably miss the holdout gate; opting "
                "out is not a valid escape from the K_law budget. If K_law was "
                "tight, simplify the form (find structural compression — e.g., one "
                "parameter per modality-class instead of per modality) rather than "
                "removing the contract."
            )

    # Stage 2: sandboxed exec
    # GP-157 Bug #35 (2026-04-25 night): the sandbox previously set
    # `__name__ = "__main__"` which caused any `if __name__ == "__main__":`
    # debug block in the mutator's submission to RUN during the R1 dry-run.
    # That's a false-positive failure mode: at actual gate-time, the real
    # gate_harness.py IMPORTS test_model.py (import context, __name__ is
    # the module's import path, NOT "__main__"), so debug blocks do NOT
    # run there. Mutators following the standard Python `if __name__ ==
    # "__main__": ...` idiom for defensive debug code were tripping R1
    # with NameErrors that wouldn't fire at gate time. Fix: name the
    # sandbox after its actual context so `__main__`-gated debug blocks
    # stay dormant in the dry-run, matching the import-time semantics
    # that gate_harness will see. Generalizable apparatus protocol fix.
    sandbox: dict = {
        "__name__": "ztare_mutator_test_model_r1_dry_run",
        "__file__": "<mutator_test_model>",
    }
    saved_sys_path = list(sys.path)
    saved_stdout = sys.stdout
    saved_stderr = sys.stderr
    try:
        if project_dir and project_dir not in sys.path:
            sys.path.insert(0, project_dir)
        # Suppress stdout/stderr from the mutator's top-level code so they
        # don't leak into the loop's logs. Errors are captured by the
        # except below.
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        try:
            exec(compiled, sandbox)
        except AssertionError as exc:
            # Top-level asserts that fail are SUBSTANTIVE falsifiers
            # (the mutator's discriminator suite executed and disproved
            # itself). NOT a contract violation — let downstream gate
            # harness handle it as fail_assert.
            return
        except (TypeError, AttributeError, NameError, ImportError, ValueError) as exc:
            tb = traceback.format_exc(limit=4)
            raise ValueError(
                f"Python suite raised {type(exc).__name__} at module load "
                f"time: {exc}. The harness would crash before any gate "
                f"could be evaluated. Fix the import-time error before "
                f"resubmission. Traceback (last 4 frames):\n{tb}"
            ) from None
        except Exception as exc:  # noqa: BLE001
            tb = traceback.format_exc(limit=4)
            raise ValueError(
                f"Python suite raised unexpected {type(exc).__name__} at "
                f"module load time: {exc}. Fix before resubmission. "
                f"Traceback (last 4 frames):\n{tb}"
            ) from None
    finally:
        sys.path[:] = saved_sys_path
        sys.stdout = saved_stdout
        sys.stderr = saved_stderr

    # Stage 3 (lightweight): confirm the suite defines I_model. Many
    # substrates rely on this contract; missing I_model means the
    # gate_harness will fail with AttributeError on any row.
    # GP-156 fix (2026-04-25): some substrates (meta_audit / gp156 /
    # gp152 / gp153) submit attack-vector snippets, not predictors.
    # Make this check OPT-OUT via require_i_model=False parameter.
    # Default True preserves back-compat for predictor substrates.
    if require_i_model and "I_model" not in sandbox:
        # GP-157 v5.0 fix (2026-04-25 night): the contract hint must
        # match the substrate's ABI, not a hardcoded features-dict
        # signature. Read cage_meta.class from rubric (passed via
        # the project_dir's rubric.json) when available; default to
        # the abstract signature otherwise.
        signature_hint = "I_model(d, params=None)  # Contract C scalar 1d"
        try:
            if project_dir:
                import json as _json
                from pathlib import Path as _Path
                # Find rubric for this project
                _proj_name = _Path(project_dir).name
                _repo_root = _Path(project_dir).resolve().parents[1] if "projects" in str(project_dir) else None
                _rubric_path = _repo_root / "rubrics" / f"{_proj_name}.json" if _repo_root else None
                if _rubric_path and _rubric_path.exists():
                    _rd = _json.loads(_rubric_path.read_text())
                    _cls = ((_rd.get("cage_meta") or {}).get("class") or "").strip().lower()
                    if _cls == "nd_features":
                        signature_hint = "I_model(features)  # Contract B feature-dict"
                    elif _cls == "1d":
                        signature_hint = "I_model(d, params=None)  # Contract C scalar 1d"
        except Exception:
            pass  # use the default scalar hint
        raise ValueError(
            "Python suite executed but does not define `I_model`. "
            f"Define `def {signature_hint}` at module scope before "
            "resubmission. The apparatus IMPORTS test_model.py and the "
            "frozen gate_harness.py invokes I_model on every visible "
            "data row. (If this is an audit / meta substrate that doesn't "
            "need a predictor, set rubric.require_i_model_in_submission=false.)"
        )


# ── GP-156 Proposal 2: visible-MRE attestation ────────────────────────

import re as _re


def _extract_visible_mre_claim(prose: str) -> Optional[float]:
    """Extract the mutator's claimed visible MRE from thesis prose.

    Patterns recognised (case-insensitive):
      - MRE_visible = 0.23
      - visible MRE = 0.23
      - visible-set MRE: 0.23
      - on visible, MRE ≈ 0.23

    Returns None if no claim is present (no-op path).

    GP-156 NaN-mask bypass fix (2026-04-25): the regex requires `\\d+\\.\\d+`
    so it does NOT match `nan`, `NaN`, `inf`, `Inf`. A mutator who writes
    `MRE_visible = nan` does not match the regex → no claim → no
    attestation runs. The NaN-mask bypass is closed at extraction.
    """
    import math as _math
    text = (prose or "").lower()
    patterns = (
        r"mre[_\s\-]?visible\s*[≈≃=:]\s*(\d+\.\d+)",
        r"visible[_\s\-]?(?:set\s+)?mre\s*[≈≃=:]\s*(\d+\.\d+)",
        r"visible.{0,20}mre\s*[≈≃≈]\s*(\d+\.\d+)",
    )
    for pat in patterns:
        m = _re.search(pat, text)
        if m:
            try:
                val = float(m.group(1))
                # Defense in depth: even if the regex group somehow
                # captured a non-finite value, reject it. NaN/Inf can
                # never be legitimate visible-MRE claims.
                if _math.isnan(val) or _math.isinf(val):
                    continue
                return val
            except ValueError:
                continue
    return None


def attest_visible_mre(
    python_code: str,
    prose: str,
    *,
    project_dir: Optional[str] = None,
    tolerance: float = 0.05,
) -> Optional[dict]:
    """Verify the mutator's prose claim of visible-set MRE matches the
    actual measurement from running their I_model on VISIBLE_SET.

    Returns:
      None — no claim was made (no-op path; nothing to attest).
      dict({state="honest", measured, claimed, diff}) — attestation passes.

    Raises:
      ValueError — claim and measurement diverge by more than tolerance.
        This is the GP-156 Proposal 2 fabrication intercept: stops a
        mutator from writing "visible MRE = 0.10" while the actual
        I_model returns predictions that produce MRE = 2.0 in the
        harness. R1 rejects the candidate so the iter is re-prompted
        instead of consumed.

    The function is fail-soft on infrastructure issues: if VISIBLE_SET
    cannot be located or evaluate_visible() is not present, it returns
    None (no-op) rather than raising — this protects substrates without
    the standard scaffold (gp146 closed-form, gp145b numerical) from
    spurious attestation failures.
    """
    claimed = _extract_visible_mre_claim(prose)
    if claimed is None:
        return None  # no-op: nothing to attest

    code = (python_code or "").strip()
    if not code:
        return None

    # Build a sandbox identical to the import-time exec sandbox, then
    # additionally try to evaluate VISIBLE_SET.
    sandbox: dict = {
        # GP-157 Bug #35 (2026-04-25 night): match the dry-run sandbox name
        # so `if __name__ == "__main__":` debug blocks don't run during
        # attestation. Same false-positive class.
        "__name__": "ztare_mutator_test_model_attest",
        "__file__": "<mutator_test_model_attest>",
    }
    saved_sys_path = list(sys.path)
    saved_stdout = sys.stdout
    saved_stderr = sys.stderr
    measured: Optional[float] = None
    try:
        if project_dir and project_dir not in sys.path:
            sys.path.insert(0, project_dir)
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        try:
            compiled = compile(code, "<mutator_test_model_attest>", "exec")
            exec(compiled, sandbox)
        except Exception:
            # If the candidate doesn't even import, R1 import-time exec
            # already caught it; nothing to attest. No-op.
            return None

        # Look for VISIBLE_SET (preferred) or call evaluate_visible() if
        # the candidate provides one. Two paths:
        I_model = sandbox.get("I_model")
        if I_model is None:
            return None

        visible_set = sandbox.get("VISIBLE_SET")
        if visible_set is None and project_dir:
            # GP-156 disk-vs-memory bug fix #3 (2026-04-25): the mutator
            # OVERWRITES test_model.py and frequently drops VISIBLE_SET.
            # Read from features.py (substrate scaffold the mutator
            # should not touch) via visible_rows() helper. Falls back to
            # test_model.py only if features.py doesn't expose it.
            try:
                import importlib.util as _ilu
                fp_path = Path(project_dir) / "features.py"
                if fp_path.exists():
                    _spec = _ilu.spec_from_file_location("_substrate_features_for_attest", str(fp_path))
                    if _spec and _spec.loader:
                        _mod = _ilu.module_from_spec(_spec)
                        try:
                            _spec.loader.exec_module(_mod)
                            _vr = getattr(_mod, "visible_rows", None)
                            if callable(_vr):
                                visible_set = _vr()
                        except Exception:
                            visible_set = None
                # Last-resort fallback: try test_model.py (legacy substrates)
                if visible_set is None:
                    tm_path = Path(project_dir) / "test_model.py"
                    if tm_path.exists():
                        _spec = _ilu.spec_from_file_location("_substrate_test_model_attest_fallback", str(tm_path))
                        if _spec and _spec.loader:
                            _mod = _ilu.module_from_spec(_spec)
                            try:
                                _spec.loader.exec_module(_mod)
                                visible_set = getattr(_mod, "VISIBLE_SET", None)
                            except Exception:
                                visible_set = None
            except Exception:
                visible_set = None

        if visible_set is None or not visible_set:
            return None  # no-op: substrate provides no canonical visible rows

        # Compute MRE using the candidate's I_model on the canonical
        # visible rows. Each row is (id, y_observed, features_dict).
        errors = []
        for entry in visible_set:
            if len(entry) != 3:
                continue
            _id, y_obs, feats = entry
            try:
                y_pred = float(I_model(feats))
            except Exception:
                errors.append(1.0)
                continue
            import math as _math
            if _math.isnan(y_pred) or _math.isinf(y_pred):
                errors.append(1.0)
                continue
            if y_obs == 0:
                errors.append(abs(y_pred))
            else:
                errors.append(abs(y_pred - y_obs) / abs(y_obs))
        if not errors:
            return None
        measured = sum(errors) / len(errors)
    finally:
        sys.path[:] = saved_sys_path
        sys.stdout = saved_stdout
        sys.stderr = saved_stderr

    if measured is None:
        return None

    # GP-156 NaN-mask bypass fix: reject non-finite measured values.
    # If evaluate_visible() returned NaN (because I_model returns NaN
    # for some rows), naive `abs(claimed - measured) > tolerance`
    # evaluates to False on NaN comparisons → fabrication slips
    # through. Treat non-finite measured as fail-closed.
    import math as _math
    if _math.isnan(measured) or _math.isinf(measured):
        raise ValueError(
            f"Visible-MRE attestation failed: thesis claims MRE_visible "
            f"= {claimed:.4f} but evaluate_visible() returned a non-"
            f"finite value ({measured!r}). I_model likely returns NaN "
            f"or Inf on some visible rows — fix before resubmission."
        )
    if _math.isnan(claimed) or _math.isinf(claimed):
        # Should never reach here (extraction filters NaN/Inf) but
        # belt-and-suspenders.
        raise ValueError(
            f"Visible-MRE attestation failed: claimed MRE is non-finite "
            f"({claimed!r}). NaN/Inf claims are not legitimate."
        )

    diff = abs(claimed - measured)
    if diff > tolerance:
        raise ValueError(
            f"Visible-MRE attestation failed: thesis claims MRE_visible "
            f"= {claimed:.4f} but evaluate_visible() on the submitted "
            f"I_model returns {measured:.4f} (discrepancy {diff:.4f} "
            f"> tolerance {tolerance:.2f}). Either your formula "
            f"doesn't match what was implemented in the Python block, "
            f"or the claimed number is fabricated. Fix the prose-vs-"
            f"code gap before resubmission."
        )

    return {
        "state": "honest",
        "claimed": claimed,
        "measured": measured,
        "diff": diff,
        "tolerance": tolerance,
    }
