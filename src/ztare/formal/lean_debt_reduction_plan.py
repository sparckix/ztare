"""Rank Lean proof-debt rows for safe reduction work.

This consumes the JSON emitted by ``lean_debt_ledger.py`` and emits a compact
action plan.  It is intentionally conservative: it does not prove that a row is
safe to edit, and it never rewrites Lean.  Its job is to separate bulk triage
from proof work so raw ``sorry``/``opaque`` counts do not become the objective.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HIGH_RISK_TOKENS = (
    "bkm",
    "blowup",
    "clay",
    "constantin",
    "ess",
    "fefferman",
    "navier",
    "navier-stokes",
    "regularity",
    "serrin",
    "smoothness",
)
SOURCE_SHAPE_TOKENS = (
    "elpnorm",
    "eLpNorm".lower(),
    "memlp",
    "indicator",
    "restrict",
    "finite-integral",
    "integral",
    "vitali",
    "translation",
)
LOCAL_PLUMBING_TOKENS = (
    "simp",
    "rfl",
    "constructor",
    "projection",
    "plumbing",
    "mechanical",
    "unfold",
    "repackage",
)
STRUCTURAL_PLACEHOLDER_TOKENS = (
    "nonempty",
    "inhabited",
    "placeholder",
    "scaffold",
    "abstract",
)


@dataclass(frozen=True)
class PlanRow:
    priority: int
    action_class: str
    risk: str
    kind: str
    file: str
    line: int
    name: str
    bucket: str
    rationale: str
    required_receipts: list[str]
    context_excerpt: str


def _hay(row: dict[str, Any]) -> str:
    return "\n".join(
        str(row.get(key, ""))
        for key in ("kind", "file", "line", "name", "owner", "field", "field_type", "context", "suggested_bucket")
    ).lower()


def _contains_any(hay: str, tokens: tuple[str, ...]) -> bool:
    return any(token.lower() in hay for token in tokens)


def _row_name(row: dict[str, Any]) -> str:
    return str(row.get("name") or row.get("field") or row.get("owner") or "")


def classify_row(row: dict[str, Any]) -> tuple[int, str, str, str, list[str]]:
    """Return priority, action class, risk, rationale, required receipts."""
    hay = _hay(row)
    kind = str(row.get("kind", ""))
    bucket = str(row.get("suggested_bucket", ""))

    receipts = [
        "statement_preservation_or_explicit_theorem_design_note",
        "targeted_lake_env_lean",
        "targeted_lake_build_when_module_owned",
    ]
    if kind in {"sorry", "admit", "axiom", "opaque", "constant"}:
        receipts.append("selected_declaration_axiom_audit")

    if kind in {"sorry", "admit"} and _contains_any(hay, HIGH_RISK_TOKENS):
        return (
            900,
            "defer_analytic_spine",
            "high",
            "Proof gap touches high-risk analytic or problem-facing vocabulary; reduce only by supplying the real mathematical input.",
            receipts + ["pencil_proof", "source_or_estimate_receipt"],
        )
    if kind in {"sorry", "admit"} and (_contains_any(hay, SOURCE_SHAPE_TOKENS) or "candidate_local_plumbing_gap" in bucket):
        return (
            180,
            "source_shape_repair",
            "medium",
            "Potential downstream proof gap, but source currency must be checked before editing.",
            receipts + ["pencil_proof", "proof_state_probe", "no_new_axiom_or_opaque"],
        )
    if kind in {"sorry", "admit"} and _contains_any(hay, LOCAL_PLUMBING_TOKENS):
        return (
            120,
            "candidate_statement_preserving_patch",
            "low_medium",
            "Looks like local proof plumbing; still needs proof-state confirmation and dependency audit.",
            receipts + ["proof_state_probe", "no_statement_weakening", "no_new_axiom_or_opaque"],
        )
    if kind in {"axiom", "constant"} and _contains_any(hay, STRUCTURAL_PLACEHOLDER_TOKENS):
        return (
            260,
            "structural_placeholder_replacement",
            "medium",
            "May be replaceable by an explicit constructor, instance, or theorem parameter, but could affect many dependents.",
            receipts + ["downstream_import_build", "replacement_constructor_or_instance"],
        )
    if kind == "opaque" and ("predicate" in hay or "prop" in hay or "interface" in hay):
        return (
            320,
            "opaque_interface_demolition",
            "medium_high",
            "Opaque interface likely needs transparent structure/theorem replacement and downstream migration.",
            receipts + ["dependency_fanout_check", "transparent_replacement", "downstream_import_build"],
        )
    if kind in {"prop_field", "proof_named_field", "evidence_named_field"}:
        return (
            420,
            "interface_assumption_demote",
            "medium_high",
            "Interface field is assumption-bearing; reduce by deriving it from constructors or moving it to an explicit theorem dependency.",
            ["owner_constructor_audit", "downstream_usage_audit", "statement_boundary_note"],
        )
    if kind in {"axiom", "constant"} and _contains_any(hay, HIGH_RISK_TOKENS):
        return (
            930,
            "defer_analytic_assumption",
            "high",
            "Named analytic assumption; do not replace with packaging unless the analytic theorem is actually proved.",
            receipts + ["external_theorem_or_estimate_receipt"],
        )
    if kind == "opaque":
        return (
            520,
            "opaque_triage_needed",
            "medium",
            "Opaque declaration needs fanout and statement audit before deciding whether it is packaging or analytic debt.",
            receipts + ["dependency_fanout_check"],
        )
    return (
        650,
        "manual_triage",
        "unknown",
        "Insufficient signal for bulk classification.",
        receipts,
    )


def build_plan(ledger: dict[str, Any], include_interfaces: bool, limit: int | None) -> dict[str, Any]:
    source_rows = list(ledger.get("rows", []))
    rows = source_rows + (list(ledger.get("interface_rows", [])) if include_interfaces else [])
    plan_rows: list[PlanRow] = []
    for row in rows:
        priority, action_class, risk, rationale, receipts = classify_row(row)
        plan_rows.append(PlanRow(
            priority=priority,
            action_class=action_class,
            risk=risk,
            kind=str(row.get("kind", "")),
            file=str(row.get("file", "")),
            line=int(row.get("line", 0) or 0),
            name=_row_name(row),
            bucket=str(row.get("suggested_bucket", "")),
            rationale=rationale,
            required_receipts=receipts,
            context_excerpt=str(row.get("context", "")).splitlines()[0:5] and "\n".join(str(row.get("context", "")).splitlines()[0:5]) or "",
        ))
    plan_rows.sort(key=lambda row: (row.priority, row.file, row.line, row.name))
    if limit is not None:
        plan_rows = plan_rows[:limit]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ledger_generated_at": ledger.get("generated_at"),
        "source_rows": len(source_rows),
        "interface_rows_included": include_interfaces,
        "rows": [asdict(row) for row in plan_rows],
        "action_counts": dict(Counter(row.action_class for row in plan_rows)),
        "risk_counts": dict(Counter(row.risk for row in plan_rows)),
    }


def write_markdown(plan: dict[str, Any], path: Path) -> None:
    lines = [
        "# Lean Debt Reduction Plan",
        "",
        f"Generated: {plan['generated_at']}",
        f"Ledger generated: {plan.get('ledger_generated_at')}",
        f"Rows shown: {len(plan['rows'])}",
        f"Interface rows included: {plan['interface_rows_included']}",
        "",
        "## Action Counts",
        "",
        "| Action class | Count |",
        "|---|---:|",
    ]
    for action, count in sorted(plan["action_counts"].items()):
        lines.append(f"| `{action}` | {count} |")
    lines.extend([
        "",
        "## Ranked Rows",
        "",
        "| Priority | Action | Risk | Kind | Location | Name | Required receipts |",
        "|---:|---|---|---|---|---|---|",
    ])
    for row in plan["rows"]:
        receipts = ", ".join(f"`{item}`" for item in row["required_receipts"])
        location = f"`{row['file']}:{row['line']}`"
        lines.append(
            f"| {row['priority']} | `{row['action_class']}` | `{row['risk']}` | "
            f"`{row['kind']}` | {location} | `{row['name']}` | {receipts} |"
        )
    lines.extend(["", "## Notes", ""])
    lines.append("This is a triage artifact, not permission to edit blindly. Every patch still needs the listed receipts.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def self_test() -> None:
    row = {
        "kind": "sorry",
        "file": "Foo.lean",
        "line": 10,
        "name": "bar",
        "context": "TODO plumbing by simp",
        "suggested_bucket": "candidate_local_plumbing_gap",
    }
    priority, action, risk, _, receipts = classify_row(row)
    assert priority < 250
    assert action == "source_shape_repair"
    assert risk == "medium"
    assert "proof_state_probe" in receipts
    high = {**row, "context": "Clay BKM regularity theorem"}
    assert classify_row(high)[1] == "defer_analytic_spine"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=False)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--md-out", type=Path)
    parser.add_argument("--include-interfaces", action="store_true")
    parser.add_argument("--limit", type=int, default=80)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        print("self-test ok")
        return 0
    if not args.ledger:
        parser.error("--ledger is required unless --self-test is used")

    ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
    plan = build_plan(ledger, include_interfaces=args.include_interfaces, limit=args.limit)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(plan, args.md_out)
    if not args.json_out and not args.md_out:
        print(json.dumps(plan, indent=2))
    else:
        print(
            "lean debt reduction plan ok "
            f"rows={len(plan['rows'])} actions={plan['action_counts']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
