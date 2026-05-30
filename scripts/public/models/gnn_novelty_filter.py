#!/usr/bin/env python3
"""TEST B — novelty filter on v3 GNN predictions.

For each top-K v3 GNN nomination:
  - Compute overlap with: (a) existing spine theorems by name match,
    (b) quantities cited in F-rows in last 7 days,
    (c) receipt-tree of currently-open obligations
  - novelty_score = gnn_score × (1 - overlap_with_known)

Output: nominations re-ranked by novelty, surface ones that have
HIGH GNN score but LOW overlap with everything Codex already touches.

If most high-GNN nominations have low novelty → apparatus is descriptive
of what's known (the v3 finding, confirmed at scale).
If a meaningful fraction have high novelty → those are the real
closure-utility candidates.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts" / "public" / "projects" / "ns"))


def load_existing_decl_names() -> set[str]:
    """Pull every Lean decl name from ztare_proofs/ZtareProofs/."""
    decl_re = re.compile(
        r"^(?:theorem|lemma|def|structure|class|instance|abbrev)\s+"
        r"([A-Za-z_][A-Za-z0-9_]*)",
        re.MULTILINE,
    )
    names = set()
    lean_dir = REPO / "ztare_proofs" / "ZtareProofs"
    for path in lean_dir.glob("*.lean"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in decl_re.finditer(text):
            names.add(m.group(1))
    return names


def load_recent_frow_quantities(days_back: int = 7) -> set[str]:
    """Pull quantity-name tokens from F-rows in the last N days."""
    track = REPO / "research_areas" / "EXPERIMENT_TRACK_RECORD.md"
    if not track.exists():
        return set()
    text = track.read_text(encoding="utf-8", errors="ignore")
    cutoff = datetime.now() - timedelta(days=days_back)
    cutoff_str = cutoff.strftime("%Y-%m-%d")
    quantities = set()
    ident_re = re.compile(r"\b([a-z][A-Za-z0-9_]+(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\b")
    for line in text.splitlines():
        if not line.startswith("| F-"):
            continue
        date_m = re.search(r"(\d{4}-\d{2}-\d{2})", line)
        if not date_m or date_m.group(1) < cutoff_str:
            continue
        for m in ident_re.finditer(line):
            tok = m.group(1)
            if len(tok) >= 4 and not tok in {"this", "that", "with", "from"}:
                quantities.add(tok)
    return quantities


def load_open_obligation_quantities() -> set[str]:
    """Pull field names from the open-obligations workmap."""
    workmap_path = (
        REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
        / "ns_trackb_instantiation_workmap.json"
    )
    if not workmap_path.exists():
        return set()
    workmap = json.loads(workmap_path.read_text())
    quantities = set()
    items = workmap if isinstance(workmap, list) else workmap.get("structures", [])
    for ob in items:
        for fld in ob.get("fields", []):
            name = fld.get("name") if isinstance(fld, dict) else fld
            if name:
                quantities.add(name)
    return quantities


def split_camel_words(name: str) -> set[str]:
    """SelfTaxLimitPrice -> {selftaxlimitprice, self, tax, limit, price}."""
    import re
    name = name.replace(".", " ").replace("_", " ").strip()
    out = {name.lower()}
    # camelCase split
    parts = re.findall(r"[A-Z][a-z]*|[a-z]+|[0-9]+", name)
    for p in parts:
        if len(p) >= 3:  # skip 1-2 char fragments
            out.add(p.lower())
    return out


def build_known_word_index(known_decls: set[str]) -> set[str]:
    """Pre-split decl names into the universe of words they cover."""
    index = set()
    for d in known_decls:
        index.update(split_camel_words(d))
    return index


def quantity_overlap_score(qty_name: str, known_decl_words: set[str],
                            recent_quantity_words: set[str],
                            open_quantity_words: set[str]) -> float:
    """0.0 = totally novel; 1.0 = entirely known.

    Vocabulary alignment fix (2026-05-06): graph quantity names are short
    (e.g. 'reserve', 'C', 'nu') while Lean decl names are PascalCase compound
    ('TrackBProfileLipschitzControlObligation'). Exact match misses; word-
    boundary match (camelCase split) bridges the gap.
    """
    short = qty_name[4:] if qty_name.startswith("qty:") else qty_name
    qty_words = split_camel_words(short)
    if not qty_words:
        return 0.0
    matches = 0
    total_checks = 3
    if qty_words & known_decl_words:
        matches += 1
    if qty_words & recent_quantity_words:
        matches += 1
    if qty_words & open_quantity_words:
        matches += 1
    return matches / total_checks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-k", type=int, default=30)
    ap.add_argument("--op", default="le")
    ap.add_argument("--out", type=Path,
                    default=REPO / "analytics" / "public" / "queries" / "gnn_v3_novelty_ranked.md")
    args = ap.parse_args()

    print("=== TEST B: v3 GNN novelty filter ===")
    print("[1] loading known decl + recent F-row + open-obligation vocabularies...")
    known_decls = load_existing_decl_names()
    recent_q = load_recent_frow_quantities()
    open_q = load_open_obligation_quantities()
    print(f"  known decls: {len(known_decls)}")
    print(f"  recent F-row quantities (last 7d): {len(recent_q)}")
    print(f"  open-obligation field quantities: {len(open_q)}")
    # Build word-level vocabularies (camelCase split) for accurate matching
    known_decl_words = build_known_word_index(known_decls)
    recent_words = build_known_word_index(recent_q)
    open_words = build_known_word_index(open_q)
    print(f"  known decl words (after camelCase split): {len(known_decl_words)}")

    print("\n[2] running v3 GNN top-K novel scoring...")
    # Re-use v3 inference machinery
    from gnn_link_predict_score_v3 import load_v3, get_h, score_pair, adamic_adar
    encoder, scorer, feat, node_idx, edges, device = load_v3()
    h = get_h(encoder, feat, edges, node_idx, device)
    existing = {(u, v) for u, v, _ in edges}
    deg = defaultdict(int)
    for u, v, _ in edges:
        deg[u] += 1; deg[v] += 1
    # Reuse plumbing detector from the constraint-basin script
    try:
        import ns_constraint_basin_graph as ncb
        def is_plumbing(n):
            short = n[4:] if n.startswith("qty:") else n
            return ncb.is_plumbing_quantity(short)
    except Exception:
        # fallback: short single-letter / underscore-prefixed names
        def is_plumbing(n):
            short = n[4:] if n.startswith("qty:") else n
            return len(short) <= 2 or short.startswith("_") or short in {
                "forall", "exists", "true", "false", "unfold", "fold"}
    candidates_n = [n for n, _ in sorted(deg.items(), key=lambda kv: -kv[1])
                    if n in node_idx and not is_plumbing(n)][:80]
    print(f"  candidate pool (after plumbing strip): {len(candidates_n)} nodes")
    pairs = [(u, v) for i, u in enumerate(candidates_n)
             for v in candidates_n[i+1:]
             if (u, v) not in existing and (v, u) not in existing]
    rows = []
    for u, v in pairs:
        gnn = score_pair(scorer, h, node_idx, u, v, args.op, device)
        aa = adamic_adar(edges, u, v)
        u_short = u[4:] if u.startswith("qty:") else u
        v_short = v[4:] if v.startswith("qty:") else v
        u_overlap = quantity_overlap_score(u, known_decl_words, recent_words, open_words)
        v_overlap = quantity_overlap_score(v, known_decl_words, recent_words, open_words)
        avg_overlap = (u_overlap + v_overlap) / 2
        # Two-stage rank: filter top-K by GNN first, then surface low-overlap
        # within those. Avoids the negative-score sign-flip artifact.
        rows.append({
            "src": u_short, "dst": v_short, "gnn": gnn or float("-inf"),
            "aa": aa,
            "u_overlap": u_overlap, "v_overlap": v_overlap,
            "avg_overlap": avg_overlap,
        })

    # Stage 1: top by GNN (most-confident predictions)
    rows.sort(key=lambda r: -r["gnn"])
    top_by_gnn = rows[:max(args.top_k * 5, 100)]
    # Stage 2: re-sort by overlap ascending (most-novel within high-confidence)
    top_by_gnn.sort(key=lambda r: r["avg_overlap"])
    # Within ties on overlap, prefer AA-confirmed
    top_by_gnn.sort(key=lambda r: (r["avg_overlap"], -r["aa"]))
    rows = top_by_gnn
    print(f"\n[3] top-{args.top_k} novel-ranked nominations:")
    print(f"  (filter: top-{max(args.top_k*5, 100)} by GNN, then re-sort by overlap asc + AA desc)")
    print(f"  {'rank':>4} {'GNN':>7} {'overlap':>7} {'AA':>5}  edge")
    for i, r in enumerate(rows[:args.top_k], 1):
        marker = "✓" if r["aa"] > 0 else "?"
        print(f"  {i:>4}  {r['gnn']:>+6.3f} "
              f"{r['avg_overlap']:>6.2f} {r['aa']:>4.2f} {marker}  "
              f"{r['src']}  {args.op}  {r['dst']}")

    # Write structured output
    out_lines = ["# v3 GNN novelty-filtered nominations\n",
                 f"**Date:** {datetime.now().isoformat()}\n",
                 f"**Pool:** {len(pairs)} non-existing pairs from top-80 degree nodes\n",
                 f"**Vocabularies used:** {len(known_decls)} known decls, "
                 f"{len(recent_q)} recent F-row quantities, "
                 f"{len(open_q)} open-obligation fields\n\n",
                 "| rank | GNN | overlap | AA | src | op | dst |",
                 "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows[:args.top_k], 1):
        marker = "✓" if r["aa"] > 0 else "?"
        out_lines.append(f"| {i} | {r['gnn']:+.3f} | "
                          f"{r['avg_overlap']:.2f} | {r['aa']:.2f} {marker} | "
                          f"{r['src']} | {args.op} | {r['dst']} |")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(out_lines))
    print(f"\nwrote {args.out}")

    # Summary stats
    print(f"\n=== summary ===")
    print(f"  top-{args.top_k} with overlap = 0 (no known-vocab match): "
          f"{sum(1 for r in rows[:args.top_k] if r['avg_overlap'] == 0)}")
    print(f"  top-{args.top_k} with overlap >= 0.5 (well-known): "
          f"{sum(1 for r in rows[:args.top_k] if r['avg_overlap'] >= 0.5)}")
    print(f"  top-{args.top_k} with AA > 0 (structurally supported): "
          f"{sum(1 for r in rows[:args.top_k] if r['aa'] > 0)}")
    print(f"\n  HONEST CAVEAT: vocabulary gap between graph quantity names "
          f"(short, lowercase) and Lean decl names (PascalCase) limits the "
          f"overlap-detection. Most plumbing-named graph nodes show overlap=0 "
          f"because they are local binders not top-level decls.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
