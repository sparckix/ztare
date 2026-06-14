"""Run Lean `#print axioms` for selected declarations.

This is a general-purpose dependency-footprint helper. It imports one Lean
module, queries one or more declarations, and writes the raw Lean response plus
a conservative parsed axiom list. It is an audit aid, not a proof checker.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory


AXIOM_LIST_PATTERN = re.compile(r"depends on axioms:\s*\[(?P<axioms>[^\]]*)\]", re.S)
NO_AXIOM_PATTERNS = (
    "does not depend on any axioms",
    "doesn't depend on any axioms",
    "depends on no axioms",
)


@dataclass(frozen=True)
class AxiomAuditRow:
    declaration: str
    returncode: int
    axioms: list[str]
    raw_output: str


def parse_axioms(raw_output: str) -> list[str]:
    lowered = raw_output.lower()
    if any(pattern in lowered for pattern in NO_AXIOM_PATTERNS):
        return []
    match = AXIOM_LIST_PATTERN.search(raw_output)
    if not match:
        return []
    return sorted(
        part.strip().strip("'\"")
        for part in match.group("axioms").split(",")
        if part.strip()
    )


def _lean_source(module: str, declaration: str) -> str:
    return f"import {module}\n\n#print axioms {declaration}\n"


def audit_declaration(lake_dir: Path, module: str, declaration: str,
                      timeout_s: "int | None" = None) -> AxiomAuditRow:
    from ztare.common.timeouts import timeout_s as _budget
    budget = int(timeout_s) if timeout_s is not None else _budget("axiom_audit")
    with TemporaryDirectory() as tmp:
        lean_file = Path(tmp) / "AxiomAudit.lean"
        lean_file.write_text(_lean_source(module, declaration), encoding="utf-8")
        try:
            proc = subprocess.run(
                ["lake", "env", "lean", str(lean_file)],
                cwd=lake_dir,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=budget,
            )
        except subprocess.TimeoutExpired:
            # FAIL-CLOSED: a wedged `lake env lean` must NEVER be read as axiom-clean. `parse_axioms` on an
            # empty/partial output returns [] = "no axioms" = clean → a silent ratification of an UNAUDITED
            # closure (the same unbounded-wait class as the REPL hang). Surface a non-zero returncode AND a
            # sentinel axiom so EITHER gate (returncode==0 OR empty-axiom-list) refuses the closure.
            return AxiomAuditRow(
                declaration=declaration, returncode=124,
                axioms=["__axiom_audit_timeout__"],
                raw_output=f"axiom_audit_timeout: `lake env lean` exceeded {budget}s (fail-closed)",
            )
    raw_output = "\n".join(part for part in (proc.stdout, proc.stderr) if part)
    return AxiomAuditRow(
        declaration=declaration,
        returncode=proc.returncode,
        axioms=parse_axioms(raw_output),
        raw_output=raw_output.strip(),
    )


def run_audit(lake_dir: Path, module: str, declarations: list[str]) -> dict:
    rows = [audit_declaration(lake_dir, module, declaration) for declaration in declarations]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lake_dir": str(lake_dir),
        "module": module,
        "rows": [asdict(row) for row in rows],
    }


def write_markdown(payload: dict, path: Path) -> None:
    lines = [
        "# Lean Axiom Dependency Audit",
        "",
        f"Generated: {payload['generated_at']}",
        f"Lake dir: `{payload['lake_dir']}`",
        f"Module: `{payload['module']}`",
        "",
        "| Declaration | Return code | Axiom count | Axioms |",
        "|---|---:|---:|---|",
    ]
    for row in payload["rows"]:
        axioms = ", ".join(f"`{axiom}`" for axiom in row["axioms"])
        lines.append(
            f"| `{row['declaration']}` | {row['returncode']} | "
            f"{len(row['axioms'])} | {axioms} |"
        )
    lines.extend(["", "## Raw Output", ""])
    for row in payload["rows"]:
        lines.extend([
            f"### `{row['declaration']}`",
            "",
            "```text",
            row["raw_output"],
            "```",
            "",
        ])
    path.write_text("\n".join(lines), encoding="utf-8")


def self_test() -> None:
    assert parse_axioms("'foo' depends on axioms: [propext, Classical.choice]") == [
        "Classical.choice",
        "propext",
    ]
    assert parse_axioms("declaration does not depend on any axioms") == []
    assert parse_axioms("unexpected output") == []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lake-dir", type=Path, default=Path("."))
    parser.add_argument("--module", required=False)
    parser.add_argument("--decl", action="append", default=[])
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--md-out", type=Path, default=None)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        print("self-test ok")
        return 0

    if not args.module:
        parser.error("--module is required unless --self-test is used")
    if not args.decl:
        parser.error("at least one --decl is required unless --self-test is used")

    payload = run_audit(args.lake_dir.resolve(), args.module, args.decl)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(payload, args.md_out)
    if not args.json_out and not args.md_out:
        print(json.dumps(payload, indent=2))
    else:
        failed = sum(1 for row in payload["rows"] if row["returncode"] != 0)
        max_axioms = max((len(row["axioms"]) for row in payload["rows"]), default=0)
        print(
            "lean axiom audit ok "
            f"decls={len(payload['rows'])} failed={failed} max_axioms={max_axioms}"
        )
    return 1 if any(row["returncode"] != 0 for row in payload["rows"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
