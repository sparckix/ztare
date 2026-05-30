#!/usr/bin/env python3
"""Analyze LeanMill benchmark checkpoints by paired rows and family-memory slices."""
from __future__ import annotations

import argparse
import json
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import leanmill_family_specs as family_specs
from leanmill_paths import DATA_DIR, REPAIR_FAMILY_REGISTRY

DEFAULT_CHECKPOINT = f"{DATA_DIR}/evaluation_harness_run.jsonl"
DEFAULT_PREP = f"{DATA_DIR}/evaluation_harness_prep.json"
DEFAULT_REGISTRY = REPAIR_FAMILY_REGISTRY
DEFAULT_SPEC_DIR = family_specs.DEFAULT_SPEC_DIR
DEFAULT_OUT = f"{DATA_DIR}/evaluation_harness_slice_analysis.json"
DEFAULT_MD = f"{DATA_DIR}/evaluation_harness_slice_analysis.md"
ARMS = [
    "public_tool_static",
    "governed_public_tool_static",
    "governed_adaptive_execution",
    "governed_adaptive_residual_curriculum",
]
INLINE_TEMPLATE_PREFIX_RE = __import__("re").compile(r"^\s*[A-Za-z0-9_'.-]+::")

POSITIVE_EXITS = {
    "raw_closure_candidate",
    "governed_tool_tactic_closure_candidate",
    "ratified_closure",
    "exact_gap",
    "valid_falsifier",
}
PROOF_VALUE_EXITS = {"ratified_closure", "exact_gap", "valid_falsifier"}
TARGET_REFERENCE_TEMPLATE_FAILURES = {
    "positive_template_references_target_theorem",
    "negative_control_references_target_theorem",
}


def _read_json(path: str | Path) -> Any:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return None


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in p.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _target_reference_quarantine_count(specs: list[dict[str, Any]], target_names_by_row: dict[str, list[str]]) -> int:
    return sum(
        1
        for failure in family_specs.validate_specs(specs, target_names_by_row=target_names_by_row)
        if str(failure.get("failure") or "") in TARGET_REFERENCE_TEMPLATE_FAILURES
    )


def _family_template_rows(
    spec_dir: str | Path,
    *,
    target_names_by_row: dict[str, list[str]] | None = None,
) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for spec in family_specs.usable_specs(family_specs.load_specs(spec_dir), target_names_by_row=target_names_by_row):
        family = str(spec.get("family") or "")
        for template in spec.get("templates") or []:
            if not isinstance(template, dict):
                continue
            if str(template.get("test_kind") or "") != "positive":
                continue
            row_id = str(template.get("row_id") or "")
            if row_id and family:
                out[row_id].add(family)
    return out


def _registry_statuses(path: str | Path) -> dict[str, str]:
    obj = _read_json(path) or {}
    return {
        str(row.get("family") or ""): str(row.get("status") or "")
        for row in obj.get("families") or []
        if isinstance(row, dict) and str(row.get("family") or "")
    }


def _selected_order(prep: dict[str, Any]) -> list[str]:
    return [str(x) for x in prep.get("selected_rows_order") or [] if str(x)]


def _positive(rec: dict[str, Any] | None) -> bool:
    return bool(rec) and str(rec.get("learning_exit") or "") in POSITIVE_EXITS


def _proof_value(rec: dict[str, Any] | None) -> bool:
    return bool(rec) and str(rec.get("learning_exit") or "") in PROOF_VALUE_EXITS


def _artifact_has_inline_template_prefix(attempt: dict[str, Any]) -> bool:
    artifact = Path(str(attempt.get("artifact") or ""))
    if not artifact.exists() or not artifact.is_file():
        return False
    try:
        for line in artifact.read_text(errors="ignore").splitlines():
            if INLINE_TEMPLATE_PREFIX_RE.search(line):
                return True
    except OSError:
        return False
    return False


def _attempt_summary(rec: dict[str, Any] | None) -> dict[str, Any]:
    if not rec:
        return {"present": False}
    return {
        "present": True,
        "learning_exit": rec.get("learning_exit"),
        "closed": bool(rec.get("closed")),
        "attempt_count": int(rec.get("attempt_count") or 0),
        "wall_time_used_s": rec.get("wall_time_used_s"),
        "target_kind_audit": rec.get("target_kind_audit"),
    }


def _c_invocation(rec: dict[str, Any] | None) -> dict[str, Any]:
    attempts = rec.get("attempts") if isinstance(rec, dict) else []
    families = []
    template_ids = []
    for attempt in attempts or []:
        if not isinstance(attempt, dict):
            continue
        if str(attempt.get("candidate_kind") or "") == "repair_family_template":
            fam = str(attempt.get("family") or "")
            tid = str(attempt.get("candidate_id") or "")
            if fam:
                families.append(fam)
            if tid:
                template_ids.append(tid)
    return {
        "family_invoked": bool(families),
        "families_invoked": sorted(set(families)),
        "template_used": bool(template_ids),
        "template_ids": template_ids[:8],
    }


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    prep = _read_json(args.prep) or {}
    records = _read_jsonl(args.checkpoint)
    if args.run_id:
        records = [r for r in records if str(r.get("run_id") or "") == args.run_id]
    by_row: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for rec in records:
        row_id = str(rec.get("row_id") or "")
        arm = str(rec.get("arm") or "")
        if row_id and arm:
            by_row[row_id][arm] = rec
    target_names_by_row = family_specs.target_names_by_row_from_context_paths([prep.get("row_context") or ""])
    raw_specs = family_specs.load_specs(args.spec_dir)
    template_rows = _family_template_rows(args.spec_dir, target_names_by_row=target_names_by_row)
    registry_status = _registry_statuses(args.registry)
    selected = _selected_order(prep)
    if not selected:
        selected = sorted(by_row)

    paired_rows = []
    partial_rows = []
    bucket_counts = Counter()
    by_bucket_arm: dict[str, Counter[str]] = defaultdict(Counter)
    exact_gap_or_falsifier = 0
    c_wrong_family = 0
    c_eligible_rows = 0
    c_family_available_rows = 0
    c_family_starved_tool_positive_rows = 0
    c_not_reached_reasons = Counter()
    c_invoked_rows = 0
    c_eligible_positive = 0
    c_static_fail_c_positive = 0
    c_over_prune = 0

    for row_id in selected:
        arms = by_row.get(row_id, {})
        complete = all(a in arms for a in ARMS)
        public = arms.get("public_tool_static")
        governed_static = arms.get("governed_public_tool_static")
        adaptive = arms.get("governed_adaptive_execution")
        c_arm = arms.get("governed_adaptive_residual_curriculum")
        eligible_families = sorted(template_rows.get(row_id, set()))
        c_inv = _c_invocation(c_arm)
        invoked = set(c_inv["families_invoked"])
        correct = bool(invoked) and bool(invoked.intersection(eligible_families))
        c_exit = str((c_arm or {}).get("learning_exit") or "")
        c_family_candidate_count = int((c_arm or {}).get("family_candidate_count") or 0)
        c_family_available = bool(c_family_candidate_count) or bool(eligible_families)
        c_not_reached_reason = str((c_arm or {}).get("family_not_reached_reason") or "")
        if not c_not_reached_reason and c_family_available and not c_inv["family_invoked"] and _positive(c_arm):
            c_not_reached_reason = "tool_positive_before_family_inferred_legacy"
        row_exact_gap_or_falsifier = any(str((r or {}).get("learning_exit") or "") in {"exact_gap", "valid_falsifier"} for r in arms.values())
        exact_gap_or_falsifier += int(row_exact_gap_or_falsifier)
        if eligible_families:
            c_eligible_rows += int(complete)
        if c_family_available:
            c_family_available_rows += int(complete)
        if complete and c_not_reached_reason:
            c_not_reached_reasons[c_not_reached_reason] += 1
        if complete and c_not_reached_reason.startswith("tool_positive_before_family"):
            c_family_starved_tool_positive_rows += 1
        if c_inv["family_invoked"]:
            c_invoked_rows += int(complete)
        if eligible_families and c_arm and _positive(c_arm):
            c_eligible_positive += int(complete)
        if complete and not _positive(public) and _positive(c_arm):
            c_static_fail_c_positive += 1
        if complete and eligible_families and c_inv["family_invoked"] and not correct:
            c_wrong_family += 1
        if complete and governed_static and c_arm and not _positive(c_arm) and int(c_arm.get("attempt_count") or 0) < int(governed_static.get("attempt_count") or 0):
            c_over_prune += 1
        if _positive(public):
            bucket = "tool_solvable"
        elif eligible_families:
            bucket = "family_memory_eligible"
        else:
            bucket = "cold_no_known_family"
        if complete:
            bucket_counts[bucket] += 1
            for arm_id, rec in arms.items():
                by_bucket_arm[bucket][f"{arm_id}:{rec.get('learning_exit')}"] += 1
        row = {
            "row_id": row_id,
            "complete": complete,
            "bucket": bucket,
            "static_closed": _positive(public),
            "governed_static_closed": _positive(governed_static),
            "adaptive_execution_closed": _positive(adaptive),
            "adaptive_residual_closed": _positive(c_arm),
            "proof_value_exit_any_arm": any(_proof_value(r) for r in arms.values()),
            "exact_gap_or_falsifier_any_arm": row_exact_gap_or_falsifier,
            "family_eligible": bool(eligible_families),
            "eligible_families": eligible_families,
            "c_family_candidate_count": c_family_candidate_count,
            "c_family_available": c_family_available,
            "c_family_not_reached_reason": c_not_reached_reason or None,
            "c_family_invoked": c_inv["family_invoked"],
            "c_families_invoked": c_inv["families_invoked"],
            "c_family_correct": correct if c_inv["family_invoked"] else None,
            "c_registry_statuses": {fam: registry_status.get(fam, "unknown") for fam in c_inv["families_invoked"]},
            "c_template_used": c_inv["template_used"],
            "c_template_ids": c_inv["template_ids"],
            "winner_positive_arms": [arm for arm, rec in arms.items() if _positive(rec)],
            "attempts": {arm: _attempt_summary(arms.get(arm)) for arm in ARMS},
        }
        if complete:
            paired_rows.append(row)
        elif arms:
            partial_rows.append(row)

    by_arm = defaultdict(Counter)
    for rec in records:
        by_arm[str(rec.get("arm") or "")][str(rec.get("learning_exit") or "")] += 1
    summary = {
        "schema": "leanmill-benchmark-slice-analysis-v1",
        "checkpoint": args.checkpoint,
        "run_id": args.run_id,
        "record_count": len(records),
        "touched_row_count": len(by_row),
        "paired_row_count": len(paired_rows),
        "partial_row_count": len(partial_rows),
        "by_arm": {arm: dict(counter) for arm, counter in sorted(by_arm.items())},
        "target_aware_family_template_filter": {
            "target_context_row_count": len(target_names_by_row),
            "target_reference_quarantine_count": _target_reference_quarantine_count(raw_specs, target_names_by_row),
            "family_template_row_count": len(template_rows),
            "rationale": "slice analysis labels family-memory eligibility with the same row-target quarantine used by runner candidate generation",
        },
        "bucket_counts": dict(bucket_counts),
        "by_bucket_arm_exit": {bucket: dict(counter) for bucket, counter in sorted(by_bucket_arm.items())},
        "family_slice": {
            "paired_family_eligible_rows": c_eligible_rows,
            "paired_c_family_available_rows": c_family_available_rows,
            "paired_c_family_invoked_rows": c_invoked_rows,
            "paired_c_family_starved_tool_positive_rows": c_family_starved_tool_positive_rows,
            "paired_c_family_not_reached_reasons": dict(c_not_reached_reasons),
            "paired_c_family_wrong_rows": c_wrong_family,
            "paired_c_family_eligible_positive_rows": c_eligible_positive,
            "paired_static_fail_c_positive_rows": c_static_fail_c_positive,
            "paired_c_over_prune_rows": c_over_prune,
            "c_discriminating": c_invoked_rows > 0,
        },
        "safety": {
            "target_kind_audit_count": sum(1 for r in records if r.get("target_kind_audit")),
            "failed_negative_control_count": sum(1 for r in records if r.get("learning_exit") == "failed_negative_control"),
            "harness_candidate_build_failure_record_count": sum(1 for r in records if r.get("learning_exit") == "harness_candidate_build_failure"),
            "harness_no_candidates_record_count": sum(1 for r in records if r.get("learning_exit") == "harness_no_candidates"),
            "candidate_build_failure_attempt_count": sum(
                1
                for r in records
                for a in r.get("attempts", [])
                if isinstance(a.get("build"), dict) and a["build"].get("status") != "pass"
            ),
            "missing_toolchain_attempt_count": sum(1 for r in records for a in r.get("attempts", []) if "no default toolchain" in str(a.get("stderr_tail") or "")),
            "missing_executable_attempt_count": sum(1 for r in records for a in r.get("attempts", []) if "missing executable" in str(a.get("stderr_tail") or "")),
            "inline_template_prefix_artifact_count": sum(1 for r in records for a in r.get("attempts", []) if _artifact_has_inline_template_prefix(a)),
        },
        "exact_gap_or_falsifier_row_count": exact_gap_or_falsifier,
        "paired_rows": paired_rows,
        "partial_rows": partial_rows,
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    if args.md:
        _write_md(args.md, summary)
    return summary


def _write_md(path: str | Path, summary: dict[str, Any]) -> None:
    lines = [
        "# LeanMill Benchmark Slice Analysis",
        "",
        f"- records: `{summary['record_count']}`",
        f"- paired rows: `{summary['paired_row_count']}`",
        f"- partial rows: `{summary['partial_row_count']}`",
        f"- bucket counts: `{summary['bucket_counts']}`",
        f"- family slice: `{summary['family_slice']}`",
        f"- safety: `{summary['safety']}`",
        "",
        "## Paired Rows",
        "",
        "| row | bucket | static | governed | adaptive | C | eligible | C available | C invoked | C not reached | C correct | C families | attempts public/governed/adaptive/C |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|---|",
    ]
    for row in summary["paired_rows"]:
        attempts = row["attempts"]
        attempt_str = "/".join(str(attempts[a].get("attempt_count", "")) for a in ARMS)
        lines.append(
            "| " + " | ".join([
                str(row["row_id"]),
                str(row["bucket"]),
                str(row["static_closed"]),
                str(row["governed_static_closed"]),
                str(row["adaptive_execution_closed"]),
                str(row["adaptive_residual_closed"]),
                str(row["family_eligible"]),
                str(row["c_family_available"]),
                str(row["c_family_invoked"]),
                str(row["c_family_not_reached_reason"] or ""),
                str(row["c_family_correct"]),
                ",".join(row["c_families_invoked"]),
                attempt_str,
            ]) + " |"
        )
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n")


def _self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="leanmill_benchmark_slice_") as td:
        root = Path(td)
        spec = root / "specs"
        spec.mkdir()
        (spec / "fam.yaml").write_text("""
family: fam
status: candidate_family
residual_match:
  row_ids: [r1]
templates:
  - id: fam_pos
    row_id: r1
    test_kind: positive
    timeout: 30
    body_lines: [trivial]
  - id: fam_neg
    row_id: r1
    test_kind: negative_control
    timeout: 30
    body_lines: [exact False.elim]
  - id: fam_pos_r3
    row_id: r3
    test_kind: positive
    timeout: 30
    body_lines: [trivial]
""")
        (spec / "leaky.yaml").write_text("""
family: leaky
status: candidate_family
residual_match:
  row_ids: [design]
templates:
  - id: leaky_pos
    row_id: design
    test_kind: positive
    timeout: 30
    body_lines: [exact design]
  - id: leaky_neg
    row_id: design
    test_kind: negative_control
    timeout: 30
    body_lines: [trivial]
""")
        ck = root / "run.jsonl"
        for arm, exit_kind in [
            ("public_tool_static", "tested_no_positive_signal"),
            ("governed_public_tool_static", "tested_no_positive_signal"),
            ("governed_adaptive_execution", "tested_no_positive_signal"),
            ("governed_adaptive_residual_curriculum", "ratified_closure"),
        ]:
            rec = {"run_id": "x", "row_id": "r1", "arm": arm, "learning_exit": exit_kind, "attempt_count": 1, "attempts": []}
            if arm.endswith("residual_curriculum"):
                rec["attempts"] = [{"candidate_kind": "repair_family_template", "family": "fam", "candidate_id": "fam_pos"}]
            ck.write_text((ck.read_text() if ck.exists() else "") + json.dumps(rec) + "\n")
        prep = root / "prep.json"
        for arm in [
            "public_tool_static",
            "governed_public_tool_static",
            "governed_adaptive_execution",
            "governed_adaptive_residual_curriculum",
        ]:
            rec = {"run_id": "x", "row_id": "r3", "arm": arm, "learning_exit": "governed_tool_tactic_closure_candidate", "attempt_count": 1, "attempts": []}
            if arm.endswith("residual_curriculum"):
                rec.update({
                    "family_candidate_count": 1,
                    "family_reached": False,
                    "family_not_reached_reason": "tool_positive_before_family",
                })
            ck.write_text(ck.read_text() + json.dumps(rec) + "\n")
        prep = root / "prep.json"
        row_context = root / "row_context.json"
        row_context.write_text(json.dumps({"rows": [{"row_id": "design", "target_theorem_name": "design"}]}) + "\n")
        prep.write_text(json.dumps({"selected_rows_order": ["r1", "r3"], "row_context": str(row_context)}) + "\n")
        reg = root / "registry.json"
        reg.write_text(json.dumps({"families": [{"family": "fam", "status": "candidate_family"}]}) + "\n")
        ck.write_text(ck.read_text() + json.dumps({
            "run_id": "x",
            "row_id": "r2",
            "arm": "public_tool_static",
            "learning_exit": "harness_candidate_build_failure",
            "attempts": [{"build": {"status": "fail", "reason": "target_theorem_not_found"}}],
        }) + "\n")
        obj = analyze(argparse.Namespace(checkpoint=str(ck), prep=str(prep), registry=str(reg), spec_dir=str(spec), run_id="x", out=None, md=None))
        assert obj["paired_row_count"] == 2, obj
        assert obj["family_slice"]["paired_c_family_invoked_rows"] == 1, obj
        assert obj["family_slice"]["paired_c_family_starved_tool_positive_rows"] == 1, obj
        assert obj["family_slice"]["paired_c_family_not_reached_reasons"]["tool_positive_before_family"] == 1, obj
        assert obj["family_slice"]["c_discriminating"] is True, obj
        assert obj["paired_rows"][0]["c_family_correct"] is True, obj
        assert obj["target_aware_family_template_filter"]["target_reference_quarantine_count"] == 1, obj
        assert obj["safety"]["harness_candidate_build_failure_record_count"] == 1, obj
        assert obj["safety"]["candidate_build_failure_attempt_count"] == 1, obj
    print("leanmill_benchmark_slice_analyzer self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", default=DEFAULT_CHECKPOINT)
    ap.add_argument("--prep", default=DEFAULT_PREP)
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    ap.add_argument("--spec-dir", default=DEFAULT_SPEC_DIR)
    ap.add_argument("--run-id", default="")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--md", default=DEFAULT_MD)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    result = analyze(args)
    print(json.dumps({
        "out": args.out,
        "md": args.md,
        "record_count": result["record_count"],
        "paired_row_count": result["paired_row_count"],
        "bucket_counts": result["bucket_counts"],
        "family_slice": result["family_slice"],
        "safety": result["safety"],
        "by_arm": result["by_arm"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
