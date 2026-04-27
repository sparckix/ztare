"""Deterministic rubric + project pre-flight validator.

Enforces every rule from `docs/concepts/rubric_specification.md` and
`docs/internal/rubric_authoring_map.md` that the autoresearch loop
treats as fail-closed at launch. Run BEFORE `make loop` to catch
malformed rubrics in seconds rather than discovering them mid-run.

Exit codes:
  0  — all checks pass
  1  — at least one fail-closed rule violated
  2  — invocation error (missing args, unreadable files)

Usage:
  python scripts/validate_rubric.py PROJECT_SLUG
  python scripts/validate_rubric.py PROJECT_SLUG --verbose
  python scripts/validate_rubric.py PROJECT_SLUG --rubric-only

Wired into Makefile as `make validate-rubric PROJECT=<slug>`. The `make loop`
target depends on validate-rubric so a malformed rubric blocks launch.

NEVER invent or relax rules without first updating
`docs/concepts/rubric_specification.md` AND incrementing the spec version.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]

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


def _check_rubric(rubric: dict[str, Any], rubric_path: Path, project_slug: str) -> list[str]:
    """Returns list of error strings. Empty = passed."""
    errors: list[str] = []
    info: list[str] = []

    # 1. Required scalar fields
    if not rubric.get("persona"):
        errors.append(_err("persona missing or empty (rubric_specification.md §3)"))
    else:
        info.append(_ok("persona present"))

    if not rubric.get("dimensions"):
        errors.append(_err("dimensions list missing or empty (rubric_specification.md §3)"))
        return errors + info  # nothing else to check
    if not isinstance(rubric["dimensions"], list):
        errors.append(_err("dimensions must be a list"))
        return errors + info

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

    # 3. rubric_mode discipline (GP-133 R4 §16-18)
    rubric_mode = (rubric.get("rubric_mode") or "kepler").lower().strip()
    if rubric_mode == "newton":
        gy_dims = [
            d for d in rubric["dimensions"]
            if "generative yield" in str(d.get("name", "")).lower()
        ]
        if not gy_dims:
            errors.append(_err(
                "rubric_mode='newton' but NO dimension whose name contains 'Generative Yield' "
                "(rubric_specification.md §16, §18). Either add the dimension with weight ≥15 OR "
                "downgrade rubric_mode to 'kepler'."
            ))
        else:
            gy_w = float(gy_dims[0].get("weight", 0))
            if gy_w < 15:
                errors.append(_err(
                    f"rubric_mode='newton' Generative Yield dimension weight = {gy_w} < 15 "
                    "(rubric_specification.md §18 minimum)."
                ))
            else:
                info.append(_ok(f"newton-mode Generative Yield dimension found, weight={gy_w}"))
    elif rubric_mode == "kepler":
        info.append(_ok("rubric_mode=kepler (no Generative Yield requirement)"))
    elif rubric.get("rubric_mode"):
        errors.append(_err(f"rubric_mode='{rubric.get('rubric_mode')}' not in {{'kepler','newton'}} (rubric_specification.md §16)"))

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

    return errors + info


def _check_project(project_dir: Path, rubric_mode: str) -> list[str]:
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
                f"missing required file: {path.relative_to(REPO)} (rubric_authoring_map.md §2)"
            ))
        elif kind == "dir" and not path.is_dir():
            errors.append(_err(
                f"missing required directory: {path.relative_to(REPO)} (rubric_authoring_map.md §2)"
            ))
        else:
            info.append(_ok(f"{name} present"))

    # Newton-mode charter must have "Secondary observable" field per §18
    if rubric_mode == "newton":
        charter_path = project_dir / "project_charter.md"
        if charter_path.is_file():
            charter_text = charter_path.read_text(encoding="utf-8", errors="ignore").lower()
            if "secondary observable" not in charter_text:
                errors.append(_err(
                    "rubric_mode='newton' but project_charter.md has no 'Secondary observable' "
                    "field (rubric_specification.md §18 — charter and rubric move in lock-step)."
                ))
            else:
                info.append(_ok("newton-mode charter has Secondary observable field"))

    return errors + info


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deterministic rubric + project pre-flight validator."
    )
    parser.add_argument("project_slug", help="Project slug (e.g., gp146_arnold_cat_map_validation)")
    parser.add_argument("--verbose", action="store_true", help="Show successful checks too")
    parser.add_argument("--rubric-only", action="store_true", help="Skip project-dir checks")
    args = parser.parse_args()

    rubric_path = REPO / "rubrics" / f"{args.project_slug}.json"
    project_dir = REPO / "projects" / args.project_slug

    if not rubric_path.is_file():
        print(f"  ❌ rubric not found: {rubric_path.relative_to(REPO)}", file=sys.stderr)
        return 2
    try:
        rubric = json.loads(rubric_path.read_text())
    except json.JSONDecodeError as exc:
        print(f"  ❌ rubric JSON malformed: {exc}", file=sys.stderr)
        return 2

    print(f"validate_rubric: {args.project_slug}")
    print(f"  rubric: {rubric_path.relative_to(REPO)}")
    if not args.rubric_only:
        print(f"  project: {project_dir.relative_to(REPO)}")

    rubric_msgs = _check_rubric(rubric, rubric_path, args.project_slug)
    project_msgs: list[str] = []
    if not args.rubric_only:
        project_msgs = _check_project(project_dir, (rubric.get("rubric_mode") or "kepler").lower())

    all_msgs = rubric_msgs + project_msgs
    errors = [m for m in all_msgs if m.startswith("  ❌")]
    warnings = [m for m in all_msgs if m.startswith("  ⚠️")]
    successes = [m for m in all_msgs if m.startswith("  ✅")]

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
        print("  Map:  docs/internal/rubric_authoring_map.md")
        return 1
    else:
        if warnings:
            print(f"  RESULT: PASSED with {len(warnings)} warning(s) (non-fatal).")
        else:
            print(f"  RESULT: PASSED — {len(successes)} checks OK.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
