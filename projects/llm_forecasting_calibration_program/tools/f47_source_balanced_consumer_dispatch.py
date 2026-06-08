#!/usr/bin/env python3
"""Fire the F47 source-balanced contrastive consumer packet.

This runner deliberately reuses the v26a contrastive prompt/runtime surface, but
the packet and scoring endpoint are source-balanced and pairwise.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
WORKSPACE = (
    REPO
    / "projects/llm_forecasting_calibration_program/forecaster_skill_calibration_v1/workspace"
)
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(WORKSPACE))

from run_pilot_v26_novel_primitives_dispatch import (  # noqa: E402
    AGENTS,
    AGENTS_SMOKE,
    append_row,
    build_v26a_prompt,
    call_agent,
    parse_json_strict,
    schema_check,
)


DEFAULT_QUEUE = WORKSPACE / "f47_source_balanced_consumer_packet_2026_06_03_dispatch_queue.jsonl"
DEFAULT_OUT = WORKSPACE / "pilot_f47_source_balanced_consumer_calls_smoke_2026_06_03.jsonl"

FAMILY_ALIASES = {
    "claude": "claude",
    "codex_55": "codex_55",
    "codex_mini": "codex_mini",
    "gemini": "gemini",
    "deepseek": "deepseek",
}


def family_of(agent_id: str, runtime: str, model: str | None) -> str:
    if runtime == "codex" and model == "gpt-5.5":
        return "codex_55"
    if runtime == "codex" and model == "gpt-5.4-mini":
        return "codex_mini"
    return runtime or agent_id


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def contract_identifier(contract: dict[str, Any]) -> str:
    return str(contract.get("contract_id") or contract.get("market_id") or contract.get("slug") or "")


def select_agents(smoke: bool, families: list[str] | None) -> list[tuple[str, str, str | None]]:
    agents = AGENTS_SMOKE if smoke else AGENTS
    if not families:
        return list(agents)
    wanted = {FAMILY_ALIASES.get(f, f) for f in families}
    selected = [
        (aid, runtime, model)
        for aid, runtime, model in agents
        if family_of(aid, runtime, model) in wanted
    ]
    if not selected:
        raise SystemExit(f"no agents matched families={sorted(wanted)}")
    return selected


def build_plan(
    queue: list[dict[str, Any]],
    agents: list[tuple[str, str, str | None]],
    max_pairs: int | None,
    start_pair_index: int,
    existing_schema_ok: set[tuple[str, str]],
) -> list[dict[str, Any]]:
    if start_pair_index < 0:
        raise SystemExit("--start-pair-index must be non-negative")
    rows = queue[start_pair_index:]
    if max_pairs is not None:
        rows = rows[:max_pairs]
    plan: list[dict[str, Any]] = []
    for row in rows:
        for aid, runtime, model in agents:
            if (str(row.get("pair_id")), aid) in existing_schema_ok:
                continue
            plan.append(
                {
                    "packet_row": row,
                    "agent_id": aid,
                    "runtime": runtime,
                    "model": model,
                }
            )
    return plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--max-pairs", type=int, default=None)
    parser.add_argument(
        "--start-pair-index",
        type=int,
        default=0,
        help="Zero-based offset into the dispatch queue before max-pairs is applied.",
    )
    parser.add_argument(
        "--skip-existing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip prior schema-ok rows for the same pair_id and agent_id in --out.",
    )
    parser.add_argument(
        "--families",
        default=None,
        help="Comma-separated family subset: gemini,deepseek,claude,codex_55,codex_mini.",
    )
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    families = [x.strip() for x in args.families.split(",") if x.strip()] if args.families else None
    agents = select_agents(smoke=args.smoke, families=families)
    queue = read_jsonl(args.queue)
    prior_rows = read_jsonl(args.out) if args.skip_existing else []
    existing_schema_ok = {
        (str(row.get("pair_id")), str(row.get("agent_id")))
        for row in prior_rows
        if (row.get("schema_audit") or {}).get("schema_ok")
    }
    plan = build_plan(
        queue,
        agents,
        args.max_pairs,
        args.start_pair_index,
        existing_schema_ok,
    )

    print(
        json.dumps(
            {
                "runner": "f47_source_balanced_consumer_dispatch",
                "queue": str(args.queue),
                "out": str(args.out),
                "queue_rows": len(queue),
                "start_pair_index": args.start_pair_index,
                "max_pairs": args.max_pairs,
                "skip_existing": args.skip_existing,
                "prior_schema_ok_rows": len(existing_schema_ok),
                "pairs": len({p["packet_row"]["pair_id"] for p in plan}),
                "calls": len(plan),
                "agents": [a[0] for a in agents],
                "dry_run": args.dry_run,
            },
            indent=2,
        )
    )
    if args.dry_run:
        return 0

    t0 = time.time()
    parsed_ok = 0
    schema_ok = 0
    for idx, item in enumerate(plan, start=1):
        packet = item["packet_row"]
        a = packet["contract_a"]
        b = packet["contract_b"]
        aid = item["agent_id"]
        runtime = item["runtime"]
        model = item["model"]
        prompt = build_v26a_prompt(str(a["question"])[:1500], str(b["question"])[:1500], "base")
        label = f"{packet['pair_id']}::{aid}"

        call_start = time.time()
        stdout, err = call_agent(runtime, model, prompt, aid, label)
        wallclock = time.time() - call_start
        parsed = parse_json_strict(stdout)
        audit = schema_check(parsed, "v26a", "base")
        row = {
            "pilot_run_ts": datetime.now(timezone.utc).isoformat(),
            "primitive": "f47_source_balanced_consumer",
            "condition": "base",
            "sub_condition": "base",
            "pair_id": packet["pair_id"],
            "source": packet["source"],
            "contract_id": contract_identifier(a),
            "partner_contract_id": contract_identifier(b),
            "contract_a": a,
            "contract_b": b,
            "agent_id": aid,
            "runtime": runtime,
            "model": model,
            "stdout_len": len(stdout or ""),
            "stdout_preview": (stdout or "")[:300],
            "parsed": parsed,
            "schema_audit": audit,
            "wallclock_s": round(wallclock, 2),
            "api_error": err,
        }
        append_row(args.out, row)
        parsed_ok += int(parsed is not None)
        schema_ok += int(bool(audit.get("schema_ok")))
        print(
            f"[f47-source-balanced] {idx}/{len(plan)} {aid} {packet['pair_id']} "
            f"wall={wallclock:.1f}s parsed={parsed is not None} "
            f"schema_ok={audit.get('schema_ok')} err={err or '-'}",
            flush=True,
        )

    print(
        f"[f47-source-balanced] DONE calls={len(plan)} parsed_ok={parsed_ok} "
        f"schema_ok={schema_ok} elapsed={time.time() - t0:.1f}s out={args.out}"
    )
    try:
        from src.ztare.forecasting import calibration_db

        calibration_db.init_db()
        calibration_db.ingest_pilot(str(args.out))
        print(f"[f47-source-balanced] auto-ingested {args.out.name}")
    except Exception as exc:
        print(f"[f47-source-balanced] auto-ingest skipped: {exc!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
