"""GP-148 Stage 1.5 enrichment — append operator-required fields to the
trajectory archive.

Reads `analytics/public/ledgers/trajectory/trajectory_archive.jsonl` (produced by mine_trajectories.py)
and appends five fields per record:

    active_constraints: list[str]   derived from the project's rubric at iter
                                    time + invariant flags (falsification_mode,
                                    rubric_mode, fit_score_mode). Best-effort
                                    "current state of the rubric" without git
                                    archaeology — flagged with
                                    active_constraints_source: "current" to
                                    indicate it is approximate for historical
                                    iters.

    diff_delta_bytes: int | None    signed byte delta of thesis.md +
                                    test_model.py between iter-1 and iter.
                                    Null for the first iter in a project or
                                    when prior-iter history is unreconstructible.

    run_session_id: str             heuristic — same session if consecutive
                                    iters in the project have a timestamp gap
                                    less than RUN_SESSION_GAP_SECONDS (default
                                    3600). Different session otherwise.

    charter_hash: str               SHA-256 of project_charter.md current text.
                                    Flagged charter_hash_source: "current".

    rubric_hash: str                SHA-256 of rubrics/<project>.json current.
                                    Flagged rubric_hash_source: "current".

The enriched archive is written to `analytics/public/ledgers/trajectory/trajectory_archive_enriched.jsonl`.
The base archive is left untouched.

Idempotent. Runs in under 10 seconds on the current corpus.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
ARCHIVE_IN = REPO / "analytics" / "public" / "ledgers" / "trajectory" / "trajectory_archive.jsonl"
ARCHIVE_OUT = REPO / "analytics" / "public" / "ledgers" / "trajectory" / "trajectory_archive_enriched.jsonl"
PROJECTS_DIR = REPO / "projects"
RUBRICS_DIR = REPO / "rubrics"

RUN_SESSION_GAP_SECONDS = 3600  # 1-hour gap → new session


def sha256_of_path(p: Path) -> str | None:
    if not p.is_file():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def history_iteration_bytes(project_dir: Path, timestamp: int) -> int | None:
    """Look in project history/ for a file matching the iteration timestamp
    and return its byte size. Historical thesis/test_model snapshots in ZTARE
    are named history/<timestamp>_iter<N>_score_<S>_<project>.md.
    """
    history = project_dir / "history"
    if not history.is_dir():
        return None
    prefix = f"{timestamp}_"
    matches = [p for p in history.iterdir() if p.name.startswith(prefix)]
    if not matches:
        return None
    return sum(p.stat().st_size for p in matches if p.is_file())


def derive_active_constraints(rubric_path: Path, charter_path: Path) -> list[str]:
    """Extract a list of constraint-like identifiers currently declared in
    the rubric + charter. Best-effort. Approximate for historical iters
    (see active_constraints_source in record)."""
    active: list[str] = []
    if rubric_path.is_file():
        try:
            rubric = json.loads(rubric_path.read_text())
        except json.JSONDecodeError:
            return active
        # Top-level flags that imply global invariants
        if rubric.get("rubric_mode") == "newton":
            active.append("rubric_mode.newton")
        if rubric.get("rubric_mode") == "kepler":
            active.append("rubric_mode.kepler")
        fs = rubric.get("falsification_mode")
        if fs:
            active.append(f"falsification_mode.{fs}")
        fsm = rubric.get("fit_score_mode")
        if fsm:
            active.append(f"fit_score_mode.{fsm}")
        if rubric.get("enable_fit_primitive"):
            active.append("INV-3_layer3_exclusive")  # implied when fit primitive is on
        if rubric.get("holdout_hard_gate"):
            active.append("holdout_hard_gate")
        if rubric.get("enable_dag_steering"):
            active.append("dag_steering")
        if rubric.get("enable_mform_audit"):
            active.append("mform_alignment_audit")
        # Each dimension is effectively an active constraint
        for d in rubric.get("dimensions", []):
            name = d.get("name", "").lower().replace(" ", "_")[:40]
            if name:
                active.append(f"rubric_dim.{name}")
    # Charter-derived invariants: parse for INV- and GP- references
    if charter_path.is_file():
        txt = charter_path.read_text(errors="ignore")
        for token in ("INV-3", "INV-10", "GP-086", "GP-053", "GP-133", "GP-143", "GP-144", "GP-148"):
            if token in txt:
                active.append(f"charter_refs.{token}")
    return sorted(set(active))


def main() -> None:
    if not ARCHIVE_IN.is_file():
        print(f"ERROR: {ARCHIVE_IN} not found. Run mine_trajectories.py first.", file=sys.stderr)
        sys.exit(1)

    # Group input records by project so we can compute consecutive-iter fields
    print(f"reading {ARCHIVE_IN} ...")
    records_by_project: dict[str, list[dict]] = defaultdict(list)
    raw_count = 0
    with ARCHIVE_IN.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            records_by_project[r["project"]].append(r)
            raw_count += 1
    print(f"  read {raw_count} records across {len(records_by_project)} projects")

    # Sort per-project records by iter_timestamp ascending
    for proj, rs in records_by_project.items():
        rs.sort(key=lambda r: r.get("iter_timestamp") or 0)

    # Enrich
    ARCHIVE_OUT.parent.mkdir(parents=True, exist_ok=True)
    n_out = 0
    with ARCHIVE_OUT.open("w") as out:
        for proj, rs in records_by_project.items():
            project_dir = PROJECTS_DIR / proj
            rubric_path = RUBRICS_DIR / f"{proj}.json"
            charter_path = project_dir / "project_charter.md"
            active = derive_active_constraints(rubric_path, charter_path)
            charter_hash = sha256_of_path(charter_path)
            rubric_hash = sha256_of_path(rubric_path)

            # Compute diff_delta_bytes per iter + run_session_id via gap heuristic
            prev_bytes: int | None = None
            prev_ts: int | None = None
            session_id = 1
            for r in rs:
                ts = r.get("iter_timestamp") or 0
                iter_bytes = history_iteration_bytes(project_dir, ts)
                if iter_bytes is not None and prev_bytes is not None:
                    diff_delta = iter_bytes - prev_bytes
                else:
                    diff_delta = None
                if prev_ts is not None and (ts - prev_ts) > RUN_SESSION_GAP_SECONDS:
                    session_id += 1
                run_session_id = f"{proj}__session_{session_id:03d}"

                enriched = {
                    **r,
                    "active_constraints": active,
                    "active_constraints_source": "current",
                    "diff_delta_bytes": diff_delta,
                    "run_session_id": run_session_id,
                    "charter_hash": charter_hash,
                    "charter_hash_source": "current",
                    "rubric_hash": rubric_hash,
                    "rubric_hash_source": "current",
                }
                out.write(json.dumps(enriched) + "\n")
                n_out += 1

                if iter_bytes is not None:
                    prev_bytes = iter_bytes
                prev_ts = ts

    print(f"  wrote {n_out} enriched records to {ARCHIVE_OUT}")

    # Tiny summary
    print("\n=== quick summary ===")
    print(f"projects covered: {len(records_by_project)}")
    any_active = sum(1 for r in records_by_project for rec in records_by_project[r] if True)
    # Sample: count projects with non-null rubric hash
    proj_with_rubric = sum(
        1 for p in records_by_project
        if (RUBRICS_DIR / f"{p}.json").is_file()
    )
    print(f"projects with a rubric JSON: {proj_with_rubric}/{len(records_by_project)}")
    proj_with_charter = sum(
        1 for p in records_by_project
        if (PROJECTS_DIR / p / "project_charter.md").is_file()
    )
    print(f"projects with a charter file: {proj_with_charter}/{len(records_by_project)}")


if __name__ == "__main__":
    main()
