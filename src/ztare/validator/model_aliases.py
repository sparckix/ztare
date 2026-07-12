from __future__ import annotations

import ast


def ensure_canonical_model_aliases(code: str) -> str:
    """Expose predictor aliases without confusing carrier combinators.

    Some legacy substrates call ``f``, ``model``, or ``I_model`` directly.
    A patch-base candidate is different: ``PATCH_DELTA(base_next, state,
    action, t)`` is a combiner, not a world-model predictor. Exporting it as a
    predictor creates an invalid carrier that gate harnesses may call with the
    wrong arity. The invariant is role/arity based and substrate-neutral.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code

    top_level_names = _top_level_names(tree)
    if {"f", "model", "I_model"}.issubset(top_level_names):
        return code

    canonical_name = _canonical_predictor_name(tree, top_level_names)
    if canonical_name is None:
        return code

    suffix_lines = [
        "",
        "# Canonical aliases - gate harnesses may call f(), model(), or I_model()",
    ]
    if "f" not in top_level_names and canonical_name != "f":
        suffix_lines.append(f"f = {canonical_name}")
    if "model" not in top_level_names and canonical_name != "model":
        suffix_lines.append(f"model = {canonical_name}")
    if "I_model" not in top_level_names and canonical_name != "I_model":
        suffix_lines.append(f"I_model = {canonical_name}")
    if len(suffix_lines) <= 2:
        return code
    return code.rstrip() + "\n" + "\n".join(suffix_lines) + "\n"


def _top_level_names(tree: ast.Module) -> set[str]:
    names: set[str] = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def _canonical_predictor_name(tree: ast.Module, names: set[str]) -> str | None:
    for preferred in ("I_model", "f", "model", "step"):
        if preferred in names and _is_predictor_callable(tree, preferred):
            return preferred

    skip_prefixes = ("test", "assert", "check", "verify", "_")
    skip_names = {
        "PATCH_DELTA",
        "PATCH_BASE",
        "PROGRAM",
        "WORLD_MODEL_SPEC",
        "GOAL_PREDICATE",
        "PROGRESS",
    }
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name in skip_names or any(node.name.startswith(prefix) for prefix in skip_prefixes):
            continue
        if _callable_arity(node) in {1, 2, 3}:
            return node.name
    return None


def _is_predictor_callable(tree: ast.Module, name: str) -> bool:
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return _callable_arity(node) in {1, 2, 3}
        if isinstance(node, ast.Assign):
            if not any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                continue
            if isinstance(node.value, ast.Name) and node.value.id == "PATCH_DELTA":
                return False
            return True
    return False


def _callable_arity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    args = node.args
    positional = len(args.posonlyargs) + len(args.args)
    required_kwonly = sum(1 for default in args.kw_defaults if default is None)
    return positional + required_kwonly
