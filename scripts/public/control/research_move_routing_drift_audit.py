#!/usr/bin/env python3
"""Audit research-move routing ownership.

The failure this catches is concrete: a new move gets added as another local
phrase list in an orchestration/checking layer, so semantic routing and primitive
surfacing never see it. New move recognition belongs in operator cards or
primitive-amnesia metadata; action contracts and briefs should consume those
surfaces.
"""
from __future__ import annotations

import argparse
import ast
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable


REPO = Path(__file__).resolve().parents[3]
PATTERN_ACTION_CONTRACT = REPO / "src/ztare/research_director/pattern_action_contract.py"
RD_TICK_BRIEF = REPO / "scripts/public/control/rd_tick_brief.py"
PRIMITIVE_AMNESIA = REPO / "src/ztare/research_director/primitive_amnesia.py"
PRIMITIVE_OPERATOR_CARDS = REPO / "src/ztare/research_director/primitive_operator_cards.py"

REQUIRED_OPERATOR_CARD_IDS = frozenset(
    {
        "OP-HRD-01",
        "OP-PDE-01",
    }
)

REQUIRED_PRIMITIVE_MODULES = frozenset(
    {
        "src/ztare/common/graph_carrier.py",
        "src/ztare/workspace/source_freshness.py",
    }
)

REQUIRED_WHEN_TO_USE_KEYS = frozenset(
    {
        "artifact_source_freshness",
        "canonical_graph_kind_specs",
        "raw_relative_path",
        "validate_graph_carrier",
    }
)


@dataclass
class AuditResult:
    ok: bool
    findings: list[str] = field(default_factory=list)
    advisories: list[str] = field(default_factory=list)
    metrics: dict[str, int | list[str]] = field(default_factory=dict)


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _string_literals(node: ast.AST) -> list[str] | None:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        values: list[str] = []
        for item in node.elts:
            if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
                return None
            values.append(item.value)
        return values
    return None


def _top_level_route_lists(path: Path) -> dict[str, list[str]]:
    tree = _parse(path)
    constants: dict[str, list[str]] = {}
    for stmt in tree.body:
        targets: list[ast.expr] = []
        value: ast.AST | None = None
        if isinstance(stmt, ast.Assign):
            targets = list(stmt.targets)
            value = stmt.value
        elif isinstance(stmt, ast.AnnAssign) and stmt.target is not None:
            targets = [stmt.target]
            value = stmt.value
        if value is None:
            continue
        for target in targets:
            if not isinstance(target, ast.Name):
                continue
            name = target.id
            if not (name.endswith("_TOKENS") or name.endswith("_PHRASES")):
                continue
            strings = _string_literals(value)
            if strings is not None:
                constants[name] = strings
    return constants


def _operator_card_ids(path: Path) -> set[str]:
    tree = _parse(path)
    card_ids: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        called = ""
        if isinstance(func, ast.Name):
            called = func.id
        elif isinstance(func, ast.Attribute):
            called = func.attr
        if called != "OperatorCard":
            continue
        for keyword in node.keywords:
            if (
                keyword.arg == "card_id"
                and isinstance(keyword.value, ast.Constant)
                and isinstance(keyword.value.value, str)
            ):
                card_ids.add(keyword.value.value)
    return card_ids


def _direct_call_lines(path: Path, function_name: str) -> list[int]:
    tree = _parse(path)
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        called = ""
        if isinstance(func, ast.Name):
            called = func.id
        elif isinstance(func, ast.Attribute):
            called = func.attr
        if called == function_name:
            lines.append(getattr(node, "lineno", 0))
    return sorted(line for line in lines if line > 0)


def _matched_terms_gate_lines(path: Path) -> list[int]:
    tree = _parse(path)
    lines: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "matched_terms":
            lines.append(getattr(node, "lineno", 0))
        if (
            isinstance(node, ast.Constant)
            and node.value == "matched_terms"
        ):
            lines.append(getattr(node, "lineno", 0))
    return sorted({line for line in lines if line > 0})


def _list_assignment_values(path: Path, name: str) -> list[str]:
    tree = _parse(path)
    for stmt in tree.body:
        if not isinstance(stmt, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == name for target in stmt.targets):
            continue
        values = _string_literals(stmt.value)
        return values or []
    return []


def _dict_literal_keys(path: Path, name: str) -> set[str]:
    tree = _parse(path)
    for stmt in tree.body:
        if not isinstance(stmt, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == name for target in stmt.targets):
            continue
        if not isinstance(stmt.value, ast.Dict):
            return set()
        keys: set[str] = set()
        for key in stmt.value.keys:
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                keys.add(key.value)
        return keys
    return set()


def _format_relative(path: Path, line: int | None = None) -> str:
    try:
        rel = path.relative_to(REPO)
    except ValueError:
        rel = path
    return f"{rel}:{line}" if line else str(rel)


def audit(
    *,
    pattern_action_contract: Path = PATTERN_ACTION_CONTRACT,
    rd_tick_brief: Path = RD_TICK_BRIEF,
    primitive_amnesia: Path = PRIMITIVE_AMNESIA,
    primitive_operator_cards: Path = PRIMITIVE_OPERATOR_CARDS,
) -> AuditResult:
    findings: list[str] = []
    advisories: list[str] = []

    route_lists = _top_level_route_lists(pattern_action_contract)
    if route_lists:
        findings.append(
            "pattern_action_contract.py owns top-level route lists in "
            f"{_format_relative(pattern_action_contract)}: {', '.join(sorted(route_lists))}. "
            "Put move recognition in primitive_operator_cards.py or primitive_amnesia metadata."
        )
    matched_term_lines = _matched_terms_gate_lines(pattern_action_contract)
    if matched_term_lines:
        findings.append(
            "pattern_action_contract.py branches on operator-card matched_terms at "
            + ", ".join(_format_relative(pattern_action_contract, line) for line in matched_term_lines)
            + "; matched terms are provenance only. Branch on routed card ids or typed receipt fields."
        )

    operator_card_ids = _operator_card_ids(primitive_operator_cards)
    missing_operator_cards = sorted(REQUIRED_OPERATOR_CARD_IDS - operator_card_ids)
    if missing_operator_cards:
        findings.append(
            "primitive_operator_cards.py is missing required route-owner cards: "
            + ", ".join(missing_operator_cards)
        )

    direct_brief_calls = _direct_call_lines(rd_tick_brief, "route_operator_cards")
    if direct_brief_calls:
        findings.append(
            "rd_tick_brief.py calls route_operator_cards directly at "
            + ", ".join(_format_relative(rd_tick_brief, line) for line in direct_brief_calls)
            + "; use route_operator_cards_semantic so embedding-backed routing can participate."
        )

    primitive_modules = set(_list_assignment_values(primitive_amnesia, "PRIMITIVE_MODULES"))
    missing_modules = sorted(REQUIRED_PRIMITIVE_MODULES - primitive_modules)
    if missing_modules:
        findings.append(
            "primitive_amnesia.PRIMITIVE_MODULES is missing common primitives: "
            + ", ".join(missing_modules)
        )

    when_to_use_keys = _dict_literal_keys(primitive_amnesia, "WHEN_TO_USE")
    missing_aliases = sorted(REQUIRED_WHEN_TO_USE_KEYS - when_to_use_keys)
    if missing_aliases:
        findings.append(
            "primitive_amnesia.WHEN_TO_USE is missing graph primitive aliases: "
            + ", ".join(missing_aliases)
        )

    metrics: dict[str, int | list[str]] = {
        "pattern_contract_route_lists": len(route_lists),
        "pattern_contract_route_list_names": sorted(route_lists),
        "pattern_contract_matched_terms_gate_lines": matched_term_lines,
        "required_operator_cards_present": len(REQUIRED_OPERATOR_CARD_IDS - set(missing_operator_cards)),
        "missing_required_operator_cards": missing_operator_cards,
        "rd_tick_brief_direct_route_operator_cards_calls": len(direct_brief_calls),
        "required_primitive_modules_present": len(REQUIRED_PRIMITIVE_MODULES - set(missing_modules)),
        "required_when_to_use_keys_present": len(REQUIRED_WHEN_TO_USE_KEYS - set(missing_aliases)),
    }
    return AuditResult(ok=not findings, findings=findings, advisories=advisories, metrics=metrics)


def render(result: AuditResult) -> str:
    lines = ["research_move_routing_drift_audit: " + ("PASS" if result.ok else "FAIL")]
    for finding in result.findings:
        lines.append(f"  FINDING: {finding}")
    for advisory in result.advisories:
        lines.append(f"  advisory: {advisory}")
    lines.append(f"  metrics: {result.metrics}")
    return "\n".join(lines)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--pattern-action-contract", type=Path, default=PATTERN_ACTION_CONTRACT)
    parser.add_argument("--rd-tick-brief", type=Path, default=RD_TICK_BRIEF)
    parser.add_argument("--primitive-amnesia", type=Path, default=PRIMITIVE_AMNESIA)
    parser.add_argument("--primitive-operator-cards", type=Path, default=PRIMITIVE_OPERATOR_CARDS)
    args = parser.parse_args(list(argv) if argv is not None else None)

    result = audit(
        pattern_action_contract=args.pattern_action_contract,
        rd_tick_brief=args.rd_tick_brief,
        primitive_amnesia=args.primitive_amnesia,
        primitive_operator_cards=args.primitive_operator_cards,
    )
    if args.json:
        print(json.dumps(asdict(result), indent=2, sort_keys=True))
    else:
        print(render(result))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
