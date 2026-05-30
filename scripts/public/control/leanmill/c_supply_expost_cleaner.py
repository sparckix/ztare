#!/usr/bin/env python3
"""Compact dirty LeanMill C-supply artifacts into a clean eval read model.

This is an ex-post hygiene pass. It never deletes raw artifacts. It reads the
historical per-corpus static checkpoints and probe corpora, collapses duplicate
row records, makes static-result conflicts explicit, and emits canonical clean
checkpoint/row-context files for C-discriminating slice prep.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import leanmill_c_supply_batch as supply
import leanmill_evaluation_harness_runner as harness
import leanmill_static_failure_miner as miner
from leanmill_paths import DATA_DIR

DEFAULT_REPORT_DIR = f"{DATA_DIR}/c_supply_batch_reports"
DEFAULT_CORPUS_GLOBS = supply.DEFAULT_CORPUS_GLOBS
DEFAULT_OUT_CHECKPOINT = f"{DATA_DIR}/c_supply_batch_cleaned_checkpoint.jsonl"
DEFAULT_OUT_ROW_CONTEXT = f"{DATA_DIR}/c_supply_batch_cleaned_row_context.json"
DEFAULT_OUT = f"{DATA_DIR}/c_supply_batch_expost_cleaner.json"
DEFAULT_MD = f"{DATA_DIR}/c_supply_batch_expost_cleaner.md"
STATIC_ARMS = {"public_tool_static", "governed_public_tool_static"}


def _read_json(path: str | Path) -> Any:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(errors="ignore"))
    except json.JSONDecodeError:
        return None


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return supply._read_jsonl(path)


def _write_json(path: str | Path, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def _checkpoint_paths(report_dir: str | Path) -> list[Path]:
    root = Path(report_dir)
    if not root.exists():
        return []
    return sorted(root.glob("*.static_failure_checkpoint.jsonl"))


def _record_key(rec: dict[str, Any]) -> tuple[str, str]:
    return (str(rec.get("row_id") or ""), str(rec.get("arm") or ""))


def _is_positive(rec: dict[str, Any] | None) -> bool:
    return bool(rec) and str(rec.get("learning_exit") or "") in miner.POSITIVE_EXITS


def _record_rank(rec: dict[str, Any]) -> tuple[int, int, int, int]:
    positive_rank = 3 if _is_positive(rec) else 0
    supply_rank = 1 if rec.get("supply_candidate") else 0
    uncached_rank = 0 if rec.get("cached_static_result") else 1
    attempts = int(rec.get("attempt_count") or 0)
    return (positive_rank, supply_rank, uncached_rank, attempts)


def _better_record(current: dict[str, Any] | None, candidate: dict[str, Any]) -> dict[str, Any]:
    if current is None or _record_rank(candidate) > _record_rank(current):
        return candidate
    return current


def _row_id(row: dict[str, Any]) -> str:
    return supply._row_id(row)


def _row_rank(row: dict[str, Any]) -> tuple[int, int, int]:
    source = str(row.get("source_file") or row.get("sorried_file") or "")
    readable = 1 if source and Path(source).exists() else 0
    target_ok = 1 if str(row.get("target_resolution_status") or "") == "pass" else 0
    has_goal = 1 if str(row.get("goal") or row.get("statement") or row.get("theorem") or "") else 0
    return (readable, target_ok, has_goal)




def _annotate_target_resolution(row: dict[str, Any]) -> dict[str, Any]:
    rec = dict(row)
    if str(rec.get("target_resolution_status") or ""):
        return rec
    check = harness._preflight_target_resolution([rec])
    rec["target_resolution_status"] = str(check.get("status") or "fail")
    rec["target_resolution_checked_by_cleaner"] = True
    rec["target_resolution_check"] = {
        "status": check.get("status"),
        "checked_row_count": check.get("checked_row_count"),
        "failure_count": check.get("failure_count"),
        "failures": check.get("failures", [])[:3],
    }
    return rec

def _corpus_paths(globs: list[str], *, max_corpora: int = 0) -> list[str]:
    paths: list[Path] = []
    for pattern in globs:
        base = Path(pattern)
        matches = sorted(Path().glob(pattern)) if not base.is_absolute() else sorted(base.parent.glob(base.name))
        paths.extend(p for p in matches if p.is_file())
    paths = sorted(set(paths), key=lambda p: (-p.stat().st_mtime, str(p)))
    if max_corpora > 0:
        paths = paths[:max_corpora]
    return [str(p) for p in paths]


def clean(args: argparse.Namespace) -> dict[str, Any]:
    checkpoint_paths = _checkpoint_paths(args.report_dir)
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    exits_by_key: dict[tuple[str, str], set[str]] = defaultdict(set)
    record_count = 0
    malformed_record_count = 0
    for checkpoint in checkpoint_paths:
        for rec in _read_jsonl(checkpoint):
            row_id, arm = _record_key(rec)
            if not row_id or not arm:
                malformed_record_count += 1
                continue
            record_count += 1
            exits_by_key[(row_id, arm)].add(str(rec.get("learning_exit") or ""))
            best = _better_record(by_key.get((row_id, arm)), rec)
            best = dict(best)
            sources = set(best.get("cleaned_from_checkpoints") or [])
            sources.add(str(checkpoint))
            best["cleaned_from_checkpoints"] = sorted(sources)
            best["cleaned_record_policy"] = "positive_static_result_dominates_no_signal; otherwise supply_candidate/uncached/attempt_count rank"
            by_key[(row_id, arm)] = best

    cleaned_records = [by_key[key] for key in sorted(by_key)]
    static_conflicts = [
        {"row_id": row_id, "arm": arm, "learning_exits": sorted(exits)}
        for (row_id, arm), exits in sorted(exits_by_key.items())
        if arm in STATIC_ARMS and len(exits) > 1
    ]
    _write_jsonl(args.out_checkpoint, cleaned_records)

    corpus_paths = _corpus_paths(args.corpus_glob or DEFAULT_CORPUS_GLOBS, max_corpora=int(args.max_corpora or 0))
    row_by_id: dict[str, dict[str, Any]] = {}
    row_sources: dict[str, set[str]] = defaultdict(set)
    raw_corpus_row_count = 0
    for corpus in corpus_paths:
        for row in supply._iter_rows(_read_json(corpus) or {}):
            row_id = _row_id(row)
            if not row_id:
                continue
            raw_corpus_row_count += 1
            row_sources[row_id].add(corpus)
            rec = _annotate_target_resolution(row)
            rec["row_id"] = row_id
            current = row_by_id.get(row_id)
            if current is None or _row_rank(rec) > _row_rank(current):
                row_by_id[row_id] = rec
    rows = []
    for row_id in sorted(row_by_id):
        rec = dict(row_by_id[row_id])
        rec["cleaned_from_corpora"] = sorted(row_sources[row_id])[:20]
        rec["cleaned_duplicate_corpus_count"] = max(0, len(row_sources[row_id]) - 1)
        rows.append(rec)
    _write_json(args.out_row_context, {
        "schema": "leanmill-c-supply-cleaned-row-context-v1",
        "source_corpora": corpus_paths,
        "raw_corpus_row_count": raw_corpus_row_count,
        "unique_row_count": len(rows),
        "duplicate_corpus_row_count": max(0, raw_corpus_row_count - len(rows)),
        "rows": rows,
    })

    positive_static_rows = sorted({row_id for (row_id, arm), rec in by_key.items() if arm in STATIC_ARMS and _is_positive(rec)})
    supply_candidate_rows = sorted({str(rec.get("row_id") or "") for rec in cleaned_records if rec.get("supply_candidate") and str(rec.get("row_id") or "")})
    exit_counts = Counter(str(rec.get("learning_exit") or "") for rec in cleaned_records)
    report = {
        "schema": "leanmill-c-supply-expost-cleaner-v1",
        "report_dir": args.report_dir,
        "checkpoint_count": len(checkpoint_paths),
        "raw_checkpoint_record_count": record_count,
        "malformed_checkpoint_record_count": malformed_record_count,
        "cleaned_checkpoint_record_count": len(cleaned_records),
        "duplicate_checkpoint_record_count": max(0, record_count - len(cleaned_records)),
        "static_conflict_key_count": len(static_conflicts),
        "static_conflicts": static_conflicts[:100],
        "static_conflict_policy": "public-tool positive dominates conflicting static no-signal records for C-slice safety",
        "positive_static_row_count": len(positive_static_rows),
        "positive_static_rows": positive_static_rows[:100],
        "supply_candidate_row_count": len(supply_candidate_rows),
        "supply_candidate_rows": supply_candidate_rows[:100],
        "exit_counts": dict(sorted(exit_counts.items())),
        "corpus_count": len(corpus_paths),
        "raw_corpus_row_count": raw_corpus_row_count,
        "unique_corpus_row_count": len(rows),
        "duplicate_corpus_row_count": max(0, raw_corpus_row_count - len(rows)),
        "out_checkpoint": args.out_checkpoint,
        "out_row_context": args.out_row_context,
        "raw_artifact_policy": "preserve raw artifacts; downstream eval reads compact clean artifacts",
    }
    _write_json(args.out, report)
    if args.md:
        _write_md(args.md, report)
    return report


def _write_md(path: str | Path, report: dict[str, Any]) -> None:
    lines = [
        "# LeanMill C-Supply Ex-Post Cleaner",
        "",
        f"- raw checkpoint records: `{report['raw_checkpoint_record_count']}`",
        f"- cleaned checkpoint records: `{report['cleaned_checkpoint_record_count']}`",
        f"- duplicate checkpoint records: `{report['duplicate_checkpoint_record_count']}`",
        f"- static conflict keys: `{report['static_conflict_key_count']}`",
        f"- positive static rows: `{report['positive_static_row_count']}`",
        f"- supply candidate rows: `{report['supply_candidate_row_count']}`",
        f"- raw corpus rows: `{report['raw_corpus_row_count']}`",
        f"- unique corpus rows: `{report['unique_corpus_row_count']}`",
        f"- duplicate corpus rows: `{report['duplicate_corpus_row_count']}`",
        f"- raw artifact policy: `{report['raw_artifact_policy']}`",
        "",
        "## Static Conflicts",
        "",
        "| row | arm | exits |",
        "|---|---|---|",
    ]
    for rec in report.get("static_conflicts", [])[:50]:
        lines.append(f"| `{rec['row_id']}` | `{rec['arm']}` | `{', '.join(rec['learning_exits'])}` |")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n")


def _self_test() -> int:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="leanmill_c_supply_cleaner_") as td:
        root = Path(td)
        reports = root / "reports"
        reports.mkdir()
        ck = reports / "a.static_failure_checkpoint.jsonl"
        ck.write_text(
            json.dumps({"run_id": "r1", "row_id": "x", "arm": "public_tool_static", "learning_exit": "tested_no_positive_signal", "attempt_count": 1, "supply_candidate": True}) + "\n" +
            json.dumps({"run_id": "r2", "row_id": "x", "arm": "public_tool_static", "learning_exit": "raw_closure_candidate", "attempt_count": 2, "supply_candidate": False}) + "\n"
        )
        src = root / "x.lean"
        src.write_text("theorem x : True := by\n  trivial\n")
        c1 = root / "probe_corpus_family_spec_a.json"
        c2 = root / "probe_corpus_family_spec_b.json"
        row = {"row_id": "x", "source_file": str(src), "goal": "theorem x : True := by"}
        c1.write_text(json.dumps({"rows": [row]}) + "\n")
        c2.write_text(json.dumps({"rows": [row]}) + "\n")
        out_ck = root / "clean.jsonl"
        out_rows = root / "rows.json"
        report = clean(argparse.Namespace(
            report_dir=str(reports),
            corpus_glob=[str(root / "probe_corpus_family_spec_*.json")],
            max_corpora=0,
            out_checkpoint=str(out_ck),
            out_row_context=str(out_rows),
            out=str(root / "report.json"),
            md=None,
        ))
        records = _read_jsonl(out_ck)
        assert len(records) == 1, records
        assert records[0]["learning_exit"] == "raw_closure_candidate", records
        assert report["static_conflict_key_count"] == 1, report
        rows = _read_json(out_rows)["rows"]
        assert len(rows) == 1 and rows[0]["row_id"] == "x", rows
        assert rows[0]["target_resolution_status"] == "pass", rows
        assert rows[0]["target_resolution_checked_by_cleaner"] is True, rows
    print("leanmill_c_supply_expost_cleaner self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-dir", default=DEFAULT_REPORT_DIR)
    ap.add_argument("--corpus-glob", action="append", default=[])
    ap.add_argument("--max-corpora", type=int, default=0)
    ap.add_argument("--out-checkpoint", default=DEFAULT_OUT_CHECKPOINT)
    ap.add_argument("--out-row-context", default=DEFAULT_OUT_ROW_CONTEXT)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--md", default=DEFAULT_MD)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    report = clean(args)
    print(json.dumps({
        "out": args.out,
        "out_checkpoint": args.out_checkpoint,
        "out_row_context": args.out_row_context,
        "cleaned_checkpoint_record_count": report.get("cleaned_checkpoint_record_count"),
        "static_conflict_key_count": report.get("static_conflict_key_count"),
        "unique_corpus_row_count": report.get("unique_corpus_row_count"),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
