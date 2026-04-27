"""GP-170 — Symbolic Logic Cage Phase 1 (deductive cage on PARAMETRIC_FORM).

Cage-routed gate (per GP-157 §3a) that runs algebraic boundary-condition
checks against the mutator's PARAMETRIC_FORM at the PRE_FIT phase. The
gate's job is to prove UNSATISFIABILITY of declared `cage_meta.algebraic_constraints`
against the form *before* scipy fits constants — turning structural
violations from "iter consumed via expensive numerical fail" into
"iter rejected in milliseconds with an algebraic counterexample R1
strike."

This module ships Phase 1 of the GP-170 seam. It honors the panel-review
+ Gemini Pro paradox fixes (a sieve without them):

  1. Regex pre-parser rejecting Python control-flow keywords FAIL-CLOSED
     (no fall-through to numerical when the parser cannot ingest).
  2. AST-rewrite layer mapping the apparatus's whitelisted primitives
     (`where`, `sigmoid`) to SymPy algebraic objects (`Piecewise`,
     closed-form sigmoid expansion) BEFORE invoking `parse_expr` —
     because the apparatus grammar is the cage's primary attack surface.
  3. Assumption-aware symbol declaration reading INIT_RANGE for
     parameters and feature-dimension defaults for features. Without
     this step, SymPy's SAT solver finds complex-number assignments
     and returns SAT on every constraint.
  4. Provenance-required constraint validation: constraints without
     `provenance` are silently dropped with a warning. SubstrateCritic
     does NOT auto-write SymPy constraints (the empirical/axiomatic
     separation from paper 5).
  5. Trivial-wrapping detector (Panel-E): each algebraic constraint
     paired with a structural-complexity floor on the inner form.
  6. Hard 15s wall-clock budget across all constraints per iter, with
     `budget_exceeded` as a distinct verdict from `symbolic_indeterminate`.
  7. `can_handle` predicate with explicit telemetry-distinguishable
     reasons for refusal (Panel-G fix on py_exec substrates).
  8. Data-belief reconciliation (Panel-H): constraints that the visible
     data violates by >5% disable the gate with a high-priority
     operator alert.
  9. R1 bounce message templates distinguishing "fundamental algebraic
     violation" from "cross-domain seed needing dimensional bridging"
     (Phase-2 prep — even though Phase 2 isn't built, the scaffolding
     is here so cold-LLM-seed-tagged forms get the constructive retry
     instead of a hard wall).

Phase 1 explicitly DOES NOT implement:
  - Phase 2 dimensional consistency (Buckingham π) — deferred until
    GP-169 is wired and producing seeds.
  - Phase 3 AST canonical-form deduplication.
  - Phase 4 symbolic limit / asymptotic verification.
"""
from __future__ import annotations

import logging
import re
import threading
import time
import warnings
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ── Regex pre-parser (Blindspot A fix, fail-closed) ───────────────────


# Python control-flow tokens that SymPy's parse_expr cannot handle.
# Detection is whole-word so we don't false-flag `iffy` or `formula`.
# `else` is included because Python ternary `a if c else b` requires both
# `if` and `else` and either alone signals a control-flow construct.
_PY_CONTROL_FLOW_TOKENS = (
    "if", "else", "elif", "for", "while", "lambda", "yield",
    "def", "class", "return", "import", "from",
    "try", "except", "finally", "with", "raise",
)
_PY_CONTROL_FLOW_REGEX = re.compile(
    r"\b(" + "|".join(_PY_CONTROL_FLOW_TOKENS) + r")\b"
)
# Comprehensions are syntactically tagged by `for ... in ...` patterns
# inside brackets/parens; `for` already catches the keyword.


def regex_reject_python_control_flow(form_str: str) -> tuple[bool, Optional[str]]:
    """Step 1 of the cage: refuse Python control-flow keywords FAIL-CLOSED.

    Returns:
        (rejected, diagnostic). When `rejected` is True, the caller MUST
        treat the form as malformed and produce an R1 bounce message.
        Per the seam: "Parser failures are fail-closed: the form is
        rejected as malformed." This is NOT a fall-through to numerical
        — that fall-through is the LLM-bypass channel (Blindspot A).

        When False, diagnostic is None.
    """
    if not isinstance(form_str, str):
        return True, "form is not a string"
    match = _PY_CONTROL_FLOW_REGEX.search(form_str)
    if match is not None:
        kw = match.group(1)
        return True, (
            f"PARAMETRIC_FORM contains Python control-flow keyword "
            f"`{kw}` which the symbolic cage cannot ingest. Use the "
            f"whitelisted primitive `where(cond, a, b)` for branching "
            f"or `sigmoid(x, center, width)` for smooth regime "
            f"crossovers. Both are AST-parseable by SymPy after the "
            f"cage's internal rewrite step."
        )
    return False, None


# ── AST-rewrite layer (Panel-C/D fix; primitive→SymPy algebraic) ─────


# `where(cond, a, b)` → `Piecewise((a, cond), (b, True))`
# Tolerates nested calls because the rewrite is applied recursively
# (the outermost `where(...)` is rewritten, and any inner `where(...)`
# in `a` or `b` is captured by re-running the regex; we use a pass loop
# until no further matches are found).
#
# Implementation note: a regex-only rewrite is brittle on deeply nested
# expressions. We do a balanced-paren tokenizer because forms can hold
# `where(features['x'] == 'A', sigmoid(x, c, w), where(...))` with
# arbitrary nesting.


def _split_top_level_args(arg_str: str) -> list[str]:
    """Split a function-argument string on top-level commas.

    Respects nested parentheses, brackets, and braces. Returns the
    individual argument substrings (whitespace-stripped).
    """
    args: list[str] = []
    depth = 0
    cur: list[str] = []
    for ch in arg_str:
        if ch in "([{":
            depth += 1
            cur.append(ch)
        elif ch in ")]}":
            depth -= 1
            cur.append(ch)
        elif ch == "," and depth == 0:
            args.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if cur:
        args.append("".join(cur).strip())
    return args


def _find_call(form_str: str, name: str) -> Optional[tuple[int, int, str]]:
    """Locate the first `name(...)` call in `form_str` with a balanced
    closing paren. Returns (start, end_exclusive, args_substring) or
    None.
    """
    pattern = re.compile(r"\b" + re.escape(name) + r"\s*\(")
    m = pattern.search(form_str)
    if m is None:
        return None
    open_idx = m.end() - 1  # index of "("
    depth = 0
    i = open_idx
    while i < len(form_str):
        ch = form_str[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return m.start(), i + 1, form_str[open_idx + 1:i]
        i += 1
    return None  # unbalanced; let downstream fail


def _rewrite_where_calls(form_str: str, max_passes: int = 64) -> str:
    """Rewrite every `where(cond, a, b)` to `Piecewise((a, cond), (b, True))`.

    Applies until no further `where(` is found or `max_passes` is hit
    (defensive cap against pathological inputs).
    """
    out = form_str
    for _ in range(max_passes):
        loc = _find_call(out, "where")
        if loc is None:
            return out
        start, end, arg_str = loc
        args = _split_top_level_args(arg_str)
        if len(args) != 3:
            # Malformed where(); leave it for parse_expr to reject.
            return out
        cond, a, b = args
        replacement = f"Piecewise(({a}, {cond}), ({b}, True))"
        out = out[:start] + replacement + out[end:]
    return out


def _rewrite_sigmoid_calls(form_str: str, max_passes: int = 64) -> str:
    """Rewrite `sigmoid(x)` to `1/(1+exp(-(x)))` and
    `sigmoid(x, c, w)` to `1/(1+exp(-((x)-(c))/(w)))`.

    Closed-form so SymPy can reason about derivatives and limits.
    """
    out = form_str
    for _ in range(max_passes):
        loc = _find_call(out, "sigmoid")
        if loc is None:
            return out
        start, end, arg_str = loc
        args = _split_top_level_args(arg_str)
        if len(args) == 1:
            x = args[0]
            replacement = f"(1/(1+exp(-({x}))))"
        elif len(args) == 3:
            x, c, w = args
            replacement = f"(1/(1+exp(-(({x})-({c}))/({w}))))"
        else:
            # 2-arg sigmoid is not in the apparatus contract; leave it
            # alone so parse_expr produces a clear error.
            return out
        out = out[:start] + replacement + out[end:]
    return out


def rewrite_form_for_sympy(form_str: str) -> str:
    """Step 2 of the cage: AST-rewrite the apparatus's whitelisted
    primitives to SymPy algebraic objects so SymPy can reason about
    them.

    Mappings:
      - `where(cond, a, b)` → `Piecewise((a, cond), (b, True))`
      - `sigmoid(x)`        → `1 / (1 + exp(-x))`
      - `sigmoid(x, c, w)`  → `1 / (1 + exp(-(x-c)/w))`

    `erf`, `tanh`, `exp`, `log`, `log10`, `sin`, `cos`, `tan`, `sqrt`,
    `abs`, `min`, `max` are SymPy-native or trivially mappable —
    parse_expr handles them directly.

    `len`, `str`, `bool`, `float`, `int` are type-coercion helpers used
    by the apparatus for indicator/categorical handling. They have no
    SymPy algebraic equivalent. The cage refuses to engage on forms
    using them (see `r170_can_handle`).
    """
    out = form_str
    out = _rewrite_where_calls(out)
    out = _rewrite_sigmoid_calls(out)
    return out


# ── Assumption-aware symbol declaration (Blindspot B fix) ────────────


def _feature_assumptions_default(feature_key: str) -> dict[str, bool]:
    """Substrate-class heuristic defaults when feature_dimensions is
    not declared. Conservative posture: real=True only.
    """
    # Heuristic naming conventions actually used in the codebase.
    # `gas_fraction` is bounded [0, 1] by definition; we mark
    # nonnegative=True (operator can override via feature_dimensions
    # to add an upper bound).
    if feature_key.endswith("_fraction") or feature_key == "gas_fraction":
        return {"real": True, "nonnegative": True}
    if feature_key.endswith("_log10") or feature_key.startswith("log_"):
        # log-space variables span all reals (signed)
        return {"real": True}
    if feature_key.endswith("_count") or feature_key.endswith("_n"):
        return {"real": True, "nonnegative": True}
    return {"real": True}


def _parameter_assumptions_from_range(
    init_range: tuple[float, float] | list,
) -> dict[str, bool]:
    """Convert INIT_RANGE = (lo, hi) into SymPy assumption kwargs.

    Per the seam:
      - lo > 0    → positive=True, real=True
      - lo >= 0   → nonnegative=True, real=True
      - else      → real=True
    """
    try:
        lo, hi = float(init_range[0]), float(init_range[1])
    except (TypeError, ValueError, IndexError):
        return {"real": True}
    if lo > 0:
        return {"positive": True, "real": True}
    if lo >= 0:
        return {"nonnegative": True, "real": True}
    return {"real": True}


# Regex that picks symbol-like identifiers out of the form. We catch
# `features['key']` and `params['key']` (the apparatus's canonical
# accessors) and bare identifiers (mutator may inline them).
_FEATURE_KEY_RE = re.compile(r"features\[\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*\]")
_PARAM_KEY_RE = re.compile(r"params\[\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]\s*\]")


def declare_symbols_with_assumptions(
    form_str: str,
    init_ranges: dict,
    feature_dimensions: dict,
) -> dict[str, Any]:
    """Step 3 of the cage: declare SymPy symbols for every feature/param
    referenced by the form, with assumptions matching INIT_RANGE and
    feature_dimensions.

    Returns a dict mapping str → sympy.Symbol that the caller passes as
    `local_dict` to `parse_expr` so SymPy uses our typed symbols
    instead of inferring untyped (complex-admitting) symbols.

    The dict also includes synthetic top-level `y` and `x` symbols
    inferred from feature_dimensions (when `y` and `x` are declared as
    feature dimensions) so constraint strings like `y < x` parse.
    """
    import sympy

    symbols: dict[str, Any] = {}

    # Features
    for f_key in set(_FEATURE_KEY_RE.findall(form_str)):
        if f_key in feature_dimensions:
            assumptions = _feature_assumptions_from_dimension(
                feature_dimensions[f_key], f_key
            )
        else:
            assumptions = _feature_assumptions_default(f_key)
        symbols[f_key] = sympy.Symbol(f_key, **assumptions)

    # Parameters
    for p_key in set(_PARAM_KEY_RE.findall(form_str)):
        rng = init_ranges.get(p_key)
        assumptions = (
            _parameter_assumptions_from_range(rng) if rng is not None
            else {"real": True}
        )
        symbols[p_key] = sympy.Symbol(p_key, **assumptions)

    # Top-level convention symbols. Constraints like "y < x" or "y > 0"
    # use the substrate's target-convention names. We declare them with
    # feature_dimensions assumptions if present, else conservative real.
    for canon in ("y", "x"):
        if canon in symbols:
            continue
        if canon in feature_dimensions:
            assumptions = _feature_assumptions_from_dimension(
                feature_dimensions[canon], canon
            )
        else:
            assumptions = _feature_assumptions_default(canon)
        symbols[canon] = sympy.Symbol(canon, **assumptions)

    return symbols


def _feature_assumptions_from_dimension(
    dim_spec: Any, feature_key: str
) -> dict[str, bool]:
    """Resolve a feature_dimensions value to SymPy assumptions.

    The seam allows two forms:
      - simple string: `"L T^-2"` → real (no sign assumption)
      - dict with bounds: `{"unit": "1", "lo": 0.0, "hi": 1.0}`
        → assumptions inferred from the bounds.
    """
    if isinstance(dim_spec, dict):
        lo = dim_spec.get("lo")
        if isinstance(lo, (int, float)):
            if lo > 0:
                return {"positive": True, "real": True}
            if lo >= 0:
                return {"nonnegative": True, "real": True}
        return {"real": True}
    return _feature_assumptions_default(feature_key)


# ── Provenance-required constraint validation (Collision-3 fix) ──────


def _validate_constraint_provenance(
    constraints: list[dict],
) -> tuple[list[dict], list[str]]:
    """Drop constraints missing `provenance`. Returns (kept, dropped_diagnostics).

    Per the seam: "Constraints without provenance are silently dropped
    with a warning at rubric load time. SubstrateCritic does NOT
    auto-write SymPy constraints."
    """
    kept: list[dict] = []
    dropped: list[str] = []
    for i, c in enumerate(constraints or []):
        if not isinstance(c, dict):
            dropped.append(
                f"constraint #{i}: not a dict ({type(c).__name__}); dropped"
            )
            continue
        prov = c.get("provenance")
        if not isinstance(prov, str) or not prov.strip():
            dropped.append(
                f"constraint #{i} ({c.get('expr', '?')!r}): missing or "
                f"empty `provenance` field; dropped per GP-170 §Collision-3."
            )
            continue
        kept.append(c)
    for msg in dropped:
        warnings.warn(msg, UserWarning, stacklevel=3)
        logger.warning(msg)
    return kept, dropped


# ── Trivial-wrapping detector (Panel-E fix) ──────────────────────────


def _structural_complexity(expr: Any) -> int:
    """Count interior nodes of a SymPy expression as a complexity proxy.

    A constant or single-symbol expression returns ≤1. A primitive
    function call wrapping a constant returns 2. Anything genuinely
    structural returns ≥3.
    """
    try:
        import sympy
    except ImportError:
        return 0
    if expr is None:
        return 0
    if isinstance(expr, (int, float)):
        return 1
    if isinstance(expr, sympy.Symbol):
        return 1
    if isinstance(expr, sympy.Number):
        return 1
    n = 1
    for arg in getattr(expr, "args", ()):
        n += _structural_complexity(arg)
    return n


# Constraints with a "wrapper-like" RHS pattern that mutators can satisfy
# trivially. Each entry is (constraint_pattern_re, wrapper_form_re,
# minimum_inner_complexity). The detector only fires when the form
# matches the wrapper pattern AND the inner complexity is below the
# floor.
_TRIVIAL_WRAP_PATTERNS = (
    # y > 0 wrapped via y = exp(...) with constant inner
    (re.compile(r"^\s*y\s*>\s*0\s*$"), re.compile(r"^\s*exp\s*\("), 2),
    # y >= x wrapped via y = x + abs(...) with constant inner
    (re.compile(r"^\s*y\s*>=\s*x\s*$"), re.compile(r"^\s*x\s*\+\s*abs\s*\("), 2),
)


def _trivial_wrapping_detected(
    constraint_expr_str: str,
    form_sympy_expr: Any,
    rewritten_form_str: str,
) -> tuple[bool, Optional[str]]:
    """Per Panel-E: detect when the form satisfies the constraint by
    structural wrapping rather than informational content.

    Returns (is_trivial, diagnostic).
    """
    try:
        import sympy
    except ImportError:
        return False, None

    for cre, fre, floor in _TRIVIAL_WRAP_PATTERNS:
        if not cre.match(constraint_expr_str):
            continue
        if not fre.match(rewritten_form_str.strip().lstrip("(").strip()):
            continue
        # Find the inner argument of the outer wrapper and check its
        # complexity.
        if isinstance(form_sympy_expr, sympy.exp):
            inner = form_sympy_expr.args[0] if form_sympy_expr.args else None
        elif (isinstance(form_sympy_expr, sympy.Add)
                and len(form_sympy_expr.args) == 2):
            # x + abs(...)
            non_x = [a for a in form_sympy_expr.args
                     if not (isinstance(a, sympy.Symbol) and a.name == "x")]
            inner = non_x[0] if non_x else None
        else:
            inner = None
        complexity = _structural_complexity(inner)
        if complexity < floor:
            return True, (
                f"Constraint {constraint_expr_str!r} is satisfied by "
                f"trivial structural wrapping: the form's outer shape "
                f"meets the constraint while the inner expression has "
                f"structural complexity {complexity} (floor: {floor}). "
                f"Per Panel-E (GP-170): forms that satisfy declared "
                f"axioms by wrapping a constant or single primitive "
                f"call carry no informational content. Reject as "
                f"trivial-wrapping Goodhart."
            )
    return False, None


# ── Wall-clock budget guard (Panel-F fix) ────────────────────────────


_MAX_AST_NODES = 600  # AST-complexity precheck before simplify


def _ast_node_count(expr: Any) -> int:
    """Count SymPy expression nodes for the precheck."""
    return _structural_complexity(expr)


@dataclass
class _BudgetGuard:
    """Wall-clock budget tracker. Emits remaining_s as a soft signal;
    callers wrap heavy SymPy ops in a thread + join with timeout when
    they want hard preemption.
    """
    budget_s: float
    started_at: float = field(default_factory=time.monotonic)

    @property
    def remaining_s(self) -> float:
        return max(0.0, self.budget_s - (time.monotonic() - self.started_at))

    @property
    def exceeded(self) -> bool:
        return self.remaining_s <= 0.0


def _run_with_timeout(
    fn: Callable[[], Any], timeout_s: float
) -> tuple[bool, Any]:
    """Run `fn` in a thread; return (completed, result).

    On timeout returns (False, None). Note: Python threads cannot be
    forcibly killed; the work continues in background but the caller
    treats it as failed. Acceptable here because the gate's worst case
    is a wasted thread, not a wasted iter.
    """
    result_box: list[Any] = [None]
    exc_box: list[BaseException] = []

    def _runner() -> None:
        try:
            result_box[0] = fn()
        except BaseException as exc:  # noqa: BLE001 — we re-raise after join
            exc_box.append(exc)

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    t.join(timeout=timeout_s)
    if t.is_alive():
        return False, None
    if exc_box:
        raise exc_box[0]
    return True, result_box[0]


# ── Main entry: check_algebraic_constraints ──────────────────────────


@dataclass
class ConstraintVerdict:
    expr: str
    verdict: str  # "satisfied" | "violated" | "indeterminate" | "trivial_wrap" | "skipped"
    diagnostic: str = ""
    counterexample: Optional[dict] = None


@dataclass
class ConstraintCheckResult:
    """Outcome of `check_algebraic_constraints` over all constraints.

    Verdicts:
      - "passed": every constraint provably satisfied (or skipped with
                  reason); no violations found.
      - "violated": at least one constraint provably UNSATISFIABLE.
      - "indeterminate": SymPy returned UNKNOWN on at least one
                         constraint, and none were violated. Caller
                         falls through to numerical check.
      - "budget_exceeded": wall-clock budget exhausted before all
                            constraints checked. Distinct from
                            indeterminate per Panel-F.
      - "rejected_form": the form itself was rejected (regex pre-parser
                         hit or AST-rewrite produced an unparseable
                         expression). FAIL-CLOSED.
      - "data_disagreement": gate refused to engage because declared
                              constraints disagree with visible data
                              (>5% violation; Panel-H).
    """
    overall: str
    per_constraint: list[ConstraintVerdict] = field(default_factory=list)
    rejected_reason: Optional[str] = None
    cross_domain_seed: bool = False
    budget_used_s: float = 0.0
    diagnostics: list[str] = field(default_factory=list)
    r1_message: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "overall": self.overall,
            "per_constraint": [
                {
                    "expr": v.expr,
                    "verdict": v.verdict,
                    "diagnostic": v.diagnostic,
                    "counterexample": v.counterexample,
                }
                for v in self.per_constraint
            ],
            "rejected_reason": self.rejected_reason,
            "cross_domain_seed": self.cross_domain_seed,
            "budget_used_s": self.budget_used_s,
            "diagnostics": list(self.diagnostics),
            "r1_message": self.r1_message,
        }


# R1 message templates (item 9 of the implementation contract).
_R1_FUNDAMENTAL_VIOLATION_TEMPLATE = (
    "Symbolic Logic Cage REJECTION (fundamental algebraic violation): "
    "{constraint!r} is unsatisfiable for the submitted PARAMETRIC_FORM "
    "under the substrate's declared parameter ranges and feature "
    "dimensions. Proof sketch: {proof}. Choose a form whose algebraic "
    "boundary admits the constraint, or revise the constraint's "
    "provenance if the substrate's belief is incorrect."
)
_R1_CROSS_DOMAIN_SEED_TEMPLATE = (
    "Symbolic Logic Cage REJECTION (cross-domain seed needs dimensional "
    "bridging): the submitted PARAMETRIC_FORM is tagged as a cold-LLM "
    "cross-domain seed and violates {constraint!r} as written. Cold-domain "
    "forms typically need dimension-canceling fitted constants to bridge "
    "into the substrate's home domain. Resubmit with explicit free "
    "parameters carrying the unit-canceling roles (e.g. wrap features in "
    "fitted scale constants whose INIT_RANGE is wide enough to absorb "
    "the dimensional gap), or pivot to a home-domain analogue that "
    "satisfies the constraint by construction."
)


def _data_belief_reconciliation(
    constraints: list[dict],
    visible_rows: list[dict] | None,
    feature_y_key: str = "y",
) -> tuple[bool, list[str]]:
    """Per Panel-H: refuse to engage if declared constraints contradict
    visible data by >5% of rows.

    Returns (engage, alerts). When `visible_rows` is None or empty we
    cannot reconcile, so we engage with a soft note.
    """
    alerts: list[str] = []
    if not visible_rows:
        return True, alerts
    # Light-touch: only check the simple positivity / inequality
    # constraints we can evaluate by row. Anything more sophisticated
    # (limits, derivatives) requires the form, not just the data, and
    # is handled later in the pipeline.
    for c in constraints:
        expr = (c.get("expr") or "").strip()
        if not expr:
            continue
        violation_count = 0
        total = 0
        for row in visible_rows:
            y = row.get(feature_y_key)
            x = row.get("x")
            if y is None:
                continue
            total += 1
            try:
                if expr == "y > 0" and not (y > 0):
                    violation_count += 1
                elif expr == "y >= 0" and not (y >= 0):
                    violation_count += 1
                elif expr == "y < x" and x is not None and not (y < x):
                    violation_count += 1
                elif expr == "y >= x" and x is not None and not (y >= x):
                    violation_count += 1
            except TypeError:
                continue
        if total >= 4 and violation_count / total > 0.05:
            alerts.append(
                f"Declared constraint {expr!r} ({c.get('provenance', '?')}) "
                f"is violated by {violation_count}/{total} visible rows "
                f"({100*violation_count/total:.1f}%). The cage refuses "
                f"to engage rather than starve discovery on a wrong "
                f"axiom. Reconcile constraint with data before re-enabling."
            )
    return (not alerts), alerts


def check_algebraic_constraints(
    form_str: str,
    constraints: list[dict],
    init_ranges: dict,
    feature_dimensions: dict,
    *,
    wall_clock_budget_s: float = 15.0,
    cross_domain_seed: bool = False,
    visible_rows: list[dict] | None = None,
    _simplify_override: Optional[Callable[[Any], Any]] = None,
) -> ConstraintCheckResult:
    """Main entry. Validate `form_str` against `constraints` symbolically.

    Args:
        form_str: the PARAMETRIC_FORM string the mutator submitted.
        constraints: list of dicts with `expr` (algebraic constraint
            string), `provenance` (required, see Collision-3), and
            optional metadata. Constraints without provenance are
            silently dropped with a warning.
        init_ranges: dict mapping `params['key']` keys to (lo, hi)
            tuples (the substrate's declared INIT_RANGE).
        feature_dimensions: dict mapping `features['key']` keys to
            dimension specs (string or dict with lo/hi).
        wall_clock_budget_s: hard ceiling across all constraints.
        cross_domain_seed: when True, R1 messages on rejection use the
            "cross-domain seed needs dimensional bridging" template
            instead of the "fundamental algebraic violation" template
            (Cross-seam Collision-2).
        visible_rows: optional list of row dicts for data-belief
            reconciliation. When provided, the gate refuses to engage
            if a constraint disagrees with the data by >5%.
        _simplify_override: test-only hook to inject a stubbed
            `simplify` (e.g. simulating timeout). Production callers
            leave it as None.

    Returns:
        ConstraintCheckResult with `overall` verdict and per-constraint
        diagnostics. Caller is responsible for surfacing `r1_message`
        to the mutator on rejection.
    """
    result = ConstraintCheckResult(overall="passed")
    result.cross_domain_seed = cross_domain_seed
    budget = _BudgetGuard(budget_s=wall_clock_budget_s)

    # Step 1: regex pre-parser, fail-closed.
    rejected, diag = regex_reject_python_control_flow(form_str)
    if rejected:
        result.overall = "rejected_form"
        result.rejected_reason = diag
        result.diagnostics.append(f"step1_regex_rejected: {diag}")
        result.r1_message = (
            _R1_CROSS_DOMAIN_SEED_TEMPLATE if cross_domain_seed
            else _R1_FUNDAMENTAL_VIOLATION_TEMPLATE
        ).format(constraint=diag, proof="pre-parser rejection")
        return result

    # Step 2: AST-rewrite.
    try:
        rewritten = rewrite_form_for_sympy(form_str)
    except Exception as exc:  # noqa: BLE001
        result.overall = "rejected_form"
        result.rejected_reason = (
            f"AST-rewrite failed: {type(exc).__name__}: {exc}"
        )
        result.diagnostics.append(result.rejected_reason)
        return result

    # Step 3: provenance validation (constraints filter).
    kept_constraints, dropped_msgs = _validate_constraint_provenance(constraints)
    result.diagnostics.extend(dropped_msgs)
    if not kept_constraints:
        result.overall = "passed"
        result.diagnostics.append(
            "no constraints with valid provenance; gate is a no-op for this iter."
        )
        return result

    # Step 3b: data-belief reconciliation (Panel-H).
    engage, alerts = _data_belief_reconciliation(kept_constraints, visible_rows)
    if not engage:
        result.overall = "data_disagreement"
        result.diagnostics.extend(alerts)
        result.rejected_reason = "; ".join(alerts)
        return result

    # Step 4: SymPy import (lazy — heavy dep).
    try:
        import sympy
        from sympy.parsing.sympy_parser import parse_expr
    except ImportError as exc:
        result.overall = "indeterminate"
        result.diagnostics.append(
            f"sympy unavailable: {exc}; symbolic cage degraded to no-op."
        )
        return result

    simplify_fn = _simplify_override or sympy.simplify

    # Step 5: declare typed symbols.
    try:
        symbols = declare_symbols_with_assumptions(
            form_str, init_ranges, feature_dimensions
        )
    except Exception as exc:  # noqa: BLE001
        result.overall = "rejected_form"
        result.rejected_reason = f"symbol declaration failed: {exc}"
        result.diagnostics.append(result.rejected_reason)
        return result

    # Step 6: parse the rewritten form.
    # Strip features['k'] / params['k'] sugar to bare symbol names so
    # parse_expr binds them to our typed symbols.
    parse_str = _strip_dict_accessors(rewritten)
    try:
        form_expr = parse_expr(parse_str, local_dict=symbols, evaluate=False)
    except Exception as exc:  # noqa: BLE001
        result.overall = "rejected_form"
        result.rejected_reason = (
            f"parse_expr failed on rewritten form: {type(exc).__name__}: {exc}"
        )
        result.diagnostics.append(result.rejected_reason)
        return result

    # Step 6b: AST-complexity precheck.
    nodes = _ast_node_count(form_expr)
    if nodes > _MAX_AST_NODES:
        result.overall = "indeterminate"
        result.diagnostics.append(
            f"form has {nodes} AST nodes (cap {_MAX_AST_NODES}); skipping "
            f"symbolic checks to preserve wall-clock budget."
        )
        result.budget_used_s = time.monotonic() - budget.started_at
        return result

    # Step 7: per-constraint check.
    any_violated = False
    any_indeterminate = False
    for c in kept_constraints:
        if budget.exceeded:
            result.overall = "budget_exceeded"
            result.diagnostics.append(
                f"wall-clock budget {wall_clock_budget_s}s exhausted "
                f"before checking all constraints"
            )
            result.budget_used_s = time.monotonic() - budget.started_at
            return result

        constraint_expr_str = (c.get("expr") or "").strip()
        verdict = _check_one_constraint(
            constraint_expr_str=constraint_expr_str,
            form_expr=form_expr,
            symbols=symbols,
            simplify_fn=simplify_fn,
            rewritten_form_str=rewritten,
            remaining_budget_s=budget.remaining_s,
        )
        result.per_constraint.append(verdict)
        if verdict.verdict == "violated":
            any_violated = True
        elif verdict.verdict == "trivial_wrap":
            any_violated = True
        elif verdict.verdict == "indeterminate":
            any_indeterminate = True

    result.budget_used_s = time.monotonic() - budget.started_at

    if any_violated:
        first_violation = next(
            (v for v in result.per_constraint
             if v.verdict in ("violated", "trivial_wrap")),
            None,
        )
        result.overall = "violated"
        if first_violation is not None:
            template = (
                _R1_CROSS_DOMAIN_SEED_TEMPLATE if cross_domain_seed
                else _R1_FUNDAMENTAL_VIOLATION_TEMPLATE
            )
            result.r1_message = template.format(
                constraint=first_violation.expr,
                proof=first_violation.diagnostic,
            )
        return result
    if any_indeterminate:
        result.overall = "indeterminate"
        return result
    return result


def _strip_dict_accessors(form_str: str) -> str:
    """Replace `features['key']` and `params['key']` with bare `key`
    so SymPy's parser sees identifiers it can bind to our symbol dict.
    """
    out = _FEATURE_KEY_RE.sub(lambda m: m.group(1), form_str)
    out = _PARAM_KEY_RE.sub(lambda m: m.group(1), out)
    return out


def _sign_under_assumptions(expr: Any) -> Optional[str]:
    """Return one of {"positive", "negative", "zero", None} for a SymPy
    expression under its symbols' declared assumptions.

    Tries multiple algebraic manipulations because SymPy's direct
    `is_positive` often returns None on expressions of the form
    `A - sqrt(...)` even when one sign is determinate. Conjugate
    rationalization (via radsimp on the reciprocal) frequently
    resolves these.
    """
    import sympy

    candidates = [expr]
    try:
        candidates.append(sympy.simplify(expr))
    except Exception:
        pass
    try:
        candidates.append(sympy.expand(expr))
    except Exception:
        pass
    try:
        candidates.append(sympy.factor(expr, extension=True))
    except Exception:
        pass
    try:
        candidates.append(sympy.together(expr))
    except Exception:
        pass
    try:
        # Conjugate-rationalization trick: 1 / radsimp(1 / expr) often
        # yields a form whose sign assumption resolves.
        if expr != 0:
            inv = 1 / expr
            radsimped = sympy.radsimp(inv)
            if radsimped != 0:
                candidates.append(sympy.simplify(1 / radsimped))
    except Exception:
        pass

    for cand in candidates:
        try:
            if cand.is_positive is True:
                return "positive"
            if cand.is_negative is True:
                return "negative"
            if cand.is_zero is True:
                return "zero"
        except Exception:
            continue
    return None


def _resolve_relational_via_sign(rel_expr: Any) -> Optional[str]:
    """Reduce a SymPy Relational `lhs OP rhs` to `(rhs - lhs) sign-test`.

    Returns one of:
      - "satisfied": the relation holds under declared assumptions
      - "violated": the relation provably fails
      - None: indeterminate; caller falls back to other strategies
    """
    import sympy

    if not isinstance(rel_expr, sympy.Rel):
        return None
    lhs, rhs = rel_expr.lhs, rel_expr.rhs
    diff = rhs - lhs  # > 0 iff lhs < rhs
    sign = _sign_under_assumptions(diff)
    if sign is None:
        return None

    op = rel_expr.func
    if op is sympy.StrictLessThan:  # lhs < rhs ↔ diff > 0
        if sign == "positive":
            return "satisfied"
        if sign in ("negative", "zero"):
            return "violated"
    elif op is sympy.LessThan:  # lhs <= rhs ↔ diff >= 0
        if sign in ("positive", "zero"):
            return "satisfied"
        if sign == "negative":
            return "violated"
    elif op is sympy.StrictGreaterThan:  # lhs > rhs ↔ diff < 0
        if sign == "negative":
            return "satisfied"
        if sign in ("positive", "zero"):
            return "violated"
    elif op is sympy.GreaterThan:  # lhs >= rhs ↔ diff <= 0
        if sign in ("negative", "zero"):
            return "satisfied"
        if sign == "positive":
            return "violated"
    elif op is sympy.Equality:  # lhs == rhs ↔ diff == 0
        if sign == "zero":
            return "satisfied"
        if sign in ("positive", "negative"):
            return "violated"
    elif op is sympy.Unequality:
        if sign in ("positive", "negative"):
            return "satisfied"
        if sign == "zero":
            return "violated"
    return None


def _check_one_constraint(
    *,
    constraint_expr_str: str,
    form_expr: Any,
    symbols: dict[str, Any],
    simplify_fn: Callable[[Any], Any],
    rewritten_form_str: str,
    remaining_budget_s: float,
) -> ConstraintVerdict:
    """Check a single constraint. Returns a ConstraintVerdict."""
    import sympy
    from sympy.parsing.sympy_parser import parse_expr

    if not constraint_expr_str:
        return ConstraintVerdict(
            expr="<empty>",
            verdict="skipped",
            diagnostic="empty constraint expression",
        )

    # Trivial-wrapping detector (Panel-E) BEFORE we ask SymPy to prove
    # anything — wrap detection is purely structural.
    triv, triv_diag = _trivial_wrapping_detected(
        constraint_expr_str, form_expr, rewritten_form_str
    )
    if triv:
        return ConstraintVerdict(
            expr=constraint_expr_str,
            verdict="trivial_wrap",
            diagnostic=triv_diag or "trivial wrapping detected",
        )

    # Substitute the form into the constraint and check.
    # Constraint may reference `y` directly. We substitute `y → form_expr`.
    try:
        constraint_expr = parse_expr(
            constraint_expr_str, local_dict=symbols, evaluate=False
        )
    except Exception as exc:  # noqa: BLE001
        return ConstraintVerdict(
            expr=constraint_expr_str,
            verdict="indeterminate",
            diagnostic=f"could not parse constraint: {exc}",
        )

    y_sym = symbols.get("y")
    if y_sym is not None:
        try:
            constraint_expr = constraint_expr.subs(y_sym, form_expr)
        except Exception:
            pass

    # Strategy A: relational difference-sign analysis.
    # For Lt/Le/Gt/Ge constraints, reduce `lhs OP rhs` to `(rhs - lhs) OP' 0`
    # and use the multi-strategy sign reducer below. SymPy's `simplify`
    # alone does not reliably resolve square-root inequalities even
    # under positivity assumptions; the dedicated reducer applies
    # `radsimp`, conjugate-rationalization, factor(extension=True),
    # and `is_positive`/`is_negative` checks in sequence.
    timeout_s = max(0.5, min(5.0, remaining_budget_s))
    try:
        completed, sign_verdict = _run_with_timeout(
            lambda: _resolve_relational_via_sign(constraint_expr),
            timeout_s=timeout_s,
        )
    except Exception:  # noqa: BLE001
        sign_verdict = None
        completed = True
    if completed and sign_verdict is not None:
        if sign_verdict == "satisfied":
            return ConstraintVerdict(
                expr=constraint_expr_str,
                verdict="satisfied",
                diagnostic=(
                    f"diff-sign analysis: under declared assumptions, "
                    f"the constraint reduces to a one-signed difference "
                    f"that satisfies the relation."
                ),
            )
        if sign_verdict == "violated":
            return ConstraintVerdict(
                expr=constraint_expr_str,
                verdict="violated",
                diagnostic=(
                    f"diff-sign analysis: under declared assumptions, "
                    f"`{constraint_expr_str}` reduces to a one-signed "
                    f"difference whose sign contradicts the relation. "
                    f"The form algebraically violates this constraint."
                ),
            )

    # Strategy B: simplify(Not(constraint)) — returning False means
    # UNSAT-of-negation, i.e. the constraint is provably satisfied;
    # True means the constraint is provably VIOLATED.
    try:
        completed, neg_simplified = _run_with_timeout(
            lambda: simplify_fn(sympy.Not(constraint_expr)),
            timeout_s=timeout_s,
        )
    except Exception as exc:  # noqa: BLE001
        return ConstraintVerdict(
            expr=constraint_expr_str,
            verdict="indeterminate",
            diagnostic=f"simplify raised: {type(exc).__name__}: {exc}",
        )
    if not completed:
        return ConstraintVerdict(
            expr=constraint_expr_str,
            verdict="indeterminate",
            diagnostic=(
                f"simplify exceeded {timeout_s:.1f}s slot; "
                f"deferring to numerical check"
            ),
        )

    # Interpret the simplified result.
    if neg_simplified is sympy.true or neg_simplified is True:
        # Negation is trivially true → constraint violated.
        return ConstraintVerdict(
            expr=constraint_expr_str,
            verdict="violated",
            diagnostic=(
                f"SymPy proved the negation of {constraint_expr_str!r} "
                f"is True under the declared assumptions; the form "
                f"algebraically violates this constraint."
            ),
        )
    if neg_simplified is sympy.false or neg_simplified is False:
        return ConstraintVerdict(
            expr=constraint_expr_str,
            verdict="satisfied",
            diagnostic=(
                f"SymPy proved {constraint_expr_str!r} holds under the "
                f"declared assumptions (negation simplified to False)."
            ),
        )

    # Try the direct route as a backup: simplify the constraint itself.
    try:
        completed, simplified = _run_with_timeout(
            lambda: simplify_fn(constraint_expr),
            timeout_s=timeout_s,
        )
    except Exception as exc:  # noqa: BLE001
        return ConstraintVerdict(
            expr=constraint_expr_str,
            verdict="indeterminate",
            diagnostic=f"simplify(constraint) raised: {exc}",
        )
    if not completed:
        return ConstraintVerdict(
            expr=constraint_expr_str,
            verdict="indeterminate",
            diagnostic=(
                f"simplify exceeded slot; deferring to numerical check"
            ),
        )
    if simplified is sympy.true or simplified is True:
        return ConstraintVerdict(
            expr=constraint_expr_str,
            verdict="satisfied",
            diagnostic=f"constraint reduced to True under assumptions",
        )
    if simplified is sympy.false or simplified is False:
        return ConstraintVerdict(
            expr=constraint_expr_str,
            verdict="violated",
            diagnostic=(
                f"constraint reduced to False under the declared "
                f"assumptions; the form algebraically violates it."
            ),
        )
    return ConstraintVerdict(
        expr=constraint_expr_str,
        verdict="indeterminate",
        diagnostic=(
            f"SymPy returned {simplified!s} (neither True nor False); "
            f"deferring to numerical check."
        ),
    )


# ── Cage-routed adapters (per GP-157 §3a) ─────────────────────────────


# AST-whitelist primitives for which we have NO SymPy mapping. If the
# form uses any of these, the cage refuses to engage (Panel-G fix).
_UNHANDLEABLE_PRIMITIVES = ("len", "str", "bool", "float", "int")
_UNHANDLEABLE_RE = re.compile(
    r"\b(" + "|".join(_UNHANDLEABLE_PRIMITIVES) + r")\s*\("
)


def r170_can_handle(substrate: Any, candidate: Any) -> tuple[bool, str]:
    """Cage `can_handle` predicate for the symbolic_logic_cage gate.

    Engages when:
      - cage_meta declares non-empty `algebraic_constraints`
      - cage_meta.class is NOT a py_exec class
      - the form, after AST-rewrite, parses as a single SymPy expression
        without referencing un-mappable primitives (len/str/bool/...)

    Refuses (returns False with explicit reason) otherwise. Telemetry
    callers MUST be able to distinguish "gate engaged and passed" from
    "gate refused to engage" — so the diagnostic strings here are the
    structured reason for refusal.
    """
    meta = getattr(substrate, "meta", {}) or {}
    cage_class = str(meta.get("class", "") or "").strip().lower()
    if cage_class in ("oeis_py_exec", "py_exec"):
        return False, (
            f"R170 refused: cage_meta.class={cage_class!r} is a "
            f"py_exec-style substrate; PARAMETRIC_FORM is a multi-statement "
            f"function body, not a SymPy-parseable expression."
        )
    constraints = meta.get("algebraic_constraints") or []
    if not isinstance(constraints, list) or not constraints:
        return False, (
            "R170 refused: cage_meta.algebraic_constraints is empty or "
            "not declared; symbolic cage has nothing to check."
        )
    # Validate that at least one constraint has provenance.
    provenanced = [
        c for c in constraints
        if isinstance(c, dict) and isinstance(c.get("provenance"), str)
        and c["provenance"].strip()
    ]
    if not provenanced:
        return False, (
            "R170 refused: no constraints carry the required `provenance` "
            "field; per GP-170 Collision-3, constraints without "
            "provenance are silently dropped at rubric load time. "
            "Declare provenance on at least one constraint to engage."
        )
    form_str = getattr(candidate, "parametric_form", None)
    if not isinstance(form_str, str) or not form_str.strip():
        return False, (
            "R170 refused: candidate.parametric_form is missing or empty; "
            "nothing to symbolically reduce."
        )
    if _UNHANDLEABLE_RE.search(form_str):
        return False, (
            "R170 refused: PARAMETRIC_FORM uses a type-coercion or "
            "categorical primitive (len/str/bool/float/int) that the "
            "symbolic cage cannot map to a SymPy algebraic object. "
            "Form falls through to numerical check."
        )
    return True, "R170 engaged"


def r170_run(substrate: Any, candidate: Any) -> ConstraintCheckResult:
    """Cage `run` adapter for R170. Pulls inputs from candidate context."""
    meta = getattr(substrate, "meta", {}) or {}
    rubric = getattr(substrate, "rubric_flags", {}) or {}

    constraints = list(meta.get("algebraic_constraints") or [])
    init_ranges = dict(getattr(candidate, "init_ranges", {}) or {})
    feature_dimensions = dict(meta.get("feature_dimensions") or {})

    # Cross-seam Collision-2: if the candidate carries a cold-LLM-seed
    # tag in its iter context, R1 messages use the dimensional-bridging
    # template instead of the fundamental-violation template.
    cross_domain_seed = bool(
        getattr(candidate, "cold_llm_erdos_seed", False)
        or getattr(candidate, "is_cold_llm_seed", False)
    )

    visible_rows = getattr(candidate, "visible_features", None)
    budget_s = float(rubric.get("symbolic_cage_budget_s", 15.0))

    return check_algebraic_constraints(
        form_str=str(candidate.parametric_form),
        constraints=constraints,
        init_ranges=init_ranges,
        feature_dimensions=feature_dimensions,
        wall_clock_budget_s=budget_s,
        cross_domain_seed=cross_domain_seed,
        visible_rows=visible_rows,
    )


def register_symbolic_logic_cage_gate(cage: Any) -> None:
    """Register the GP-170 symbolic logic cage gate with a Cage instance.

    Called from `build_cage_runtime` in `src/ztare/orchestrator/state.py`
    after `register_cross_class_gates`. Per GP-157 §3a, gate auto-loads
    based on cage_meta and rubric flags rather than autoresearch_loop
    direct-wire.
    """
    try:
        from src.ztare.gates.cage import Gate
    except ImportError:
        return  # cage module unavailable; gate is unreachable
    gate = Gate(
        name="R170_symbolic_logic_cage",
        phase="PRE_FIT",
        can_handle=r170_can_handle,
        run=r170_run,
        dependencies=[],
    )
    if hasattr(cage, "gates") and isinstance(cage.gates, dict):
        cage.gates[gate.name] = gate
        if hasattr(cage, "_topo_cache"):
            cage._topo_cache = None
