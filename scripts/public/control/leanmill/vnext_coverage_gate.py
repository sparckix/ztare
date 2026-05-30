#!/usr/bin/env python3
"""Machine coverage gate for LeanMill vNext pull-forwards and 24x7 lanes."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]


REQUIREMENTS: list[dict[str, Any]] = [
    {
        "id": "work_queue",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/work_queue.py"],
        "self_test": ["scripts/public/control/leanmill/work_queue.py", "self-test"],
    },
    {
        "id": "event_ledger",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/work_queue.py"],
        "self_test": ["scripts/public/control/leanmill/work_queue.py", "self-test"],
    },
    {
        "id": "station_scheduler",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/station_scheduler.py"],
        "self_test": ["scripts/public/control/leanmill/station_scheduler.py", "--self-test"],
    },
    {
        "id": "learning_work_seeder",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/learning_work_seeder.py"],
        "self_test": ["scripts/public/control/leanmill/learning_work_seeder.py", "--self-test"],
    },
    {
        "id": "backlog_replenisher",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/backlog_replenisher.py"],
        "self_test": ["scripts/public/control/leanmill/backlog_replenisher.py", "--self-test"],
    },
    {
        "id": "safe_runner",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/24x7_runner.py"],
        "self_test": ["scripts/public/control/leanmill/24x7_runner.py", "--self-test"],
    },
    {
        "id": "local_watchdog",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/watchdog.py"],
        "self_test": ["scripts/public/control/leanmill/watchdog.py", "--self-test"],
    },
    {
        "id": "andon_cord",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/andon_cord.py"],
        "self_test": ["scripts/public/control/leanmill/andon_cord.py", "--self-test"],
    },
    {
        "id": "factory_policy_profile",
        "kind": "24x7",
        "artifacts": ["analytics/public/leanmill/dashboard_data/leanmill_factory_policy.json"],
    },
    {
        "id": "factory_policy_loader",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/factory_config.py"],
        "self_test": ["scripts/public/control/leanmill/factory_config.py", "--self-test"],
    },
    {
        "id": "factory_shutdown",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/shutdown.py"],
        "self_test": ["scripts/public/control/leanmill/shutdown.py", "--self-test"],
    },
    {
        "id": "source_worker",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/source_worker.py"],
        "self_test": ["scripts/public/control/leanmill/source_worker.py", "--self-test"],
    },
    {
        "id": "source_plan_worker",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/source_plan_worker.py"],
        "self_test": ["scripts/public/control/leanmill/source_plan_worker.py", "--self-test"],
    },
    {
        "id": "source_search_worker",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/source_search_worker.py"],
        "self_test": ["scripts/public/control/leanmill/source_search_worker.py", "--self-test"],
    },
    {
        "id": "corpus_expansion_from_files",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/corpus_expansion_from_files.py"],
        "self_test": ["scripts/public/control/leanmill/corpus_expansion_from_files.py", "--self-test"],
    },
    {
        "id": "external_source_scout_seeder",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/external_source_scout_seeder.py"],
        "self_test": ["scripts/public/control/leanmill/external_source_scout_seeder.py", "--self-test"],
    },
    {
        "id": "external_source_search_recovery",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/external_source_search_recovery.py"],
        "self_test": ["scripts/public/control/leanmill/external_source_search_recovery.py", "--self-test"],
    },
    {
        "id": "source_search_integrator",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/source_search_integrator.py"],
        "self_test": ["scripts/public/control/leanmill/source_search_integrator.py", "--self-test"],
    },
    {
        "id": "source_binding_ingester",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/source_binding_ingester.py"],
        "self_test": ["scripts/public/control/leanmill/source_binding_ingester.py", "--self-test"],
    },
    {
        "id": "canary_validator_worker",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/canary_validator_worker.py"],
        "self_test": ["scripts/public/control/leanmill/canary_validator_worker.py", "--self-test"],
    },
    {
        "id": "probe_worker",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/probe_worker.py"],
        "self_test": ["scripts/public/control/leanmill/probe_worker.py", "--self-test"],
    },
    {
        "id": "post_probe_triage",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/post_probe_triage.py"],
        "self_test": ["scripts/public/control/leanmill/post_probe_triage.py", "--self-test"],
    },
    {
        "id": "handoff_integrity_gate",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/handoff_integrity_gate.py"],
        "self_test": ["scripts/public/control/leanmill/handoff_integrity_gate.py", "--self-test"],
    },
    {
        "id": "retryable_failure_recovery",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/retryable_failure_recovery.py"],
        "self_test": ["scripts/public/control/leanmill/retryable_failure_recovery.py", "--self-test"],
    },
    {
        "id": "probe_credit_boundary",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/search/repair_canary_drain.py"],
        "self_test": ["scripts/public/control/leanmill/search/repair_canary_drain.py", "--self-test"],
    },
    {
        "id": "governance_worker",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/governance_worker.py"],
        "self_test": ["scripts/public/control/leanmill/governance_worker.py", "--self-test"],
    },
    {
        "id": "llm_proposal_worker",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/llm_proposal_worker.py", "scripts/public/control/leanmill/llm_proposal_gate.py"],
        "self_test": ["scripts/public/control/leanmill/llm_proposal_worker.py", "--self-test"],
    },
    {
        "id": "agent_repair_worker",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/agent_repair_worker.py", "src/ztare/common/subscription_agent_runtime.py"],
        "self_test": ["scripts/public/control/leanmill/agent_repair_worker.py", "--self-test"],
    },
    {
        "id": "leanmill_operator_contracts",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/operator_contracts.py"],
        "self_test": ["scripts/public/control/leanmill/operator_contracts.py", "--self-test"],
    },
    {
        "id": "c_supply_template_backfill",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/c_supply_template_backfill.py", "scripts/public/control/leanmill/operator_contracts.py"],
        "self_test": ["scripts/public/control/leanmill/c_supply_template_backfill.py", "--self-test"],
    },
    {
        "id": "c_supply_upstream_rater",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/c_supply_upstream_rater.py"],
        "self_test": ["scripts/public/control/leanmill/c_supply_upstream_rater.py", "--self-test"],
    },
    {
        "id": "agent_output_ingester",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/agent_output_ingester.py"],
        "self_test": ["scripts/public/control/leanmill/agent_output_ingester.py", "--self-test"],
    },
    {
        "id": "subscription_agent_runtime",
        "kind": "24x7",
        "artifacts": ["src/ztare/common/subscription_agent_runtime.py"],
        "self_test_module": ["-m", "src.ztare.common.subscription_agent_runtime", "--self-test"],
    },
    {
        "id": "station_health_dashboard",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/station_health_dashboard.py"],
        "self_test": ["scripts/public/control/leanmill/station_health_dashboard.py", "--self-test"],
    },
    {
        "id": "central_observability",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/observability.py"],
        "self_test": ["scripts/public/control/leanmill/observability.py", "--self-test"],
    },
    {
        "id": "infra_freeze_gate",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/infra_freeze_gate.py"],
        "self_test": ["scripts/public/control/leanmill/infra_freeze_gate.py", "--self-test"],
    },
    {
        "id": "dead_letter_triage",
        "kind": "24x7",
        "artifacts": ["scripts/public/control/leanmill/dead_letter_triage.py"],
        "self_test": ["scripts/public/control/leanmill/dead_letter_triage.py", "--self-test"],
    },
    {
        "id": "family_specs",
        "kind": "pull_forward",
        "artifacts": [
            "scripts/public/control/leanmill/family_specs.py",
            "analytics/public/leanmill/repair_families/asymptotics_bigo_eq_mul_planner.yaml",
            "analytics/public/leanmill/repair_families/ennreal_tsum_condensation_planner.yaml",
            "analytics/public/leanmill/repair_families/interval_alignment_planner.yaml",
        ],
    },
    {
        "id": "family_spec_gate",
        "kind": "pull_forward",
        "artifacts": ["scripts/public/control/leanmill/family_spec_gate.py"],
        "self_test": ["scripts/public/control/leanmill/family_spec_gate.py", "--self-test"],
    },
    {
        "id": "residual_lifecycle",
        "kind": "pull_forward",
        "artifacts": ["scripts/public/control/leanmill/residual_lifecycle.py"],
        "self_test": ["scripts/public/control/leanmill/residual_lifecycle.py", "--self-test"],
    },
    {
        "id": "family_metrics_registry",
        "kind": "pull_forward",
        "artifacts": ["scripts/public/control/leanmill/search/repair_family_registry.py", "scripts/public/control/leanmill/heldout_receipt_gate.py"],
        "self_test": ["scripts/public/control/leanmill/search/repair_family_registry.py", "--self-test"],
    },
    {
        "id": "heldout_independence_receipt",
        "kind": "pull_forward",
        "artifacts": ["scripts/public/control/leanmill/heldout_receipt_gate.py"],
        "self_test": ["scripts/public/control/leanmill/heldout_receipt_gate.py", "--self-test"],
    },
    {
        "id": "heldout_independence_scout",
        "kind": "pull_forward",
        "artifacts": ["scripts/public/control/leanmill/heldout_independence_scout.py"],
        "self_test": ["scripts/public/control/leanmill/heldout_independence_scout.py", "--self-test"],
    },
    {
        "id": "heldout_promotion_worker",
        "kind": "pull_forward",
        "artifacts": ["scripts/public/control/leanmill/heldout_promotion_worker.py"],
        "self_test": ["scripts/public/control/leanmill/heldout_promotion_worker.py", "--self-test"],
    },
    {
        "id": "station_action_contract",
        "kind": "pull_forward",
        "artifacts": ["scripts/public/control/leanmill/station_action_contract.py"],
        "self_test": ["scripts/public/control/leanmill/station_action_contract.py", "--self-test"],
    },
    {
        "id": "exact_gap_falsifier_path",
        "kind": "pull_forward",
        "artifacts": ["scripts/public/control/leanmill/governance_worker.py", "scripts/public/control/leanmill/llm_proposal_gate.py"],
        "self_test": ["scripts/public/control/leanmill/governance_worker.py", "--self-test"],
    },
    {
        "id": "source_family_allocator",
        "kind": "pull_forward",
        "artifacts": ["scripts/public/control/leanmill/source_family_allocator.py"],
        "self_test": ["scripts/public/control/leanmill/source_family_allocator.py", "--self-test"],
    },
    {
        "id": "evaluation_harness_contract",
        "kind": "pull_forward",
        "artifacts": ["scripts/public/control/leanmill/de_experiment_contract.py"],
        "self_test": ["scripts/public/control/leanmill/de_experiment_contract.py", "--self-test"],
    },
    {
        "id": "evaluation_harness_prep",
        "kind": "pull_forward",
        "artifacts": ["scripts/public/control/leanmill/benchmark_prep.py"],
        "self_test": ["scripts/public/control/leanmill/benchmark_prep.py", "--self-test"],
    },
    {
        "id": "regression_against_curated_cases",
        "kind": "pull_forward",
        "artifacts": ["scripts/public/control/leanmill/regression_gate.py"],
        "self_test": ["scripts/public/control/leanmill/regression_gate.py", "--self-test"],
    },
    {
        "id": "vnext_spec",
        "kind": "spec",
        "artifacts": [
            "research_areas/seams/engine/lean/GP-225_leanmill_vnext_station_factory_seam.md",
            "research_areas/specs/active/engine/lean/GP-225_leanmill_vnext_station_factory_spec.md",
        ],
    },
]


def _run_self_test(cmd: list[str]) -> dict[str, Any]:
    display_cmd = ["<python>", *cmd]
    try:
        proc = subprocess.run([sys.executable, *cmd], text=True, capture_output=True, cwd=REPO_ROOT, timeout=120)
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": display_cmd,
            "returncode": 124,
            "timed_out": True,
            "stdout_tail": (exc.stdout or "")[-1000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-1000:] if isinstance(exc.stderr, str) else "",
        }
    return {
        "cmd": display_cmd,
        "returncode": proc.returncode,
        "timed_out": False,
        "stdout_tail": proc.stdout[-1000:],
        "stderr_tail": proc.stderr[-1000:],
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    rows = []
    for req in REQUIREMENTS:
        if req.get("self_test") and req.get("self_test_module"):
            raise AssertionError(f"requirement has both self_test and self_test_module: {req['id']}")
        missing = [path for path in req["artifacts"] if not (REPO_ROOT / path).exists()]
        test_result = None
        if args.run_self_tests and not missing and req.get("self_test"):
            test_result = _run_self_test(list(req["self_test"]))
        if args.run_self_tests and not missing and req.get("self_test_module"):
            test_result = _run_self_test(list(req["self_test_module"]))
        ok = not missing and (test_result is None or test_result["returncode"] == 0)
        rows.append({
            "id": req["id"],
            "kind": req["kind"],
            "status": "pass" if ok else "fail",
            "missing": missing,
            "self_test": test_result,
        })
    passed = sum(1 for row in rows if row["status"] == "pass")
    payload = {
        "schema": "leanmill-vnext-coverage-gate-v1",
        "requirement_count": len(rows),
        "passed": passed,
        "failed": len(rows) - passed,
        "coverage_percent": round((passed / len(rows)) * 100, 3) if rows else 100.0,
        "status": "pass" if passed == len(rows) else "fail",
        "self_tests_executed": bool(args.run_self_tests),
        "requirements": rows,
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    payload = build(argparse.Namespace(run_self_tests=False, out=None))
    assert payload["requirement_count"] >= 20
    assert payload["self_tests_executed"] is False
    print("leanmill_vnext_coverage_gate self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-self-tests", action="store_true")
    ap.add_argument("--out", default="analytics/public/leanmill/dashboard_data/vnext_coverage_gate.json")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    payload = build(args)
    print(json.dumps({
        "status": payload["status"],
        "coverage_percent": payload["coverage_percent"],
        "passed": payload["passed"],
        "failed": payload["failed"],
        "out": args.out,
    }, sort_keys=True))
    return 0 if payload["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
