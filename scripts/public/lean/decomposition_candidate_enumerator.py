#!/usr/bin/env python3
"""Enumerate Lean source candidates that may decompose a structure field.

This is a lightweight source probe, not a Lean elaborator.  Given a Lean file,
structure name, and field name, it extracts the field type and searches Lean
sources for declarations whose nearby signature text mentions either the field
type head or the field name.  The output is intended to make "try to
decompose this endpoint field" falsifiable before more routing edits are made.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
DEFAULT_LEAN_ROOT = REPO / "ztare_proofs" / "ZtareProofs"


def strip_comments(text: str) -> str:
    chars = list(text)
    i = 0
    depth = 0
    while i < len(chars):
        if depth == 0 and i + 1 < len(chars) and chars[i] == "-" and chars[i + 1] == "-":
            chars[i] = " "
            chars[i + 1] = " "
            i += 2
            while i < len(chars) and chars[i] != "\n":
                chars[i] = " "
                i += 1
            continue
        if i + 1 < len(chars) and chars[i] == "/" and chars[i + 1] == "-":
            depth += 1
            chars[i] = " "
            chars[i + 1] = " "
            i += 2
            continue
        if depth > 0:
            if i + 1 < len(chars) and chars[i] == "-" and chars[i + 1] == "/":
                depth -= 1
                chars[i] = " "
                chars[i + 1] = " "
                i += 2
                continue
            if chars[i] != "\n":
                chars[i] = " "
            i += 1
            continue
        i += 1
    return "".join(chars)


def parse_structure_fields(file_text: str, struct_name: str) -> list[dict[str, str]]:
    cleaned = strip_comments(file_text)
    lines = cleaned.splitlines()
    struct_pat = re.compile(rf"^(\s*)structure\s+{re.escape(struct_name)}\b")
    where_line_idx: int | None = None
    struct_indent = 0
    for i, line in enumerate(lines):
        match = struct_pat.match(line)
        if not match:
            continue
        struct_indent = len(match.group(1))
        for j in range(i, min(i + 12, len(lines))):
            if re.search(r"\bwhere\b", lines[j]):
                where_line_idx = j
                break
        break
    if where_line_idx is None:
        return []

    body_lines: list[str] = []
    for line in lines[where_line_idx + 1:]:
        if not line.strip():
            body_lines.append("")
            continue
        indent = len(line) - len(line.lstrip())
        if indent <= struct_indent:
            break
        body_lines.append(line)

    fields: list[dict[str, str]] = []
    current_name: str | None = None
    current_type_parts: list[str] = []
    field_indent: int | None = None
    for line in body_lines:
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_']*)\s*:\s*(.*)$", stripped)
        if match and (field_indent is None or indent == field_indent):
            if current_name:
                fields.append({"name": current_name, "type": " ".join(current_type_parts).strip()})
            field_indent = indent
            current_name = match.group(1)
            current_type_parts = [match.group(2)]
            continue
        if current_name and indent > (field_indent or 0):
            current_type_parts.append(stripped)
    if current_name:
        fields.append({"name": current_name, "type": " ".join(current_type_parts).strip()})
    return fields


def type_heads(field_type: str) -> list[str]:
    heads = []
    for token in re.findall(r"\b[A-Z][A-Za-z0-9_']+\b", field_type):
        if token not in heads:
            heads.append(token)
    return heads


def declaration_windows(path: Path, text: str, window_lines: int) -> list[dict[str, Any]]:
    lines = text.splitlines()
    decl_pat = re.compile(r"^\s*(?:noncomputable\s+)?(?:def|theorem|lemma|structure|class|inductive)\s+([A-Za-z_][A-Za-z0-9_'.]*)\b")
    windows = []
    for idx, line in enumerate(lines):
        match = decl_pat.match(line)
        if not match:
            continue
        end = min(len(lines), idx + window_lines)
        windows.append({
            "name": match.group(1),
            "line": idx + 1,
            "path": str(path.relative_to(REPO)),
            "kind_line": line.strip(),
            "window": "\n".join(lines[idx:end]),
        })
    return windows


def enumerate_candidates(
    source_file: Path,
    structure: str,
    field: str,
    lean_root: Path,
    max_results: int,
    window_lines: int,
) -> dict[str, Any]:
    source_text = source_file.read_text(errors="ignore")
    fields = parse_structure_fields(source_text, structure)
    field_info = next((item for item in fields if item["name"] == field), None)
    if field_info is None:
        return {
            "status": "field_not_found",
            "source_file": str(source_file.relative_to(REPO)),
            "structure": structure,
            "field": field,
            "fields_seen": fields,
            "candidates": [],
        }

    heads = type_heads(field_info["type"])
    needles = [field, *heads]
    candidates: list[dict[str, Any]] = []
    for path in sorted(lean_root.glob("*.lean")):
        text = strip_comments(path.read_text(errors="ignore"))
        for window in declaration_windows(path, text, window_lines):
            haystack = window["window"]
            hits = [needle for needle in needles if needle and needle in haystack]
            if not hits:
                continue
            score = len(set(hits))
            if "def " in window["kind_line"] and any(head in window["kind_line"] for head in heads):
                score += 2
            if any(head in window["name"] for head in heads):
                score += 1
            candidates.append({
                "name": window["name"],
                "path": window["path"],
                "line": window["line"],
                "score": score,
                "hits": sorted(set(hits)),
                "signature_preview": " ".join(window["window"].split())[:500],
            })
    candidates.sort(key=lambda item: (-item["score"], item["path"], item["line"]))
    return {
        "status": "ok",
        "source_file": str(source_file.relative_to(REPO)),
        "structure": structure,
        "field": field,
        "field_type": field_info["type"],
        "field_type_heads": heads,
        "candidate_count": len(candidates),
        "candidates": candidates[:max_results],
    }


def infer_source_and_structure(lean_root: Path, field: str) -> tuple[Path, str] | None:
    matches: list[tuple[Path, str]] = []
    struct_pat = re.compile(r"^\s*structure\s+([A-Za-z_][A-Za-z0-9_']*)\b")
    for path in sorted(lean_root.glob("*.lean")):
        text = path.read_text(errors="ignore")
        cleaned = strip_comments(text)
        for match in struct_pat.finditer(cleaned):
            struct_name = match.group(1)
            fields = parse_structure_fields(cleaned, struct_name)
            if any(item["name"] == field for item in fields):
                matches.append((path, struct_name))
    if len(matches) == 1:
        return matches[0]
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_file", nargs="?", type=Path)
    parser.add_argument("structure", nargs="?")
    parser.add_argument("field_positional", nargs="?")
    parser.add_argument("--field", dest="field_flag")
    parser.add_argument("--lean-root", type=Path, default=DEFAULT_LEAN_ROOT)
    parser.add_argument("--max-results", type=int, default=25)
    parser.add_argument("--window-lines", type=int, default=28)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--logfile", type=Path)
    args = parser.parse_args()

    if args.source_file is None or args.structure is None:
        inferred = infer_source_and_structure(
            args.lean_root if args.lean_root.is_absolute() else (REPO / args.lean_root).resolve(),
            args.field_flag or args.field_positional or "",
        )
        if inferred is None:
            parser.error("source_file and structure are required unless --field resolves to one unique structure field")
        args.source_file, args.structure = inferred
    field = args.field_flag or args.field_positional
    if not field:
        parser.error("field is required")
    source_file = args.source_file
    if not source_file.is_absolute():
        source_file = (REPO / source_file).resolve()
    lean_root = args.lean_root if args.lean_root.is_absolute() else (REPO / args.lean_root).resolve()
    result = enumerate_candidates(
        source_file,
        args.structure,
        field,
        lean_root,
        args.max_results,
        args.window_lines,
    )
    output = json.dumps(result, indent=2, sort_keys=True) if args.json else render_text(result)
    if args.logfile:
        log_path = args.logfile if args.logfile.is_absolute() else (REPO / args.logfile)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(output)
    print(output)
    return 0 if result.get("status") == "ok" else 1


def render_text(result: dict[str, Any]) -> str:
    if result.get("status") != "ok":
        return json.dumps(result, indent=2, sort_keys=True)
    lines = [
        f"# Decomposition Candidates: {result['structure']}.{result['field']}",
        "",
        f"- Source file: `{result['source_file']}`",
        f"- Field type: `{result['field_type']}`",
        f"- Field type heads: {', '.join(result['field_type_heads']) or 'none'}",
        f"- Candidates found: {result['candidate_count']}",
        "",
    ]
    for idx, candidate in enumerate(result["candidates"], 1):
        lines.append(
            f"{idx}. `{candidate['name']}` at `{candidate['path']}:{candidate['line']}` "
            f"(score={candidate['score']}, hits={', '.join(candidate['hits'])})"
        )
        lines.append(f"   {candidate['signature_preview']}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
