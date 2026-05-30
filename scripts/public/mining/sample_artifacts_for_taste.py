#!/usr/bin/env python3
"""Sample apparatus artifacts for taste rating.

GP-227 follow-up: deterministic volume mining counts how much was
created per week, but not whether it was insight-rich or boilerplate.
This sampler picks ~10 representative artifacts per week from
Insight-relevant sources and emits a single markdown document where
each artifact has a unique ID (SAMPLE_NNN) but **its week label is
withheld from the visible content** to reduce rater bias toward
recent / familiar work.

The rater (Claude in the active conversation, or a future LLM call)
reads the document, scores each SAMPLE_NNN on insight density 0-5
with a one-line rationale, and writes a CSV / markdown table of
ratings. The aggregator (aggregate_taste.py) joins ratings with
the metadata sidecar (which has the week info) and produces
taste-weighted insight curves.

Sample sources (per week):
  - F-rows from EXPERIMENT_TRACK_RECORD.md
  - Seam files (research_areas/private/seams/**)
  - Project evaluations (projects/*/evaluation_*.json)
  - Project debate logs (projects/*/debate_log.md slices)
  - Paper sections (papers/*/draft.md or sections)
  - Verified axioms (projects/*/verified_axioms.json entries)

Outputs:
  analytics/public/queries/taste/_taste_sample.md       — visible to rater (no week)
  analytics/public/queries/taste/_taste_metadata.json   — week mapping (rater hides)

Usage:
    python scripts/public/mining/sample_artifacts_for_taste.py [--per-week 10]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import yaml  # type: ignore[import-untyped]

REPO = Path(__file__).resolve().parents[3]
F_ROWS_PATH = REPO / "research_areas" / "EXPERIMENT_TRACK_RECORD.md"
SAMPLE_MD = REPO / "analytics" / "public" / "queries" / "taste" / "_taste_sample.md"
METADATA_JSON = REPO / "analytics" / "public" / "queries" / "taste" / "_taste_metadata.json"
PRIMER_PATH = REPO / "analytics" / "public" / "queries" / "taste" / "_taste_context_primer.md"
# Content-hash ledger of previously-rated artifacts. Avoids paying
# the LLM/sub-agent twice for the same content. Same architecture as
# the v5-op tagging script's per-axiom cache.
LEDGER_PATH = REPO / "analytics" / "public" / "queries" / "taste" / "taste_ledger.json"

# Bump LEDGER_SCHEMA_VERSION when the rated-content extraction logic
# changes incompatibly (e.g., max_chars changes, fields rearranged).
# Entries with mismatching schema_version are treated as stale and
# re-rated on the next pass. Previous-version entries are KEPT in the
# ledger under a `_deprecated` key for audit / rollback.
LEDGER_SCHEMA_VERSION = 1

# CODE_VERSION is bumped manually by whoever fixes a bug in the
# sampler / rater pipeline. If the operator finds out next week that
# today's truncation logic was wrong, they bump CODE_VERSION → all
# entries with the old version get re-rated. Cheap kill-switch.
CODE_VERSION = "2026-05-06.r1"


def _content_sha(content: str) -> str:
    """16-char SHA1 of the content the rater would see. Stable cache key."""
    return hashlib.sha1((content or "").encode("utf-8")).hexdigest()[:16]


def _file_sha(path: Path) -> str:
    """SHA of file contents (used for primer fingerprinting)."""
    if not path.exists():
        return ""
    try:
        return hashlib.sha1(path.read_bytes()).hexdigest()[:16]
    except Exception:  # noqa: BLE001
        return ""


def _load_ledger(path: Path) -> dict[str, dict]:
    """Load ledger with schema-version awareness.

    Returns ONLY entries valid at LEDGER_SCHEMA_VERSION. Older entries
    are still present in the JSON file but ignored at lookup time.
    Older entries get archived under a _deprecated key on next write.
    """
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
    except Exception:  # noqa: BLE001
        return {}
    out: dict[str, dict] = {}
    for k, v in data.items():
        if k.startswith("_"):
            continue  # metadata / deprecation markers
        if not isinstance(v, dict):
            continue
        # Only consider entries matching the active schema version.
        # Missing schema_version means pre-versioned entry (treat as
        # legacy v1 — accept).
        ver = v.get("schema_version", 1)
        if ver == LEDGER_SCHEMA_VERSION:
            out[k] = v
    return out

_DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def _week_bucket(dt: datetime) -> str:
    monday = dt - timedelta(days=dt.weekday())
    return monday.strftime("%Y-%m-%d")


def _safe_read(p: Path, max_chars: int = 1000) -> str:
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return ""
    return text[:max_chars]


def _file_create_date(path: Path) -> datetime:
    """Frontmatter date > stat birthtime > mtime."""
    if path.suffix.lower() == ".md":
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")[:2048]
        except Exception:  # noqa: BLE001
            text = ""
        m = _FRONTMATTER_RE.match(text)
        if m:
            try:
                fm = yaml.safe_load(m.group(1)) or {}
                if isinstance(fm, dict):
                    for k in ("opened", "discovered", "authored", "created", "date"):
                        v = fm.get(k)
                        if v:
                            md = _DATE_RE.search(str(v))
                            if md:
                                return datetime.fromisoformat(md.group(1)).replace(tzinfo=timezone.utc)
            except Exception:  # noqa: BLE001
                pass
    try:
        st = path.stat()
        ts = getattr(st, "st_birthtime", st.st_mtime)
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except Exception:  # noqa: BLE001
        return datetime.now(timezone.utc)


def _gather_f_rows() -> list[dict]:
    """Each non-trivial F-row is a sample candidate."""
    out = []
    if not F_ROWS_PATH.exists():
        return out
    text = F_ROWS_PATH.read_text(encoding="utf-8", errors="ignore")
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
        out.append({
            "kind": "f_row",
            "source_path": str(F_ROWS_PATH.relative_to(REPO)),
            "week": _week_bucket(d),
            "content": line.strip()[:600],
        })
    return out


def _gather_evidence_ledgers() -> list[dict]:
    """High-signal evidence/insight ledgers (operator-requested 2026-05-16:
    'mine the insight ledger and gp-233 evidence ledger'). These are
    authored evidence prose — taste-rate them. The prediction ledger is
    structured data with its own calibration miner (orchestrator Phase 2b),
    NOT taste-rated here. F/E rows are already covered by _gather_f_rows."""
    targets = [
        REPO / "research_areas" / "insights_ledger.md",
        REPO / "analytics" / "public" / "ledgers" / "research_yield_decomposition" / "GP-233_EVIDENCE_LEDGER.md",
    ]
    out: list[dict] = []
    for path in targets:
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            continue
        mtime_wk = _week_bucket(datetime.fromtimestamp(
            path.stat().st_mtime, tz=timezone.utc))
        block: list[str] = []

        def _flush(blk: list[str]) -> None:
            chunk = "\n".join(blk).strip()
            if len(chunk) < 120:
                return
            wk = mtime_wk
            m = _DATE_RE.search(chunk)
            if m:
                try:
                    wk = _week_bucket(datetime.fromisoformat(
                        m.group(1)).replace(tzinfo=timezone.utc))
                except Exception:  # noqa: BLE001
                    pass
            out.append({
                "kind": "evidence_ledger",
                "source_path": str(path.relative_to(REPO)),
                "week": wk,
                "content": chunk[:800],
            })

        for line in text.splitlines():
            if line.startswith(("## ", "### ", "#### ")) and block:
                _flush(block)
                block = [line]
            else:
                block.append(line)
        _flush(block)
    return out


def _gather_seams() -> list[dict]:
    out = []
    seams_dir = REPO / "research_areas" / "private" / "seams"
    if not seams_dir.exists():
        return out
    for p in seams_dir.rglob("*.md"):
        if not p.is_file():
            continue
        if p.name.startswith("."):
            continue
        d = _file_create_date(p)
        wk = _week_bucket(d)
        out.append({
            "kind": "seam",
            "source_path": str(p.relative_to(REPO)),
            "week": wk,
            "content": _safe_read(p, max_chars=1200),
        })
    return out


def _gather_paper_sections() -> list[dict]:
    out = []
    papers = REPO / "papers"
    if not papers.exists():
        return out
    for p in papers.rglob("*.md"):
        if not p.is_file() or p.name.startswith("."):
            continue
        d = _file_create_date(p)
        wk = _week_bucket(d)
        out.append({
            "kind": "paper_md",
            "source_path": str(p.relative_to(REPO)),
            "week": wk,
            "content": _safe_read(p, max_chars=1200),
        })
    return out


def _gather_evaluations() -> list[dict]:
    """Project evaluation JSONs: take the highest-scoring iter per project."""
    out = []
    projects = REPO / "projects"
    if not projects.exists():
        return out
    for proj in projects.iterdir():
        if not proj.is_dir():
            continue
        evals = list(proj.glob("evaluation_iter_*.json"))
        if not evals:
            evals = list(proj.glob("evaluation_*.json"))
        if not evals:
            continue
        best = None
        best_score = -1.0
        for ev_path in evals:
            try:
                ev = json.loads(ev_path.read_text(encoding="utf-8"))
                score = float(ev.get("score") or 0)
                if score > best_score:
                    best_score = score
                    best = (ev_path, ev)
            except Exception:  # noqa: BLE001
                continue
        if not best:
            continue
        ev_path, ev = best
        d = _file_create_date(ev_path)
        wk = _week_bucket(d)
        weakest = str(ev.get("weakest_point") or "")[:300]
        rationale = str(ev.get("rationale") or "")[:300]
        out.append({
            "kind": "evaluation",
            "source_path": str(ev_path.relative_to(REPO)),
            "week": wk,
            "content": (
                f"score={best_score:.0f}\n"
                f"weakest_point: {weakest}\n"
                f"rationale: {rationale}"
            ),
        })
    return out


def _gather_axioms() -> list[dict]:
    """All non-sentinel axioms across projects. Caller stratifies."""
    out = []
    projects = REPO / "projects"
    if not projects.exists():
        return out
    for path in projects.glob("*/verified_axioms.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        axioms_list = (
            data if isinstance(data, list)
            else (data.get("axioms", []) if isinstance(data, dict) else [])
        )
        for ax in axioms_list:
            ax_text = ""
            if isinstance(ax, str):
                ax_text = ax
            elif isinstance(ax, dict):
                ax_text = (
                    ax.get("content") or ax.get("statement") or
                    ax.get("axiom") or ax.get("text") or ""
                )
            if not ax_text or "inherited truth" in ax_text.lower():
                continue
            try:
                mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            except Exception:  # noqa: BLE001
                continue
            wk = _week_bucket(mtime)
            out.append({
                "kind": "verified_axiom",
                "source_path": str(path.relative_to(REPO)),
                "week": wk,
                "content": ax_text[:500],
            })
    return out


def _gather_project_workspace_md() -> list[dict]:
    """Substantive markdown files inside project workspaces.

    This was the major sampling gap fixed 2026-05-06 PM: the original
    sampler only took 1 evaluation + 1 axiom per project, missing
    903 files of substantive workspace content (NS phase markdowns,
    consciousness theory, gravity bridges, Fermi paradox arguments,
    etc.). This function reaches into projects/*/workspace/* + any
    project-level markdown >2KB and emits each as a sample candidate.
    """
    out = []
    projects = REPO / "projects"
    if not projects.exists():
        return out
    for proj in projects.iterdir():
        if not proj.is_dir():
            continue
        if proj.name.startswith("_bench_"):
            # Benchmark runs are apparatus testing, not research projects
            continue
        # Walk workspace + project root for markdown
        candidates = list(proj.rglob("*.md"))
        for p in candidates:
            try:
                size = p.stat().st_size
            except Exception:  # noqa: BLE001
                continue
            if size < 1500:
                # Too short — likely a stub or sentinel
                continue
            if size > 200_000:
                # Pathologically large — generated dump or accidentally
                # checked-in artifact. Skip.
                continue
            wk = _week_bucket(_file_create_date(p))
            out.append({
                "kind": "project_workspace_md",
                "source_path": str(p.relative_to(REPO)),
                "week": wk,
                "content": _safe_read(p, max_chars=1400),
            })
    return out


def _gather_evidence_files() -> list[dict]:
    """Project-level evidence.txt + raw/*.md + research-area evidence/*.

    Expansion 2026-05-06 PM: project raw/ directories contain
    operator-curated evidence inputs that are pre-distilled insight
    content. 358 such files exist across projects.
    """
    out = []
    # Project-level evidence files
    for evidence_path in (REPO / "projects").rglob("evidence*.txt"):
        if not evidence_path.is_file():
            continue
        try:
            size = evidence_path.stat().st_size
        except Exception:  # noqa: BLE001
            continue
        if size < 500 or size > 200_000:
            continue
        wk = _week_bucket(_file_create_date(evidence_path))
        out.append({
            "kind": "evidence_file",
            "source_path": str(evidence_path.relative_to(REPO)),
            "week": wk,
            "content": _safe_read(evidence_path, max_chars=1400),
        })
    # Per-project raw/ evidence inputs
    for proj in (REPO / "projects").iterdir():
        if not proj.is_dir() or proj.name.startswith("_bench_"):
            continue
        raw_dir = proj / "raw"
        if not raw_dir.exists():
            continue
        for p in raw_dir.rglob("*.md"):
            try:
                size = p.stat().st_size
            except Exception:  # noqa: BLE001
                continue
            if size < 500 or size > 200_000:
                continue
            wk = _week_bucket(_file_create_date(p))
            out.append({
                "kind": "raw_evidence_input",
                "source_path": str(p.relative_to(REPO)),
                "week": wk,
                "content": _safe_read(p, max_chars=1400),
            })
    # Research-area evidence
    research_evidence = REPO / "research_areas" / "private" / "evidence"
    if research_evidence.exists():
        for p in research_evidence.rglob("*.md"):
            try:
                size = p.stat().st_size
            except Exception:  # noqa: BLE001
                continue
            if size < 500 or size > 200_000:
                continue
            wk = _week_bucket(_file_create_date(p))
            out.append({
                "kind": "evidence_file",
                "source_path": str(p.relative_to(REPO)),
                "week": wk,
                "content": _safe_read(p, max_chars=1400),
            })
    return out


def _gather_project_charters() -> list[dict]:
    """Per-project project_charter.md — operator-authored framing per project."""
    out = []
    projects = REPO / "projects"
    if not projects.exists():
        return out
    for p in projects.glob("*/project_charter.md"):
        try:
            size = p.stat().st_size
        except Exception:  # noqa: BLE001
            continue
        if size < 500:
            continue
        wk = _week_bucket(_file_create_date(p))
        out.append({
            "kind": "project_charter",
            "source_path": str(p.relative_to(REPO)),
            "week": wk,
            "content": _safe_read(p, max_chars=1400),
        })
    return out


def _gather_top_level_apparatus_reasoning() -> list[dict]:
    """DECISION_LOG.md, MIRROR.md, README.md, RELEASE_CHECKLIST.md, AGENTS.md."""
    out = []
    for name in ("DECISION_LOG.md", "MIRROR.md", "README.md",
                 "RELEASE_CHECKLIST.md", "AGENTS.md", "CLAUDE.md"):
        p = REPO / name
        if not p.exists():
            continue
        wk = _week_bucket(_file_create_date(p))
        out.append({
            "kind": "top_level_reasoning",
            "source_path": str(p.relative_to(REPO)),
            "week": wk,
            "content": _safe_read(p, max_chars=1400),
        })
    # Internal architectural maps + concept docs
    for d in ("docs/internal", "docs/concepts", "docs/guides"):
        root = REPO / d
        if not root.exists():
            continue
        for p in root.rglob("*.md"):
            try:
                size = p.stat().st_size
            except Exception:  # noqa: BLE001
                continue
            if size < 500:
                continue
            wk = _week_bucket(_file_create_date(p))
            out.append({
                "kind": "concept_doc",
                "source_path": str(p.relative_to(REPO)),
                "week": wk,
                "content": _safe_read(p, max_chars=1400),
            })
    return out


def _gather_memory_entries() -> list[dict]:
    """Operator-curated memory entries (insight summaries by definition)."""
    out = []
    memory_dir = Path(
        os.environ.get(
            "ZTARE_CLAUDE_PROJECT_MEMORY",
            str(Path.home() / ".claude/projects" / os.environ.get("CLAUDE_PROJECT_SLUG", "") / "memory"),
        )
    )
    if not memory_dir.exists():
        return out
    for p in memory_dir.glob("*.md"):
        if p.name == "MEMORY.md":
            continue
        try:
            size = p.stat().st_size
        except Exception:  # noqa: BLE001
            continue
        if size < 200:
            continue
        wk = _week_bucket(_file_create_date(p))
        out.append({
            "kind": "memory_entry",
            "source_path": str(p),  # absolute path; outside repo
            "week": wk,
            "content": _safe_read(p, max_chars=1400),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-week", type=int, default=10,
                    help="Target sample count per week (will pick across kinds)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-md", type=Path, default=SAMPLE_MD)
    ap.add_argument("--out-meta", type=Path, default=METADATA_JSON)
    # Delta-method invalidation flags (all default off — cache stays
    # warm; flip on when a bug fix or primer change requires re-rate)
    ap.add_argument("--require-code-version-match", action="store_true",
                    help="Invalidate ledger entries whose code_version differs from current")
    ap.add_argument("--require-primer-match", action="store_true",
                    help="Invalidate ledger entries rated under a different primer hash")
    ap.add_argument("--force-rerate", type=str, default="",
                    help="Comma-separated path substrings; matching entries get re-rated")
    ap.add_argument("--force-rerate-rater", type=str, default="",
                    help="Invalidate all ledger entries by this rater_id")
    args = ap.parse_args()

    print("=== artifact sampler for taste rating ===")
    random.seed(args.seed)

    pool: list[dict] = []
    pool += _gather_f_rows()
    pool += _gather_seams()
    pool += _gather_paper_sections()
    pool += _gather_evaluations()
    pool += _gather_axioms()
    pool += _gather_project_workspace_md()
    pool += _gather_evidence_files()
    pool += _gather_project_charters()
    pool += _gather_top_level_apparatus_reasoning()
    pool += _gather_memory_entries()
    pool += _gather_evidence_ledgers()
    print(f"  total candidate artifacts: {len(pool)}")
    # Distribution by kind
    from collections import Counter as _C
    kind_counts = _C(r["kind"] for r in pool)
    for k, n in kind_counts.most_common():
        print(f"    {k}: {n}")

    by_week: dict[str, list[dict]] = defaultdict(list)
    for r in pool:
        by_week[r["week"]].append(r)

    # Stratified sample: take a balanced mix from each week.
    # 2026-05-06 PM expansion: project_workspace_md is now a major
    # source class, taking ~5 of per_week. Other kinds get smaller
    # quotas. Cap each PROJECT's representation at 3 to prevent the
    # NS millennium hunt (which has ~200+ phase files) from
    # dominating.
    sampled: list[dict] = []
    for wk, items in sorted(by_week.items()):
        per_kind: dict[str, list[dict]] = defaultdict(list)
        for it in items:
            per_kind[it["kind"]].append(it)
        # Per-project cap to avoid NS dominating
        def _project_id(it: dict) -> str:
            sp = it.get("source_path") or ""
            parts = sp.split("/")
            if len(parts) >= 2 and parts[0] == "projects":
                return parts[1]
            return sp.split("/")[0]
        chosen: list[dict] = []
        per_project: dict[str, int] = defaultdict(int)
        # Quota per kind. Designed for per_week ≈ 25 to spread across
        # 10 kinds. Sum is ~28 so quotas are slightly oversubscribed —
        # the per-project cap typically prunes some.
        kind_quotas = {
            "project_workspace_md": 8,
            "raw_evidence_input": 3,
            "evidence_file": 2,
            "project_charter": 2,
            "seam": 3,
            "evaluation": 2,
            "paper_md": 2,
            "concept_doc": 2,
            "memory_entry": 2,
            "top_level_reasoning": 1,
            "verified_axiom": 1,
            "f_row": 1,
        }
        for kind, quota in kind_quotas.items():
            picks = per_kind.get(kind, [])
            random.shuffle(picks)
            taken = 0
            for it in picks:
                pid = _project_id(it)
                if per_project[pid] >= 3:
                    continue
                chosen.append(it)
                per_project[pid] += 1
                taken += 1
                if taken >= quota:
                    break
        # Top up to per_week with random
        if len(chosen) < args.per_week:
            remaining = [it for it in items if it not in chosen]
            random.shuffle(remaining)
            for it in remaining:
                if len(chosen) >= args.per_week:
                    break
                pid = _project_id(it)
                if per_project[pid] >= 3:
                    continue
                chosen.append(it)
                per_project[pid] += 1
        chosen = chosen[: args.per_week]
        sampled.extend(chosen)

    # Shuffle so the rater can't infer week from order
    random.shuffle(sampled)

    # Assign blinded IDs
    for i, item in enumerate(sampled, start=1):
        item["sample_id"] = f"SAMPLE_{i:03d}"

    # ── Cache lookup: skip artifacts whose content_sha is in the ledger.
    # Each item gets a content_sha; cached items carry their previous
    # score forward into the metadata; only uncached items appear in
    # the rater-visible _taste_sample.md.
    #
    # Delta-method robustness checks (all reasons to invalidate cache):
    #   1. schema_version mismatch — ledger entry from incompatible
    #      pipeline version
    #   2. code_version mismatch — pipeline bug fix forces re-rate
    #   3. primer_sha mismatch (when --require-primer-match) — primer
    #      changed so the rating's anchoring is stale
    #   4. force-rerate path glob match
    #   5. force-rerate-rater match — invalidate by rater_id
    ledger = _load_ledger(LEDGER_PATH)
    primer_sha = _file_sha(PRIMER_PATH) if PRIMER_PATH.exists() else ""
    n_cached = 0
    n_invalidated = {"schema": 0, "code_version": 0, "primer": 0, "force": 0, "rater": 0}
    force_rerate_paths = (args.force_rerate or "").split(",") if args.force_rerate else []
    force_rerate_rater = args.force_rerate_rater or ""
    for item in sampled:
        sha = _content_sha(item["content"])
        item["content_sha"] = sha
        item["cached"] = False
        if sha not in ledger:
            continue
        entry = ledger[sha]

        # Invalidation checks
        if entry.get("schema_version", 1) != LEDGER_SCHEMA_VERSION:
            n_invalidated["schema"] += 1
            continue
        if args.require_code_version_match and entry.get("code_version") != CODE_VERSION:
            n_invalidated["code_version"] += 1
            continue
        if args.require_primer_match and primer_sha and entry.get("primer_sha") != primer_sha:
            n_invalidated["primer"] += 1
            continue
        if force_rerate_paths and any(g and g in item["source_path"] for g in force_rerate_paths):
            n_invalidated["force"] += 1
            continue
        if force_rerate_rater and entry.get("rater") == force_rerate_rater:
            n_invalidated["rater"] += 1
            continue

        # Cache hit
        item["cached"] = True
        item["cached_score"] = entry.get("score")
        item["cached_rationale"] = entry.get("rationale", "")
        item["cached_rater"] = entry.get("rater", "")
        item["cached_rated_at"] = entry.get("rated_at_utc", "")
        n_cached += 1
    n_new = len(sampled) - n_cached
    print(f"  cache hit: {n_cached} / {len(sampled)} samples already rated")
    print(f"  new to rate: {n_new}")
    if any(n_invalidated.values()):
        print(f"  invalidated: {n_invalidated}")

    # Write metadata sidecar (the rater hides this from themselves)
    metadata = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "n_samples": len(sampled),
        "n_cached": n_cached,
        "n_new": n_new,
        "ledger_path": str(LEDGER_PATH.relative_to(REPO)),
        "samples": [
            {
                "sample_id": s["sample_id"],
                "kind": s["kind"],
                "week": s["week"],
                "source_path": s["source_path"],
                "content_sha": s["content_sha"],
                "cached": s["cached"],
                **({
                    "cached_score": s.get("cached_score"),
                    "cached_rationale": s.get("cached_rationale", ""),
                    "cached_rater": s.get("cached_rater", ""),
                    "cached_rated_at": s.get("cached_rated_at", ""),
                } if s["cached"] else {}),
            }
            for s in sampled
        ],
    }
    args.out_meta.parent.mkdir(parents=True, exist_ok=True)
    args.out_meta.write_text(json.dumps(metadata, indent=2))
    print(f"  wrote {args.out_meta} (week mapping — RATER MUST NOT READ)")

    # Write the BLINDED rater-visible markdown — ONLY uncached samples.
    # Cached samples flow through the metadata into the aggregator
    # without ever hitting the rater.
    new_samples = [s for s in sampled if not s["cached"]]
    md = ["# Taste Sample — Blind Rating Sheet\n"]
    md.append(
        f"This batch has **{len(new_samples)} samples** to rate. "
        f"({n_cached} additional samples were skipped because they're "
        f"already in the taste_ledger from previous runs.)\n\n"
        "Each sample below has a unique `SAMPLE_NNN` ID. Read each sample "
        "and rate it 0-5 on **insight density**:\n\n"
        "  - **0** = boilerplate, scaffolding, or restated apparatus state\n"
        "  - **1** = trivially observable; doesn't change downstream reasoning\n"
        "  - **2** = useful but expected; consolidates known\n"
        "  - **3** = non-obvious finding or sharp framing; would help a future reader\n"
        "  - **4** = surprising / load-bearing / mechanism-revealing\n"
        "  - **5** = paradigm-shifting; reframes the problem or apparatus\n\n"
        "Output format:\n```\n"
        "SAMPLE_001 | score | one-line rationale\n"
        "SAMPLE_002 | score | one-line rationale\n"
        "...\n```\n\n"
        "**Bias warning to rater:** if you've worked on this codebase recently, "
        "you'll be tempted to score familiar / recent / self-authored content "
        "higher. Try to score on the artifact text alone, not on what you "
        "remember about it.\n\n---\n"
    )
    for s in new_samples:
        md.append(f"## {s['sample_id']} ({s['kind']})\n")
        md.append("```")
        md.append(s["content"])
        md.append("```")
        md.append("")
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(md) + "\n")
    print(f"  wrote {args.out_md} ({len(new_samples)} new samples to rate)")
    print(f"  sample distribution by week (HIDDEN from rater):")
    by_wk = defaultdict(int)
    for s in sampled:
        by_wk[s["week"]] += 1
    for wk, n in sorted(by_wk.items()):
        print(f"    {wk}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
