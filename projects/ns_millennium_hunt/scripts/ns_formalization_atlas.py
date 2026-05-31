#!/usr/bin/env python3
"""Generate a standalone interactive atlas for the NS Lean formalization.

The atlas is a consumption artifact for mathematicians: it compresses the Lean
declaration graph, route/friction diagnostics, and current NS graph packet into
one self-contained HTML page.  It is deliberately advisory.  It does not certify
claims, close ticks, or write official store state.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
QUERIES = REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
LEAN_ROOT = REPO / "ztare_proofs" / "ZtareProofs"
DEFAULT_OUT = REPO / "projects" / "ns_millennium_hunt" / "public" / "index.html"
EMBEDDING_MANIFEST = REPO / "projects" / "ns_millennium_hunt" / "public" / "ns_atlas_embeddings_manifest.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_rag_manifest() -> dict:
    if not EMBEDDING_MANIFEST.exists():
        return {"available": False}
    try:
        manifest = load_json(EMBEDDING_MANIFEST)
    except Exception as exc:  # pragma: no cover - defensive for corrupt generated artifacts.
        return {"available": False, "error": str(exc)}
    return {
        "available": True,
        "generated_at": manifest.get("generated_at"),
        "model": manifest.get("model"),
        "dimensions": manifest.get("dimensions"),
        "entries": manifest.get("entries"),
        "corpus_entries": manifest.get("corpus_entries"),
        "selection": manifest.get("selection"),
        "corpus_sha256": manifest.get("corpus_sha256"),
        "embedding_sha256": manifest.get("embedding_sha256"),
        "corpus_path": manifest.get("corpus_path"),
        "embedding_path": manifest.get("embedding_path"),
    }


def compact_doc(text: str, limit: int = 380) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def strip_lean_comments_and_strings(text: str) -> str:
    """Remove Lean comments and strings while preserving line positions."""
    out: list[str] = []
    i = 0
    depth = 0
    in_string = False
    escaped = False
    while i < len(text):
        char = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if depth:
            if char == "/" and nxt == "-":
                depth += 1
                out.extend((" ", " "))
                i += 2
                continue
            if char == "-" and nxt == "/":
                depth -= 1
                out.extend((" ", " "))
                i += 2
                continue
            out.append("\n" if char == "\n" else " ")
            i += 1
            continue
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            out.append("\n" if char == "\n" else " ")
            i += 1
            continue
        if char == "/" and nxt == "-":
            depth = 1
            out.extend((" ", " "))
            i += 2
            continue
        if char == "-" and nxt == "-":
            while i < len(text) and text[i] != "\n":
                out.append(" ")
                i += 1
            continue
        if char == '"':
            in_string = True
            out.append(" ")
            i += 1
            continue
        out.append(char)
        i += 1
    return "".join(out)


def declaration_audit() -> dict:
    files = sorted(LEAN_ROOT.glob("ns*.lean"))
    declaration_patterns = {
        "axiom": re.compile(r"^\s*axiom\s+([^\s:]+)", re.M),
        "opaque": re.compile(r"^\s*opaque\s+([^\s:]+)", re.M),
        "unsafe": re.compile(r"^\s*unsafe\s+([^\s:]+)", re.M),
        "partial": re.compile(r"^\s*partial\s+([^\s:]+)", re.M),
        "constant": re.compile(r"^\s*constant\s+([^\s:]+)", re.M),
    }
    rows: dict[str, list[dict]] = {key: [] for key in declaration_patterns}
    sorry_rows: list[dict] = []
    admit_rows: list[dict] = []
    line_count = 0
    for path in files:
        raw = path.read_text(encoding="utf-8", errors="ignore")
        line_count += raw.count("\n") + 1
        text = strip_lean_comments_and_strings(raw)
        rel = str(path.relative_to(REPO))
        for kind, pattern in declaration_patterns.items():
            for match in pattern.finditer(text):
                rows[kind].append({
                    "file": rel,
                    "line": text.count("\n", 0, match.start()) + 1,
                    "name": match.group(1),
                })
        for match in re.finditer(r"\bsorry\b", text):
            sorry_rows.append({
                "file": rel,
                "line": text.count("\n", 0, match.start()) + 1,
            })
        for match in re.finditer(r"\badmit\b", text):
            admit_rows.append({
                "file": rel,
                "line": text.count("\n", 0, match.start()) + 1,
            })

    def top_files(kind: str) -> list[dict]:
        counts = Counter(row["file"] for row in rows[kind])
        return [
            {"file": file, "count": count}
            for file, count in counts.most_common(14)
        ]

    return {
        "scope": "direct ns*.lean files under ztare_proofs/ZtareProofs, comments and strings stripped before counting",
        "files": len(files),
        "lines": line_count,
        "counts": {key: len(value) for key, value in rows.items()},
        "sorry": len(sorry_rows),
        "admit": len(admit_rows),
        "top_axiom_files": top_files("axiom"),
        "top_opaque_files": top_files("opaque"),
        "sorry_locs": sorry_rows[:80],
        "sample_axioms": rows["axiom"][:80],
    }


def parse_tick_timeline(paths: list[Path]) -> list[dict]:
    rows: list[dict] = []
    seen: set[tuple[int, str]] = set()
    pattern = re.compile(r"(?m)^#{2,4}\s+((?:POST-)?TICK(\d+)[^\n]*)")
    for path in paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        matches = list(pattern.finditer(text))
        for i, match in enumerate(matches):
            tick = int(match.group(2))
            heading = match.group(1).strip()
            key = (tick, heading)
            if key in seen:
                continue
            seen.add(key)
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            excerpt = compact_doc(text[match.end():end], limit=420)
            rows.append({
                "tick": tick,
                "heading": heading,
                "source": str(path.relative_to(REPO)),
                "excerpt": excerpt,
            })
    rows.sort(key=lambda row: (row["tick"], row["heading"]))
    return rows


def derive_proof_status_kpis(status_counts: Counter, audit: dict,
                              duplicate_report: dict | None) -> dict:
    """Compute the disciplined headline KPIs surfaced in the public HTML.
    Mirrors the metric definitions in
    ``projects/ns_millennium_hunt/workspace/ns_proof_status_benchmark_*.md``
    so the page and the benchmark doc tell the same story.

    Every KPI carries an honest non-claim or a caveat — the renderer
    surfaces those next to the number, never the number alone.
    """
    closed = status_counts.get("closed_theorem", 0)
    exclusion = status_counts.get("exclusion_theorem", 0)
    receipts = status_counts.get("receipt_interface", 0)
    obligations = status_counts.get("open_obligation", 0)
    falsifiers = status_counts.get("falsifier_surface", 0)
    declarations_untyped = status_counts.get("declaration", 0)
    unclosed = status_counts.get("unclosed_proof_gap", 0)
    total_decls = sum(status_counts.values())

    counts = audit.get("counts", {})
    axioms = counts.get("axiom", 0)
    opaques = counts.get("opaque", 0)
    sorries = audit.get("sorry", 0)
    admits = audit.get("admit", 0)
    debt_total = axioms + opaques + sorries

    def _ratio(num: int, den: int) -> float | None:
        return round(num / den, 3) if den else None

    avenues = duplicate_report.get("n_distinct_research_avenues_est") \
        if duplicate_report else None
    dup_factor = duplicate_report.get("duplication_factor_est") \
        if duplicate_report else None
    n_clusters = duplicate_report.get("n_clusters_size_ge_2") \
        if duplicate_report else None

    return {
        "non_claim": (
            "This page is public self-measurement for the ZTARE NS campaign. "
            "It does not license any Clay proof claim. The corpus is best "
            "read as a large, disciplined residual-characterization and "
            "route-demotion atlas with visible proof debt, not as a clean "
            "formal proof corpus."
        ),
        "totals": {
            "files": audit.get("files"),
            "raw_lines": audit.get("lines"),
            "graph_declarations": total_decls,
            "distinct_research_avenues_est": avenues,
            "duplication_factor_est": dup_factor,
            "near_duplicate_clusters_size_ge_2": n_clusters,
        },
        "status_breakdown": {
            "closed_theorem": closed,
            "exclusion_theorem": exclusion,
            "receipt_interface": receipts,
            "open_obligation": obligations,
            "falsifier_surface": falsifiers,
            "untyped_declaration": declarations_untyped,
            "unclosed_proof_gap": unclosed,
        },
        "trust_footprint": {
            "axiom": axioms,
            "opaque": opaques,
            "sorry": sorries,
            "admit": admits,
            "debt_share": _ratio(debt_total, total_decls),
        },
        "process_ratios": {
            "exclusion_to_receipt": _ratio(exclusion, receipts),
            "closed_or_exclusion_share": _ratio(closed + exclusion, total_decls),
            "open_obligation_share": _ratio(obligations, total_decls),
            "falsifier_to_closed": _ratio(falsifiers, closed),
        },
        "axes": [
            # Mirrors the §"Outcome rubric" 0-4 scorecard in the benchmark
            # doc. Self-scored, surfaced honestly. NOT a public ranking.
            {"axis": "Clay statement fidelity", "self_score": 3, "max": 4,
             "read": "Exact target statement present in the corpus; not the proof."},
            {"axis": "Analytic obligation depth", "self_score": 4, "max": 4,
             "read": "Deep PDE-side machinery (BKM, ESS-L3, pressure/C7 lane)."},
            {"axis": "Clean proof footprint", "self_score": 1, "max": 4,
             "read": (f"Heavy axiom/opaque debt ({axioms} axioms, {opaques} opaques, "
                      f"{sorries} sorries). This is the weakest axis.")},
            {"axis": "Residual localization", "self_score": 4, "max": 4,
             "read": ("Named failing estimates, missing receipts (e.g. "
                      "C7NonadaptiveSourceSelectionReceipt), explicit no-go basins.")},
            {"axis": "Negative-result value", "self_score": 4, "max": 4,
             "read": f"{exclusion} typed exclusion theorems + {falsifiers} falsifier surfaces."},
            {"axis": "External reproducibility", "self_score": 2, "max": 4,
             "read": "Buildable locally; not yet cold-read by an outside Lean reviewer."},
        ],
        "source_md": "projects/ns_millennium_hunt/workspace/ns_proof_status_benchmark_20260524.md",
    }


def build_data() -> dict:
    artifact = load_json(QUERIES / "ns_trackb_artifact_graph.json")
    constraint = load_json(QUERIES / "ns_trackb_constraint_basin_graph.json")
    maze = load_json(QUERIES / "ns_trackb_maze_view.json")
    closure = load_json(QUERIES / "ns_trackb_closure_miner_report.json")

    raw_nodes = artifact.get("@graph", [])
    decl_raw = [node for node in raw_nodes if node.get("@type") == "ns_lean_decl"]
    file_raw = [node for node in raw_nodes if node.get("@type") == "ns_lean_file"]

    canonical_by_orig: dict[str, str] = {}
    unique_seen: Counter[str] = Counter()
    unique_by_orig: dict[str, list[str]] = defaultdict(list)
    node_records: list[dict] = []
    source_order: list[tuple[str, str]] = []

    for raw in decl_raw:
        orig_id = str(raw.get("@id", ""))
        unique_seen[orig_id] += 1
        suffix = "" if unique_seen[orig_id] == 1 else f"#{unique_seen[orig_id]}"
        unique_id = f"{orig_id}{suffix}"
        canonical_by_orig.setdefault(orig_id, unique_id)
        unique_by_orig[orig_id].append(unique_id)
        source_order.append((unique_id, orig_id))
        node_records.append({
            "id": unique_id,
            "orig": orig_id,
            "name": raw.get("name", ""),
            "file": str(raw.get("file", "")).replace("ns_file:", ""),
            "path": raw.get("path", ""),
            "line": raw.get("line"),
            "kind": raw.get("kind", ""),
            "status": raw.get("status", ""),
            "tags": raw.get("content_tags", [])[:10],
            "ops": raw.get("op_classes", [])[:8],
            "doc": compact_doc(raw.get("doc_excerpt", "")),
            "uses_orig": [
                dep for dep in raw.get("uses_decl", [])
                if dep in canonical_by_orig or dep.startswith("ns_decl:")
            ],
        })

    index = {row["id"]: i for i, row in enumerate(node_records)}
    canonical_index = {
        orig: index[unique_id]
        for orig, unique_id in canonical_by_orig.items()
        if unique_id in index
    }

    used_by: dict[int, list[int]] = defaultdict(list)
    edges: list[list[int]] = []
    for i, row in enumerate(node_records):
        uses: list[int] = []
        for dep in row.pop("uses_orig"):
            j = canonical_index.get(dep)
            if j is None or j == i:
                continue
            uses.append(j)
            used_by[j].append(i)
            edges.append([i, j])
        row["uses"] = sorted(set(uses))[:80]

    for i, row in enumerate(node_records):
        row["used_by"] = sorted(set(used_by.get(i, [])))[:120]
        row["used_by_count"] = len(set(used_by.get(i, [])))

    file_records = []
    file_status_counts: dict[str, Counter[str]] = defaultdict(Counter)
    file_kind_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in node_records:
        file_status_counts[row["file"]][row["status"]] += 1
        file_kind_counts[row["file"]][row["kind"]] += 1
    for raw in file_raw:
        name = str(raw.get("name", ""))
        file_records.append({
            "id": raw.get("@id", ""),
            "name": name,
            "path": raw.get("path", ""),
            "decl_count": raw.get("decl_count", 0),
            "imports": [str(item).replace("ns_file:", "") for item in raw.get("imports", [])],
            "tags": raw.get("content_tags", [])[:10],
            "ops": raw.get("op_classes", [])[:8],
            "status_counts": dict(file_status_counts.get(name, Counter())),
            "kind_counts": dict(file_kind_counts.get(name, Counter())),
        })
    file_records.sort(key=lambda row: (-int(row.get("decl_count", 0)), row["name"]))

    status_counts = Counter(row["status"] for row in node_records)
    kind_counts = Counter(row["kind"] for row in node_records)
    tag_counts = Counter(tag for row in node_records for tag in row["tags"])

    quantity_nodes = [
        node for node in constraint.get("@graph", [])
        if node.get("@type") == "ns_lean_quantity"
    ]
    quantity_nodes.sort(
        key=lambda node: -int(node.get("in_degree", 0) + node.get("out_degree", 0))
    )
    top_quantities = [
        {
            "name": str(node.get("@id", "")).replace("qty:", ""),
            "in_degree": node.get("in_degree", 0),
            "out_degree": node.get("out_degree", 0),
        }
        for node in quantity_nodes[:80]
    ]

    layers = maze.get("layers", {})
    recommendations = layers.get("disagreement_intelligence", [])
    temporal = layers.get("temporal_route_signals", [])
    aliases = layers.get("text_heterogeneous_aliases", [])
    locality = layers.get("locality_neighborhoods", [])
    closure_targets = closure.get("ranked_targets", [])[:80]

    timeline = parse_tick_timeline([
        REPO / "projects" / "ns_millennium_hunt" / "workspace" / "ns_residual_manifest.md",
        REPO / "projects" / "ns_millennium_hunt" / "research-output" / "2026-05-19-ns-research-log.md",
    ])

    audit = declaration_audit()
    live_kind_counts = dict(kind_counts)
    for key, value in audit.get("counts", {}).items():
        live_kind_counts[key] = value
    dup_path = QUERIES / "ns_near_duplicate_clusters.json"
    duplicate_report = load_json(dup_path) if dup_path.exists() else None
    kpis = derive_proof_status_kpis(status_counts, audit, duplicate_report)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "decls": len(node_records),
            "files": len(file_records),
            "edges": len(edges),
            "quantities": len(quantity_nodes),
            "status_counts": dict(status_counts),
            "kind_counts": live_kind_counts,
            "top_tags": tag_counts.most_common(18),
        },
        "audit": audit,
        "duplicate_report": duplicate_report,
        "proof_status_kpis": kpis,
        "nodes": node_records,
        "edges": edges[:180000],
        "files": file_records,
        "top_quantities": top_quantities,
        "maze": {
            "funnel_shape": maze.get("funnel_shape", {}),
            "recommendations": recommendations[:24],
            "temporal": temporal[:36],
            "aliases": aliases[:24],
            "locality": locality[:24],
            "algorithm_consensus": layers.get("algorithm_consensus", [])[:18],
            "algorithm_disagreement": layers.get("sink_disagreement", [])[:18],
            "integrity": maze.get("integrity", {}),
        },
        "closure_targets": closure_targets,
        "timeline": timeline[-80:],
        "source_paths": {
            "artifact_graph": str((QUERIES / "ns_trackb_artifact_graph.json").relative_to(REPO)),
            "constraint_graph": str((QUERIES / "ns_trackb_constraint_basin_graph.json").relative_to(REPO)),
            "maze_view": str((QUERIES / "ns_trackb_maze_view.json").relative_to(REPO)),
            "unified_jsonl": str((QUERIES / "ns_graph_unified_intelligence.jsonl").relative_to(REPO)),
        },
        "rag": load_rag_manifest(),
    }


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>NS Lean Formalization Atlas</title>
  <style>
    :root {
      --bg: #f6f7f4;
      --surface: #ffffff;
      --surface-2: #eef2f1;
      --ink: #161616;
      --muted: #5f6665;
      --line: #d8ddda;
      --teal: #0f766e;
      --indigo: #4338ca;
      --amber: #b45309;
      --red: #b91c1c;
      --green: #15803d;
      --violet: #7c3aed;
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: var(--ink); background: var(--bg); }
    button, input, select { font: inherit; }
    .app { min-height: 100vh; display: grid; grid-template-rows: auto 1fr; }
    header { display: grid; grid-template-columns: 1fr auto; gap: 16px; align-items: start; padding: 18px 22px; border-bottom: 1px solid var(--line); background: var(--surface); }
    h1 { margin: 0; font-size: 28px; line-height: 1.1; letter-spacing: 0; }
    .sub { margin-top: 6px; color: var(--muted); max-width: 980px; line-height: 1.45; }
    .metrics { display: grid; grid-template-columns: repeat(4, minmax(92px, 1fr)); gap: 8px; min-width: 420px; }
    .metric { border: 1px solid var(--line); border-radius: 8px; padding: 9px 10px; background: var(--surface-2); }
    .metric strong { display: block; font-size: 20px; }
    .metric span { color: var(--muted); font-size: 12px; }
    main { display: grid; grid-template-columns: 320px minmax(480px, 1fr) 360px; min-height: 0; }
    aside, .inspector { overflow: auto; padding: 14px; border-right: 1px solid var(--line); background: var(--surface); }
    .inspector { border-left: 1px solid var(--line); border-right: 0; }
    .stage { min-width: 0; display: grid; grid-template-rows: auto 1fr auto; }
    .toolbar { display: grid; grid-template-columns: 1fr auto auto auto; gap: 10px; padding: 12px 14px; border-bottom: 1px solid var(--line); background: var(--surface); }
    .toolbar input, select, aside input, aside select { width: 100%; border: 1px solid var(--line); border-radius: 6px; padding: 8px 10px; background: #fff; color: var(--ink); }
    .button-row { display: flex; gap: 8px; flex-wrap: wrap; }
    button { border: 1px solid var(--line); border-radius: 6px; padding: 8px 10px; background: #fff; color: var(--ink); cursor: pointer; }
    button.active { border-color: var(--teal); color: #fff; background: var(--teal); }
    button:hover { border-color: var(--teal); }
    .panel { border: 1px solid var(--line); border-radius: 8px; background: #fff; margin-bottom: 12px; overflow: hidden; }
    .panel h2 { margin: 0; font-size: 14px; padding: 10px 12px; border-bottom: 1px solid var(--line); background: var(--surface-2); }
    .panel .body { padding: 10px 12px; }
    label { display: block; color: var(--muted); font-size: 12px; margin: 10px 0 4px; }
    .checkboxes { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 8px; font-size: 12px; }
    .checkboxes label { display: flex; align-items: center; gap: 6px; margin: 0; color: var(--ink); }
    .checkboxes input { width: auto; }
    canvas { width: 100%; height: 100%; display: block; }
    /* Background ONLY on the static fallback canvas. The cytoscape renderer
       stacks transparent overlay layers (drag z=2, selectbox z=3) ABOVE the
       node layer (z=1); giving every canvas an opaque background paints those
       overlays solid over the nodes, leaving the graph invisible. Keep the
       cytoscape canvases transparent; #cyGraph itself provides the backdrop. */
    #graphCanvas { background: #fbfcfa; }
    .canvas-wrap { height: calc(100vh - 176px); min-height: 520px; position: relative; }
    .graph-status { position: absolute; left: 12px; top: 12px; z-index: 2; border: 1px solid var(--line); border-radius: 6px; background: rgba(255,255,255,0.9); color: var(--muted); font-size: 12px; padding: 6px 8px; pointer-events: none; }
    #cyGraph { position: absolute; inset: 0; display: none; background: #fbfcfa; }
    #cyGraph.active { display: block; }
    #graphCanvas.hidden { display: none; }
    .legend { display: flex; gap: 10px; flex-wrap: wrap; padding: 8px 14px; border-top: 1px solid var(--line); background: var(--surface); font-size: 12px; color: var(--muted); }
    .dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; margin-right: 5px; vertical-align: -1px; }
    .list { max-height: 270px; overflow: auto; }
    .row { border-bottom: 1px solid var(--line); padding: 8px 0; cursor: pointer; }
    .row:last-child { border-bottom: 0; }
    .row:hover { color: var(--teal); }
    .row-title { font-weight: 650; font-size: 13px; overflow-wrap: anywhere; }
    .row-meta { color: var(--muted); font-size: 12px; margin-top: 2px; }
    .pill { display: inline-block; border-radius: 999px; border: 1px solid var(--line); padding: 2px 7px; margin: 2px 4px 2px 0; font-size: 11px; background: #fff; color: var(--muted); }
    .pill.hot { color: #fff; border-color: var(--teal); background: var(--teal); }
    .doc { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; white-space: pre-wrap; font-size: 12px; line-height: 1.45; background: #f3f5f2; border: 1px solid var(--line); border-radius: 6px; padding: 9px; overflow-wrap: anywhere; }
    .split { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .small { font-size: 12px; color: var(--muted); line-height: 1.4; }
    .route { border-left: 4px solid var(--teal); padding: 8px 10px; background: #eef8f5; margin-bottom: 8px; border-radius: 6px; }
    .warn { border-left-color: var(--amber); background: #fff8eb; }
    .bad { border-left-color: var(--red); background: #fff1f1; }
    table { width: 100%; border-collapse: collapse; font-size: 12px; }
    th, td { border-bottom: 1px solid var(--line); text-align: left; padding: 6px; vertical-align: top; }
    th { color: var(--muted); font-weight: 600; background: #f8faf8; }
    .benchmark-table { margin: 8px 0 10px; font-size: 11px; }
    .benchmark-table td.num { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
    .agent-launcher { position: fixed; right: 22px; bottom: 22px; z-index: 20; width: 62px; height: 62px; border-radius: 50%; border: 1px solid #0b5f59; background: var(--teal); color: #fff; display: grid; place-items: center; box-shadow: 0 14px 32px rgba(15, 118, 110, 0.28); font-weight: 750; }
    .agent-shell { position: fixed; right: 22px; bottom: 96px; z-index: 19; width: min(440px, calc(100vw - 28px)); max-height: min(700px, calc(100vh - 120px)); display: none; grid-template-rows: auto auto 1fr auto; border: 1px solid var(--line); border-radius: 8px; background: #fff; box-shadow: 0 20px 48px rgba(22, 22, 22, 0.18); overflow: hidden; }
    .agent-shell.open { display: grid; }
    .agent-head { padding: 12px 14px; border-bottom: 1px solid var(--line); background: #f7faf8; display: flex; justify-content: space-between; gap: 12px; align-items: center; }
    .agent-title { font-weight: 750; }
    .agent-subtitle { font-size: 12px; color: var(--muted); margin-top: 2px; }
    .agent-close { border: 0; background: transparent; padding: 4px 6px; font-size: 20px; line-height: 1; }
    .agent-prompts { padding: 10px 12px; border-bottom: 1px solid var(--line); display: flex; flex-wrap: wrap; gap: 7px; }
    .agent-prompts button { font-size: 12px; padding: 6px 8px; }
    .agent-log { overflow: auto; padding: 12px; background: #fbfcfa; }
    .agent-msg { margin-bottom: 10px; border-radius: 8px; padding: 9px 10px; line-height: 1.42; font-size: 13px; }
    .agent-msg.user { margin-left: 42px; background: #e8f5f2; border: 1px solid #c7e3dc; }
    .agent-msg.agent { margin-right: 18px; background: #fff; border: 1px solid var(--line); }
    .agent-answer-list { padding-left: 18px; margin: 6px 0; }
    .agent-cite { display: block; text-align: left; width: 100%; margin: 5px 0; padding: 7px 8px; border-color: #d1d8d5; background: #fff; }
    .agent-cite .row-title { font-size: 12px; }
    .agent-cite .row-meta { font-size: 11px; }
    .agent-form { display: grid; grid-template-columns: 1fr auto; gap: 8px; padding: 10px; border-top: 1px solid var(--line); background: #fff; }
    .agent-form input { width: 100%; border: 1px solid var(--line); border-radius: 6px; padding: 9px 10px; }
    .agent-note { color: var(--muted); font-size: 12px; }
    @media (max-width: 1160px) {
      main { grid-template-columns: 290px 1fr; }
      .inspector { grid-column: 1 / -1; border-left: 0; border-top: 1px solid var(--line); max-height: 420px; }
      header { grid-template-columns: 1fr; }
      .metrics { min-width: 0; }
    }
    @media (max-width: 760px) {
      main { grid-template-columns: 1fr; }
      aside { border-right: 0; border-bottom: 1px solid var(--line); max-height: 520px; }
      .toolbar { grid-template-columns: 1fr; }
      .metrics { grid-template-columns: repeat(2, 1fr); }
      h1 { font-size: 23px; }
      .agent-launcher { right: 14px; bottom: 14px; }
      .agent-shell { right: 14px; bottom: 86px; }
    }
  </style>
  <!-- Cytoscape inlined from vendor/cytoscape.min.js (pinned 3.31.0).
       Single-file deploy: no CDN, no network at runtime. -->
  <script>__CYTOSCAPE_INLINE__</script>
  <style>
    /* Fallback banner shown only when the inlined library somehow
       failed to define window.cytoscape (vendor corruption, sanitizer
       stripped the inline, file:// CSP override). The interactive graph
       is replaced by a static canvas drawing; everything else still
       works. */
    .graph-fallback-banner {
      display: none;
      background: #fff7ed; color: #7c2d12;
      border: 1px solid #fdba74;
      border-radius: 6px;
      padding: 10px 14px;
      margin: 12px 0;
      font-size: 13px;
    }
    .graph-fallback-banner code {
      background: #fed7aa; padding: 1px 4px; border-radius: 3px;
    }
    body.graph-fallback .graph-fallback-banner { display: block; }

    /* Mathematician's-view header section. Light theme matches the
       existing atlas palette; emphasis on disciplined KPIs over raw
       counts, with the honest non-claim called out at the top. */
    .proof-status {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 22px 26px;
      margin: 18px 0 26px;
    }
    .proof-status h2 {
      margin: 0 0 6px;
      font-size: 17px;
      letter-spacing: 0.02em;
      color: var(--ink);
    }
    .proof-status .sub {
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 14px;
    }
    .proof-status .non-claim {
      background: #fffbea;
      border-left: 3px solid #b45309;
      color: #4a2c08;
      padding: 12px 14px;
      border-radius: 0 6px 6px 0;
      margin: 0 0 18px;
      font-size: 13px;
      line-height: 1.55;
    }
    .proof-status .non-claim strong { color: #7c2d12; }
    .ps-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }
    .ps-card {
      background: var(--surface-2);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px 12px;
    }
    .ps-card .v {
      font-size: 22px; font-weight: 600; color: var(--ink);
      line-height: 1.2;
      font-variant-numeric: tabular-nums;
    }
    .ps-card .k {
      font-size: 11px; color: var(--muted);
      text-transform: uppercase; letter-spacing: 0.06em;
      margin-top: 4px;
    }
    .ps-card .c {
      font-size: 11px; color: var(--muted); margin-top: 5px;
      line-height: 1.4;
    }
    .ps-section { margin-top: 16px; }
    .ps-section h3 {
      font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em;
      color: var(--muted); margin: 0 0 8px;
    }
    .ps-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    .ps-table th, .ps-table td {
      padding: 6px 10px;
      text-align: left;
      border-bottom: 1px solid var(--line);
    }
    .ps-table th {
      font-weight: 600; color: var(--ink);
      background: var(--surface-2);
    }
    .ps-table td.num { text-align: right; font-variant-numeric: tabular-nums; }
    .ps-axes { display: flex; flex-direction: column; gap: 4px; }
    .ps-axis {
      display: grid;
      grid-template-columns: 200px 120px 1fr;
      gap: 12px;
      align-items: center;
      padding: 6px 0;
      border-bottom: 1px solid var(--line);
    }
    .ps-axis .name { font-weight: 500; color: var(--ink); font-size: 13px; }
    .ps-axis .bar {
      height: 6px; background: #e5e7eb; border-radius: 3px; position: relative;
    }
    .ps-axis .bar > span {
      display: block; height: 100%; border-radius: 3px;
      background: var(--teal);
    }
    .ps-axis .read { color: var(--muted); font-size: 12px; }
    .ps-source {
      font-size: 11px; color: var(--muted); margin-top: 12px;
    }
    .ps-source code { font-size: 11px; }
    .public-links {
      display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px;
    }
    .public-links a {
      color: var(--accent);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 5px 8px;
      text-decoration: none;
      background: #f8fafc;
      font-size: 12px;
      font-weight: 650;
    }
    .public-links a:hover { background: #eff6ff; }
  </style>
</head>
<body>
<div class="app">
  <header>
    <div>
      <h1>NS Lean Formalization Atlas</h1>
      <div class="sub">
        Interactive map of the Navier-Stokes formal corpus: declarations, dependencies,
        pressure/C7 residuals, graph disagreement, killed basins, and tick history.
        Scale is not a proof claim; use the graph to inspect what is formalized and
        where the current PDE frontier actually sits.
      </div>
      <nav class="public-links" aria-label="Public NS documentation">
        <a href="JOURNEY.md">Current status and journey</a>
        <a href="../workspace/ns_residual_manifest.md">Residual manifest</a>
      </nav>
    </div>
    <div class="metrics" id="metrics"></div>
  </header>
  <div class="graph-fallback-banner" role="status">
    <strong>Graph library unavailable.</strong>
    The interactive Cytoscape view did not initialize — a reduced static
    canvas view is shown instead. The inlined library
    (<code>vendor/cytoscape.min.js</code>) failed to define
    <code>window.cytoscape</code>. Run
    <code>scripts/ns_formalization_atlas.py</code> to regenerate, or
    check that the embedded <code>&lt;script&gt;</code> tag survived
    any post-processing.
  </div>

  <!-- Mathematician's view: disciplined KPIs at the top, the honest
       non-claim called out, the existing operator atlas below. -->
  <section class="proof-status" id="proofStatus">
    <h2>Proof status — disciplined view</h2>
    <div class="sub">Surfaces the KPIs the benchmark doc tracks, not raw declaration count. A mathematician should read this section before the graph atlas.</div>
    <div class="non-claim" id="psNonClaim"></div>
    <div class="ps-grid" id="psHeadlines"></div>
    <div class="ps-section">
      <h3>Status breakdown</h3>
      <table class="ps-table" id="psStatusTable">
        <thead><tr><th>Kind</th><th class="num">Count</th><th>What it means</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>
    <div class="ps-section">
      <h3>Trust footprint &amp; process ratios</h3>
      <table class="ps-table" id="psRatiosTable">
        <thead><tr><th>Metric</th><th class="num">Value</th><th>Read</th></tr></thead>
        <tbody></tbody>
      </table>
    </div>
    <div class="ps-section">
      <h3>Self-scored rubric (0–4)</h3>
      <div class="ps-axes" id="psAxes"></div>
    </div>
    <div class="ps-source" id="psSource"></div>
  </section>
  <main>
    <aside>
      <div class="panel">
        <h2>Traversal</h2>
        <div class="body">
          <label for="viewMode">View</label>
          <select id="viewMode">
            <option value="theorems">Theorems / lemmas</option>
            <option value="frontier">Frontier obligations</option>
            <option value="pressure">Pressure / C7 lane</option>
            <option value="radius">Radius-charge basin</option>
            <option value="guardrails">Killed basins / guardrails</option>
            <option value="files">File architecture</option>
            <option value="search">Search results</option>
          </select>
          <label for="query">Search declarations, tags, docs</label>
          <input id="query" placeholder="pressure carrier, C7, radius, CF..." />
          <div class="split">
            <div>
              <label for="depth">Neighborhood depth</label>
              <select id="depth">
                <option value="1">1 hop</option>
                <option value="2">2 hops</option>
              </select>
            </div>
            <div>
              <label for="maxNodes">Max nodes</label>
              <select id="maxNodes">
                <option value="80">80</option>
                <option value="130" selected>130</option>
                <option value="220">220</option>
              </select>
            </div>
          </div>
          <label>Status filter</label>
          <div class="checkboxes" id="statusFilters"></div>
          <label>Tag contains</label>
          <input id="tagFilter" placeholder="receipt, falsifier, pricing..." />
        </div>
      </div>
      <div class="panel">
        <h2>Graph Recommendations</h2>
        <div class="body list" id="recommendations"></div>
      </div>
      <div class="panel">
        <h2>Tick Timeline</h2>
        <div class="body list" id="timeline"></div>
      </div>
    </aside>
    <section class="stage">
      <div class="toolbar">
        <input id="quickFocus" placeholder="Focus exact declaration..." />
        <button id="focusBtn">Focus</button>
        <button id="fitBtn">Fit</button>
        <button id="resetBtn">Reset</button>
      </div>
      <div class="canvas-wrap"><div class="graph-status" id="graphStatus">Building graph...</div><div id="cyGraph"></div><canvas id="graphCanvas"></canvas></div>
      <div class="legend">
        <span><i class="dot" style="background:var(--teal)"></i>open/frontier</span>
        <span><i class="dot" style="background:var(--indigo)"></i>receipt/interface</span>
        <span><i class="dot" style="background:var(--green)"></i>closed theorem</span>
        <span><i class="dot" style="background:var(--amber)"></i>falsifier/boundary</span>
        <span><i class="dot" style="background:var(--red)"></i>guardrail</span>
      </div>
    </section>
    <section class="inspector">
      <div class="panel">
        <h2>Selected Declaration</h2>
        <div class="body" id="inspector"></div>
      </div>
      <div class="panel">
        <h2>Search / Neighborhood</h2>
        <div class="body list" id="results"></div>
      </div>
      <div class="panel">
        <h2>Corpus Notes</h2>
        <div class="body small" id="notes"></div>
      </div>
    </section>
  </main>
  <button class="agent-launcher" id="agentLauncher" title="Ask the atlas">Ask</button>
  <section class="agent-shell" id="agentShell" aria-label="Atlas research agent">
    <div class="agent-head">
      <div>
        <div class="agent-title">Atlas Research Agent</div>
        <div class="agent-subtitle">Answers from the embedded Lean graph and audit snapshot.</div>
      </div>
      <button class="agent-close" id="agentClose" aria-label="Close">×</button>
    </div>
    <div class="agent-prompts" id="agentPrompts"></div>
    <div class="agent-log" id="agentLog"></div>
    <form class="agent-form" id="agentForm">
      <input id="agentInput" autocomplete="off" placeholder="Ask about theorems, assumptions, pressure/C7, open gaps..." />
      <button type="submit">Ask</button>
    </form>
  </section>
</div>
<script>
const DATA = __DATA__;

const nodes = DATA.nodes;
const files = DATA.files;
const byId = new Map(nodes.map((n, i) => [n.id, i]));
const byName = new Map();
nodes.forEach((n, i) => {
  if (!byName.has(n.name)) byName.set(n.name, []);
  byName.get(n.name).push(i);
});
const reverse = nodes.map(() => []);
nodes.forEach((n, i) => (n.uses || []).forEach(j => reverse[j]?.push(i)));
let cy = null;

function graphLibraryReady() {
  const ok = typeof window.cytoscape === "function";
  if (!ok && !document.body.classList.contains("graph-fallback")) {
    document.body.classList.add("graph-fallback");
    console.warn(
      "ns-atlas: window.cytoscape is undefined — the inlined " +
      "vendor/cytoscape.min.js did not register. Falling back to " +
      "static canvas. Regenerate via ns_formalization_atlas.py."
    );
  }
  return ok;
}

const statusColor = (n) => {
  const text = `${n.status} ${n.name} ${(n.tags || []).join(" ")}`.toLowerCase();
  if (text.includes("cf") || text.includes("decoherence")) return "#b91c1c";
  if (text.includes("falsifier") || text.includes("boundary")) return "#b45309";
  if (text.includes("open")) return "#0f766e";
  if (text.includes("receipt") || text.includes("interface")) return "#4338ca";
  if (text.includes("closed")) return "#15803d";
  return "#475569";
};

const state = {
  view: "theorems",
  query: "",
  tag: "",
  depth: 1,
  maxNodes: 130,
  statuses: new Set(),
  selected: null,
  graphNodes: [],
  graphEdges: [],
  positions: new Map(),
  dragging: null,
};

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c]));
}

function includesAny(text, terms) {
  text = text.toLowerCase();
  return terms.some(t => text.includes(t));
}

function nodeText(n) {
  return `${n.name} ${n.file} ${n.kind} ${n.status} ${(n.tags||[]).join(" ")} ${n.doc}`.toLowerCase();
}

function statusPass(n) {
  if (!state.statuses.size) return true;
  return state.statuses.has(n.status || "unknown");
}

function tagPass(n) {
  if (!state.tag.trim()) return true;
  return (n.tags || []).some(t => t.toLowerCase().includes(state.tag.toLowerCase()));
}

function searchNodeIndexes(q, limit = 220) {
  const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
  if (!terms.length) return [];
  return nodes.map((n, i) => {
    const text = nodeText(n);
    let score = 0;
    for (const term of terms) {
      if (String(n.name).toLowerCase() === term) score += 10;
      if (String(n.name).toLowerCase().includes(term)) score += 4;
      if ((n.tags || []).join(" ").toLowerCase().includes(term)) score += 3;
      if (text.includes(term)) score += 1;
    }
    score += Math.min(n.used_by_count || 0, 50) / 25;
    return { i, score };
  }).filter(r => r.score > 0 && statusPass(nodes[r.i]) && tagPass(nodes[r.i]))
    .sort((a, b) => b.score - a.score || nodes[a.i].name.localeCompare(nodes[b.i].name))
    .slice(0, limit)
    .map(r => r.i);
}

function seedIndexesForView() {
  const max = state.maxNodes;
  if (state.query.trim()) return searchNodeIndexes(state.query, max);
  const pick = (pred, limit = max) => nodes.map((n, i) => ({ n, i }))
    .filter(({n}) => pred(n) && statusPass(n) && tagPass(n))
    .sort((a, b) => (b.n.used_by_count || 0) - (a.n.used_by_count || 0) || a.n.name.localeCompare(b.n.name))
    .slice(0, limit)
    .map(r => r.i);
  if (state.view === "theorems") return pick(n => n.kind === "theorem" || /lemma|theorem|criterion|corollary|bridge/i.test(n.name));
  if (state.view === "frontier") return pick(n => /open|falsifier|boundary|obligation/i.test(`${n.status} ${n.name} ${(n.tags||[]).join(" ")}`));
  if (state.view === "pressure") return pick(n => includesAny(nodeText(n), ["pressure", "fresh", "invoice", "carrier", "dual", "punctured", "c7", "carleson", "radius"]));
  if (state.view === "radius") return pick(n => includesAny(nodeText(n), ["radiuscharging", "radius charge", "badscale", "same tree", "invoice", "eventtoradius"]));
  if (state.view === "guardrails") return pick(n => includesAny(nodeText(n), ["cf", "constantin", "decoherence", "selftax", "strict", "parabolic", "endpoint", "falsifier"]));
  if (state.view === "files") {
    return files.slice(0, max).flatMap(f => nodes.map((n, i) => n.file === f.name ? i : -1).filter(i => i >= 0).slice(0, 3));
  }
  return pick(() => true);
}

function expandNeighborhood(seeds) {
  const max = state.maxNodes;
  const keep = new Set(seeds.slice(0, max));
  let frontier = new Set(seeds.slice(0, Math.min(seeds.length, 40)));
  for (let d = 0; d < state.depth; d++) {
    const next = new Set();
    for (const i of frontier) {
      for (const j of (nodes[i].uses || []).slice(0, 20)) if (keep.size < max) { keep.add(j); next.add(j); }
      for (const j of (reverse[i] || []).slice(0, 24)) if (keep.size < max) { keep.add(j); next.add(j); }
    }
    frontier = next;
  }
  return Array.from(keep);
}

function buildGraph() {
  const seeds = seedIndexesForView();
  const ids = expandNeighborhood(seeds);
  const idSet = new Set(ids);
  const edges = [];
  for (const i of ids) {
    for (const j of nodes[i].uses || []) {
      if (idSet.has(j)) edges.push([i, j]);
    }
  }
  state.graphNodes = ids;
  state.graphEdges = edges.slice(0, 900);
  const graphStatus = document.getElementById("graphStatus");
  if (graphStatus) graphStatus.textContent = `${ids.length.toLocaleString()} nodes · ${state.graphEdges.length.toLocaleString()} edges · ${state.view}`;
  if (graphLibraryReady()) {
    renderCytoscape();
  } else {
    initPositions();
  }
  renderResults(seeds);
  draw();
}

function renderCytoscape() {
  const container = document.getElementById("cyGraph");
  const canvas = document.getElementById("graphCanvas");
  container.classList.add("active");
  canvas.classList.add("hidden");
  // The container just went from display:none → block. The browser
  // has not laid it out yet; container.clientWidth/Height are still 0
  // at this exact instant, which makes cytoscape mount into a 0×0 box
  // and never recover unless something nudges it. Force a layout pass
  // before measuring by reading offsetHeight (a documented trick that
  // triggers a reflow), then drive cytoscape's resize/fit after the
  // next animation frame regardless. Belt-and-suspenders against the
  // container-size race.
  // eslint-disable-next-line no-unused-expressions
  container.offsetHeight;
  const elements = [
    ...state.graphNodes.map(i => {
      const n = nodes[i];
      return {
        group: "nodes",
        data: {
          id: String(i),
          label: n.name,
          color: statusColor(n),
          size: Math.min(38, 16 + Math.sqrt(n.used_by_count || 0) * 3),
          status: n.status,
          kind: n.kind,
        },
      };
    }),
    ...state.graphEdges.map(([a, b], k) => ({
      group: "edges",
      data: { id: `e-${a}-${b}-${k}`, source: String(a), target: String(b) },
    })),
  ];
  if (!cy) {
    cy = window.cytoscape({
      container,
      wheelSensitivity: 0.18,
      minZoom: 0.12,
      maxZoom: 3.4,
      style: [
        { selector: "node", style: {
          "background-color": "data(color)",
          "width": "data(size)",
          "height": "data(size)",
          "label": "data(label)",
          "font-size": 10,
          "text-valign": "center",
          "text-halign": "right",
          "text-margin-x": 8,
          "text-background-color": "#fbfcfa",
          "text-background-opacity": 0.74,
          "text-background-padding": 2,
          "color": "#161616",
        }},
        { selector: "edge", style: {
          "width": 1,
          "line-color": "rgba(70, 80, 78, 0.18)",
          "target-arrow-color": "rgba(70, 80, 78, 0.18)",
          "target-arrow-shape": "triangle",
          "curve-style": "bezier",
        }},
        { selector: ".selected", style: {
          "border-width": 4,
          "border-color": "#161616",
          "z-index": 10,
        }},
        { selector: ".faded", style: {
          "opacity": 0.24,
          "text-opacity": 0.18,
        }},
      ],
      elements,
    });
    cy.on("tap", "node", event => selectNode(Number(event.target.id())));
  } else {
    cy.elements().remove();
    cy.add(elements);
  }
  const layout = cy.layout({
    name: "cose",
    animate: false,
    randomize: true,
    fit: true,
    padding: 32,
    nodeRepulsion: 7200,
    idealEdgeLength: 110,
    edgeElasticity: 0.22,
    nestingFactor: 1.2,
    numIter: 900,
  });
  layout.run();
  markCytoscapeSelection();
  // After the first animation frame, the container has its real size
  // and cytoscape can be told to re-measure + re-fit. Without this,
  // an initial 0-size mount stays blank even after the container
  // becomes visible.
  if (typeof requestAnimationFrame === "function") {
    requestAnimationFrame(() => {
      try { cy.resize(); cy.fit(undefined, 32); } catch (_) {}
    });
  }
}

function markCytoscapeSelection() {
  if (!cy) return;
  cy.elements().removeClass("selected faded");
  if (state.selected === null) return;
  const selected = cy.getElementById(String(state.selected));
  if (!selected.length) return;
  const neighbors = selected.closedNeighborhood();
  cy.elements().not(neighbors).addClass("faded");
  selected.addClass("selected");
}

function initPositions() {
  const canvas = document.getElementById("graphCanvas");
  const w = canvas.clientWidth || 900, h = canvas.clientHeight || 600;
  const count = Math.max(state.graphNodes.length, 1);
  state.graphNodes.forEach((id, k) => {
    if (state.positions.has(id)) return;
    const a = (Math.PI * 2 * k) / count;
    const r = Math.min(w, h) * (0.25 + 0.22 * ((k % 7) / 7));
    state.positions.set(id, { x: w/2 + Math.cos(a) * r, y: h/2 + Math.sin(a) * r, vx: 0, vy: 0 });
  });
  for (let i = 0; i < 80; i++) tickLayout();
}

function tickLayout() {
  const canvas = document.getElementById("graphCanvas");
  const w = canvas.clientWidth || 900, h = canvas.clientHeight || 600;
  const ids = state.graphNodes;
  for (let a = 0; a < ids.length; a++) {
    const pa = state.positions.get(ids[a]);
    pa.vx += (w / 2 - pa.x) * 0.0009;
    pa.vy += (h / 2 - pa.y) * 0.0009;
    for (let b = a + 1; b < ids.length; b++) {
      const pb = state.positions.get(ids[b]);
      let dx = pa.x - pb.x, dy = pa.y - pb.y;
      let dist2 = dx*dx + dy*dy + 0.01;
      if (dist2 > 62000) continue;
      const f = Math.min(280 / dist2, 0.09);
      pa.vx += dx * f; pa.vy += dy * f;
      pb.vx -= dx * f; pb.vy -= dy * f;
    }
  }
  for (const [a, b] of state.graphEdges) {
    const pa = state.positions.get(a), pb = state.positions.get(b);
    if (!pa || !pb) continue;
    const dx = pb.x - pa.x, dy = pb.y - pa.y;
    const dist = Math.hypot(dx, dy) || 1;
    const f = (dist - 110) * 0.006;
    pa.vx += dx / dist * f; pa.vy += dy / dist * f;
    pb.vx -= dx / dist * f; pb.vy -= dy / dist * f;
  }
  for (const id of ids) {
    const p = state.positions.get(id);
    p.vx *= 0.82; p.vy *= 0.82;
    p.x = Math.max(18, Math.min(w - 18, p.x + p.vx));
    p.y = Math.max(18, Math.min(h - 18, p.y + p.vy));
  }
}

function draw() {
  if (graphLibraryReady()) {
    markCytoscapeSelection();
    return;
  }
  const canvas = document.getElementById("graphCanvas");
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.max(1, Math.floor(rect.width * dpr));
  canvas.height = Math.max(1, Math.floor(rect.height * dpr));
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, rect.width, rect.height);
  ctx.lineWidth = 1;
  ctx.strokeStyle = "rgba(70, 80, 78, 0.18)";
  for (const [a, b] of state.graphEdges) {
    const pa = state.positions.get(a), pb = state.positions.get(b);
    if (!pa || !pb) continue;
    ctx.beginPath(); ctx.moveTo(pa.x, pa.y); ctx.lineTo(pb.x, pb.y); ctx.stroke();
  }
  const selected = state.selected;
  const labelBudget = state.graphNodes.length < 120 ? 70 : 36;
  const sorted = state.graphNodes.slice().sort((a, b) => (nodes[b].used_by_count || 0) - (nodes[a].used_by_count || 0));
  const labelSet = new Set(sorted.slice(0, labelBudget));
  for (const id of state.graphNodes) {
    const n = nodes[id], p = state.positions.get(id);
    const radius = Math.min(13, 5 + Math.sqrt(n.used_by_count || 0));
    ctx.beginPath();
    ctx.fillStyle = statusColor(n);
    ctx.globalAlpha = selected === null || selected === id ? 1 : 0.72;
    ctx.arc(p.x, p.y, selected === id ? radius + 4 : radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;
    if (selected === id) { ctx.lineWidth = 3; ctx.strokeStyle = "#161616"; ctx.stroke(); ctx.lineWidth = 1; }
    if (labelSet.has(id) || selected === id) {
      ctx.fillStyle = "#161616";
      ctx.font = selected === id ? "650 12px system-ui" : "12px system-ui";
      ctx.fillText(n.name.slice(0, 42), p.x + radius + 5, p.y + 4);
    }
  }
}

function animate() {
  if (!graphLibraryReady()) {
    tickLayout();
    draw();
  }
  requestAnimationFrame(animate);
}

function renderMetrics() {
  const s = DATA.summary;
  document.getElementById("metrics").innerHTML = [
    ["Declarations", s.decls], ["Files", s.files], ["Decl edges", s.edges], ["Quantities", s.quantities]
  ].map(([k, v]) => `<div class="metric"><strong>${v.toLocaleString()}</strong><span>${k}</span></div>`).join("");
}

function renderProofStatus() {
  const k = DATA.proof_status_kpis;
  if (!k) return;
  const fmt = v => (v === null || v === undefined) ? "—"
    : (typeof v === "number" ? v.toLocaleString(undefined, {maximumFractionDigits: 3}) : String(v));

  document.getElementById("psNonClaim").innerHTML =
    `<strong>Honest non-claim:</strong> ${esc(k.non_claim)}`;

  // Headline KPI cards: the numbers a mathematician should read first.
  const t = k.totals || {};
  const tf = k.trust_footprint || {};
  const headlines = [
    {v: fmt(t.graph_declarations), key: "Graph declarations",
     c: "Volume only — not a proof-status metric."},
    {v: fmt(t.distinct_research_avenues_est), key: "Distinct research avenues (est.)",
     c: `Duplication factor ≈ ${fmt(t.duplication_factor_est)}× by structural fingerprint. The honest divisor.`},
    {v: fmt(tf.axiom), key: "Axiom declarations",
     c: "Each row is an assumed lemma. Lower is better; 0 is the clean target."},
    {v: fmt(tf.opaque), key: "Opaque declarations",
     c: "Hidden proof bodies. Heavy trust footprint."},
    {v: fmt(tf.sorry), key: "Sorry occurrences",
     c: "Each is a deferred proof obligation. 0 is the clean target."},
    {v: fmt(tf.debt_share != null ? (tf.debt_share * 100).toFixed(1) + "%" : null),
     key: "Trust-debt share",
     c: "axiom + opaque + sorry as a share of all declarations."},
  ];
  document.getElementById("psHeadlines").innerHTML = headlines.map(h =>
    `<div class="ps-card"><div class="v">${esc(h.v)}</div><div class="k">${esc(h.key)}</div><div class="c">${esc(h.c)}</div></div>`
  ).join("");

  // Status breakdown table
  const sb = k.status_breakdown || {};
  const statusRows = [
    ["closed_theorem", "Closed theorems — proved in this corpus (may still depend on local axioms/opaques)."],
    ["exclusion_theorem", "Exclusion theorems — formally rule out a route under stated hypotheses. The corpus's strongest axis."],
    ["receipt_interface", "Receipt interfaces — typed proof-currency carriers. Count only when proof-carrying fields are filled."],
    ["open_obligation", "Open obligations — explicitly named proof debt."],
    ["falsifier_surface", "Falsifier surfaces — what would kill a route if instantiated."],
    ["untyped_declaration", "Untyped declarations — defs/instances not yet classified as theorem/obligation/receipt."],
    ["unclosed_proof_gap", "Unclosed proof gaps — explicitly named missing receipts."],
  ];
  document.getElementById("psStatusTable").querySelector("tbody").innerHTML =
    statusRows.filter(([key]) => sb[key] !== undefined && sb[key] > 0)
      .map(([key, read]) =>
        `<tr><td><code>${esc(key)}</code></td><td class="num">${fmt(sb[key])}</td><td>${esc(read)}</td></tr>`)
      .join("");

  // Trust + process ratios
  const pr = k.process_ratios || {};
  const ratioRows = [
    ["exclusion_to_receipt", pr.exclusion_to_receipt,
     "How many demotions per receipt. Higher = stronger anti-tautology discipline."],
    ["closed_or_exclusion_share", pr.closed_or_exclusion_share,
     "Share of declarations that are closed-positive or closed-negative surfaces."],
    ["open_obligation_share", pr.open_obligation_share,
     "Share of declarations that are live proof debt."],
    ["falsifier_to_closed", pr.falsifier_to_closed,
     "Falsifiers per closed theorem. Bounds the 'all positives, no negatives' failure mode."],
  ];
  document.getElementById("psRatiosTable").querySelector("tbody").innerHTML =
    ratioRows.filter(([_k, v]) => v !== null && v !== undefined).map(([key, v, read]) =>
      `<tr><td><code>${esc(key)}</code></td><td class="num">${fmt(v)}</td><td>${esc(read)}</td></tr>`
    ).join("");

  // Self-scored rubric
  const axes = k.axes || [];
  document.getElementById("psAxes").innerHTML = axes.map(a => {
    const pct = a.max ? Math.round((a.self_score / a.max) * 100) : 0;
    return `<div class="ps-axis">
      <div class="name">${esc(a.axis)} <span style="color:var(--muted);font-weight:400;">${a.self_score}/${a.max}</span></div>
      <div class="bar"><span style="width:${pct}%"></span></div>
      <div class="read">${esc(a.read)}</div>
    </div>`;
  }).join("");

  document.getElementById("psSource").innerHTML =
    `Source measurement: <code>${esc(k.source_md || "")}</code> · ` +
    `KPI definitions mirror the same doc · self-scores are internal planning signals, not public rankings.`;
}

function renderStatusFilters() {
  const statuses = Object.keys(DATA.summary.status_counts).sort();
  document.getElementById("statusFilters").innerHTML = statuses.map(st => (
    `<label><input type="checkbox" value="${esc(st)}"> ${esc(st || "unknown")}</label>`
  )).join("");
  document.querySelectorAll("#statusFilters input").forEach(input => input.addEventListener("change", () => {
    state.statuses = new Set(Array.from(document.querySelectorAll("#statusFilters input:checked")).map(x => x.value));
    buildGraph();
  }));
}

function renderRecommendations() {
  const rows = DATA.maze.recommendations || [];
  document.getElementById("recommendations").innerHTML = rows.map(r => {
    const cls = r.recommendation === "old_basin_guard" ? "route bad" : r.recommendation.includes("consensus") ? "route warn" : "route";
    return `<div class="${cls}" data-name="${esc(r.name)}"><div class="row-title">${esc(r.name)}</div><div class="row-meta">${esc(r.recommendation)} · ${Number(r.route_score || 0).toFixed(2)}</div><div class="small">${esc(r.next_action)}</div></div>`;
  }).join("") || "<div class='small'>No recommendation rows.</div>";
  document.querySelectorAll("#recommendations [data-name]").forEach(el => el.addEventListener("click", () => focusName(el.dataset.name)));
}

function renderTimeline() {
  const rows = DATA.timeline.slice().reverse();
  document.getElementById("timeline").innerHTML = rows.slice(0, 36).map(r => (
    `<div class="row"><div class="row-title">${esc(r.heading)}</div><div class="row-meta">${esc(r.source)}</div><div class="small">${esc(r.excerpt)}</div></div>`
  )).join("");
}

function renderResults(seedIds = []) {
  const ids = seedIds.length ? seedIds.slice(0, 80) : state.graphNodes.slice(0, 80);
  document.getElementById("results").innerHTML = ids.map(i => {
    const n = nodes[i];
    return `<div class="row" data-i="${i}"><div class="row-title">${esc(n.name)}</div><div class="row-meta">${esc(n.kind)} · ${esc(n.status)} · used by ${n.used_by_count}</div></div>`;
  }).join("") || "<div class='small'>No matching declarations.</div>";
  document.querySelectorAll("#results [data-i]").forEach(el => el.addEventListener("click", () => selectNode(Number(el.dataset.i))));
}

function renderInspector() {
  const box = document.getElementById("inspector");
  if (state.selected === null) {
    box.innerHTML = "<div class='small'>Click a node or search result to inspect dependencies, users, tags, and source location.</div>";
    return;
  }
  const n = nodes[state.selected];
  const deps = (n.uses || []).slice(0, 12).map(i => `<div class="row" data-i="${i}"><div class="row-title">${esc(nodes[i].name)}</div><div class="row-meta">${esc(nodes[i].status)} · ${esc(nodes[i].kind)}</div></div>`).join("");
  const users = (reverse[state.selected] || []).slice(0, 12).map(i => `<div class="row" data-i="${i}"><div class="row-title">${esc(nodes[i].name)}</div><div class="row-meta">${esc(nodes[i].status)} · ${esc(nodes[i].kind)}</div></div>`).join("");
  box.innerHTML = `
    <div class="row-title">${esc(n.name)}</div>
    <div class="row-meta">${esc(n.kind)} · ${esc(n.status)} · ${esc(n.path)}:${esc(n.line ?? "")}</div>
    <div>${(n.tags || []).map(t => `<span class="pill">${esc(t)}</span>`).join("")}</div>
    <p class="doc">${esc(n.doc || "No doc excerpt captured.")}</p>
    <div class="split">
      <div><h3>Depends On</h3>${deps || "<div class='small'>No captured deps.</div>"}</div>
      <div><h3>Used By</h3>${users || "<div class='small'>No captured users.</div>"}</div>
    </div>`;
  box.querySelectorAll("[data-i]").forEach(el => el.addEventListener("click", () => selectNode(Number(el.dataset.i))));
}

function renderNotes() {
  const s = DATA.summary;
  const topTags = (s.top_tags || []).slice(0, 10).map(([t, c]) => `<span class="pill">${esc(t)} ${c}</span>`).join("");
  const integrity = DATA.maze.integrity || {};
  const rag = DATA.rag || {};
  const ragLine = rag.available
    ? `Gemini embedding artifact: ${Number(rag.entries || 0).toLocaleString()} selected declarations from ${Number(rag.corpus_entries || 0).toLocaleString()} corpus rows, ${esc(rag.model)} at ${esc(rag.dimensions)} dims. Corpus hash ${esc(String(rag.corpus_sha256 || "").slice(0, 12))}; vector hash ${esc(String(rag.embedding_sha256 || "").slice(0, 12))}.`
    : `No Gemini embedding artifact is bundled yet; the floating atlas agent is using local lexical graph retrieval.`;
  document.getElementById("notes").innerHTML = `
    <p><strong>Scope.</strong> This atlas maps the local Lean corpus and route diagnostics. It is not a millennium-problem result.</p>
    <p><strong>Proof status.</strong> The public surface shows the local graph and audit snapshot only.</p>
    <p><strong>Top tags.</strong><br>${topTags}</p>
    <p><strong>Lean RAG.</strong> ${ragLine}</p>
    <p><strong>Graph integrity.</strong> ${esc(integrity.ok ? "ok" : "warnings present")} ${(integrity.observations || []).map(esc).join("; ")}</p>
    <p><strong>Generated.</strong> ${esc(DATA.generated_at)}</p>
  `;
}

function selectNode(i) {
  state.selected = i;
  if (!state.graphNodes.includes(i)) {
    state.query = nodes[i].name;
    document.getElementById("query").value = state.query;
    state.view = "search";
    document.getElementById("viewMode").value = "search";
    buildGraph();
  }
  renderInspector();
  markCytoscapeSelection();
  draw();
}

function focusName(name) {
  const ids = byName.get(name) || searchNodeIndexes(name, 1);
  if (ids.length) selectNode(ids[0]);
}

function fitGraph() {
  if (cy) {
    cy.fit(undefined, 32);
    return;
  }
  state.positions.clear();
  initPositions();
  draw();
}

const AGENT_PROMPTS = [
  "What should I inspect first?",
  "Show central theorems and lemmas",
  "What are the open gaps?",
  "Audit axioms and sorrys",
  "Explain the pressure/C7 frontier",
  "Is this a Clay proof?"
];

function topNodeIndexes(pred, limit = 8) {
  return nodes.map((n, i) => ({ n, i }))
    .filter(({n}) => pred(n))
    .sort((a, b) => (b.n.used_by_count || 0) - (a.n.used_by_count || 0) || a.n.name.localeCompare(b.n.name))
    .slice(0, limit)
    .map(row => row.i);
}

function nodeCitations(ids) {
  if (!ids.length) return "<div class='agent-note'>No matching declarations in the embedded graph.</div>";
  return ids.map(i => {
    const n = nodes[i];
    return `<button class="agent-cite" data-agent-i="${i}"><span class="row-title">${esc(n.name)}</span><span class="row-meta">${esc(n.kind)} · ${esc(n.status)} · ${esc(n.path)}:${esc(n.line ?? "")}</span></button>`;
  }).join("");
}

function setLens(view, query = "") {
  state.view = view;
  state.query = query;
  const viewEl = document.getElementById("viewMode");
  if (viewEl) viewEl.value = view;
  const queryEl = document.getElementById("query");
  if (queryEl) queryEl.value = query;
  buildGraph();
}

function auditHtml() {
  const audit = DATA.audit || {};
  const counts = audit.counts || {};
  const topAxioms = (audit.top_axiom_files || []).slice(0, 5)
    .map(row => `<li>${esc(row.file)}: ${esc(row.count)} axioms</li>`).join("");
  const sorrys = (audit.sorry_locs || []).slice(0, 8)
    .map(row => `<li>${esc(row.file)}:${esc(row.line)}</li>`).join("");
  return `
    <p><strong>Audit snapshot.</strong> Comment/string-stripped scan of ${esc(audit.files || 0)} NS Lean files and ${Number(audit.lines || 0).toLocaleString()} lines.</p>
    <ul class="agent-answer-list">
      <li>${esc(counts.axiom || 0)} explicit <code>axiom</code> declarations</li>
      <li>${esc(counts.opaque || 0)} explicit <code>opaque</code> declarations</li>
      <li>${esc(audit.sorry || 0)} executable <code>sorry</code> tokens</li>
      <li>${esc(audit.admit || 0)} executable <code>admit</code> tokens</li>
      <li>${esc(counts.unsafe || 0)} <code>unsafe</code> and ${esc(counts.partial || 0)} <code>partial</code> declarations</li>
    </ul>
    <p><strong>Top axiom files.</strong></p>
    <ul class="agent-answer-list">${topAxioms}</ul>
    <p><strong>First sorry locations.</strong></p>
    <ul class="agent-answer-list">${sorrys || "<li>None found.</li>"}</ul>
    <p class="agent-note">This is a formal-footprint audit, not an endorsement of the mathematical assumptions.</p>
  `;
}

function agentAnswer(question) {
  const q = question.toLowerCase();
  if (/axiom|sorry|audit|unsafe|opaque|assumption/.test(q)) {
    setLens("guardrails", "");
    return auditHtml();
  }
  if (/clay|proof|proved|solution|millennium|best|world/.test(q)) {
    const ids = topNodeIndexes(n => /GlobalSmooth|Clay|BKM|ESS|Constantin|Fefferman|smoothness/i.test(n.name + " " + n.doc), 6);
    return `
      <p><strong>Status.</strong> The atlas shows a large, specialized NS formalization corpus. It does not show a millennium-problem proof. The safe comparative claim is scale and specialization, while a ranking claim needs external audit of assumptions, theorem depth, Mathlib integration, and executable gaps.</p>
      <p><strong>Relevant declarations.</strong></p>
      ${nodeCitations(ids)}
    `;
  }
  if (/theorem|lemma|criterion|corollary|statement|formalized/.test(q)) {
    setLens("theorems", "");
    const ids = topNodeIndexes(n => n.kind === "theorem" && /closed|exclusion|receipt|declaration/.test(n.status), 9);
    return `
      <p><strong>Theorem lens.</strong> Mathematicians usually want the statement, hypotheses, dependencies, and users. These central theorem nodes are good entry points because other declarations point at them.</p>
      ${nodeCitations(ids)}
    `;
  }
  if (/gap|open|frontier|obligation|residual|next/.test(q)) {
    setLens("frontier", "");
    const ids = topNodeIndexes(n => /open_obligation|unclosed_proof_gap|falsifier_surface/.test(n.status), 9);
    return `
      <p><strong>Open frontier.</strong> These are not solved theorem endpoints. They are the places where the formal architecture says a PDE estimate, bridge, or obstruction remains to be supplied.</p>
      ${nodeCitations(ids)}
    `;
  }
  if (/pressure|c7|carrier|fresh|punctured|carleson|invoice/.test(q)) {
    setLens("pressure", "");
    const ids = topNodeIndexes(n => includesAny(nodeText(n), ["pressure", "c7", "carrier", "fresh", "punctured", "carleson", "invoice"]), 9);
    const recs = (DATA.maze.recommendations || []).slice(0, 4)
      .map(r => `<li><strong>${esc(r.name)}</strong>: ${esc(r.next_action || r.recommendation)}</li>`).join("");
    return `
      <p><strong>Pressure/C7 frontier.</strong> The current useful question is whether pressure-carrier localization can be charged to the residual fresh region, or whether harmonic/inherited pressure escapes the invoice.</p>
      <ul class="agent-answer-list">${recs}</ul>
      ${nodeCitations(ids)}
    `;
  }
  if (/start|first|inspect|read|overview|guide/.test(q)) {
    setLens("theorems", "");
    const ids = topNodeIndexes(n => n.kind === "theorem" && n.status === "closed_theorem", 5)
      .concat(topNodeIndexes(n => /open_obligation|unclosed_proof_gap/.test(n.status), 4));
    return `
      <p><strong>Start here.</strong> Use three passes: first inspect central theorem nodes, then the explicit audit footprint, then the frontier obligations. That sequence separates formal scale from unsolved analytic content.</p>
      <ul class="agent-answer-list">
        <li>Use the Theorems / lemmas lens for established formal objects.</li>
        <li>Ask for the axiom/sorry audit before trusting any closure phrase.</li>
        <li>Use the Pressure / C7 lens for the current research lane.</li>
      </ul>
      ${nodeCitations(ids.slice(0, 9))}
    `;
  }
  const ids = searchNodeIndexes(question, 8);
  setLens("search", question);
  return `
    <p><strong>Search result.</strong> I matched your question against declaration names, docs, tags, and file names. Click any citation to jump the graph and inspect dependencies.</p>
    ${nodeCitations(ids)}
  `;
}

function appendAgentMessage(role, html) {
  const log = document.getElementById("agentLog");
  const item = document.createElement("div");
  item.className = `agent-msg ${role}`;
  item.innerHTML = html;
  log.appendChild(item);
  log.scrollTop = log.scrollHeight;
}

function askAgent(text) {
  const question = String(text || "").trim();
  if (!question) return;
  appendAgentMessage("user", esc(question));
  appendAgentMessage("agent", agentAnswer(question));
}

function initAgent() {
  document.getElementById("agentPrompts").innerHTML = AGENT_PROMPTS
    .map(prompt => `<button type="button" data-agent-prompt="${esc(prompt)}">${esc(prompt)}</button>`)
    .join("");
  appendAgentMessage("agent", "<p><strong>Ask me to find theorem statements, assumptions, proof gaps, pressure/C7 objects, or a compact audit of the corpus.</strong></p><p class='agent-note'>This version answers locally from the embedded atlas data, so it can run safely as a static Vercel page.</p>");
  document.getElementById("agentLauncher").addEventListener("click", () => document.getElementById("agentShell").classList.toggle("open"));
  document.getElementById("agentClose").addEventListener("click", () => document.getElementById("agentShell").classList.remove("open"));
  document.getElementById("agentPrompts").addEventListener("click", e => {
    const btn = e.target.closest("[data-agent-prompt]");
    if (btn) askAgent(btn.dataset.agentPrompt);
  });
  document.getElementById("agentForm").addEventListener("submit", e => {
    e.preventDefault();
    const input = document.getElementById("agentInput");
    askAgent(input.value);
    input.value = "";
  });
  document.getElementById("agentLog").addEventListener("click", e => {
    const btn = e.target.closest("[data-agent-i]");
    if (btn) selectNode(Number(btn.dataset.agentI));
  });
}

function wire() {
  document.getElementById("viewMode").addEventListener("change", e => { state.view = e.target.value; buildGraph(); });
  document.getElementById("query").addEventListener("input", e => { state.query = e.target.value; if (state.query.trim()) { state.view = "search"; document.getElementById("viewMode").value = "search"; } buildGraph(); });
  document.getElementById("tagFilter").addEventListener("input", e => { state.tag = e.target.value; buildGraph(); });
  document.getElementById("depth").addEventListener("change", e => { state.depth = Number(e.target.value); buildGraph(); });
  document.getElementById("maxNodes").addEventListener("change", e => { state.maxNodes = Number(e.target.value); buildGraph(); });
  document.getElementById("fitBtn").addEventListener("click", fitGraph);
  document.getElementById("resetBtn").addEventListener("click", () => { state.query = ""; state.tag = ""; state.view = "theorems"; state.statuses.clear(); document.getElementById("query").value = ""; document.getElementById("tagFilter").value = ""; document.getElementById("viewMode").value = "theorems"; document.querySelectorAll("#statusFilters input").forEach(x => x.checked = false); buildGraph(); });
  document.getElementById("focusBtn").addEventListener("click", () => focusName(document.getElementById("quickFocus").value.trim()));
  const canvas = document.getElementById("graphCanvas");
  canvas.addEventListener("click", e => {
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left, y = e.clientY - rect.top;
    let best = null, bd = Infinity;
    for (const id of state.graphNodes) {
      const p = state.positions.get(id); if (!p) continue;
      const d = Math.hypot(p.x - x, p.y - y);
      if (d < bd) { bd = d; best = id; }
    }
    if (best !== null && bd < 24) selectNode(best);
  });
  window.addEventListener("resize", () => { fitGraph(); });
}

renderMetrics();
renderProofStatus();
renderStatusFilters();
renderRecommendations();
renderTimeline();
renderNotes();
renderInspector();
initAgent();
wire();
buildGraph();
animate();
</script>
</body>
</html>
"""


def _load_vendor_cytoscape() -> str:
    """Return the vendored cytoscape.min.js content for inlining. The
    file is pinned (cytoscape 3.31.0) so the published HTML never
    depends on an external CDN at runtime."""
    candidates = [
        Path(__file__).resolve().parent.parent / "vendor" / "cytoscape.min.js",
        REPO / "projects" / "ns_millennium_hunt" / "vendor" / "cytoscape.min.js",
    ]
    for cand in candidates:
        if cand.is_file():
            return cand.read_text(encoding="utf-8")
    raise FileNotFoundError(
        "vendor/cytoscape.min.js not found; re-vendor with:\n"
        "  curl -sSL -o projects/ns_millennium_hunt/vendor/cytoscape.min.js "
        "https://cdn.jsdelivr.net/npm/cytoscape@3.31.0/dist/cytoscape.min.js"
    )


def write_html(out: Path) -> None:
    data = build_data()
    cytoscape_js = _load_vendor_cytoscape()
    out.parent.mkdir(parents=True, exist_ok=True)
    html = (HTML_TEMPLATE
            .replace("__DATA__", json.dumps(data, separators=(",", ":")))
            .replace("__CYTOSCAPE_INLINE__", cytoscape_js))
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out.relative_to(REPO)}")
    print(
        f"decls={data['summary']['decls']} files={data['summary']['files']} "
        f"edges={data['summary']['edges']} quantities={data['summary']['quantities']}"
    )
    print(f"cytoscape inlined: {len(cytoscape_js):,} bytes "
          f"(self-contained, no CDN at runtime)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    write_html(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
