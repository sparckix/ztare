#!/usr/bin/env python3
"""Validate LeanMill repair-family specs before canary drains."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import leanmill_family_specs as family_specs
from leanmill_paths import DATA_DIR, REPAIR_FAMILY_REGISTRY as DEFAULT_REGISTRY


DEFAULT_ROW_CONTEXTS = [
    f"{DATA_DIR}/c_supply_batch_cleaned_row_context.json",
    f"{DATA_DIR}/c_supply_batch_row_context.json",
    f"{DATA_DIR}/c_supply_batch_cleaned_c_discriminating_row_context.json",
    f"{DATA_DIR}/c_supply_batch_c_discriminating_row_context.json",
]


def _read_json(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}


def _row_contexts(args: argparse.Namespace) -> list[str]:
    supplied = [str(x) for x in (getattr(args, "row_context", None) or []) if str(x)]
    return supplied or DEFAULT_ROW_CONTEXTS


def build(args: argparse.Namespace) -> dict:
    specs = family_specs.load_specs(args.spec_dir)
    registry = _read_json(args.registry)
    row_contexts = _row_contexts(args)
    target_names_by_row = family_specs.target_names_by_row_from_context_paths(row_contexts)
    failures = family_specs.validate_specs(specs, registry, target_names_by_row=target_names_by_row)
    blocking = [f for f in failures if family_specs.failure_is_blocking(f)]
    quarantined = [f for f in failures if not family_specs.failure_is_blocking(f)]
    payload = {
        **family_specs.specs_summary(specs),
        "schema": "leanmill-family-spec-gate-v1",
        "spec_dir": args.spec_dir,
        "registry": args.registry,
        "row_contexts": row_contexts,
        "target_context_row_count": len(target_names_by_row),
        "usable": family_specs.specs_summary(family_specs.usable_specs(specs, target_names_by_row=target_names_by_row)),
        "supply_quality": family_specs.family_supply_quality(specs, target_names_by_row=target_names_by_row),
        "supply_quality_summary": family_specs.supply_quality_summary(specs, target_names_by_row=target_names_by_row),
        "overclaim_disqualification_summary": family_specs.overclaim_disqualification_summary(specs),
        "overclaim_disqualification_findings": family_specs.overclaim_disqualification_findings(specs),
        "failure_count": len(failures),
        "blocking_failure_count": len(blocking),
        "quarantine_failure_count": len(quarantined),
        "failures": failures,
        "status": "pass" if not blocking else "fail",
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    payload = build(argparse.Namespace(
        spec_dir=family_specs.DEFAULT_SPEC_DIR,
        registry="/tmp/no_such_registry.json",
        row_context=[],
        out=None,
    ))
    assert "status" in payload
    advisory = family_specs.validate_specs([
        {
            "_path": "candidate.yaml",
            "family": "missing_candidate",
            "version": 1,
            "status": "candidate_family",
            "credit": {"source_credit_eligible": False, "clean_solver_credit_eligible": False},
            "templates": [
                {"id": "p", "row_id": "R", "test_kind": "positive", "timeout": 10, "body": "exact h"},
                {"id": "n", "row_id": "R", "test_kind": "negative_control", "timeout": 10, "body": "exact bad"},
            ],
        }
    ], {"families": [{"family": "unrelated_family", "unique_ratified_rows": 99, "negative_controls_expected_fail": 99}]})
    assert advisory and advisory[0]["failure"] == "candidate_status_registry_family_absent"
    assert not family_specs.failure_is_blocking(advisory[0])
    self_ref = family_specs.validate_specs([
        {
            "_path": "selfref.yaml",
            "family": "self_ref",
            "version": 1,
            "status": "seed_only",
            "credit": {"source_credit_eligible": False, "clean_solver_credit_eligible": False},
            "templates": [
                {"id": "p", "row_id": "R", "test_kind": "positive", "timeout": 10, "body": "exact gold_target"},
                {"id": "n", "row_id": "R", "test_kind": "negative_control", "timeout": 10, "body": "exact bad"},
            ],
        }
    ], target_names_by_row={"R": ["gold_target"]})
    assert any(f["failure"] == "positive_template_references_target_theorem" and not family_specs.failure_is_blocking(f) for f in self_ref), self_ref
    assert family_specs.specs_summary(family_specs.usable_specs([
        {
            "_path": "selfref.yaml",
            "family": "self_ref",
            "version": 1,
            "status": "seed_only",
            "credit": {"source_credit_eligible": False, "clean_solver_credit_eligible": False},
            "templates": [
                {"id": "p", "row_id": "R", "test_kind": "positive", "timeout": 10, "body": "exact gold_target"},
                {"id": "n", "row_id": "R", "test_kind": "negative_control", "timeout": 10, "body": "exact bad"},
            ],
        }
    ], target_names_by_row={"R": ["gold_target"]}))["row_template_count"] == 0
    overclaim = family_specs.overclaim_disqualification_summary([
        {
            "_path": "overclaim.yaml",
            "family": "overclaim",
            "version": 1,
            "status": "seed_only",
            "credit": {"source_credit_eligible": False, "clean_solver_credit_eligible": False},
            "residual_match": {"head_patterns": ["Finset.le_sum_condensed"]},
            "templates": [
                {"id": "p", "row_id": "R", "test_kind": "positive", "timeout": 10, "body": "simpa using Finset.le_sum_condensed hf n"},
                {"id": "n", "row_id": "R", "test_kind": "negative_control", "timeout": 10, "body": "exact bad"},
            ],
        }
    ])
    assert overclaim["finding_count"] >= 1 and overclaim["by_family"].get("overclaim") == 1, overclaim
    explicit_bad = family_specs.validate_specs([
        {
            "_path": "candidate.yaml",
            "family": "weak_candidate",
            "version": 1,
            "status": "candidate_family",
            "credit": {"source_credit_eligible": False, "clean_solver_credit_eligible": False},
            "templates": [
                {"id": "p", "row_id": "R", "test_kind": "positive", "timeout": 10, "body": "exact h"},
                {"id": "n", "row_id": "R", "test_kind": "negative_control", "timeout": 10, "body": "exact bad"},
            ],
        }
    ], {"families": [{"family": "weak_candidate", "unique_ratified_rows": 1, "negative_controls_expected_fail": 0}]})
    assert any(f["failure"] == "candidate_status_without_registry_evidence" and family_specs.failure_is_blocking(f) for f in explicit_bad)
    print("leanmill_family_spec_gate self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec-dir", default=family_specs.DEFAULT_SPEC_DIR)
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    ap.add_argument("--row-context", action="append", default=[], help="row context JSON; defaults to current C-supply contexts")
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    payload = build(args)
    print(json.dumps({
        "status": payload["status"],
        "spec_count": payload["spec_count"],
        "row_template_count": payload["row_template_count"],
        "failure_count": payload["failure_count"],
        "blocking_failure_count": payload["blocking_failure_count"],
        "quarantine_failure_count": payload["quarantine_failure_count"],
        "target_context_row_count": payload.get("target_context_row_count", 0),
        "usable_row_template_count": payload["usable"]["row_template_count"],
        "overclaim_disqualification_summary": payload.get("overclaim_disqualification_summary", {}),
        "supply_quality": payload.get("supply_quality_summary", {}),
        "out": args.out,
    }, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
