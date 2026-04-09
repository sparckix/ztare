from __future__ import annotations

import ast
import re
import symtable
from pathlib import Path


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


def jaccard_distance(set_a: set[str], set_b: set[str]) -> float:
    union = set_a | set_b
    if not union:
        return 0.0
    return 1.0 - (len(set_a & set_b) / len(union))


def normalize_anchor_proxy_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        return ""
    if normalized.startswith(("proxy:", "test:", "unresolved:")):
        return normalized
    if normalized.startswith("test_"):
        return f"test:{normalized}"
    return f"proxy:{normalized}"


def extract_anchor_proxies_from_charter(charter_text: str | None) -> list[str]:
    if not charter_text:
        return []

    lines = charter_text.splitlines()
    in_section = False
    anchors: list[str] = []
    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped.startswith("## "):
            in_section = stripped == "## Anchor Proxies"
            continue
        if not in_section:
            continue
        if not stripped:
            continue
        if stripped.startswith("### "):
            break
        match = re.match(r"^-\s+(.+?)\s*$", stripped)
        if not match:
            continue
        normalized = normalize_anchor_proxy_name(match.group(1))
        if normalized:
            anchors.append(normalized)
    return anchors


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
