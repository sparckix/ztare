#!/usr/bin/env python3
"""Executable governance sentinels for the LeanMill evaluation harness.

This is a small adversarial suite, not a benchmark arm. It checks that the
harness can observe the governance behaviors the prereg benchmark relies on:
valid repair-template ratification, negative-control rejection, tool-only
closure labeling, wrong-target credit blocking, and harness build failures.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

import leanmill_evaluation_harness_runner as harness
import leanmill_governance_worker as governance_worker


class _Args:
    residual_fallback_family_call_budget = 1
    per_candidate_timeout_s = 10


def _source(root: Path) -> Path:
    path = root / "Sentinel.lean"
    path.write_text(
        "theorem sentinel_demo : True := by\n"
        "  trivial\n\n"
        "theorem after : True := by\n"
        "  trivial\n"
    )
    return path


def _run_case(root: Path, *, name: str, row: dict[str, Any], arm: dict[str, Any], specs: list[dict[str, Any]], max_calls: int = 2) -> dict[str, Any]:
    rec = harness._run_row_arm(
        _Args(),
        row=row,
        arm=arm,
        specs=specs,
        max_calls=max_calls,
        run_root=root / name,
        wall_timeout_s=20,
    )
    return {
        "case": name,
        "learning_exit": rec.get("learning_exit"),
        "closed": rec.get("closed"),
        "family_candidate_count": rec.get("family_candidate_count"),
        "family_reached": rec.get("family_reached"),
        "family_not_reached_reason": rec.get("family_not_reached_reason"),
        "target_kind_audit": rec.get("target_kind_audit"),
        "attempt_count": rec.get("attempt_count"),
        "build_failure_count": rec.get("build_failure_count"),
        "lean_attempt_count": rec.get("lean_attempt_count"),
    }



def _governance_worker_case(root: Path) -> dict[str, Any]:
    artifact = root / "SmuggledSorry.lean"
    artifact.write_text("theorem smuggled_sorry : True := by\n  sorry\n")
    candidate = root / "smuggled_sorry_candidate.json"
    candidate.write_text(json.dumps({
        "candidate_kind": "closure",
        "target_kind": "repair_canary",
        "expected_outcome": "closure",
        "artifact_paths": [str(artifact)],
    }, sort_keys=True) + "\n")
    validation = governance_worker._validate_candidate(str(candidate))
    return {
        "case": "smuggled_sorry_governance_rejects",
        "learning_exit": "governance_rejected" if validation.get("status") == "fail" else "governance_shape_checked",
        "candidate_validation": validation,
        "forbidden_token_rejected": any(
            f.get("failure") == "artifact_contains_forbidden_proof_token"
            for f in validation.get("failures") or []
        ),
    }


def _governance_gap_case(root: Path) -> dict[str, Any]:
    artifact = root / "vague_gap.json"
    artifact.write_text(json.dumps({"schema": "sentinel", "decision": "exact_gap_candidate"}) + "\n")
    candidate = root / "vague_gap_candidate.json"
    candidate.write_text(json.dumps({
        "candidate_kind": "exact_gap",
        "target_kind": "post_probe_next_artifact",
        "expected_outcome": "exact_gap",
        "artifact_paths": [str(artifact)],
    }, sort_keys=True) + "\n")
    validation = governance_worker._validate_candidate(str(candidate))
    return {
        "case": "vague_gap_governance_rejects",
        "learning_exit": "governance_rejected" if validation.get("status") == "fail" else "governance_shape_checked",
        "candidate_validation": validation,
        "gap_evidence_rejected": any(
            f.get("failure") in {"missing_gap_or_falsifier_statement", "missing_gap_or_falsifier_evidence"}
            for f in validation.get("failures") or []
        ),
    }

def run_suite() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="leanmill_governance_sentinels_") as td:
        root = Path(td)
        source = _source(root)
        row = {"row_id": "sentinel_row", "goal": "theorem sentinel_demo : True := by", "source_file": str(source), "target_kind": "closure"}
        repair_arm = {"arm": "governed_adaptive_residual_curriculum", "uses_governance_gate": True, "uses_residual_memory": True, "route": []}
        tool_arm = {"arm": "governed_public_tool_static", "uses_governance_gate": True, "route": [{"tool_id": "trivial", "tactic": "trivial"}]}
        good_spec = [{"family": "sentinel_family", "templates": [
            {"id": "sentinel_pos", "row_id": "sentinel_row", "test_kind": "positive", "body_lines": ["trivial"]},
            {"id": "sentinel_neg_expected_fail", "row_id": "sentinel_row", "test_kind": "negative_control", "body_lines": ["exact False.elim"]},
        ]}]
        bad_negative_spec = [{"family": "sentinel_family", "templates": [
            {"id": "sentinel_pos", "row_id": "sentinel_row", "test_kind": "positive", "body_lines": ["trivial"]},
            {"id": "sentinel_neg_unexpected_pass", "row_id": "sentinel_row", "test_kind": "negative_control", "body_lines": ["trivial"]},
        ]}]
        cases = [
            _run_case(root, name="valid_repair_template", row=row, arm=repair_arm, specs=good_spec),
            _run_case(root, name="negative_control_false_positive", row=row, arm=repair_arm, specs=bad_negative_spec),
            _run_case(root, name="governed_tool_closure", row=row, arm=tool_arm, specs=[]),
            _run_case(root, name="wrong_target_kind_block", row={**row, "target_kind": "exact_gap"}, arm=tool_arm, specs=[]),
            _run_case(root, name="missing_source_build_failure", row={"row_id": "missing", "source_file": str(root / "missing.lean")}, arm=tool_arm, specs=[], max_calls=1),
            _governance_worker_case(root),
            _governance_gap_case(root),
        ]
    expected = {
        "valid_repair_template": "ratified_closure",
        "negative_control_false_positive": "failed_negative_control",
        "governed_tool_closure": "governed_tool_tactic_closure_candidate",
        "wrong_target_kind_block": "target_kind_audit_failure",
        "missing_source_build_failure": "harness_candidate_build_failure",
        "smuggled_sorry_governance_rejects": "governance_rejected",
        "vague_gap_governance_rejects": "governance_rejected",
    }
    failures = [case for case in cases if case.get("learning_exit") != expected.get(str(case.get("case")))]
    by_case = {str(case.get("case") or ""): case for case in cases}
    negative_control_case = by_case.get("negative_control_false_positive") or {}
    smuggled_case = by_case.get("smuggled_sorry_governance_rejects") or {}
    vague_gap_case = by_case.get("vague_gap_governance_rejects") or {}
    liveness = {
        "valid_repair_template_ratified": (by_case.get("valid_repair_template") or {}).get("learning_exit") == "ratified_closure",
        "negative_control_false_positive_blocked": negative_control_case.get("learning_exit") == "failed_negative_control",
        "smuggled_sorry_blocked": bool(smuggled_case.get("forbidden_token_rejected")),
        "vague_gap_blocked": bool(vague_gap_case.get("gap_evidence_rejected")),
    }
    return {
        "schema": "leanmill-governance-sentinel-suite-v2",
        "status": "pass" if not failures and all(liveness.values()) else "fail",
        "case_count": len(cases),
        "failures": failures,
        "liveness": liveness,
        "cases": cases,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    result = run_suite()
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
    if args.self_test and result["status"] != "pass":
        return 1
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
