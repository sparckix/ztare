#!/usr/bin/env python3
"""Admit one ratified external-science result into a frozen LeanMill attempt."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ztare.leanmill.frontier_campaign_runner import (
    run_external_science_recovery_admission,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt-dir", required=True)
    parser.add_argument("--source-file", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--finite-witness-model-id", required=True)
    parser.add_argument("--literature-audit", required=True)
    parser.add_argument("--lineage-id", required=True)
    parser.add_argument("--submitted-by", default="external-science-recovery")
    parser.add_argument(
        "--closure-ledger",
        default="analytics/public/queries/adhoc_closure_certificates.jsonl",
    )
    parser.add_argument(
        "--kernel-parity-ledger",
        default="analytics/public/queries/kernel_parity.jsonl",
    )
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument(
        "--reasoning-effort",
        choices=("low", "medium", "high", "ultra"),
        default="medium",
    )
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    result = run_external_science_recovery_admission(
        args.attempt_dir,
        source_path=args.source_file,
        theorem_target=args.target,
        finite_witness_model_id=args.finite_witness_model_id,
        literature_audit_path=args.literature_audit,
        lineage_id=args.lineage_id,
        submitted_by=args.submitted_by,
        closure_ledger_path=args.closure_ledger,
        kernel_parity_ledger_path=args.kernel_parity_ledger,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        repo=Path(args.repo_root).resolve(),
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
