#!/usr/bin/env python3
"""Enqueue a single NS Lean lemma into the LeanMill work queue.

Bridges the gap surfaced by audit #79 + #80: LeanMill has 0 NS attempts in
its event log because no caller has been seeding NS work items. This script
is the minimal-scope "fire one NS work item" bridge.

Usage:
  python3 scripts/public/control/leanmill/enqueue_ns_lemma.py \\
      --target SomeNSLemmaName \\
      --source-file ztare_proofs/ZtareProofs/ns_route1_some_file.lean \\
      --kind subscription_agent_task \\
      [--rationale-hint "<short context>"] [--expected-difficulty easy|medium|hard] \\
      [--dry-run]

Validates against the ns_corpus contract before enqueueing. Default --dry-run
prints the normalized item without touching the work queue (safe to use in
this session). Pass --commit to actually enqueue (will perturb LeanMill
operational state).
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from ztare.leanmill.contracts.ns_corpus import (  # noqa: E402
    SCHEMA, validate_work_item, build_ns_lane_floor,
)
from ztare.leanmill.policy import FACTORY_POLICY as DEFAULT_FACTORY_POLICY, priority_value  # noqa: E402


def _resolve_repo_path(rel_path: str) -> Path:
    path = (REPO / rel_path).resolve()
    if not path.is_relative_to(REPO):
        raise ValueError(f"path escapes repo: {rel_path}")
    return path


def _decl_exists(source_file: str, target: str) -> tuple[bool, str]:
    path = _resolve_repo_path(source_file)
    if not path.exists():
        return False, f"source file does not exist: {source_file}"
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(rf"^\s*(?:def|theorem|lemma|axiom)\s+{re.escape(target)}\b", re.MULTILINE)
    if not pattern.search(text):
        return False, f"target declaration not found in source file: {target}"
    return True, "ok"


def _build_worker_payload(normalized: dict[str, object]) -> dict[str, object]:
    work_id = f"ns:{normalized['target']}:{normalized['kind']}"
    return {
        **normalized,
        "work_id": work_id,
        "station": "ns_corpus",
        "runtime": "codex",
        "proof_affecting": False,
        "requires_negative_control": False,
        "expected_exit": "sibling_or_heldout_target_evidence",
        "allowed_paths": [normalized["source_file"], "/tmp/rung1"],
        "task": (
            "Inspect the NS Lean declaration named in target. Do not claim a proof. "
            "Return a bounded JSON result with exit_kind=sibling_or_heldout_target_evidence, "
            "including whether the declaration is theorem-shaped, what exact gap remains, "
            "and one concrete next LeanMill action if productive. Target: "
            f"{normalized['target']} in {normalized['source_file']}. "
            f"Context: {normalized.get('rationale_hint') or 'initial NS corpus smoke attempt'}."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target", required=True, help="Lean declaration name (NS-corpus identifier).")
    ap.add_argument("--source-file", required=True,
                    help="Relative path under ztare_proofs/ZtareProofs/ (must start ns_).")
    ap.add_argument("--kind", default="subscription_agent_task",
                    help="LeanMill work item kind (default: subscription_agent_task).")
    ap.add_argument("--rationale-hint", default="",
                    help="Short context for the worker prompt (≤500 chars).")
    ap.add_argument("--expected-difficulty", default="medium",
                    choices=("easy", "medium", "hard"))
    ap.add_argument("--prior-attempts-json", default="[]",
                    help="JSON list of prior work_ids that targeted the same lemma.")
    ap.add_argument("--factory-policy", default=DEFAULT_FACTORY_POLICY)
    ap.add_argument("--dry-run", action="store_true", default=True,
                    help="Default — validate + print, do not enqueue. Pass --commit to enqueue.")
    ap.add_argument("--commit", action="store_true",
                    help="Actually enqueue (perturbs LeanMill state).")
    args = ap.parse_args()

    if args.commit:
        args.dry_run = False

    item = {
        "schema": SCHEMA,
        "target": args.target,
        "source_file": args.source_file,
        "kind": args.kind,
        "rationale_hint": args.rationale_hint,
        "expected_difficulty": args.expected_difficulty,
        "prior_attempts": json.loads(args.prior_attempts_json),
    }
    result = validate_work_item(item)
    print("=== contract validation ===")
    print(json.dumps(result, indent=2))
    if not result["ok"]:
        print("REJECTED — fix reasons above before enqueueing.")
        return 2

    normalized = result["normalized"]
    decl_ok, decl_reason = _decl_exists(normalized["source_file"], normalized["target"])
    print("\n=== source declaration validation ===")
    print(json.dumps({"ok": decl_ok, "reason": decl_reason}, indent=2))
    if not decl_ok:
        print("REJECTED — source target must exist before enqueueing.")
        return 2

    try:
        sys.path.insert(0, str(REPO / "scripts" / "public" / "control"))
        import leanmill_work_queue as wq  # noqa: E402
        from leanmill_agent_repair_worker import validate_contract  # noqa: E402
    except ImportError as e:
        print(f"FAILED to import LeanMill worker modules: {e}")
        return 3

    payload = _build_worker_payload(normalized)
    worker_contract = validate_contract(payload, max_iterations=3, max_wall_time_s=1200)
    print("\n=== worker contract validation ===")
    print(json.dumps(worker_contract, indent=2, sort_keys=True))
    if worker_contract["status"] != "pass":
        print("REJECTED — payload would not be claimable by leanmill_agent_repair_worker.")
        return 3

    if args.dry_run:
        print("\n=== dry-run ===")
        print("Would enqueue the worker-ready payload below.")
        print(json.dumps(payload, indent=2, sort_keys=True))
        print("Re-run with --commit to actually enqueue (perturbs LeanMill).")
        print("\nRecommended initial lane floors for ns corpus:")
        print(json.dumps(build_ns_lane_floor(), indent=2))
        return 0

    # Commit path — enqueue via LeanMill work_queue after both contracts pass.
    print("\n=== commit path: enqueueing to LeanMill work queue ===")
    try:
        cx = wq.connect(wq.DEFAULT_DB)
        wq.enqueue(
            cx,
            kind=payload["kind"],
            payload=payload,
            priority=priority_value(
                path=args.factory_policy,
                namespace="work_queue",
                key="ns_lemma_enqueue",
                fallback=50,
            ),
            max_attempts=2,
        )
        print(f"enqueued: work_id={payload['work_id']}")
        return 0
    except (sqlite3.Error, Exception) as e:
        print(f"FAILED to enqueue: {e}")
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
