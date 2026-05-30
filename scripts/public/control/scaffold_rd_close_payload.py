#!/usr/bin/env python3
"""Create a standard RD close payload scaffold.

This helper is intentionally not an authority and does not submit a close.
It writes the clerical payload shape expected by rd_forecast_tick_close.py so
the RD spends time on the research receipt rather than file-layout memory.
The generated files still contain explicit research assertions supplied by the
caller, and the normal close preflight/daemon gates remain mandatory.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from src.ztare.research_director.pattern_action_contract import (  # noqa: E402
    build_pattern_action_contract,
)


def _write_text(path: Path, text: str, *, force: bool) -> None:
    if path.exists() and not force:
        raise SystemExit(f"refusing to overwrite existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, value: object, *, force: bool) -> None:
    _write_text(
        path,
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        force=force,
    )


def _artifact_ref(name: str) -> dict[str, str]:
    return {"root": "payload", "path": f"artifacts/{name}.md"}


def _schema_receipt_template(carrier: dict[str, object]) -> dict[str, object]:
    fields = [
        str(field).strip()
        for field in (carrier.get("required_fields") or [])
        if str(field).strip()
    ]
    name = str(carrier.get("name") or "")
    slot = str(carrier.get("artifact_slot") or "")
    if name == "claim_boundary_typed_rows" or slot == "claim_boundary_schema_artifact":
        return {
            "rows": [
                {field: "REPLACE_ME" for field in fields} | {
                    "claim_kind": "broad",
                    "permitted_status": "BLOCKED",
                },
                {field: "REPLACE_ME" for field in fields} | {
                    "claim_kind": "narrow",
                    "permitted_status": "PERMITTED",
                },
            ]
        }
    return {field: "REPLACE_ME" for field in fields}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tick-id", required=True)
    ap.add_argument("--contract-id", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--owner", default="codex:RD")
    ap.add_argument("--consumes-surfaced", required=True)
    ap.add_argument("--summary", required=True,
                    help="Short factual result summary for the F-row.")
    ap.add_argument("--next", required=True,
                    help="Corrected next lever or live target.")
    ap.add_argument("--why-enough", required=True,
                    help="Why this tick can stop without satisficing.")
    ap.add_argument("--scope", default=None,
                    help="Optional substrate/scope for dynamic pattern contract.")
    ap.add_argument("--goal", default=None,
                    help="Optional exact tick goal for dynamic pattern contract.")
    ap.add_argument("--stop-reason", default="frontier_split_required",
                    choices=[
                        "diminishing_information_yield",
                        "named_kill_condition_hit",
                        "budget_exhausted",
                        "operator_interrupt",
                        "superseded_by_new_contract",
                        "frontier_split_required",
                    ])
    ap.add_argument("--dispatch-ledger",
                    default=("label=adversarial_kill; "
                             "label=divide_and_conquer; "
                             "label=cold_deanchor_carveout3"))
    ap.add_argument("--l2-move",
                    default="pec_a Auxiliary Comparison Object Construction",
                    help="Catalog-backed structural-language move id/name.")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    out = Path(args.out_dir)
    today = date.today().isoformat()
    stem = args.tick_id.replace("TICK", "F-NS-TICK", 1)

    f_row = (
        f"date: `{today}`\n"
        f"| {stem} | `{today}` | VPS membrane tick; forecast contract "
        f"`{args.contract_id}`; generated close-payload scaffold filled by "
        f"{args.owner} | **success=TRUE as target-sharpening. "
        f"{args.summary}** | `success_TRUE / useful_boundary / "
        f"next={args.next}` | owner: {args.owner}; tick_id {args.tick_id}; "
        f"forecast contract {args.contract_id}; consumes_surfaced: "
        f"{args.consumes_surfaced} dispatch_ledger: "
        f"{args.dispatch_ledger}\n"
    )

    declared = {
        "l1_pattern": "PATTERN-011 swarm_dispatch or equivalent split",
        "l1_witness": (
            "Caller-supplied scaffold: replace this with the concrete "
            "dispatch and consolidation witness before close."
        ),
        "l2_move": args.l2_move,
        "l2_witness": (
            "Caller-supplied scaffold: replace this with the concrete "
            "mathematical move before close."
        ),
        "l3_antipattern": "scientific_amnesia and premature_settled_negative",
        "l3_witness": (
            "Caller-supplied scaffold: replace this with the actual recurrence "
            "guard and non-overclaim statement before close."
        ),
    }
    why_not = {
        "premature_settled_negative": {
            "reason": "not_a_negative_claim",
            "justification": (
                "This scaffold does not assert a terminal impossibility. "
                "Replace this with the concrete live target or obstruction "
                "boundary before submitting close."
            ),
        }
    }
    contract_goal = args.goal or f"{args.summary} {args.next}"
    pattern_contract = asdict(
        build_pattern_action_contract(scope=args.scope, goal=contract_goal)
    )

    artifacts = {
        "orientation": "Replace with the orientation artifact for this tick.\n",
        "stress_test": "Replace with the stress-test artifact for this tick.\n",
        "verification": "Replace with the verification artifact for this tick.\n",
    }
    carrier_artifacts = {
        "orientation": _artifact_ref("orientation"),
        "stress_test": _artifact_ref("stress_test"),
        "verification": _artifact_ref("verification"),
    }
    carrier_schema_receipts: dict[str, object] = {}
    for carrier in pattern_contract.get("evidence_carriers", []):
        if not isinstance(carrier, dict) or not carrier.get("required"):
            continue
        name = str(carrier.get("name") or "").strip()
        if not name or name in carrier_artifacts:
            continue
        required_fields = [
            str(field).strip()
            for field in (carrier.get("required_fields") or [])
            if str(field).strip()
        ]
        if required_fields:
            carrier_schema_receipts[name] = _schema_receipt_template(carrier)
            continue
        carrier_artifacts[name] = _artifact_ref(name)
        artifacts[name] = (
            f"Replace with the pattern-action receipt for `{name}`.\n\n"
            f"Acceptance check: {carrier.get('acceptance_check', '')}\n"
        )
    research_done = {
        "research_completion": {
            "tick_id": args.tick_id,
            "contract_id": args.contract_id,
            "min_recursive_loops": 1,
            "pattern_action_contract": {
                "root": "payload",
                "path": "artifacts/pattern_action_contract.json",
            },
            "carrier_artifacts": carrier_artifacts,
            "carrier_schema_receipts": carrier_schema_receipts,
            "loops": [
                {
                    "orientation_artifact": _artifact_ref("orientation"),
                    "stress_test_artifact": _artifact_ref("stress_test"),
                    "verification_artifact": _artifact_ref("verification"),
                    "new_information": (
                        "Replace with at least sixty characters describing "
                        "what this recursive loop learned."
                    ),
                    "next_question_or_kill": args.next,
                }
            ],
            "stop_rule": (
                "Stop only after the filled verification artifact identifies "
                "a named next theorem, countermodel, or recurrence boundary."
            ),
            "stop_reason": args.stop_reason,
            "why_enough": args.why_enough,
            "remaining_live_vectors": [args.next],
        }
    }

    _write_text(out / "f_row.txt", f_row, force=args.force)
    _write_json(out / "declared.json", declared, force=args.force)
    _write_json(out / "witnesses.json", {}, force=args.force)
    _write_json(out / "why_not.json", why_not, force=args.force)
    _write_json(out / "research_done.json", research_done, force=args.force)
    for name, text in artifacts.items():
        _write_text(out / "artifacts" / f"{name}.md", text, force=args.force)
    _write_json(
        out / "artifacts" / "pattern_action_contract.json",
        pattern_contract,
        force=args.force,
    )
    print(json.dumps({
        "status": "scaffold_written",
        "out_dir": str(out),
        "next": (
            "Fill declared.json, why_not.json, research_done.json, and "
            "artifacts/*.md with concrete receipts, then run "
            "bash deploy/vps_run.sh rd-close-local-payload ..."
        ),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
