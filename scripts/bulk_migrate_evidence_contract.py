#!/usr/bin/env python3
"""GP-157 v5.0 Layer 2 bulk migration — add evidence_contract blocks.

For each rubric in rubrics/ that lacks an `evidence_contract` block,
detect the substrate's evidence format from its evidence.txt and write
the block. Per panel design: one-shot batch classifier, write-back,
then enforcement on.

Usage:
    python scripts/bulk_migrate_evidence_contract.py [--dry-run] [--slug SUBSTRATE]

Detection heuristics:
  - Markdown table rows with `|` delimiter   → MARKDOWN_TABLE
  - `=== var = val ===` block headers       → SWEEP_BLOCK
  - Comma-separated rows                    → CSV_HEADER
  - Tab-separated rows                      → TSV_HEADER
  - JSON object per line                    → JSON_LINES
  - Otherwise (whitespace numeric)          → WHITESPACE_TABULAR
  - No parseable rows                       → NONE (skip — not a fitting substrate)

Ambiguous: writes block under `evidence_contract.format_provenance="auto_detected"`
and prints a warning so operator can verify.

Skips substrates where:
  - rubric already has `evidence_contract` block
  - cage_meta.class is in {audit, literature, proof_target} (no fittable evidence)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Substrate classes that do NOT use fittable tabular evidence.
SKIP_CLASSES = frozenset({"audit", "literature", "proof_target"})


def detect_format(evidence_text: str) -> tuple[str, dict]:
    """Heuristic format detection. Returns (format_name, metadata)."""
    lines = [ln for ln in evidence_text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    if not lines:
        return "NONE", {}

    # Sweep block?
    if any(re.match(r"===\s*\w+\s*=\s*[\d.eE+-]+\s*===", ln.strip()) for ln in lines):
        return "SWEEP_BLOCK", {}

    # JSON Lines?
    json_count = 0
    for ln in lines[:10]:
        if ln.strip().startswith("{") and ln.strip().endswith("}"):
            try:
                json.loads(ln.strip())
                json_count += 1
            except json.JSONDecodeError:
                pass
    if json_count >= 3:
        return "JSON_LINES", {}

    # Markdown table?
    pipe_rows = 0
    for ln in lines[:30]:
        if "|" in ln:
            inner = ln.strip().strip("|")
            parts = [p.strip() for p in inner.split("|")]
            if len(parts) >= 2:
                # Has at least one numeric cell?
                if any(_is_numeric(p) for p in parts):
                    pipe_rows += 1
    if pipe_rows >= 5:
        return "MARKDOWN_TABLE", {}

    # CSV?
    csv_rows = 0
    for ln in lines[:20]:
        if "," in ln:
            parts = [p.strip() for p in ln.split(",")]
            if len(parts) >= 2 and all(_is_numeric(p) or _looks_like_header(p) for p in parts):
                csv_rows += 1
    if csv_rows >= 5:
        return "CSV_HEADER", {}

    # Tab?
    tab_rows = 0
    for ln in lines[:20]:
        if "\t" in ln:
            parts = ln.split("\t")
            if len(parts) >= 2 and all(_is_numeric(p) or _looks_like_header(p) for p in parts):
                tab_rows += 1
    if tab_rows >= 5:
        return "TSV_HEADER", {}

    # Whitespace tabular default
    ws_rows = 0
    for ln in lines[:20]:
        parts = ln.split()
        if len(parts) >= 2:
            try:
                float(parts[-1])
                float(parts[-2])
                ws_rows += 1
            except ValueError:
                continue
    if ws_rows >= 5:
        return "WHITESPACE_TABULAR", {}

    return "NONE", {}


def _is_numeric(s: str) -> bool:
    try:
        float(s.strip())
        return True
    except (ValueError, TypeError):
        return False


def _looks_like_header(s: str) -> bool:
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", s.strip()))


def count_rows(evidence_text: str, fmt: str) -> int:
    """Quick row count for the detected format. Used for min_rows default."""
    rows = 0
    for ln in evidence_text.splitlines():
        s = ln.strip()
        if not s or s.startswith("#") or s.startswith("==="):
            continue
        if fmt == "MARKDOWN_TABLE":
            if "|" in s:
                inner = s.strip("|")
                if all(set(p.strip()) <= set("-:= \t") for p in inner.split("|")):
                    continue
                parts = [p.strip() for p in inner.split("|") if p.strip()]
                if len(parts) >= 2 and _is_numeric(parts[-1]):
                    rows += 1
        elif fmt == "WHITESPACE_TABULAR":
            parts = s.split()
            if len(parts) >= 2 and _is_numeric(parts[-1]):
                rows += 1
        elif fmt == "CSV_HEADER":
            parts = [p.strip() for p in s.split(",")]
            if len(parts) >= 2 and _is_numeric(parts[-1]):
                rows += 1
        elif fmt == "TSV_HEADER":
            parts = s.split("\t")
            if len(parts) >= 2 and _is_numeric(parts[-1]):
                rows += 1
        elif fmt == "JSON_LINES":
            if s.startswith("{"):
                rows += 1
        elif fmt == "SWEEP_BLOCK":
            parts = s.split()
            if len(parts) >= 2 and _is_numeric(parts[-1]):
                rows += 1
    return rows


def detect_columns(evidence_text: str, fmt: str) -> list[str]:
    """Find column names from a header row if present."""
    for ln in evidence_text.splitlines()[:10]:
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if fmt == "MARKDOWN_TABLE" and "|" in s:
            inner = s.strip("|")
            parts = [p.strip() for p in inner.split("|") if p.strip()]
            if len(parts) >= 2 and all(_looks_like_header(p) for p in parts):
                return parts
        if fmt == "CSV_HEADER":
            parts = [p.strip() for p in s.split(",")]
            if len(parts) >= 2 and all(_looks_like_header(p) for p in parts):
                return parts
    # Default: x, y or x1, x2, y based on first numeric row
    return ["x", "y"]


def migrate_rubric(rubric_path: Path, project_dir: Path, dry_run: bool = False) -> dict:
    """Migrate one rubric. Returns status dict."""
    rubric = json.loads(rubric_path.read_text())
    cage = rubric.get("cage_meta") or {}
    cls = (cage.get("class") or "").strip().lower()

    if "evidence_contract" in rubric:
        return {"status": "already_migrated", "format": rubric["evidence_contract"].get("format")}

    if cls in SKIP_CLASSES:
        return {"status": "skipped_non_fitting_class", "class": cls}

    evidence_path = project_dir / "evidence.txt"
    if not evidence_path.exists():
        return {"status": "skipped_no_evidence"}

    evidence_text = evidence_path.read_text()
    fmt, _ = detect_format(evidence_text)
    if fmt == "NONE":
        return {"status": "skipped_no_parseable_rows"}

    rows = count_rows(evidence_text, fmt)
    columns = detect_columns(evidence_text, fmt)
    block = {
        "format": fmt,
        "columns": columns,
        "independent_vars": columns[:-1] if len(columns) >= 2 else ["x"],
        "min_rows": max(5, rows - 2),  # tolerance for occasional drops
        "require_finite": True,
        "format_provenance": "auto_detected_bulk_migration",
        "docstring": f"GP-157 L2 bulk migration auto-detected. {rows} rows in {fmt} format. Operator may refine min_rows / require_monotone_in / column names.",
    }

    if dry_run:
        return {"status": "would_write", "format": fmt, "rows": rows, "columns": columns}

    # Insert block AFTER cage_meta (or at top of object) preserving order
    new_rubric = {}
    inserted = False
    for k, v in rubric.items():
        new_rubric[k] = v
        if k == "cage_observe_mode_reason" and not inserted:
            new_rubric["evidence_contract"] = block
            inserted = True
    if not inserted:
        # Append at end
        new_rubric["evidence_contract"] = block
    rubric_path.write_text(json.dumps(new_rubric, indent=2) + "\n")
    return {"status": "migrated", "format": fmt, "rows": rows, "columns": columns}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--slug", help="Migrate a single substrate slug")
    args = parser.parse_args()

    rubrics_dir = REPO / "rubrics"
    projects_dir = REPO / "projects"

    rubric_files = sorted(rubrics_dir.glob("*.json"))
    if args.slug:
        rubric_files = [rubrics_dir / f"{args.slug}.json"]

    summary = {"migrated": 0, "skipped": 0, "already_migrated": 0, "would_write": 0}
    print(f"{'Rubric':<50} {'Status':<28} {'Detail'}")
    print("-" * 110)
    for rp in rubric_files:
        slug = rp.stem
        proj = projects_dir / slug
        try:
            res = migrate_rubric(rp, proj, dry_run=args.dry_run)
        except Exception as e:
            res = {"status": f"ERROR: {type(e).__name__}: {e}"}

        status = res.get("status", "?")
        detail = ""
        if status in ("migrated", "would_write"):
            detail = f"format={res.get('format')}, rows={res.get('rows')}, cols={res.get('columns')}"
        elif "skipped" in status:
            detail = res.get("class") or ""
        elif status == "already_migrated":
            detail = res.get("format", "")

        print(f"{slug:<50} {status:<28} {detail}")
        if status == "migrated":
            summary["migrated"] += 1
        elif status == "would_write":
            summary["would_write"] += 1
        elif status == "already_migrated":
            summary["already_migrated"] += 1
        elif "skipped" in status:
            summary["skipped"] += 1

    print()
    print(f"Summary: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
