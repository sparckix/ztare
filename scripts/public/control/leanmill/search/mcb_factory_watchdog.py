#!/usr/bin/env python3
"""Wait for an expanded MCB corpus, then run the source-to-factory conveyor.

This is the cycle-time reducer around the proof factory. It does no proving
while the corpus builder is alive. Once the corpus is present and stable, it
runs:

  expanded corpus -> source pipeline -> intake SQLite -> bounded mill drain

The mill drain is optional and bounded so the watchdog can be left running on a
VPS without turning into unaccounted exhaustive search.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[5]
CTL = REPO / "scripts/public/control"


def _proc_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _append_jsonl(path: Path, rec: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()


def _run(cmd: list[str], log: Path, dry_run: bool = False) -> dict[str, Any]:
    t0 = time.monotonic()
    rec: dict[str, Any] = {
        "cmd": cmd,
        "cwd": str(REPO),
        "dry_run": bool(dry_run),
        "phase": "command_start",
        "ts": time.time(),
    }
    _append_jsonl(log, rec)
    if dry_run:
        done = {**rec, "phase": "command_done", "returncode": 0, "elapsed_s": 0.0}
        _append_jsonl(log, done)
        return done
    proc = subprocess.run(cmd, cwd=str(REPO), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    done = {
        **rec,
        "phase": "command_done",
        "returncode": proc.returncode,
        "elapsed_s": round(time.monotonic() - t0, 3),
        "stdout_tail": proc.stdout[-4000:],
        "stderr_tail": proc.stderr[-4000:],
    }
    _append_jsonl(log, done)
    if proc.returncode != 0:
        raise SystemExit(json.dumps(done, indent=2, sort_keys=True))
    return done


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(errors="ignore"))


def _corpus_ready(path: Path, stable_s: float) -> bool:
    if not path.exists() or path.stat().st_size <= 0:
        return False
    first = path.stat()
    time.sleep(stable_s)
    second = path.stat()
    if first.st_size != second.st_size or first.st_mtime != second.st_mtime:
        return False
    try:
        _read_json(path)
    except Exception:
        return False
    return True


def pipeline_cmd(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(CTL / "leansearch_mcb_source_pipeline.py"),
        "--corpus",
        args.corpus,
        "--exclude",
        args.exclude,
        "--root",
        str(Path(args.root) / "source_pipeline"),
        "--intake-db",
        args.intake_db,
        "--max-rows",
        str(args.max_rows),
        "--leansearch-limit",
        str(args.leansearch_limit),
        "--max-candidates-per-row",
        str(args.max_candidates_per_row),
        "--summary",
        str(Path(args.root) / "source_pipeline" / "summary.json"),
    ]


def mill_cmd(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(CTL / "leansearch_factory_mill.py"),
        "--from-intake",
        "--intake-db",
        args.intake_db,
        "--root",
        str(Path(args.root) / "mill"),
        "--summary",
        str(Path(args.root) / "mill" / "summary.json"),
        "--intake-limit",
        str(args.intake_limit),
        "--a-timeout",
        str(args.a_timeout),
        "--b-timeout",
        str(args.b_timeout),
        "--b-workers",
        str(args.b_workers),
        "--max-candidates",
        str(args.max_candidates),
        "--max-actions",
        str(args.max_actions),
        "--backend",
        args.backend,
        "--candidate-mode",
        args.candidate_mode,
        "--overlap-stations",
    ]


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    log = root / "watchdog_events.jsonl"
    corpus = Path(args.corpus)
    deadline = time.time() + args.max_wait_s
    while time.time() < deadline:
        alive = _proc_alive(args.wait_for_pid)
        ready = _corpus_ready(corpus, args.stable_s) if not alive else False
        _append_jsonl(log, {
            "phase": "poll",
            "ts": time.time(),
            "wait_for_pid": args.wait_for_pid,
            "pid_alive": alive,
            "corpus_exists": corpus.exists(),
            "corpus_bytes": corpus.stat().st_size if corpus.exists() else 0,
            "corpus_ready": ready,
        })
        if ready:
            break
        time.sleep(args.poll_s)
    else:
        raise SystemExit(f"timed out waiting for stable corpus: {corpus}")

    pipe = _run(pipeline_cmd(args), log, args.dry_run)
    pipe_summary_path = root / "source_pipeline" / "summary.json"
    pipe_summary = _read_json(pipe_summary_path)
    ready_total = int((pipe_summary.get("summary") or {}).get("intake_ready_total") or 0)
    result: dict[str, Any] = {
        "schema": "leansearch-mcb-factory-watchdog-v1",
        "root": str(root),
        "corpus": args.corpus,
        "pipeline": pipe,
        "pipeline_summary": pipe_summary.get("summary") or {},
        "mill_started": False,
        "log": str(log),
    }
    if ready_total > 0 and args.run_mill:
        result["mill_started"] = True
        result["mill"] = _run(mill_cmd(args), log, args.dry_run)
    elif ready_total <= 0:
        result["skip_reason"] = "no_intake_ready_rows"
    else:
        result["skip_reason"] = "run_mill_disabled"

    out = root / "watchdog_summary.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def _self_test() -> int:
    args = argparse.Namespace(
        corpus="/tmp/corpus.json",
        exclude="/tmp/exclude.json",
        root="/tmp/root",
        intake_db="/tmp/root/intake.sqlite",
        max_rows=9,
        leansearch_limit=3,
        max_candidates_per_row=2,
        intake_limit=4,
        a_timeout=55,
        b_timeout=66,
        b_workers=2,
        max_candidates=4,
        max_actions=3,
        backend="repl_step",
        candidate_mode="first_then_all",
        wait_for_pid=None,
        poll_s=1,
        stable_s=0.01,
        max_wait_s=1,
        run_mill=True,
        dry_run=True,
    )
    pcmd = pipeline_cmd(args)
    mcmd = mill_cmd(args)
    assert "leansearch_mcb_source_pipeline.py" in pcmd[1]
    assert "--from-intake" in mcmd
    assert "--backend" in mcmd and "repl_step" in mcmd
    assert "--overlap-stations" in mcmd
    assert _proc_alive(None) is False
    print("leansearch_mcb_factory_watchdog self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=False, default="/tmp/rung1/mcb_expand100/mcb_corpus_expand100.json")
    ap.add_argument("--exclude", default="/tmp/rung1/mcb_corpus_v2.json")
    ap.add_argument("--root", default="/tmp/rung1/mcb_expand100/factory_watchdog")
    ap.add_argument("--intake-db", default="/tmp/rung1/mcb_expand100/intake.sqlite")
    ap.add_argument("--max-rows", type=int, default=80)
    ap.add_argument("--leansearch-limit", type=int, default=8)
    ap.add_argument("--max-candidates-per-row", type=int, default=6)
    ap.add_argument("--intake-limit", type=int, default=20)
    ap.add_argument("--a-timeout", type=int, default=90)
    ap.add_argument("--b-timeout", type=int, default=180)
    ap.add_argument("--b-workers", type=int, default=2)
    ap.add_argument("--max-candidates", type=int, default=4)
    ap.add_argument("--max-actions", type=int, default=3)
    ap.add_argument("--backend", choices=["subprocess", "repl", "repl_step", "repl_file"], default="repl_step")
    ap.add_argument("--candidate-mode", choices=["first_then_all", "all"], default="first_then_all")
    ap.add_argument("--wait-for-pid", type=int)
    ap.add_argument("--poll-s", type=float, default=30.0)
    ap.add_argument("--stable-s", type=float, default=3.0)
    ap.add_argument("--max-wait-s", type=float, default=21600.0)
    ap.add_argument("--run-mill", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    obj = run(args)
    print(json.dumps({
        "root": obj["root"],
        "pipeline_summary": obj.get("pipeline_summary"),
        "mill_started": obj.get("mill_started"),
        "skip_reason": obj.get("skip_reason", ""),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
