#!/usr/bin/env python3
"""Process-loop classifier — auto-detect loop vs one-shot artifacts.

Closes a known reflexive-mining blind spot. Today's miners (closure
patterns, primitive ROI, seam health) score COVERAGE / ROI of
existing entities. They cannot ask structural-analogy questions like
"this one-shot generation step looks like that loop — should it
become recursive?"

This miner produces the DATA layer that a structural-analogy miner
needs. It does NOT use git history (the operator's commit cadence is
sparse so git mtimes are unreliable). Instead it combines:

  1. **Filesystem mtime** — last write to the actual file
  2. **Frontmatter signals** — declared status (open/closed/active),
     `recurrence`, `last_attested`, `re_trigger_period` if present
  3. **Static code patterns** — for .py files, look for closed-loop
     shapes: reads telemetry source AND writes back to a feedback
     ledger, has `for ... in` over a corpus of iter records, etc.
  4. **The seed catalog** at ``org/runtime/process_catalog_seed.yaml``
     for cross-validation

For each artifact we emit ``inferred_kind`` (loop / periodic /
one_shot / static / unclassified) and a confidence score. A separate
miner (mine_structural_analogies.py) consumes this and pairs
one-shots with loops.

Outputs:
  ``analytics/public/queries/process/process_catalog.{json,md}``

Pure CPU. No LLM. No git.

Usage:
    python scripts/public/mining/mine_process_loops.py
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml  # type: ignore[import-untyped]

REPO = Path(__file__).resolve().parents[3]
SEED_PATH = REPO / "org" / "runtime" / "process_catalog_seed.yaml"
OUT_JSON = REPO / "analytics" / "public" / "queries" / "process" / "process_catalog.json"
OUT_MD = REPO / "analytics" / "public" / "queries" / "process" / "process_catalog.md"

SCAN_ROOTS = [
    "org/charters",
    "org/mandates",
    "org/key_results",
    "org/objectives",
    "org/signals",
    "org/runtime",
    "research_areas/private/seams",
    "research_areas/private/evidence",
    "analytics/public/queries",
    "src/ztare/gates",
    "src/ztare/orchestrator",
    "scripts/public/mining",
    "scripts",  # for top-level apparatus scripts
]

TEXT_EXTS = {".md", ".yaml", ".yml", ".json"}
CODE_EXTS = {".py"}

# Exclusion globs for path components that are NOT apparatus
# generators (build artifacts, tests, generated reports, vendored code).
PATH_EXCLUDE_PARTS = {
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    "tests",  # generated unit tests
    "_v5_enrich_run",
    "lemma_relevance",  # GPU outputs, not apparatus
    "gflownet",
}

# Regex patterns that, when found in a .py file, indicate it's a
# closed-loop generator (reads signal → writes back). Heuristic only —
# false positives are fine as the seed catalog overrides.
CLOSED_LOOP_PATTERNS = [
    re.compile(r"\bcage_engagement\.jsonl\b"),
    re.compile(r"\bdamage_signals?\b"),
    re.compile(r"\bderived_constraints?(_ledger)?\b"),
    re.compile(r"\bevidence/.*\.md\b"),
    re.compile(r"\bupdate_.*_ledger\("),
    re.compile(r"\bappend_.*_proposal\("),
    re.compile(r"\biter_history\b"),
    re.compile(r"for .* in .*\biter\b"),
    re.compile(r"\bre[_-]trigger\b|\bstagnation\b"),
]

# Patterns indicating a one-shot generator: writes a single artifact,
# called from a project setup / initialization context.
ONE_SHOT_PATTERNS = [
    re.compile(r"\bgenerate_charter\b|\bbuild_charter\b"),
    re.compile(r"\bauthor_rubric\b|\bscaffold_rubric\b"),
    re.compile(r"\bproject_init\b|\bproject_setup\b"),
    re.compile(r"\bonly run at startup\b", re.I),
    re.compile(r"\bone-?shot\b", re.I),
]

# Frontmatter keys that signal a periodic / KR-driven loop
PERIODIC_FRONTMATTER_KEYS = ("recurrence", "last_attested", "P\\d+D")


@dataclass
class ArtifactRecord:
    path: str  # repo-relative
    extension: str
    last_mtime: Optional[str] = None
    age_days: int = 0
    frontmatter_status: Optional[str] = None
    frontmatter_recurrence: Optional[str] = None
    frontmatter_seam_id: Optional[str] = None
    closed_loop_pattern_hits: int = 0
    one_shot_pattern_hits: int = 0
    inferred_kind: str = "unclassified"
    confidence: float = 0.0
    seed_declared_kind: Optional[str] = None
    kind_disagreement: bool = False
    notes: list[str] = field(default_factory=list)


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def _read_frontmatter(path: Path) -> dict:
    """Return YAML frontmatter dict if present at top of file. Cheap."""
    if path.suffix.lower() not in {".md"}:
        return {}
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")[:4096]
    except Exception:  # noqa: BLE001
        return {}
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    try:
        out = yaml.safe_load(m.group(1)) or {}
        return out if isinstance(out, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _scan_code_patterns(path: Path) -> tuple[int, int]:
    """For a .py file, count closed-loop and one-shot pattern hits."""
    if path.suffix.lower() != ".py":
        return 0, 0
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return 0, 0
    cl_hits = sum(1 for r in CLOSED_LOOP_PATTERNS if r.search(text))
    os_hits = sum(1 for r in ONE_SHOT_PATTERNS if r.search(text))
    return cl_hits, os_hits


def _classify_kind(rec: ArtifactRecord) -> tuple[str, float]:
    """Heuristic kind classifier from mtime + frontmatter + code patterns.

    Returns (kind, confidence in [0, 1]). Higher confidence when
    multiple signals agree.
    """
    signals: list[tuple[str, float]] = []  # (kind_vote, weight)

    # Frontmatter signals (high weight when present)
    if rec.frontmatter_recurrence:
        signals.append(("periodic", 0.9))
    elif rec.frontmatter_status in ("active", "open") and rec.age_days <= 14:
        signals.append(("loop", 0.4))
    elif rec.frontmatter_status == "closed":
        signals.append(("static", 0.6))

    # Code-pattern signals
    if rec.closed_loop_pattern_hits >= 3:
        signals.append(("loop", 0.7))
    elif rec.closed_loop_pattern_hits >= 1:
        signals.append(("loop", 0.3))
    if rec.one_shot_pattern_hits >= 1:
        signals.append(("one_shot", 0.5))

    # Mtime signals (lower weight; mtime is noisy without commit history)
    if rec.age_days > 90:
        signals.append(("static", 0.3))
    elif rec.age_days <= 7:
        signals.append(("recently_authored", 0.2))

    if not signals:
        return "unclassified", 0.0

    # Aggregate by kind: highest summed weight wins
    weights: dict[str, float] = {}
    for kind, w in signals:
        weights[kind] = weights.get(kind, 0.0) + w
    best_kind = max(weights.items(), key=lambda kv: kv[1])
    total_weight = sum(weights.values())
    confidence = best_kind[1] / max(total_weight, 1e-9)
    return best_kind[0], round(confidence, 3)


def _walk_artifacts() -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    for root_rel in SCAN_ROOTS:
        root = REPO / root_rel
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path in seen:
                continue
            ext = path.suffix.lower()
            in_apparatus = (
                ext in TEXT_EXTS
                or (
                    ext in CODE_EXTS
                    and (
                        "scripts/public/mining" in str(path)
                        or "src/ztare/gates" in str(path)
                        or "src/ztare/orchestrator" in str(path)
                        or path.parent == REPO / "scripts"
                    )
                )
            )
            if not in_apparatus:
                continue
            rel = path.relative_to(REPO)
            if any(part in PATH_EXCLUDE_PARTS for part in rel.parts):
                continue
            if any(part.startswith(".") for part in rel.parts):
                continue
            seen.add(path)
            found.append(path)
    return sorted(found)


def _load_seed() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not SEED_PATH.exists():
        return out
    try:
        data = yaml.safe_load(SEED_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return out
    for entry in (data or {}).get("processes", []) or []:
        kind = entry.get("kind")
        for ptr in entry.get("code_pointers") or []:
            if not isinstance(ptr, str):
                continue
            ptr = ptr.strip()
            if not ptr or ptr.startswith("(TODO"):
                continue
            out[ptr] = {"name": entry.get("name"), "kind": kind, "entry": entry}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    args = ap.parse_args()

    print("=== process-loop classifier (no-git, mtime + patterns) ===")
    paths = _walk_artifacts()
    print(f"  artifacts to classify: {len(paths)}")
    seed = _load_seed()
    print(f"  seed catalog code_pointer entries: {len(seed)}")

    now = datetime.now(timezone.utc)
    records: list[ArtifactRecord] = []
    for p in paths:
        rel = str(p.relative_to(REPO))
        rec = ArtifactRecord(path=rel, extension=p.suffix.lower())
        # mtime
        try:
            mtime_ts = p.stat().st_mtime
            mtime_dt = datetime.fromtimestamp(mtime_ts, tz=timezone.utc)
            rec.last_mtime = mtime_dt.isoformat()
            rec.age_days = max(0, (now - mtime_dt).days)
        except Exception:  # noqa: BLE001
            pass
        # frontmatter
        fm = _read_frontmatter(p)
        rec.frontmatter_status = fm.get("status")
        rec.frontmatter_recurrence = fm.get("recurrence") or fm.get(
            "re_trigger_period"
        )
        rec.frontmatter_seam_id = fm.get("seam_id")
        # code patterns
        cl, os_ = _scan_code_patterns(p)
        rec.closed_loop_pattern_hits = cl
        rec.one_shot_pattern_hits = os_
        # classify
        rec.inferred_kind, rec.confidence = _classify_kind(rec)
        # cross-validate with seed
        if rel in seed:
            rec.seed_declared_kind = seed[rel]["kind"]
            if (
                rec.seed_declared_kind != rec.inferred_kind
                and rec.inferred_kind != "unclassified"
            ):
                rec.kind_disagreement = True
                rec.notes.append(
                    f"seed declared {rec.seed_declared_kind!r} but heuristic "
                    f"inference is {rec.inferred_kind!r} (confidence "
                    f"{rec.confidence})"
                )
        records.append(rec)

    by_kind: dict[str, int] = {}
    for r in records:
        by_kind[r.inferred_kind] = by_kind.get(r.inferred_kind, 0) + 1

    one_shots = [r for r in records if r.inferred_kind == "one_shot"]
    loops = [r for r in records if r.inferred_kind in ("loop", "periodic")]

    # High-leverage one-shot candidates: in org/ space, frontmatter
    # absent or status=open, in well-known recursion-candidate namespaces
    recursion_candidates = [
        r for r in records
        if r.inferred_kind in ("one_shot", "static", "unclassified")
        and (
            r.path.startswith("org/charters")
            or r.path.startswith("org/mandates")
            or "rubric" in r.path.lower()
            or "charter" in r.path.lower()
            or "anti_pattern" in r.path.lower()
            or r.path.startswith("research_areas/private/seams") and r.frontmatter_status == "open"
        )
    ]

    payload = {
        "audit_timestamp_utc": now.isoformat(),
        "n_artifacts": len(records),
        "by_inferred_kind": by_kind,
        "n_seed_disagreements": sum(1 for r in records if r.kind_disagreement),
        "n_one_shots": len(one_shots),
        "n_loops": len(loops),
        "recursion_candidates": [r.__dict__ for r in recursion_candidates[:50]],
        "loops": [r.__dict__ for r in loops],
        "all_records": [r.__dict__ for r in records],
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2, default=str))
    print(f"  wrote {args.out_json}")

    md = ["# Process-Loop Catalog (auto-classified, no-git)\n"]
    md.append(f"_Generated {payload['audit_timestamp_utc']}_  ")
    md.append(
        f"_Artifacts:_ {len(records)}  "
        f"_Inferred kinds:_ {by_kind}  "
        f"_Seed disagreements:_ {payload['n_seed_disagreements']}\n"
    )

    md.append("## Loops detected\n")
    md.append(
        "| Path | Confidence | Frontmatter recurrence | Code-loop hits |\n"
        "|---|---:|---|---:|"
    )
    for r in loops[:30]:
        md.append(
            f"| `{r.path}` | {r.confidence} | "
            f"{r.frontmatter_recurrence or '—'} | "
            f"{r.closed_loop_pattern_hits} |"
        )
    md.append("")

    md.append("## Recursion candidates (one-shots in operator-loop namespaces)\n")
    md.append(
        "| Path | Inferred kind | Age (d) | Confidence | Frontmatter |\n"
        "|---|---|---:|---:|---|"
    )
    for r in payload["recursion_candidates"]:
        md.append(
            f"| `{r['path']}` | `{r['inferred_kind']}` | "
            f"{r['age_days']} | {r['confidence']} | "
            f"`status={r['frontmatter_status'] or '—'}` |"
        )
    md.append("")

    seed_disagreements = [r for r in records if r.kind_disagreement]
    if seed_disagreements:
        md.append("## Seed disagreements (heuristic vs seed)\n")
        md.append(
            "| Path | Seed kind | Inferred | Confidence | Notes |\n"
            "|---|---|---|---:|---|"
        )
        for r in seed_disagreements:
            md.append(
                f"| `{r.path}` | `{r.seed_declared_kind}` | "
                f"`{r.inferred_kind}` | {r.confidence} | "
                f"{(r.notes[0] if r.notes else '—')[:80]} |"
            )
        md.append("")

    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(md) + "\n")
    print(f"  wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
