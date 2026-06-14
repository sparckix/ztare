#!/usr/bin/env python3
"""Publish the LeanMill mechanism-vs-overclaim boundary as an internal receipt."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from leanmill_paths import DATA_DIR  # noqa: E402
import leanmill_work_queue as work_queue  # noqa: E402
from src.ztare.leanmill.common import read_json, sha256_file, write_json_atomic, write_text_atomic  # noqa: E402


DEFAULT_GATE = f"{DATA_DIR}/family_spec_gate.json"
DEFAULT_NO_LIFT = f"{DATA_DIR}/evaluation_harness_no_lift_report.json"
DEFAULT_OUT = f"{DATA_DIR}/mechanism_vs_overclaim_report.json"
DEFAULT_MD = f"{DATA_DIR}/mechanism_vs_overclaim_report.md"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def build(args: argparse.Namespace) -> dict[str, Any]:
    gate = _dict(read_json(args.family_spec_gate, default={}))
    no_lift = _dict(read_json(args.no_lift_report, default={}))
    overclaim = _dict(gate.get("overclaim_disqualification_summary"))
    by_family = _dict(overclaim.get("by_family"))
    finding_count = int(overclaim.get("finding_count") or 0)
    family_count = int(overclaim.get("family_count") or len(by_family))
    no_lift_published = str(no_lift.get("status") or "") == "published_no_lift_result"
    status = (
        "published_mechanism_vs_overclaim_boundary"
        if finding_count > 0 else
        "no_overclaim_disqualification_findings"
    )
    top_families = [
        {"family": family, "finding_count": int(count or 0)}
        for family, count in sorted(by_family.items(), key=lambda item: int(item[1] or 0), reverse=True)[:20]
    ]
    return {
        "schema": "leanmill-mechanism-vs-overclaim-report-v1",
        "generated_at_epoch": int(time.time()),
        "status": status,
        "source_family_spec_gate": args.family_spec_gate,
        "source_family_spec_gate_sha256": sha256_file(args.family_spec_gate),
        "source_no_lift_report": args.no_lift_report,
        "source_no_lift_report_sha256": sha256_file(args.no_lift_report),
        "no_lift_report_status": no_lift.get("status") if no_lift else "missing",
        "no_lift_published": no_lift_published,
        "finding_count": finding_count,
        "family_count": family_count,
        "top_families": top_families,
        "allowed_internal_claim": (
            "Family-spec positives include mechanism/calibration signals, but the current benchmark publication forbids treating them as overclaim evidence."
            if finding_count > 0 else
            "No mechanism-vs-overclaim disqualification findings are present in the current gate."
        ),
        "forbidden_claims": [
            "competitive overclaim evidence from public/gold lemma wrappers",
            "benchmark lift without a matching published lift receipt",
            "proof credit from family-spec mechanism/calibration positives",
        ],
        "credit_boundary": "classification/reporting receipt only; no proof credit and no competitive overclaim claim",
        "meta_reasoning_receipt": {
            "failure_mode": "mechanism positives can be summarized as overclaim evidence when public/static baselines explain the win",
            "mechanized_prevention": "publish a gate-hash-bound report that separates mechanism/calibration findings from overclaim claims",
            "gaming_guard": "the report lowers claim strength; it never upgrades mechanism findings into benchmark lift",
        },
        "next_action": "prioritize C-discriminating rows where public/static tools fail and require benchmark uplift before competitive claims",
    }


def write_markdown(path: str | Path, payload: dict[str, Any]) -> None:
    lines = [
        "# LeanMill Mechanism vs Overclaim Report",
        "",
        f"- generated_at_epoch: `{payload.get('generated_at_epoch')}`",
        f"- status: `{payload.get('status')}`",
        f"- source_family_spec_gate: `{payload.get('source_family_spec_gate')}`",
        f"- source_family_spec_gate_sha256: `{payload.get('source_family_spec_gate_sha256')}`",
        f"- no_lift_report_status: `{payload.get('no_lift_report_status')}`",
        f"- finding_count: `{payload.get('finding_count')}`",
        f"- family_count: `{payload.get('family_count')}`",
        f"- allowed_internal_claim: {payload.get('allowed_internal_claim')}",
        f"- forbidden_claims: `{payload.get('forbidden_claims')}`",
        f"- credit_boundary: {payload.get('credit_boundary')}",
        f"- next_action: {payload.get('next_action')}",
        "",
        "## Top Families",
        "",
    ]
    for row in payload.get("top_families") or []:
        lines.append(f"- `{row.get('family')}`: `{row.get('finding_count')}`")
    write_text_atomic(path, "\n".join(lines) + "\n")


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="leanmill_mechanism_overclaim_") as td:
        root = Path(td)
        gate = root / "gate.json"
        no_lift = root / "no_lift.json"
        gate.write_text(json.dumps({
            "overclaim_disqualification_summary": {
                "finding_count": 3,
                "family_count": 2,
                "by_family": {"a": 2, "b": 1},
            }
        }) + "\n")
        no_lift.write_text(json.dumps({"status": "published_no_lift_result"}) + "\n")
        payload = build(argparse.Namespace(family_spec_gate=str(gate), no_lift_report=str(no_lift)))
        assert payload["status"] == "published_mechanism_vs_overclaim_boundary", payload
        assert payload["source_family_spec_gate_sha256"] == sha256_file(gate), payload
    print("leanmill_mechanism_vs_overclaim_report self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family-spec-gate", default=DEFAULT_GATE)
    ap.add_argument("--no-lift-report", default=DEFAULT_NO_LIFT)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--md", default=DEFAULT_MD)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    payload = build(args)
    write_json_atomic(args.out, payload)
    write_markdown(args.md, payload)
    if args.events:
        work_queue.append_event(args.events, {
            "event_type": "leanmill_mechanism_vs_overclaim_published",
            "payload": {
                "status": payload.get("status"),
                "source_family_spec_gate_sha256": payload.get("source_family_spec_gate_sha256"),
                "finding_count": payload.get("finding_count"),
                "next_action": payload.get("next_action"),
            },
            "artifact_paths": [args.out, args.md],
        })
    print(json.dumps({
        "out": args.out,
        "md": args.md,
        "status": payload.get("status"),
        "finding_count": payload.get("finding_count"),
        "next_action": payload.get("next_action"),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
