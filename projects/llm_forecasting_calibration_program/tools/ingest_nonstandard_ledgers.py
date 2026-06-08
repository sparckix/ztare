#!/usr/bin/env python3
"""Ingest GP-245 nonstandard JSONL ledgers into forecaster_calibration.db.

The normal `ztare forecast calibration-db ingest-pilot` path handles
`pilot_*_calls*.jsonl`. Several later research games deliberately use clearer
filenames (`f106_*`, `f107_*`, `premium_*`, `f105_*`) and therefore need an
explicit mapping. This script keeps those runs queryable in the master DB
without pretending all of them are resolved binary forecasts.
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from anti_bias_collapse_dispatch_packet import (
    DEFAULT_FAMILIES as ANTI_BIAS_DEFAULT_FAMILIES,
    DEFAULT_QUEUE as ANTI_BIAS_DEFAULT_QUEUE,
    DEFAULT_SMOKE_SLATE as ANTI_BIAS_DEFAULT_SMOKE_SLATE,
    build_packet as build_anti_bias_dispatch_packet,
)


REPO = Path(__file__).resolve().parents[3]
DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
GP245_WS = REPO / "projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace"
F105_WS = REPO / "projects/llm_forecasting_calibration_program/llm_effort_estimation/workspace"
ANTI_BIAS_WS = REPO / "projects/llm_forecasting_calibration_program/anti_bias_collapse_v1/workspace"
PREMIUM_GT = Path("/tmp/premium_batch1_gt.json")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def family_of(agent_id: str | None, runtime: str | None = None, model: str | None = None) -> str | None:
    text = " ".join(str(x or "").lower() for x in (agent_id, runtime, model))
    if "claude" in text:
        return "claude"
    if "codex_55" in text or "gpt-5.5" in text or "gpt5.5" in text:
        return "codex_55"
    if "codex_54mini" in text or "gpt-5.4-mini" in text or "5.4-mini" in text:
        return "codex_54mini"
    if "codex_mini" in text:
        return "codex_54mini"
    if "gemini" in text:
        return "gemini"
    if "deepseek" in text:
        return "deepseek"
    return None


def canonical_family(value: str | None) -> str | None:
    if value == "codex":
        return "codex_55"
    if value == "codex_mini":
        return "codex_54mini"
    return value


def brier(p: float | None, y: int | None) -> float | None:
    if p is None or y is None:
        return None
    return (p - y) ** 2


def upsert_contract(
    con: sqlite3.Connection,
    *,
    contract_id: str,
    question: str,
    source: str,
    source_corpus: str,
    y_known: int | None,
    raw: dict[str, Any],
) -> None:
    existing = con.execute(
        "SELECT y_known FROM contracts WHERE contract_id = ?",
        (contract_id,),
    ).fetchone()
    if existing and existing[0] is not None and y_known is None:
        con.execute(
            "UPDATE contracts SET question = ?, raw_json = ? WHERE contract_id = ?",
            (question, json.dumps(raw, sort_keys=True), contract_id),
        )
        return
    con.execute(
        """
        INSERT OR REPLACE INTO contracts
          (contract_id, question, source, source_corpus, horizon, y_known,
           post_training_cutoff, task_type, external_market_open,
           resolution_source_url, y_known_provenance, raw_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            contract_id,
            question,
            source,
            source_corpus,
            raw.get("horizon"),
            y_known,
            raw.get("post_training_cutoff"),
            raw.get("task_type") or raw.get("experiment"),
            raw.get("external_market_open"),
            raw.get("resolution_source_url"),
            raw.get("y_known_provenance") or ("ledger_ground_truth" if y_known is not None else None),
            json.dumps(raw, sort_keys=True),
            datetime.now(timezone.utc).isoformat(),
        ),
    )


def replace_pilot_run(
    con: sqlite3.Connection,
    *,
    pilot_id: str,
    pilot_name: str,
    primitive: str,
    corpus: str,
    source_path: Path,
    n_calls: int,
    n_schema_ok: int,
) -> None:
    con.execute("DELETE FROM pilot_calls WHERE pilot_id = ?", (pilot_id,))
    con.execute("DELETE FROM pilot_runs WHERE pilot_id = ?", (pilot_id,))
    con.execute(
        """
        INSERT INTO pilot_runs
          (pilot_id, pilot_name, primitive, corpus, source_jsonl_path,
           fired_at, n_calls, n_schema_ok)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            pilot_id,
            pilot_name,
            primitive,
            corpus,
            str(source_path.relative_to(REPO)),
            datetime.now(timezone.utc).isoformat(),
            n_calls,
            n_schema_ok,
        ),
    )


def insert_call(
    con: sqlite3.Connection,
    *,
    pilot_id: str,
    contract_id: str,
    agent_id: str | None,
    family: str | None,
    condition: str | None,
    primitive: str,
    primitive_base: str,
    phase: str | None,
    p_success: float | None,
    y_known: int | None,
    schema_ok: bool,
    parsed: dict[str, Any],
    fired_at: str | None,
    raw: dict[str, Any],
) -> None:
    con.execute(
        """
        INSERT INTO pilot_calls
          (pilot_id, contract_id, agent_id, family, condition, primitive,
           primitive_base, phase, role, pair_id, p_success, brier,
           schema_ok, parsed_json, fired_at, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            pilot_id,
            contract_id,
            agent_id,
            family,
            condition,
            primitive,
            primitive_base,
            phase,
            None,
            raw.get("event_id") or raw.get("qid") or raw.get("task_id"),
            p_success,
            brier(p_success, y_known),
            1 if schema_ok else 0,
            json.dumps(parsed, sort_keys=True),
            fired_at,
            json.dumps(raw, sort_keys=True),
        ),
    )


def ingest_bias_panel(con: sqlite3.Connection, *, path: Path, pilot_id: str, primitive: str) -> dict[str, Any]:
    rows = load_jsonl(path)
    replace_pilot_run(
        con,
        pilot_id=pilot_id,
        pilot_name=path.stem,
        primitive=primitive,
        corpus="bias_inheritance_ood",
        source_path=path,
        n_calls=len(rows),
        n_schema_ok=sum(1 for row in rows if row.get("schema_ok") or (row.get("schema_audit") or {}).get("schema_ok")),
    )
    for row in rows:
        cid = row.get("contract_id") or f"{pilot_id}_{row.get('bias_id')}_{row.get('event_id')}_{row.get('framing')}"
        parsed = row.get("parsed") if isinstance(row.get("parsed"), dict) else {}
        p = row.get("p_success")
        if p is None:
            p = parsed.get("p_success")
        p = float(p) if isinstance(p, (int, float)) else None
        agent_id = row.get("agent_id")
        fam = family_of(agent_id, row.get("runtime"), row.get("model"))
        upsert_contract(
            con,
            contract_id=cid,
            question=f"{row.get('bias_name') or row.get('bias_id')} / {row.get('event_id')} / framing {row.get('framing')}",
            source="bias_inheritance_ood",
            source_corpus=pilot_id,
            y_known=None,
            raw=row,
        )
        insert_call(
            con,
            pilot_id=pilot_id,
            contract_id=cid,
            agent_id=agent_id,
            family=fam,
            condition=row.get("framing"),
            primitive=primitive,
            primitive_base=primitive,
            phase=row.get("mode"),
            p_success=p,
            y_known=None,
            schema_ok=bool(row.get("schema_ok") or (row.get("schema_audit") or {}).get("schema_ok")),
            parsed={**parsed, "predicted_cell": row.get("predicted_cell"), "g0": row.get("g0")},
            fired_at=row.get("fired_at"),
            raw=row,
        )
    return {"pilot_id": pilot_id, "rows": len(rows)}


def validate_anti_bias_collapse_receipt(path: Path) -> None:
    if not path.exists():
        return
    dispatch_packet = build_anti_bias_dispatch_packet(
        db=DB,
        smoke_slate=ANTI_BIAS_DEFAULT_SMOKE_SLATE,
        calls=path,
        queue_path=ANTI_BIAS_DEFAULT_QUEUE,
        families=ANTI_BIAS_DEFAULT_FAMILIES,
    )
    if not dispatch_packet.get("ready_for_ingest"):
        validation = dispatch_packet.get("calls_receipt_validation") or {}
        raise SystemExit(
            "anti_bias_collapse_v1 receipt is not ready for ingest; "
            "rerun `projects/llm_forecasting_calibration_program/tools/anti_bias_collapse_dispatch_packet.py` "
            "and fix errors: "
            f"{validation.get('errors') or validation}"
        )


def ingest_anti_bias_collapse(con: sqlite3.Connection, *, validate_receipt: bool = True) -> dict[str, Any]:
    path = ANTI_BIAS_WS / "anti_bias_collapse_v1_calls.jsonl"
    pilot_id = "anti_bias_collapse_v1"
    if not path.exists():
        return {"pilot_id": pilot_id, "rows": 0, "status": "missing"}
    if validate_receipt:
        validate_anti_bias_collapse_receipt(path)
    rows = load_jsonl(path)
    replace_pilot_run(
        con,
        pilot_id=pilot_id,
        pilot_name=path.stem,
        primitive="anti_bias_collapse_v1",
        corpus="bias_inheritance_ood",
        source_path=path,
        n_calls=len(rows),
        n_schema_ok=sum(1 for row in rows if row.get("schema_ok", True)),
    )
    for row in rows:
        parsed = row.get("parsed") if isinstance(row.get("parsed"), dict) else {}
        p = row.get("p_success")
        if p is None:
            p = parsed.get("p_success")
        p = float(p) if isinstance(p, (int, float)) else None
        bias_id = row.get("bias_id") or parsed.get("bias_id")
        event_id = row.get("event_id") or parsed.get("event_id")
        frame = row.get("frame") or parsed.get("frame")
        prompt_arm = row.get("prompt_arm") or parsed.get("prompt_arm")
        contract_id = row.get("contract_id") or row.get("db_contract_id") or f"abc_v1_{bias_id}_{event_id}_{frame}"
        agent_id = row.get("agent_id") or row.get("model") or row.get("family")
        family = canonical_family(row.get("family")) or family_of(agent_id, row.get("runtime"), row.get("model"))
        merged_parsed = {
            **parsed,
            "bias_id": bias_id,
            "event_id": event_id,
            "frame": frame,
            "prompt_arm": prompt_arm,
            "g0": row.get("g0", parsed.get("g0")),
            "bias_class_preregistered": row.get(
                "bias_class_preregistered",
                parsed.get("bias_class_preregistered"),
            ),
            "source_finding_ids": row.get("source_finding_ids"),
            "p_success": p,
        }
        question = row.get("event_core") or row.get("question") or f"{bias_id} / {event_id} / frame {frame}"
        upsert_contract(
            con,
            contract_id=contract_id,
            question=question,
            source="bias_inheritance_ood",
            source_corpus=pilot_id,
            y_known=None,
            raw=row,
        )
        insert_call(
            con,
            pilot_id=pilot_id,
            contract_id=contract_id,
            agent_id=agent_id,
            family=family,
            condition=frame,
            primitive="anti_bias_collapse_v1",
            primitive_base="anti_bias_collapse_v1",
            phase=prompt_arm,
            p_success=p,
            y_known=None,
            schema_ok=bool(row.get("schema_ok", p is not None)),
            parsed=merged_parsed,
            fired_at=row.get("fired_at"),
            raw=row,
        )
    return {"pilot_id": pilot_id, "rows": len(rows), "status": "ingested"}


def ingest_f105(con: sqlite3.Connection) -> dict[str, Any]:
    path = F105_WS / "f105_metacognition_smoke_n15_calls.jsonl"
    rows = load_jsonl(path)
    pilot_id = "f105_metacognition_smoke_n15"
    replace_pilot_run(
        con,
        pilot_id=pilot_id,
        pilot_name=path.stem,
        primitive="f105_metacognition",
        corpus="f105_objective_effort",
        source_path=path,
        n_calls=len(rows),
        n_schema_ok=sum(1 for row in rows if row.get("schema_ok")),
    )
    for row in rows:
        cid = f"f105_{row.get('task_id')}_{row.get('agent_id')}"
        y = row.get("ground_truth_y")
        y = int(y) if y is not None else None
        parsed = row.get("parsed") if isinstance(row.get("parsed"), dict) else {}
        lo = parsed.get("p_low")
        hi = parsed.get("p_high")
        p = None
        if isinstance(lo, (int, float)) and isinstance(hi, (int, float)):
            p = (float(lo) + float(hi)) / 2.0
        upsert_contract(
            con,
            contract_id=cid,
            question=f"F105 effort task {row.get('task_id')} for {row.get('agent_id')}",
            source="f105_metacognition",
            source_corpus="f105_metacognition_smoke_n15",
            y_known=y,
            raw=row,
        )
        insert_call(
            con,
            pilot_id=pilot_id,
            contract_id=cid,
            agent_id=row.get("agent_id"),
            family=family_of(row.get("agent_id"), row.get("runtime"), row.get("model")),
            condition=row.get("difficulty"),
            primitive="f105_metacognition",
            primitive_base="f105",
            phase="smoke_n15",
            p_success=p,
            y_known=y,
            schema_ok=bool(row.get("schema_ok")),
            parsed={**parsed, "ground_truth_y": y, "p_mid": p},
            fired_at=row.get("fired_at"),
            raw=row,
        )
    return {"pilot_id": pilot_id, "rows": len(rows)}


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        out = float(value)
    except Exception:
        return None
    return out


def _log_abs_ratio(est_mid: float | None, actual: float | None) -> float | None:
    if est_mid is None or actual is None or est_mid <= 0 or actual <= 0:
        return None
    return abs(math.log(est_mid / actual))


def ingest_f105_effort_pairs(
    con: sqlite3.Connection,
    *,
    path: Path,
    pilot_id: str,
    default_family: str,
    metric: str,
) -> dict[str, Any]:
    """Ingest F105 hard-prompt-break effort ledgers as paired continuous forecasts.

    The raw ledgers have Turn 1 estimate rows and Turn 2 measurement rows. We
    store one DB call per Turn 1 forecast, enriched with the matched Turn 2
    measurement. `p_success` and `y_known` intentionally stay NULL: these are
    continuous effort estimates, not binary forecast probabilities.
    """
    raw_rows = load_jsonl(path)
    actual_key = "actual_steps" if metric == "steps" else "actual_tokens"
    unit = "steps" if metric == "steps" else "effort_tokens"
    actuals: dict[str, dict[str, Any]] = {}
    for row in raw_rows:
        if row.get("turn") != 2:
            continue
        task_id = row.get("task_id")
        if not task_id:
            continue
        actuals[str(task_id)] = row

    forecast_rows = [
        row for row in raw_rows
        if row.get("turn") == 1 and row.get("est_mid") is not None
    ]
    replace_pilot_run(
        con,
        pilot_id=pilot_id,
        pilot_name=path.stem,
        primitive=f"f105_{metric}_effort_estimation",
        corpus="f105_objective_effort",
        source_path=path,
        n_calls=len(forecast_rows),
        n_schema_ok=sum(1 for row in forecast_rows if row.get("schema_ok")),
    )
    inserted = 0
    missing_actual = 0
    for row in forecast_rows:
        task_id = str(row.get("task_id"))
        actual_row = actuals.get(task_id)
        if not actual_row:
            missing_actual += 1
        family = canonical_family(row.get("family")) or default_family
        agent_id = f"{family}_f105_{metric}"
        arm = row.get("arm")
        split = row.get("split")
        actual = _as_float((actual_row or {}).get(actual_key))
        passed_raw = (actual_row or {}).get("passed")
        passed = bool(passed_raw) if passed_raw is not None else None
        est_mid = _as_float(row.get("est_mid"))
        parsed = {
            "task_id": task_id,
            "difficulty": row.get("difficulty"),
            "split": split,
            "arm": arm,
            "estimate_low": _as_float(row.get("est_low")),
            "estimate_high": _as_float(row.get("est_high")),
            "estimate_mid": est_mid,
            "actual": actual,
            "actual_metric": actual_key,
            "unit": unit,
            "passed": passed,
            "resolve_detail": (actual_row or {}).get("resolve_detail"),
            "log_abs_ratio": _log_abs_ratio(est_mid, actual),
            "forecast_wall_s": row.get("wall_s"),
            "solve_wall_s": (actual_row or {}).get("wall_s"),
            "raw_forecast_schema_ok": bool(row.get("schema_ok")),
            "hard_prompt_break": True,
        }
        cid = f"{pilot_id}_{family}_{task_id}_{arm}"
        upsert_contract(
            con,
            contract_id=cid,
            question=f"F105 {metric} effort estimate: {family} task {task_id} arm {arm}",
            source="f105_effort_estimation",
            source_corpus=pilot_id,
            y_known=None,
            raw={**row, "matched_actual": actual_row},
        )
        insert_call(
            con,
            pilot_id=pilot_id,
            contract_id=cid,
            agent_id=agent_id,
            family=family,
            condition=row.get("difficulty"),
            primitive=f"f105_{metric}_effort_estimation",
            primitive_base="f105",
            phase=f"{metric}_{split}_{arm}",
            p_success=None,
            y_known=None,
            schema_ok=bool(row.get("schema_ok")) and actual is not None,
            parsed=parsed,
            fired_at=row.get("fired_at"),
            raw={**row, "matched_actual": actual_row},
        )
        inserted += 1
    return {
        "pilot_id": pilot_id,
        "rows": inserted,
        "raw_rows": len(raw_rows),
        "missing_actual": missing_actual,
    }


def ingest_f105_effort_rescue(con: sqlite3.Connection) -> list[dict[str, Any]]:
    specs = [
        (
            F105_WS / "f105_v5_effort_estimation_calls.jsonl",
            "f105_v5_effort_claude",
            "claude",
            "token_length",
        ),
        (
            F105_WS / "f105_v5_multifamily_codex_calls.jsonl",
            "f105_v5_effort_codex_55",
            "codex_55",
            "token_length",
        ),
        (
            F105_WS / "f105_v5_multifamily_gemini_calls.jsonl",
            "f105_v5_effort_gemini",
            "gemini",
            "token_length",
        ),
        (
            F105_WS / "f105_v5_multifamily_deepseek_calls.jsonl",
            "f105_v5_effort_deepseek",
            "deepseek",
            "token_length",
        ),
        (
            F105_WS / "f105_v6_stepcount_claude_calls.jsonl",
            "f105_v6_stepcount_claude",
            "claude",
            "steps",
        ),
    ]
    out: list[dict[str, Any]] = []
    for path, pilot_id, family, metric in specs:
        out.append(
            ingest_f105_effort_pairs(
                con,
                path=path,
                pilot_id=pilot_id,
                default_family=family,
                metric=metric,
            )
        )
    return out


def ingest_premium(con: sqlite3.Connection) -> list[dict[str, Any]]:
    gt: dict[str, int] = {}
    if PREMIUM_GT.exists():
        gt = {k: int(v) for k, v in json.loads(PREMIUM_GT.read_text(encoding="utf-8")).items()}
    specs = [
        ("premium_batch1", GP245_WS / "premium_batch1_calls.jsonl", "claude"),
        ("premium_crossfamily", GP245_WS / "premium_crossfamily_calls.jsonl", None),
    ]
    out = []
    for pilot_id, path, default_family in specs:
        raw_rows = load_jsonl(path)
        grouped: dict[tuple[str, str], dict[str, Any]] = defaultdict(dict)
        titles: dict[str, str] = {}
        for row in raw_rows:
            fam = canonical_family(row.get("family") or default_family)
            qid = row.get("qid")
            if not fam or not qid:
                continue
            grouped[(fam, qid)][row.get("kind")] = row.get("value")
            if row.get("title"):
                titles[qid] = row["title"]
        replace_pilot_run(
            con,
            pilot_id=pilot_id,
            pilot_name=path.stem,
            primitive="premium_equal_budget_controls",
            corpus="premium_public_clean",
            source_path=path,
            n_calls=len(grouped),
            n_schema_ok=len(grouped),
        )
        for (fam, qid), values in grouped.items():
            y = gt.get(qid)
            p = values.get("prob")
            p = float(p) if isinstance(p, (int, float)) else None
            raw = {"qid": qid, "family": fam, "values": values, "title": titles.get(qid)}
            upsert_contract(
                con,
                contract_id=qid,
                question=titles.get(qid) or f"Premium clean contract {qid}",
                source="premium_public_clean",
                source_corpus="premium_public_clean_20260531",
                y_known=y,
                raw=raw,
            )
            insert_call(
                con,
                pilot_id=pilot_id,
                contract_id=qid,
                agent_id=fam,
                family=fam,
                condition="premium_equal_budget_controls",
                primitive="premium_equal_budget_controls",
                primitive_base="premium",
                phase="premium_v1",
                p_success=p,
                y_known=y,
                schema_ok=p is not None,
                parsed={
                    "worry": values.get("worry"),
                    "confidence": values.get("confidence"),
                    "sham": values.get("sham"),
                    "p2": values.get("prob2"),
                    "y_known": y,
                    "abserr": None if p is None or y is None else abs(p - y),
                },
                fired_at="2026-05-31T00:00:00+00:00",
                raw=raw,
            )
        out.append({"pilot_id": pilot_id, "rows": len(grouped), "gt_available": bool(gt)})
    return out


def run(*, verify_only: bool) -> dict[str, Any]:
    anti_bias_path = ANTI_BIAS_WS / "anti_bias_collapse_v1_calls.jsonl"
    if not verify_only:
        validate_anti_bias_collapse_receipt(anti_bias_path)
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys = OFF")
    if not verify_only:
        results = [
            ingest_bias_panel(
                con,
                path=GP245_WS / "f106_ood_inheritance_cheap_n15_calls.jsonl",
                pilot_id="f106_ood_inheritance_cheap_n15",
                primitive="f106_ood_inheritance",
            ),
            ingest_bias_panel(
                con,
                path=GP245_WS / "f107_corrected_ood_panel_calls.jsonl",
                pilot_id="f107_corrected_ood_panel",
                primitive="f107_corrected_ood",
            ),
            ingest_f105(con),
            *ingest_f105_effort_rescue(con),
            ingest_anti_bias_collapse(con, validate_receipt=False),
            *ingest_premium(con),
        ]
        con.commit()
    else:
        results = []
    summary = []
    for pilot_id in [
        "f105_metacognition_smoke_n15",
        "f105_v5_effort_claude",
        "f105_v5_effort_codex_55",
        "f105_v5_effort_gemini",
        "f105_v5_effort_deepseek",
        "f105_v6_stepcount_claude",
        "f106_ood_inheritance_cheap_n15",
        "f107_corrected_ood_panel",
        "premium_batch1",
        "premium_crossfamily",
        "anti_bias_collapse_v1",
    ]:
        row = con.execute(
            """
            SELECT COUNT(*), SUM(schema_ok = 1), SUM(brier IS NOT NULL)
            FROM pilot_calls WHERE pilot_id = ?
            """,
            (pilot_id,),
        ).fetchone()
        run_row = con.execute(
            "SELECT COUNT(*) FROM pilot_runs WHERE pilot_id = ?",
            (pilot_id,),
        ).fetchone()
        summary.append(
            {
                "pilot_id": pilot_id,
                "pilot_run_rows": int(run_row[0] or 0),
                "pilot_calls": int(row[0] or 0),
                "schema_ok": int(row[1] or 0),
                "with_brier": int(row[2] or 0),
            }
        )
    con.close()
    return {"ingested": results, "summary": summary}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(verify_only=args.verify), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
