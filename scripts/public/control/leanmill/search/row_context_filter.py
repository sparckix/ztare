#!/usr/bin/env python3
"""Check LeanSearch candidates in each row's actual module context.

`leansearch_candidate_static_filter.py` checks names under `import Mathlib`.
That is useful for global availability, but replay happens inside the
original sorried module file, whose imports, namespace, and source order may
be narrower. This filter inserts `#check` lines immediately before the target
declaration and records which candidates resolve at the proof site.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[5]
DEFAULT_CORPUS = "/tmp/rung1/mcb_corpus_v2.json"
DEFAULT_STATIC_FILTER = "analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_STATIC_FILTER.json"
DEFAULT_OUT = "analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_ROW_CONTEXT_FILTER.json"
DEFAULT_MD = "analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_ROW_CONTEXT_FILTER.md"


def _read_rows(path: Path) -> list[dict[str, Any]]:
    obj = json.loads(path.read_text(errors="ignore"))
    if isinstance(obj, list):
        return obj
    return list(obj.get("rows") or obj.get("corpus") or obj.get("targets") or [])


def _row_map(path: Path) -> dict[str, dict[str, Any]]:
    return {str(r.get("id") or r.get("row_id")): r for r in _read_rows(path)}


def _run_lean(path: Path, timeout: int) -> dict[str, Any]:
    start = time.time()
    try:
        import sys
        sys.path.insert(0, str(REPO / "scripts/public/control"))
        import coherent_rung1 as cr
        cwd = Path(cr.SB)
    except Exception:
        cwd = REPO / "ztare_proofs"
    cmd = f"cd {shlex.quote(str(cwd))} && lake env lean {shlex.quote(str(path))}"
    try:
        proc = subprocess.run(
            ["bash", "-lc", cmd],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        proc = exc
        timed_out = True
    stdout = getattr(proc, "stdout", "") or ""
    stderr = getattr(proc, "stderr", "") or ""
    rc = None if timed_out else int(getattr(proc, "returncode", 1))
    return {
        "returncode": rc,
        "timed_out": timed_out,
        "seconds": round(time.time() - start, 3),
        "stdout": stdout,
        "stderr": stderr,
    }


def _error_lines(text: str) -> set[int]:
    out: set[int] = set()
    for m in re.finditer(r"(?m)^.*\.lean:(\d+):\d+: error", text):
        out.add(int(m.group(1)))
    return out


def _error_sample(text: str, line: int) -> str:
    pat = re.compile(rf"(?m)^.*\.lean:{line}:\d+: error.*(?:\n(?!.*\.lean:\d+:\d+:).*)*")
    m = pat.search(text)
    return (m.group(0).strip()[:500] if m else "")


def _static_rows(path: Path) -> list[dict[str, Any]]:
    obj = json.loads(path.read_text(errors="ignore"))
    return [r for r in (obj.get("rows") or []) if not str(r.get("row_id", "")).startswith("__")]


def _target_insertion_index(lines: list[str], target_line: int) -> int:
    idx = max(0, min(len(lines), target_line - 1))
    prev = idx - 1
    while prev >= 0 and not lines[prev].strip():
        prev -= 1
    if prev >= 0 and "-/" in lines[prev]:
        cur = prev
        while cur >= 0:
            if "/--" in lines[cur]:
                return cur
            cur -= 1
    return idx


def _payload(corpus: Path, static_filter: Path, rows_out: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "leansearch-row-context-filter-v1",
        "corpus": str(corpus),
        "static_filter": str(static_filter),
        "row_count": len(rows_out),
        "candidate_count": sum(r["candidate_count"] for r in rows_out),
        "row_context_ready_total": sum(r["row_context_resolved_count"] for r in rows_out),
        "rows": rows_out,
        "source_policy": {
            "row_import_context_checked": True,
            "target_site_context_checked": True,
            "no_replay_or_training": True,
            "path_b_required_before_any_closure_credit": True,
        },
    }


def _write_progress(partial_out: Path | None, checkpoint_jsonl: Path | None,
                    corpus: Path, static_filter: Path,
                    rows_out: list[dict[str, Any]], row: dict[str, Any]) -> None:
    if partial_out:
        partial_out.parent.mkdir(parents=True, exist_ok=True)
        partial_out.write_text(json.dumps(_payload(corpus, static_filter, rows_out), indent=2, sort_keys=True) + "\n")
    if checkpoint_jsonl:
        checkpoint_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with checkpoint_jsonl.open("a") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def build(corpus: Path, static_filter: Path, out: Path | None, markdown: Path | None,
          timeout: int, max_candidates_per_row: int | None = None,
          row_id: str | None = None, partial_out: Path | None = None,
          checkpoint_jsonl: Path | None = None) -> dict[str, Any]:
    rows_by_id = _row_map(corpus)
    rows_out: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="leansearch_row_context_") as td:
        root = Path(td)
        for sf_row in _static_rows(static_filter):
            rid = str(sf_row.get("row_id") or "")
            if row_id and rid != row_id:
                continue
            corpus_row = rows_by_id.get(rid)
            if not corpus_row:
                out_row = {
                    "row_id": rid,
                    "status": "missing_corpus_row",
                    "candidate_count": 0,
                    "row_context_resolved_count": 0,
                    "row_context_ready_candidates": [],
                    "candidates": [],
                }
                rows_out.append(out_row)
                _write_progress(partial_out, checkpoint_jsonl, corpus, static_filter, rows_out, out_row)
                continue
            candidates = list(sf_row.get("canary_ready_candidates") or [])
            if max_candidates_per_row is not None:
                candidates = candidates[:max_candidates_per_row]
            src_path = Path(str(corpus_row.get("sorried_file") or ""))
            src = src_path.read_text(errors="ignore")
            lines = src.splitlines()
            insert_idx = _target_insertion_index(lines, int(corpus_row.get("target_line") or 1))
            line_map: dict[int, int] = {}
            inserted = ["/- ztare target-context LeanSearch candidate checks -/"]
            for i, cand in enumerate(candidates):
                inserted.append(f"-- CANDIDATE {i} {cand.get('name')}")
                line_no = insert_idx + len(inserted) + 1
                inserted.append(f"#check {cand.get('name')}")
                line_map[line_no] = i
            probe = root / f"{re.sub(r'[^A-Za-z0-9_]+', '_', rid)}.lean"
            probe_lines = lines[:insert_idx] + inserted + [""] + lines[insert_idx:]
            probe.write_text("\n".join(probe_lines) + "\n")
            res = _run_lean(probe, timeout)
            text = f"{res.get('stdout', '')}\n{res.get('stderr', '')}"
            err_lines = _error_lines(text)
            cand_out: list[dict[str, Any]] = []
            for i, cand in enumerate(candidates):
                line = next((ln for ln, idx in line_map.items() if idx == i), None)
                failed = bool(line in err_lines)
                resolves = not failed and not res.get("timed_out")
                cand_out.append({
                    "name": cand.get("name"),
                    "kind": cand.get("kind"),
                    "global_name_resolves": cand.get("name_resolves"),
                    "row_context_resolves": resolves,
                    "target_context_resolves": resolves,
                    "check_line": line,
                    "error_sample": _error_sample(text, int(line)) if failed and line else "",
                })
            # If the row file has unrelated errors before appended checks, keep candidates conservative.
            unmapped = sorted(ln for ln in err_lines if ln not in line_map)
            if unmapped:
                for c in cand_out:
                    if c["row_context_resolves"]:
                        c["row_context_resolves"] = False
                        c["error_sample"] = c["error_sample"] or "unmapped_row_context_error_before_or_around_checks"
            ready = [c for c in cand_out if c["row_context_resolves"]]
            out_row = {
                "row_id": rid,
                "status": "checked",
                "source_file": corpus_row.get("sorried_file"),
                "returncode": res.get("returncode"),
                "timed_out": res.get("timed_out"),
                "seconds": res.get("seconds"),
                "target_line": corpus_row.get("target_line"),
                "candidate_count": len(cand_out),
                "row_context_resolved_count": len(ready),
                "unmapped_error_lines": unmapped,
                "row_context_ready_candidates": ready,
                "candidates": cand_out,
                "stdout_tail": str(res.get("stdout", ""))[-1000:],
                "stderr_tail": str(res.get("stderr", ""))[-1000:],
            }
            rows_out.append(out_row)
            _write_progress(partial_out, checkpoint_jsonl, corpus, static_filter, rows_out, out_row)
    payload = _payload(corpus, static_filter, rows_out)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if markdown:
        _write_md(payload, markdown)
    return payload


def _write_md(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# LeanSearch Row-Context Filter",
        "",
        f"Rows: `{payload['row_count']}`",
        f"Candidates checked: `{payload['candidate_count']}`",
        f"Row-context ready candidates: `{payload['row_context_ready_total']}`",
        "",
        "| Row | Ready | Top Row-Context Candidates |",
        "|---|---:|---|",
    ]
    for row in payload["rows"]:
        names = ", ".join(f"`{c['name']}`" for c in row["row_context_ready_candidates"][:5])
        lines.append(f"| `{row['row_id']}` | {row['row_context_resolved_count']} | {names} |")
    lines.append("")
    lines.append("Boundary: target-site name resolution only; no proof replay or closure credit.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def _self_test() -> int:
    assert _error_lines("/tmp/x.lean:3:4: error: bad") == {3}
    assert "error" in _error_sample("/tmp/x.lean:3:4: error: bad\nmore", 3)
    assert _target_insertion_index(["/-- doc", "-/", "theorem x"], 3) == 0
    assert _target_insertion_index(["def y := 1", "theorem x"], 2) == 1
    print("leansearch_row_context_filter self-test PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--static-filter", default=DEFAULT_STATIC_FILTER)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--markdown", default=DEFAULT_MD)
    ap.add_argument("--timeout", type=int, default=75)
    ap.add_argument("--max-candidates-per-row", type=int, default=4)
    ap.add_argument("--row-id")
    ap.add_argument("--partial-out")
    ap.add_argument("--checkpoint-jsonl")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    obj = build(
        Path(args.corpus),
        Path(args.static_filter),
        Path(args.out) if args.out else None,
        Path(args.markdown) if args.markdown else None,
        args.timeout,
        args.max_candidates_per_row,
        args.row_id,
        Path(args.partial_out) if args.partial_out else None,
        Path(args.checkpoint_jsonl) if args.checkpoint_jsonl else None,
    )
    print(json.dumps({
        "out": args.out,
        "markdown": args.markdown,
        "row_count": obj["row_count"],
        "candidate_count": obj["candidate_count"],
        "row_context_ready_total": obj["row_context_ready_total"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
