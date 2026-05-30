#!/usr/bin/env python3
"""Run the MCB source-to-intake pipeline as one checkpointed command.

This script does not prove anything. It automates the source expansion conveyor:
expanded MCB corpus -> new-row queue -> LeanSearch source packet -> static
filter -> row-context filter -> SQLite intake buffer. Downstream Path A/B/C
factory runs remain separate and must preserve the same governance boundary.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[5]
CTL = REPO / "scripts/public/control"


def _run(cmd: list[str], cwd: Path, dry_run: bool) -> dict[str, Any]:
    rec: dict[str, Any] = {"cmd": cmd, "cwd": str(cwd)}
    if dry_run:
        rec["returncode"] = 0
        rec["dry_run"] = True
        return rec
    proc = subprocess.run(cmd, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    rec.update({
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    })
    if proc.returncode != 0:
        raise SystemExit(json.dumps(rec, indent=2, sort_keys=True))
    return rec


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(errors="ignore"))


def build_commands(args: argparse.Namespace) -> list[tuple[str, list[str]]]:
    root = Path(args.root)
    queue = root / "queue.json"
    queue_md = root / "queue.md"
    source = root / "source_packet.json"
    source_md = root / "source_packet.md"
    static = root / "static_filter.json"
    static_md = root / "static_filter.md"
    row_context = root / "row_context_filter.json"
    row_context_md = root / "row_context_filter.md"
    row_context_partial = root / "row_context_filter.partial.json"
    row_context_checkpoint = root / "row_context_filter.checkpoint.jsonl"
    intake_json = root / "intake.json"
    py = sys.executable
    intake_cmd = [
        py, str(CTL / "leansearch_factory_intake.py"),
        "--row-context-filter", str(row_context),
        "--queue-db", args.intake_db,
        "--out", str(intake_json),
    ]
    if args.exclude_unclassified:
        intake_cmd.append("--exclude-unclassified")
    return [
        ("queue", [
            py, str(CTL / "leansearch_mcb_queue.py"),
            "--corpus", args.corpus,
            "--exclude", args.exclude,
            "--out", str(queue),
            "--markdown", str(queue_md),
        ]),
        ("source", [
            py, str(CTL / "leansearch_source_adapter.py"),
            "--source-queue", str(queue),
            "--out", str(source),
            "--markdown", str(source_md),
            "--max-rows", str(args.max_rows),
            "--limit", str(args.leansearch_limit),
        ]),
        ("static_filter", [
            py, str(CTL / "leansearch_candidate_static_filter.py"),
            "--packet", str(source),
            "--out", str(static),
            "--markdown", str(static_md),
            "--timeout", str(args.static_timeout),
            "--max-candidates-per-row", str(args.max_candidates_per_row),
        ]),
        ("row_context_filter", [
            py, str(CTL / "leansearch_row_context_filter.py"),
            "--corpus", args.corpus,
            "--static-filter", str(static),
            "--out", str(row_context),
            "--markdown", str(row_context_md),
            "--timeout", str(args.row_context_timeout),
            "--max-candidates-per-row", str(args.max_candidates_per_row),
            "--partial-out", str(row_context_partial),
            "--checkpoint-jsonl", str(row_context_checkpoint),
        ]),
        ("intake", intake_cmd),
    ]


def run_pipeline(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    steps: list[dict[str, Any]] = []
    for name, cmd in build_commands(args):
        if args.start_at and name != args.start_at and not steps:
            continue
        rec = _run(cmd, REPO, args.dry_run)
        rec["step"] = name
        steps.append(rec)
        if args.stop_after and name == args.stop_after:
            break
    payload = {
        "schema": "leansearch-mcb-source-pipeline-v1",
        "root": str(root),
        "corpus": args.corpus,
        "exclude": args.exclude,
        "intake_db": args.intake_db,
        "dry_run": bool(args.dry_run),
        "steps": steps,
        "summary": {},
    }
    if not args.dry_run:
        queue = _read_json(root / "queue.json")
        source = _read_json(root / "source_packet.json")
        static = _read_json(root / "static_filter.json")
        row_context = _read_json(root / "row_context_filter.json")
        intake = _read_json(root / "intake.json")
        payload["summary"] = {
            "source_discovery_queue_count": queue.get("source_discovery_queue_count"),
            "usable_candidate_total": source.get("usable_candidate_total"),
            "canary_ready_total": static.get("canary_ready_total"),
            "row_context_ready_total": row_context.get("row_context_ready_total"),
            "intake_inserted": intake.get("inserted"),
            "intake_ready_total": intake.get("wip_ready_total"),
        }
    if args.summary:
        Path(args.summary).parent.mkdir(parents=True, exist_ok=True)
        Path(args.summary).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _self_test() -> int:
    args = argparse.Namespace(
        root="/tmp/leansearch_mcb_source_pipeline_self_test",
        corpus="/tmp/corpus.json",
        exclude="/tmp/exclude.json",
        intake_db="/tmp/intake.sqlite",
        max_rows=7,
        leansearch_limit=3,
        static_timeout=11,
        row_context_timeout=13,
        max_candidates_per_row=2,
        exclude_unclassified=True,
        start_at=None,
        stop_after=None,
        dry_run=True,
        summary=None,
    )
    cmds = build_commands(args)
    assert [name for name, _ in cmds] == ["queue", "source", "static_filter", "row_context_filter", "intake"]
    assert "--exclude-unclassified" in cmds[-1][1]
    assert "--partial-out" in cmds[3][1]
    assert "--checkpoint-jsonl" in cmds[3][1]
    obj = run_pipeline(args)
    assert obj["dry_run"] is True
    assert len(obj["steps"]) == 5
    args.stop_after = "source"
    obj = run_pipeline(args)
    assert [s["step"] for s in obj["steps"]] == ["queue", "source"]
    print("leansearch_mcb_source_pipeline self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus")
    ap.add_argument("--exclude", default="/tmp/rung1/mcb_corpus_v2.json")
    ap.add_argument("--root")
    ap.add_argument("--intake-db")
    ap.add_argument("--max-rows", type=int, default=80)
    ap.add_argument("--leansearch-limit", type=int, default=8)
    ap.add_argument("--static-timeout", type=int, default=180)
    ap.add_argument("--row-context-timeout", type=int, default=120)
    ap.add_argument("--max-candidates-per-row", type=int, default=6)
    ap.add_argument("--include-unclassified", action="store_true")
    ap.add_argument("--start-at", choices=["queue", "source", "static_filter", "row_context_filter", "intake"])
    ap.add_argument("--stop-after", choices=["queue", "source", "static_filter", "row_context_filter", "intake"])
    ap.add_argument("--summary")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if args.start_at and args.stop_after:
        order = ["queue", "source", "static_filter", "row_context_filter", "intake"]
        if order.index(args.stop_after) < order.index(args.start_at):
            raise SystemExit("--stop-after must be at or after --start-at")
    missing = [name for name in ("corpus", "root", "intake_db") if not getattr(args, name)]
    args.exclude_unclassified = not args.include_unclassified
    if missing:
        raise SystemExit(f"missing required arguments: {', '.join('--' + m.replace('_', '-') for m in missing)}")
    obj = run_pipeline(args)
    print(json.dumps({
        "root": obj["root"],
        "dry_run": obj["dry_run"],
        "summary": obj["summary"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
