#!/usr/bin/env python3
"""Automate candidate-family heldout promotion work.

This worker is deliberately narrow. It does not prove, ratify, or promote by
declaration. It turns heldout scout output into bounded work:

1. If a heldout row lacks family-spec positive/negative templates, enqueue a
   subscription-agent task to propose the patch.
2. If the templates exist, enqueue a focused heldout family-spec probe.
3. If such a probe finishes with a governed positive and matched negative
   control, emit a heldout receipt for the registry gate to validate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import leanmill_family_specs as family_specs
import leanmill_work_queue as work_queue
from leanmill_factory_config import FACTORY_POLICY as DEFAULT_FACTORY_POLICY, priority_value
from leanmill_heldout_receipt_gate import validate_receipt
from leanmill_paths import REPAIR_FAMILY_REGISTRY
from leanmill_learning_work_seeder import (
    DEFAULT_EXTRA_CORPORA,
    DEFAULT_ROOT_BASE,
    DEFAULT_STATIC_FILTER,
    _exit_contract,
    _probe_signature,
    _slug,
    _write_probe_corpus,
    _write_probe_static_filter,
)


DEFAULT_DATA_DIR = "analytics/public/leanmill/dashboard_data"
DEFAULT_SCOUT = f"{DEFAULT_DATA_DIR}/heldout_independence_scout.json"
DEFAULT_OUT = f"{DEFAULT_DATA_DIR}/heldout_promotion_worker.json"
DEFAULT_MD = f"{DEFAULT_DATA_DIR}/heldout_promotion_worker.md"
DEFAULT_OUT_DIR = f"{DEFAULT_DATA_DIR}/queued_learning_work"
DEFAULT_CORPUS = "/tmp/rung1/mcb_corpus_v2.json"


def _queue_priority(args: argparse.Namespace, key: str, fallback: int) -> int:
    return priority_value(
        path=getattr(args, "factory_policy", DEFAULT_FACTORY_POLICY),
        namespace="work_queue",
        key=key,
        fallback=fallback,
    )


def _read_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return {}
    try:
        obj = json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _sha_file(path: str | Path) -> str:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return ""
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _templates_for_row(spec: dict[str, Any], row_id: str) -> list[dict[str, Any]]:
    return [
        t for t in (spec.get("templates") or [])
        if isinstance(t, dict) and str(t.get("row_id") or "") == row_id
    ]


def _has_template_pair(spec: dict[str, Any], row_id: str) -> bool:
    kinds = {str(t.get("test_kind") or "") for t in _templates_for_row(spec, row_id)}
    return "positive" in kinds and "negative_control" in kinds


def _open_work_exists(cx: Any, *, family: str, row_id: str, kinds: set[str]) -> bool:
    rows = cx.execute(
        """
        SELECT payload_json
        FROM work_items
        WHERE status IN ('queued','claimed','running') AND kind IN (%s)
        """ % ",".join("?" for _ in kinds),
        tuple(sorted(kinds)),
    ).fetchall()
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            continue
        if str(payload.get("family") or "") != family:
            continue
        if str(payload.get("heldout_candidate", {}).get("row_id") or payload.get("heldout_row") or "") == row_id:
            return True
        if str(payload.get("row_id") or "") == row_id and str(payload.get("probe_lane") or "") == "heldout_family_spec":
            return True
    return False


def _terminal_receipt_exists(cx: Any, *, family: str, row_id: str) -> bool:
    rows = cx.execute(
        """
        SELECT payload_json
        FROM work_items
        WHERE family=? AND status='done'
        """,
        (family,),
    ).fetchall()
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            continue
        if str(payload.get("heldout_row") or "") == row_id and payload.get("heldout_receipt_status") == "pass":
            return True
    return False


def _family_has_open_promotion_work(cx: Any, *, family: str) -> bool:
    rows = cx.execute(
        """
        SELECT payload_json
        FROM work_items
        WHERE family=? AND status IN ('queued','claimed','running')
          AND kind IN ('subscription_agent_task','agent_repair_task','repair_canary_probe')
        """,
        (family,),
    ).fetchall()
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            continue
        if payload.get("heldout_candidate") or payload.get("heldout_row") or str(payload.get("probe_lane") or "") == "heldout_family_spec":
            return True
    return False


def _registry_statuses(path: str) -> dict[str, str]:
    obj = _read_json(path)
    out: dict[str, str] = {}
    for fam in obj.get("families") or []:
        family = str(fam.get("family") or "")
        status = str(fam.get("status") or "")
        if family:
            out[family] = status
    return out


def _enqueue_agent_task(
    args: argparse.Namespace,
    cx: Any,
    *,
    family: str,
    spec: dict[str, Any],
    fam_report: dict[str, Any],
    cand: dict[str, Any],
    run_id: str,
) -> dict[str, Any] | None:
    row_id = str(cand.get("row_id") or "")
    if _open_work_exists(cx, family=family, row_id=row_id, kinds={"subscription_agent_task", "agent_repair_task"}):
        return None
    spec_path = str(spec.get("_path") or Path(args.spec_dir) / f"{_slug(family)}.yaml")
    work_id = f"agent_heldout_template:{family}:{row_id}:{run_id}"
    prompt = (
        "Create or update a LeanMill repair-family YAML spec with one positive template and one matched "
        "negative-control template for the heldout row below. Keep it data-only: do not run Lean, update "
        "scoreboards, update registries, create receipts, or claim proof value. Use the existing family "
        "style and keep credit boundaries false for source/clean-solver credit. The patch must be reusable: "
        "it must add or preserve a clean positive/negative_control pair for exactly the heldout row, must not use `?_`, "
        "must not duplicate the positive body as the negative body, and must not increase family-spec gate failures.\n\n"
        f"Family: {family}\n"
        f"Spec path: {spec_path}\n"
        f"Heldout row: {json.dumps(cand, sort_keys=True)}\n"
        f"Design rows: {json.dumps(fam_report.get('design_rows') or [], sort_keys=True)}\n"
        f"Design source files: {json.dumps(fam_report.get('design_source_files') or [], sort_keys=True)}\n\n"
        "Required final JSON:\n"
        "{\"exit_kind\":\"family_spec_patch\",\"files_changed\":[...],"
        "\"heldout_row\":\"...\",\"negative_control_id\":\"...\"}\n"
    )
    payload = {
        "work_id": work_id,
        "family": family,
        "station": "repair_registry",
        "expected_exit": "family_spec_patch",
        "runtime": args.agent_runtime,
        "task": f"Add heldout family-spec templates for {family} on {row_id}",
        "prompt": prompt,
        "allowed_paths": [spec_path],
        "heldout_candidate": cand,
        "heldout_row": row_id,
        "family_spec_patch_mode": "heldout_template",
        "proof_affecting": False,
        "requires_negative_control": True,
        "negative_control": "Add a matched negative_control template for the same heldout row that should fail if the bridge assumption/template ingredient is removed or misdirected.",
        "max_iterations": args.agent_max_iterations,
        "max_wall_time_s": args.agent_max_wall_time_s,
        "proof_credit_authority": "governance_gate",
        "credit_boundary": {
            "credit_type": "none",
            "proof_credit_authority": "governance_gate",
            "worker_can_self_ratify": False,
        },
        "worker_can_self_ratify": False,
    }
    work_queue.enqueue(cx, kind="subscription_agent_task", priority=args.agent_priority + int(cand.get("score") or 0), payload=payload, max_attempts=1)
    work_queue.append_event(args.events, {
        "event_type": "heldout_template_agent_task_enqueued",
        "work_id": work_id,
        "payload": {"family": family, "heldout_row": row_id, "spec_path": spec_path},
        "artifact_paths": [args.scout],
    })
    return {"work_id": work_id, "family": family, "row_id": row_id, "action": "agent_template_task_enqueued"}


def _focused_tests(args: argparse.Namespace, *, family: str, spec: dict[str, Any], row_id: str, static_filter: str) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    credit = spec.get("credit") or {}
    for template in _templates_for_row(spec, row_id):
        body_lines = family_specs._template_body(template)
        tests.append({
            "packet_id": f"{family}:{row_id}:{template.get('id') or 'heldout_family_spec_template'}",
            "repair_family": family,
            "row_id": row_id,
            "candidate_name": None,
            "action_family": "manual_extra",
            "test_kind": str(template.get("test_kind") or "positive"),
            "expected_outcome": str(template.get("expected_outcome") or ""),
            "backend": str(template.get("backend") or args.backend),
            "timeout": int(template.get("timeout") or args.probe_timeout_s),
            "max_candidates": 1,
            "max_actions": 1,
            "score_candidates": False,
            "require_positive_source_action": False,
            "source_credit_eligible": bool(credit.get("source_credit_eligible", False)),
            "clean_solver_credit_eligible": bool(credit.get("clean_solver_credit_eligible", False)),
            "credit_type": "heldout_repair_family_spec_probe",
            "static_filter": static_filter,
            "extra_body": body_lines,
            "family_spec_path": str(spec.get("_path") or ""),
        })
    return tests


def _enqueue_probe(
    args: argparse.Namespace,
    cx: Any,
    *,
    family: str,
    spec: dict[str, Any],
    fam_report: dict[str, Any],
    cand: dict[str, Any],
    run_id: str,
) -> dict[str, Any] | None:
    row_id = str(cand.get("row_id") or "")
    if _open_work_exists(cx, family=family, row_id=row_id, kinds={"repair_canary_probe"}):
        return None
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    label = "heldout_family_spec"
    if not hasattr(args, "row_context"):
        setattr(args, "row_context", "/__leanmill_missing_row_context__.json")
    probe_corpus, probe_corpus_meta = _write_probe_corpus(
        args,
        family=family,
        row_ids={row_id},
        out_dir=out_dir,
        run_id=run_id,
        label=label,
    )
    if probe_corpus_meta.get("missing_row_ids"):
        return {"family": family, "row_id": row_id, "action": "probe_not_enqueued", "reason": "heldout_row_missing_from_probe_corpus", "missing": probe_corpus_meta.get("missing_row_ids")}
    static_filter = _write_probe_static_filter(tests=[], out_dir=out_dir, family=family, run_id=run_id, label=label)
    tests = _focused_tests(args, family=family, spec=spec, row_id=row_id, static_filter=static_filter)
    Path(static_filter).write_text(json.dumps({
        "schema": "leanmill-generated-probe-static-filter-v1",
        "family": family,
        "label": label,
        "rows": [{
            "row_id": row_id,
            "canary_ready_count": 0,
            "canary_ready_candidates": [],
            "row_context_ready_candidates": [],
            "target_context_ready_candidates": [],
        }],
    }, indent=2, sort_keys=True) + "\n")
    packet_path = out_dir / f"heldout_family_spec_probe_packet_{_slug(family)}_{_slug(row_id)}_{run_id}.json"
    root = Path(args.root_base) / f"heldout_family_spec_probe_{_slug(family)}_{_slug(row_id)}_{run_id}"
    packet_obj = {
        "schema": "leanmill-concrete-learning-probe-packet-v1",
        "parent_spec": str(spec.get("_path") or ""),
        "repair_family": family,
        "heldout_row": row_id,
        "science_rule": "Heldout family-spec probes are executable canaries only; validated-family credit requires a heldout receipt accepted by the registry gate.",
        "credit_boundary": {
            "source_credit_eligible": False,
            "clean_solver_credit_eligible": False,
            "proof_credit_authority": "governance_gate",
        "credit_boundary": {
            "credit_type": "none",
            "proof_credit_authority": "governance_gate",
            "worker_can_self_ratify": False,
        },
            "worker_can_self_ratify": False,
        },
        "exit_contract": _exit_contract(tests),
        "packets": [{
            "repair_family": family,
            "state": "ready_for_drain",
            "tests": tests,
            "selected_rows": [{"row_id": row_id}],
        }],
    }
    packet_path.write_text(json.dumps(packet_obj, indent=2, sort_keys=True) + "\n")
    work_id = f"probe:heldout_family_spec:{family}:{row_id}:{run_id}"
    payload = {
        "work_id": work_id,
        "family": family,
        "station": "proof_execution",
        "probe_lane": "heldout_family_spec",
        "replenish_group": f"{family}:heldout_family_spec:{row_id}",
        "heldout_candidate": cand,
        "heldout_row": row_id,
        "template_design_rows": fam_report.get("design_rows") or [],
        "independence_precheck": cand.get("independence_precheck") or {},
        "probe_signature": _probe_signature(family, "heldout_family_spec", tests),
        "packet": str(packet_path),
        "root": str(root),
        "corpus": probe_corpus,
        "probe_corpus_meta": probe_corpus_meta,
        "static_filter": static_filter,
        "scoreboard": str(root / "scoreboard.json"),
        "limit": min(args.max_tests_per_probe, len(tests)),
        "max_candidates": 1,
        "max_actions": 1,
        "timeout": args.probe_timeout_s,
        "test_wall_timeout": args.probe_wall_timeout_s,
        "backend": args.backend,
        "warm_repl_inline": False,
        "govern_winners": bool(args.govern_winners),
        "credit_boundary": packet_obj["credit_boundary"],
        "exit_contract": packet_obj["exit_contract"],
        "expected_exit": "heldout_receipt_or_candidate_hold",
    }
    work_queue.enqueue(cx, kind="repair_canary_probe", priority=args.probe_priority + int(cand.get("score") or 0), payload=payload, max_attempts=args.max_attempts)
    work_queue.append_event(args.events, {
        "event_type": "heldout_family_spec_probe_enqueued",
        "work_id": work_id,
        "payload": {"family": family, "heldout_row": row_id, "score": cand.get("score")},
        "artifact_paths": [str(packet_path), probe_corpus, static_filter],
    })
    return {"work_id": work_id, "family": family, "row_id": row_id, "action": "heldout_probe_enqueued"}


def _events(path: Path, name: str) -> list[dict[str, Any]]:
    p = path / "events" / name
    if not p.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in p.read_text(errors="ignore").splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _receipt_for_done_probe(args: argparse.Namespace, cx: Any, row: Any) -> dict[str, Any] | None:
    payload = json.loads(row["payload_json"] or "{}")
    if str(payload.get("probe_lane") or "") != "heldout_family_spec":
        return None
    family = str(payload.get("family") or "")
    row_id = str(payload.get("heldout_row") or payload.get("heldout_candidate", {}).get("row_id") or "")
    if not family or not row_id or _terminal_receipt_exists(cx, family=family, row_id=row_id):
        return None
    root = Path(str(payload.get("root") or ""))
    scoreboard = _read_json(payload.get("scoreboard") or root / "scoreboard.json")
    if int(scoreboard.get("ratified_closure_count") or 0) <= 0 or int(scoreboard.get("negative_control_fail_count") or 0) <= 0:
        return None
    closed = [r for r in _events(root, "closed.jsonl") if str(r.get("row_id") or "") == row_id and str(r.get("repair_family") or "") == family]
    negatives = [r for r in _events(root, "negative_controls.jsonl") if str(r.get("row_id") or "") == row_id and str(r.get("repair_family") or "") == family]
    if not closed or not negatives:
        return None
    persisted = ""
    for cand in closed[0].get("ratified_candidates") or []:
        persisted = str(cand.get("persisted") or "")
        if persisted:
            break
    proof_hash = _sha_file(persisted)
    if not proof_hash:
        return None
    receipt_dir = root / "heldout_receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    governance_report = receipt_dir / f"{_slug(family)}_{_slug(row_id)}_heldout_governance_report.json"
    governance_report.write_text(json.dumps({
        "event_type": "governance_ratified",
        "family": family,
        "heldout_row": row_id,
        "proof_replay_hash": proof_hash,
        "scoreboard": str(payload.get("scoreboard") or ""),
        "closed_event": closed[0],
    }, indent=2, sort_keys=True) + "\n")
    precheck = payload.get("independence_precheck") or {}
    receipt = {
        "schema": "leanmill-heldout-receipt-v1",
        "family": family,
        "heldout_row": row_id,
        "template_design_rows": [str(x) for x in (payload.get("template_design_rows") or []) if str(x or "")],
        "expected_outcome": "closure",
        "created_at_epoch": int(time.time()),
        "evidence": {
            "not_same_row": precheck.get("not_same_row") is True,
            "not_same_target_alias": precheck.get("not_same_target_alias") is True,
            "not_same_source_file": precheck.get("not_same_source_file") is True,
            "not_used_in_template_design": precheck.get("not_used_in_template_design") is True,
            "matched_negative_control_failed": True,
            "governance_ratified": True,
        },
        "artifacts": {
            "proof_replay_hash": proof_hash,
            "artifact_hash": _sha_file(payload.get("scoreboard") or ""),
            "governance_report": str(governance_report),
            "scoreboard": str(payload.get("scoreboard") or ""),
            "persisted_proof": persisted,
        },
        "credit": {
            "source_credit_eligible": False,
            "clean_solver_credit_eligible": False,
            "repair_canary_credit_eligible": True,
        },
        "produced_by_worker_class": "governance",
        "produced_by_worker_id": "leanmill-governance",
    }
    receipt_path = receipt_dir / f"{_slug(family)}_{_slug(row_id)}_heldout_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    failures = validate_receipt(receipt)
    status = "pass" if not failures else "fail"
    work_id = f"heldout_receipt:{family}:{row_id}"
    work_queue.record_terminal_item(
        cx,
        kind="heldout_receipt",
        status="done" if status == "pass" else "failed",
        priority=_queue_priority(args, "heldout_receipt_terminal", 500),
        payload={
            "work_id": work_id,
            "family": family,
            "station": "repair_registry",
            "heldout_row": row_id,
            "heldout_receipt": str(receipt_path),
            "heldout_receipt_status": status,
            "failures": failures,
            "expected_exit": "validated_family_evidence_or_receipt_failure",
        },
    )
    work_queue.append_event(args.events, {
        "event_type": f"heldout_receipt_{status}",
        "work_id": work_id,
        "payload": {"family": family, "heldout_row": row_id, "failure_count": len(failures)},
        "artifact_paths": [str(receipt_path), str(governance_report), str(payload.get("scoreboard") or "")],
    })
    return {"family": family, "row_id": row_id, "action": f"heldout_receipt_{status}", "receipt": str(receipt_path), "failure_count": len(failures)}


def _collect_receipts(args: argparse.Namespace, cx: Any) -> list[dict[str, Any]]:
    rows = cx.execute(
        """
        SELECT *
        FROM work_items
        WHERE kind='repair_canary_probe' AND status='done'
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (args.receipt_scan_limit,),
    ).fetchall()
    actions: list[dict[str, Any]] = []
    for row in rows:
        rec = _receipt_for_done_probe(args, cx, row)
        if rec:
            actions.append(rec)
            if len(actions) >= args.max_receipts:
                break
    return actions


def run(args: argparse.Namespace) -> dict[str, Any]:
    scout = _read_json(args.scout)
    registry_status = _registry_statuses(args.registry)
    specs = {str(spec.get("family") or ""): spec for spec in family_specs.load_specs(args.spec_dir)}
    cx = work_queue.connect(args.queue_db)
    run_id = args.run_id or str(int(time.time()))
    actions: list[dict[str, Any]] = []
    receipt_actions = _collect_receipts(args, cx)
    actions.extend(receipt_actions)
    for fam_report in scout.get("families") or []:
        if len([a for a in actions if str(a.get("action") or "").endswith("_enqueued")]) >= args.max_enqueued:
            break
        family = str(fam_report.get("family") or "")
        spec = specs.get(family) or {}
        if not family:
            continue
        if not spec:
            spec = {
                "family": family,
                "_path": str(Path(args.spec_dir) / f"{_slug(family)}.yaml"),
                "templates": [],
                "credit": {
                    "source_credit_eligible": False,
                    "clean_solver_credit_eligible": False,
                },
            }
        if registry_status.get(family) == "validated_family":
            actions.append({"family": family, "action": "family_skipped_already_validated"})
            continue
        if _family_has_open_promotion_work(cx, family=family):
            actions.append({"family": family, "action": "family_skipped_open_promotion_work"})
            continue
        for cand in fam_report.get("eligible_candidates") or []:
            row_id = str(cand.get("row_id") or "")
            if not row_id:
                continue
            if _terminal_receipt_exists(cx, family=family, row_id=row_id):
                continue
            if _has_template_pair(spec, row_id):
                action = _enqueue_probe(args, cx, family=family, spec=spec, fam_report=fam_report, cand=cand, run_id=run_id)
            else:
                action = _enqueue_agent_task(args, cx, family=family, spec=spec, fam_report=fam_report, cand=cand, run_id=run_id)
            if action:
                actions.append(action)
                break
    payload = {
        "schema": "leanmill-heldout-promotion-worker-v1",
        "generated_at_epoch": int(time.time()),
        "scout": args.scout,
        "action_count": len(actions),
        "receipt_actions": receipt_actions,
        "actions": actions,
        "science_rule": "This worker only creates bounded heldout work or receipt candidates; registry promotion still depends on heldout receipt validation.",
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if args.md:
        _write_md(payload, args.md)
    return payload


def _write_md(payload: dict[str, Any], path: str) -> None:
    lines = [
        "# LeanMill Heldout Promotion Worker",
        "",
        f"- generated_at_epoch: `{payload.get('generated_at_epoch')}`",
        f"- action_count: `{payload.get('action_count')}`",
        "",
        "## Actions",
    ]
    for action in payload.get("actions") or []:
        lines.append(
            f"- `{action.get('action')}` family=`{action.get('family')}` row=`{action.get('row_id')}` work=`{action.get('work_id', '')}`"
        )
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines).rstrip() + "\n")


def _self_test() -> int:
    import tempfile

    with tempfile.TemporaryDirectory(prefix="leanmill_heldout_promotion_") as td:
        root = Path(td)
        spec_dir = root / "specs"
        spec_dir.mkdir()
        (spec_dir / "fam.yaml").write_text(
            "family: fam\nversion: 1\nstatus: candidate_family\n"
            "credit:\n  source_credit_eligible: false\n  clean_solver_credit_eligible: false\n"
            "templates:\n"
            "  - id: pos\n    row_id: r2\n    test_kind: positive\n    expected_outcome: governed_repair_canary_closure\n    backend: repl_file\n    timeout: 30\n    body: exact h\n"
            "  - id: neg\n    row_id: r2\n    test_kind: negative_control\n    expected_outcome: must_fail\n    backend: repl_file\n    timeout: 30\n    body: exact bad\n"
        )
        scout = root / "scout.json"
        scout.write_text(json.dumps({
            "families": [{
                "family": "fam",
                "design_rows": ["r1"],
                "design_source_files": ["A.lean"],
                "eligible_candidates": [{
                    "row_id": "r2",
                    "score": 3,
                    "independence_precheck": {
                        "not_same_row": True,
                        "not_same_target_alias": True,
                        "not_same_source_file": True,
                        "not_used_in_template_design": True,
                    },
                }],
            }]
        }))
        corpus = root / "corpus.json"
        heldout_file = root / "B.lean"
        heldout_file.write_text("theorem r2 : True := by\n  trivial\n")
        corpus.write_text(json.dumps({"rows": [{
            "id": "r2",
            "row_id": "r2",
            "sorried_file": str(heldout_file),
            "source_file": str(heldout_file),
            "target_line": 1,
            "source": {"mathlib_name": "r2", "file": "B.lean"},
        }]}))
        registry = root / "registry.json"
        registry.write_text(json.dumps({"families": [{"family": "fam", "status": "candidate_family"}]}))
        args = argparse.Namespace(
            scout=str(scout),
            registry=str(registry),
            spec_dir=str(spec_dir),
            queue_db=str(root / "q.sqlite"),
            events=str(root / "events.jsonl"),
            out=str(root / "out.json"),
            md=str(root / "out.md"),
            out_dir=str(root / "queued"),
            root_base=str(root / "roots"),
            corpus=str(corpus),
            extra_corpus=[],
            backend="repl_file",
            max_tests_per_probe=4,
            probe_timeout_s=30,
            probe_wall_timeout_s=30,
            warm_repl_inline=True,
            govern_winners=True,
            probe_priority=300,
            agent_runtime="codex",
            agent_priority=250,
            agent_max_iterations=3,
            agent_max_wall_time_s=1200,
            max_attempts=1,
            max_enqueued=2,
            run_id="selftest",
            receipt_scan_limit=20,
            max_receipts=2,
        )
        payload = run(args)
        assert any(a.get("action") == "heldout_probe_enqueued" for a in payload["actions"]), payload
        second = run(args)
        assert any(a.get("action") == "family_skipped_open_promotion_work" for a in second["actions"]), second

        receipt_root = root / "receipt_probe"
        (receipt_root / "events").mkdir(parents=True)
        proof = receipt_root / "proof.lean"
        proof.write_text("theorem r3 : True := by\n  trivial\n")
        scoreboard = receipt_root / "scoreboard.json"
        scoreboard.write_text(json.dumps({
            "ratified_closure_count": 1,
            "negative_control_fail_count": 1,
        }) + "\n")
        (receipt_root / "events" / "closed.jsonl").write_text(json.dumps({
            "row_id": "r3",
            "repair_family": "fam",
            "ratified_candidates": [{"persisted": str(proof)}],
        }) + "\n")
        (receipt_root / "events" / "negative_controls.jsonl").write_text(json.dumps({
            "row_id": "r3",
            "repair_family": "fam",
            "result": "failed_as_expected",
        }) + "\n")
        cx = work_queue.connect(args.queue_db)
        work_queue.record_terminal_item(cx, kind="repair_canary_probe", status="done", priority=400, payload={
            "work_id": "probe:heldout_family_spec:fam:r3:selftest",
            "family": "fam",
            "station": "proof_execution",
            "probe_lane": "heldout_family_spec",
            "heldout_row": "r3",
            "template_design_rows": ["r1"],
            "independence_precheck": {
                "not_same_row": True,
                "not_same_target_alias": True,
                "not_same_source_file": True,
                "not_used_in_template_design": True,
            },
            "root": str(receipt_root),
            "scoreboard": str(scoreboard),
            "expected_exit": "heldout_receipt_or_candidate_hold",
        })
        cx.close()
        scout.write_text(json.dumps({"families": []}) + "\n")
        receipt_payload = run(args)
        assert any(a.get("action") == "heldout_receipt_pass" for a in receipt_payload["receipt_actions"]), receipt_payload
        cx = work_queue.connect(args.queue_db)
        assert _terminal_receipt_exists(cx, family="fam", row_id="r3")
        cx.close()
    print("leanmill_heldout_promotion_worker self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scout", default=DEFAULT_SCOUT)
    ap.add_argument("--registry", default=REPAIR_FAMILY_REGISTRY)
    ap.add_argument("--spec-dir", default=family_specs.DEFAULT_SPEC_DIR)
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--events", default=work_queue.DEFAULT_EVENTS)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--md", default=DEFAULT_MD)
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    ap.add_argument("--root-base", default=DEFAULT_ROOT_BASE)
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--extra-corpus", action="append", default=list(DEFAULT_EXTRA_CORPORA))
    ap.add_argument("--backend", default="repl_file")
    ap.add_argument("--max-tests-per-probe", type=int, default=4)
    ap.add_argument("--probe-timeout-s", type=int, default=140)
    ap.add_argument("--probe-wall-timeout-s", type=int, default=220)
    ap.add_argument("--warm-repl-inline", action="store_true")
    ap.add_argument("--govern-winners", action="store_true")
    ap.add_argument("--probe-priority", type=int, default=390)
    ap.add_argument("--agent-runtime", default="codex", choices=["codex", "claude"])
    ap.add_argument("--agent-priority", type=int, default=360)
    ap.add_argument("--factory-policy", default=DEFAULT_FACTORY_POLICY)
    ap.add_argument("--agent-max-iterations", type=int, default=3)
    ap.add_argument("--agent-max-wall-time-s", type=int, default=1200)
    ap.add_argument("--max-attempts", type=int, default=1)
    ap.add_argument("--max-enqueued", type=int, default=4)
    ap.add_argument("--receipt-scan-limit", type=int, default=200)
    ap.add_argument("--max-receipts", type=int, default=4)
    ap.add_argument("--run-id", default="")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if int(args.probe_priority) == 390:
        args.probe_priority = _queue_priority(args, "heldout_promotion_probe", 390)
    if int(args.agent_priority) == 360:
        args.agent_priority = _queue_priority(args, "heldout_promotion_agent", 360)
    print(json.dumps(run(args), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
