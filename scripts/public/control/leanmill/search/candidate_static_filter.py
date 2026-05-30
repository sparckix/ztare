#!/usr/bin/env python3
"""Static Lean filter for LeanSearch candidate-source packets.

This is a Path-C sourcing guard, not a prover. It consumes
LEANSEARCH_SOURCE_CANDIDATE_PACKET.json, checks candidate declaration
names with Lean `#check`, and emits which candidate sources are safe
enough to feed into a bounded canary replay.

Science boundary:
  - no proof bodies are consumed or persisted
  - exact targets and post-target same-file declarations stay excluded
  - source-order debt blocks canary promotion
  - a resolved name is candidate-source evidence only, never closure
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


DEFAULT_PACKET = "analytics/public/leanmill/leansearch/LEANSEARCH_SOURCE_CANDIDATE_PACKET.json"
DEFAULT_OUT = "analytics/public/leanmill/leansearch/LEANSEARCH_STATIC_FILTER.json"
DEFAULT_MD = "analytics/public/leanmill/leansearch/LEANSEARCH_STATIC_FILTER.md"
DEFAULT_SANDBOX = (
    "analytics/public/leanmill/external_benchmarks/sandboxes/"
    "v28A_carleson_baseline/carleson"
)


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _env() -> dict[str, str]:
    env = os.environ.copy()
    elan_bin = Path.home() / ".elan" / "bin"
    if elan_bin.exists():
        env["PATH"] = f"{elan_bin}:{env.get('PATH', '')}"
    return env


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(errors="ignore"))


def _candidate_allowed_before_lean(c: dict[str, Any]) -> tuple[bool, str]:
    if c.get("exact_target_excluded"):
        return False, "exact_target_excluded"
    if c.get("post_target_forbidden"):
        return False, "post_target_same_file_forbidden"
    if c.get("requires_source_order_check"):
        return False, "source_order_check_owed"
    if not c.get("name"):
        return False, "missing_name"
    return True, "eligible_for_name_resolution"


def _lean_prelude() -> str:
    return "\n".join([
        "import Mathlib",
        "set_option maxHeartbeats 200000",
        "",
    ])


def _write_probe(packet: dict[str, Any], max_candidates_per_row: int | None,
                 path: Path) -> tuple[dict[int, tuple[str, int, str]], dict[str, list[dict[str, Any]]]]:
    line_map: dict[int, tuple[str, int, str]] = {}
    by_row: dict[str, list[dict[str, Any]]] = {}
    lines = _lean_prelude().splitlines()
    for row in packet.get("rows", []):
        row_id = str(row.get("row_id") or "")
        candidates = list(row.get("usable_candidates") or [])
        if max_candidates_per_row is not None:
            candidates = candidates[:max_candidates_per_row]
        by_row[row_id] = []
        for idx, c in enumerate(candidates):
            ok, reason = _candidate_allowed_before_lean(c)
            rec = {
                "candidate_index": idx,
                "name": c.get("name"),
                "kind": c.get("kind"),
                "module_name": c.get("module_name"),
                "source_safety_status": c.get("source_safety_status"),
                "source_order_status": c.get("source_order_status"),
                "source_order_safe": c.get("source_order_safe"),
                "pre_lean_allowed": ok,
                "pre_lean_reason": reason,
            }
            if ok:
                lines.append(f"-- ROW {row_id} CANDIDATE {idx}")
                check_line = len(lines) + 1
                lines.append(f"#check {c.get('name')}")
                rec["check_line"] = check_line
                line_map[check_line] = (row_id, idx, str(c.get("name")))
            by_row[row_id].append(rec)
    path.write_text("\n".join(lines) + "\n")
    return line_map, by_row


def _run_lean(probe_file: Path, sandbox: Path, timeout: int) -> dict[str, Any]:
    started = time.time()
    try:
        proc = subprocess.Popen(
            ["nice", "-n", "10", "lake", "env", "lean", str(probe_file)],
            cwd=str(sandbox),
            env=_env(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            return {
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "timed_out": False,
                "elapsed_sec": round(time.time() - started, 3),
                "stdout": stdout,
                "stderr": stderr,
            }
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait(timeout=5)
            return {
                "ok": False,
                "returncode": None,
                "timed_out": True,
                "elapsed_sec": round(time.time() - started, 3),
                "stdout": "",
                "stderr": "timeout",
            }
    except Exception as e:
        return {
            "ok": False,
            "returncode": None,
            "timed_out": False,
            "elapsed_sec": round(time.time() - started, 3),
            "stdout": "",
            "stderr": repr(e),
        }


def _error_lines(lean_text: str) -> set[int]:
    lines: set[int] = set()
    for m in re.finditer(r"(?m)^.*\.lean:(\d+):\d+: error:", lean_text):
        try:
            lines.add(int(m.group(1)))
        except ValueError:
            pass
    return lines


def _line_error_sample(lean_text: str, line: int) -> str:
    pat = re.compile(rf"(?m)^.*\.lean:{line}:\d+: error:.*(?:\n(?!.*\.lean:\d+:\d+:).*)*")
    m = pat.search(lean_text)
    return (m.group(0).strip()[:500] if m else "")


def _classify(by_row: dict[str, list[dict[str, Any]]],
              line_map: dict[int, tuple[str, int, str]],
              lean_result: dict[str, Any]) -> list[dict[str, Any]]:
    text = f"{lean_result.get('stdout', '')}\n{lean_result.get('stderr', '')}"
    err_lines = _error_lines(text)
    mapped_lines = set(line_map)
    unmapped_error_lines = sorted(n for n in err_lines if n not in mapped_lines)
    run_failed_without_mapped_errors = bool(
        (lean_result.get("timed_out") or lean_result.get("returncode") not in (0, None))
        and not err_lines
    )
    rows: list[dict[str, Any]] = []
    for row_id, candidates in by_row.items():
        out_candidates: list[dict[str, Any]] = []
        for rec in candidates:
            check_line = rec.get("check_line")
            if not rec.get("pre_lean_allowed"):
                name_resolves = False
                resolution_status = "blocked_before_lean"
            elif run_failed_without_mapped_errors:
                name_resolves = False
                resolution_status = "lean_run_failed"
            elif check_line in err_lines:
                name_resolves = False
                resolution_status = "name_resolution_failed"
            else:
                name_resolves = True
                resolution_status = "name_resolves"
            canary_ready = bool(
                name_resolves
                and rec.get("pre_lean_allowed")
                and str(rec.get("kind") or "").lower() in {"theorem", "lemma"}
            )
            out = {
                **rec,
                "name_resolves": name_resolves,
                "resolution_status": resolution_status,
                "usable_for_canary_source": canary_ready,
                "error_sample": _line_error_sample(text, int(check_line)) if check_line in err_lines else "",
            }
            out_candidates.append(out)
        rows.append({
            "row_id": row_id,
            "candidate_count": len(out_candidates),
            "resolved_count": sum(1 for c in out_candidates if c["name_resolves"]),
            "canary_ready_count": sum(1 for c in out_candidates if c["usable_for_canary_source"]),
            "canary_ready_candidates": [c for c in out_candidates if c["usable_for_canary_source"]],
            "candidates": out_candidates,
        })
    for row in rows:
        row["recommended_next_step"] = (
            "one_row_canary_replay"
            if row["canary_ready_count"]
            else "do_not_replay_without_new_source"
        )
    if unmapped_error_lines:
        rows.append({
            "row_id": "__probe_unmapped_errors__",
            "candidate_count": 0,
            "resolved_count": 0,
            "canary_ready_count": 0,
            "canary_ready_candidates": [],
            "candidates": [],
            "unmapped_error_lines": unmapped_error_lines,
            "recommended_next_step": "inspect_probe_before_using_filter",
        })
    return rows


def _should_fallback_per_row(lean_result: dict[str, Any]) -> bool:
    if lean_result.get("timed_out"):
        return False
    if lean_result.get("returncode") in (0, None):
        return False
    text = f"{lean_result.get('stdout', '')}\n{lean_result.get('stderr', '')}"
    return not _error_lines(text)


def _packet_for_one_row(packet: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    return {**packet, "rows": [row]}


def _run_per_row_fallback(packet: dict[str, Any], sandbox: Path, timeout: int,
                          max_candidates_per_row: int | None, root: Path,
                          max_rows: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    for idx, row in enumerate(packet.get("rows", [])[:max_rows]):
        row_id = str(row.get("row_id") or f"row_{idx}")
        probe = root / f"leansearch_static_filter_probe_{idx:04d}.lean"
        line_map, by_row = _write_probe(_packet_for_one_row(packet, row), max_candidates_per_row, probe)
        lean_result = _run_lean(probe, sandbox, timeout)
        row_result = _classify(by_row, line_map, lean_result)
        rows.extend(row_result)
        attempts.append({
            "row_id": row_id,
            "ok": lean_result.get("ok"),
            "returncode": lean_result.get("returncode"),
            "timed_out": lean_result.get("timed_out"),
            "elapsed_sec": lean_result.get("elapsed_sec"),
            "unmapped_error_only": bool(_error_lines(
                f"{lean_result.get('stdout', '')}\n{lean_result.get('stderr', '')}"
            ) - set(line_map)),
        })
    if len(packet.get("rows", [])) > max_rows:
        rows.append({
            "row_id": "__fallback_row_limit__",
            "candidate_count": 0,
            "resolved_count": 0,
            "canary_ready_count": 0,
            "canary_ready_candidates": [],
            "candidates": [],
            "recommended_next_step": f"rerun_with_higher_fallback_max_rows_{len(packet.get('rows', []))}",
        })
    return rows, attempts


def build(packet_path: Path, sandbox: Path, out: Path | None, markdown: Path | None,
          timeout: int, max_candidates_per_row: int | None = None,
          lean_output_fixture: Path | None = None,
          fallback_per_row: bool = True,
          fallback_max_rows: int = 200) -> dict[str, Any]:
    packet = _read_json(packet_path)
    with tempfile.TemporaryDirectory(prefix="leansearch_static_filter_") as td:
        root = Path(td)
        probe = root / "leansearch_static_filter_probe.lean"
        line_map, by_row = _write_probe(packet, max_candidates_per_row, probe)
        if lean_output_fixture:
            lean_result = {
                "ok": False,
                "returncode": 1,
                "timed_out": False,
                "elapsed_sec": 0,
                "stdout": lean_output_fixture.read_text(errors="ignore"),
                "stderr": "",
            }
        else:
            lean_result = _run_lean(probe, sandbox, timeout)
        rows = _classify(by_row, line_map, lean_result)
        fallback_used = False
        fallback_attempts: list[dict[str, Any]] = []
        if fallback_per_row and not lean_output_fixture and _should_fallback_per_row(lean_result):
            fallback_used = True
            rows, fallback_attempts = _run_per_row_fallback(
                packet, sandbox, timeout, max_candidates_per_row, root, fallback_max_rows
            )
        payload = {
            "schema": "leansearch-static-filter-v1",
            "generated_at": _now(),
            "packet": str(packet_path),
            "sandbox": str(sandbox),
            "timeout_sec": timeout,
            "lean_ok": lean_result.get("ok"),
            "lean_returncode": lean_result.get("returncode"),
            "lean_timed_out": lean_result.get("timed_out"),
            "lean_elapsed_sec": lean_result.get("elapsed_sec"),
            "lean_stdout_tail": str(lean_result.get("stdout", ""))[-4000:],
            "lean_stderr_tail": str(lean_result.get("stderr", ""))[-4000:],
            "fallback_per_row_used": fallback_used,
            "fallback_per_row_attempts": fallback_attempts,
            "fallback_max_rows": fallback_max_rows,
            "row_count": sum(1 for r in rows if not r["row_id"].startswith("__")),
            "candidate_count": sum(r["candidate_count"] for r in rows),
            "resolved_total": sum(r["resolved_count"] for r in rows),
            "canary_ready_total": sum(r["canary_ready_count"] for r in rows),
            "status": "canary_sources_ready" if any(r["canary_ready_count"] for r in rows) else "no_canary_sources_ready",
            "source_policy": {
                "proof_bodies_consumed": False,
                "proof_bodies_persisted": False,
                "exact_targets_remain_excluded": True,
                "post_target_same_file_remains_excluded": True,
                "source_order_debt_blocks_canary": True,
                "name_resolution_only_no_replay": True,
                "path_b_required_before_any_closure_credit": True,
            },
            "rows": rows,
            "decision": {
                "claim_closure": False,
                "train_model_now": False,
                "next_artifact": "one_row_canary_replay_from_canary_ready_candidates",
            },
        }
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if markdown:
        _write_md(payload, markdown)
    return payload


def _write_md(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# LeanSearch Static Filter",
        "",
        f"Rows: `{payload['row_count']}`",
        f"Candidates checked/listed: `{payload['candidate_count']}`",
        f"Resolved names: `{payload['resolved_total']}`",
        f"Canary-ready candidate sources: `{payload['canary_ready_total']}`",
        f"Lean timed out: `{payload['lean_timed_out']}`",
        f"Per-row fallback used: `{payload.get('fallback_per_row_used')}`",
        "",
        "| Row | Resolved | Canary Ready | Top Ready Candidates |",
        "|---|---:|---:|---|",
    ]
    for row in payload["rows"]:
        if row["row_id"].startswith("__"):
            continue
        names = ", ".join(f"`{c['name']}`" for c in row["canary_ready_candidates"][:5])
        lines.append(f"| `{row['row_id']}` | {row['resolved_count']} | {row['canary_ready_count']} | {names} |")
    lines.append("")
    lines.append("Boundary: this is name-resolution/source-readiness only; no proof replay or closure credit.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def _self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        packet = root / "packet.json"
        fixture = root / "lean.out"
        out = root / "out.json"
        md = root / "out.md"
        packet.write_text(json.dumps({
            "rows": [{
                "row_id": "r1",
                "usable_candidates": [
                    {
                        "name": "Good.Source",
                        "kind": "theorem",
                        "module_name": "Good",
                        "exact_target_excluded": False,
                        "post_target_forbidden": False,
                        "requires_source_order_check": False,
                        "source_safety_status": "non_target_external_module_candidate",
                        "source_order_status": "not_same_module",
                    },
                    {
                        "name": "Bad.Source",
                        "kind": "theorem",
                        "module_name": "Bad",
                        "exact_target_excluded": False,
                        "post_target_forbidden": False,
                        "requires_source_order_check": False,
                        "source_safety_status": "non_target_external_module_candidate",
                        "source_order_status": "not_same_module",
                    },
                    {
                        "name": "Post.Target",
                        "kind": "theorem",
                        "module_name": "Post",
                        "exact_target_excluded": False,
                        "post_target_forbidden": True,
                        "requires_source_order_check": False,
                        "source_safety_status": "post_target_same_file_forbidden",
                        "source_order_status": "post_target_same_file_forbidden",
                    },
                ],
            }]
        }))
        # import + set_option = lines 1-2, then comment/check pairs.
        fixture.write_text(f"{root}/leansearch_static_filter_probe.lean:6:8: error: unknown constant 'Bad.Source'\n")
        obj = build(packet, root, out, md, 1, lean_output_fixture=fixture)
        row = obj["rows"][0]
        assert row["resolved_count"] == 1, row
        assert row["canary_ready_count"] == 1, row
        assert row["canary_ready_candidates"][0]["name"] == "Good.Source", row
        statuses = {c["name"]: c["resolution_status"] for c in row["candidates"]}
        assert statuses["Bad.Source"] == "name_resolution_failed", statuses
        assert statuses["Post.Target"] == "blocked_before_lean", statuses
        assert "proof" not in json.dumps(obj).lower() or obj["source_policy"]["proof_bodies_persisted"] is False
    print("leansearch_candidate_static_filter self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--packet", default=DEFAULT_PACKET)
    ap.add_argument("--sandbox", default=DEFAULT_SANDBOX)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--markdown", default=DEFAULT_MD)
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--max-candidates-per-row", type=int, default=None)
    ap.add_argument("--no-fallback-per-row", action="store_true")
    ap.add_argument("--fallback-max-rows", type=int, default=200)
    ap.add_argument("--lean-output-fixture")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    obj = build(
        Path(args.packet),
        Path(args.sandbox),
        Path(args.out) if args.out else None,
        Path(args.markdown) if args.markdown else None,
        args.timeout,
        args.max_candidates_per_row,
        Path(args.lean_output_fixture) if args.lean_output_fixture else None,
        not args.no_fallback_per_row,
        args.fallback_max_rows,
    )
    print(json.dumps({
        "out": args.out,
        "markdown": args.markdown,
        "row_count": obj["row_count"],
        "candidate_count": obj["candidate_count"],
        "resolved_total": obj["resolved_total"],
        "canary_ready_total": obj["canary_ready_total"],
        "lean_timed_out": obj["lean_timed_out"],
        "fallback_per_row_used": obj["fallback_per_row_used"],
        "status": obj["status"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
