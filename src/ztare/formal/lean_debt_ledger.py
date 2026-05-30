"""Generate a machine-readable Lean trust-footprint ledger.

This scanner is intentionally syntactic. It strips comments and strings while
preserving line positions, then records explicit declarations, executable proof
gaps (`axiom`, `opaque`, `unsafe`, `partial`, `constant`, `sorry`, `admit`),
and proposition-bearing interface fields inside `structure`/`class` blocks. It
does not certify theorem dependencies or mathematical truth.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable


DECLARATION_PATTERNS = {
    "axiom": re.compile(r"^[ \t]*axiom\s+([^\s:]+)", re.M),
    "opaque": re.compile(r"^[ \t]*opaque\s+([^\s:]+)", re.M),
    "unsafe": re.compile(r"^[ \t]*unsafe\s+([^\s:]+)", re.M),
    "partial": re.compile(r"^[ \t]*partial\s+([^\s:]+)", re.M),
    "constant": re.compile(r"^[ \t]*constant\s+([^\s:]+)", re.M),
}

OWNER_START_PATTERN = re.compile(r"^[ \t]*(structure|class)\s+([^\s:{(]+)")
TOP_LEVEL_PATTERN = re.compile(
    r"^(?:def|theorem|lemma|example|instance|abbrev|inductive|structure|class|"
    r"axiom|opaque|constant|namespace|section|end)\b"
)
FIELD_PATTERN = re.compile(r"^[ \t]*([A-Za-z_][A-Za-z0-9_'!?]*)\s*:\s*(.+)$")
PROOF_FIELD_NAME_PARTS = (
    "assumption",
    "certificate",
    "cert",
    "evidence",
    "holds",
    "hyp",
    "obligation",
    "proof",
    "receipt",
    "source",
    "witness",
)


@dataclass(frozen=True)
class DebtRow:
    kind: str
    file: str
    line: int
    name: str | None
    context: str
    suggested_bucket: str


@dataclass(frozen=True)
class InterfaceDebtRow:
    kind: str
    file: str
    line: int
    owner: str
    field: str
    field_type: str
    context: str
    suggested_bucket: str


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


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _context(raw_lines: list[str], line: int, radius: int = 2) -> str:
    start = max(1, line - radius)
    end = min(len(raw_lines), line + radius)
    rows = []
    for idx in range(start, end + 1):
        rows.append(f"{idx}: {raw_lines[idx - 1].rstrip()}")
    return "\n".join(rows)


def suggest_bucket(kind: str, path: str, name: str | None, context: str) -> str:
    """Conservative first-pass classification for triage, not a verdict."""
    hay = f"{path}\n{name or ''}\n{context}".lower()
    if kind in {"sorry", "admit"}:
        if "blocked" in hay or "clay" in hay or "bkm" in hay or "constantin" in hay:
            return "analytic_or_clay_adjacent_gap"
        if "todo" in hay or "plumbing" in hay or "mechanical" in hay:
            return "candidate_local_plumbing_gap"
        return "unclassified_proof_gap"
    if kind in {"axiom", "constant"}:
        if "bkm" in hay or "serrin" in hay or "constantin" in hay or "fefferman" in hay:
            return "named_analytic_assumption"
        if "nonempty" in hay or "inhabited" in hay:
            return "structural_nonempty_placeholder"
        return "unclassified_assumption"
    if kind == "opaque":
        if "predicate" in hay or "prop" in hay or "target" in hay:
            return "opaque_predicate_interface"
        return "unclassified_opaque"
    return "unclassified_structural_debt"


def _is_proposition_like_type(field_type: str) -> bool:
    compact = field_type.strip()
    return (
        compact == "Prop"
        or " Prop" in compact
        or compact.startswith("Prop ")
        or compact.startswith("∀")
        or compact.startswith("∃")
        or " → Prop" in compact
        or " -> Prop" in compact
    )


def _proof_named_field_kind(field: str) -> str | None:
    lowered = field.lower()
    if lowered.endswith("_proof") or lowered.endswith("proof"):
        return "proof_named_field"
    if any(part in lowered for part in PROOF_FIELD_NAME_PARTS):
        return "evidence_named_field"
    return None


def _interface_kind(field: str, field_type: str) -> str | None:
    if _is_proposition_like_type(field_type):
        return "prop_field"
    return _proof_named_field_kind(field)


def suggest_interface_bucket(kind: str, owner: str, field: str, field_type: str) -> str:
    hay = f"{owner}\n{field}\n{field_type}".lower()
    if "source" in hay or "receipt" in hay or "certificate" in hay:
        return "assumption_bearing_receipt_interface"
    if kind == "prop_field":
        return "proposition_interface"
    if kind == "proof_named_field":
        return "proof_named_interface"
    return "evidence_named_interface"


def scan_interface_fields(
    stripped: str,
    raw_lines: list[str],
    rel: str,
) -> list[InterfaceDebtRow]:
    rows: list[InterfaceDebtRow] = []
    owner: str | None = None
    for idx, line in enumerate(stripped.splitlines(), start=1):
        owner_match = OWNER_START_PATTERN.match(line)
        if owner_match:
            owner = owner_match.group(2)
            continue

        if owner and line and not line.startswith((" ", "\t", "|")):
            if TOP_LEVEL_PATTERN.match(line):
                owner = None
            continue

        if not owner:
            continue

        stripped_line = line.strip()
        if not stripped_line or stripped_line in {"where", "deriving"}:
            continue
        if stripped_line.startswith(("extends ", "deriving ", "where ")):
            continue

        field_match = FIELD_PATTERN.match(line)
        if not field_match:
            continue
        field = field_match.group(1)
        field_type = field_match.group(2).strip()
        kind = _interface_kind(field, field_type)
        if not kind:
            continue
        rows.append(InterfaceDebtRow(
            kind=kind,
            file=rel,
            line=idx,
            owner=owner,
            field=field,
            field_type=field_type,
            context=_context(raw_lines, idx),
            suggested_bucket=suggest_interface_bucket(kind, owner, field, field_type),
        ))
    return rows


def iter_lean_files(root: Path, glob_pattern: str) -> Iterable[Path]:
    yield from sorted(path for path in root.glob(glob_pattern) if path.is_file())


def scan(root: Path, glob_pattern: str = "**/*.lean", repo_root: Path | None = None) -> dict:
    repo_root = repo_root or root
    files = list(iter_lean_files(root, glob_pattern))
    rows: list[DebtRow] = []
    interface_rows: list[InterfaceDebtRow] = []
    line_count = 0
    for path in files:
        raw = path.read_text(encoding="utf-8", errors="ignore")
        raw_lines = raw.splitlines()
        line_count += raw.count("\n") + 1
        stripped = strip_lean_comments_and_strings(raw)
        rel = str(path.relative_to(repo_root)) if path.is_relative_to(repo_root) else str(path)
        interface_rows.extend(scan_interface_fields(stripped, raw_lines, rel))
        for kind, pattern in DECLARATION_PATTERNS.items():
            for match in pattern.finditer(stripped):
                line = _line_number(stripped, match.start())
                ctx = _context(raw_lines, line)
                name = match.group(1)
                rows.append(DebtRow(
                    kind=kind,
                    file=rel,
                    line=line,
                    name=name,
                    context=ctx,
                    suggested_bucket=suggest_bucket(kind, rel, name, ctx),
                ))
        for kind in ("sorry", "admit"):
            for match in re.finditer(rf"\b{kind}\b", stripped):
                line = _line_number(stripped, match.start())
                ctx = _context(raw_lines, line)
                rows.append(DebtRow(
                    kind=kind,
                    file=rel,
                    line=line,
                    name=None,
                    context=ctx,
                    suggested_bucket=suggest_bucket(kind, rel, None, ctx),
                ))
    rows.sort(key=lambda row: (row.file, row.line, row.kind, row.name or ""))
    interface_rows.sort(key=lambda row: (row.file, row.line, row.owner, row.field))
    counts = Counter(row.kind for row in rows)
    buckets = Counter(row.suggested_bucket for row in rows)
    interface_counts = Counter(row.kind for row in interface_rows)
    interface_buckets = Counter(row.suggested_bucket for row in interface_rows)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "glob": glob_pattern,
        "files": len(files),
        "lines": line_count,
        "counts": dict(sorted(counts.items())),
        "bucket_counts": dict(sorted(buckets.items())),
        "rows": [asdict(row) for row in rows],
        "interface_counts": dict(sorted(interface_counts.items())),
        "interface_bucket_counts": dict(sorted(interface_buckets.items())),
        "interface_rows": [asdict(row) for row in interface_rows],
    }


def write_markdown(payload: dict, path: Path) -> None:
    rows = payload["rows"]
    counts = payload["counts"]
    interface_rows = payload["interface_rows"]
    lines = [
        "# Lean Trust-Footprint Debt Ledger",
        "",
        f"Generated: {payload['generated_at']}",
        f"Root: `{payload['root']}`",
        f"Glob: `{payload['glob']}`",
        f"Files: {payload['files']}",
        f"Lines: {payload['lines']}",
        "",
        "## Counts",
        "",
        "| Kind | Count |",
        "|---|---:|",
    ]
    for kind, count in sorted(counts.items()):
        lines.append(f"| `{kind}` | {count} |")
    lines.extend([
        "",
        "## Bucket Counts",
        "",
        "| Suggested bucket | Count |",
        "|---|---:|",
    ])
    for bucket, count in sorted(payload["bucket_counts"].items()):
        lines.append(f"| `{bucket}` | {count} |")
    lines.extend([
        "",
        "## Interface Counts",
        "",
        "| Kind | Count |",
        "|---|---:|",
    ])
    for kind, count in sorted(payload["interface_counts"].items()):
        lines.append(f"| `{kind}` | {count} |")
    lines.extend([
        "",
        "## Interface Bucket Counts",
        "",
        "| Suggested bucket | Count |",
        "|---|---:|",
    ])
    for bucket, count in sorted(payload["interface_bucket_counts"].items()):
        lines.append(f"| `{bucket}` | {count} |")
    lines.extend([
        "",
        "## Interface Rows",
        "",
        "| Kind | Location | Owner | Field | Suggested bucket |",
        "|---|---|---|---|---|",
    ])
    for row in interface_rows:
        loc = f"{row['file']}:{row['line']}"
        lines.append(
            f"| `{row['kind']}` | `{loc}` | `{row['owner']}` | "
            f"`{row['field']}` | `{row['suggested_bucket']}` |"
        )
    lines.extend([
        "",
        "## Rows",
        "",
        "| Kind | Location | Name | Suggested bucket |",
        "|---|---|---|---|",
    ])
    for row in rows:
        name = row["name"] or ""
        loc = f"{row['file']}:{row['line']}"
        lines.append(
            f"| `{row['kind']}` | `{loc}` | `{name}` | `{row['suggested_bucket']}` |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def self_test() -> None:
    sample = '''import Mathlib

/- comment with sorry and axiom fake : True -/
axiom real_axiom : True
opaque Hidden : Prop
theorem gap : True := by
  -- comment sorry
  sorry
def quoted := "admit axiom opaque sorry"

structure Receipt where
  proof : True
  claim : Prop
  emittedSource : Nat
'''
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        path = root / "Demo.lean"
        path.write_text(sample, encoding="utf-8")
        payload = scan(root, "*.lean", repo_root=root)
    assert payload["counts"] == {"axiom": 1, "opaque": 1, "sorry": 1}, payload
    assert payload["rows"][0]["line"] == 4, payload["rows"]
    assert payload["rows"][2]["line"] == 8, payload["rows"]
    assert payload["interface_counts"] == {
        "evidence_named_field": 1,
        "proof_named_field": 1,
        "prop_field": 1,
    }, payload["interface_rows"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--glob", default="**/*.lean")
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--md-out", type=Path, default=None)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        print("self-test ok")
        return 0

    payload = scan(args.root.resolve(), args.glob, args.repo_root.resolve() if args.repo_root else None)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(payload, args.md_out)
    if not args.json_out and not args.md_out:
        print(json.dumps(payload, indent=2))
    else:
        print(
            "lean debt ledger ok "
            f"files={payload['files']} lines={payload['lines']} counts={payload['counts']} "
            f"interface_counts={payload['interface_counts']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
