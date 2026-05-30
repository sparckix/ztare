#!/usr/bin/env python3
"""Apparatus trajectory curves — sophistication, insight, confound.

Implements GP-227 Phase 1. Walks the apparatus's own artifact-creation
record (file mtimes, frontmatter dates, F-row entries) and emits 9
weekly time-series:

  Sophistication (the apparatus is more capable):
    A. Capability count — cumulative cage gates registered + seams
       opened + mandates authored
    D. Autonomous-action density — events emitted to cage_engagement.jsonl
       per project run, aggregated by week the project ran

  Insight (the apparatus produces more findings):
    Insight-A. F-row creation rate — new E-rows / week
    Insight-B. F-row closure rate — verified + falsified_with_finding
       per week (objective closures)

  Confound (might mimic apparatus acceleration):
    Confound-A. File-mtime density across src/ztare/ + scripts/public/
    Confound-B. Total artifact-creation rate across the repo
    Confound-C. External event timeline (from external_events.yaml)

  Sophistication-B and -C (recursive depth, operator-labor-displaced)
  are operator-curated metrics; this miner emits placeholders the
  operator fills in via inflection_points.yaml after seeing curves.

Outputs:
  ``analytics/public/queries/trajectory_curves.{json,md}``

Pure CPU, no LLM, no git (uses filesystem mtime + frontmatter dates +
F-row table).

Usage:
    python scripts/public/mining/mine_trajectory_curves.py
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import yaml  # type: ignore[import-untyped]

REPO = Path(__file__).resolve().parents[3]
F_ROWS_PATH = REPO / "research_areas" / "EXPERIMENT_TRACK_RECORD.md"
EXTERNAL_EVENTS_PATH = REPO / "org" / "runtime" / "external_events.yaml"
OUT_JSON = REPO / "analytics" / "public" / "queries" / "trajectory" / "trajectory_curves.json"
OUT_MD = REPO / "analytics" / "public" / "queries" / "trajectory" / "trajectory_curves.md"

# Soph-A inputs — exhaustive scan of every apparatus generator dir.
# Operator emphasized 2026-05-06: "mine exhaustively from filesystem,
# not git". This list expands to cover ALL dirs that hold apparatus
# components whose creation represents a sophistication step.
SOPH_A_DIRS = [
    # Source code — all subdirs of src/ztare/, not just gates
    "src/ztare/gates",
    "src/ztare/orchestrator",
    "src/ztare/validator",
    "src/ztare/diagnostics",
    "src/ztare/fit",
    "src/ztare/framer",
    "src/ztare/motion",
    "src/ztare/composition",
    "src/ztare/substrates",
    "src/ztare/workspace",
    "src/ztare/common",
    # Org primitives
    "org/mandates",
    "org/key_results",
    "org/objectives",
    "org/signals",
    "org/roles",
    "org/charters",
    "org/runtime",
    "org/directives",
    "org/preferences",
    "org/controls",
    "org/gates",
    "org/tasks",
    "org/members",
    # Seams (apparatus thinking trail)
    "research_areas/private/seams",
    "research_areas/private/evidence",
    "research_areas/private/philosophy",
    # Scripts (mining + audits + utilities)
    "scripts/public/mining",
    "scripts",  # top-level scripts (audit_*, etc)
    # Concept docs (apparatus thinking codified)
    "docs/concepts",
    "docs/internal",
    "docs/guides",
    # Analytics outputs (past mining results — apparatus history)
    "analytics/public/queries",
    # Specs
    "specs",
]

# Insight content dirs — these are OUTPUTS of the apparatus
# (operator-authored or apparatus-emitted), not Sophistication
# (apparatus capability). Papers + project workspaces live here.
INSIGHT_CONTENT_DIRS = [
    "papers",                   # operator-authored paper drafts
    "projects",                 # 186 project workspaces with debate logs,
                                # evaluations, evidence files, verified axioms
]

# Confound-A: code activity (file mtime density on src + scripts)
CONFOUND_A_DIRS = ["src", "scripts"]

# Confound-B: total artifact density across the repo (apparatus +
# non-apparatus). Excludes vendored / build dirs.
PATH_EXCLUDES = {
    "node_modules", "venv", ".venv", "__pycache__", ".git", "orbit",
    "dist", "build", "site-packages", ".pytest_cache", ".ruff_cache",
}


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
_DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")


def _read_frontmatter_date(path: Path) -> Optional[datetime]:
    """Return frontmatter creation/opened/discovered date if present."""
    if path.suffix.lower() != ".md":
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")[:2048]
    except Exception:  # noqa: BLE001
        return None
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(fm, dict):
        return None
    for key in ("opened", "discovered", "authored", "created", "date"):
        v = fm.get(key)
        if v:
            ds = str(v).strip()
            md = _DATE_RE.search(ds)
            if md:
                try:
                    return datetime.fromisoformat(md.group(1)).replace(tzinfo=timezone.utc)
                except Exception:  # noqa: BLE001
                    pass
    return None


def _file_create_date(path: Path) -> datetime:
    """Best-effort creation date: frontmatter > stat birthtime > mtime."""
    fm = _read_frontmatter_date(path)
    if fm:
        return fm
    try:
        st = path.stat()
        # macOS has st_birthtime; linux has only st_mtime
        ts = getattr(st, "st_birthtime", st.st_mtime)
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except Exception:  # noqa: BLE001
        return datetime.now(timezone.utc)


def _week_bucket(dt: datetime) -> str:
    """ISO week-start (Monday) as YYYY-MM-DD."""
    monday = dt - timedelta(days=dt.weekday())
    return monday.strftime("%Y-%m-%d")


def _walk_files(root: Path) -> list[Path]:
    out = []
    if not root.exists():
        return out
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in PATH_EXCLUDES or part.startswith(".") for part in p.relative_to(REPO).parts):
            continue
        out.append(p)
    return out


def _collect_soph_a() -> dict[str, int]:
    """Cumulative count by week (week-monday → cumulative count up to that week)."""
    week_counts: dict[str, int] = defaultdict(int)
    seen: set[Path] = set()
    for d in SOPH_A_DIRS:
        for p in _walk_files(REPO / d):
            if p in seen:
                continue
            seen.add(p)
            if p.suffix.lower() not in {".py", ".md", ".yaml", ".yml"}:
                continue
            wk = _week_bucket(_file_create_date(p))
            week_counts[wk] += 1
    sorted_weeks = sorted(week_counts.keys())
    cumulative: dict[str, int] = {}
    running = 0
    for wk in sorted_weeks:
        running += week_counts[wk]
        cumulative[wk] = running
    return cumulative


def _collect_soph_d() -> dict[str, int]:
    """Cage-engagement events per week. Each event line has its own
    ``utc`` field; bin by that timestamp, NOT by file mtime — file
    mtime is the LAST event in the file, lumping all earlier events
    into one week."""
    week_events: dict[str, int] = defaultdict(int)
    projects_dir = REPO / "projects"
    if not projects_dir.exists():
        return week_events
    for proj in projects_dir.iterdir():
        if not proj.is_dir():
            continue
        cage = proj / "workspace" / "cage_engagement.jsonl"
        if not cage.exists():
            continue
        try:
            for line in cage.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:  # noqa: BLE001
                    continue
                utc_str = rec.get("utc")
                if not isinstance(utc_str, str):
                    continue
                try:
                    dt = datetime.fromisoformat(utc_str)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                except Exception:  # noqa: BLE001
                    continue
                wk = _week_bucket(dt)
                # Each line counts as one cage-event per gate engaged
                # (engaged_count gives autonomous-action count for this iter).
                n = rec.get("engaged_count")
                if not isinstance(n, int) or n < 0:
                    n = 1
                week_events[wk] += n
        except Exception:  # noqa: BLE001
            continue
    return dict(week_events)


def _collect_insight_c_paper_growth() -> dict[str, int]:
    """Insight-C: paper-content growth — new files in papers/* per
    week, weighted by line-count (so a 500-line draft addition counts
    more than a 5-line README)."""
    week_lines: dict[str, int] = defaultdict(int)
    for p in _walk_files(REPO / "papers"):
        if p.suffix.lower() not in {".md", ".tex"}:
            continue
        wk = _week_bucket(_file_create_date(p))
        try:
            n_lines = sum(1 for _ in p.read_text(encoding="utf-8", errors="ignore").splitlines())
        except Exception:  # noqa: BLE001
            n_lines = 1
        week_lines[wk] += n_lines
    return dict(week_lines)


def _collect_insight_d_project_artifacts() -> dict[str, int]:
    """Insight-D: project-workspace artifact creation per week.

    Walks projects/*/workspace/* + projects/*/*.md / *.json
    (debate_log.md, evaluation_*.json, score_history.jsonl, etc).
    Each artifact is one creation event; date from frontmatter / mtime.

    Captures the apparatus-emitted insight production (debate logs,
    evaluations, evidence files, verified-axioms, etc.) that the
    F-row table misses because operator F-row updates lag actual work.
    """
    week_counts: dict[str, int] = defaultdict(int)
    projects_dir = REPO / "projects"
    if not projects_dir.exists():
        return week_counts
    for proj in projects_dir.iterdir():
        if not proj.is_dir():
            continue
        # Walk all files in the project, not just workspace/, but
        # cap depth to avoid scanning generated subtrees.
        for p in proj.rglob("*"):
            if not p.is_file():
                continue
            ext = p.suffix.lower()
            if ext not in {".md", ".json", ".jsonl", ".py", ".yaml"}:
                continue
            # Skip large generated artifacts that aren't insight content
            name = p.name
            if name.startswith(".") or name in {"__pycache__"}:
                continue
            # Skip the cage_engagement.jsonl — already counted in Soph-D
            if name == "cage_engagement.jsonl":
                continue
            try:
                wk = _week_bucket(_file_create_date(p))
                week_counts[wk] += 1
            except Exception:  # noqa: BLE001
                continue
    return dict(week_counts)


def _collect_insight_e_verified_axioms() -> dict[str, int]:
    """Insight-E: verified-axiom additions per week.

    Walks projects/*/verified_axioms.json. Each axiom-string is one
    insight unit; date attributed by file mtime (we don't have
    per-axiom timestamps inside the JSON)."""
    week_axioms: dict[str, int] = defaultdict(int)
    projects_dir = REPO / "projects"
    if not projects_dir.exists():
        return week_axioms
    for path in projects_dir.glob("*/verified_axioms.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        axioms_list = (
            data if isinstance(data, list)
            else (data.get("axioms", []) if isinstance(data, dict) else [])
        )
        # Skip sentinel "no inherited truth" entries
        n = sum(
            1 for ax in axioms_list
            if ax and "inherited truth" not in str(ax).lower()
        )
        if n == 0:
            continue
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            wk = _week_bucket(mtime)
            week_axioms[wk] += n
        except Exception:  # noqa: BLE001
            continue
    return dict(week_axioms)


def _collect_insight_a_b() -> tuple[dict[str, int], dict[str, int]]:
    """Insight-A: F-rows created per week. Insight-B: closures per week.

    F-rows have format ``| E-{ID} | {date or other} | ... | status |``.
    We classify status text via simple regex (mirrors mine_closure_patterns).
    """
    if not F_ROWS_PATH.exists():
        return {}, {}
    text = F_ROWS_PATH.read_text(encoding="utf-8", errors="ignore")
    creates: dict[str, int] = defaultdict(int)
    closures: dict[str, int] = defaultdict(int)
    closure_re = re.compile(
        r"\b(verified|theorem proven|machine-?check|falsified.*finding|"
        r"counterexample.*found)\b",
        re.I,
    )
    for line in text.splitlines():
        if not line.startswith("| E-"):
            continue
        m = _DATE_RE.search(line)
        if not m:
            continue
        try:
            d = datetime.fromisoformat(m.group(1)).replace(tzinfo=timezone.utc)
        except Exception:  # noqa: BLE001
            continue
        wk = _week_bucket(d)
        creates[wk] += 1
        if closure_re.search(line):
            closures[wk] += 1
    return dict(creates), dict(closures)


def _collect_confound_a() -> dict[str, int]:
    """Code-activity proxy: file mtime density on src/ztare + scripts."""
    week_counts: dict[str, int] = defaultdict(int)
    for d in CONFOUND_A_DIRS:
        for p in _walk_files(REPO / d):
            if p.suffix.lower() not in {".py", ".md", ".yaml"}:
                continue
            try:
                mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
                wk = _week_bucket(mtime)
                week_counts[wk] += 1
            except Exception:  # noqa: BLE001
                continue
    return dict(week_counts)


def _collect_confound_b() -> dict[str, int]:
    """Total apparatus-creation rate: NEW files per week across the repo."""
    week_counts: dict[str, int] = defaultdict(int)
    for top in ("src", "scripts", "research_areas", "org", "papers", "docs", "analytics"):
        for p in _walk_files(REPO / top):
            if p.suffix.lower() not in {".py", ".md", ".yaml", ".json"}:
                continue
            wk = _week_bucket(_file_create_date(p))
            week_counts[wk] += 1
    return dict(week_counts)


def _load_external_events() -> list[dict]:
    if not EXTERNAL_EVENTS_PATH.exists():
        return []
    try:
        data = yaml.safe_load(EXTERNAL_EVENTS_PATH.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return []
    return data.get("events", []) or []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    args = ap.parse_args()

    print("=== trajectory curves miner ===")

    soph_a = _collect_soph_a()
    print(f"  Sophistication-A (capability count): {len(soph_a)} weeks")
    soph_d = _collect_soph_d()
    print(f"  Sophistication-D (autonomous actions): {len(soph_d)} weeks")
    ins_a, ins_b = _collect_insight_a_b()
    print(f"  Insight-A (F-row creates): {len(ins_a)} weeks")
    print(f"  Insight-B (F-row closures): {len(ins_b)} weeks")
    # Insight-C (paper LINE growth) REMOVED 2026-05-17 — line count is a
    # gameable, self-defeating proxy (more lines ≠ more value). Operator-
    # directed: do not compute or surface it as a metric anywhere.
    ins_d = _collect_insight_d_project_artifacts()
    print(f"  Insight-D (project workspace artifacts): {len(ins_d)} weeks")
    ins_e = _collect_insight_e_verified_axioms()
    print(f"  Insight-E (verified-axioms additions): {len(ins_e)} weeks")
    conf_a = _collect_confound_a()
    print(f"  Confound-A (code activity): {len(conf_a)} weeks")
    conf_b = _collect_confound_b()
    print(f"  Confound-B (total artifact creation): {len(conf_b)} weeks")
    events = _load_external_events()
    print(f"  Confound-C (external events): {len(events)} events")

    all_weeks = sorted(
        set(soph_a) | set(soph_d) | set(ins_a) | set(ins_b)
        | set(ins_d) | set(ins_e)
        | set(conf_a) | set(conf_b)
    )

    payload = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "n_weeks": len(all_weeks),
        "weeks": all_weeks,
        "curves": {
            "sophistication_a_capability_count_cumulative": soph_a,
            "sophistication_d_autonomous_actions_per_week": soph_d,
            "insight_a_f_row_creates_per_week": ins_a,
            "insight_b_f_row_closures_per_week": ins_b,
            "insight_d_project_workspace_artifacts_per_week": ins_d,
            "insight_e_verified_axioms_added_per_week": ins_e,
            "confound_a_code_activity_density": conf_a,
            "confound_b_total_artifact_creation_per_week": conf_b,
        },
        "external_events": events,
        "notes": [
            "Sophistication-B (recursive depth) and Sophistication-C (operator-labor-displaced) "
            "are operator-curated; not generated here. Add as inflection annotations after curves are reviewed.",
            "Sham-arm comparison (running same metrics on a non-apparatus dir): "
            "use --sham-dir flag (not yet implemented; ship after first review).",
        ],
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2, default=str))
    print(f"  wrote {args.out_json}")

    md = ["# Apparatus Trajectory Curves\n"]
    md.append(f"_Generated {payload['audit_timestamp_utc']}_  ")
    md.append(f"_Weeks observed:_ {len(all_weeks)}  _External events:_ {len(events)}\n")
    md.append("## Weekly time series (raw counts)\n")
    md.append(
        "| Week | Soph-A cap | Soph-D auto | "
        "Ins-A creates | Ins-B closures | "
        "Ins-D proj-artifacts | Ins-E axioms | "
        "Conf-A activity | Conf-B all-creates |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    )
    for wk in all_weeks:
        md.append(
            f"| {wk} | {soph_a.get(wk, '')} | {soph_d.get(wk, 0)} | "
            f"{ins_a.get(wk, 0)} | {ins_b.get(wk, 0)} | "
            f"{ins_d.get(wk, 0)} | {ins_e.get(wk, 0)} | "
            f"{conf_a.get(wk, 0)} | {conf_b.get(wk, 0)} |"
        )
    md.append("")
    if events:
        md.append("## External events (Confound-C)\n")
        md.append("| Date | Kind | Label |\n|---|---|---|")
        for e in sorted(events, key=lambda x: x.get("date", "")):
            md.append(f"| {e.get('date', '')} | `{e.get('kind', '')}` | {e.get('label', '')} |")
        md.append("")
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(md) + "\n")
    print(f"  wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
