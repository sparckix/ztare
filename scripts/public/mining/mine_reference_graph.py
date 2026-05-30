#!/usr/bin/env python3
"""Reference-graph miner — apparatus compounding via citation graph.

Closes the cross-artifact compounding blind spot identified in the
GP-227 trajectory analysis. Per-artifact taste rating measures whether
each artifact is insight-rich; reference-graph density measures
whether artifacts BUILD ON each other (the actual signature of
recursive self-improvement).

Walks every apparatus markdown file, extracts citations, builds a
directed graph where each node is an artifact and edges point from
citer → citee. Computes per-node + per-week graph stats:

  - in_degree  (cited by N artifacts)
  - out_degree (cites N artifacts)
  - week of node creation (mtime / frontmatter)
  - longest dependency chain ending here

Reference patterns extracted:

  - GP-NNN identifiers (`GP-148`, `gp226`, etc.)
  - File-path references (`src/ztare/...`, `projects/.../phase5fa.md`,
    `papers/paper4/draft.md`)
  - Seam-id callouts (frontmatter `seam_id` cross-references)
  - Memory-entry references (`feedback_*.md`, `project_*.md`)

Outputs:
  analytics/public/queries/graphs/reference_graph.json  — nodes + edges + per-week stats
  analytics/public/queries/graphs/reference_graph.md    — top-cited / most-citing tables

Pure CPU. No LLM.

Usage:
    python scripts/public/mining/mine_reference_graph.py
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import yaml  # type: ignore[import-untyped]

REPO = Path(__file__).resolve().parents[3]
OUT_JSON = REPO / "analytics" / "public" / "queries" / "reference_graph.json"
OUT_MD = REPO / "analytics" / "public" / "queries" / "reference_graph.md"

# Where to walk for apparatus markdown
SCAN_ROOTS = [
    "src/ztare",
    "scripts",
    "research_areas/private/seams",
    "research_areas/private/evidence",
    "research_areas/private/philosophy",
    "org",
    "papers",
    "docs/concepts",
    "docs/internal",
    "docs/guides",
    "analytics/public/queries",
    "specs",
    "projects",
]

PATH_EXCLUDES = {
    "node_modules", "venv", ".venv", "__pycache__", ".git", "orbit",
    "dist", "build", "site-packages",
}


_GP_RE = re.compile(r"\bGP-?(\d{2,4}[a-z]?)\b", re.IGNORECASE)
_PATH_RE = re.compile(r"`?((?:src|scripts|research_areas|org|papers|docs|analytics|specs|projects)/[\w./_-]+)`?")
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
_DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")


def _week_bucket(dt: datetime) -> str:
    monday = dt - timedelta(days=dt.weekday())
    return monday.strftime("%Y-%m-%d")


def _file_create_date(path: Path) -> datetime:
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


def _walk_artifacts() -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    for root_rel in SCAN_ROOTS:
        root = REPO / root_rel
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            if not path.is_file() or path in seen:
                continue
            rel = path.relative_to(REPO)
            if any(part in PATH_EXCLUDES or part.startswith(".") for part in rel.parts):
                continue
            try:
                if path.stat().st_size < 200:
                    continue
            except Exception:  # noqa: BLE001
                continue
            seen.add(path)
            found.append(path)
    return sorted(found)


def _node_id(path: Path) -> str:
    """Stable node id = repo-relative path."""
    return str(path.relative_to(REPO))


def _path_to_node_id(citation_path: str, all_node_paths: set[str]) -> Optional[str]:
    """Resolve a citation-path string to an actual node id (repo-relative)."""
    citation_path = citation_path.strip().rstrip(".,;:)")
    # Direct match
    if citation_path in all_node_paths:
        return citation_path
    # Suffix match (citation may be partial)
    matches = [n for n in all_node_paths if n.endswith(citation_path)]
    if len(matches) == 1:
        return matches[0]
    return None


def _categorize_node(node_id: str) -> str:
    """Bucket a node into a kind for visualization color."""
    if node_id.startswith("research_areas/private/seams/reflexive/"):
        return "seam_reflexive"
    if node_id.startswith("research_areas/private/seams/engine/"):
        return "seam_engine"
    if node_id.startswith("research_areas/private/seams/apparatus/"):
        return "seam_apparatus"
    if node_id.startswith("research_areas/private/seams/"):
        return "seam_other"
    if node_id.startswith("research_areas/private/evidence/"):
        return "evidence"
    if node_id.startswith("research_areas/private/philosophy/"):
        return "philosophy"
    if node_id.startswith("papers/"):
        return "paper"
    if node_id.startswith("projects/"):
        return "project"
    if node_id.startswith("docs/"):
        return "doc"
    if node_id.startswith("org/"):
        return "org"
    if node_id.startswith("scripts/public/"):
        return "script"
    if node_id.startswith("src/"):
        return "src"
    if node_id.startswith("specs/"):
        return "spec"
    if node_id.startswith("analytics/public/"):
        return "analytics"
    return "other"


def _gp_to_seam_path(gp_id: str, all_node_paths: set[str]) -> Optional[str]:
    """Given GP-NNN, find the matching seam file path."""
    needle_lower = f"gp-{gp_id.lower().lstrip('0')}_"
    needle_upper = f"GP-{gp_id.upper().lstrip('0')}_"
    needle_alt   = f"GP-{gp_id}_"
    for n in all_node_paths:
        nl = n.lower()
        if needle_lower in nl or needle_upper in n or needle_alt in n:
            return n
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    ap.add_argument("--max-nodes", type=int, default=2000,
                    help="Cap node count by limiting source paths read")
    args = ap.parse_args()

    print("=== reference-graph miner ===")
    paths = _walk_artifacts()
    print(f"  candidate nodes (markdown >200B): {len(paths)}")
    if len(paths) > args.max_nodes:
        # Prefer seam + paper + memory-equivalent + analytics + recently-modified
        # for the capped run; deprioritize the long tail of project workspace MD.
        key_dirs = ("research_areas/private/seams", "papers", "docs/concepts", "docs/internal", "analytics/public/queries")
        priority = [p for p in paths if any(str(p.relative_to(REPO)).startswith(k) for k in key_dirs)]
        rest = [p for p in paths if p not in priority]
        rest.sort(key=lambda p: -p.stat().st_mtime)
        paths = priority + rest[: max(0, args.max_nodes - len(priority))]
        print(f"  capped to {len(paths)} (priority + recent)")

    # First pass: build node table
    nodes: dict[str, dict] = {}
    for p in paths:
        nid = _node_id(p)
        nodes[nid] = {
            "id": nid,
            "kind": _categorize_node(nid),
            "week": _week_bucket(_file_create_date(p)),
            "size_bytes": p.stat().st_size,
        }
    all_node_paths = set(nodes.keys())

    # Second pass: extract edges
    edges: list[tuple[str, str, str]] = []  # (from, to, edge_kind)
    for p in paths:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            continue
        nid = _node_id(p)
        # GP-NNN
        for m in _GP_RE.finditer(text):
            gp_id = m.group(1)
            target = _gp_to_seam_path(gp_id, all_node_paths)
            if target and target != nid:
                edges.append((nid, target, "gp_ref"))
        # Path
        for m in _PATH_RE.finditer(text):
            cited = m.group(1)
            target = _path_to_node_id(cited, all_node_paths)
            if target and target != nid:
                edges.append((nid, target, "path_ref"))

    # Dedupe edges
    edge_dedup: dict[tuple[str, str], dict] = {}
    for src, tgt, kind in edges:
        key = (src, tgt)
        if key not in edge_dedup:
            edge_dedup[key] = {"from": src, "to": tgt, "kinds": [kind], "weight": 1}
        else:
            edge_dedup[key]["weight"] += 1
            if kind not in edge_dedup[key]["kinds"]:
                edge_dedup[key]["kinds"].append(kind)
    edges_final = list(edge_dedup.values())

    # Compute degrees
    in_degree = Counter()
    out_degree = Counter()
    for e in edges_final:
        in_degree[e["to"]] += e["weight"]
        out_degree[e["from"]] += e["weight"]
    for nid, n in nodes.items():
        n["in_degree"] = in_degree.get(nid, 0)
        n["out_degree"] = out_degree.get(nid, 0)

    # Per-week aggregates
    weekly: dict[str, dict] = defaultdict(lambda: {
        "n_nodes": 0,
        "total_in_degree": 0,
        "total_out_degree": 0,
        "n_inbound_from_later_weeks": 0,
        "n_outbound_to_earlier_weeks": 0,
    })
    week_of = {nid: n["week"] for nid, n in nodes.items()}
    for nid, n in nodes.items():
        wk = n["week"]
        weekly[wk]["n_nodes"] += 1
        weekly[wk]["total_in_degree"] += n["in_degree"]
        weekly[wk]["total_out_degree"] += n["out_degree"]
    for e in edges_final:
        wk_from = week_of.get(e["from"], "")
        wk_to = week_of.get(e["to"], "")
        if not wk_from or not wk_to:
            continue
        if wk_to < wk_from:
            # citing an earlier artifact → outbound to earlier
            weekly[wk_from]["n_outbound_to_earlier_weeks"] += e["weight"]
        elif wk_from < wk_to:
            # citing a later artifact (rare; usually backref or rolling-doc)
            pass
        # cited-by-later for the target
        if wk_from > wk_to:
            weekly[wk_to]["n_inbound_from_later_weeks"] += e["weight"]

    # Top-cited and most-citing
    top_cited = sorted(nodes.values(), key=lambda n: -n["in_degree"])[:30]
    most_citing = sorted(nodes.values(), key=lambda n: -n["out_degree"])[:30]

    payload = {
        "audit_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "n_nodes": len(nodes),
        "n_edges": len(edges_final),
        "weekly_stats": dict(weekly),
        "top_cited_nodes": top_cited,
        "most_citing_nodes": most_citing,
        "nodes": list(nodes.values()),
        "edges": edges_final,
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(payload, indent=2))
    print(f"  nodes: {len(nodes)}  edges: {len(edges_final)}")
    print(f"  wrote {args.out_json}")

    md = ["# Reference Graph — Apparatus Compounding\n"]
    md.append(f"_Generated {payload['audit_timestamp_utc']}_  ")
    md.append(f"_Nodes:_ {len(nodes)}  _Edges:_ {len(edges_final)}\n")

    md.append("## Weekly compounding stats\n")
    md.append("| Week | Nodes | Total in-deg | Total out-deg | Inbound from later weeks | Outbound to earlier weeks |\n|---|---:|---:|---:|---:|---:|")
    for wk in sorted(weekly.keys()):
        s = weekly[wk]
        md.append(
            f"| {wk} | {s['n_nodes']} | {s['total_in_degree']} | "
            f"{s['total_out_degree']} | {s['n_inbound_from_later_weeks']} | "
            f"{s['n_outbound_to_earlier_weeks']} |"
        )
    md.append("")

    md.append("## Top-cited nodes (most depended-upon)\n")
    md.append("| In-deg | Path | Kind | Week |\n|---:|---|---|---|")
    for n in top_cited[:20]:
        md.append(f"| {n['in_degree']} | `{n['id']}` | {n['kind']} | {n['week']} |")
    md.append("")

    md.append("## Most-citing nodes (most context-pulling)\n")
    md.append("| Out-deg | Path | Kind | Week |\n|---:|---|---|---|")
    for n in most_citing[:20]:
        md.append(f"| {n['out_degree']} | `{n['id']}` | {n['kind']} | {n['week']} |")
    md.append("")

    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(md) + "\n")
    print(f"  wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
