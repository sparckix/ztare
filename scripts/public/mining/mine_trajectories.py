#!/usr/bin/env python3
"""Stage 1 extractor: build a unified JSONL archive of ZTARE iteration trajectories.

Walks /projects/*/, emits one JSON record per
iteration (one line per iteration) to
/analytics/public/ledgers/trajectory/trajectory_archive.jsonl.

No analysis; extraction only. Standard library only.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Iterator

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
PROJECTS_DIR = ROOT / "projects"
RUBRICS_DIR = ROOT / "rubrics"
ARCHIVE_PATH = ROOT / "analytics" / "public" / "ledgers" / "trajectory" / "trajectory_archive.jsonl"

DEBATE_LOG_RE = re.compile(r"^debate_log_iter_(\d+)\.md$")
SCORE_RE = re.compile(r"^#\s*Final\s+Score:\s*(-?\d+)", re.MULTILINE)
WEAKEST_RE = re.compile(r"^\*\*Weakest Point:\*\*\s*(.+?)\s*$", re.MULTILINE)
RATIONALE_RE = re.compile(r"^\*\*Rationale:\*\*\s*(.+?)\s*$", re.MULTILINE)
PRIMITIVE_RE = re.compile(r"^### Primitive \d+:\s*([^\n]+)$", re.MULTILINE)
BEST_ITER_RE = re.compile(r"best_iteration:\s*(\d+)_iter(\d+)_score_(-?\d+)")


def warn(msg: str) -> None:
    print(f"[warn] {msg}", file=sys.stderr)


def read_text_safe(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        warn(f"read failed {path}: {exc}")
        return None


def iter_projects() -> Iterator[Path]:
    if not PROJECTS_DIR.is_dir():
        return
    for entry in sorted(PROJECTS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        charter = entry / "project_charter.md"
        if not charter.is_file():
            continue
        # require at least one debate log
        try:
            has_log = any(DEBATE_LOG_RE.match(p.name) for p in entry.iterdir())
        except OSError as exc:
            warn(f"list failed {entry}: {exc}")
            continue
        if not has_log:
            continue
        yield entry


def parse_debate_log(path: Path) -> dict[str, Any]:
    out: dict[str, Any] = {"score": None, "weakest_point": None, "rationale": None}
    text = read_text_safe(path)
    if text is None:
        return out
    m = SCORE_RE.search(text)
    if m:
        try:
            out["score"] = int(m.group(1))
        except ValueError:
            warn(f"bad score in {path}")
    m = WEAKEST_RE.search(text)
    if m:
        out["weakest_point"] = m.group(1).strip()
    m = RATIONALE_RE.search(text)
    if m:
        out["rationale"] = m.group(1).strip()
    return out


def load_telemetry(project_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Return (iteration_records, run_start_record_or_None).

    Iteration records are those with record_type == 'iteration' (or any record
    that looks like an iteration — has iteration_index). Order preserved.
    """
    tele_path = project_dir / "workspace" / "iteration_telemetry.jsonl"
    if not tele_path.is_file():
        return [], None
    iters: list[dict[str, Any]] = []
    run_start: dict[str, Any] | None = None
    try:
        with tele_path.open("r", encoding="utf-8", errors="replace") as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError as exc:
                    warn(f"telemetry parse error {tele_path}:{lineno}: {exc}")
                    continue
                rtype = rec.get("record_type")
                if rtype == "run_start" and run_start is None:
                    run_start = rec
                elif rtype == "iteration" or "iteration_index" in rec:
                    iters.append(rec)
    except OSError as exc:
        warn(f"telemetry read failed {tele_path}: {exc}")
    return iters, run_start


def load_rubric_version(project_slug: str) -> str | None:
    path = RUBRICS_DIR / f"{project_slug}.json"
    if not path.is_file():
        return None
    text = read_text_safe(path)
    if text is None:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        warn(f"rubric parse error {path}: {exc}")
        return None
    rv = data.get("rubric_version")
    if rv is None:
        return None
    return str(rv)


def load_current_iteration(project_dir: Path) -> tuple[list[str], int | None]:
    """Return (primitive_names, best_iteration_timestamp_or_None).

    Primitives are extracted from ### Primitive N: <name> headers.
    The best_iteration marker (if present) lets us check whether the
    current_iteration.md reflects a specific debate log's timestamp.
    """
    path = project_dir / "current_iteration.md"
    if not path.is_file():
        return [], None
    text = read_text_safe(path)
    if text is None:
        return [], None
    names = [m.group(1).strip() for m in PRIMITIVE_RE.finditer(text)]
    best_ts: int | None = None
    m = BEST_ITER_RE.search(text)
    if m:
        try:
            best_ts = int(m.group(1))
        except ValueError:
            pass
    return names, best_ts


def match_telemetry(
    iter_ts: int,
    idx_in_project: int,
    telemetry_iters: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Match a debate log to a telemetry record.

    Strategy:
      1. Prefer timestamp-based matching: any telemetry record whose
         iteration_start_utc / iteration_end_utc brackets iter_ts (allowing
         small slack) or whose run-start-relative index hints at the same
         iteration. If telemetry has an 'iteration_timestamp' field, use it.
      2. Fallback: positional match — iter N-th debate log (chronologically)
         to N-th iteration record.
    """
    # Positional fallback is usually what ZTARE supports; the debate logs are
    # named by their completion unix timestamp, and telemetry records are in
    # iteration_index order. We use positional matching as the primary path,
    # since iteration_end_utc is ISO-formatted and comparing across that and
    # the debate log mtime drifted in our sample. Positional is deterministic.
    if idx_in_project < len(telemetry_iters):
        return telemetry_iters[idx_in_project]
    return None


def build_record(
    project_slug: str,
    debate_log: Path,
    iter_ts: int,
    idx_in_project: int,
    telemetry_iters: list[dict[str, Any]],
    run_start: dict[str, Any] | None,
    rubric_version: str | None,
    primitive_names: list[str],
    primitive_ts: int | None,
) -> dict[str, Any]:
    parsed = parse_debate_log(debate_log)
    tele = match_telemetry(iter_ts, idx_in_project, telemetry_iters)

    def tget(key: str, default: Any = None) -> Any:
        if tele is None:
            return default
        return tele.get(key, default)

    # Fall back to run_start for model ids / falsification_mode if the per-iter
    # record omits them.
    def tget_or_runstart(key: str, alt_key: str | None = None) -> Any:
        v = tget(key)
        if v is not None:
            return v
        if run_start is not None:
            v = run_start.get(key)
            if v is not None:
                return v
            if alt_key is not None:
                return run_start.get(alt_key)
        return None

    # Only attach primitives to the iteration referenced by current_iteration.md
    # (best_iteration marker). Otherwise emit an empty list — Stage 2 can
    # still attach by joining on (project, iter_ts) if needed.
    attached_primitives: list[str] = []
    if primitive_ts is not None and primitive_ts == iter_ts:
        attached_primitives = list(primitive_names)

    return {
        "project": project_slug,
        "iter_timestamp": iter_ts,
        "iteration_index": tget("iteration_index"),
        "score": parsed["score"],
        "weakest_point": parsed["weakest_point"],
        "rationale": parsed["rationale"],
        "failed_gate_ids": tget("failed_gate_ids", []),
        "gate_engagement": tget("gate_engagement"),
        "gate_failure_count": tget("gate_failure_count"),
        "stagnation_count": tget("stagnation_count"),
        "falsification_mode": tget_or_runstart("falsification_mode"),
        "mutator_model_id": tget_or_runstart("mutator_model_id", "mutator_model"),
        "judge_model_id": tget_or_runstart("judge_model_id", "judge_model"),
        "rubric_version": rubric_version,
        "thesis_primitive_names": attached_primitives,
        "champion_promoted": tget("champion_promoted"),
        "score_improved": tget("score_improved"),
    }


def iter_debate_logs(project_dir: Path) -> list[tuple[int, Path]]:
    pairs: list[tuple[int, Path]] = []
    try:
        for p in project_dir.iterdir():
            m = DEBATE_LOG_RE.match(p.name)
            if not m:
                continue
            try:
                ts = int(m.group(1))
            except ValueError:
                warn(f"bad timestamp in filename {p}")
                continue
            pairs.append((ts, p))
    except OSError as exc:
        warn(f"list failed {project_dir}: {exc}")
    pairs.sort(key=lambda x: x[0])
    return pairs


def extract_all(archive_path: Path) -> tuple[int, int, Counter]:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    scored = 0
    per_project: Counter[str] = Counter()

    with archive_path.open("w", encoding="utf-8") as out:
        for project_dir in iter_projects():
            slug = project_dir.name
            logs = iter_debate_logs(project_dir)
            if not logs:
                continue
            telemetry_iters, run_start = load_telemetry(project_dir)
            rubric_version = load_rubric_version(slug)
            primitive_names, primitive_ts = load_current_iteration(project_dir)

            for idx, (ts, log_path) in enumerate(logs):
                try:
                    rec = build_record(
                        project_slug=slug,
                        debate_log=log_path,
                        iter_ts=ts,
                        idx_in_project=idx,
                        telemetry_iters=telemetry_iters,
                        run_start=run_start,
                        rubric_version=rubric_version,
                        primitive_names=primitive_names,
                        primitive_ts=primitive_ts,
                    )
                except Exception as exc:  # noqa: BLE001 — defensive per spec
                    warn(f"record build failed {log_path}: {exc}")
                    continue
                out.write(json.dumps(rec, ensure_ascii=False, sort_keys=True))
                out.write("\n")
                total += 1
                if rec["score"] is not None:
                    scored += 1
                per_project[slug] += 1
    return total, scored, per_project


def main() -> int:
    total, scored, per_project = extract_all(ARCHIVE_PATH)
    null_scores = total - scored
    print(f"total_records={total}")
    print(f"records_with_score={scored}")
    print(f"records_with_null_score={null_scores}")
    print("top_projects_by_iter_count:")
    for slug, count in per_project.most_common(10):
        print(f"  {slug}\t{count}")
    print(f"archive_path={ARCHIVE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
