#!/usr/bin/env python3
"""Mathlib lemma scout — index Mathlib.Analysis.* (and friends) by type shape.

Borrowed from compiler-verification practice: pre-curated lemma libraries
matching specific proof shapes. Codex's typed-endpoint pack currently sees
only `ztare_proofs/ZtareProofs/` declarations; the analytic primitives that
discharge most PDE estimates live in `Mathlib.Analysis.*`, `Mathlib.Topology.*`,
`Mathlib.MeasureTheory.*`. This script indexes them and exposes a query
API for the typed-endpoint pack.

# What this is, and what it isn't

  IS:  a regex+keyword indexer that builds a JSON index of mathlib decls,
       typed by their result-type shape (LE / LT / EQ / EXISTS / ABS_LE /
       NORM_LE / SOBOLEV / HOLDER / CAUCHY_SCHWARZ / etc.) and tagged with
       file path + first-line preview.

  IS NOT: a Lean elaborator. The shape classification is heuristic.

# Substrate-agnostic by design

  Defaults target NS Track B's relevant analysis subdirs. Override with
  --include-paths to scout other corpora (e.g. number-theory section
  for Riemann work; algebraic-geometry for Yang-Mills; etc.).

# Reuse note

  This is a sibling indexer to `lean_decl_index.py` (which indexes the
  spine itself). The two outputs are concatenable — typed_endpoint_pack
  can union them when building its "resolved set + nearby lemmas" prompt.

Usage:
    # Build the mathlib analysis index (one-time, ~minutes)
    python scripts/public/lean/mathlib_lemma_scout.py --build

    # Query by shape
    python scripts/public/lean/mathlib_lemma_scout.py --query SOBOLEV --top 20
    python scripts/public/lean/mathlib_lemma_scout.py --query HOLDER --top 20
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
MATHLIB_ROOT = REPO / "ztare_proofs" / ".lake" / "packages" / "mathlib" / "Mathlib"
INDEX_PATH = REPO / "analytics" / "public" / "queries" / "lean" / "mathlib_lemma_index.json"

# Default subpaths most relevant to NS-style PDE work. Override via CLI.
DEFAULT_INCLUDE_PATHS = [
    "Analysis",
    "MeasureTheory",
    "Topology",
    "LinearAlgebra/Matrix",  # for matrix bounds
]

# Shape classifiers — regexes matched against the theorem type body
# after stripping binders. Heuristic; multi-tag possible.
SHAPE_PATTERNS = {
    "LE": re.compile(r"\s≤\s|\.le\s+"),
    "LT": re.compile(r"\s<\s|\.lt\s+"),
    "EQ_REAL": re.compile(r"\s=\s.*\s+(ℝ|Real)\b"),
    "EXISTS": re.compile(r"^\s*∃|\bExists\s"),
    "ABS_LE": re.compile(r"\|.*\|\s*≤"),
    "NORM_LE": re.compile(r"\bnorm\b.*≤|‖.*‖.*≤"),
    # PDE-flavored shapes
    "SOBOLEV": re.compile(r"\bSobolev|\bWithDeriv|\bContDiff|\bH\^|\bW\^",
                            re.IGNORECASE),
    "HOLDER": re.compile(r"\bHolder|\bHölder|holder", re.IGNORECASE),
    "CAUCHY_SCHWARZ": re.compile(r"cauchy_schwarz|inner_mul_le", re.IGNORECASE),
    "CAUCHY": re.compile(
        r"\bCauchy\b|cauchy|CauchySeq|IsCauSeq|CauchySeq",
        re.IGNORECASE),
    "TRIANGLE": re.compile(r"\btriangle|norm_add_le", re.IGNORECASE),
    "INTEGRAL": re.compile(r"\b(∫|integral|∫⁻|setIntegral|MeasureTheory\.integral)"),
    "LOWER_SEMICONTINUOUS": re.compile(
        r"LowerSemicontinuous|lowerSemicontinuous|lower_semicont",
        re.IGNORECASE),
    "LIMINF": re.compile(r"\bliminf\b|bliminf|liminf_", re.IGNORECASE),
    "TENDSTO": re.compile(r"\bTendsto\b|\.tendsto\b|tendsto_", re.IGNORECASE),
    "FATOU": re.compile(r"\bFatou\b|fatou", re.IGNORECASE),
    "INTERPOLATION": re.compile(r"interpolation|interp|riesz_thorin", re.IGNORECASE),
    "EMBEDDING": re.compile(r"embedding|inclusion|continuous_inclusion", re.IGNORECASE),
    "COERCIVITY": re.compile(r"coercive|coercivity|gardin|garding", re.IGNORECASE),
    "POSITIVE": re.compile(r"\.nonneg\b|0\s*≤|\b0_le_|nonneg_of"),
    "PROPAGATION": re.compile(r"propagat|finite_speed|domain_of_dependence", re.IGNORECASE),
}

DECL_RE = re.compile(
    r"^(theorem|lemma)\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.MULTILINE,
)


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


def classify_shape(decl_body: str) -> list[str]:
    """Return all shape tags that match the decl body."""
    tags = []
    for shape, pat in SHAPE_PATTERNS.items():
        if pat.search(decl_body):
            tags.append(shape)
    return tags


def scan_mathlib(include_paths: list[str], limit_files: int = 0) -> dict:
    """Walk mathlib, classify each theorem/lemma by shape."""
    decls_by_shape: dict[str, list[dict]] = defaultdict(list)
    decls_by_name: dict[str, dict] = {}
    file_count = 0
    decl_count = 0

    files = []
    for sub in include_paths:
        sub_path = MATHLIB_ROOT / sub
        if sub_path.is_dir():
            files.extend(sub_path.rglob("*.lean"))
        elif sub_path.with_suffix(".lean").exists():
            files.append(sub_path.with_suffix(".lean"))
    if limit_files:
        files = files[:limit_files]
    print(f"[scout] scanning {len(files)} files across {include_paths}")

    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        text = strip_comments(text)
        file_count += 1

        positions = [(m.start(), m.group(1), m.group(2))
                     for m in DECL_RE.finditer(text)]
        positions.append((len(text), "", ""))
        for i in range(len(positions) - 1):
            start, kind, name = positions[i]
            end = min(positions[i + 1][0], start + 800)
            body = text[start:end].strip()
            decl_count += 1
            shapes = classify_shape(body)
            entry = {
                "name": name, "kind": kind,
                "file": str(path.relative_to(MATHLIB_ROOT)),
                "preview": body[:300].replace("\n", " "),
                "shapes": shapes,
            }
            decls_by_name[name] = entry
            for shape in shapes:
                decls_by_shape[shape].append(entry)

        if file_count % 200 == 0:
            print(f"  [{file_count}/{len(files)}] decls={decl_count}")

    return {
        "summary": {
            "n_files": file_count,
            "n_decls": decl_count,
            "by_shape": {k: len(v) for k, v in decls_by_shape.items()},
            "include_paths": include_paths,
            "generated": datetime.now().isoformat(),
        },
        "by_name": decls_by_name,
        "by_shape": {k: [e["name"] for e in v[:500]]
                     for k, v in decls_by_shape.items()},  # cap per-shape list
    }


def query_index(index: dict, shapes: list[str], top: int = 20) -> list[dict]:
    """Return decls matching ALL of the requested shape tags."""
    matched = []
    for name, entry in index["by_name"].items():
        if all(s in entry["shapes"] for s in shapes):
            matched.append(entry)
    matched.sort(key=lambda e: e["name"])
    return matched[:top]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true",
                    help="(re)build the mathlib lemma index")
    ap.add_argument("--include-paths", nargs="*",
                    default=DEFAULT_INCLUDE_PATHS,
                    help="mathlib subpaths to scan")
    ap.add_argument("--limit-files", type=int, default=0,
                    help="cap files scanned (debug)")
    ap.add_argument("--query", nargs="*",
                    help="shape tags to query (e.g. SOBOLEV LE)")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--out", type=Path, default=INDEX_PATH)
    args = ap.parse_args()

    if args.build or not args.out.exists():
        print(f"[scout] building mathlib lemma index from {MATHLIB_ROOT}")
        if not MATHLIB_ROOT.exists():
            print(f"[scout] ERROR: mathlib not at {MATHLIB_ROOT}; run lake update first")
            return 1
        index = scan_mathlib(args.include_paths, args.limit_files)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(index, indent=1))
        print(f"\n[scout] wrote {args.out} ({args.out.stat().st_size / 1e6:.1f} MB)")
        for shape, count in sorted(
                index["summary"]["by_shape"].items(),
                key=lambda kv: -kv[1])[:15]:
            print(f"  {shape}: {count}")

    if args.query:
        index = json.loads(args.out.read_text())
        shapes = [s.upper() for s in args.query]
        results = query_index(index, shapes, args.top)
        print(f"\n[scout] query {shapes}: {len(results)} matches")
        for r in results:
            print(f"  {r['name']} ({r['file']})")
            print(f"    shapes: {r['shapes']}")
            print(f"    preview: {r['preview'][:140]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
