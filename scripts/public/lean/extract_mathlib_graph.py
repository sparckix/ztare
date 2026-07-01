#!/usr/bin/env python3
"""Extract mathlib4 dependency graph for v4 GNN pre-training.

Walks ztare_proofs/.lake/packages/mathlib/Mathlib/, parses each .lean
file for top-level declarations + identifier references, builds a
JSON-LD graph: nodes = decls, edges = decl_X uses decl_Y.

Output: analytics/public/index/mathlib_graph/mathlib_graph.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MATHLIB_ROOT = REPO / "ztare_proofs" / ".lake" / "packages" / "mathlib" / "Mathlib"
OUT = REPO / "analytics" / "public" / "index" / "mathlib_graph" / "mathlib_graph.json"

DECL_RE = re.compile(
    r"^(theorem|lemma|def|abbrev|structure|class|instance|inductive)\s+"
    r"([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)
IDENT_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\b")
LEAN_KW = {
    "by", "do", "if", "then", "else", "let", "in", "fun", "with", "match",
    "have", "show", "from", "exact", "refine", "apply", "intro", "intros",
    "use", "constructor", "rfl", "ring", "linarith", "omega", "simp",
    "Nat", "Int", "Real", "Rat", "Type", "Sort", "Prop", "True", "False",
    "namespace", "end", "open", "import", "section", "variable", "variables",
}


def strip_comments(text: str) -> str:
    out = []; i = 0; depth = 0
    while i < len(text):
        if depth == 0 and text[i:i+2] == "--":
            while i < len(text) and text[i] != "\n":
                i += 1
            continue
        if text[i:i+2] == "/-":
            depth += 1; i += 2; continue
        if depth > 0:
            if text[i:i+2] == "-/":
                depth -= 1; i += 2; continue
            i += 1; continue
        out.append(text[i]); i += 1
    return "".join(out)


def extract_one_file(path: Path) -> tuple[list[dict], list[dict]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return [], []
    text = strip_comments(text)
    file_stem = path.stem
    nodes = []
    edges = []
    decl_positions = [(m.start(), m.group(1), m.group(2)) for m in DECL_RE.finditer(text)]
    if not decl_positions:
        return [], []
    decl_positions.append((len(text), "", ""))  # sentinel
    for i in range(len(decl_positions) - 1):
        start, kind, name = decl_positions[i]
        end = decl_positions[i + 1][0]
        body = text[start:end]
        nodes.append({
            "@type": "decl", "name": name, "kind": kind, "file": file_stem,
        })
        # Find all qualified-name references in the body (likely decls used)
        for m in IDENT_RE.finditer(body):
            ref = m.group(1)
            if ref == name:
                continue
            edges.append({"@type": "depends_on", "src": name, "dst": ref})
    return nodes, edges


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-files", type=int, default=0,
                    help="cap number of files (0 = all)")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    print(f"=== mathlib graph extractor ===")
    print(f"  scanning {MATHLIB_ROOT}")
    files = sorted(MATHLIB_ROOT.rglob("*.lean"))
    if args.limit_files:
        files = files[:args.limit_files]
    print(f"  {len(files)} files")

    all_nodes = []
    all_edges = []
    for i, path in enumerate(files):
        n, e = extract_one_file(path)
        all_nodes.extend(n)
        all_edges.extend(e)
        if (i + 1) % 500 == 0:
            print(f"  [{i+1}/{len(files)}] decls={len(all_nodes)} edges={len(all_edges)}")

    # Dedupe nodes (decls are unique by name globally but may collide; keep
    # first occurrence)
    seen = set()
    unique_nodes = []
    for n in all_nodes:
        if n["name"] in seen: continue
        seen.add(n["name"]); unique_nodes.append(n)
    decl_names = {n["name"] for n in unique_nodes}

    # Filter edges: drop refs to non-decl identifiers (would be stdlib calls)
    kept_edges = []
    for e in all_edges:
        if e["src"] in decl_names and e["dst"] in decl_names:
            kept_edges.append(e)

    print(f"\n=== summary ===")
    print(f"  total decl nodes (unique): {len(unique_nodes)}")
    print(f"  total raw refs: {len(all_edges)}")
    print(f"  edges (both endpoints are decls): {len(kept_edges)}")

    out_obj = {
        "@context": {"@vocab": "https://figs.local/mathlib_graph#"},
        "summary": {
            "n_files": len(files),
            "n_decls": len(unique_nodes),
            "n_edges": len(kept_edges),
        },
        "@graph": unique_nodes + kept_edges,
    }
    args.out.write_text(json.dumps(out_obj, separators=(",", ":")))
    print(f"  wrote {args.out} ({args.out.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
