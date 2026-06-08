#!/usr/bin/env python3
"""Build a no-call dispatch-readiness packet for GP-245 Law 1.

This validates the existing anti-bias-collapse smoke slate and reports the
exact DB rows still missing before the minimal smoke can be scored. It does not
dispatch models and does not mutate the DB.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_WORKSPACE = REPO / "projects/llm_forecasting_calibration_program/anti_bias_collapse_v1/workspace"
DEFAULT_SMOKE_SLATE = DEFAULT_WORKSPACE / "anti_bias_collapse_smoke_slate.jsonl"
DEFAULT_CALLS = DEFAULT_WORKSPACE / "anti_bias_collapse_v1_calls.jsonl"
DEFAULT_QUEUE = DEFAULT_WORKSPACE / "anti_bias_collapse_dispatch_queue.jsonl"
DEFAULT_OUT = DEFAULT_WORKSPACE
DEFAULT_FAMILIES = ("claude", "codex_54mini", "gemini")
PILOT_ID = "anti_bias_collapse_v1"


REQUIRED_ROW_KEYS = {
    "schema",
    "pilot_id",
    "primitive",
    "bias_id",
    "bias_class_preregistered",
    "event_id",
    "event_core",
    "frame",
    "prompt_arm",
    "g0",
    "prompt",
    "db_contract_id",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise SystemExit(f"{path}:{line_no}: expected JSON object")
        out.append(row)
    return out


def db_counts(db: Path) -> dict[str, Any]:
    if not db.exists():
        return {
            "db": str(db),
            "exists": False,
            "contracts": None,
            "pilot_runs": None,
            "pilot_calls": None,
            "families": [],
        }
    con = sqlite3.connect(db)
    try:
        contracts = con.execute(
            "SELECT COUNT(*) FROM contracts WHERE source_corpus = ? OR contract_id LIKE 'abc_v1_%'",
            (PILOT_ID,),
        ).fetchone()[0]
        pilot_runs = con.execute(
            "SELECT COUNT(*) FROM pilot_runs WHERE pilot_id = ?",
            (PILOT_ID,),
        ).fetchone()[0]
        pilot_calls = con.execute(
            "SELECT COUNT(*) FROM pilot_calls WHERE pilot_id = ?",
            (PILOT_ID,),
        ).fetchone()[0]
        families = [
            str(row[0])
            for row in con.execute(
                """
                SELECT DISTINCT family
                FROM pilot_calls
                WHERE pilot_id = ?
                  AND family IS NOT NULL
                ORDER BY family
                """,
                (PILOT_ID,),
            )
        ]
    finally:
        con.close()
    return {
        "db": str(db),
        "exists": True,
        "contracts": int(contracts),
        "pilot_runs": int(pilot_runs),
        "pilot_calls": int(pilot_calls),
        "families": families,
    }


def validate_slate(rows: list[dict[str, Any]], families: tuple[str, ...]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    missing_key_rows: list[dict[str, Any]] = []
    by_bias = Counter(str(row.get("bias_id")) for row in rows)
    by_class = Counter(str(row.get("bias_class_preregistered")) for row in rows)
    by_frame = Counter(str(row.get("frame")) for row in rows)
    by_arm = Counter(str(row.get("prompt_arm")) for row in rows)
    unique_contracts = {(row.get("bias_id"), row.get("event_id"), row.get("frame")) for row in rows}
    unique_bias_events = {(row.get("bias_id"), row.get("event_id")) for row in rows}

    for idx, row in enumerate(rows, 1):
        missing = sorted(k for k in REQUIRED_ROW_KEYS if k not in row or row.get(k) in (None, ""))
        if missing:
            missing_key_rows.append({"row": idx, "missing": missing})
        if row.get("pilot_id") != PILOT_ID:
            errors.append(f"row {idx}: pilot_id != {PILOT_ID}")
        if row.get("primitive") != PILOT_ID:
            errors.append(f"row {idx}: primitive != {PILOT_ID}")
        if row.get("frame") not in {"A", "B"}:
            errors.append(f"row {idx}: frame must be A or B")
        if row.get("prompt_arm") not in {"normal", "anti_bias_correction"}:
            errors.append(f"row {idx}: prompt_arm must be normal or anti_bias_correction")
        if "Do NOT use web search" not in str(row.get("prompt", "")):
            warnings.append(f"row {idx}: prompt lacks explicit no-web instruction")
        if "Reply with ONLY a JSON object" not in str(row.get("prompt", "")):
            warnings.append(f"row {idx}: prompt lacks JSON-only instruction")

    if missing_key_rows:
        errors.append(f"{len(missing_key_rows)} rows are missing required keys")
    if len(rows) != 60:
        errors.append(f"expected 60 smoke prompt surfaces, found {len(rows)}")
    if len(unique_contracts) != 30:
        errors.append(f"expected 30 unique contracts, found {len(unique_contracts)}")
    if len(unique_bias_events) != 15:
        errors.append(f"expected 15 unique bias-events, found {len(unique_bias_events)}")
    if set(by_frame) != {"A", "B"} or any(count != 30 for count in by_frame.values()):
        errors.append(f"expected balanced frames A/B at 30 each, found {dict(by_frame)}")
    if set(by_arm) != {"normal", "anti_bias_correction"} or any(count != 30 for count in by_arm.values()):
        errors.append(f"expected balanced prompt arms at 30 each, found {dict(by_arm)}")

    expected_biases = {"F_status_quo", "S_social_proof", "K_availability_control"}
    if set(by_bias) != expected_biases:
        errors.append(f"expected smoke biases {sorted(expected_biases)}, found {sorted(by_bias)}")
    for bias_id in expected_biases:
        if by_bias[bias_id] != 20:
            errors.append(f"expected 20 rows for {bias_id}, found {by_bias[bias_id]}")
    if by_class["INHERIT_CONTROL"] == 0:
        errors.append("missing INHERIT_CONTROL class")
    if not any(str(label).startswith("MIMIC") for label in by_class):
        errors.append("missing MIMIC class")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "row_count": len(rows),
        "unique_contracts": len(unique_contracts),
        "unique_bias_events": len(unique_bias_events),
        "bias_counts": dict(sorted(by_bias.items())),
        "class_counts": dict(sorted(by_class.items())),
        "frame_counts": dict(sorted(by_frame.items())),
        "prompt_arm_counts": dict(sorted(by_arm.items())),
        "dispatch_families": list(families),
        "expected_calls": len(rows) * len(families),
        "expected_contract_rows": len(unique_contracts),
        "expected_pilot_runs": 1,
        "missing_key_examples": missing_key_rows[:5],
    }


def make_dispatch_id(row: dict[str, Any], family: str) -> str:
    return f"{row.get('db_contract_id')}::{row.get('prompt_arm')}::{family}"


def runtime_for_family(family: str) -> str:
    if family == "claude":
        return "claude_subscription"
    if family.startswith("codex"):
        return "codex_subscription"
    if family == "gemini":
        return "gemini_api_or_manual"
    return "manual"


def build_dispatch_queue(rows: list[dict[str, Any]], families: tuple[str, ...]) -> list[dict[str, Any]]:
    queue: list[dict[str, Any]] = []
    for row in rows:
        for family in families:
            queue.append(
                {
                    "schema": "gp245-anti-bias-collapse-dispatch-queue-v1",
                    "pilot_id": PILOT_ID,
                    "dispatch_id": make_dispatch_id(row, family),
                    "family": family,
                    "agent_id": f"{family}_anti_bias_collapse_v1",
                    "runtime_route": runtime_for_family(family),
                    "db_contract_id": row.get("db_contract_id"),
                    "bias_id": row.get("bias_id"),
                    "bias_class_preregistered": row.get("bias_class_preregistered"),
                    "event_id": row.get("event_id"),
                    "event_core": row.get("event_core"),
                    "frame": row.get("frame"),
                    "prompt_arm": row.get("prompt_arm"),
                    "g0": row.get("g0"),
                    "normative_gap_direction": row.get("normative_gap_direction"),
                    "predicted_cell": row.get("predicted_cell"),
                    "source_finding_ids": row.get("source_finding_ids"),
                    "prompt": row.get("prompt"),
                    "required_receipt_fields": [
                        "dispatch_id",
                        "family",
                        "agent_id",
                        "db_contract_id",
                        "p_success",
                        "schema_ok",
                        "parsed",
                        "raw_response",
                        "fired_at",
                    ],
                }
            )
    return queue


def expected_dispatch_ids(rows: list[dict[str, Any]], families: tuple[str, ...]) -> set[str]:
    return {make_dispatch_id(row, family) for row in rows for family in families}


def call_dispatch_id(row: dict[str, Any]) -> str | None:
    parsed = row.get("parsed") if isinstance(row.get("parsed"), dict) else {}
    dispatch_id = row.get("dispatch_id") or parsed.get("dispatch_id")
    if dispatch_id:
        return str(dispatch_id)
    contract_id = row.get("db_contract_id") or row.get("contract_id") or parsed.get("db_contract_id") or parsed.get("contract_id")
    prompt_arm = row.get("prompt_arm") or parsed.get("prompt_arm")
    family = row.get("family") or parsed.get("family") or row.get("agent_id") or row.get("model")
    if contract_id and prompt_arm and family:
        return f"{contract_id}::{prompt_arm}::{family}"
    return None


def validate_calls_receipt(path: Path, families: tuple[str, ...], expected_ids: set[str]) -> dict[str, Any]:
    rows = load_jsonl(path)
    if not rows:
        return {
            "path": str(path),
            "exists": path.exists(),
            "row_count": 0,
            "ready_for_ingest": False,
            "message": "No call receipt yet. Dispatch smoke rows first.",
        }
    by_family = Counter(str(row.get("family") or row.get("agent_id") or row.get("model")) for row in rows)
    bad: list[str] = []
    seen: Counter[str] = Counter()
    for idx, row in enumerate(rows, 1):
        parsed = row.get("parsed") if isinstance(row.get("parsed"), dict) else row
        p = row.get("p_success", parsed.get("p_success") if isinstance(parsed, dict) else None)
        if not isinstance(p, (int, float)):
            bad.append(f"row {idx}: missing numeric p_success")
        elif not (0.0 <= float(p) <= 1.0):
            bad.append(f"row {idx}: p_success outside [0,1]")
        for key in ("bias_id", "event_id", "frame", "prompt_arm"):
            if row.get(key) is None and (not isinstance(parsed, dict) or parsed.get(key) is None):
                bad.append(f"row {idx}: missing {key}")
        dispatch_id = call_dispatch_id(row)
        if not dispatch_id:
            bad.append(f"row {idx}: cannot derive dispatch_id")
            continue
        seen[dispatch_id] += 1
    missing = sorted(expected_ids - set(seen))
    extra = sorted(set(seen) - expected_ids)
    duplicates = sorted(dispatch_id for dispatch_id, count in seen.items() if count > 1)
    if missing:
        bad.append(f"missing {len(missing)} expected dispatch rows")
    if extra:
        bad.append(f"found {len(extra)} unexpected dispatch rows")
    if duplicates:
        bad.append(f"found {len(duplicates)} duplicate dispatch rows")
    return {
        "path": str(path),
        "exists": True,
        "row_count": len(rows),
        "family_counts": dict(sorted(by_family.items())),
        "expected_families": list(families),
        "expected_row_count": len(expected_ids),
        "matched_dispatch_rows": len(set(seen) & expected_ids),
        "missing_dispatch_rows": len(missing),
        "unexpected_dispatch_rows": len(extra),
        "duplicate_dispatch_rows": len(duplicates),
        "missing_examples": missing[:10],
        "unexpected_examples": extra[:10],
        "duplicate_examples": duplicates[:10],
        "ready_for_ingest": not bad,
        "errors": bad[:20],
    }


def build_packet(
    *,
    db: Path,
    smoke_slate: Path,
    calls: Path,
    queue_path: Path,
    families: tuple[str, ...],
) -> dict[str, Any]:
    rows = load_jsonl(smoke_slate)
    slate = validate_slate(rows, families)
    queue = build_dispatch_queue(rows, families)
    expected_ids = expected_dispatch_ids(rows, families)
    counts = db_counts(db)
    calls_receipt = validate_calls_receipt(calls, families, expected_ids)
    expected_contracts = slate.get("expected_contract_rows") or 0
    expected_calls = slate.get("expected_calls") or 0
    missing = {
        "contracts": max(int(expected_contracts) - int(counts.get("contracts") or 0), 0),
        "pilot_runs": max(1 - int(counts.get("pilot_runs") or 0), 0),
        "pilot_calls": max(int(expected_calls) - int(counts.get("pilot_calls") or 0), 0),
    }
    ready_for_dispatch = bool(slate["ok"]) and int(counts.get("pilot_calls") or 0) == 0
    ready_for_scoring = int(counts.get("pilot_calls") or 0) >= int(expected_calls)
    return {
        "schema": "gp245-anti-bias-collapse-dispatch-packet-v1",
        "pilot_id": PILOT_ID,
        "db": str(db),
        "smoke_slate": str(smoke_slate),
        "dispatch_queue": str(queue_path),
        "calls_receipt": str(calls),
        "families": list(families),
        "slate_validation": slate,
        "dispatch_queue_summary": {
            "row_count": len(queue),
            "expected_dispatch_ids": len(expected_ids),
            "runtime_route_counts": dict(sorted(Counter(row["runtime_route"] for row in queue).items())),
        },
        "db_state": counts,
        "calls_receipt_validation": calls_receipt,
        "missing_for_minimal_smoke": missing,
        "ready_for_dispatch": ready_for_dispatch,
        "ready_for_ingest": bool(calls_receipt.get("ready_for_ingest")),
        "ready_for_scoring": ready_for_scoring,
        "strongest_falsifier": [
            "MIMIC collapse is not greater than INHERIT_CONTROL collapse.",
            "The apparent collapse is explained by raw normal-arm gap size.",
            "Family order does not track the F107 alignment-damping axis.",
        ],
        "do_not_repeat": [
            "generic OOD bias slate",
            "status-quo/loss-frame replication",
            "five-family panel before the 180-call smoke",
            "generic worry-vs-Brier",
            "cutoff model calls before matched pre/post metadata",
        ],
        "next_commands_after_dispatch": [
            "./venv/bin/python -m src.ztare.cli forecast anti-bias-dispatch --out-dir projects/llm_forecasting_calibration_program/anti_bias_collapse_v1/workspace",
            "./venv/bin/python projects/llm_forecasting_calibration_program/tools/ingest_nonstandard_ledgers.py",
            "./venv/bin/python projects/llm_forecasting_calibration_program/tools/anti_bias_collapse_score.py --out-dir projects/llm_forecasting_calibration_program/anti_bias_collapse_v1/workspace",
            "./venv/bin/python projects/llm_forecasting_calibration_program/tools/law_readiness_report.py --out-dir projects/llm_forecasting_calibration_program/law_validation_v1/workspace",
        ],
    }


def write_outputs(packet: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "anti_bias_collapse_dispatch_packet.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = ["# Anti-Bias-Collapse Dispatch Packet", ""]
    lines.append(f"- Pilot: `{packet['pilot_id']}`")
    lines.append(f"- Ready for dispatch: `{packet['ready_for_dispatch']}`")
    lines.append(f"- Ready for ingest: `{packet['ready_for_ingest']}`")
    lines.append(f"- Ready for scoring: `{packet['ready_for_scoring']}`")
    lines.append(f"- Families: `{', '.join(packet['families'])}`")
    slate = packet["slate_validation"]
    lines.append(f"- Smoke prompt surfaces: `{slate['row_count']}`")
    lines.append(f"- Expected calls: `{slate['expected_calls']}`")
    lines.append(f"- Unique contracts: `{slate['unique_contracts']}`")
    lines.append(f"- Dispatch queue rows: `{packet['dispatch_queue_summary']['row_count']}`")
    lines.append("")
    lines.append("## Slate Validation")
    lines.append("")
    lines.append(f"- OK: `{slate['ok']}`")
    lines.append(f"- Bias counts: `{slate['bias_counts']}`")
    lines.append(f"- Class counts: `{slate['class_counts']}`")
    lines.append(f"- Frame counts: `{slate['frame_counts']}`")
    lines.append(f"- Prompt-arm counts: `{slate['prompt_arm_counts']}`")
    if slate["errors"]:
        lines.append("- Errors:")
        for err in slate["errors"]:
            lines.append(f"  - {err}")
    if slate["warnings"]:
        lines.append("- Warnings:")
        for warning in slate["warnings"][:10]:
            lines.append(f"  - {warning}")
    lines.append("")
    lines.append("## DB Gap")
    lines.append("")
    lines.append(f"- Current DB state: `{packet['db_state']}`")
    lines.append(f"- Missing for minimal smoke: `{packet['missing_for_minimal_smoke']}`")
    lines.append("")
    lines.append("## Dispatch Queue")
    lines.append("")
    lines.append("Use this exact queue for model calls:")
    lines.append("")
    lines.append("```text")
    lines.append(packet["dispatch_queue"])
    lines.append("```")
    lines.append("")
    lines.append(f"- Runtime routes: `{packet['dispatch_queue_summary']['runtime_route_counts']}`")
    lines.append("")
    lines.append("## Strongest Falsifier")
    lines.append("")
    for item in packet["strongest_falsifier"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Do Not Repeat")
    lines.append("")
    for item in packet["do_not_repeat"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## After Dispatch")
    lines.append("")
    lines.append("Write call receipts to:")
    lines.append("")
    lines.append("```text")
    lines.append(packet["calls_receipt"])
    lines.append("```")
    lines.append("")
    lines.append("Then run:")
    lines.append("")
    lines.append("```bash")
    for command in packet["next_commands_after_dispatch"]:
        lines.append(command)
    lines.append("```")
    lines.append("")
    (out_dir / "anti_bias_collapse_dispatch_packet.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--smoke-slate", type=Path, default=DEFAULT_SMOKE_SLATE)
    parser.add_argument("--calls", type=Path, default=DEFAULT_CALLS)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--families", default=",".join(DEFAULT_FAMILIES))
    args = parser.parse_args()
    families = tuple(part.strip() for part in args.families.split(",") if part.strip())
    packet = build_packet(
        db=args.db,
        smoke_slate=args.smoke_slate,
        calls=args.calls,
        queue_path=args.queue,
        families=families,
    )
    rows = load_jsonl(args.smoke_slate)
    queue = build_dispatch_queue(rows, families)
    args.queue.parent.mkdir(parents=True, exist_ok=True)
    args.queue.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in queue) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(packet, indent=2, sort_keys=True))
    if args.out_dir:
        write_outputs(packet, args.out_dir)
    return 0 if packet["slate_validation"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
