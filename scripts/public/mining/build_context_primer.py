#!/usr/bin/env python3
"""Build a context primer for the contextualized taste rater.

The cold rater never gives ≥5 because it has no codebase context —
to it, every "impossibility result" looks the same. The contextualized
rater gets a primer of THIS codebase's decision-critical infrastructure
plus the operator's curated memory entries, then rates new samples
relative to those anchors.

The primer is BOUNDED in size to avoid ballooning the rating prompt:

  - Top-N most-cited seams from the reference graph (default 15)
  - All memory entries with their MEMORY.md one-line description
  - DECISION_LOG.md key headers (compressed)
  - Anti-pattern catalog one-liners

Each primer entry is one paragraph at most: title + 1-2 line summary
extracted from the artifact's frontmatter description / first
heading / first informative paragraph.

Outputs:
  analytics/public/queries/taste/_taste_context_primer.md

The contextualized rater script consumes this primer.

Pure CPU. No LLM.

Usage:
    python scripts/public/mining/mine_reference_graph.py
    python scripts/public/mining/build_context_primer.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Optional

import yaml  # type: ignore[import-untyped]

REPO = Path(__file__).resolve().parents[3]
GRAPH_PATH = REPO / "analytics" / "public" / "queries" / "reference_graph.json"
MEMORY_INDEX = Path(
    os.environ.get(
        "ZTARE_CLAUDE_MEMORY_INDEX",
        str(Path.home() / ".claude/projects" / os.environ.get("CLAUDE_PROJECT_SLUG", "") / "memory/MEMORY.md"),
    )
)
DECISION_LOG = REPO / "DECISION_LOG.md"
ANTI_PATTERN_CATALOG = REPO / "docs" / "concepts" / "anti_pattern_catalog.md"
OUT_PRIMER = REPO / "analytics" / "public" / "queries" / "taste" / "_taste_context_primer.md"

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def _frontmatter(path: Path) -> dict:
    if not path.exists() or path.suffix.lower() != ".md":
        return {}
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")[:4096]
    except Exception:  # noqa: BLE001
        return {}
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except Exception:  # noqa: BLE001
        return {}


def _first_para_after_frontmatter(path: Path, max_chars: int = 250) -> str:
    """Get the first informative paragraph (non-heading) after frontmatter."""
    if not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return ""
    # Strip frontmatter
    text = _FRONTMATTER_RE.sub("", text, count=1).strip()
    # Strip top H1
    paras = re.split(r"\n\s*\n", text, maxsplit=20)
    for p in paras:
        p = p.strip()
        if not p:
            continue
        if p.startswith("#"):
            continue
        if p.startswith("**") and p.endswith("**"):
            continue
        # Take it; truncate
        cleaned = p.replace("\n", " ")[:max_chars]
        return cleaned
    return ""


def _summarize_seam(path: Path) -> str:
    fm = _frontmatter(path)
    desc = fm.get("description") or ""
    if not desc:
        # Try first paragraph
        desc = _first_para_after_frontmatter(path)
    return str(desc)[:300]


def _gather_top_cited_seams(graph_path: Path, limit: int) -> list[dict]:
    if not graph_path.exists():
        return []
    data = json.loads(graph_path.read_text(encoding="utf-8"))
    top = []
    for n in data.get("top_cited_nodes", []):
        nid = n["id"]
        if not nid.startswith("research_areas/private/seams/"):
            continue
        top.append(n)
        if len(top) >= limit:
            break
    return top


def _gather_memory_entries() -> list[dict]:
    """Parse MEMORY.md to get one-line descriptions per entry."""
    if not MEMORY_INDEX.exists():
        return []
    out = []
    text = MEMORY_INDEX.read_text(encoding="utf-8", errors="ignore")
    # Lines look like: - [Title](file.md) — one-line description
    for line in text.splitlines():
        m = re.match(r"^-\s*\[([^\]]+)\]\(([^)]+)\)\s*[—-]\s*(.+)$", line.strip())
        if not m:
            continue
        out.append({
            "title": m.group(1),
            "file": m.group(2),
            "description": m.group(3).strip(),
        })
    return out


def _gather_decision_log_headers() -> list[str]:
    if not DECISION_LOG.exists():
        return []
    text = DECISION_LOG.read_text(encoding="utf-8", errors="ignore")
    headers = []
    for line in text.splitlines():
        # Top-level decision headers
        if re.match(r"^##\s+", line):
            headers.append(line.strip("# ").strip())
    return headers[:20]  # cap


def _gather_anti_patterns() -> list[str]:
    if not ANTI_PATTERN_CATALOG.exists():
        return []
    text = ANTI_PATTERN_CATALOG.read_text(encoding="utf-8", errors="ignore")
    out = []
    # Look for level-3 headers (## or ###)
    for line in text.splitlines():
        if re.match(r"^###\s+", line):
            out.append(line.strip("# ").strip())
    return out[:25]  # cap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-cited", type=int, default=15)
    ap.add_argument("--out", type=Path, default=OUT_PRIMER)
    ap.add_argument("--graph", type=Path, default=GRAPH_PATH)
    args = ap.parse_args()

    print("=== context primer builder ===")

    top_cited = _gather_top_cited_seams(args.graph, args.top_cited)
    print(f"  top-cited seams: {len(top_cited)}")
    memory = _gather_memory_entries()
    print(f"  memory entries: {len(memory)}")
    decision_headers = _gather_decision_log_headers()
    print(f"  decision-log headers: {len(decision_headers)}")
    anti_patterns = _gather_anti_patterns()
    print(f"  anti-pattern entries: {len(anti_patterns)}")

    md = ["# Taste Rater — Context Primer\n"]
    md.append(
        "This primer is given to a contextualized rater BEFORE rating "
        "samples. It establishes 'what this codebase considers decision-critical.' "
        "The rater uses this as the anchor for distinguishing "
        "domain-significant insights from generic-looking ones.\n\n"
        "**Use this only to anchor scoring relative to the codebase's "
        "own structure. Do NOT use it to recognize specific samples and "
        "score them higher because they're familiar.**\n\n---\n"
    )

    md.append("## Load-bearing seams (top by in-degree from reference graph)\n")
    md.append(
        "These seams are most-cited by other apparatus artifacts. They "
        "represent the structural infrastructure of the codebase. An artifact "
        "that materially extends or refutes one of these is paradigm-shifting "
        "for this codebase (score 5).\n"
    )
    for n in top_cited:
        path = REPO / n["id"]
        summary = _summarize_seam(path)
        md.append(f"- **{Path(n['id']).stem}** (cited {n['in_degree']}x, week {n['week']}): {summary}")
    md.append("")

    md.append("## Operator-curated memory entries\n")
    md.append(
        "These are the operator's distilled lessons across the project's "
        "lifetime. Each is what the operator wanted to remember. An artifact "
        "that surfaces a NEW lesson at this level of generality is high-quality.\n"
    )
    for m in memory:
        md.append(f"- **{m['title']}**: {m['description']}")
    md.append("")

    if anti_patterns:
        md.append("## Known anti-patterns (failure modes already catalogued)\n")
        md.append(
            "Artifacts that surface a NEW failure mode not in this list are "
            "decision-critical. Artifacts that re-discover a known anti-pattern "
            "are typical (score 2).\n"
        )
        for ap_entry in anti_patterns:
            md.append(f"- {ap_entry}")
        md.append("")

    if decision_headers:
        md.append("## Recent decision-log entries (operator-binding decisions)\n")
        for h in decision_headers:
            md.append(f"- {h}")
        md.append("")

    md.append("---\n")
    md.append(
        "## Calibration anchors for the rating scale (0-5)\n\n"
        "Use these as worked examples:\n\n"
        "  - **Score 5 (paradigm-shifting):** A structural finding that "
        "would force a rewrite of one of the decision-critical seams above. "
        "Example: GP-168 unfalsifiability theorem (closure requires "
        "exogenous resource pressure) reframed the apparatus's bicameral "
        "design assumption.\n"
        "  - **Score 4 (decision-critical/mechanism-revealing):** Concrete "
        "mechanism, named gap, or structural framing that a future "
        "reader/seam will cite. Example: GP-138 Noether information-"
        "theoretic impossibility (selector group bounded by Aut(AST)).\n"
        "  - **Score 3 (sharp framing/non-obvious):** A reformulation "
        "that helps but doesn't change the apparatus. Example: 'frame-not-"
        "code was the bottleneck' meta-observation.\n"
        "  - **Score 2 (useful, expected):** Standard apparatus state "
        "recorded clearly. Project charters, evidence sheets that "
        "consolidate without surprising.\n"
        "  - **Score 1 (trivially observable):** Apparatus restatement, "
        "single-fact observation that doesn't change downstream.\n"
        "  - **Score 0 (boilerplate/scaffolding):** README, sentinel "
        "content, generated stubs.\n\n"
        "**Paradigm shifts are RARE.** Most of the corpus is 1-3. A 4 "
        "should appear in 10-20% of samples. A 5 should appear in <5%.\n"
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(md) + "\n")
    print(f"  wrote {args.out} ({args.out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
