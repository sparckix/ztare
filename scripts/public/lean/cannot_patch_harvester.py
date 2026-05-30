#!/usr/bin/env python3
"""CANNOT-PATCH diagnostic harvester — mine LLM refusals for missing primitives.

When the LLM refuses with `# CANNOT PATCH`, the diagnosis paragraph names
a missing analytic inequality / constructor / type / lemma. Currently
those refusals just sit in
`projects/ns_millennium_hunt/workspace/queries/typed_endpoint_failure_log.jsonl`
and the per-run response files, but they ARE the apparatus's most-honest
output: "this specific gap in the spine is what's blocking closure."

This script aggregates all CANNOT-PATCH diagnoses across runs and
extracts a structured backlog Codex can act on.

# Output

  projects/ns_millennium_hunt/workspace/queries/missing_primitives_backlog.md

  Categories:
    missing_constructor — type X has no resolvable constructor in the pack
    missing_inequality  — bound between specific quantities X and Y
    missing_lemma_class — broader class of lemmas needed
    missing_definition  — type or value referenced but not defined
    other_diagnosis     — couldn't categorize automatically

# Sources

  - projects/ns_millennium_hunt/workspace/queries/typed_endpoint_failure_log.jsonl
  - projects/ns_millennium_hunt/workspace/queries/typed_endpoint_runs/*_response.md
  - projects/ns_millennium_hunt/workspace/queries/typed_patch_runs/*_response.md (legacy)

Usage:
    python scripts/public/lean/cannot_patch_harvester.py
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
FAILURE_LOG = (
    REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
    / "typed_endpoint_failure_log.jsonl"
)
RESPONSE_DIRS = [
    REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries" / "typed_endpoint_runs",
    REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries" / "typed_patch_runs",
]
OUT_PATH = (
    REPO / "projects" / "ns_millennium_hunt" / "workspace" / "queries"
    / "missing_primitives_backlog.md"
)

# Patterns that classify a diagnosis paragraph
PATTERNS = [
    ("missing_constructor",
     re.compile(r"\b(constructor|elimination principle|Field type|inductive)"
                r"|definitions?,?\s+constructors?",
                re.IGNORECASE)),
    ("missing_inequality",
     re.compile(r"\b(inequality|bound|≤|<|estimate|comparison|le_)",
                re.IGNORECASE)),
    ("missing_lemma_class",
     re.compile(r"\b(lemma|theorem|missing.*(lemma|theorem)|require.*proof"
                r"|analytic\s+inequality)",
                re.IGNORECASE)),
    ("missing_definition",
     re.compile(r"\b(definition|undefined|reference|undeclared)",
                re.IGNORECASE)),
]

IDENT_RE = re.compile(r"`([A-Z][A-Za-z0-9_.]*)`|`([a-z][A-Za-z0-9_.]+)`")


def categorize(diagnosis: str) -> str:
    for cat, pat in PATTERNS:
        if pat.search(diagnosis):
            return cat
    return "other_diagnosis"


def extract_named_objects(diagnosis: str) -> list[str]:
    """Pull backticked Lean names from diagnosis."""
    out = []
    for m in IDENT_RE.finditer(diagnosis):
        name = m.group(1) or m.group(2)
        if name and len(name) >= 3:
            out.append(name)
    return list(dict.fromkeys(out))[:8]  # dedupe, cap


def harvest_from_failure_log() -> list[dict]:
    out = []
    if not FAILURE_LOG.exists():
        return out
    for line in FAILURE_LOG.read_text().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("category") != "llm_refused":
            continue
        diagnosis = row.get("llm_response_tail", "")
        if "# CANNOT PATCH" not in diagnosis.upper():
            continue
        # The diagnosis paragraph is everything after CANNOT PATCH
        idx = diagnosis.upper().find("# CANNOT PATCH")
        diag_text = diagnosis[idx + len("# CANNOT PATCH"):].strip()
        if not diag_text:
            continue
        out.append({
            "source": "failure_log",
            "ts": row.get("ts"),
            "target": row.get("target"),
            "field": row.get("field"),
            "patch_class": row.get("patch_class"),
            "diagnosis": diag_text[:1000],
            "category": categorize(diag_text),
            "named_objects": extract_named_objects(diag_text),
        })
    return out


def harvest_from_response_files() -> list[dict]:
    out = []
    for dir_path in RESPONSE_DIRS:
        if not dir_path.exists():
            continue
        for path in dir_path.glob("*_response.md"):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            if "# CANNOT PATCH" not in text.upper():
                continue
            idx = text.upper().find("# CANNOT PATCH")
            diag_text = text[idx + len("# CANNOT PATCH"):].strip()
            if not diag_text:
                continue
            # Try to parse the filename as <target>_<field>_<class>_response.md
            stem_parts = path.stem.replace("_response", "").rsplit("_", 2)
            target = stem_parts[0] if stem_parts else path.stem
            field = stem_parts[1] if len(stem_parts) > 1 else ""
            patch_class = stem_parts[2] if len(stem_parts) > 2 else ""
            out.append({
                "source": str(path.relative_to(REPO)),
                "ts": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                "target": target,
                "field": field,
                "patch_class": patch_class,
                "diagnosis": diag_text[:1000],
                "category": categorize(diag_text),
                "named_objects": extract_named_objects(diag_text),
            })
    return out


def aggregate(items: list[dict]) -> dict:
    by_category = defaultdict(list)
    by_named_object = Counter()
    by_target = defaultdict(list)
    for item in items:
        by_category[item["category"]].append(item)
        for n in item["named_objects"]:
            by_named_object[n] += 1
        by_target[item["target"]].append(item)
    return {
        "total": len(items),
        "by_category": {k: len(v) for k, v in by_category.items()},
        "by_named_object_top": by_named_object.most_common(15),
        "by_target": {k: len(v) for k, v in by_target.items()},
        "items": items,
        "category_groups": dict(by_category),
    }


def render_backlog(agg: dict) -> str:
    lines = ["# Missing Primitives Backlog",
             "",
             f"Aggregated from CANNOT-PATCH diagnoses across all apparatus runs.",
             f"Generated: {datetime.now().isoformat()}",
             "",
             f"## Summary",
             f"- total CANNOT-PATCH events: {agg['total']}",
             f"- by category: {agg['by_category']}",
             "",
             f"## Most-mentioned named objects (likely missing primitives)",
             ""]
    for name, count in agg["by_named_object_top"]:
        lines.append(f"- **{name}** — referenced in {count} CANNOT-PATCH events")
    lines.extend(["", f"## Targets with CANNOT-PATCH events", ""])
    for target, count in sorted(agg["by_target"].items(),
                                  key=lambda kv: -kv[1]):
        lines.append(f"- {target}: {count}")
    lines.extend(["", "## Diagnoses by category", ""])
    for cat, items in agg["category_groups"].items():
        lines.append(f"### {cat} ({len(items)})")
        lines.append("")
        for item in items[:10]:  # cap per category
            lines.append(f"- **{item.get('target')}::{item.get('field')}** "
                          f"({item.get('patch_class')}, {item.get('source')[:40]})")
            lines.append(f"  > {item['diagnosis'][:300].replace(chr(10), ' ')}")
            if item["named_objects"]:
                lines.append(f"  named: {', '.join(item['named_objects'])}")
            lines.append("")
    lines.append("---\n")
    lines.append("## Codex action: missing-primitive backlog")
    lines.append("")
    lines.append("For each high-frequency named object, decide:")
    lines.append("- `add_to_spine` — write the missing constructor/lemma in Lean")
    lines.append("- `import_from_mathlib` — exists in mathlib, just needs import")
    lines.append("- `wrong_diagnosis` — apparatus misread the gap")
    lines.append("- `out_of_scope` — closure doesn't actually need this")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=OUT_PATH)
    args = ap.parse_args()

    print("=== CANNOT-PATCH harvester ===")
    log_items = harvest_from_failure_log()
    response_items = harvest_from_response_files()
    print(f"  failure_log items: {len(log_items)}")
    print(f"  response_dir items: {len(response_items)}")
    items = log_items + response_items

    if not items:
        print("  no CANNOT-PATCH events found yet")
        return 0

    agg = aggregate(items)
    print(f"\n  total: {agg['total']}")
    print(f"  by_category: {agg['by_category']}")
    print(f"  top named objects: {agg['by_named_object_top'][:5]}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_backlog(agg))
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
