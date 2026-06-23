#!/usr/bin/env python3
"""Offline first-run demo for ZTARE.

A new reader should see useful behavior in one screen:

* a ready project-intake file validates before in-loop routing;
* malformed intake is blocked before the loop;
* an overbroad claim is demoted to bounded wording with missing evidence and a
  next falsifier.

The demo is model-free and writes no persistent runtime state.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from ztare.scaffold.substrate_queue import (  # noqa: E402
    validate_project_packet_falsifier,
    validate_project_packet_path,
)


def _load_claim_discipline_demo():
    path = REPO / "scripts/public/control/claim_discipline_demo.py"
    spec = importlib.util.spec_from_file_location("claim_discipline_demo", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_demo_payload = _load_claim_discipline_demo().build_demo_payload


def _print_list(title: str, values: list[str]) -> None:
    print(title)
    for value in values:
        print(f"  - {value}")


def _intake_result(path: Path) -> dict[str, Any]:
    result = validate_project_packet_path(path)
    return {
        "path": str(path.relative_to(REPO)),
        "ok": result["ok"],
        "packet_id": result.get("packet_id"),
        "project": result.get("project"),
        "rubric": result.get("rubric"),
        "errors": result.get("errors", []),
        "warnings": result.get("warnings", []),
        "source_preflight": result.get("source_preflight") or {},
    }


def _intake_falsifier_result(path: Path, remove_ref: str) -> dict[str, Any]:
    result = validate_project_packet_falsifier(path, remove_ref=remove_ref)
    return {
        "path": str(path.relative_to(REPO)),
        "ok": result["ok"],
        "remove_ref": result["remove_ref"],
        "removed_ref": result.get("removed_ref"),
        "baseline_ok": result["baseline"]["ok"],
        "falsified_ok": result["falsified"]["ok"],
        "errors": result.get("errors", []),
        "falsified_errors": result["falsified"].get("errors", []),
        "path_safety": result.get("path_safety") or {},
    }


def _print_intake_result(title: str, result: dict[str, Any]) -> None:
    status = "accepted" if result["ok"] else "blocked"
    print(f"{title}: {status}")
    print(f"  intake: {result['path']}")
    print(f"  project/rubric: {result['project']} / {result['rubric']}")
    source_preflight = result.get("source_preflight") or {}
    if source_preflight.get("checked"):
        print(
            "  source-preflight: "
            f"{source_preflight.get('status')} "
            f"({source_preflight.get('source_evidence_count', 0)} source evidence, "
            f"{source_preflight.get('untyped_source_count', 0)} untyped)"
        )
    if result["errors"]:
        _print_list("  Why it stopped:", result["errors"])
    if result["warnings"]:
        _print_list("  Warnings:", result["warnings"])


def _print_intake_falsifier_result(title: str, result: dict[str, Any]) -> None:
    status = "passed" if result["ok"] else "failed"
    print(f"{title}: {status}")
    print(f"  intake: {result['path']}")
    print(f"  removed ref selector: {result['remove_ref']}")
    print(f"  removed ref: {result.get('removed_ref')}")
    if result["errors"]:
        _print_list("  Falsifier errors:", result["errors"])
    if result["falsified_errors"]:
        _print_list("  Expected missing-ref failure:", result["falsified_errors"])


DISPLAY_BOUNDARY = (
    "This offline demo shows the review boundary before a model spends tokens: "
    "complete project intake is accepted for review, malformed intake stops "
    "early, and broad claims are reduced to what the attached evidence can "
    "support."
)

DISPLAY_MISSING_EVIDENCE = [
    "a named external baseline or comparison set",
    "a pre-registered metric and pass/fail threshold",
    "the evidence artifacts that would support the stronger wording",
    "a binary falsifier that would demote the bounded claim",
]

DISPLAY_NON_CLAIMS = [
    "not proof that the demo claim is true",
    "not a model-performance comparison",
    "not an autoresearch run",
    "not a replacement for external replication",
]

DISPLAY_NEXT_FALSIFIER = (
    "Run the same bounded claim against a named external baseline with a "
    "pre-registered metric; demote the claim if the baseline wins, the metric "
    "is missing, or the evidence artifacts cannot be reproduced."
)


def _build_machine_summary(
    *,
    payload: dict[str, Any],
    ready_intake: dict[str, Any],
    ready_intake_falsifier: dict[str, Any],
    malformed_intake: dict[str, Any],
    blocked_sources: list[str],
    failed_checks: list[str],
    include_compat: bool = False,
) -> dict[str, Any]:
    decision = payload["decision"]
    summary: dict[str, Any] = {
        "ok": payload["ok"],
        "demo": "hello_value_demo",
        "verdict": decision["verdict"],
        "claim_allowed": decision["claim_allowed"],
        "ready_intake_ok": ready_intake["ok"],
        "ready_intake_source_preflight_ok": bool(
            ready_intake.get("source_preflight", {}).get("ok")
        ),
        "ready_intake_source_evidence_count": int(
            ready_intake.get("source_preflight", {}).get(
                "source_evidence_count", 0
            )
        ),
        "ready_intake_falsifier_ok": ready_intake_falsifier["ok"],
        "ready_intake_falsifier_removed_ref": ready_intake_falsifier.get(
            "removed_ref"
        ),
        "malformed_intake_ok": malformed_intake["ok"],
        "blocked_source_count": len(blocked_sources),
        "failed_check_count": len(failed_checks),
        "writes_persistent_runtime_state": payload[
            "writes_persistent_runtime_state"
        ],
    }
    if include_compat:
        summary.update(
            {
                "ready_intake_falsifier_path_safety": ready_intake_falsifier.get(
                    "path_safety"
                ),
                "ready_packet_ok": ready_intake["ok"],
                "ready_packet_source_preflight_ok": bool(
                    ready_intake.get("source_preflight", {}).get("ok")
                ),
                "ready_packet_source_evidence_count": int(
                    ready_intake.get("source_preflight", {}).get(
                        "source_evidence_count", 0
                    )
                ),
                "ready_packet_falsifier_ok": ready_intake_falsifier["ok"],
                "ready_packet_falsifier_removed_ref": ready_intake_falsifier.get(
                    "removed_ref"
                ),
                "ready_packet_falsifier_path_safety": ready_intake_falsifier.get(
                    "path_safety"
                ),
                "malformed_packet_ok": malformed_intake["ok"],
            }
        )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the offline first-value ZTARE demo."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "print only the full machine summary, including legacy compatibility "
            "fields used by older telemetry"
        ),
    )
    args = parser.parse_args([] if argv is None else argv)

    payload: dict[str, Any] = build_demo_payload()
    decision = payload["decision"]
    ready_intake = _intake_result(
        REPO / "examples/project_packets/ready_demo_claims_intake.json"
    )
    ready_intake_falsifier = _intake_falsifier_result(
        REPO / "examples/project_packets/ready_demo_claims_intake.json",
        "evidence_refs[1]",
    )
    malformed_intake = _intake_result(
        REPO / "examples/project_packets/malformed_missing_evidence_intake.json"
    )
    blocked_sources = [
        row["source_id"]
        for row in payload["source_readiness"]["rows"]
        if row["readiness"] == "blocked"
    ]
    failed_checks = [
        check["check"]
        for check in payload["claim_discipline_checks"]
        if not check["passes"]
    ]
    summary = _build_machine_summary(
        payload=payload,
        ready_intake=ready_intake,
        ready_intake_falsifier=ready_intake_falsifier,
        malformed_intake=malformed_intake,
        blocked_sources=blocked_sources,
        failed_checks=failed_checks,
        include_compat=args.json,
    )

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return (
            0
            if payload["ok"]
            and ready_intake["ok"]
            and ready_intake_falsifier["ok"]
            and not malformed_intake["ok"]
            and not decision["claim_allowed"]
            else 1
        )

    print("ZTARE hello: offline claim review in one run")
    print()
    print("1. Project intake boundary")
    _print_intake_result("Ready intake", ready_intake)
    _print_intake_falsifier_result(
        "Ready intake missing-ref falsifier",
        ready_intake_falsifier,
    )
    print()
    _print_intake_result("Malformed intake", malformed_intake)
    print()
    print("2. Public-claim review")
    print("  Input: a plausible agent/research claim asks for public promotion.")
    print(f"  Verdict: {decision['verdict']}")
    print(f"  Claim allowed: {decision['claim_allowed']}")
    print()
    print("  What a reviewer can say:")
    print(f"  {DISPLAY_BOUNDARY}")
    print()
    _print_list("Missing evidence:", DISPLAY_MISSING_EVIDENCE)
    print()
    _print_list("Non-claims:", DISPLAY_NON_CLAIMS)
    print()
    print("Next falsifier:")
    print(f"  {DISPLAY_NEXT_FALSIFIER}")
    print()
    print("Next runnable project:")
    print("  ztare project walkthrough --ops-demo")
    print(
        "  ztare autoresearch trace --project ops_root_cause_diagnosis_demo "
        "--rubric ops_root_cause_diagnosis_demo "
        "--intake projects/ops_root_cause_diagnosis_demo/"
        "ops_root_cause_diagnosis_demo_intake.json --brief"
    )
    print()
    print("Machine summary for CI/review:")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return (
        0
        if payload["ok"]
        and ready_intake["ok"]
        and ready_intake_falsifier["ok"]
        and not malformed_intake["ok"]
        and not decision["claim_allowed"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
