#!/usr/bin/env python3
"""GP-221 seam health audit — periodic corpus audit over the seam tree.

Walks ``research_areas/private/seams/``. For each seam:

  - parse YAML frontmatter for ``status`` field
  - measure file mtime
  - count grep matches in F-rows (``research_areas/EXPERIMENT_TRACK_RECORD.md``)
  - count grep matches in ``src/`` and ``scripts/public/`` for the seam id
  - check whether each declared file path mention exists on disk
    (path-drift detector)

Plus pairwise re-seam detection: bigram-Jaccard similarity across
seam eigenquestions (or descriptions when eigenquestion absent),
flagging pairs >= threshold that are at least 30 days apart.

Output:
  - ``analytics/public/queries/audits/seam_health_report.json`` — full per-seam record
  - ``analytics/public/queries/audits/seam_health_report.md`` — operator-readable summary

Verdict bands per seam:

  alive: status active OR last_referenced < 30d ago
  stale: status open AND last_referenced >= 60d ago
  orphan: status open AND no spec under specs/ AND no code reference
  implemented_unmarked: status open BUT code/test reference exists
                        for the named primitive
  path_drift: any declared path no longer exists
  re_seam_candidate: bigram-Jaccard >= threshold against another
                     seam from >=30d ago

Usage:
    python scripts/public/audits/seam_health_audit.py
    python scripts/public/audits/seam_health_audit.py --seams-dir research_areas/private/seams/
    python scripts/public/audits/seam_health_audit.py --re-seam-threshold 0.65
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

REPO = Path(__file__).resolve().parents[3]
SEAMS_DIR = REPO / "research_areas" / "private" / "seams"
F_ROWS = REPO / "research_areas" / "EXPERIMENT_TRACK_RECORD.md"
SPECS_DIR = REPO / "research_areas" / "private" / "specs"
OUT_JSON = REPO / "analytics" / "public" / "queries" / "audits" / "seam_health_report.json"
OUT_MD = REPO / "analytics" / "public" / "queries" / "audits" / "seam_health_report.md"


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)
_GP_ID_RE = re.compile(r"GP-\d{3,4}[a-z]?")
# A path-mention heuristic: anything starting with one of the canonical
# repo-rooted prefixes that looks like a real file
_PATH_MENTION_RE = re.compile(
    r"\b(src/|scripts/public/|org/|analytics/public/queries/|"
    r"projects/|research_areas/|docs/|papers/|ztare_proofs/)"
    r"[A-Za-z0-9_/.\-]+(?:\.py|\.md|\.json|\.yaml|\.lean|\.txt)\b"
)


def parse_frontmatter(text: str) -> dict:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    body = m.group(1)
    out: dict = {}
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def extract_seam_id(path: Path) -> str | None:
    """Extract the GP-XXX id from a seam filename."""
    m = _GP_ID_RE.search(path.name)
    return m.group(0) if m else None


def extract_eigenquestion(text: str) -> str:
    """Best-effort: grab the paragraph after '## Eigenquestion' header.

    Falls back to the first non-empty paragraph after the H1 if no
    explicit eigenquestion section exists.
    """
    m = re.search(
        r"##\s+Eigenquestion\s*\n+(.*?)(?=\n##|\Z)",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    # Fallback: first paragraph after the H1
    body = re.sub(r"^---.*?---\n", "", text, flags=re.DOTALL)
    body = re.sub(r"^#\s+[^\n]*\n+", "", body)
    paras = [p.strip() for p in body.split("\n\n") if p.strip()]
    return paras[0] if paras else ""


def bigrams(s: str) -> set[str]:
    """Word-level bigrams over normalized lowercase text."""
    tokens = re.findall(r"[a-z]+", s.lower())
    return {f"{a} {b}" for a, b in zip(tokens, tokens[1:])}


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def grep_count(pattern: str, root: Path | None = None) -> int:
    """Best-effort grep count via `grep -r -l` on the given root."""
    if root is None:
        root = REPO
    try:
        result = subprocess.run(
            ["grep", "-rln", pattern, str(root)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return sum(1 for line in result.stdout.splitlines() if line.strip())
    except Exception:  # noqa: BLE001
        return 0


def grep_count_in_file(pattern: str, path: Path) -> int:
    if not path.exists():
        return 0
    try:
        result = subprocess.run(
            ["grep", "-c", pattern, str(path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        s = result.stdout.strip()
        return int(s) if s.isdigit() else 0
    except Exception:  # noqa: BLE001
        return 0


def find_specs_for_seam(seam_id: str) -> list[Path]:
    if not SPECS_DIR.exists():
        return []
    return sorted(SPECS_DIR.rglob(f"*{seam_id}*"))


def walk_seams() -> Iterator[Path]:
    if not SEAMS_DIR.exists():
        return
    for p in sorted(SEAMS_DIR.rglob("*.md")):
        # Skip the audit reports / non-seam READMEs etc.
        if p.name in ("README.md", "INDEX.md"):
            continue
        if "/reflexive/" in str(p) and not _GP_ID_RE.search(p.name):
            # The reflexive subdir contains audit reports too; only
            # scan files that look like a seam (have a GP-XXX id).
            continue
        yield p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seams-dir", type=Path, default=SEAMS_DIR)
    ap.add_argument(
        "--re-seam-threshold",
        type=float,
        default=0.55,
        help="bigram-Jaccard cutoff for re-seam pair detection",
    )
    ap.add_argument(
        "--reference-window-days",
        type=int,
        default=60,
        help="seams not referenced within this window go to stale band",
    )
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    args = ap.parse_args()

    print(f"=== GP-221 seam health audit ===")
    print(f"  seams dir: {args.seams_dir}")
    print(f"  reference window: {args.reference_window_days} days")
    print(f"  re-seam Jaccard threshold: {args.re_seam_threshold}")

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=args.reference_window_days)

    seams = []
    for path in walk_seams():
        seam_id = extract_seam_id(path)
        if not seam_id:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001
            continue
        fm = parse_frontmatter(text)
        status = (fm.get("status") or fm.get("Status") or "").strip().lower()
        # Some seams use "**Status:** open" inline
        if not status:
            m = re.search(
                r"\*\*Status:?\*\*:?\s*([A-Za-z_]+)", text[:500], re.IGNORECASE
            )
            if m:
                status = m.group(1).strip().lower()

        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        age_days = (now - mtime).days

        f_row_hits = grep_count_in_file(seam_id, F_ROWS)
        # Code-trace: grep for the seam id under src/ and scripts/public/
        code_hits = grep_count(seam_id, REPO / "src") + grep_count(
            seam_id, REPO / "scripts"
        )

        # Path-drift detector: count mentioned paths that don't exist
        mentioned_paths = set(_PATH_MENTION_RE.findall(text))
        # The regex above returns the prefix-only group on Python's findall
        # for groups; re-extract full matches.
        mentioned_paths_full = set(
            m.group(0) for m in _PATH_MENTION_RE.finditer(text)
        )
        existing = sum(1 for p in mentioned_paths_full if (REPO / p).exists())
        nonexistent = len(mentioned_paths_full) - existing
        drift_ratio = (
            nonexistent / max(1, len(mentioned_paths_full))
            if mentioned_paths_full
            else 0.0
        )

        specs = find_specs_for_seam(seam_id)

        # Verdict
        verdict_tags = []
        if status in ("active", "shipped", "closed"):
            verdict = "alive_marked"
        elif age_days < args.reference_window_days and (
            f_row_hits > 0 or code_hits > 0
        ):
            verdict = "alive"
        elif status == "open" and code_hits > 0 and f_row_hits == 0:
            verdict = "implemented_unmarked"
        elif status == "open" and not specs and code_hits == 0:
            verdict = "orphan"
        elif age_days >= args.reference_window_days and f_row_hits == 0:
            verdict = "stale"
        else:
            verdict = "uncategorized"
        if drift_ratio >= 0.3 and len(mentioned_paths_full) >= 3:
            verdict_tags.append("path_drift")

        seams.append({
            "seam_id": seam_id,
            "path": str(path.relative_to(REPO)),
            "status": status or "(no status field)",
            "mtime_utc": mtime.isoformat(),
            "age_days": age_days,
            "f_row_hits": f_row_hits,
            "code_hits": code_hits,
            "specs_count": len(specs),
            "mentioned_paths": len(mentioned_paths_full),
            "nonexistent_paths": nonexistent,
            "verdict": verdict,
            "tags": verdict_tags,
            "_eigenquestion_bigrams": bigrams(extract_eigenquestion(text)),
        })

    print(f"  scanned {len(seams)} seams")

    # Re-seam pair detection (bigram Jaccard, for seams >=30 days apart)
    re_seam_pairs = []
    for i in range(len(seams)):
        for j in range(i + 1, len(seams)):
            a, b = seams[i], seams[j]
            ts_a = datetime.fromisoformat(a["mtime_utc"])
            ts_b = datetime.fromisoformat(b["mtime_utc"])
            delta_days = abs((ts_a - ts_b).days)
            if delta_days < 30:
                continue
            sim = jaccard(a["_eigenquestion_bigrams"], b["_eigenquestion_bigrams"])
            if sim >= args.re_seam_threshold:
                re_seam_pairs.append({
                    "seam_a": a["seam_id"],
                    "seam_b": b["seam_id"],
                    "jaccard": round(sim, 3),
                    "days_apart": delta_days,
                    "path_a": a["path"],
                    "path_b": b["path"],
                })
    re_seam_pairs.sort(key=lambda x: -x["jaccard"])

    # Drop the bigram set from the persisted records (it's huge)
    for s in seams:
        s.pop("_eigenquestion_bigrams", None)

    # Aggregate verdict counts
    by_verdict: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for s in seams:
        by_verdict[s["verdict"]] = by_verdict.get(s["verdict"], 0) + 1
        by_status[s["status"]] = by_status.get(s["status"], 0) + 1

    # Top stale + orphan candidates
    stale_candidates = sorted(
        [s for s in seams if s["verdict"] == "stale"],
        key=lambda s: -s["age_days"],
    )[:25]
    orphan_candidates = sorted(
        [s for s in seams if s["verdict"] == "orphan"],
        key=lambda s: -s["age_days"],
    )[:15]
    implemented_unmarked = sorted(
        [s for s in seams if s["verdict"] == "implemented_unmarked"],
        key=lambda s: -s["code_hits"],
    )[:15]

    payload = {
        "audit_timestamp_utc": now.isoformat(),
        "seams_scanned": len(seams),
        "by_verdict": by_verdict,
        "by_status": by_status,
        "re_seam_pairs": re_seam_pairs[:20],
        "stale_candidates": stale_candidates,
        "orphan_candidates": orphan_candidates,
        "implemented_unmarked": implemented_unmarked,
        "all_seams": seams,
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2))
    print(f"  wrote {args.out_json}")

    # Operator-readable markdown summary
    md = ["# Seam Health Report\n"]
    md.append(f"_Generated {payload['audit_timestamp_utc']}_  ")
    md.append(f"_Seams scanned:_ {len(seams)}\n")
    md.append("## By verdict\n")
    md.append("| Verdict | Count |\n|---|---:|")
    for v, c in sorted(by_verdict.items(), key=lambda kv: -kv[1]):
        md.append(f"| `{v}` | {c} |")
    md.append("")
    md.append("## By status field\n")
    md.append("| Status | Count |\n|---|---:|")
    for st, c in sorted(by_status.items(), key=lambda kv: -kv[1]):
        md.append(f"| `{st}` | {c} |")
    md.append("")
    if implemented_unmarked:
        md.append("## Implemented-unmarked (open status but code exists — promote to shipped)\n")
        md.append("| Seam | Status | Code hits | Path |\n|---|---|---:|---|")
        for s in implemented_unmarked:
            md.append(
                f"| `{s['seam_id']}` | {s['status']} | {s['code_hits']} | "
                f"{s['path']} |"
            )
        md.append("")
    if stale_candidates:
        md.append("## Stale candidates (close or revive)\n")
        md.append("| Seam | Age days | Status | Code | F-rows | Path |\n|---|---:|---|---:|---:|---|")
        for s in stale_candidates:
            md.append(
                f"| `{s['seam_id']}` | {s['age_days']} | {s['status']} | "
                f"{s['code_hits']} | {s['f_row_hits']} | {s['path']} |"
            )
        md.append("")
    if orphan_candidates:
        md.append("## Orphan candidates (open, no spec, no code)\n")
        md.append("| Seam | Age days | Path |\n|---|---:|---|")
        for s in orphan_candidates:
            md.append(f"| `{s['seam_id']}` | {s['age_days']} | {s['path']} |")
        md.append("")
    if re_seam_pairs:
        md.append("## Re-seam pair candidates (high bigram overlap, ≥30 days apart)\n")
        md.append("| Seam A | Seam B | Jaccard | Days apart |\n|---|---|---:|---:|")
        for p in re_seam_pairs[:15]:
            md.append(
                f"| `{p['seam_a']}` | `{p['seam_b']}` | {p['jaccard']} | "
                f"{p['days_apart']} |"
            )
        md.append("")
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(md) + "\n")
    print(f"  wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
