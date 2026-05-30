#!/usr/bin/env python3
"""Failure-cluster meta-analyzer — find systematic apparatus gaps.

Reads `projects/ns_millennium_hunt/workspace/queries/typed_endpoint_failure_log.jsonl` and clusters
failures by (target_type_head, patch_class, category) triples. Each
cluster reveals a systematic gap:

  - "all *Receipt types fail with endpoint_unbound under TRANSITIVITY_ADAPTER"
    → constructor for Receipt-class types is missing from the pack
  - "all instance_with_evidence runs fail with trivial_degenerate"
    → revision loop degenerates because LLM gives up

Output: a backlog of cluster-level fixes Codex can prioritize.

# Honest scope

  - At small N (<20 failures) clusters are anecdotal. Run after Codex
    has accumulated 50+ runs for meaningful patterns.
  - "Type head" extraction is regex-based on target name; some types
    won't cluster cleanly without manual grouping.

Usage:
    python scripts/public/utilities/failure_cluster_analyzer.py
    python scripts/public/utilities/failure_cluster_analyzer.py --min-cluster-size 3
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
LOG_PATH = (
    REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
    / "typed_endpoint_failure_log.jsonl"
)
OUT_PATH = REPO / "analytics" / "public" / "queries" / "audits" / "failure_clusters.md"


def extract_type_head(target: str) -> str:
    """Extract the type-head suffix from a target name.
    e.g. 'TrackBProfileLipschitzControlObligation' -> 'Obligation'
         'LeraySelfTaxProfilePriceStream' -> 'Stream'
         'GP216BridgeCompositionReceipt' -> 'Receipt'
    """
    suffixes = ["Obligation", "Receipt", "Stream", "Certificate", "Lift",
                "Bridge", "Spine"]
    for suf in sorted(suffixes, key=len, reverse=True):
        if target.endswith(suf):
            return suf
    # Fallback: last camelCase segment
    parts = re.findall(r"[A-Z][a-z]*", target)
    return parts[-1] if parts else target


def load_log() -> list[dict]:
    if not LOG_PATH.exists():
        return []
    out = []
    for line in LOG_PATH.read_text().splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-cluster-size", type=int, default=2,
                    help="suppress clusters smaller than this")
    ap.add_argument("--out", type=Path, default=OUT_PATH)
    args = ap.parse_args()

    rows = load_log()
    if not rows:
        print(f"no failure log; nothing to cluster yet")
        return 0

    print(f"=== failure cluster analyzer ===")
    print(f"  total failures: {len(rows)}")

    # Cluster by (type_head, patch_class, category)
    clusters: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        target = r.get("target", "?")
        type_head = extract_type_head(target)
        cluster_key = (type_head, r.get("patch_class", "?"),
                        r.get("category", "?"))
        clusters[cluster_key].append(r)

    # Sort by size desc
    sorted_clusters = sorted(clusters.items(), key=lambda kv: -len(kv[1]))

    print(f"\n=== clusters (min size {args.min_cluster_size}) ===")
    visible = [(k, v) for k, v in sorted_clusters if len(v) >= args.min_cluster_size]
    if not visible:
        print(f"  no clusters at threshold; lower --min-cluster-size to see")
    for (type_head, patch_class, category), items in visible:
        print(f"\n  [{len(items)}x] type_head={type_head} class={patch_class} category={category}")
        for item in items[:3]:
            tname = item.get("target", "?")[:60]
            print(f"    - {tname}::{item.get('field', '?')[:30]}")

    # Single-axis distributions
    print(f"\n=== single-axis distributions ===")
    by_category = Counter(r.get("category") for r in rows)
    by_class = Counter(r.get("patch_class") for r in rows)
    by_type_head = Counter(extract_type_head(r.get("target", "?")) for r in rows)
    print(f"  by category:   {dict(by_category)}")
    print(f"  by patch_class: {dict(by_class)}")
    print(f"  by type_head:  {dict(by_type_head)}")

    # Write markdown
    lines = ["# Failure Cluster Analysis", "",
             f"Generated: {datetime.now().isoformat()}",
             f"Total failures: {len(rows)}",
             "",
             f"## Single-axis distributions", "",
             f"### By category", ""]
    for k, v in by_category.most_common():
        lines.append(f"- {k}: {v}")
    lines.extend(["", "### By patch_class", ""])
    for k, v in by_class.most_common():
        lines.append(f"- {k}: {v}")
    lines.extend(["", "### By type_head", ""])
    for k, v in by_type_head.most_common():
        lines.append(f"- {k}: {v}")
    lines.extend(["", f"## Clusters (size ≥ {args.min_cluster_size})", ""])
    for (type_head, patch_class, category), items in visible:
        lines.append(f"### {len(items)}x: type_head={type_head}, "
                      f"class={patch_class}, category={category}")
        lines.append("")
        for item in items:
            tname = item.get("target", "?")
            lines.append(f"- {tname}::{item.get('field', '?')} ({item.get('ts', '')[:19]})")
        lines.append("")
        # Hypothesize a fix
        if category == "endpoint_unbound":
            lines.append(f"  **Hypothesis:** the resolved set for type_head=`{type_head}` "
                          f"is missing some constructor / lemma the LLM keeps reaching for. "
                          f"Action: dump the actual stderr to find the unresolved name; "
                          f"add to the pack's resolved set.")
        elif category == "trivial_degenerate":
            lines.append(f"  **Hypothesis:** revision loop degenerates on this class. "
                          f"Either tighten the anti-degen check or add stronger "
                          f"non-trivial-content requirement to the prompt.")
        elif category == "llm_refused":
            lines.append(f"  **Hypothesis:** the LLM correctly identifies missing primitives. "
                          f"Run `cannot_patch_harvester.py` to extract the named missing objects "
                          f"and add them to the spine.")
        elif category == "missing_constructor":
            lines.append(f"  **Hypothesis:** field type's constructors aren't being resolved. "
                          f"Check `find_type_constructors` regex against this type_head.")
        lines.append("")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines))
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
