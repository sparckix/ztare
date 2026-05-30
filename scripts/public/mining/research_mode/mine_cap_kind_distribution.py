#!/usr/bin/env python3
"""Cross-substrate cap-kind distribution miner.

Walks ``projects/*/workspace/cap_kind_iter_*.json`` files and aggregates
by (substrate_class, cap_kind) tuple. Surfaces:

  - which substrate classes hit which cap kinds most often
  - whether new gates / primitives shifted the distribution over time
  - recurring (substrate-class, cap-kind) clusters → primitive candidates

Cap kinds are emitted by the per-iter telemetry (GP-183 phase A5):
``gaming``, ``physics_violation``, ``generalization_gap``,
``holdout_miss``, ``numerical_failure``, ``none`` (or ``unknown``).

Substrate classes are derived from the rubric's ``cage_meta.class``
field when present; falls back to a heuristic from project name
patterns (gp###, oeis_*, ns_*, etc.).

Pure CPU, no LLM. Output:
  ``analytics/public/queries/classification/cap_kind_distribution.json``
  ``analytics/public/queries/classification/cap_kind_distribution.md``  (operator-readable)

Usage:
    python scripts/public/mining/mine_cap_kind_distribution.py
    python scripts/public/mining/mine_cap_kind_distribution.py --since 2026-04-01
    python scripts/public/mining/mine_cap_kind_distribution.py --substrate-filter gp\*
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PROJECTS_DIR = REPO / "projects"
RUBRICS_DIR = REPO / "rubrics"
OUT_JSON = REPO / "analytics" / "public" / "queries" / "classification" / "cap_kind_distribution.json"
OUT_MD = REPO / "analytics" / "public" / "queries" / "classification" / "cap_kind_distribution.md"


def derive_substrate_class(project_name: str, rubric_dir: Path) -> str:
    """Return substrate-class string for the project.

    Preference order:
      1. ``rubrics/<project>.json`` cage_meta.class field
      2. ``rubrics/dynamic_<project>.json`` cage_meta.class field
      3. Heuristic from project name pattern
    """
    for candidate in (rubric_dir / f"{project_name}.json",
                      rubric_dir / f"dynamic_{project_name}.json"):
        if candidate.exists():
            try:
                rubric = json.loads(candidate.read_text())
                cm = rubric.get("cage_meta") or {}
                cls = cm.get("class")
                if isinstance(cls, str) and cls.strip():
                    return cls.strip()
            except Exception:  # noqa: BLE001
                pass

    # Heuristic fallback by project name pattern
    n = project_name.lower()
    if n.startswith("ns_") or "ns_" in n[:5]:
        return "ns_pde"
    if n.startswith("oeis"):
        return "oeis_sequence"
    if n.startswith("gp"):
        # Numbered gp* projects span multiple substrate types; mark
        # explicitly when not declared
        return "gp_unspecified"
    if "consciousness" in n or "ai_" in n:
        return "qualitative_business"
    if n.startswith("paper") or "draft" in n:
        return "paper_review"
    if "tariff" in n or "housing" in n or "stress" in n or "passthrough" in n:
        return "qualitative_macro"
    return "uncategorized"


def parse_ts(s: str) -> datetime | None:
    if not s:
        return None
    try:
        s = s.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:  # noqa: BLE001
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--since",
        type=str,
        default=None,
        help="ISO date — only count cap_kind files modified on/after this",
    )
    ap.add_argument(
        "--substrate-filter",
        type=str,
        default=None,
        help="fnmatch pattern on project name (e.g. 'gp*')",
    )
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    args = ap.parse_args()

    cutoff_dt = parse_ts(args.since) if args.since else None

    print("=== cap-kind distribution miner ===")
    print(f"  projects: {PROJECTS_DIR}")
    print(f"  since:    {args.since or '(all)'}")
    print(f"  filter:   {args.substrate_filter or '(none)'}")

    # Per-substrate-class cap-kind counts
    by_class: dict[str, Counter[str]] = defaultdict(Counter)
    # Per-project (project_name, substrate_class, cap_kind) records
    per_project: dict[str, dict] = {}
    # Across all events
    total_events = 0
    skipped_no_class = 0
    skipped_old = 0

    if not PROJECTS_DIR.exists():
        print(f"  ERROR: {PROJECTS_DIR} not found")
        return 1

    for project_path in sorted(PROJECTS_DIR.iterdir()):
        if not project_path.is_dir():
            continue
        project_name = project_path.name
        if args.substrate_filter and not fnmatch.fnmatch(
            project_name, args.substrate_filter
        ):
            continue
        workspace = project_path / "workspace"
        if not workspace.is_dir():
            continue

        substrate_class = derive_substrate_class(project_name, RUBRICS_DIR)
        if not substrate_class:
            skipped_no_class += 1
            continue

        per_proj_cap_counts: Counter[str] = Counter()
        per_proj_iter_count = 0

        for cap_file in sorted(workspace.glob("cap_kind_iter_*.json")):
            if cutoff_dt:
                file_dt = datetime.fromtimestamp(
                    cap_file.stat().st_mtime, tz=timezone.utc
                )
                if file_dt < cutoff_dt:
                    skipped_old += 1
                    continue
            try:
                rec = json.loads(cap_file.read_text())
            except Exception:  # noqa: BLE001
                continue
            cap_kind = str(rec.get("cap_kind") or "unknown").strip().lower()
            if not cap_kind:
                cap_kind = "unknown"
            by_class[substrate_class][cap_kind] += 1
            per_proj_cap_counts[cap_kind] += 1
            per_proj_iter_count += 1
            total_events += 1

        if per_proj_iter_count > 0:
            per_project[project_name] = {
                "substrate_class": substrate_class,
                "n_iters": per_proj_iter_count,
                "cap_kind_counts": dict(per_proj_cap_counts),
                "dominant_cap_kind": (
                    per_proj_cap_counts.most_common(1)[0][0]
                    if per_proj_cap_counts
                    else None
                ),
            }

    print(f"  total cap_kind events: {total_events}")
    print(f"  substrate classes seen: {len(by_class)}")
    print(f"  projects with data: {len(per_project)}")
    if skipped_old:
        print(f"  skipped (older than --since): {skipped_old}")
    if skipped_no_class:
        print(f"  skipped (no substrate class): {skipped_no_class}")
    print()

    # Build the contingency matrix sorted by class total
    class_totals = {cls: sum(c.values()) for cls, c in by_class.items()}
    sorted_classes = sorted(class_totals, key=lambda k: -class_totals[k])
    all_cap_kinds = sorted(set().union(*[set(c) for c in by_class.values()]))

    # Per-class summary: dominant cap kind + concentration
    class_summary = {}
    for cls in sorted_classes:
        counts = by_class[cls]
        total = sum(counts.values())
        sorted_kinds = counts.most_common()
        class_summary[cls] = {
            "total_events": total,
            "n_projects": sum(
                1 for p in per_project.values() if p["substrate_class"] == cls
            ),
            "by_cap_kind": dict(counts),
            "dominant_cap_kind": sorted_kinds[0][0] if sorted_kinds else None,
            "dominant_concentration": (
                sorted_kinds[0][1] / total if (total > 0 and sorted_kinds) else 0.0
            ),
        }

    # Top recurring (substrate_class, cap_kind) clusters across the corpus
    pair_counts: list[tuple[str, str, int]] = [
        (cls, kind, count)
        for cls, c in by_class.items()
        for kind, count in c.items()
    ]
    pair_counts.sort(key=lambda t: -t[2])
    top_pairs = pair_counts[:20]

    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "since": args.since,
        "substrate_filter": args.substrate_filter,
        "total_events": total_events,
        "n_substrate_classes": len(by_class),
        "n_projects_with_data": len(per_project),
        "class_summary": class_summary,
        "top_pairs": [
            {"substrate_class": cls, "cap_kind": kind, "count": count}
            for cls, kind, count in top_pairs
        ],
        "per_project": per_project,
        "all_cap_kinds": all_cap_kinds,
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2))
    print(f"  wrote {args.out_json}")

    # Operator-readable markdown summary
    md = ["# Cap-Kind Distribution Across Substrate Classes\n"]
    md.append(f"_Generated {payload['generated_utc']}_  ")
    md.append(
        f"_Total events:_ {total_events}  _Classes:_ {len(by_class)}  "
        f"_Projects with data:_ {len(per_project)}\n"
    )
    md.append("## By substrate class\n")
    md.append(
        "| Class | Total | Dominant cap kind | Concentration | Projects |\n"
        "|---|---:|---|---:|---:|"
    )
    for cls in sorted_classes:
        s = class_summary[cls]
        md.append(
            f"| `{cls}` | {s['total_events']} | "
            f"{s['dominant_cap_kind'] or '—'} | "
            f"{s['dominant_concentration']:.1%} | {s['n_projects']} |"
        )
    md.append("")
    md.append("## Top (substrate_class, cap_kind) pairs\n")
    md.append("| # | Class | Cap kind | Count |\n|---:|---|---|---:|")
    for i, (cls, kind, count) in enumerate(top_pairs, 1):
        md.append(f"| {i} | `{cls}` | `{kind}` | {count} |")
    md.append("")
    md.append("## Per-project dominant pattern\n")
    md.append("| Project | Class | Iters | Dominant cap kind |\n|---|---|---:|---|")
    for proj, info in sorted(
        per_project.items(), key=lambda x: -x[1]["n_iters"]
    )[:30]:
        md.append(
            f"| `{proj}` | `{info['substrate_class']}` | "
            f"{info['n_iters']} | {info['dominant_cap_kind'] or '—'} |"
        )
    if len(per_project) > 30:
        md.append(f"\n_({len(per_project) - 30} more projects truncated)_\n")
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(md) + "\n")
    print(f"  wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
