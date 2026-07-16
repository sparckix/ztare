#!/usr/bin/env python3
"""Validate autoresearch-adjacent LLM dispatch boundaries.

The invariant is small:
- main mutator/judge/committee may keep direct API fallback calls, but only
  inside their dispatch-covered safe wrappers;
- the out-of-loop judge may keep its dedicated API function because the module
  also owns a subscription transport;
- all other autoresearch-adjacent LLM calls should go through
  ``dispatch_call_text`` so subscription CLI transport can be enabled with a
  scoped environment variable.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
SCAN_GLOBS = (
    "src/ztare/validator/*.py",
    "src/ztare/orchestrator/*.py",
)
SCAN_FILES = (
    "src/ztare/rubrics/review_rubric.py",
    "src/ztare/fit/cold_llm_erdos_seed.py",
    "src/ztare/fit/analogy.py",
    "src/ztare/research_director/eigenquestion_generator.py",
    "src/ztare/research_director/primitive_amnesia.py",
    "src/ztare/research_director/substrate_recommender.py",
)
ALLOWED_DIRECT = {
    ("src/ztare/validator/autoresearch_loop.py", "safe_mutate"): "dispatch-covered mutator fallback",
    ("src/ztare/validator/test_thesis.py", "safe_generate"): "dispatch-covered judge fallback",
    ("src/ztare/validator/generate_committee.py", "safe_generate_committee"): "dispatch-covered committee fallback",
    ("src/ztare/validator/judge_out_of_loop.py", "_llm_api"): "dedicated out-of-loop dual transport",
}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    function: str
    kind: str
    detail: str


@dataclass(frozen=True)
class DispatchSite:
    path: str
    line: int
    function: str
    call_site: str


class _Visitor(ast.NodeVisitor):
    def __init__(self, source: str, path: str) -> None:
        self.source = source
        self.path = path
        self.stack: list[str] = []
        self.parent_stack: list[ast.AST] = []
        self.findings: list[Finding] = []
        self.dispatch_sites: list[DispatchSite] = []

    def visit(self, node: ast.AST) -> None:  # type: ignore[override]
        self.parent_stack.append(node)
        try:
            super().visit(node)
        finally:
            self.parent_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)  # type: ignore[arg-type]

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        function = ".".join(self.stack) or "<module>"
        if _is_call_name(node, "dispatch_call_text"):
            call_site = _literal_first_arg(node)
            if call_site:
                self.dispatch_sites.append(
                    DispatchSite(self.path, node.lineno, function, call_site)
                )
            else:
                self.findings.append(
                    Finding(
                        self.path,
                        node.lineno,
                        function,
                        "dispatch_call_text_nonliteral_site",
                        "dispatch_call_text first argument must be a literal call-site name",
                    )
                )
        if _is_attr_call(node, "call_text") and not self._inside_dispatch_lambda():
            allowed_reason = ALLOWED_DIRECT.get((self.path, function))
            if allowed_reason is None:
                self.findings.append(
                    Finding(
                        self.path,
                        node.lineno,
                        function,
                        "unwrapped_call_text",
                        "wrap with dispatch_call_text or add an explicit direct-call exception",
                    )
                )
            else:
                self.dispatch_sites.append(
                    DispatchSite(self.path, node.lineno, function, f"direct:{allowed_reason}")
                )
        self.generic_visit(node)

    def _inside_dispatch_lambda(self) -> bool:
        for idx, parent in enumerate(reversed(self.parent_stack)):
            if isinstance(parent, ast.Lambda):
                ancestors = list(reversed(self.parent_stack))[idx + 1 :]
                return any(
                    isinstance(a, ast.Call) and _is_call_name(a, "dispatch_call_text")
                    for a in ancestors
                )
        return False


def _is_call_name(node: ast.Call, name: str) -> bool:
    if isinstance(node.func, ast.Name):
        return node.func.id == name
    if isinstance(node.func, ast.Attribute):
        return node.func.attr == name
    return False


def _is_attr_call(node: ast.Call, attr: str) -> bool:
    return isinstance(node.func, ast.Attribute) and node.func.attr == attr


def _literal_first_arg(node: ast.Call) -> str | None:
    if not node.args:
        return None
    first = node.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value
    return None


def scan_paths(repo: Path = REPO) -> list[Path]:
    paths: set[Path] = set()
    for pattern in SCAN_GLOBS:
        paths.update(p for p in repo.glob(pattern) if p.is_file())
    for rel in SCAN_FILES:
        p = repo / rel
        if p.is_file():
            paths.add(p)
    return sorted(paths)


def validate(repo: Path = REPO) -> dict[str, object]:
    findings: list[Finding] = []
    dispatch_sites: list[DispatchSite] = []
    scanned: list[str] = []
    for path in scan_paths(repo):
        rel = path.relative_to(repo).as_posix()
        scanned.append(rel)
        source = path.read_text(encoding="utf-8")
        visitor = _Visitor(source, rel)
        visitor.visit(ast.parse(source, filename=rel))
        findings.extend(visitor.findings)
        dispatch_sites.extend(visitor.dispatch_sites)
    registered_sites, registry_error = _registered_family_call_sites()
    if registry_error:
        findings.append(
            Finding(
                "src/ztare/research_director/primitive_family_registry.py",
                1,
                "<module>",
                "family_registry_unavailable",
                registry_error,
            )
        )
    else:
        for site in dispatch_sites:
            if site.call_site.startswith("direct:"):
                continue
            if site.call_site not in registered_sites:
                findings.append(
                    Finding(
                        site.path,
                        site.line,
                        site.function,
                        "dispatch_site_missing_family_card",
                        f"{site.call_site!r} is wrapped but absent from primitive_family_registry",
                    )
                )
    direct_allowed = [
        {
            "path": site.path,
            "line": site.line,
            "function": site.function,
            "reason": site.call_site.removeprefix("direct:"),
        }
        for site in dispatch_sites
        if site.call_site.startswith("direct:")
    ]
    return {
        "schema": "ztare-autoresearch-llm-dispatch-validator-v1",
        "scanned_paths": scanned,
        "summary": {
            "scanned_paths": len(scanned),
            "dispatch_sites": len(dispatch_sites),
            "findings": len(findings),
            "wrapped_sites": sum(1 for s in dispatch_sites if not s.call_site.startswith("direct:")),
            "direct_allowed_sites": sum(1 for s in dispatch_sites if s.call_site.startswith("direct:")),
            "registered_family_call_sites": len(registered_sites),
        },
        "direct_allowed": direct_allowed,
        "dispatch_sites": [asdict(site) for site in dispatch_sites],
        "findings": [asdict(finding) for finding in findings],
    }


def _registered_family_call_sites() -> tuple[set[str], str | None]:
    try:
        from ztare.research_director.primitive_family_registry import dispatch_call_sites
    except Exception as exc:  # noqa: BLE001
        return set(), f"{type(exc).__name__}: {str(exc)[:200]}"
    return set(dispatch_call_sites()), None


def _render_text(report: dict[str, object]) -> str:
    summary = report["summary"]
    assert isinstance(summary, dict)
    lines = [
        "Autoresearch LLM dispatch validator",
        f"scanned_paths: {summary['scanned_paths']}",
        f"dispatch_sites: {summary['dispatch_sites']}",
        f"wrapped_sites: {summary['wrapped_sites']}",
        f"direct_allowed_sites: {summary['direct_allowed_sites']}",
        f"registered_family_call_sites: {summary['registered_family_call_sites']}",
        f"findings: {summary['findings']}",
    ]
    direct_allowed = report.get("direct_allowed")
    if isinstance(direct_allowed, list) and direct_allowed:
        lines.append("")
        lines.append("Direct allowed call sites:")
        for item in direct_allowed:
            lines.append(
                f"- {item['path']}:{item['line']} {item['function']}: {item['reason']}"
            )
    findings = report["findings"]
    assert isinstance(findings, list)
    if findings:
        lines.append("")
        lines.append("Findings:")
        for item in findings:
            lines.append(
                f"- {item['path']}:{item['line']} {item['function']} "
                f"{item['kind']}: {item['detail']}"
            )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    args = parser.parse_args(argv)
    report = validate()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(_render_text(report))
    return 1 if report["summary"]["findings"] else 0  # type: ignore[index]


if __name__ == "__main__":
    raise SystemExit(main())
