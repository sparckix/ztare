"""Measure syntactic fanout for Lean declarations.

This is a conservative planning helper for trust-footprint reduction.  It
counts references to selected declaration names across Lean files while
ignoring comments and strings.  It does not understand namespaces or Lean
elaboration; use it to choose audit targets, not as proof of unused code.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from lean_debt_ledger import strip_lean_comments_and_strings


@dataclass(frozen=True)
class FanoutRow:
    declaration: str
    basename: str
    total_hits: int
    files: int
    definition_hits: int
    non_definition_hits: int
    top_files: list[dict]


def iter_lean_files(root: Path, glob_pattern: str) -> Iterable[Path]:
    yield from sorted(path for path in root.glob(glob_pattern) if path.is_file())


def _basename(declaration: str) -> str:
    return declaration.rsplit(".", 1)[-1]


def _name_pattern(name: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9_'.]){re.escape(name)}(?![A-Za-z0-9_'.])")


def _definition_pattern(name: str) -> re.Pattern[str]:
    return re.compile(
        rf"^[ \t]*(?:def|theorem|lemma|opaque|axiom|constant|structure|class|"
        rf"abbrev|inductive|instance)\s+{re.escape(name)}(?:\s|:|\\.|$)",
        re.M,
    )


def measure_fanout(root: Path, glob_pattern: str, declarations: list[str], repo_root: Path | None = None) -> dict:
    repo_root = repo_root or root
    files = list(iter_lean_files(root, glob_pattern))
    rows: list[FanoutRow] = []
    stripped_by_file: list[tuple[Path, str]] = []
    for path in files:
        stripped_by_file.append((path, strip_lean_comments_and_strings(path.read_text(encoding="utf-8"))))

    for declaration in declarations:
        name = _basename(declaration)
        name_pat = _name_pattern(name)
        def_pat = _definition_pattern(name)
        per_file: Counter[str] = Counter()
        definition_hits = 0
        total_hits = 0
        for path, stripped in stripped_by_file:
            hits = len(name_pat.findall(stripped))
            if not hits:
                continue
            defs = len(def_pat.findall(stripped))
            rel = str(path.relative_to(repo_root))
            per_file[rel] = hits
            definition_hits += defs
            total_hits += hits
        top_files = [
            {"file": file, "hits": hits}
            for file, hits in per_file.most_common(12)
        ]
        rows.append(FanoutRow(
            declaration=declaration,
            basename=name,
            total_hits=total_hits,
            files=len(per_file),
            definition_hits=definition_hits,
            non_definition_hits=max(0, total_hits - definition_hits),
            top_files=top_files,
        ))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "glob": glob_pattern,
        "files_scanned": len(files),
        "rows": [asdict(row) for row in rows],
    }


def write_markdown(payload: dict, path: Path) -> None:
    lines = [
        "# Lean Declaration Fanout",
        "",
        f"Generated: {payload['generated_at']}",
        f"Root: `{payload['root']}`",
        f"Glob: `{payload['glob']}`",
        f"Files scanned: {payload['files_scanned']}",
        "",
        "| Declaration | Hits | Files | Definition hits | Non-definition hits | Top files |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in payload["rows"]:
        top = "; ".join(f"`{item['file']}` ({item['hits']})" for item in row["top_files"][:5])
        lines.append(
            f"| `{row['declaration']}` | {row['total_hits']} | {row['files']} | "
            f"{row['definition_hits']} | {row['non_definition_hits']} | {top} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def self_test() -> None:
    sample = 'opaque Foo : Type\n/-- Foo hidden -/\ndef bar : Foo := by sorry\n"Foo"\n'
    stripped = strip_lean_comments_and_strings(sample)
    assert len(_name_pattern("Foo").findall(stripped)) == 2
    assert len(_definition_pattern("Foo").findall(stripped)) == 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--glob", default="**/*.lean")
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--decl", action="append", default=[])
    parser.add_argument("--decl-file", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--md-out", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        print("self-test ok")
        return 0

    declarations = list(args.decl)
    if args.decl_file:
        declarations.extend(
            line.strip()
            for line in args.decl_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    if not declarations:
        parser.error("provide at least one --decl or --decl-file")

    payload = measure_fanout(args.root, args.glob, declarations, repo_root=args.repo_root or args.root)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(payload, args.md_out)
    if not args.json_out and not args.md_out:
        print(json.dumps(payload, indent=2))
    else:
        max_hits = max((row["total_hits"] for row in payload["rows"]), default=0)
        print(f"lean decl fanout ok decls={len(payload['rows'])} max_hits={max_hits}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
