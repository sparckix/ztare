#!/usr/bin/env python3
"""LeanMill Andon cord for stop-the-line containment.

The cord is a deterministic control-plane guard. It does not prove, score, or
promote. It detects factory states where continuing normal scheduling would
create downstream waste or risk, writes an auditable containment policy, and
lets the runner/watchdog apply that policy.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue
from leanmill_paths import DATA_DIR as DEFAULT_DATA_DIR


DEFAULT_INTELLIGENCE = f"{DEFAULT_DATA_DIR}/leanmill_factory_intelligence.json"
DEFAULT_OUT = f"{DEFAULT_DATA_DIR}/leanmill_andon_cord.json"


def _now() -> int:
    return int(time.time())


def _read_json(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists() or not p.is_file():
        return {}
    try:
        obj = json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _write_json(path: str | Path, obj: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    intel = _read_json(args.intelligence)
    cx = work_queue.connect(args.queue_db)
    open_stats = work_queue.open_stats(cx)
    flow = intel.get("learning_unit_flow") or {}
    verdict = intel.get("verdict") or {}
    conversion = intel.get("conversion_diagnostics") or {}
    stage_counts = conversion.get("stage_outcome_counts") or {}
    recommendations = intel.get("recommendations") or []
    queue = intel.get("queue") or {}
    open_kinds = open_stats.get("by_kind") or queue.get("open_kind_counts") or {}

    scoreboard = flow.get("scoreboard_tail_counts") or {}
    governed_value = _as_int(verdict.get("governed_value_tail_count"))
    if not governed_value:
        governed_value = sum(_as_int(scoreboard.get(k)) for k in ("ratified_closure_count", "exact_gap_candidate_count", "valid_falsifier_count"))
    source_flow = _as_int(verdict.get("source_flow_tail_count"))
    source_open = _as_int(open_kinds.get("source_scout_task")) + _as_int(open_kinds.get("source_search_task"))
    probe_open = _as_int(open_kinds.get("repair_canary_probe"))
    gm_open = _as_int(open_kinds.get("gm_operator_task"))
    source_probe = stage_counts.get("probe_source_binding") or {}
    source_probe_total = sum(_as_int(v) for v in source_probe.values()) if isinstance(source_probe, dict) else 0
    source_probe_value = sum(
        _as_int(source_probe.get(k))
        for k in ("ratified_closure", "exact_gap_candidate", "valid_falsifier")
    ) if isinstance(source_probe, dict) else 0

    defects: list[dict[str, Any]] = []
    unexpected_neg = _as_int(scoreboard.get("negative_control_unexpected_pass_count"))
    if unexpected_neg:
        defects.append({
            "class": "safety_unexpected_negative_control_pass",
            "severity": "stop",
            "evidence": {"negative_control_unexpected_pass_count": unexpected_neg},
            "containment": "pause new proof-credit work and require governance review",
        })

    if source_probe_total >= args.min_source_bound_probes and source_probe_value == 0:
        defects.append({
            "class": "source_bound_zero_value",
            "severity": "contain",
            "evidence": {"source_probe_total": source_probe_total, "source_probe_value": source_probe_value},
            "containment": "pause direct source-binding expansion and route to family-spec, heldout, or strategy repair",
        })

    if source_flow >= args.min_source_flow and governed_value < args.min_governed_value and probe_open < args.min_probe_open:
        defects.append({
            "class": "verified_exit_starvation",
            "severity": "contain",
            "evidence": {
                "source_flow_tail_count": source_flow,
                "governed_value_tail_count": governed_value,
                "open_repair_canary_probe": probe_open,
            },
            "containment": "stop source/scout overproduction until proof-value work is queued or blocked with receipts",
        })

    if gm_open >= args.min_gm_open:
        defects.append({
            "class": "gm_review_queue_not_drained",
            "severity": "contain",
            "evidence": {"open_gm_operator_task": gm_open},
            "containment": "auto-drain no-credit GM decisions into bounded worker paths",
        })

    top = recommendations[0] if recommendations else {}
    if str(top.get("class") or "").startswith("conversion_source_bound"):
        defects.append({
            "class": "factory_brain_source_bound_conversion_warning",
            "severity": "contain",
            "evidence": top,
            "containment": "honor factory-brain recommendation before feeding more source-bound work",
        })

    active = any(d.get("severity") in {"stop", "contain"} for d in defects)
    stop = any(d.get("severity") == "stop" for d in defects)
    defect_classes = {str(d.get("class") or "") for d in defects}
    source_binding_containment = bool(
        stop
        or "source_bound_zero_value" in defect_classes
        or "factory_brain_source_bound_conversion_warning" in defect_classes
    )
    source_scout_containment = bool(
        stop
        or "verified_exit_starvation" in defect_classes
        or "factory_brain_source_bound_conversion_warning" in defect_classes
    )
    containment = {
        "pause_external_source_scouts": source_scout_containment,
        "pause_source_binding_ingest": source_binding_containment,
        "pause_source_binding_probes": source_binding_containment,
        "reset_probe_signature_cooldown_s": False,
        "reset_proof_value_family_cooldown_s": active,
        "auto_drain_gm_operator": active,
        "max_gm_auto_drain_tasks": 4 if active else 0,
        "prefer_family_spec_and_heldout_probes": active,
        "max_external_source_scout_floor": 0 if source_scout_containment else None,
    }
    payload = {
        "schema": "leanmill-andon-cord-v1",
        "generated_at_epoch": _now(),
        "active": active,
        "severity": "stop" if stop else "contain" if active else "normal",
        "defect_count": len(defects),
        "defects": defects,
        "containment": containment,
        "release_criteria": [
            "negative_control_unexpected_pass_count remains 0",
            "open proof-value probe lane is nonempty or blocked by explicit receipt",
            "source-bound zero-value families are held or routed to strategy repair",
            "GM heldout/source review queue is drained to no-credit decisions",
        ],
        "observed": {
            "governed_value_tail_count": governed_value,
            "source_flow_tail_count": source_flow,
            "source_open": source_open,
            "probe_open": probe_open,
            "gm_open": gm_open,
        },
        "science_rule": "The Andon cord pauses or redirects work only; Governance Gate remains the only proof-credit authority.",
    }
    if args.out:
        _write_json(args.out, payload)
    if args.apply:
        work_queue.append_event(args.events, {
            "event_type": "leanmill_andon_cord_active" if active else "leanmill_andon_cord_clear",
            "payload": {
                "active": active,
                "severity": payload["severity"],
                "defect_classes": [d.get("class") for d in defects],
                "containment": containment,
            },
            "artifact_paths": [args.out] if args.out else [],
        })
    return payload


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="leanmill_andon_") as td:
        root = Path(td)
        db = str(root / "q.sqlite")
        cx = work_queue.connect(db)
        work_queue.enqueue(cx, kind="source_scout_task", priority=1, payload={"family": "fam", "work_id": "source"})
        intel = root / "intel.json"
        intel.write_text(json.dumps({
            "verdict": {"governed_value_tail_count": 0, "source_flow_tail_count": 0},
            "learning_unit_flow": {"scoreboard_tail_counts": {"negative_control_unexpected_pass_count": 0}},
            "conversion_diagnostics": {"stage_outcome_counts": {"probe_source_binding": {"tested_no_positive_signal": 12}}},
            "recommendations": [],
        }) + "\n")
        out = root / "andon.json"
        payload = evaluate(argparse.Namespace(
            intelligence=str(intel),
            queue_db=db,
            events=str(root / "events.jsonl"),
            out=str(out),
            apply=True,
            min_source_bound_probes=5,
            min_source_flow=10,
            min_governed_value=1,
            min_probe_open=1,
            min_gm_open=1,
        ))
        assert payload["active"] is True
        assert payload["containment"]["pause_external_source_scouts"] is False
        assert payload["containment"]["pause_source_binding_probes"] is True
        assert out.exists()
        intel_starve = root / "intel_starve.json"
        intel_starve.write_text(json.dumps({
            "verdict": {"governed_value_tail_count": 0, "source_flow_tail_count": 25},
            "learning_unit_flow": {"scoreboard_tail_counts": {"negative_control_unexpected_pass_count": 0}},
            "conversion_diagnostics": {"stage_outcome_counts": {}},
            "recommendations": [],
        }) + "\n")
        payload_starve = evaluate(argparse.Namespace(
            intelligence=str(intel_starve),
            queue_db=db,
            events=str(root / "events_starve.jsonl"),
            out=str(root / "andon_starve.json"),
            apply=True,
            min_source_bound_probes=5,
            min_source_flow=10,
            min_governed_value=1,
            min_probe_open=1,
            min_gm_open=1,
        ))
        assert payload_starve["containment"]["pause_external_source_scouts"] is True
        db2 = str(root / "q2.sqlite")
        cx2 = work_queue.connect(db2)
        work_queue.enqueue(cx2, kind="gm_operator_task", priority=1, payload={"work_id": "gm"})
        intel2 = root / "intel2.json"
        intel2.write_text(json.dumps({
            "verdict": {"governed_value_tail_count": 1, "source_flow_tail_count": 0},
            "learning_unit_flow": {"scoreboard_tail_counts": {"negative_control_unexpected_pass_count": 0}},
            "conversion_diagnostics": {"stage_outcome_counts": {}},
            "recommendations": [],
        }) + "\n")
        payload2 = evaluate(argparse.Namespace(
            intelligence=str(intel2),
            queue_db=db2,
            events=str(root / "events2.jsonl"),
            out=str(root / "andon2.json"),
            apply=True,
            min_source_bound_probes=5,
            min_source_flow=10,
            min_governed_value=1,
            min_probe_open=1,
            min_gm_open=1,
        ))
        assert payload2["active"] is True
        assert payload2["defects"][0]["class"] == "gm_review_queue_not_drained"
        assert payload2["containment"]["auto_drain_gm_operator"] is True
        assert payload2["containment"]["pause_external_source_scouts"] is False
    print("leanmill_andon_cord self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--intelligence", default=DEFAULT_INTELLIGENCE)
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--min-source-bound-probes", type=int, default=5)
    ap.add_argument("--min-source-flow", type=int, default=20)
    ap.add_argument("--min-governed-value", type=int, default=1)
    ap.add_argument("--min-probe-open", type=int, default=1)
    ap.add_argument("--min-gm-open", type=int, default=1)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    payload = evaluate(args)
    print(json.dumps({
        "active": payload["active"],
        "severity": payload["severity"],
        "defect_count": payload["defect_count"],
        "out": args.out,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
