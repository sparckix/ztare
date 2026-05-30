#!/usr/bin/env python3
"""Cross-miner triangulation — per-target dossier joining 4 miner outputs.

Joins the 4 most useful miner outputs by ``target`` name to produce
a per-target compounding-signal view:

  - **Failure clusters** (`failure_clusters.md` + cluster JSON) — which
    type-head + patch-class + category combinations recurred for this
    target
  - **CANNOT-PATCH events** (`projects/ns_millennium_hunt/workspace/queries/typed_endpoint_failure_log.jsonl`) — raw
    events the LLM declined to patch on this target
  - **Endpoint compression candidates** (`endpoint_compression_audit.json`)
    — endpoints on this target that match the X_of_Y projection shape
  - **Cap-kind distribution** (`cap_kind_distribution.json`) — when
    a project related to this target hit which cap kinds

Output:
  ``projects/ns_millennium_hunt/workspace/queries/triangulation_per_target.json``
  ``projects/ns_millennium_hunt/workspace/queries/triangulation_per_target.md``

Pure CPU + jsonl reads. No LLM.

Usage:
    python scripts/public/mining/triangulate_per_target.py
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
QUERIES = REPO / "analytics" / "public" / "queries"
OUT_JSON = REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries" / "triangulation_per_target.json"
OUT_MD = REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries" / "triangulation_per_target.md"


def load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:  # noqa: BLE001
                continue
    except Exception:  # noqa: BLE001
        return []
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    args = ap.parse_args()

    print("=== cross-miner triangulation ===")

    # ---- Source 1: typed_endpoint_failure_log.jsonl (CANNOT-PATCH events) ----
    failure_events = load_jsonl(
        REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
        / "typed_endpoint_failure_log.jsonl"
    )
    print(f"  CANNOT-PATCH events: {len(failure_events)}")

    # ---- Source 2: endpoint_compression_audit.json (Layer 3 candidates) ----
    compression_audit = load_json(QUERIES / "lean" / "endpoint_compression_audit.json") or {}
    compression_candidates = compression_audit.get("candidates", []) or []
    print(f"  compression candidates: {len(compression_candidates)}")

    # ---- Source 3: failure_clusters.md is markdown; the json equivalent
    # is what failure_cluster_analyzer would emit if asked. Re-cluster
    # from the raw events at audit time. ----
    cluster_index: dict[str, list[dict]] = defaultdict(list)
    for e in failure_events:
        target = str(e.get("target") or "")
        if not target:
            continue
        cluster_index[target].append(e)

    # ---- Source 4: cap_kind_distribution.json (per_project) ----
    cap_kind_data = load_json(QUERIES / "classification" / "cap_kind_distribution.json") or {}
    per_project_cap = cap_kind_data.get("per_project", {}) or {}
    print(f"  cap_kind per-project records: {len(per_project_cap)}")

    # Build the per-target dossier
    targets_seen: set[str] = set()
    for events in cluster_index.values():
        for e in events:
            t = str(e.get("target") or "")
            if t:
                targets_seen.add(t)
    for c in compression_candidates:
        t = str(c.get("target") or "")
        if t:
            targets_seen.add(t)
    print(f"  unique targets: {len(targets_seen)}")

    dossiers: list[dict] = []
    for target in sorted(targets_seen):
        events = cluster_index.get(target, [])
        # Cluster events by (patch_class, category)
        cluster_counts: Counter = Counter()
        for e in events:
            cls = str(e.get("patch_class") or "?")
            cat = str(e.get("category") or "?")
            cluster_counts[(cls, cat)] += 1

        # Compression candidates for this target
        target_compressions = [
            c
            for c in compression_candidates
            if str(c.get("target") or "") == target
        ]

        # Type head (used for cap-kind project lookup heuristic)
        type_head = re.split(r"::", target, maxsplit=1)[0]

        # Cap-kind data: targets are NS Track B Lean obligation names;
        # cap_kind data is per-project. Join via fuzzy match on name
        # fragments. The NS targets are typically suffixed/prefixed
        # variations of project names — best-effort.
        related_cap_kind_projects = []
        head_tokens = re.findall(r"[A-Z][a-z]+", type_head)[:3]
        if head_tokens:
            keyword = head_tokens[0].lower()
            for proj_name, info in per_project_cap.items():
                if keyword in proj_name.lower():
                    related_cap_kind_projects.append({
                        "project": proj_name,
                        "n_iters": info.get("n_iters"),
                        "dominant_cap_kind": info.get("dominant_cap_kind"),
                    })

        compounding_score = (
            len(events) * 1
            + len(target_compressions) * 3  # compression candidates worth more
            + sum(c for c in cluster_counts.values() if c >= 2) * 2
        )

        dossiers.append({
            "target": target,
            "type_head": type_head,
            "compounding_score": compounding_score,
            "n_cannot_patch_events": len(events),
            "cluster_summary": [
                {"patch_class": cls, "category": cat, "count": n}
                for (cls, cat), n in cluster_counts.most_common()
            ],
            "compression_candidates": [
                {
                    "field": c.get("field"),
                    "name_pattern": c.get("name_pattern"),
                    "explanation": (c.get("explanation") or "")[:200],
                }
                for c in target_compressions
            ],
            "related_cap_kind_projects": related_cap_kind_projects,
        })

    dossiers.sort(key=lambda d: -d["compounding_score"])

    payload = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "n_targets": len(dossiers),
        "n_cannot_patch_events_total": len(failure_events),
        "n_compression_candidates_total": len(compression_candidates),
        "dossiers": dossiers,
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2))
    print(f"  wrote {args.out_json}")

    md = ["# Cross-Miner Triangulation — Per-Target Dossier\n"]
    md.append(f"_Generated {payload['audit_timestamp_utc']}_  ")
    md.append(
        f"_Targets:_ {len(dossiers)}  "
        f"_Total CANNOT-PATCH:_ {len(failure_events)}  "
        f"_Total compression candidates:_ {len(compression_candidates)}\n"
    )
    md.append(
        "## Dossier (top 20 by compounding-signal score)\n"
        "Score = `n_events + 3·n_compression + 2·n_recurring_clusters`\n"
    )
    md.append("")
    for d in dossiers[:20]:
        md.append(f"### `{d['target']}` (compounding_score = {d['compounding_score']})\n")
        md.append(f"- CANNOT-PATCH events: **{d['n_cannot_patch_events']}**")
        if d["cluster_summary"]:
            md.append("- Clusters (recurring patch_class + category):")
            for c in d["cluster_summary"]:
                md.append(
                    f"  - {c['count']}× `{c['patch_class']}` → "
                    f"`{c['category']}`"
                )
        if d["compression_candidates"]:
            md.append(
                f"- **{len(d['compression_candidates'])} compression candidate(s)** "
                "(GP-223 Layer 3 — could close by projection):"
            )
            for c in d["compression_candidates"]:
                md.append(
                    f"  - field `{c['field']}` (pattern: `{c['name_pattern']}`)"
                )
        if d["related_cap_kind_projects"]:
            md.append(
                f"- Related projects (cap-kind): "
                + ", ".join(
                    f"`{p['project']}`(n={p['n_iters']})"
                    for p in d["related_cap_kind_projects"][:3]
                )
            )
        md.append("")
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(md) + "\n")
    print(f"  wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
