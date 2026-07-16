"""Deterministic rubric + project pre-flight validator.

Enforces every rule from `docs/concepts/rubric_specification.md` and
`docs/internal/agent_workflow/rubric_authoring_map.md` that the autoresearch loop
treats as fail-closed at launch. Run BEFORE `make loop` to catch
malformed rubrics in seconds rather than discovering them mid-run.

Exit codes:
  0  — all checks pass
  1  — at least one fail-closed rule violated
  2  — invocation error (missing args, unreadable files)

Usage:
  python scripts/public/validators/validate_rubric.py PROJECT_SLUG
  python scripts/public/validators/validate_rubric.py PROJECT_SLUG --verbose
  python scripts/public/validators/validate_rubric.py PROJECT_SLUG --rubric rubrics/custom.json
  python scripts/public/validators/validate_rubric.py PROJECT_SLUG --rubric-only

Wired into Makefile as `make validate-rubric PROJECT=<slug>`. The `make loop`
target depends on validate-rubric so a malformed rubric blocks launch.

NEVER invent or relax rules without first updating
`docs/concepts/rubric_specification.md` AND incrementing the spec version.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ztare.orchestrator.contract_table import get_spec_by_class
from ztare.orchestrator.submission_path_helpers import (
    requires_i_model_submission,
    submission_contract_kind,
)
from ztare.validator.rubric_mode_resolver import validate_rubric_mode_contract

KNOWN_FALSIFICATION_MODES = {
    "numerical_proof",
    "bounded_discriminator",
    "qualitative_thesis",
    "narrative",  # legacy; some old rubrics still use
}


def _err(msg: str) -> str:
    return f"  ❌ {msg}"


def _warn(msg: str) -> str:
    return f"  ⚠️  {msg}"


def _ok(msg: str) -> str:
    return f"  ✅ {msg}"


def _rel(path: Path, repo: Path = REPO) -> str:
    try:
        return str(path.relative_to(repo))
    except ValueError:
        return str(path)


def _secondary_observable_contract_errors(rubric: dict[str, Any]) -> list[str]:
    contract = rubric.get("secondary_observable_contract")
    if contract is None:
        return []
    if not isinstance(contract, dict):
        return ["secondary_observable_contract must be an object when present."]
    required = ("observable", "measurement", "expected_range", "falsifier")
    missing = [key for key in required if not str(contract.get(key, "") or "").strip()]
    if missing:
        return [
            "secondary_observable_contract missing non-empty field(s): "
            + ", ".join(missing)
        ]
    return []


def _has_secondary_observable_contract(rubric: dict[str, Any]) -> bool:
    return not _secondary_observable_contract_errors(rubric) and isinstance(
        rubric.get("secondary_observable_contract"),
        dict,
    )


def _check_rubric(rubric: dict[str, Any], rubric_path: Path, project_slug: str) -> list[str]:
    """Returns list of error strings. Empty = passed."""
    errors: list[str] = []
    info: list[str] = []

    # 1. Required scalar fields
    personas = rubric.get("personas")
    if isinstance(personas, dict) and any(
        isinstance(v, str) and v.strip() for v in personas.values()
    ):
        info.append(_ok("personas dict present (role-conditional)"))
    elif rubric.get("persona"):
        info.append(_ok("persona present"))
    else:
        errors.append(
            _err("persona (or personas dict) missing or empty (rubric_specification.md §3)")
        )

    if not rubric.get("dimensions"):
        errors.append(_err("dimensions list missing or empty (rubric_specification.md §3)"))
        return errors + info  # nothing else to check
    if not isinstance(rubric["dimensions"], list):
        errors.append(_err("dimensions must be a list"))
        return errors + info
    if not isinstance(rubric.get("criteria"), dict) or not rubric.get("criteria"):
        errors.append(_err(
            "criteria object missing or empty; test_thesis.py meta-judge reads "
            "main_rubric_data['criteria'] and will crash without it."
        ))

    # 2. Weight sum (floats permitted; total must equal 100 within 1e-6)
    weight_sum = 0.0
    for i, dim in enumerate(rubric["dimensions"]):
        if not isinstance(dim, dict):
            errors.append(_err(f"dimensions[{i}] is not an object"))
            continue
        if "name" not in dim:
            errors.append(_err(f"dimensions[{i}] missing 'name'"))
        if "weight" not in dim:
            errors.append(_err(f"dimensions[{i}] missing 'weight'"))
            continue
        try:
            w = float(dim["weight"])
        except (TypeError, ValueError):
            errors.append(_err(f"dimensions[{i}] weight not numeric: {dim.get('weight')!r}"))
            continue
        if w < 0:
            errors.append(_err(f"dimensions[{i}] negative weight: {w}"))
        weight_sum += w
    if abs(weight_sum - 100.0) > 1e-6:
        errors.append(_err(
            f"dimension weight sum = {weight_sum:g}, must be 100 within 1e-6 "
            "(rubric_specification.md §3)"
        ))
    else:
        info.append(_ok(f"weight sum = 100 across {len(rubric['dimensions'])} dimensions"))

    # 3. rubric_mode discipline (GP-133 R4 §16-18). Keep this validator
    # aligned with the loop's launch contract; do not maintain a parallel
    # allowlist here.
    mode_result = validate_rubric_mode_contract(rubric)
    if not mode_result.ok:
        errors.append(_err(mode_result.message))
    elif mode_result.mode == "newton":
        for contract_error in _secondary_observable_contract_errors(rubric):
            errors.append(_err(contract_error + " (rubric_specification.md §18)"))
        gy_dims = [
            d for d in rubric["dimensions"]
            if "generative yield" in str(d.get("name", "")).lower()
        ]
        gy_w = float(gy_dims[0].get("weight", 0)) if gy_dims else 0.0
        info.append(_ok(f"newton-mode Generative Yield dimension found, weight={gy_w}"))
    elif mode_result.message:
        info.append(_ok(mode_result.message))
    else:
        info.append(_ok("rubric_mode unset (legacy accepted; loop uses explicit defaults elsewhere)"))

    # 4. py_exec grammar gates (§17)
    grammar = (rubric.get("fit_expression_grammar") or "").lower().strip()
    if grammar == "py_exec":
        if not rubric.get("py_exec_authorized_by"):
            errors.append(_err(
                "fit_expression_grammar='py_exec' requires 'py_exec_authorized_by' "
                "(seam-id) (rubric_specification.md §17)."
            ))
        try:
            byte_budget = int(rubric.get("expression_byte_budget", 0))
            if byte_budget <= 0:
                errors.append(_err(
                    f"py_exec requires expression_byte_budget > 0, got {byte_budget} "
                    "(rubric_specification.md §17)."
                ))
        except (TypeError, ValueError):
            errors.append(_err(
                f"expression_byte_budget not a positive int: {rubric.get('expression_byte_budget')!r}"
            ))

    # 5. falsification_mode check
    fm = rubric.get("falsification_mode")
    if fm is not None and fm not in KNOWN_FALSIFICATION_MODES:
        errors.append(_err(
            f"falsification_mode='{fm}' not in known set {sorted(KNOWN_FALSIFICATION_MODES)} "
            "(rubric_specification.md §4-5)."
        ))

    # 6. Qualitative-flavor gate opt-outs (rubric_authoring_map §3)
    fit_score_mode = (rubric.get("fit_score_mode") or "continuous_l2").lower().strip()
    is_qualitative = fit_score_mode == "none"
    if is_qualitative:
        # Each disable flag should be true with a _reason
        flag_reason_pairs = [
            ("disable_evidence_fit_gate", "disable_evidence_fit_gate_reason"),
            ("disable_uniqueness_gap_gate", "disable_uniqueness_gap_gate_reason"),
        ]
        for flag, reason in flag_reason_pairs:
            if not rubric.get(flag):
                errors.append(_err(
                    f"qualitative rubric (fit_score_mode='none') must set {flag}=true "
                    "(rubric_authoring_map.md §3)."
                ))
            elif not rubric.get(reason):
                errors.append(_err(
                    f"{flag}=true requires explanatory {reason} string (rubric_authoring_map.md §5)."
                ))
        # farther_tail_region must be null + _disable_reason
        if rubric.get("farther_tail_region") is not None:
            errors.append(_err(
                "qualitative rubric must set farther_tail_region=null "
                "(rubric_authoring_map.md §3)."
            ))

    # 7. criteria mirror (warning-level)
    criteria = rubric.get("criteria") or {}
    if criteria and rubric.get("dimensions"):
        crit_keys_lower = {k.lower().replace("_", " ").replace("-", " ") for k in criteria.keys()}
        for dim in rubric["dimensions"]:
            dname = str(dim.get("name", "")).lower().replace("_", " ").replace("-", " ")
            # crude match — substring either direction
            if dname and not any(dname[:8] in ck or ck[:8] in dname for ck in crit_keys_lower):
                info.append(_warn(
                    f"dimension '{dim.get('name')}' has no matching criteria key "
                    "(rubric_authoring_map.md §6 mirror-discipline; non-fatal, may degrade scoring)."
                ))

    # 8. Evidence-gap score caps (§7). These are opt-in raw-score safety rails:
    # malformed rules are dangerous because they can silently fail to cap proof
    # inflation, so validate the machine-readable shape at preflight.
    cap_rules = rubric.get("evidence_gap_score_caps")
    if cap_rules is not None:
        if not isinstance(cap_rules, list):
            errors.append(_err(
                "evidence_gap_score_caps must be a list of rule objects "
                "(rubric_specification.md §7)."
            ))
        elif not cap_rules:
            errors.append(_err("evidence_gap_score_caps is present but empty."))
        else:
            selector_keys = {
                "severity_any",
                "severities_any",
                "gap_type_any",
                "gap_types_any",
                "target_contains_any",
                "targets_any",
                "description_contains_any",
                "descriptions_any",
                "text_contains_any",
                "keywords_any",
            }
            for idx, rule in enumerate(cap_rules):
                if not isinstance(rule, dict):
                    errors.append(_err(f"evidence_gap_score_caps[{idx}] must be an object."))
                    continue
                try:
                    cap = int(rule.get("cap"))
                except (TypeError, ValueError):
                    errors.append(_err(
                        f"evidence_gap_score_caps[{idx}].cap must be an integer."
                    ))
                    continue
                if cap < 0 or cap > 100:
                    errors.append(_err(
                        f"evidence_gap_score_caps[{idx}].cap={cap} outside 0..100."
                    ))
                if not str(rule.get("reason", "")).strip():
                    errors.append(_err(
                        f"evidence_gap_score_caps[{idx}] missing non-empty reason."
                    ))
                if not any(key in rule for key in selector_keys):
                    errors.append(_err(
                        f"evidence_gap_score_caps[{idx}] has no selector; add severity/gap/target/"
                        "description/text match keys."
                    ))
                for key in selector_keys:
                    if key not in rule:
                        continue
                    value = rule[key]
                    if isinstance(value, str):
                        if not value.strip():
                            errors.append(_err(
                                f"evidence_gap_score_caps[{idx}].{key} is an empty string."
                            ))
                    elif isinstance(value, list):
                        if not value or not all(isinstance(item, str) and item.strip() for item in value):
                            errors.append(_err(
                                f"evidence_gap_score_caps[{idx}].{key} must be a non-empty list of strings."
                            ))
                    else:
                        errors.append(_err(
                            f"evidence_gap_score_caps[{idx}].{key} must be a string or list of strings."
                        ))
                if cap >= 90:
                    info.append(_warn(
                        f"evidence_gap_score_caps[{idx}] cap={cap}; proof-band caps usually "
                        "should be below 90."
                    ))
            info.append(_ok(f"evidence_gap_score_caps declared ({len(cap_rules)} rule(s))"))

    return errors + info


def _check_project(
    project_dir: Path,
    rubric: dict[str, Any],
    rubric_mode: str,
    repo: Path = REPO,
) -> list[str]:
    """Returns list of error strings."""
    errors: list[str] = []
    info: list[str] = []
    required = {
        "project_charter.md": "file",
        "evidence.txt": "file",
        "thesis.md": "file",
        "raw": "dir",
    }
    for name, kind in required.items():
        path = project_dir / name
        if kind == "file" and not path.is_file():
            errors.append(_err(
                f"missing required file: {_rel(path, repo)} (rubric_authoring_map.md §2)"
            ))
        elif kind == "dir" and not path.is_dir():
            errors.append(_err(
                f"missing required directory: {_rel(path, repo)} (rubric_authoring_map.md §2)"
            ))
        else:
            info.append(_ok(f"{name} present"))

    if rubric.get("holdout_hard_gate"):
        for name in ("gate_harness.py", "evidence_holdout.txt"):
            path = project_dir / name
            if not path.is_file():
                errors.append(_err(
                    f"holdout_hard_gate=true requires {_rel(path, repo)} "
                    "(rubric_specification.md §2, §5, §15)"
                ))
            else:
                info.append(_ok(f"holdout hard-gate companion present: {name}"))

    theorem_contract = rubric.get("theorem_packet_contract")
    if theorem_contract is not None:
        if rubric.get("require_i_model_in_submission") is not False:
            errors.append(_err(
                "theorem_packet_contract present but require_i_model_in_submission is not false; "
                "theorem-packet substrates must opt out of scalar I_model R1 scaffolding "
                "(rubric_specification.md §7; harness_specification.md §4)"
            ))
        if not isinstance(theorem_contract, dict):
            errors.append(_err("theorem_packet_contract must be an object when present"))
        else:
            required_functions = theorem_contract.get("required_top_level_functions")
            if not isinstance(required_functions, list) or not required_functions:
                errors.append(_err(
                    "theorem_packet_contract.required_top_level_functions must be a non-empty list"
                ))
                required_functions = []
            else:
                bad_names = [
                    name for name in required_functions
                    if not isinstance(name, str) or not name.isidentifier()
                ]
                if bad_names:
                    errors.append(_err(
                        "theorem_packet_contract.required_top_level_functions contains "
                        f"non-identifier entries: {bad_names!r}"
                    ))
                else:
                    info.append(_ok(
                        "theorem-packet required functions declared: "
                        + ", ".join(required_functions)
                    ))

            def _top_level_functions(path: Path) -> set[str]:
                try:
                    tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
                except (OSError, SyntaxError):
                    return set()
                return {
                    node.name for node in tree.body
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                }

            for file_name in ("evidence.txt", "test_model.py", "gate_harness.py"):
                path = project_dir / file_name
                if not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                missing: list[str] = []
                if file_name == "test_model.py":
                    present = _top_level_functions(path)
                    missing = [name for name in required_functions if name not in present]
                else:
                    missing = [
                        name for name in required_functions
                        if name not in text and f"def {name}(" not in text
                    ]
                if missing:
                    errors.append(_err(
                        f"theorem_packet_contract declares {missing!r}, but "
                        f"{_rel(path, repo)} does not expose/mention them."
                    ))
                elif required_functions:
                    info.append(_ok(
                        f"theorem-packet contract mirrored in {_rel(path, repo)}"
                    ))

    # Newton-mode charter must have "Secondary observable" field per §18
    if rubric_mode == "newton":
        if _has_secondary_observable_contract(rubric):
            info.append(_ok("newton-mode rubric has secondary_observable_contract"))
        else:
            charter_path = project_dir / "project_charter.md"
            if not charter_path.is_file():
                return errors + info
            charter_text = charter_path.read_text(encoding="utf-8", errors="ignore").lower()
            if "secondary observable" not in charter_text:
                errors.append(_err(
                    "rubric_mode='newton' but neither secondary_observable_contract nor "
                    "project_charter.md 'Secondary observable' field is present "
                    "(rubric_specification.md §18)."
                ))
            else:
                info.append(_ok("newton-mode charter has Secondary observable field"))

    return errors + info


def _launch_contract_summary(rubric: dict[str, Any]) -> dict[str, Any]:
    """Return the active launch-time submission contract for a rubric.

    This is intentionally observational. The loop and briefing providers still
    own enforcement; the validator exposes the same decision so trace/userland
    can show the contract before an in-loop run starts.
    """
    cage_meta = rubric.get("cage_meta") if isinstance(rubric.get("cage_meta"), dict) else {}
    cage_meta_class = str(cage_meta.get("class") or "").strip()
    spec = get_spec_by_class(cage_meta_class) if cage_meta_class else None
    contract_kind = submission_contract_kind(rubric)
    requires_i_model = requires_i_model_submission(rubric)
    theorem_contract = rubric.get("theorem_packet_contract")
    if not isinstance(theorem_contract, dict):
        theorem_contract = {}
    required_functions = [
        str(name)
        for name in theorem_contract.get("required_top_level_functions") or []
        if isinstance(name, str)
    ]
    if contract_kind == "theorem_packet":
        expected_surface = "theorem-packet top-level functions"
    elif contract_kind == "assertion_suite":
        expected_surface = "plain Python assertion suite"
    else:
        expected_surface = "numeric I_model submission"
    return {
        "schema": "ztare-launch-contract-summary-v1",
        "submission_contract_kind": contract_kind,
        "expected_submission_surface": expected_surface,
        "requires_i_model": requires_i_model,
        "rubric_mode": str(rubric.get("rubric_mode") or "").strip().lower() or None,
        "falsification_mode": str(rubric.get("falsification_mode") or "").strip().lower() or None,
        "fit_score_mode": str(rubric.get("fit_score_mode") or "").strip().lower() or None,
        "enable_fit_primitive": bool(rubric.get("enable_fit_primitive", True)),
        "enable_fit_primitive_features": bool(rubric.get("enable_fit_primitive_features", False)),
        "holdout_hard_gate": bool(rubric.get("holdout_hard_gate", False)),
        "cage_meta_class": cage_meta_class or None,
        "registered_substrate_abi": spec.abi.name.lower() if spec is not None else None,
        "registered_signature": spec.signature_str if spec is not None else None,
        "theorem_required_functions": required_functions,
        "numeric_cross_class_diagnostic_eligible": cage_meta_class in {"nd_features", "time_series"},
    }


def validate_rubric_project(
    project_slug: str,
    *,
    rubric: str | Path | None = None,
    repo: str | Path = REPO,
    rubric_only: bool = False,
) -> dict[str, Any]:
    repo_path = Path(repo).resolve()
    rubric_path = Path(rubric) if rubric else repo_path / "rubrics" / f"{project_slug}.json"
    if not rubric_path.is_absolute():
        rubric_path = repo_path / rubric_path
    project_dir = repo_path / "projects" / project_slug

    if not rubric_path.is_file():
        return {
            "ok": False,
            "exit_code": 2,
            "rubric_path": _rel(rubric_path, repo_path),
            "project_dir": _rel(project_dir, repo_path),
            "messages": [],
            "errors": [_err(f"rubric not found: {_rel(rubric_path, repo_path)}")],
            "warnings": [],
            "successes": [],
            "launch_contract": None,
        }
    try:
        rubric_data = json.loads(rubric_path.read_text())
    except json.JSONDecodeError as exc:
        return {
            "ok": False,
            "exit_code": 2,
            "rubric_path": _rel(rubric_path, repo_path),
            "project_dir": _rel(project_dir, repo_path),
            "messages": [],
            "errors": [_err(f"rubric JSON malformed: {exc}")],
            "warnings": [],
            "successes": [],
            "launch_contract": None,
        }

    rubric_msgs = _check_rubric(rubric_data, rubric_path, project_slug)
    project_msgs: list[str] = []
    if not rubric_only:
        project_msgs = _check_project(
            project_dir,
            rubric_data,
            (rubric_data.get("rubric_mode") or "kepler").lower(),
            repo=repo_path,
        )

    all_msgs = rubric_msgs + project_msgs
    errors = [m for m in all_msgs if m.startswith("  ❌")]
    warnings = [m for m in all_msgs if m.startswith("  ⚠️")]
    successes = [m for m in all_msgs if m.startswith("  ✅")]
    return {
        "ok": not errors,
        "exit_code": 1 if errors else 0,
        "rubric_path": _rel(rubric_path, repo_path),
        "project_dir": _rel(project_dir, repo_path),
        "messages": all_msgs,
        "errors": errors,
        "warnings": warnings,
        "successes": successes,
        "launch_contract": _launch_contract_summary(rubric_data),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deterministic rubric + project pre-flight validator."
    )
    parser.add_argument("project_slug", help="Project slug (e.g., gp146_arnold_cat_map_validation)")
    parser.add_argument("--rubric", help="Optional rubric path; defaults to rubrics/<project_slug>.json")
    parser.add_argument("--verbose", action="store_true", help="Show successful checks too")
    parser.add_argument("--rubric-only", action="store_true", help="Skip project-dir checks")
    args = parser.parse_args()

    print(f"validate_rubric: {args.project_slug}")
    result = validate_rubric_project(
        args.project_slug,
        rubric=args.rubric,
        repo=REPO,
        rubric_only=args.rubric_only,
    )
    print(f"  rubric: {result['rubric_path']}")
    if not args.rubric_only:
        print(f"  project: {result['project_dir']}")

    errors = list(result["errors"])
    warnings = list(result["warnings"])
    successes = list(result["successes"])

    if result["exit_code"] == 2:
        for m in errors:
            print(m, file=sys.stderr)
        return 2

    if args.verbose or errors or warnings:
        for m in successes if args.verbose else []:
            print(m)
        for m in warnings:
            print(m)
        for m in errors:
            print(m)

    print("")
    if errors:
        print(f"  RESULT: FAILED — {len(errors)} error(s), {len(warnings)} warning(s).")
        print("  Fix the rubric/project before running `make loop`.")
        print("  Spec: docs/concepts/rubric_specification.md")
        print("  Map:  docs/internal/agent_workflow/rubric_authoring_map.md")
        return 1
    else:
        if warnings:
            print(f"  RESULT: PASSED with {len(warnings)} warning(s) (non-fatal).")
        else:
            print(f"  RESULT: PASSED — {len(successes)} checks OK.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
