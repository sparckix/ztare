#!/usr/bin/env python3
"""Render `analytics/public/index/architecture_index.jsonl` into `src/ztare/architecture_index/INDEX.md`.

The index is the discoverability meta-graph for ZTARE architectural primitives —
analogous to the seam graph but for code/runtime capabilities. It's wired into
`org/mandates/research_director_mandate.md` so every Director dispatch sees the
catalog of available primitives, pattern-matched by lexical triggers and
impact-weighted from the catch ledger + climb-trigger mining.

Relocated 2026-05-08 from `org/ARCHITECTURE_INDEX.md` per operator directive:
the index is ZTARE-specific (mining, GP-216/219 ops, Lagrangian primitive); `org/`
is the public-kernel split-target so ZTARE-specific artifacts must live in `src/ztare/`.

Usage:
    python scripts/public/control/render_architecture_index.py
    python scripts/public/control/render_architecture_index.py --grep <substring>
    python scripts/public/control/render_architecture_index.py --kind gate
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
INDEX_PATH = REPO_ROOT / "analytics" / "public" / "index" / "architecture_index.jsonl"
OUTPUT_PATH = REPO_ROOT / "src" / "ztare" / "architecture_index" / "INDEX.md"


def load_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def validate_paths(rows: list[dict]) -> list[str]:
    missing = []
    for r in rows:
        if not (REPO_ROOT / r["path"]).exists():
            missing.append(r["path"])
    return missing


KIND_ORDER = [
    "reflexive_primitive",
    "pattern",
    "anti-pattern",
    "op",
    "gate",
    "primitive",
    "validator",
    "orchestrator",
    "mining",
    "script",
]

KIND_LABELS = {
    "reflexive_primitive": "Reflexive Primitives (Self-Referential Architectural Components)",
    "pattern": "Orchestration Patterns",
    "anti-pattern": "Anti-Patterns (Catch-Ledger-Backed)",
    "op": "Universal / Domain Op Vocabularies",
    "gate": "Gates (Cage-Runtime Deterministic Checks)",
    "primitive": "Fit + Research-Director Primitives",
    "validator": "Validator-Core (Autoresearch Loop)",
    "orchestrator": "Orchestrator Briefing Providers",
    "mining": "Mining Scripts (Trajectory + Catch Analysis)",
    "script": "One-Shot / Specialized Scripts",
}


def render_row(r: dict) -> str:
    triggers = ", ".join(f"`{t}`" for t in r["applicability"][:6])
    if len(r["applicability"]) > 6:
        triggers += f", +{len(r['applicability']) - 6} more"
    deps = ", ".join(r["dependencies"]) if r["dependencies"] else "—"
    return (
        f"| **{r['id']}** | `{r['path']}` | {r['impact_factor_expost']} | "
        f"{r['last_used']} | {r['description']} | {triggers} | {deps} |"
    )


def _coerce_rows(rows: list[dict]) -> list[dict]:
    """Defensive schema coercion so a malformed concurrent-session row
    cannot crash the render the precheck consumes (the index is the
    discoverability surface — a hard crash makes it stale for ALL agents).
    Coerces to nearest-valid + flags `_schema_coerced`; does NOT edit the
    underlying jsonl (another agent may own that row)."""
    for r in rows:
        flagged = []
        if "impact_factor_expost" not in r:
            r["impact_factor_expost"] = 0
            flagged.append("impact_factor_expost")
        v = r.get("impact_factor_expost", 0)
        if not isinstance(v, int):
            try:
                r["impact_factor_expost"] = int(float(v))
            except (TypeError, ValueError):
                r["impact_factor_expost"] = 0
            flagged.append("impact_factor_expost")
        for k in ("applicability", "dependencies"):
            if not isinstance(r.get(k), list):
                r[k] = [str(r[k])] if r.get(k) not in (None, "") else []
                flagged.append(k)
        for k in ("id", "path", "kind", "description", "last_used"):
            if k not in r:
                r[k] = ""
                flagged.append(k)
            elif not isinstance(r.get(k), str):
                r[k] = str(r.get(k, ""))
                flagged.append(k)
        if flagged:
            r["_schema_coerced"] = flagged
    return rows


def render(rows: list[dict]) -> str:
    rows_sorted_by_impact = sorted(
        rows,
        key=lambda r: (-r["impact_factor_expost"], r["id"]),
    )
    top10 = rows_sorted_by_impact[:10]
    bottom_stale = sorted(
        [r for r in rows if r["impact_factor_expost"] <= 1],
        key=lambda r: (r["impact_factor_expost"], r["last_used"]),
    )[:10]

    impact_hist = collections.Counter(r["impact_factor_expost"] for r in rows)
    kind_hist = collections.Counter(r["kind"] for r in rows)

    lines: list[str] = []
    lines.append("# ZTARE Architecture Index")
    lines.append("")
    lines.append(
        "**Discoverability meta-graph** for ZTARE architectural primitives "
        "— analogous to the seam graph but for code/runtime capabilities. "
        "Pattern-match by lexical triggers / problem class. "
        "Impact-weighted from the catch ledger + climb-trigger mining + "
        "session usage."
    )
    lines.append("")
    lines.append(
        f"**Total primitives indexed:** {len(rows)} "
        f"(rendered from `analytics/public/index/architecture_index.jsonl`)."
    )
    lines.append("")
    lines.append("**Schema:** `analytics/public/index/architecture_index_schema.md`")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## How to use (for Director / agent dispatchers)")
    lines.append("")
    lines.append(
        "Before dispatching agents on a hard problem, scan the **TOP-10** + "
        "the **kind table** matching your problem class. Use lexical/structural "
        "triggers in the `applicability` column to match. **Honest scoring rule:** "
        "primitives at impact_factor 0-1 may be architectural debt — verify "
            "before invoking; primitives at 4-5 produced consequential outputs recently "
        "and are safe defaults."
    )
    lines.append("")
    lines.append(
        "Re-render via `python scripts/public/control/render_architecture_index.py`. "
        "Update `impact_factor_expost` + `last_used` when a primitive fires "
        "in a consequential way."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Distribution")
    lines.append("")
    lines.append("**By kind:**")
    lines.append("")
    for kind in KIND_ORDER:
        if kind in kind_hist:
            lines.append(f"- `{kind}`: {kind_hist[kind]}")
    lines.append("")
    lines.append("**By impact factor (0=stale ... 5=recently consequential):**")
    lines.append("")
    for impact in sorted(impact_hist.keys(), reverse=True):
        bar = "#" * impact_hist[impact]
        lines.append(f"- `{impact}`: {impact_hist[impact]:>3}  {bar}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## TOP 10 HIGH-IMPACT PRIMITIVES")
    lines.append("")
    lines.append(
        "These are the primitives with the strongest recent evidence. New agents "
        "should **default to these** when applicable; deviation requires a "
        "stated reason in the F-row."
    )
    lines.append("")
    lines.append("| ID | Path | Impact | Last Used | Description | Triggers | Depends |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in top10:
        lines.append(render_row(r))
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## BOTTOM 10 STALE (impact 0-1) — Architectural Debt Candidates")
    lines.append("")
    lines.append(
        "Untouched in last 30 days OR never observed firing in a catch ledger. "
        "Flag for principal review during retirement sweeps. Do **not** auto-delete."
    )
    lines.append("")
    lines.append("| ID | Path | Impact | Last Used | Description |")
    lines.append("|---|---|---|---|---|")
    for r in bottom_stale:
        lines.append(
            f"| **{r['id']}** | `{r['path']}` | {r['impact_factor_expost']} | "
            f"{r['last_used']} | {r['description']} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Full Catalog (grouped by kind, sorted by impact)")
    lines.append("")

    by_kind: dict[str, list[dict]] = collections.defaultdict(list)
    for r in rows:
        by_kind[r["kind"]].append(r)

    for kind in KIND_ORDER:
        if kind not in by_kind:
            continue
        kind_rows = sorted(
            by_kind[kind],
            key=lambda r: (-r["impact_factor_expost"], r["id"]),
        )
        lines.append(f"### {KIND_LABELS[kind]} (`{kind}`, n={len(kind_rows)})")
        lines.append("")
        lines.append(
            "| ID | Path | Impact | Last Used | Description | Triggers | Depends |"
        )
        lines.append("|---|---|---|---|---|---|---|")
        for r in kind_rows:
            lines.append(render_row(r))
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "*Generated by `scripts/public/control/render_architecture_index.py` from "
        "`analytics/public/index/architecture_index.jsonl`. Schema: "
        "`analytics/public/index/architecture_index_schema.md`.*"
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--grep",
        help="Filter rows where any field contains the substring (case-insensitive).",
    )
    ap.add_argument(
        "--kind",
        help="Filter rows by kind.",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="Validate paths exist; non-zero exit if any are missing.",
    )
    ap.add_argument(
        "--out",
        default=str(OUTPUT_PATH),
        help=f"Output markdown path (default: {OUTPUT_PATH}).",
    )
    args = ap.parse_args()

    if not INDEX_PATH.exists():
        print(f"ERROR: index not found at {INDEX_PATH}", file=sys.stderr)
        return 2

    rows = load_rows(INDEX_PATH)
    rows = _coerce_rows(rows)

    missing = validate_paths(rows)
    if missing:
        print(f"WARN: {len(missing)} primitive paths do not exist on disk:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        if args.check:
            return 1

    if args.grep:
        needle = args.grep.lower()
        rows = [
            r
            for r in rows
            if needle in json.dumps(r).lower()
        ]
        for r in rows:
            print(
                f"{r['id']:50s} impact={r['impact_factor_expost']} "
                f"last={r['last_used']} kind={r['kind']:12s} {r['path']}"
            )
        print(f"\n{len(rows)} match(es).")
        return 0

    if args.kind:
        rows = [r for r in rows if r["kind"] == args.kind]

    md = render(rows)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md)
    print(f"Wrote {out_path} ({len(rows)} primitives, {len(md):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
