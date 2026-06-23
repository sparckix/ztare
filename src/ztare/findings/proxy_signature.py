"""Anchor-proxy signature extraction from a project's test harness.

Originally this module was a junk drawer holding proxy extraction,
generic set distance, charter parsing, and forecast-type normalization.
The 2026-04-11 split moved:

- ``jaccard_distance`` → ``set_distance.py``
- charter parsers and name normalizers → ``charter_parsing.py``

Re-exports of the moved symbols are intentionally NOT provided. There
were only two callers in-tree (``test_thesis.py``, ``autoresearch_loop.py``),
both updated in the same commit, so a transitional shim would just be
dead code.

What remains here is the original concern the file was named for:
walking ``test_model.py`` and producing the set of identifiers the
test suite actually exercises (its "proxy signature"), plus the
anchor-vs-active drift comparison built on top of it.
"""

from __future__ import annotations

import ast
import re
import symtable
from pathlib import Path

from ztare.validator.core.charter_parsing import normalize_anchor_proxy_name


def _collect_name_targets(target: ast.AST) -> set[str]:
    names: set[str] = set()
    if isinstance(target, ast.Name):
        names.add(target.id)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            names.update(_collect_name_targets(elt))
    return names


def _extract_unresolved_tokens(source: str) -> set[str]:
    tokens: set[str] = set()
    stopwords = {"a", "an", "and", "as", "for", "of", "or", "the", "to", "vs", "whether"}
    for line in source.splitlines():
        if "UNRESOLVED:" not in line:
            continue
        _, _, tail = line.partition("UNRESOLVED:")
        candidate = tail.lstrip(" :#")
        candidate = re.split(r"[—.-]", candidate, maxsplit=1)[0]
        words = [
            word
            for word in re.findall(r"[A-Za-z]+", candidate.lower())
            if word not in stopwords
        ]
        if words:
            tokens.add(f"unresolved:{'_'.join(words[:3])}")
    return tokens


def _iter_top_level_runtime_nodes(tree: ast.Module) -> list[ast.AST]:
    runtime_nodes: list[ast.AST] = []
    for node in tree.body:
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
                ast.Import,
                ast.ImportFrom,
            ),
        ):
            continue
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            continue
        runtime_nodes.append(node)
    return runtime_nodes


def _collect_loaded_names(nodes: list[ast.AST]) -> set[str]:
    loaded: set[str] = set()
    for node in nodes:
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                loaded.add(child.id)
    return loaded


def extract_proxy_set(test_model_path: Path) -> set[str]:
    source = test_model_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(test_model_path))
    table = symtable.symtable(source, str(test_model_path), "exec")

    module_level_names: set[str] = set()
    test_nodes: list[ast.FunctionDef | ast.AsyncFunctionDef] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            module_level_names.add(node.name)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
                "test_"
            ):
                test_nodes.append(node)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                module_level_names.update(_collect_name_targets(target))
        elif isinstance(node, ast.AnnAssign):
            module_level_names.update(_collect_name_targets(node.target))

    function_tables = {
        (child.get_name(), child.get_lineno()): child
        for child in table.get_children()
        if child.get_type() == "function"
    }

    proxies: set[str] = set()
    for node in test_nodes:
        proxies.add(f"test:{node.name}")
        fn_table = function_tables.get((node.name, node.lineno))
        if fn_table is None:
            continue
        for symbol in fn_table.get_symbols():
            if not symbol.is_referenced() or not symbol.is_global():
                continue
            name = symbol.get_name()
            if name in module_level_names and not name.startswith("__"):
                proxies.add(f"proxy:{name}")

    # Fallback for older suites that execute checks at module scope rather than in test_* functions.
    top_level_loaded_names = _collect_loaded_names(_iter_top_level_runtime_nodes(tree))
    for name in top_level_loaded_names:
        if name in module_level_names and not name.startswith("__"):
            proxies.add(f"proxy:{name}")

    proxies.update(_extract_unresolved_tokens(source))
    return proxies


def compute_anchor_proxy_coverage(
    test_model_path: Path,
    anchor_proxies: list[str],
) -> dict[str, object]:
    normalized_anchors = {
        normalized
        for name in anchor_proxies
        if (normalized := normalize_anchor_proxy_name(name))
    }
    active_proxies = extract_proxy_set(test_model_path)
    overlap = active_proxies & normalized_anchors
    coverage = len(overlap) / len(normalized_anchors) if normalized_anchors else 1.0
    return {
        "active_proxies": sorted(active_proxies),
        "anchor_proxies": sorted(normalized_anchors),
        "overlap": sorted(overlap),
        "anchor_total": len(normalized_anchors),
        "overlap_count": len(overlap),
        "coverage": coverage,
        "drift_distance": 1.0 - coverage if normalized_anchors else 0.0,
    }
