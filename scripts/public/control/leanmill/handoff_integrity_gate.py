#!/usr/bin/env python3
"""LeanMill cross-seam handoff integrity gate.

This gate checks invariants that span multiple workers. Unit tests can pass
while handoffs still leak value, so this read-only gate inspects the live queue
and probe receipts for conversion-seam failures.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

import leanmill_work_queue as work_queue
from leanmill_factory_config import FACTORY_POLICY, read_policy
from leanmill_paths import DATA_DIR as LEANMILL_DATA_DIR

DEFAULT_OUT = str(Path(LEANMILL_DATA_DIR) / "leanmill_handoff_integrity_gate.json")
DEFAULT_CANARY_CACHE_DIR = "/tmp/rung1/leanmill_canary_result_cache"
OPEN = {"queued", "claimed", "running"}
TERMINAL = {"done", "failed", "retired", "dead_letter"}
OPERATIONAL_CACHE_MARKERS = {"KeyboardInterrupt", "SystemExit"}


def _payload(row: sqlite3.Row) -> dict[str, Any]:
    try:
        obj = json.loads(row["payload_json"] or "{}")
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _read_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return {}
    try:
        obj = json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_", ":"} else "_" for ch in value).strip("_") or "item"


def _regovern_work_id(work_id: str) -> str:
    return f"post_probe_regovern:{_slug(work_id)}"


def _int_count(obj: dict[str, Any], key: str) -> int:
    try:
        return int(obj.get(key) or 0)
    except (TypeError, ValueError):
        return 0


def _governed_family_spec_payload(payload: dict[str, Any]) -> bool:
    if str(payload.get("probe_lane") or "") != "family_spec":
        return True
    return bool(payload.get("governance_required")) and bool(payload.get("govern_winners"))


def _scoreboard_counts(payload: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key in (
        "compile_candidate_count",
        "ratified_closure_count",
        "negative_control_fail_count",
        "negative_control_unexpected_pass_count",
        "exact_gap_candidate_count",
        "valid_falsifier_count",
    ):
        value = _int_count(payload, key)
        if value:
            counts[key] = value
    scoreboard = _read_json(str(payload.get("scoreboard") or ""))
    for key in (
        "compile_candidate_count",
        "ratified_closure_count",
        "negative_control_fail_count",
        "negative_control_unexpected_pass_count",
        "exact_gap_candidate_count",
        "valid_falsifier_count",
    ):
        value = _int_count(scoreboard, key)
        if value:
            counts[key] = value
    return counts


def _profile_section(policy_path: str | Path, profile: str, section: str) -> dict[str, Any]:
    obj = read_policy(policy_path)
    values = (((obj.get("profiles") or {}).get(profile) or {}).get(section) or {})
    return values if isinstance(values, dict) else {}


def _family_spec_probe_expected_policy(args: argparse.Namespace) -> dict[str, Any]:
    return _profile_section(args.factory_policy, args.policy_profile, "probe_worker")


def _scoreboard_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return _read_json(str(payload.get("scoreboard") or ""))


def _family_spec_scoreboard_warm(payload: dict[str, Any]) -> bool | None:
    scoreboard = _scoreboard_payload(payload)
    if "warm" in scoreboard:
        return bool(scoreboard.get("warm"))
    if "warm_repl_inline" in scoreboard:
        return bool(scoreboard.get("warm_repl_inline"))
    return None


def _family_spec_batch_row_coverage(payload: dict[str, Any]) -> dict[str, Any] | None:
    if str(payload.get("probe_lane") or "") != "family_spec":
        return None
    shard = payload.get("family_spec_shard") or {}
    if not isinstance(shard, dict) or shard.get("mode") != "rows":
        return None
    expected = [str(x) for x in (shard.get("row_ids") or []) if str(x)]
    if not expected:
        return None
    outcomes = payload.get("row_outcomes")
    if not isinstance(outcomes, list):
        outcomes = (_scoreboard_payload(payload).get("row_outcomes") or [])
    seen = {
        str(row.get("row_id") or "")
        for row in outcomes
        if isinstance(row, dict) and str(row.get("row_id") or "")
    }
    missing = [row_id for row_id in expected if row_id not in seen]
    if not missing:
        return None
    return {
        "expected_row_count": len(expected),
        "observed_row_count": len(seen),
        "missing_row_ids": missing[:20],
    }


def _payload_covers_family_row(payload: dict[str, Any], family: str, row_id: str) -> bool:
    if str(payload.get("probe_lane") or "") != "family_spec":
        return False
    if str(payload.get("family") or "") != family:
        return False
    outcomes = payload.get("row_outcomes")
    if not isinstance(outcomes, list):
        outcomes = (_scoreboard_payload(payload).get("row_outcomes") or [])
    for outcome in outcomes:
        if isinstance(outcome, dict) and str(outcome.get("row_id") or "") == row_id:
            return True
    shard = payload.get("family_spec_shard") or {}
    if isinstance(shard, dict) and str(shard.get("row_id") or "") == row_id and payload.get("learning_unit_exit"):
        return True
    return False


def _family_row_terminal_evidence(
    cx: sqlite3.Connection,
    *,
    family: str,
    row_id: str,
    min_updated_at: int,
    exclude_work_id: str,
) -> str:
    for row in cx.execute(
        """
        SELECT work_id, payload_json FROM work_items
        WHERE kind='repair_canary_probe'
          AND status IN ('done','retired','dead_letter')
          AND updated_at >= ?
          AND work_id != ?
        ORDER BY updated_at DESC
        LIMIT 200
        """,
        (int(min_updated_at), exclude_work_id),
    ):
        payload = _payload(row)
        if _payload_covers_family_row(payload, family, row_id):
            return str(row["work_id"] or "")
    return ""


def _closed_governance_summary(root: str) -> dict[str, Any]:
    out = {
        "closed_candidate_count": 0,
        "missing_governance_count": 0,
        "untyped_governance_rejection_count": 0,
        "ratified_count": 0,
        "reason_counts": {},
        "examples": [],
    }
    rows_dir = Path(root) / "rows" if root else Path("__missing__")
    for path in sorted(rows_dir.glob("*.json")) if rows_dir.exists() else []:
        obj = _read_json(path)
        for rec in obj.get("results") or []:
            if not isinstance(rec, dict) or not rec.get("closed"):
                continue
            out["closed_candidate_count"] += 1
            governance = rec.get("governance")
            if not isinstance(governance, dict) or not governance:
                out["missing_governance_count"] += 1
                reason = "missing_governance"
            else:
                verdict = str(governance.get("verdict") or "")
                reason = str(governance.get("reason") or verdict or "")
                if verdict == "closure":
                    out["ratified_count"] += 1
                elif not reason:
                    out["untyped_governance_rejection_count"] += 1
                    reason = "untyped_governance_rejection"
            out["reason_counts"][reason] = int(out["reason_counts"].get(reason, 0)) + 1
            if len(out["examples"]) < 8:
                out["examples"].append({
                    "result_path": str(path),
                    "candidate": rec.get("candidate"),
                    "governance": governance if isinstance(governance, dict) else None,
                })
    return out


def _work_exists(cx: sqlite3.Connection, work_id: str) -> bool:
    return cx.execute("SELECT 1 FROM work_items WHERE work_id=? LIMIT 1", (work_id,)).fetchone() is not None


def _operational_failure_cache_entries(cache_dir: str | Path, *, limit: int = 12) -> dict[str, Any]:
    root = Path(cache_dir)
    out = {"cache_dir": str(root), "count": 0, "examples": []}
    if not root.exists() or not root.is_dir():
        return out
    for path in sorted(root.glob("*.json")):
        obj = _read_json(path)
        if not obj:
            continue
        text = json.dumps(obj, sort_keys=True)[:20000]
        bad = bool(obj.get("worker_exception") or obj.get("worker_missing_result") or obj.get("outer_wall_timeout"))
        bad = bad or any(marker in text for marker in OPERATIONAL_CACHE_MARKERS)
        if not bad:
            continue
        out["count"] += 1
        if len(out["examples"]) < limit:
            out["examples"].append({
                "path": str(path),
                "worker_exception": obj.get("worker_exception"),
                "outer_wall_timeout": bool(obj.get("outer_wall_timeout")),
                "worker_missing_result": bool(obj.get("worker_missing_result")),
            })
    return out


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    cx = work_queue.connect(args.queue_db)
    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    probe_policy = _family_spec_probe_expected_policy(args)

    open_family_missing = []
    for row in cx.execute("SELECT * FROM work_items WHERE kind='repair_canary_probe' AND status IN ('queued','claimed','running')"):
        payload = _payload(row)
        if not _governed_family_spec_payload(payload):
            open_family_missing.append({"work_id": row["work_id"], "status": row["status"], "family": row["family"] or payload.get("family")})
    if open_family_missing:
        failures.append({
            "class": "family_spec_probe_missing_governance_requirement",
            "count": len(open_family_missing),
            "examples": open_family_missing[:10],
        })

    if bool(probe_policy.get("warm_repl_inline")):
        open_family_cold_payload = []
        for row in cx.execute("SELECT * FROM work_items WHERE kind='repair_canary_probe' AND status IN ('queued','claimed','running')"):
            payload = _payload(row)
            if str(payload.get("probe_lane") or "") != "family_spec":
                continue
            if not bool(payload.get("warm_repl_inline")):
                open_family_cold_payload.append({
                    "work_id": row["work_id"],
                    "status": row["status"],
                    "family": row["family"] or payload.get("family"),
                })
        if open_family_cold_payload:
            warnings.append({
                "class": "family_spec_probe_open_payload_not_warm_policy_aligned",
                "count": len(open_family_cold_payload),
                "examples": open_family_cold_payload[:10],
                "why": "queued payloads should be regenerated under policy; current probe workers may override true, but stale payloads should not persist",
            })

    queued_fresh_probe_max = cx.execute(
        """
        SELECT max(priority) AS max_priority FROM work_items
        WHERE kind='repair_canary_probe'
          AND status='queued'
          AND work_id NOT LIKE 'post_probe_regovern:%'
        """
    ).fetchone()["max_priority"]
    queued_regovernance_low_priority = []
    if queued_fresh_probe_max is not None:
        for row in cx.execute(
            """
            SELECT work_id, status, priority, family FROM work_items
            WHERE kind='repair_canary_probe'
              AND status='queued'
              AND work_id LIKE 'post_probe_regovern:%'
              AND priority <= ?
            ORDER BY priority ASC, created_at ASC
            LIMIT 20
            """,
            (int(queued_fresh_probe_max),),
        ):
            queued_regovernance_low_priority.append({
                "work_id": row["work_id"],
                "status": row["status"],
                "priority": row["priority"],
                "fresh_probe_max_priority": int(queued_fresh_probe_max),
                "family": row["family"],
            })
    if queued_regovernance_low_priority:
        failures.append({
            "class": "regovernance_rescue_priority_below_fresh_probe",
            "count": len(queued_regovernance_low_priority),
            "examples": queued_regovernance_low_priority[:10],
        })

    compile_missing_without_rescue = []
    compile_missing_with_rescue = []
    untyped_rejections = []
    compile_rejected = []
    threshold = int(time.time()) - max(0, int(args.window_s))
    for row in cx.execute("SELECT * FROM work_items WHERE kind='repair_canary_probe' AND status IN ('done','failed') AND updated_at >= ?", (threshold,)):
        payload = _payload(row)
        counts = _scoreboard_counts(payload)
        if _int_count(counts, "compile_candidate_count") <= 0:
            continue
        summary = _closed_governance_summary(str(payload.get("root") or ""))
        if int(summary.get("missing_governance_count") or 0) > 0:
            missing_rec = {
                "work_id": row["work_id"],
                "family": row["family"] or payload.get("family"),
                "missing_governance_count": summary.get("missing_governance_count"),
                "expected_regovern_work_id": _regovern_work_id(str(row["work_id"])),
                "examples": summary.get("examples", [])[:3],
            }
            if _work_exists(cx, _regovern_work_id(str(row["work_id"]))):
                compile_missing_with_rescue.append(missing_rec)
            else:
                compile_missing_without_rescue.append(missing_rec)
        if int(summary.get("untyped_governance_rejection_count") or 0) > 0:
            untyped_rejections.append({"work_id": row["work_id"], "summary": summary})
        typed_reasons = {
            str(k): int(v or 0)
            for k, v in (summary.get("reason_counts") or {}).items()
            if str(k) not in {"missing_governance", ""}
        }
        if typed_reasons and int(summary.get("ratified_count") or 0) == 0:
            compile_rejected.append({
                "work_id": row["work_id"],
                "family": row["family"] or payload.get("family"),
                "reason_counts": typed_reasons,
            })
    if compile_missing_without_rescue:
        failures.append({
            "class": "compile_candidate_missing_governance_without_rescue",
            "count": len(compile_missing_without_rescue),
            "examples": compile_missing_without_rescue[:10],
        })
    if untyped_rejections:
        failures.append({
            "class": "compile_candidate_untyped_governance_rejection",
            "count": len(untyped_rejections),
            "examples": untyped_rejections[:10],
        })
    if compile_missing_with_rescue:
        warnings.append({
            "class": "historical_compile_candidate_missing_governance_rescued",
            "count": len(compile_missing_with_rescue),
            "examples": compile_missing_with_rescue[:10],
        })
    if compile_rejected:
        warnings.append({
            "class": "compile_candidate_governance_rejections_present",
            "count": len(compile_rejected),
            "examples": compile_rejected[:10],
        })

    if bool(probe_policy.get("warm_repl_inline")):
        terminal_cold = []
        for row in cx.execute("SELECT * FROM work_items WHERE kind='repair_canary_probe' AND status='done' AND updated_at >= ?", (threshold,)):
            payload = _payload(row)
            if str(payload.get("probe_lane") or "") != "family_spec":
                continue
            warm = _family_spec_scoreboard_warm(payload)
            if warm is False:
                terminal_cold.append({
                    "work_id": row["work_id"],
                    "family": row["family"] or payload.get("family"),
                    "scoreboard": payload.get("scoreboard"),
                })
        if terminal_cold:
            warnings.append({
                "class": "family_spec_probe_completed_without_warm_repl_policy",
                "count": len(terminal_cold),
                "examples": terminal_cold[:10],
                "why": "speed-policy drift affects throughput/accounting, not proof correctness; regenerate stale work but do not treat it as proof-governance failure",
            })

    incomplete_batched = []
    compensated_batched = []
    for row in cx.execute("SELECT * FROM work_items WHERE kind='repair_canary_probe' AND status='done' AND updated_at >= ?", (threshold,)):
        payload = _payload(row)
        coverage = _family_spec_batch_row_coverage(payload)
        if not coverage:
            continue
        family = str(row["family"] or payload.get("family") or "")
        compensated = {}
        uncompensated = []
        for row_id in coverage.get("missing_row_ids") or []:
            evidence_work_id = _family_row_terminal_evidence(
                cx,
                family=family,
                row_id=str(row_id),
                min_updated_at=int(row["updated_at"] or 0),
                exclude_work_id=str(row["work_id"] or ""),
            )
            if evidence_work_id:
                compensated[str(row_id)] = evidence_work_id
            else:
                uncompensated.append(str(row_id))
        coverage.update({
            "work_id": row["work_id"],
            "family": family,
            "scoreboard": payload.get("scoreboard"),
            "compensated_row_ids": compensated,
            "missing_row_ids": uncompensated,
        })
        if uncompensated:
            incomplete_batched.append(coverage)
        else:
            compensated_batched.append(coverage)
    if incomplete_batched:
        failures.append({
            "class": "family_spec_batched_probe_missing_row_outcomes",
            "count": len(incomplete_batched),
            "examples": incomplete_batched[:10],
        })
    if compensated_batched:
        warnings.append({
            "class": "historical_family_spec_batched_probe_missing_rows_compensated",
            "count": len(compensated_batched),
            "examples": compensated_batched[:10],
        })

    source_binding_followups = [
        {"work_id": row["work_id"], "kind": row["kind"], "status": row["status"]}
        for row in cx.execute(
            """
            SELECT work_id, kind, status FROM work_items
            WHERE status IN ('queued','claimed','running')
              AND work_id LIKE 'post_probe_gap_triage:probe:source_binding:%'
            LIMIT 20
            """
        )
    ]
    if source_binding_followups:
        failures.append({
            "class": "source_binding_no_signal_followups_open_while_paused",
            "count": len(source_binding_followups),
            "examples": source_binding_followups,
        })

    bad_cache = _operational_failure_cache_entries(args.canary_cache_dir)
    if int(bad_cache.get("count") or 0) > 0:
        failures.append({
            "class": "operational_failure_canary_cache_entries_present",
            "count": bad_cache.get("count"),
            "cache_dir": bad_cache.get("cache_dir"),
            "examples": bad_cache.get("examples", []),
            "why": "worker exceptions/timeouts/interrupted runs must be retried, not replayed from cache as no-signal proof outcomes",
        })

    dead_letters = int(cx.execute("SELECT count(*) c FROM work_items WHERE status='dead_letter'").fetchone()["c"])
    if dead_letters:
        failures.append({"class": "dead_letters_present", "count": dead_letters})

    health = work_queue.worker_version_health(cx, stale_after_s=args.worker_heartbeat_stale_s, policy_profile=args.policy_profile)
    if int(health.get("stale_process_count") or 0) or int(health.get("runtime_mismatch_count") or 0):
        failures.append({
            "class": "runtime_version_health_failed",
            "stale_process_count": health.get("stale_process_count"),
            "runtime_mismatch_count": health.get("runtime_mismatch_count"),
            "stale_processes": (health.get("stale_processes") or [])[:5],
            "runtime_mismatches": (health.get("runtime_mismatches") or [])[:5],
        })

    out = {
        "schema": "leanmill-handoff-integrity-gate-v1",
        "generated_at_epoch": int(time.time()),
        "status": "fail" if failures else "pass",
        "failure_count": len(failures),
        "warning_count": len(warnings),
        "failures": failures,
        "warnings": warnings,
        "window_s": int(args.window_s),
        "policy_profile": args.policy_profile,
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    return out


def _self_test() -> int:
    import tempfile

    assert _regovern_work_id("probe:a/b") == "post_probe_regovern:probe:a_b"
    assert _governed_family_spec_payload({"probe_lane": "legacy"})
    assert _governed_family_spec_payload({"probe_lane": "family_spec", "governance_required": True, "govern_winners": True})
    assert not _governed_family_spec_payload({"probe_lane": "family_spec", "govern_winners": True})
    assert _family_spec_scoreboard_warm({"scoreboard": ""}) is None
    assert _family_spec_batch_row_coverage({
        "probe_lane": "family_spec",
        "family_spec_shard": {"mode": "rows", "row_ids": ["r1", "r2"]},
        "row_outcomes": [{"row_id": "r1"}],
    })["missing_row_ids"] == ["r2"]
    assert _family_spec_batch_row_coverage({
        "probe_lane": "family_spec",
        "family_spec_shard": {"mode": "rows", "row_ids": ["r1"]},
        "row_outcomes": [{"row_id": "r1"}],
    }) is None
    assert _payload_covers_family_row({
        "probe_lane": "family_spec",
        "family": "fam",
        "family_spec_shard": {"mode": "row", "row_id": "r1"},
        "learning_unit_exit": "tested_no_positive_signal",
    }, "fam", "r1")
    with tempfile.TemporaryDirectory(prefix="leanmill_handoff_cache_") as td:
        root = Path(td)
        (root / "good.json").write_text(json.dumps({"n_closed": 0, "results": [{"error_class": "lean_error"}]}) + "\n")
        assert _operational_failure_cache_entries(root)["count"] == 0
        (root / "bad.json").write_text(json.dumps({"worker_exception": "KeyboardInterrupt()"}) + "\n")
        bad = _operational_failure_cache_entries(root)
        assert bad["count"] == 1 and bad["examples"]
    print("leanmill_handoff_integrity_gate self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-db", default=work_queue.DEFAULT_DB)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--window-s", type=int, default=6 * 3600)
    ap.add_argument("--factory-policy", default=FACTORY_POLICY)
    ap.add_argument("--policy-profile", default="supervised_24x7")
    ap.add_argument("--worker-heartbeat-stale-s", type=int, default=900)
    ap.add_argument("--canary-cache-dir", default=DEFAULT_CANARY_CACHE_DIR)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    out = evaluate(args)
    print(json.dumps({"status": out["status"], "failure_count": out["failure_count"], "warning_count": out["warning_count"], "out": args.out}, sort_keys=True))
    return 0 if out["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
