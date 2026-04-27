"""GP-157 v5.0 — substrate-contract adherence telemetry.

Operator concern (2026-04-25 night): the substrate-contract hint is one
of ~15 prompt sections; the mutator may skim past it. Empirical question
whether the hint is effective. This module surfaces the answer by
inspecting each iteration's emitted test_model.py for contract
violations and emitting a JSONL log to workspace/contract_violations.jsonl.

What we measure (per iteration):
  - Active contract: A (assert), B (features-dict), C (scalar 1D), or none.
  - Whether the emitted test_model.py honors the active contract's shape.
  - Specific violation codes when it doesn't.

Scope: SHAPE checks only. No semantic judgment about the mutator's
scientific choice. Deliberately conservative — false positives erode
trust faster than false negatives lose signal.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional

from src.ztare.orchestrator.iter_context import IterContext
from src.ztare.orchestrator.prompt import (
    needs_override_contract_hint,
    needs_scalar_contract_hint,
)


VIOLATION_CODES = {
    "module_level_imodel_call": "I_model(...) called at module scope (R1 strike class)",
    "wrong_signature_b_for_c": "Contract C active but def I_model(features) emitted (Contract B signature)",
    "wrong_signature_c_for_b": "Contract B active but def I_model(d) emitted (Contract C signature)",
    "missing_imodel_def": "test_model.py has no `def I_model(`",
    "deferred_assert_helper": "asserts hidden in non-called helper (e.g., _post_fit_sanity)",
    "nan_return_literal": "I_model body returns NaN literal",
    "runtime_nan_return": "I_model returned NaN/inf/non-float at runtime on visible-set sample",
    "runtime_import_failure": "test_model.py raised on import (apparatus cannot run gates)",
    "runtime_imodel_raises": "I_model raised an exception on visible-set sample",
}


@dataclass(frozen=True)
class AdherenceReport:
    """Per-iteration contract-adherence snapshot."""
    iter: int
    active_contract: str  # "A" / "B" / "C" / "none"
    violations: list[str] = field(default_factory=list)
    test_model_present: bool = True

    @property
    def adheres(self) -> bool:
        return not self.violations

    def to_jsonl_line(self) -> str:
        return json.dumps({
            "iter": self.iter,
            "active_contract": self.active_contract,
            "test_model_present": self.test_model_present,
            "violations": self.violations,
            "adheres": self.adheres,
        })


def _resolve_active_contract(
    rubric_data: Mapping[str, Any],
    project_dir: Path,
) -> str:
    """Return one of "A" / "B" / "C" / "none".

    Mirrors the resolution order in select_substrate_contract_hint.
    Used only for telemetry classification — not for prompt assembly.
    """
    if needs_override_contract_hint(rubric_data):
        return "B"
    if needs_scalar_contract_hint(rubric_data, project_dir=project_dir):
        return "C"
    # Legacy assert-based discriminator default.
    cage_meta = rubric_data.get("cage_meta") or {}
    cls = cage_meta.get("class") if isinstance(cage_meta, Mapping) else None
    if cls and str(cls).strip().lower() == "1d":
        return "A"
    return "none"


def check_contract_adherence(
    test_model_text: str,
    rubric_data: Mapping[str, Any],
    project_dir: Path,
) -> list[str]:
    """Inspect emitted test_model.py for shape violations.

    Returns a list of violation codes (each from VIOLATION_CODES). Empty
    list = adherent. False-positive rate is the constraint — keep
    detection narrow.
    """
    violations: list[str] = []
    if not test_model_text:
        return ["missing_imodel_def"]

    contract = _resolve_active_contract(rubric_data, project_dir)

    # Universal: must define I_model
    if not re.search(r"\bdef\s+I_model\s*\(", test_model_text):
        violations.append("missing_imodel_def")
        return violations  # other checks meaningless without the def

    # Universal: NO module-level I_model(...) calls.
    # Track whether we are inside an `if __name__ == "__main__":` block —
    # those are debug guards, not module-load-time code per panel review.
    in_main_guard = False
    for lineno, line in enumerate(test_model_text.splitlines(), 1):
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        # Toggle main-guard state on column-0 lines that match the guard.
        if line == stripped and re.match(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]', stripped):
            in_main_guard = True
            continue
        # Reset on any new column-0 def/class/if/for/while/with.
        if line == stripped and re.match(r"(def|class|if|for|while|with|try)\s+", stripped):
            in_main_guard = False
        if line != stripped:
            continue  # indented — inside a function body or guard
        if in_main_guard:
            continue  # module-level debug guard — allowed
        # Skip the def / class / import lines themselves.
        if re.match(r"def\s+", stripped) or re.match(r"class\s+", stripped):
            continue
        if stripped.startswith("from ") or stripped.startswith("import "):
            continue
        # Detect `I_model(` invocation — but not `I_model = ...` (rebind).
        if re.search(r"\bI_model\s*\(", stripped) and not re.match(r"I_model\s*=", stripped):
            violations.append("module_level_imodel_call")
            break

    # Contract-shape checks
    if contract == "C":
        # Expect def I_model(d ...) — scalar. If the signature uses
        # `features` as the first arg, the mutator emitted Contract B shape.
        m = re.search(r"def\s+I_model\s*\(\s*([A-Za-z_]\w*)", test_model_text)
        if m and m.group(1).strip().lower() in {"features"}:
            violations.append("wrong_signature_b_for_c")
    elif contract == "B":
        m = re.search(r"def\s+I_model\s*\(\s*([A-Za-z_]\w*)", test_model_text)
        if m and m.group(1).strip().lower() in {"d", "x"}:
            violations.append("wrong_signature_c_for_b")

    # Deferred-assert detection: ANY private helper (`def _<name>(`)
    # whose body contains `assert` but is never called at module scope or
    # inside I_model. Generalized 2026-04-25 night per panel review:
    # previously hardcoded {_post_fit_sanity, _validate, _sanity_check,
    # _verify_assumptions} — the next mutator hiding asserts in
    # `_check_invariants()` or any other private name would have evaded.
    private_helper_pattern = re.compile(r"def\s+(_\w+)\s*\(")
    for helper_match in private_helper_pattern.finditer(test_model_text):
        helper_name = helper_match.group(1)
        if helper_name in {"_", "__init__", "__call__", "__repr__"}:
            continue  # dunder/standard methods — not helpers
        body_start = helper_match.end()
        next_def = re.search(r"\ndef\s+", test_model_text[body_start:])
        body = test_model_text[body_start: body_start + next_def.start()] if next_def else test_model_text[body_start:]
        if "assert" not in body:
            continue
        # Is the helper called anywhere except at its own def line?
        call_pattern = re.compile(rf"\b{re.escape(helper_name)}\s*\(")
        called_anywhere = False
        for c in call_pattern.finditer(test_model_text):
            preceding = test_model_text[max(0, c.start() - 4):c.start()]
            if preceding.endswith("def "):
                continue  # this is the def line itself
            called_anywhere = True
            break
        if not called_anywhere:
            violations.append("deferred_assert_helper")
            break

    # NaN literal in I_model body
    nan_in_body = re.search(
        r"def\s+I_model\s*\([^)]*\)[^:]*:[^#]*?(?:return\s+float\(['\"]nan['\"]\)|return\s+math\.nan|return\s+np\.nan)",
        test_model_text,
        re.DOTALL | re.IGNORECASE,
    )
    if nan_in_body:
        violations.append("nan_return_literal")

    return violations


def runtime_check_imodel(
    test_model_path: Path,
    *,
    sample_count: int = 3,
) -> list[str]:
    """Runtime adherence: import test_model.py + call I_model on
    sample VISIBLE_SET rows; flag NaN/inf/non-float returns + raises.

    Catches the case where test_model.py is statically clean
    (no deferred-assert helper, signature correct) but I_model
    returns NaN due to arithmetic bug — surfaced by gp159 o3 mutator
    runs 2026-04-25 night. Static analysis cannot see this.

    Returns a list of violation codes; empty when adherent at runtime.
    Caller decides whether to surface as warnings or to use as R1
    strike triggers.
    """
    if not test_model_path.exists():
        return []  # nothing to check; structural check covers this

    violations: list[str] = []
    import importlib.util as _ilu
    import math as _math
    import sys as _sys

    spec = _ilu.spec_from_file_location(
        f"_adherence_probe_{test_model_path.parent.name}",
        str(test_model_path),
    )
    if spec is None or spec.loader is None:
        return violations

    module = _ilu.module_from_spec(spec)
    # Add the project dir to sys.path so `from features import ...`
    # works if the substrate authors features.py.
    project_dir = str(test_model_path.parent)
    sys_path_added = False
    if project_dir not in _sys.path:
        _sys.path.insert(0, project_dir)
        sys_path_added = True

    try:
        try:
            spec.loader.exec_module(module)
        except Exception:
            violations.append("runtime_import_failure")
            return violations

        I_model = getattr(module, "I_model", None)
        if I_model is None or not callable(I_model):
            return violations  # structural check catches missing def

        visible = getattr(module, "VISIBLE_SET", None)
        if not visible:
            return violations  # nothing to probe against

        # Probe `sample_count` rows. Format may be:
        #   (id, y, features_dict)  — Contract B (nd_features substrate)
        #   (id, x, y)              — Contract C (1D scalar with id+x+y, gp159 pattern)
        #   (x, y)                  — legacy 1D
        # Stop on first NaN-class violation.
        for entry in list(visible)[:sample_count]:
            try:
                if not isinstance(entry, (tuple, list)) or len(entry) < 2:
                    continue
                # Determine call signature
                if len(entry) >= 3 and isinstance(entry[2], dict):
                    # (id, y, features_dict) — Contract B shape
                    result = I_model(entry[2])
                elif len(entry) >= 3 and isinstance(entry[0], int) and isinstance(entry[1], (int, float)):
                    # (id, x, y) — gp159 / gp160 / gp161 / gp145 pattern.
                    # entry[0] is the id (integer); entry[1] is the d-value (real).
                    # Call I_model on the d-value, NOT the id.
                    result = I_model(entry[1])
                elif len(entry) == 2 and isinstance(entry[0], (int, float)):
                    # Legacy (x, y) — call on x.
                    result = I_model(entry[0])
                else:
                    continue
            except Exception:
                violations.append("runtime_imodel_raises")
                break

            if not isinstance(result, (int, float)):
                violations.append("runtime_nan_return")
                break
            try:
                if _math.isnan(float(result)) or _math.isinf(float(result)):
                    violations.append("runtime_nan_return")
                    break
            except (TypeError, ValueError):
                violations.append("runtime_nan_return")
                break
    finally:
        if sys_path_added:
            try:
                _sys.path.remove(project_dir)
            except ValueError:
                pass

    return violations


def emit_adherence(
    ctx: IterContext,
    test_model_text: str,
) -> AdherenceReport:
    """Build + emit an AdherenceReport from the current iter's test_model.py.

    Logs to ctx.workspace_dir / "contract_violations.jsonl" (append).
    Returns the report so the caller can decide whether to act on it
    (e.g., print a console banner, or in a future iteration, escalate
    by promoting the contract hint).
    """
    project_dir = ctx.workspace_dir.parent
    contract = _resolve_active_contract(ctx.rubric_data, project_dir)
    violations = check_contract_adherence(test_model_text, ctx.rubric_data, project_dir)
    report = AdherenceReport(
        iter=ctx.iteration_index + 1,
        active_contract=contract,
        violations=violations,
        test_model_present=bool(test_model_text),
    )
    log_path = ctx.workspace_dir / "contract_violations.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(report.to_jsonl_line() + "\n")
    return report


def format_adherence_summary(report: AdherenceReport) -> Optional[str]:
    """One-line console summary, or None when adherent (silent on success)."""
    if report.adheres:
        return None
    codes = ", ".join(report.violations)
    return (
        f"📋 contract-adherence: iter {report.iter}, contract={report.active_contract}, "
        f"violations=[{codes}] (logged to workspace/contract_violations.jsonl)"
    )
