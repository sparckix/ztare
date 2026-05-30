#!/usr/bin/env python3
"""Classify local Lean declarations for safe retrieval/ranker use.

This is a cheap hygiene pass, not a proof checker.  It separates direct
placeholders (`axiom`, `opaque`, `sorry`/`admit`) from declarations whose body is
present in the file.  The output is intended to stop GNN vocabulary expansion
from treating scaffolding names as if they were verified mathlib-style lemmas.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


DECL_RE = re.compile(
    r"^\s*(?:@[^\n]+\s+)?(?:(?:private|protected|noncomputable|unsafe)\s+)*"
    r"(?P<kind>theorem|lemma|def|abbrev|structure|class|inductive|instance|opaque|axiom)\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_.'!?\u2080-\u209C]*)"
)

BAD_TOKEN_RE = re.compile(r"\b(sorry|admit)\b")


@dataclass
class Declaration:
    name: str
    kind: str
    file: str
    start_line: int
    end_line: int
    has_sorry_or_admit: bool
    is_direct_placeholder: bool
    trusted_for_ranker_vocab: bool
    route: str
    preview: str


def route_for(path: Path) -> str:
    stem = path.stem
    if stem.startswith("ns_"):
        return "navier_stokes"
    if stem.startswith("PR_") or stem.startswith("oeis"):
        return "math_smoke"
    if stem.startswith("batched_"):
        return "generated_batch"
    if stem == "ztareonztare":
        return "ztare_meta"
    return "other"


def iter_declarations(path: Path, root: Path) -> Iterable[Declaration]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    starts: list[tuple[int, re.Match[str]]] = []
    for idx, line in enumerate(lines, start=1):
        match = DECL_RE.match(line)
        if match:
            starts.append((idx, match))

    for pos, (start, match) in enumerate(starts):
        end = starts[pos + 1][0] - 1 if pos + 1 < len(starts) else len(lines)
        body = "\n".join(lines[start - 1 : end])
        kind = match.group("kind")
        name = match.group("name")
        has_bad_token = BAD_TOKEN_RE.search(body) is not None
        is_placeholder = kind in {"axiom", "opaque"}
        trusted = not has_bad_token and not is_placeholder
        preview = " ".join(body.strip().split())[:240]
        yield Declaration(
            name=name,
            kind=kind,
            file=str(path.relative_to(root)),
            start_line=start,
            end_line=end,
            has_sorry_or_admit=has_bad_token,
            is_direct_placeholder=is_placeholder,
            trusted_for_ranker_vocab=trusted,
            route=route_for(path),
            preview=preview,
        )


def build_report(root: Path, out_json: Path, out_md: Path) -> None:
    proof_dir = root / "ztare_proofs" / "ZtareProofs"
    decls: list[Declaration] = []
    for path in sorted(proof_dir.glob("*.lean")):
        decls.extend(iter_declarations(path, root))

    by_kind = Counter(d.kind for d in decls)
    by_route = Counter(d.route for d in decls)
    trusted_by_route = Counter(d.route for d in decls if d.trusted_for_ranker_vocab)
    placeholder_by_route = Counter(d.route for d in decls if not d.trusted_for_ranker_vocab)
    by_file: dict[str, Counter[str]] = defaultdict(Counter)
    for d in decls:
        bucket = "trusted" if d.trusted_for_ranker_vocab else "placeholder_or_sorry"
        by_file[d.file][bucket] += 1
        by_file[d.file]["total"] += 1

    report = {
        "version": "ztare_lean_declaration_hygiene_2026_05_11",
        "root": str(root),
        "proof_dir": str(proof_dir),
        "summary": {
            "declarations": len(decls),
            "trusted_for_ranker_vocab": sum(d.trusted_for_ranker_vocab for d in decls),
            "placeholder_or_sorry": sum(not d.trusted_for_ranker_vocab for d in decls),
            "by_kind": dict(by_kind),
            "by_route": dict(by_route),
            "trusted_by_route": dict(trusted_by_route),
            "placeholder_by_route": dict(placeholder_by_route),
        },
        "by_file": {k: dict(v) for k, v in sorted(by_file.items())},
        "trusted_names": [d.name for d in decls if d.trusted_for_ranker_vocab],
        "blocked_names": [d.name for d in decls if not d.trusted_for_ranker_vocab],
        "declarations": [asdict(d) for d in decls],
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    lines: list[str] = []
    s = report["summary"]
    lines.append("# ZTARE Lean Declaration Hygiene")
    lines.append("")
    lines.append("Status: local static hygiene pass; not a proof checker.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- declarations: `{s['declarations']}`")
    lines.append(f"- trusted for ranker vocab: `{s['trusted_for_ranker_vocab']}`")
    lines.append(f"- blocked placeholder/sorry declarations: `{s['placeholder_or_sorry']}`")
    lines.append("")
    lines.append("## Route Counts")
    lines.append("")
    lines.append("| route | total | trusted | blocked |")
    lines.append("|---|---:|---:|---:|")
    for route in sorted(by_route):
        lines.append(
            f"| {route} | {by_route[route]} | {trusted_by_route[route]} | {placeholder_by_route[route]} |"
        )
    lines.append("")
    lines.append("## Highest Blocked Files")
    lines.append("")
    lines.append("| file | total | trusted | blocked |")
    lines.append("|---|---:|---:|---:|")
    rows = sorted(
        by_file.items(),
        key=lambda kv: (kv[1]["placeholder_or_sorry"], kv[1]["total"]),
        reverse=True,
    )[:25]
    for file, counts in rows:
        lines.append(
            f"| `{file}` | {counts['total']} | {counts['trusted']} | {counts['placeholder_or_sorry']} |"
        )
    lines.append("")
    lines.append("## Use")
    lines.append("")
    lines.append(
        "Use `trusted_names` as the first allowlist for v2.1+ local retrieval tests. "
        "Do not treat this as a final verification certificate; it only blocks direct scaffolding."
    )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path.cwd())
    ap.add_argument(
        "--out-json",
        type=Path,
        default=Path("analytics/public/leanmill/results/ztare_lean_declaration_hygiene.json"),
    )
    ap.add_argument(
        "--out-md",
        type=Path,
        default=Path("analytics/public/leanmill/results/ztare_lean_declaration_hygiene.md"),
    )
    args = ap.parse_args()
    build_report(args.root.resolve(), args.out_json, args.out_md)


if __name__ == "__main__":
    main()
